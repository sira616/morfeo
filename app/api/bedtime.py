"""La recomendación: lo que la app existe para dar."""
from __future__ import annotations

import json
from datetime import date, time

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sleep import BedtimeRecommendation
from app.models.user import User
from app.schemas.sleep import (
    FactorOut,
    FollowedIn,
    RecommendationOut,
    SimulationIn,
    SleepDebtOut,
)
from app.services import audit_service, sleep_service

router = APIRouter(prefix="/api/bedtime", tags=["bedtime"])


def _to_out(
    day: date,
    wake_target: time,
    rec,
    source: str,
    followed: bool | None = None,
    sleep_debt: SleepDebtOut | None = None,
) -> RecommendationOut:
    return RecommendationOut(
        day=day,
        wake_target=wake_target,
        wake_target_source=source,
        bedtime=rec.bedtime,
        window_start=rec.window_start,
        window_end=rec.window_end,
        target_sleep_minutes=rec.target_sleep_minutes,
        sleep_window_minutes=rec.sleep_window_minutes,
        time_in_bed_minutes=rec.time_in_bed_minutes,
        onset_latency_minutes=rec.onset_latency_minutes,
        mode=rec.mode,
        confidence=rec.confidence,
        factors=[FactorOut(**f.__dict__) for f in rec.factors],
        notes=rec.notes,
        followed=followed,
        sleep_debt=sleep_debt,
    )


def _debt(db: Session, user: User, day: date) -> SleepDebtOut:
    """La deuda acumulada, con el plazo para saldarla y la tendencia.

    Viaja dentro de la recomendación en lugar de en su propia ruta porque es parte
    de por qué hoy la hora sale más temprana que ayer: separarlas dejaría la
    portada enseñando el número sin lo que lo explica.
    """
    detail, previous = sleep_service.debt_detail(db, user, day)
    return SleepDebtOut(
        **detail.__dict__,
        previous_minutes=previous,
        delta_minutes=detail.minutes - previous if previous is not None else None,
    )


@router.get("/tonight", response_model=RecommendationOut)
def tonight(
    simulation: Annotated[SimulationIn, Query()],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Hora recomendada para acostarse esta noche.

    Sin parámetros devuelve la del día y **la guarda**. Con cualquier parámetro puesto
    responde a un «¿y si...?» —otra hora de despertar, menos cafés, sin siesta— y
    entonces no guarda nada.

    Esa condición es lo único delicado de esta ruta: si una simulación se guardara, el
    histórico acabaría lleno de noches que nadie vivió y dejaría de servir para lo
    único que existe, que es comprobar después si el motor acertaba.
    """
    today = date.today()
    resolved, source = sleep_service.resolve_wake_target(
        db, user, today, simulation.wake_target
    )
    rec = sleep_service.compute(db, user, today, resolved, simulation)

    if not simulation.active:
        sleep_service.store(db, user, today, resolved, rec)
    return _to_out(today, resolved, rec, source, sleep_debt=_debt(db, user, today))


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
            sleep_window_minutes=r.sleep_window_minutes,
            time_in_bed_minutes=r.sleep_window_minutes + r.onset_latency_minutes,
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
