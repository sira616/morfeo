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


@dataclass(frozen=True)
class SocialJetlag:
    minutes: int
    weekday_midpoint_minutes: int
    weekend_midpoint_minutes: int
    weekday_nights: int
    weekend_nights: int


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


def circular_distance(a: float, b: float) -> float:
    """Distancia más corta entre dos horas del día, en minutos (0 a 720)."""
    raw = abs(a - b) % MINUTES_PER_DAY
    return min(raw, MINUTES_PER_DAY - raw)


def social_jetlag(midpoints_by_day: list[tuple[date, int]]) -> SocialJetlag | None:
    """Desfase entre el horario de diario y el del fin de semana.

    Es la diferencia entre los puntos medios de sueño de unos días y otros: dormir de
    viernes a domingo con dos horas de retraso equivale a cruzar dos husos horarios
    cada semana, de ahí el nombre.

    Se agrupa por la noche en que uno se acuesta: viernes y sábado cuentan como fin de
    semana, porque es cuando se trasnocha, no cuando se madruga.
    """
    weekday = [m for day, m in midpoints_by_day if day.weekday() < 4 or day.weekday() == 6]
    weekend = [m for day, m in midpoints_by_day if day.weekday() in (4, 5)]
    if len(weekday) < 3 or len(weekend) < 2:
        return None

    weekday_mean, _ = _circular_mean_and_sd(weekday)
    weekend_mean, _ = _circular_mean_and_sd(weekend)
    return SocialJetlag(
        minutes=round(circular_distance(weekday_mean, weekend_mean)),
        weekday_midpoint_minutes=round(weekday_mean) % MINUTES_PER_DAY,
        weekend_midpoint_minutes=round(weekend_mean) % MINUTES_PER_DAY,
        weekday_nights=len(weekday),
        weekend_nights=len(weekend),
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
