"""La recomendación: lo que la app existe para dar."""
from __future__ import annotations

import json
from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sleep import BedtimeRecommendation
from app.models.user import User
from app.schemas.sleep import FactorOut, FollowedIn, RecommendationOut
from app.services import audit_service, sleep_service

router = APIRouter(prefix="/api/bedtime", tags=["bedtime"])


def _to_out(day: date, wake_target: time, rec, followed: bool | None = None) -> RecommendationOut:
    return RecommendationOut(
        day=day,
        wake_target=wake_target,
        bedtime=rec.bedtime,
        window_start=rec.window_start,
        window_end=rec.window_end,
        target_sleep_minutes=rec.target_sleep_minutes,
        time_in_bed_minutes=rec.time_in_bed_minutes,
        onset_latency_minutes=rec.onset_latency_minutes,
        mode=rec.mode,
        confidence=rec.confidence,
        factors=[FactorOut(**f.__dict__) for f in rec.factors],
        notes=rec.notes,
        followed=followed,
    )


@router.get("/tonight", response_model=RecommendationOut)
def tonight(
    wake_target: time | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Hora recomendada para acostarse esta noche.

    `wake_target` permite simular ("¿y si mañana madrugo a las 6?") sin tocar el perfil.
    La simulación no se guarda; solo la recomendación del día con la hora real.
    """
    today = date.today()
    resolved = sleep_service.resolve_wake_target(db, user, today, wake_target)
    rec = sleep_service.compute(db, user, today, resolved)

    if wake_target is None:
        sleep_service.store(db, user, today, resolved, rec)
    return _to_out(today, resolved, rec)


@router.get("/history", response_model=list[RecommendationOut])
def history(
    limit: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.scalars(
        select(BedtimeRecommendation)
        .where(BedtimeRecommendation.user_id == user.id)
        .order_by(BedtimeRecommendation.day.desc())
        .limit(limit)
    )
    return [
        RecommendationOut(
            day=r.day,
            wake_target=r.wake_target,
            bedtime=r.bedtime,
            window_start=r.window_start,
            window_end=r.window_end,
            target_sleep_minutes=r.target_sleep_minutes,
            time_in_bed_minutes=r.time_in_bed_minutes,
            onset_latency_minutes=r.onset_latency_minutes,
            mode=r.mode,
            confidence=r.confidence,
            factors=[FactorOut(**f) for f in json.loads(r.factors)],
            notes=json.loads(r.notes),
            followed=r.followed,
        )
        for r in rows
    ]


@router.patch("/{day}/followed", status_code=status.HTTP_204_NO_CONTENT)
def mark_followed(
    day: date,
    payload: FollowedIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Marca si se siguió la recomendación.

    Es el cierre del bucle: cruzando esto con la noche que vino después se puede
    medir si el motor acierta, en vez de suponerlo.
    """
    row = db.scalar(
        select(BedtimeRecommendation).where(
            BedtimeRecommendation.user_id == user.id, BedtimeRecommendation.day == day
        )
    )
    # 404 y no 403 cuando la fila es de otro usuario: no se confirma ni que exista.
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sin recomendación ese día")
    row.followed = payload.followed
    db.commit()
    audit_service.record(db, user, "followed", f"{day}: {'sí' if payload.followed else 'no'}")
