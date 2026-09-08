"""Contrato común de los relojes.

Todo lo que entra de un wearable pasa por aquí antes de tocar la base de datos. El
motor de `app.domain.bedtime` no sabe si los datos vienen de un Oura, de un Garmin o
de un CSV pegado a mano, y eso es deliberado: cambiar de reloj no debe obligar a
tocar el cálculo.

Dos decisiones de normalización que conviene tener presentes:

- **El estrés siempre es 0-100, más alto peor.** El Body Battery de Garmin va al
  revés (100 es estar fresco) y se invierte en su adaptador, no aquí.
- **`night_of` es la fecha en que uno se acuesta**, no la del despertar. Cada API lo
  cuenta a su manera y cada adaptador tiene que traducir.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class NightSample:
    night_of: date
    total_sleep_minutes: int
    time_in_bed_minutes: int
    bed_at: datetime | None = None
    sleep_start: datetime | None = None
    sleep_end: datetime | None = None
    out_of_bed_at: datetime | None = None
    onset_latency_minutes: int | None = None
    awakenings: int | None = None
    deep_minutes: int | None = None
    rem_minutes: int | None = None
    light_minutes: int | None = None
    resting_hr: int | None = None
    hrv_ms: float | None = None


@dataclass(frozen=True)
class DaySample:
    day: date
    steps: int | None = None
    exercise_minutes: int = 0
    exercise_intensity: str = "none"  # none | light | moderate | hard
    exercise_end: time | None = None
    stress_avg: int | None = None  # 0-100, más alto = más estrés
    resting_hr: int | None = None
    hrv_ms: float | None = None


@runtime_checkable
class WearableProvider(Protocol):
    """Un reloj o una fuente de datos de sueño.

    Los proveedores son de solo lectura: la app nunca escribe en el reloj.
    """

    name: str

    def fetch_nights(self, since: date, until: date) -> list[NightSample]: ...

    def fetch_days(self, since: date, until: date) -> list[DaySample]: ...


def classify_intensity(
    hard_minutes: int = 0, moderate_minutes: int = 0, light_minutes: int = 0
) -> tuple[int, str]:
    """Reduce los minutos por zona a (minutos, intensidad) para el motor.

    Se queda con la zona más alta que tenga volumen suficiente: veinte minutos de
    serie fuerte pesan más en el sueño de esta noche que dos horas de paseo.
    """
    if hard_minutes >= 20:
        return hard_minutes + moderate_minutes, "hard"
    if moderate_minutes >= 20:
        return moderate_minutes + light_minutes, "moderate"
    if light_minutes > 0:
        return light_minutes, "light"
    return 0, "none"
