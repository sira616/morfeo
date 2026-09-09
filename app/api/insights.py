"""Métricas del histórico y consejos del día."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.insights import (
    AdherenceOut,
    AssociationOut,
    InsightsOut,
    RegularityOut,
    TipOut,
    TipsOut,
    WeeklyOut,
)
from app.services import insights_service, tips_service

router = APIRouter(prefix="/api", tags=["insights"])


@router.get("/insights", response_model=InsightsOut)
def get_insights(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    reg = insights_service.regularity(db, user, today)

    return InsightsOut(
        regularity=RegularityOut(**reg.__dict__) if reg else None,
        associations=[
            AssociationOut(**a.__dict__, delta_sleep_minutes=a.delta_sleep_minutes)
            for a in insights_service.associations(db, user, today)
        ],
        adherence=AdherenceOut(**insights_service.adherence(db, user, today)),
        heatmap=insights_service.heatmap(db, user, today),
    )


@router.get("/insights/weekly", response_model=WeeklyOut)
def get_weekly(
    offset: int = Query(default=0, ge=0, le=52),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """El informe de las últimas siete noches, disponible cualquier día.

    `offset` retrocede semanas enteras. La ventana es móvil y no la semana del
    calendario a propósito: un resumen que solo cuadra los domingos hay que
    acordarse de abrirlo el domingo, y entonces no lo abre nadie.
    """
    return WeeklyOut(**insights_service.weekly(db, user, date.today(), offset))


@router.get("/tips/today", response_model=TipsOut)
def get_tips(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Cinco consejos, con su nivel de evidencia.

    No es una lista aleatoria de tópicos: prioriza lo que hoy le viene a cuento a esta
    persona y es estable durante el día, para que se puedan leer en vez de hojear.
    """
    today = date.today()
    tips, signals = tips_service.tips_for(db, user, today)
    return TipsOut(
        day=today,
        signals=sorted(signals),
        tips=[
            TipOut(
                **{k: v for k, v in tip.__dict__.items() if k != "applies_when"},
                relevant=bool(tip.applies_when and tip.applies_when in signals),
            )
            for tip in tips
        ],
    )
