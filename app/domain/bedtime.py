"""Motor de recomendación de hora de acostarse.

Función pura: no toca base de datos, ni red, ni el reloj del sistema. Todo lo que
necesita entra por parámetros. Eso hace que cada regla sea testeable, que dos
ejecuciones con los mismos datos den lo mismo, y que la app pueda explicar por qué
recomienda una hora en vez de limitarse a decirla.

El LLM no participa en este cálculo. Entrevista al usuario y narra el resultado,
pero los minutos los pone este fichero.

Distinción central de la app: la hora recomendada es la de **meterse en la cama**,
no la de dormirse. Entre una y otra está la latencia de conciliación, que en una
persona con insomnio de inicio pasa a menudo de 45 minutos. Recomendar "acuéstate a
las 23:00 para dormir 8 horas" a quien tarda 50 minutos en dormirse le está pidiendo
7 horas y 10 minutos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

# --- Topes de seguridad ---------------------------------------------------------
# El objetivo de sueño se recorta a este rango pase lo que pase con los ajustes.
# Sin techo, unos días malos encadenados acaban recomendando 11 horas en la cama,
# que es contraproducente; sin suelo, una siesta larga podría bajar la recomendación
# a un valor que ninguna guía de sueño respalda.
SLEEP_NEED_FLOOR_MINUTES = 360  # 6 h
SLEEP_NEED_CEILING_MINUTES = 600  # 10 h

# La deuda de sueño no se paga de golpe: dormir tres horas de más una noche desplaza
# el ritmo circadiano y empeora la noche siguiente. Se recupera a plazos.
DEBT_RECOVERY_RATIO = 0.25
DEBT_RECOVERY_CAP_MINUTES = 60

# Se recomienda una ventana, no un instante. Un "acuéstate a las 23:37" es precisión
# falsa: ni los datos del reloj ni la fisiología dan para ese nivel de detalle.
WINDOW_HALF_WIDTH_MINUTES = 20

# Por debajo de esta eficiencia (dormido / tiempo en cama) el problema no es falta de
# oportunidad para dormir, es que la cama se está usando para estar despierto.
RESTRICTION_EFFICIENCY_THRESHOLD = 0.85
RESTRICTION_MIN_NIGHTS = 5
RESTRICTION_BUFFER_MINUTES = 30
RESTRICTION_FLOOR_MINUTES = 330  # 5 h 30: suelo de la restricción de sueño clásica

# Margen de vigilia tolerable dentro de la ventana cuando la eficiencia es buena.
# Sin este tope, `objetivo / eficiencia` crece sin control: con una eficiencia del 86%
# y un objetivo de 9 h salen 10 h 40 en la cama, que es exactamente lo que la app
# desaconseja en el modo restricción.
MAX_WAKE_IN_BED_MINUTES = 60

# Ejercicio intenso terminado dentro de esta ventana antes de acostarse: la
# temperatura central sigue alta y la conciliación se alarga.
LATE_EXERCISE_HOURS = 3
LATE_EXERCISE_LATENCY_PENALTY = 15

# La cafeína tiene una vida media de 5-6 h: la tomada por la tarde sigue en sangre
# a la hora de acostarse.
CAFFEINE_CUTOFF_HOURS = 8
CAFFEINE_LATENCY_PENALTY = 10

# El alcohol acorta la latencia y fragmenta la segunda mitad de la noche: no se
# compensa alargando el sueño, se avisa y se baja la eficiencia esperada.
ALCOHOL_EFFICIENCY_PENALTY = 0.04

INTENSITY_LEVELS = ("none", "light", "moderate", "hard")


@dataclass(frozen=True)
class SleepProfile:
    """Lo que sabemos del usuario a medio plazo, no de hoy."""

    sleep_need_minutes: int = 480
    # Mediana observada de lo que tarda en dormirse, o lo que declara si no hay datos.
    onset_latency_minutes: int = 20
    # Dormido / tiempo en cama, medido por el reloj sobre las últimas noches.
    efficiency: float = 0.90
    # Media de sueño real reciente. Necesaria para el modo restricción.
    observed_sleep_minutes: int | None = None
    nights_observed: int = 0


@dataclass(frozen=True)
class DaySignals:
    """Lo de hoy: mitad del reloj, mitad del check-in conversacional."""

    sleep_debt_minutes: int = 0
    # 0-100, más alto es más estrés. Cada adaptador de wearable normaliza a esta
    # escala (el Body Battery de Garmin va al revés y se invierte en su adaptador).
    stress: int | None = None
    exercise_minutes: int = 0
    exercise_intensity: str = "none"
    exercise_end: time | None = None
    nap_minutes: int = 0
    mood: int | None = None  # 1-5, del check-in
    last_caffeine: time | None = None
    alcohol: bool = False


@dataclass(frozen=True)
class Factor:
    """Una contribución al objetivo de sueño, en minutos, con su porqué.

    Es lo que hace la recomendación auditable: el usuario puede ver que los 25
    minutos de más vienen de la deuda acumulada y no de una corazonada del modelo.
    """

    label: str
    minutes: int
    detail: str


@dataclass(frozen=True)
class Recommendation:
    bedtime: time
    window_start: time
    window_end: time
    target_sleep_minutes: int
    time_in_bed_minutes: int
    onset_latency_minutes: int
    mode: str  # "normal" | "restriccion"
    confidence: str  # "baja" | "media" | "alta"
    factors: list[Factor] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _shift(reference: time, minutes: int) -> time:
    """Aritmética de horas que cruza medianoche sin sorpresas."""
    anchor = datetime.combine(date(2000, 1, 2), reference)
    return (anchor + timedelta(minutes=minutes)).time()


def _hours_between(earlier: time, later: time) -> float:
    """Horas de `earlier` a `later`, asumiendo que `later` cae el mismo día o el
    siguiente. Sirve para medir cuánto falta del último café a la cama."""
    a = datetime.combine(date(2000, 1, 2), earlier)
    b = datetime.combine(date(2000, 1, 2), later)
    if b < a:
        b += timedelta(days=1)
    return (b - a).total_seconds() / 3600


def _confidence(nights_observed: int) -> str:
    if nights_observed >= 14:
        return "alta"
    if nights_observed >= RESTRICTION_MIN_NIGHTS:
        return "media"
    return "baja"


def recommend_bedtime(
    wake_target: time,
    profile: SleepProfile,
    signals: DaySignals,
) -> Recommendation:
    """Hora a la que meterse en la cama para levantarse a `wake_target`."""
    factors: list[Factor] = [
        Factor("Necesidad basal", profile.sleep_need_minutes, "Tu necesidad de sueño de referencia")
    ]
    notes: list[str] = []
    target = profile.sleep_need_minutes

    if signals.sleep_debt_minutes > 0:
        recovery = min(
            round(signals.sleep_debt_minutes * DEBT_RECOVERY_RATIO), DEBT_RECOVERY_CAP_MINUTES
        )
        if recovery:
            target += recovery
            factors.append(
                Factor(
                    "Deuda de sueño",
                    recovery,
                    f"Arrastras {signals.sleep_debt_minutes} min de déficit; se recupera a "
                    f"plazos, no en una sola noche",
                )
            )

    if signals.stress is not None:
        if signals.stress >= 70:
            target += 20
            factors.append(Factor("Estrés alto", 20, f"Nivel {signals.stress}/100 según el reloj"))
        elif signals.stress >= 55:
            target += 10
            factors.append(Factor("Estrés moderado", 10, f"Nivel {signals.stress}/100"))

    if signals.exercise_minutes >= 45:
        if signals.exercise_intensity == "hard":
            target += 20
            factors.append(
                Factor(
                    "Carga de ejercicio", 20, f"{signals.exercise_minutes} min de intensidad alta"
                )
            )
        elif signals.exercise_intensity == "moderate":
            target += 10
            factors.append(
                Factor(
                    "Carga de ejercicio", 10, f"{signals.exercise_minutes} min de intensidad media"
                )
            )

    if signals.nap_minutes > 0:
        # La siesta descuenta solo la mitad: no equivale al sueño nocturno, pero sí
        # reduce la presión de sueño de esta noche.
        discount = min(round(signals.nap_minutes * 0.5), 45)
        target -= discount
        factors.append(
            Factor("Siesta de hoy", -discount, f"{signals.nap_minutes} min; descuentan a la mitad")
        )

    if signals.mood is not None and signals.mood <= 2:
        target += 10
        factors.append(Factor("Ánimo bajo", 10, "Declarado en el check-in de hoy"))

    clamped = max(SLEEP_NEED_FLOOR_MINUTES, min(target, SLEEP_NEED_CEILING_MINUTES))
    if clamped != target:
        factors.append(
            Factor(
                "Tope de seguridad",
                clamped - target,
                f"El objetivo se recorta al rango {SLEEP_NEED_FLOOR_MINUTES}-"
                f"{SLEEP_NEED_CEILING_MINUTES} min",
            )
        )
    target = clamped

    efficiency = profile.efficiency
    latency = profile.onset_latency_minutes

    if signals.alcohol:
        efficiency = max(0.5, efficiency - ALCOHOL_EFFICIENCY_PENALTY)
        notes.append(
            "Con alcohol te dormirás antes, pero la segunda mitad de la noche se fragmenta. "
            "Eso no se compensa acostándose antes."
        )

    if signals.last_caffeine is not None:
        provisional_bedtime = _shift(wake_target, -round(target / efficiency))
        if _hours_between(signals.last_caffeine, provisional_bedtime) < CAFFEINE_CUTOFF_HOURS:
            latency += CAFFEINE_LATENCY_PENALTY
            notes.append(
                f"Cafeína a las {signals.last_caffeine.strftime('%H:%M')}: con una vida media de "
                f"5-6 h todavía estará activa. Cuenta {CAFFEINE_LATENCY_PENALTY} min más para "
                f"conciliar."
            )

    mode = "normal"
    # Tope duro de vigilia dentro de la ventana: por buena que sea la eficiencia
    # declarada, no se prescribe más de una hora en la cama sin dormir.
    time_in_bed = min(round(target / efficiency), target + MAX_WAKE_IN_BED_MINUTES)

    if (
        profile.nights_observed >= RESTRICTION_MIN_NIGHTS
        and profile.observed_sleep_minutes is not None
    ):
        # La ventana se ancla en lo que la persona duerme de verdad, no en el déficit
        # que arrastra. Quien lleva tres semanas durmiendo seis horas no va a dormir
        # nueve esta noche por estar once en la cama: solo sumará vigilia.
        restricting = profile.efficiency < RESTRICTION_EFFICIENCY_THRESHOLD
        buffer = RESTRICTION_BUFFER_MINUTES if restricting else MAX_WAKE_IN_BED_MINUTES
        anchored = max(profile.observed_sleep_minutes + buffer, RESTRICTION_FLOOR_MINUTES)
        if anchored < time_in_bed:
            time_in_bed = anchored
            if restricting:
                # Contraintuitivo y deliberado: con la eficiencia baja, ampliar la
                # ventana empeora el problema. Cada hora despierta en la cama refuerza
                # la asociación cama-desvelo. Es la base de la restricción de sueño
                # de la TCC-I.
                mode = "restriccion"
                notes.append(
                    f"Tu eficiencia de sueño es del {profile.efficiency:.0%} (dormido frente a "
                    f"tiempo en la cama). Por debajo del {RESTRICTION_EFFICIENCY_THRESHOLD:.0%} lo "
                    f"indicado es acortar la ventana, no alargarla: pasar horas despierta en la "
                    f"cama entrena al cerebro a no dormir en ella."
                )
            else:
                notes.append(
                    f"La ventana se ajusta a lo que duermes de verdad últimamente "
                    f"({profile.observed_sleep_minutes // 60} h {profile.observed_sleep_minutes % 60:02d} "
                    f"min de media) más una hora de margen. Estar más tiempo en la cama no añade "
                    f"sueño: añade vigilia."
                )

    if signals.exercise_end is not None and signals.exercise_intensity in ("moderate", "hard"):
        provisional = _shift(wake_target, -(time_in_bed + latency))
        if _hours_between(signals.exercise_end, provisional) < LATE_EXERCISE_HOURS:
            latency += LATE_EXERCISE_LATENCY_PENALTY
            notes.append(
                f"Terminaste de entrenar a las {signals.exercise_end.strftime('%H:%M')}, menos de "
                f"{LATE_EXERCISE_HOURS} h antes de acostarte: la temperatura corporal sigue alta y "
                f"tardarás más en dormirte."
            )

    bedtime = _shift(wake_target, -(time_in_bed + latency))

    return Recommendation(
        bedtime=bedtime,
        window_start=_shift(bedtime, -WINDOW_HALF_WIDTH_MINUTES),
        window_end=_shift(bedtime, WINDOW_HALF_WIDTH_MINUTES),
        target_sleep_minutes=target,
        time_in_bed_minutes=time_in_bed,
        onset_latency_minutes=latency,
        mode=mode,
        confidence=_confidence(profile.nights_observed),
        factors=factors,
        notes=notes,
    )


def sleep_debt(recent_sleep_minutes: list[int], sleep_need_minutes: int, window: int = 14) -> int:
    """Déficit acumulado en las últimas `window` noches, en minutos.

    Solo suma déficit: las noches en que se duerme de más no generan crédito, porque
    nueve horas un sábado no dejan al cuerpo con reservas para el lunes.
    """
    return sum(max(0, sleep_need_minutes - m) for m in recent_sleep_minutes[-window:])


def build_profile(
    recent_sleep_minutes: list[int],
    recent_time_in_bed_minutes: list[int],
    recent_latency_minutes: list[int | None],
    sleep_need_minutes: int = 480,
) -> SleepProfile:
    """Perfil derivado del histórico del reloj. Con pocas noches cae a los valores
    por defecto, y `nights_observed` deja claro que la confianza es baja.

    Las tres listas van alineadas por noche; la de latencias admite `None` en las
    noches que el reloj no la midió.

    Ojo con la eficiencia: aquí **no** es la definición clásica. El tiempo en cama que
    reporta el reloj incluye los minutos que se tarda en dormir, y `recommend_bedtime`
    suma esa latencia aparte. Dividir por la eficiencia clásica la contaría dos veces
    y adelantaría la hora recomendada entre veinte y cuarenta minutos. Por eso la
    latencia se descuenta del tiempo en cama antes de calcularla: lo que sale mide la
    fragmentación de la noche **una vez dormido**, que es lo que el motor necesita.
    """
    nights = min(len(recent_sleep_minutes), len(recent_time_in_bed_minutes))
    if nights == 0:
        return SleepProfile(sleep_need_minutes=sleep_need_minutes)

    slept = recent_sleep_minutes[-nights:]
    in_bed = recent_time_in_bed_minutes[-nights:]
    # Se rellena por delante: si faltan latencias son las noches más antiguas las que
    # se quedan sin dato, no las recientes.
    latencies_per_night = ([None] * nights + list(recent_latency_minutes))[-nights:]

    measured = [lat for lat in latencies_per_night if lat is not None]
    latency = sorted(measured)[len(measured) // 2] if measured else 20

    asleep_window = [
        max(1, bed - (lat if lat is not None else latency))
        for bed, lat in zip(in_bed, latencies_per_night)
    ]
    total_window = sum(asleep_window)
    efficiency = sum(slept) / total_window if total_window else 0.90

    return SleepProfile(
        sleep_need_minutes=sleep_need_minutes,
        onset_latency_minutes=latency,
        efficiency=round(min(max(efficiency, 0.5), 1.0), 3),
        observed_sleep_minutes=round(sum(slept) / nights),
        nights_observed=nights,
    )
