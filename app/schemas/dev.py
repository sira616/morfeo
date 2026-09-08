from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated

from pydantic import BaseModel, PlainSerializer


def _as_utc(value: datetime | None) -> str | None:
    """Marca como UTC lo que la base de datos guarda sin zona.

    SQLite almacena `func.now()` en UTC y sin `tzinfo`, así que al serializarlo salía
    un ISO sin zona; el navegador lo interpretaba como hora **local** y el panel
    enseñaba todo con dos horas de retraso en España. Poner la Z deja que cada cliente
    lo convierta a su hora.
    """
    if value is None:
        return None
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return aware.isoformat()


# Fechas sin hora (`date`) no llevan zona y no sufren este problema.
UtcDatetime = Annotated[datetime, PlainSerializer(_as_utc, return_type=str)]


class ActivityCount(BaseModel):
    action: str
    count: int
    last: UtcDatetime | None


class DevUserOut(BaseModel):
    """Perfil visto desde el panel.

    A propósito **sin** contenido de check-ins ni transcripciones: solo cuántas cosas
    registró y cuándo. El panel sirve para ver que la app se usa, no para leer lo que
    la gente escribe.
    """

    id: str
    username: str
    email: str | None
    display_name: str | None
    is_admin: bool
    onboarding_done: bool
    created_at: UtcDatetime | None
    wearable_provider: str | None
    nights: int
    checkins: int
    recommendations: int
    last_night: date | None
    last_seen: UtcDatetime | None


class DevEventOut(BaseModel):
    at: UtcDatetime
    action: str
    summary: str | None


class DevUserDetailOut(BaseModel):
    user: DevUserOut
    activity: list[ActivityCount]
    events: list[DevEventOut]
