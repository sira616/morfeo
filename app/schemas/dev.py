from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ActivityCount(BaseModel):
    action: str
    count: int
    last: datetime | None


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
    created_at: datetime | None
    wearable_provider: str | None
    nights: int
    checkins: int
    recommendations: int
    last_night: date | None
    last_seen: datetime | None


class DevEventOut(BaseModel):
    at: datetime
    action: str
    summary: str | None


class DevUserDetailOut(BaseModel):
    user: DevUserOut
    activity: list[ActivityCount]
    events: list[DevEventOut]
