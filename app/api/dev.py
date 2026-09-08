"""Panel de administración: quién se ha registrado y qué registra.

Toda la sección va detrás de `require_admin`, que responde **404** a quien no lo es.
Un 403 confirmaría que la ruta existe y que hay algo detrás.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.audit import AuditEvent
from app.models.sleep import BedtimeRecommendation, Checkin, SleepNight
from app.models.user import User
from app.schemas.dev import ActivityCount, DevEventOut, DevUserDetailOut, DevUserOut
from app.services import audit_service

router = APIRouter(prefix="/api/dev", tags=["dev"])


def _counts(db: Session, model, user_ids: list[str]) -> dict[str, int]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(model.user_id, func.count())
        .where(model.user_id.in_(user_ids))
        .group_by(model.user_id)
    ).all()
    return {user_id: count for user_id, count in rows}


def _to_out(user: User, nights: int, checkins: int, recs: int, last_night, last_seen) -> DevUserOut:
    return DevUserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
        onboarding_done=user.onboarding_done,
        created_at=user.created_at,
        wearable_provider=user.wearable_provider,
        nights=nights,
        checkins=checkins,
        recommendations=recs,
        last_night=last_night,
        last_seen=last_seen,
    )


@router.get("/users", response_model=list[DevUserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    users = list(db.scalars(select(User).order_by(User.created_at.desc())))
    ids = [u.id for u in users]

    nights = _counts(db, SleepNight, ids)
    checkins = _counts(db, Checkin, ids)
    recs = _counts(db, BedtimeRecommendation, ids)

    last_nights = dict(
        db.execute(
            select(SleepNight.user_id, func.max(SleepNight.night_of))
            .where(SleepNight.user_id.in_(ids))
            .group_by(SleepNight.user_id)
        ).all()
    ) if ids else {}
    last_seen = dict(
        db.execute(
            select(AuditEvent.user_id, func.max(AuditEvent.at))
            .where(AuditEvent.user_id.in_(ids))
            .group_by(AuditEvent.user_id)
        ).all()
    ) if ids else {}

    return [
        _to_out(
            u,
            nights.get(u.id, 0),
            checkins.get(u.id, 0),
            recs.get(u.id, 0),
            last_nights.get(u.id),
            last_seen.get(u.id),
        )
        for u in users
    ]


@router.get("/users/{user_id}", response_model=DevUserDetailOut)
def user_detail(
    user_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")

    nights = db.scalar(select(func.count()).select_from(SleepNight).where(SleepNight.user_id == user_id)) or 0
    checkins = db.scalar(select(func.count()).select_from(Checkin).where(Checkin.user_id == user_id)) or 0
    recs = db.scalar(
        select(func.count()).select_from(BedtimeRecommendation).where(BedtimeRecommendation.user_id == user_id)
    ) or 0
    last_night = db.scalar(select(func.max(SleepNight.night_of)).where(SleepNight.user_id == user_id))
    last_seen = db.scalar(select(func.max(AuditEvent.at)).where(AuditEvent.user_id == user_id))

    summary = audit_service.activity_summary(db, user_id)
    events = audit_service.events_for(db, user_id, limit=limit)

    return DevUserDetailOut(
        user=_to_out(user, nights, checkins, recs, last_night, last_seen),
        activity=[
            ActivityCount(action=action, count=data["count"], last=data["last"])
            for action, data in sorted(summary.items())
        ],
        events=[DevEventOut(at=e.at, action=e.action, summary=e.summary) for e in events],
    )
