"""Registro de actividad.

Guarda **qué** hizo cada persona, nunca **qué escribió**: el tipo de acción y un
resumen corto. El panel de `/dev` existe para ver que la app se usa y para depurar,
no para leer los check-ins de nadie.

Escribir aquí no debe poder tumbar una petición: si el registro falla, la acción del
usuario ya se ha hecho y perderla sería peor que perder la línea de log.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.models.audit import AuditEvent
from app.models.user import User

MAX_SUMMARY_CHARS = 200


def record(db: DbSession, user: User, action: str, summary: str | None = None) -> None:
    try:
        db.add(
            AuditEvent(
                user_id=user.id,
                action=action,
                summary=(summary or "")[:MAX_SUMMARY_CHARS] or None,
            )
        )
        db.commit()
    except Exception:
        db.rollback()


def events_for(db: DbSession, user_id: str, limit: int = 100) -> list[AuditEvent]:
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.user_id == user_id)
            .order_by(AuditEvent.at.desc())
            .limit(limit)
        )
    )


def activity_summary(db: DbSession, user_id: str, days: int = 30) -> dict:
    """Cuántas acciones de cada tipo y cuándo fue la última."""
    since = date.today() - timedelta(days=days)
    rows = db.execute(
        select(AuditEvent.action, func.count(), func.max(AuditEvent.at))
        .where(AuditEvent.user_id == user_id, AuditEvent.at >= since)
        .group_by(AuditEvent.action)
    ).all()
    return {action: {"count": count, "last": last} for action, count, last in rows}
