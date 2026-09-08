"""Métricas del histórico y consejos del día."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.insights import (
    AdherenceOut,
    InsightsOut,
    RegularityOut,
    SocialJetlagOut,
    TipOut,
    TipsOut,
)
from app.services import insights_service, tips_service

router = APIRouter(prefix="/api", tags=["insights"])


@router.get("/insights", response_model=InsightsOut)
def get_insights(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    reg = insights_service.regularity(db, user, today)
    jetlag = insights_service.social_jetlag(db, user, today)

    return InsightsOut(
        regularity=RegularityOut(**reg.__dict__) if reg else None,
        social_jetlag=SocialJetlagOut(**jetlag.__dict__) if jetlag else None,
        adherence=AdherenceOut(**insights_service.adherence(db, user, today)),
        heatmap=insights_service.heatmap(db, user, today),
    )


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
