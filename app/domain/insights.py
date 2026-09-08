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
