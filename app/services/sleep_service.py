"""Puente entre la base de datos y el motor puro de `app.domain.bedtime`.

Aquí vive todo lo que ensucia: sesiones de SQLAlchemy, upserts y fechas. El cálculo
en sí no está en este fichero a propósito, para poder testearlo sin base de datos.
"""
from __future__ import annotations

import json
from datetime import date, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.domain.bedtime import (
    DaySignals,
    Recommendation,
    SleepProfile,
    build_profile,
    recommend_bedtime,
    sleep_debt,
)
from app.models.sleep import BedtimeRecommendation, Checkin, DailyMetrics, SleepNight
from app.models.user import User
from app.wearables.base import DaySample, NightSample

# Ventana de histórico con la que se construye el perfil. Un mes captura el patrón
# actual sin arrastrar hábitos de hace medio año que ya no aplican.
PROFILE_WINDOW_DAYS = 30
DEBT_WINDOW_DAYS = 14


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
    return build_profile(
        recent_sleep_minutes=[n.total_sleep_minutes for n in nights],
        recent_time_in_bed_minutes=[n.time_in_bed_minutes for n in nights],
        recent_latency_minutes=[
            n.onset_latency_minutes for n in nights if n.onset_latency_minutes is not None
        ]
        or [user.declared_latency_minutes],
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

    return DaySignals(
        sleep_debt_minutes=debt,
        stress=stress,
        exercise_minutes=metrics.exercise_minutes if metrics else 0,
        exercise_intensity=metrics.exercise_intensity if metrics else "none",
        exercise_end=metrics.exercise_end if metrics else None,
        nap_minutes=checkin.nap_minutes if checkin else 0,
        mood=checkin.mood if checkin else None,
        last_caffeine=checkin.last_caffeine if checkin else None,
        alcohol=bool(checkin.alcohol) if checkin else False,
    )


def resolve_wake_target(db: DbSession, user: User, day: date, override: time | None) -> time:
    if override is not None:
        return override
    checkin = db.scalar(select(Checkin).where(Checkin.user_id == user.id, Checkin.day == day))
    if checkin and checkin.wake_target:
        return checkin.wake_target
    return user.default_wake_time


def compute(db: DbSession, user: User, day: date, wake_target: time | None = None) -> Recommendation:
    return recommend_bedtime(
        wake_target=resolve_wake_target(db, user, day, wake_target),
        profile=load_profile(db, user, day),
        signals=build_signals(db, user, day),
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
    row.time_in_bed_minutes = rec.time_in_bed_minutes
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
    for key, value in fields.items():
        # Un campo que el extractor no supo deducir llega como None y no debe borrar
        # lo que la persona ya había respondido antes en el formulario.
        if value is not None and hasattr(checkin, key):
            setattr(checkin, key, value)
    db.commit()
    db.refresh(checkin)
    return checkin
