from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditEvent(Base):
    """Qué ha registrado cada persona y cuándo.

    Es un diario de acciones, no una copia de los datos: guarda el tipo de evento y un
    resumen corto, nunca el contenido del check-in ni la transcripción. El panel de
    `/dev` sirve para ver que la app se está usando y para depurar cuando algo no
    cuadra, no para leer lo que la gente escribe.

    Sin borrado automático: son pocas filas y el proyecto es de dos personas. Si algún
    día crece, lo que toca es purgar por antigüedad, no dejar de escribirlas.
    """

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    # "checkin", "nights", "import", "recommendation", "followed", "profile", "login"
    action: Mapped[str] = mapped_column(String(32), index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
