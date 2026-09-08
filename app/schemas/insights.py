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
