from __future__ import annotations

from datetime import date, time
from typing import Literal

from pydantic import BaseModel


class HeatmapNight(BaseModel):
    night_of: date
    total_sleep_minutes: int
    efficiency: float


class RegularityOut(BaseModel):
    score: int
    sd_minutes: int
    mean_midpoint_minutes: int
    nights: int


class AssociationOut(BaseModel):
    """Una comparación entre las noches con un factor y las noches sin él.

    Es asociación, no causa: son los datos de una sola persona y sin control de nada.
    El frontend lo dice con esas palabras.
    """

    key: str
    label: str
    nights_with: int
    nights_without: int
    mean_sleep_with: int
    mean_sleep_without: int
    mean_efficiency_with: float
    mean_efficiency_without: float
    delta_sleep_minutes: int


class AdherenceNight(BaseModel):
    day: date
    recommended: time
    # Falta cuando el reloj no trajo la hora real de acostarse.
    actual: time | None
    followed: bool | None


class AdherenceOut(BaseModel):
    streak: int
    rate: float | None
    series: list[AdherenceNight]


class InsightsOut(BaseModel):
    # `regularity` va a null cuando faltan noches con horas medidas. El frontend lo
    # dibuja como "faltan datos", nunca como un cero.
    regularity: RegularityOut | None
    # Vacío mientras no haya check-ins suficientes a los dos lados de cada factor.
    associations: list[AssociationOut]
    adherence: AdherenceOut
    heatmap: list[HeatmapNight]


class TipOut(BaseModel):
    id: str
    title: str
    body: str
    category: str
    evidence: Literal["alta", "media", "baja"]
    source: str
    # True cuando el consejo sale por algo que pasa hoy y no por relleno.
    relevant: bool


class TipsOut(BaseModel):
    day: date
    signals: list[str]
    tips: list[TipOut]


class WeekStatsOut(BaseModel):
    """Medias de una semana. Van a `null` cuando faltan noches, nunca a cero."""

    nights: int
    mean_sleep_minutes: int | None
    mean_efficiency: float | None
    # Minutos desde medianoche. Circulares: ver app/domain/insights.py.
    mean_midpoint_minutes: int | None
    sd_midpoint_minutes: int | None


class WeeklyNightOut(BaseModel):
    night_of: date
    total_sleep_minutes: int
    efficiency: float
    midpoint_minutes: int | None
    recommended: time | None
    actual: time | None
    # `null` cuando falta la recomendación de ese día o la hora real de acostarse. No
    # es lo mismo que no haberla cumplido, y el frontend lo pinta como hueco.
    in_window: bool | None
    followed: bool | None


class WeeklyFactorOut(BaseModel):
    """Qué coincidió con las peores noches. Coincidencia, no causa: con siete noches
    no hay estadística, y por eso viajan los recuentos de los dos lados."""

    key: str
    label: str
    nights_worst: int
    of_worst: int
    nights_rest: int
    of_rest: int


class WeeklyOut(BaseModel):
    start: date
    end: date
    offset: int

    current: WeekStatsOut
    previous: WeekStatsOut
    sleep_delta_minutes: int | None
    efficiency_delta: float | None
    # Positivo es acostarse más tarde. Diferencia circular, no resta.
    midpoint_shift_minutes: int | None
    # Diferencia de dispersión del punto medio: negativo es más regular.
    regularity_delta_minutes: int | None

    debt_minutes: int
    debt_delta_minutes: int | None

    nights: list[WeeklyNightOut]
    best_night: date | None
    worst_night: date | None

    window_kept: int
    window_measured: int
    followed: int
    answered: int
    recommended: int

    worst_night_factors: list[WeeklyFactorOut]
    # Las frases ya escritas por el motor. El LLM no participa: un resumen distinto
    # cada vez no se puede comparar con el de la semana pasada.
    highlights: list[str]
