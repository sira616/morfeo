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


class SocialJetlagOut(BaseModel):
    minutes: int
    weekday_midpoint_minutes: int
    weekend_midpoint_minutes: int
    weekday_nights: int
    weekend_nights: int


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
    # `regularity` y `social_jetlag` van a null cuando faltan noches con horas medidas.
    # El frontend lo dibuja como "faltan datos", nunca como un cero.
    regularity: RegularityOut | None
    social_jetlag: SocialJetlagOut | None
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
