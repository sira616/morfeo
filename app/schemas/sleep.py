from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Topes de entrada. No son paranoia: sin ellos una sola petición puede llenar la base
# de datos o disparar el coste de tokens del check-in.
MAX_IMPORT_CHARS = 2_000_000  # ~5000 noches en JSON
MAX_TRANSCRIPT_CHARS = 4000
MAX_NIGHTS_PER_REQUEST = 400

# 24 h en minutos: cualquier noche por encima es un error de unidades (segundos
# metidos donde van minutos), no una noche real.
MAX_MINUTES = 1440

Intensity = Literal["none", "light", "moderate", "hard"]


class NightIn(BaseModel):
    night_of: date
    total_sleep_minutes: int = Field(ge=0, le=MAX_MINUTES)
    time_in_bed_minutes: int = Field(ge=0, le=MAX_MINUTES)
    onset_latency_minutes: int | None = Field(default=None, ge=0, le=600)
    awakenings: int | None = Field(default=None, ge=0, le=100)
    bed_at: datetime | None = None
    sleep_start: datetime | None = None
    sleep_end: datetime | None = None
    deep_minutes: int | None = Field(default=None, ge=0, le=MAX_MINUTES)
    rem_minutes: int | None = Field(default=None, ge=0, le=MAX_MINUTES)
    light_minutes: int | None = Field(default=None, ge=0, le=MAX_MINUTES)
    resting_hr: int | None = Field(default=None, ge=20, le=220)
    hrv_ms: float | None = Field(default=None, ge=0, le=500)
    source: str = Field(default="manual", max_length=32)

    @model_validator(mode="after")
    def _sleep_fits_in_bed(self) -> NightIn:
        if self.total_sleep_minutes > self.time_in_bed_minutes:
            raise ValueError(
                "total_sleep_minutes no puede superar time_in_bed_minutes: no se puede "
                "dormir más tiempo del que se pasa en la cama"
            )
        return self


class NightOut(NightIn):
    efficiency: float


class NightsIn(BaseModel):
    nights: list[NightIn] = Field(min_length=1, max_length=MAX_NIGHTS_PER_REQUEST)


class ImportIn(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_IMPORT_CHARS)
    format: Literal["json", "csv"] = "json"


class DailyMetricsIn(BaseModel):
    day: date
    steps: int | None = Field(default=None, ge=0, le=200_000)
    exercise_minutes: int = Field(default=0, ge=0, le=MAX_MINUTES)
    exercise_intensity: Intensity = "none"
    exercise_end: time | None = None
    stress_avg: int | None = Field(default=None, ge=0, le=100)
    resting_hr: int | None = Field(default=None, ge=20, le=220)
    hrv_ms: float | None = Field(default=None, ge=0, le=500)
    source: str = Field(default="manual", max_length=32)


class CheckinIn(BaseModel):
    """Los campos que el reloj no puede medir. Llegan del formulario o del extractor
    del LLM; el motor no distingue el origen.

    Los rangos son topes de cordura, no juicios: 40 cafés o 20 h de siesta son un dedo
    resbalado o un cliente roto, y dejarlos entrar estropea las medias del histórico.
    """

    day: date | None = None
    mood: int | None = Field(default=None, ge=1, le=5)
    energy: int | None = Field(default=None, ge=1, le=5)
    perceived_stress: int | None = Field(default=None, ge=1, le=5)
    nap_minutes: int = Field(default=0, ge=0, le=300)
    last_caffeine: time | None = None
    alcohol: bool = False
    wake_target: time | None = None

    coffees: int = Field(default=0, ge=0, le=20)
    alcohol_units: int = Field(default=0, ge=0, le=30)
    # Días desde el último porro. 0 = hoy. Por encima de un mes deja de importar.
    cannabis_days_ago: int | None = Field(default=None, ge=0, le=365)

    exercise_minutes: int = Field(default=0, ge=0, le=MAX_MINUTES)
    exercise_intensity: Intensity = "none"
    exercise_end: time | None = None

    meals: int | None = Field(default=None, ge=0, le=12)
    last_meal: time | None = None

    notes: str | None = Field(default=None, max_length=1000)
    transcript: str | None = Field(default=None, max_length=MAX_TRANSCRIPT_CHARS)


class FactorOut(BaseModel):
    label: str
    minutes: int
    detail: str


class RecommendationOut(BaseModel):
    day: date
    wake_target: time
    # "perfil" | "checkin" | "simulacion": de dónde sale la hora de despertar. Sin
    # esto, cambiarla en el perfil y que no pasara nada parecía un fallo.
    wake_target_source: Literal["perfil", "checkin", "simulacion"] = "perfil"
    bedtime: time
    window_start: time
    window_end: time
    target_sleep_minutes: int
    # Desde que te duermes hasta que suena el despertador.
    sleep_window_minutes: int
    # Lo que de verdad pasas en la cama: lo anterior más la conciliación.
    time_in_bed_minutes: int
    onset_latency_minutes: int
    mode: Literal["normal", "restriccion"]
    confidence: Literal["baja", "media", "alta"]
    factors: list[FactorOut]
    notes: list[str]
    followed: bool | None = None


class FollowedIn(BaseModel):
    followed: bool


class CheckinOut(BaseModel):
    """Un check-in ya guardado, para pintar la racha reciente de ánimo.

    Deliberadamente **sin** `notes` ni `transcript`: esta ruta alimenta un resumen de
    la portada, y lo que alguien escribió no pinta nada ahí.
    """

    day: date
    mood: int | None
    energy: int | None
    nap_minutes: int
    coffees: int
    alcohol_units: int
    cannabis_days_ago: int | None
