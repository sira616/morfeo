"""Puente entre la base de datos y el motor puro de `app.domain.bedtime`.

Aquí vive todo lo que ensucia: sesiones de SQLAlchemy, upserts y fechas. El cálculo
en sí no está en este fichero a propósito, para poder testearlo sin base de datos.
"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.domain.bedtime import (
    DaySignals,
    Recommendation,
    SleepDebt,
    SleepProfile,
    build_profile,
    recommend_bedtime,
    sleep_debt,
    sleep_debt_detail,
)
from app.models.sleep import BedtimeRecommendation, Checkin, DailyMetrics, SleepNight
from app.models.user import User
from app.schemas.sleep import SimulationIn
from app.wearables.base import DaySample, NightSample

# Ventana de histórico con la que se construye el perfil. Un mes captura el patrón
# actual sin arrastrar hábitos de hace medio año que ya no aplican.
PROFILE_WINDOW_DAYS = 30
DEBT_WINDOW_DAYS = 14
# Contra qué se compara la deuda de hoy para saber si va subiendo o bajando. Una
# semana: menos es ruido de una noche mala, más y ya no se parece a "cómo voy".
DEBT_TREND_DAYS = 7


def upsert_nights(db: DbSession, user: User, samples: list[NightSample], source: str) -> int:
    """Inserta o actualiza noches. Idempotente por (usuario, fecha).

    Reimportar la misma exportación no duplica: es lo normal cuando se sincroniza a
    diario y el reloj corrige una noche a posteriori.
    """
    written = 0
    for sample in samples:
        night = db.scalar(
            select(SleepNight).where(
                SleepNight.user_id == user.id, SleepNight.night_of == sample.night_of
            )
        )
        if night is None:
            night = SleepNight(user_id=user.id, night_of=sample.night_of)
            db.add(night)
        night.source = source
        night.total_sleep_minutes = sample.total_sleep_minutes
        night.time_in_bed_minutes = sample.time_in_bed_minutes
        night.bed_at = sample.bed_at
        night.sleep_start = sample.sleep_start
        night.sleep_end = sample.sleep_end
        night.out_of_bed_at = sample.out_of_bed_at
        night.onset_latency_minutes = sample.onset_latency_minutes
        night.awakenings = sample.awakenings
        night.deep_minutes = sample.deep_minutes
        night.rem_minutes = sample.rem_minutes
        night.light_minutes = sample.light_minutes
        night.resting_hr = sample.resting_hr
        night.hrv_ms = sample.hrv_ms
        written += 1
    db.commit()
    return written


def upsert_day(db: DbSession, user: User, sample: DaySample, source: str) -> DailyMetrics:
    metrics = db.scalar(
        select(DailyMetrics).where(DailyMetrics.user_id == user.id, DailyMetrics.day == sample.day)
    )
    if metrics is None:
        metrics = DailyMetrics(user_id=user.id, day=sample.day)
        db.add(metrics)
    metrics.source = source
    metrics.steps = sample.steps
    metrics.exercise_minutes = sample.exercise_minutes
    metrics.exercise_intensity = sample.exercise_intensity
    metrics.exercise_end = sample.exercise_end
    metrics.stress_avg = sample.stress_avg
    metrics.resting_hr = sample.resting_hr
    metrics.hrv_ms = sample.hrv_ms
    db.commit()
    return metrics


def recent_nights(db: DbSession, user: User, days: int, until: date) -> list[SleepNight]:
    since = until - timedelta(days=days)
    return list(
        db.scalars(
            select(SleepNight)
            .where(
                SleepNight.user_id == user.id,
                SleepNight.night_of > since,
                SleepNight.night_of <= until,
            )
            .order_by(SleepNight.night_of)
        )
    )


def load_profile(db: DbSession, user: User, today: date) -> SleepProfile:
    nights = recent_nights(db, user, PROFILE_WINDOW_DAYS, today)
    if not nights:
        # Sin histórico se usan las preferencias declaradas y `nights_observed=0`, que
        # es lo que hace que la recomendación salga marcada como confianza baja.
        return SleepProfile(
            sleep_need_minutes=user.sleep_need_minutes,
            onset_latency_minutes=user.declared_latency_minutes,
        )
    # Las latencias van alineadas noche a noche (con None donde el reloj no la midió),
    # porque build_profile las descuenta del tiempo en cama de *esa* noche.
    return build_profile(
        recent_sleep_minutes=[n.total_sleep_minutes for n in nights],
        recent_time_in_bed_minutes=[n.time_in_bed_minutes for n in nights],
        recent_latency_minutes=[n.onset_latency_minutes for n in nights],
        sleep_need_minutes=user.sleep_need_minutes,
    )


def build_signals(db: DbSession, user: User, day: date) -> DaySignals:
    """Junta lo del reloj y lo del check-in en la entrada del motor.

    Cuando las dos fuentes hablan de estrés, manda la del reloj: es una medida, no un
    recuerdo. El estrés percibido del check-in se usa solo si no hay dato medido.
    """
    metrics = db.scalar(
        select(DailyMetrics).where(DailyMetrics.user_id == user.id, DailyMetrics.day == day)
    )
    checkin = db.scalar(select(Checkin).where(Checkin.user_id == user.id, Checkin.day == day))

    nights = recent_nights(db, user, DEBT_WINDOW_DAYS, day)
    debt = sleep_debt([n.total_sleep_minutes for n in nights], user.sleep_need_minutes)

    stress = metrics.stress_avg if metrics and metrics.stress_avg is not None else None
    if stress is None and checkin and checkin.perceived_stress is not None:
        # El check-in va de 1 a 5; la escala del motor es 0-100.
        stress = round((checkin.perceived_stress - 1) * 25)

    # El ejercicio puede venir del reloj o declararse en el check-in. Gana el reloj
    # cuando lo trae: es una medida, no un recuerdo.
    exercise_minutes = metrics.exercise_minutes if metrics and metrics.exercise_minutes else 0
    exercise_intensity = metrics.exercise_intensity if metrics and metrics.exercise_minutes else "none"
    exercise_end = metrics.exercise_end if metrics and metrics.exercise_minutes else None
    if not exercise_minutes and checkin and checkin.exercise_minutes:
        exercise_minutes = checkin.exercise_minutes
        exercise_intensity = checkin.exercise_intensity
        exercise_end = checkin.exercise_end

    return DaySignals(
        sleep_debt_minutes=debt,
        stress=stress,
        exercise_minutes=exercise_minutes,
        exercise_intensity=exercise_intensity,
        exercise_end=exercise_end,
        nap_minutes=checkin.nap_minutes if checkin else 0,
        mood=checkin.mood if checkin else None,
        last_caffeine=checkin.last_caffeine if checkin else None,
        coffees=checkin.coffees if checkin else 0,
        alcohol=bool(checkin.alcohol or checkin.alcohol_units) if checkin else False,
        cannabis_days_ago=checkin.cannabis_days_ago if checkin else None,
        last_meal=checkin.last_meal if checkin else None,
    )


def debt_on(db: DbSession, user: User, day: date) -> int:
    """Deuda acumulada tal como estaba el día `day`, en minutos."""
    nights = recent_nights(db, user, DEBT_WINDOW_DAYS, day)
    return sleep_debt([n.total_sleep_minutes for n in nights], user.sleep_need_minutes)


def debt_detail(db: DbSession, user: User, day: date) -> tuple[SleepDebt, int | None]:
    """La deuda de hoy con su contexto, y la que había hace una semana.

    La segunda es lo que convierte el número en una dirección. Va a `None` cuando no
    hay histórico suficiente para mirar tan atrás: inventar un cero de referencia
    haría que la primera semana de uso saliera siempre "subiendo".
    """
    nights = recent_nights(db, user, DEBT_WINDOW_DAYS, day)
    detail = sleep_debt_detail(
        [n.total_sleep_minutes for n in nights], user.sleep_need_minutes, DEBT_WINDOW_DAYS
    )

    before = day - timedelta(days=DEBT_TREND_DAYS)
    earlier = recent_nights(db, user, DEBT_WINDOW_DAYS, before)
    # Solo se compara contra una ventana igual de llena. Durante las tres primeras
    # semanas de uso la ventana de atrás tiene menos noches que la de ahora, así que
    # la deuda sale "subiendo" siempre —no porque se duerma peor, sino porque hay más
    # noches contadas—, y ese es justo el número que no conviene enseñar de noche.
    previous = (
        sleep_debt([n.total_sleep_minutes for n in earlier], user.sleep_need_minutes)
        if len(earlier) >= detail.nights_counted
        else None
    )
    return detail, previous


def apply_overrides(signals: DaySignals, sim: SimulationIn) -> DaySignals:
    """Sustituye en las señales de hoy lo que traiga la simulación.

    Dos reglas que no son obvias, y sin las cuales el simulador miente:

    - Simular **cero cafés** borra también la hora del último. El motor trata «hay
      hora de café pero no sé cuántos» como dosis media, así que dejar la hora puesta
      haría que quitar todos los cafés siguiera penalizando, y el usuario vería que
      su cambio no hace nada.
    - Simular **cero minutos de ejercicio** apaga la intensidad y la hora de fin, por
      lo mismo. Y si alguien manda 0 minutos con intensidad alta, mandan los minutos:
      es una entrada que se contradice, y la parte que dice «no hubo» es la más
      concreta.
    """
    changes: dict[str, object] = {}

    if sim.coffees is not None:
        changes["coffees"] = sim.coffees
    if sim.last_caffeine is not None:
        changes["last_caffeine"] = sim.last_caffeine
    elif sim.coffees == 0:
        changes["last_caffeine"] = None

    if sim.nap_minutes is not None:
        changes["nap_minutes"] = sim.nap_minutes

    if sim.exercise_minutes is not None:
        changes["exercise_minutes"] = sim.exercise_minutes
    if sim.exercise_intensity is not None:
        changes["exercise_intensity"] = sim.exercise_intensity
    if sim.exercise_end is not None:
        changes["exercise_end"] = sim.exercise_end
    if sim.exercise_minutes == 0:
        changes["exercise_intensity"] = "none"
        changes["exercise_end"] = None

    return replace(signals, **changes) if changes else signals


def resolve_wake_target(
    db: DbSession, user: User, day: date, override: time | None
) -> tuple[time, str]:
    """Hora de despertar y **de dónde sale**.

    El check-in de hoy gana sobre el perfil, porque "mañana me levanto a las seis" es
    más específico que un valor por defecto. Pero esa precedencia hay que contarla: sin
    decirlo, cambiar la hora en el perfil no hacía nada y parecía que la app se había
    quedado colgada.
    """
    if override is not None:
        return override, "simulacion"
    checkin = db.scalar(select(Checkin).where(Checkin.user_id == user.id, Checkin.day == day))
    if checkin and checkin.wake_target:
        return checkin.wake_target, "checkin"
    return user.default_wake_time, "perfil"


def compute(
    db: DbSession,
    user: User,
    day: date,
    wake_target: time | None = None,
    simulation: SimulationIn | None = None,
) -> Recommendation:
    """La recomendación del día, opcionalmente con señales sustituidas.

    `simulation` no toca nada guardado: solo cambia las señales que entran al motor
    para esta llamada. Quien la use es responsable de **no** llamar a `store` después.
    """
    resolved, _ = resolve_wake_target(db, user, day, wake_target)
    signals = build_signals(db, user, day)
    if simulation is not None:
        signals = apply_overrides(signals, simulation)
    return recommend_bedtime(
        wake_target=resolved,
        profile=load_profile(db, user, day),
        signals=signals,
    )


def store(
    db: DbSession, user: User, day: date, wake_target: time, rec: Recommendation
) -> BedtimeRecommendation:
    """Congela la recomendación del día.

    Guardarla no es opcional: sin el registro de qué se recomendó y con qué factores,
    no hay forma de comprobar después si el motor acertaba.
    """
    row = db.scalar(
        select(BedtimeRecommendation).where(
            BedtimeRecommendation.user_id == user.id, BedtimeRecommendation.day == day
        )
    )
    if row is None:
        row = BedtimeRecommendation(user_id=user.id, day=day)
        db.add(row)
    row.wake_target = wake_target
    row.bedtime = rec.bedtime
    row.window_start = rec.window_start
    row.window_end = rec.window_end
    row.target_sleep_minutes = rec.target_sleep_minutes
    row.sleep_window_minutes = rec.sleep_window_minutes
    row.onset_latency_minutes = rec.onset_latency_minutes
    row.mode = rec.mode
    row.confidence = rec.confidence
    row.factors = json.dumps([f.__dict__ for f in rec.factors], ensure_ascii=False)
    row.notes = json.dumps(rec.notes, ensure_ascii=False)
    db.commit()
    db.refresh(row)
    return row


def upsert_checkin(db: DbSession, user: User, day: date, fields: dict) -> Checkin:
    checkin = db.scalar(select(Checkin).where(Checkin.user_id == user.id, Checkin.day == day))
    if checkin is None:
        checkin = Checkin(user_id=user.id, day=day)
        db.add(checkin)
    # Un `None` explícito **borra**, y tiene que poder hacerlo: sin esto no había
    # forma de quitar la hora de despertar de un check-in, que se quedaba mandando
    # sobre el perfil para siempre.
    #
    # Quien no quiera pisar nada simplemente no manda la clave: la ruta usa
    # `exclude_unset`, y el extractor del LLM filtra sus nulos antes de llamar aquí,
    # porque "no supe deducirlo" no es lo mismo que "bórralo".
    for key, value in fields.items():
        if hasattr(checkin, key):
            setattr(checkin, key, value)
    db.commit()
    db.refresh(checkin)
    return checkin
