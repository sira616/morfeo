"""Métricas derivadas del histórico. Puras, como el motor de `bedtime.py`.

Todo lo que hay aquí se calcula sobre minutos desde medianoche, y por eso casi todas
las funciones usan **estadística circular**: el punto medio de sueño de alguien que se
acuesta a las 00:30 vale 30, y el de quien se acuesta a las 23:30 vale 1410. La media
aritmética de esos dos da las 12 del mediodía, que es absurdo. En el círculo da la
medianoche, que es lo correcto.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime

MINUTES_PER_DAY = 1440

# Por encima de esta desviación el horario ya no tiene forma reconocible. Sirve para
# llevar la dispersión a una puntuación de 0 a 100 que se pueda enseñar.
REGULARITY_WORST_SD_MINUTES = 120
MIN_NIGHTS_FOR_REGULARITY = 5


@dataclass(frozen=True)
class Regularity:
    score: int  # 0-100, más alto es más regular
    sd_minutes: int
    mean_midpoint_minutes: int
    nights: int


def midpoint_minutes(sleep_start: datetime, sleep_end: datetime) -> int:
    """Punto medio del sueño, en minutos desde medianoche.

    Es el marcador de fase circadiana que usan los estudios de regularidad, y aguanta
    mejor que "hora de acostarse" cuando la duración cambia de una noche a otra.
    """
    middle = sleep_start + (sleep_end - sleep_start) / 2
    return middle.hour * 60 + middle.minute


def _circular_mean_and_sd(values: list[int]) -> tuple[float, float]:
    """Media y desviación circulares, en minutos."""
    angles = [2 * math.pi * v / MINUTES_PER_DAY for v in values]
    sin_sum = sum(math.sin(a) for a in angles) / len(angles)
    cos_sum = sum(math.cos(a) for a in angles) / len(angles)

    mean_angle = math.atan2(sin_sum, cos_sum) % (2 * math.pi)
    mean = mean_angle * MINUTES_PER_DAY / (2 * math.pi)

    # R es la longitud del vector resultante: 1 con todos los valores iguales, 0 con
    # los valores repartidos por todo el círculo.
    r = math.hypot(sin_sum, cos_sum)
    if r >= 1.0:
        return mean, 0.0
    sd_angle = math.sqrt(-2 * math.log(r))
    return mean, sd_angle * MINUTES_PER_DAY / (2 * math.pi)


def regularity(midpoints: list[int]) -> Regularity | None:
    """Cómo de estable es el horario. `None` si no hay noches suficientes."""
    if len(midpoints) < MIN_NIGHTS_FOR_REGULARITY:
        return None

    mean, sd = _circular_mean_and_sd(midpoints)
    score = round(100 * max(0.0, 1 - sd / REGULARITY_WORST_SD_MINUTES))
    return Regularity(
        score=score,
        sd_minutes=round(sd),
        mean_midpoint_minutes=round(mean) % MINUTES_PER_DAY,
        nights=len(midpoints),
    )


def current_streak(followed_by_day: list[tuple[date, bool | None]]) -> int:
    """Noches seguidas siguiendo la recomendación, contando desde la más reciente.

    Un día sin respuesta (`None`) no rompe la racha pero tampoco suma: castigar el
    olvido de marcarlo convertiría la racha en una obligación de registrar, que es
    justo el tipo de presión que estropea el sueño.
    """
    streak = 0
    for _, followed in sorted(followed_by_day, key=lambda pair: pair[0], reverse=True):
        if followed is True:
            streak += 1
        elif followed is False:
            break
    return streak


def adherence_rate(followed_by_day: list[tuple[date, bool | None]]) -> float | None:
    """Proporción de noches seguidas sobre las que sí se respondieron."""
    answered = [f for _, f in followed_by_day if f is not None]
    if not answered:
        return None
    return round(sum(answered) / len(answered), 3)


# --- Qué acompaña a tus mejores noches -----------------------------------------
# Con menos noches de estas a cada lado la diferencia es ruido y no se enseña.
MIN_NIGHTS_PER_SIDE = 3
# Por debajo de esta diferencia tampoco vale la pena decir nada: veinte minutos
# entran dentro de la variación normal entre noches.
MIN_MEANINGFUL_DELTA_MINUTES = 20

FACTOR_LABELS: dict[str, str] = {
    "cafe_tarde": "café después de las cuatro",
    "muchos_cafes": "tres cafés o más",
    "alcohol": "alcohol",
    "cannabis": "cannabis",
    "ejercicio": "media hora de ejercicio",
    "siesta": "siesta",
    "cena_tarde": "cenar tarde",
    "animo_bajo": "ánimo bajo",
}


@dataclass(frozen=True)
class FactorAssociation:
    key: str
    label: str
    nights_with: int
    nights_without: int
    mean_sleep_with: int
    mean_sleep_without: int
    mean_efficiency_with: float
    mean_efficiency_without: float

    @property
    def delta_sleep_minutes(self) -> int:
        return self.mean_sleep_with - self.mean_sleep_without


def associations(
    samples: list[tuple[set[str], int, float]],
    min_per_side: int = MIN_NIGHTS_PER_SIDE,
) -> list[FactorAssociation]:
    """Compara las noches con cada factor contra las noches sin él.

    Es una **asociación, no una causa**, y el nombre de la función no lo disimula: son
    los datos de una sola persona, sin control de nada. Sirve para mirar dónde fijarse,
    no para concluir.

    Cada muestra es (factores presentes ese día, minutos dormidos esa noche,
    eficiencia). Se descartan los factores que no tengan suficientes noches a los dos
    lados, porque con dos noches cualquier diferencia es ruido.
    """
    if not samples:
        return []

    found: list[FactorAssociation] = []
    for key in FACTOR_LABELS:
        with_it = [(sleep, eff) for factors, sleep, eff in samples if key in factors]
        without_it = [(sleep, eff) for factors, sleep, eff in samples if key not in factors]
        if len(with_it) < min_per_side or len(without_it) < min_per_side:
            continue

        found.append(
            FactorAssociation(
                key=key,
                label=FACTOR_LABELS[key],
                nights_with=len(with_it),
                nights_without=len(without_it),
                mean_sleep_with=round(sum(s for s, _ in with_it) / len(with_it)),
                mean_sleep_without=round(sum(s for s, _ in without_it) / len(without_it)),
                mean_efficiency_with=round(sum(e for _, e in with_it) / len(with_it), 3),
                mean_efficiency_without=round(sum(e for _, e in without_it) / len(without_it), 3),
            )
        )

    # Lo que más mueve la aguja primero, en cualquier dirección.
    relevant = [f for f in found if abs(f.delta_sleep_minutes) >= MIN_MEANINGFUL_DELTA_MINUTES]
    return sorted(relevant, key=lambda f: abs(f.delta_sleep_minutes), reverse=True)


# --- Informe de la semana --------------------------------------------------------
# Se mira una ventana móvil de siete noches que termina hoy, no la semana natural. Un
# informe que solo tiene sentido los domingos obliga a acordarse de entrar el domingo;
# este se puede abrir cualquier día y siempre habla de las últimas siete noches.
WEEK_NIGHTS = 7

# Con menos noches medidas no hay semana que resumir: dos noches no tienen media.
MIN_NIGHTS_FOR_WEEK = 3

# Cuántas de las peores noches se miran para buscar qué las acompañó.
WORST_NIGHTS_LOOKED_AT = 3
# Un factor que aparece en una sola de esas noches es una anécdota.
MIN_WORST_NIGHTS_WITH_FACTOR = 2
# Y por debajo de esto no hay semana suficiente para separar las peores del resto.
MIN_NIGHTS_FOR_WORST_FACTORS = 5

# Umbrales para decidir si un cambio merece una frase. Por debajo es la variación
# normal de una semana a otra, y contarla como noticia sería ruido con formato.
MEANINGFUL_SLEEP_DELTA_MINUTES = 20
MEANINGFUL_SHIFT_MINUTES = 30
MEANINGFUL_SD_DELTA_MINUTES = 15
MEANINGFUL_DEBT_DELTA_MINUTES = 60


@dataclass(frozen=True)
class WeekStats:
    """Las medias de una semana. Todo a `None` cuando faltan noches, nunca a cero."""

    nights: int
    mean_sleep_minutes: int | None
    mean_efficiency: float | None
    # Circulares los dos, por lo mismo que el resto del módulo.
    mean_midpoint_minutes: int | None
    sd_midpoint_minutes: int | None


@dataclass(frozen=True)
class WeeklyFactor:
    """Qué acompañó a las peores noches de la semana.

    Con siete noches no hay estadística que valga, así que esto no afirma nada: dice
    en cuántas de las peores estaba el factor y en cuántas del resto, y deja la
    comparación a la vista para que se pueda desconfiar de ella.
    """

    key: str
    label: str
    nights_worst: int
    of_worst: int
    nights_rest: int
    of_rest: int


def circular_delta(now: int, before: int) -> int:
    """Cuánto se movió una hora respecto de otra, por el camino corto.

    En minutos con signo: positivo es más tarde. Pasar de las 23:50 a las 00:20 son
    treinta minutos más tarde, no mil cuatrocientos menos.
    """
    diff = (now - before) % MINUTES_PER_DAY
    return diff - MINUTES_PER_DAY if diff > MINUTES_PER_DAY // 2 else diff


def within_window(actual: int, start: int, end: int) -> bool:
    """¿Se metió en la cama dentro de la ventana recomendada?

    Los tres van en minutos desde medianoche, y la ventana cruza medianoche a menudo:
    de 23:40 a 00:20 el rango válido es "desde 1420" **o** "hasta 20", no un intervalo
    corriente.
    """
    if start <= end:
        return start <= actual <= end
    return actual >= start or actual <= end


def week_stats(
    sleep_minutes: list[int], efficiencies: list[float], midpoints: list[int]
) -> WeekStats:
    """Resumen de una semana.

    La lista de puntos medios puede ser más corta que la de duraciones: muchos
    importadores traen cuánto se durmió pero no cuándo, y esas noches cuentan para la
    media de sueño aunque no tengan fase que medir.
    """
    nights = len(sleep_minutes)
    mean_midpoint = sd_midpoint = None
    if midpoints:
        mean, sd = _circular_mean_and_sd(midpoints)
        mean_midpoint = round(mean) % MINUTES_PER_DAY
        sd_midpoint = round(sd)

    return WeekStats(
        nights=nights,
        mean_sleep_minutes=round(sum(sleep_minutes) / nights) if nights else None,
        mean_efficiency=round(sum(efficiencies) / len(efficiencies), 3) if efficiencies else None,
        mean_midpoint_minutes=mean_midpoint,
        sd_midpoint_minutes=sd_midpoint,
    )


def worst_night_factors(
    samples: list[tuple[set[str], int]],
    worst_count: int = WORST_NIGHTS_LOOKED_AT,
) -> list[WeeklyFactor]:
    """Qué señales coincidieron con las noches más cortas de la semana.

    Cada muestra es (factores de ese día, minutos dormidos esa noche). Se comparan las
    `worst_count` noches más cortas contra el resto, y solo sale el factor que estuvo
    en al menos dos de ellas y además fue más frecuente ahí que en las demás.

    Es coincidencia, no causa, y con siete noches ni siquiera es una coincidencia
    fuerte. Sirve para mirar hacia algún sitio, no para concluir nada.
    """
    if len(samples) < MIN_NIGHTS_FOR_WORST_FACTORS:
        return []

    ordered = sorted(samples, key=lambda pair: pair[1])
    worst = ordered[:worst_count]
    rest = ordered[worst_count:]
    if not rest:
        return []

    found: list[WeeklyFactor] = []
    for key, label in FACTOR_LABELS.items():
        in_worst = sum(1 for factors, _ in worst if key in factors)
        if in_worst < MIN_WORST_NIGHTS_WITH_FACTOR:
            continue
        in_rest = sum(1 for factors, _ in rest if key in factors)
        if in_worst / len(worst) <= in_rest / len(rest):
            continue
        found.append(
            WeeklyFactor(
                key=key,
                label=label,
                nights_worst=in_worst,
                of_worst=len(worst),
                nights_rest=in_rest,
                of_rest=len(rest),
            )
        )

    return sorted(
        found,
        key=lambda f: (f.nights_worst / f.of_worst - f.nights_rest / f.of_rest, f.nights_worst),
        reverse=True,
    )


def _duration_text(minutes: int) -> str:
    minutes = abs(minutes)
    if minutes < 60:
        return f"{minutes} min"
    hours, rest = divmod(minutes, 60)
    return f"{hours} h" if not rest else f"{hours} h {rest} min"


def weekly_highlights(
    current: WeekStats,
    previous: WeekStats,
    midpoint_shift_minutes: int | None,
    factors: list[WeeklyFactor],
    window_kept: int,
    window_measured: int,
    debt_delta_minutes: int | None,
) -> list[str]:
    """Las frases del informe, escritas por el motor y no por el modelo.

    Mismo reparto que en el resto de la app: aquí se decide qué se dice y con qué
    número; el LLM, si acaso, lo cuenta con otras palabras. Un resumen semanal escrito
    por el modelo no sería reproducible ni comparable con el de la semana pasada, que
    es justo para lo que sirve un informe.
    """
    if current.nights < MIN_NIGHTS_FOR_WEEK:
        return [
            f"Solo hay {current.nights} "
            f"{'noche medida' if current.nights == 1 else 'noches medidas'} esta semana. "
            f"Con tan pocas, las medias no dicen gran cosa."
        ]

    lines: list[str] = []

    if current.mean_sleep_minutes is not None and previous.mean_sleep_minutes is not None:
        delta = current.mean_sleep_minutes - previous.mean_sleep_minutes
        if abs(delta) >= MEANINGFUL_SLEEP_DELTA_MINUTES:
            lines.append(
                f"Dormiste {_duration_text(delta)} "
                f"{'más' if delta > 0 else 'menos'} por noche que la semana anterior."
            )
        else:
            lines.append("Dormiste prácticamente lo mismo que la semana anterior.")

    if (
        midpoint_shift_minutes is not None
        and abs(midpoint_shift_minutes) >= MEANINGFUL_SHIFT_MINUTES
    ):
        lines.append(
            f"Tu punto medio de sueño se "
            f"{'retrasó' if midpoint_shift_minutes > 0 else 'adelantó'} "
            f"{_duration_text(midpoint_shift_minutes)}."
        )

    if current.sd_midpoint_minutes is not None and previous.sd_midpoint_minutes is not None:
        sd_delta = current.sd_midpoint_minutes - previous.sd_midpoint_minutes
        if abs(sd_delta) >= MEANINGFUL_SD_DELTA_MINUTES:
            lines.append(
                f"Tu horario fue {'más irregular' if sd_delta > 0 else 'más regular'} "
                f"que el de la semana anterior."
            )

    if window_measured:
        lines.append(
            f"Te metiste en la cama dentro de la ventana en {window_kept} de "
            f"{window_measured} {'noche' if window_measured == 1 else 'noches'} con hora medida."
        )

    if factors:
        top = factors[0]
        lines.append(
            f"En tus {top.of_worst} peores noches coincidió {top.label} "
            f"{top.nights_worst} {'vez' if top.nights_worst == 1 else 'veces'}, frente a "
            f"{top.nights_rest} de {top.of_rest} en el resto. Es coincidencia, no causa."
        )

    if debt_delta_minutes is not None and abs(debt_delta_minutes) >= MEANINGFUL_DEBT_DELTA_MINUTES:
        lines.append(
            f"Tu deuda de sueño {'subió' if debt_delta_minutes > 0 else 'bajó'} "
            f"{_duration_text(debt_delta_minutes)} en la semana."
        )

    return lines
