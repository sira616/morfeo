"""Adaptador de Oura (API v2).

Es el proveedor con menos fricción para un proyecto en solitario: se autentica con un
Personal Access Token que se saca del panel de Oura en un minuto, sin OAuth, sin
registrar una aplicación y sin aprobación de nadie. Si tienes anillo Oura, empieza
por aquí.

Documentación: https://cloud.ouraring.com/v2/docs
"""
from __future__ import annotations

from datetime import date, datetime

import httpx

from app.wearables.base import DaySample, NightSample, classify_intensity

BASE_URL = "https://api.ouraring.com/v2/usercollection"
TIMEOUT_SECONDS = 20


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    # Oura devuelve ISO-8601 con offset; se guarda como naive local para que las
    # comparaciones con las horas declaradas por el usuario no mezclen zonas.
    return datetime.fromisoformat(value).replace(tzinfo=None)


class OuraProvider:
    name = "oura"

    def __init__(self, access_token: str, client: httpx.Client | None = None) -> None:
        self._token = access_token
        self._client = client

    def _get(self, path: str, since: date, until: date) -> list[dict]:
        params = {"start_date": since.isoformat(), "end_date": until.isoformat()}
        headers = {"Authorization": f"Bearer {self._token}"}
        client = self._client or httpx.Client(timeout=TIMEOUT_SECONDS)
        try:
            response = client.get(f"{BASE_URL}/{path}", params=params, headers=headers)
            response.raise_for_status()
            return response.json().get("data", [])
        finally:
            if self._client is None:
                client.close()

    def fetch_nights(self, since: date, until: date) -> list[NightSample]:
        nights: list[NightSample] = []
        for row in self._get("sleep", since, until):
            # Oura reparte varios registros por día (siestas incluidas): solo el
            # periodo largo cuenta como noche.
            if row.get("type") not in (None, "long_sleep", "sleep"):
                continue
            total = int(row.get("total_sleep_duration") or 0) // 60
            in_bed = int(row.get("time_in_bed") or 0) // 60
            if total == 0 or in_bed == 0:
                continue
            start = _parse_dt(row.get("bedtime_start"))
            nights.append(
                NightSample(
                    # `day` en Oura es el día del despertar; la app agrupa por el de
                    # acostarse, así que manda `bedtime_start`.
                    night_of=start.date() if start else date.fromisoformat(row["day"]),
                    total_sleep_minutes=total,
                    time_in_bed_minutes=in_bed,
                    bed_at=start,
                    sleep_start=start,
                    sleep_end=_parse_dt(row.get("bedtime_end")),
                    onset_latency_minutes=int(row.get("latency") or 0) // 60 or None,
                    deep_minutes=int(row.get("deep_sleep_duration") or 0) // 60 or None,
                    rem_minutes=int(row.get("rem_sleep_duration") or 0) // 60 or None,
                    light_minutes=int(row.get("light_sleep_duration") or 0) // 60 or None,
                    resting_hr=row.get("lowest_heart_rate"),
                    hrv_ms=row.get("average_hrv"),
                )
            )
        return nights

    def fetch_days(self, since: date, until: date) -> list[DaySample]:
        activity = {row["day"]: row for row in self._get("daily_activity", since, until)}
        stress = {row["day"]: row for row in self._get("daily_stress", since, until)}

        days: list[DaySample] = []
        for day_str, row in activity.items():
            minutes, intensity = classify_intensity(
                hard_minutes=int(row.get("high_activity_time") or 0) // 60,
                moderate_minutes=int(row.get("medium_activity_time") or 0) // 60,
                light_minutes=int(row.get("low_activity_time") or 0) // 60,
            )
            days.append(
                DaySample(
                    day=date.fromisoformat(day_str),
                    steps=row.get("steps"),
                    exercise_minutes=minutes,
                    exercise_intensity=intensity,
                    stress_avg=_stress_score(stress.get(day_str)),
                    resting_hr=row.get("resting_heart_rate"),
                )
            )
        return sorted(days, key=lambda d: d.day)


def _stress_score(row: dict | None) -> int | None:
    """Oura da segundos en estrés alto y en recuperación, no un índice.

    Se convierte a la escala 0-100 de la app como la proporción del tiempo medido que
    se pasó en estrés alto. Es una aproximación: queda documentada aquí para que no
    parezca un dato del fabricante.
    """
    if not row:
        return None
    high = int(row.get("stress_high") or 0)
    recovery = int(row.get("recovery_high") or 0)
    total = high + recovery
    if total == 0:
        return None
    return round(100 * high / total)
