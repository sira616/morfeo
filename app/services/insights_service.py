"""Une el histórico de la base de datos con las métricas puras de `app.domain.insights`."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.domain import insights
from app.models.sleep import BedtimeRecommendation, SleepNight
from app.models.user import User
from app.services import sleep_service

# Ocho semanas: suficiente para que se vea un patrón en la cuadrícula sin que la
# pantalla se convierta en un año de píxeles diminutos.
HEATMAP_DAYS = 56


def _midpoints(nights: list[SleepNight]) -> list[tuple[date, int]]:
    """Solo las noches con horas reales. Sin `sleep_start` no hay fase que medir.

    Muchos importadores traen únicamente duración y tiempo en cama, así que esta lista
    puede quedarse corta aunque haya muchas noches: quien llama debe tratar el vacío
    como "faltan datos", no como "horario irregular".
    """
    return [
        (n.night_of, insights.midpoint_minutes(n.sleep_start, n.sleep_end))
        for n in nights
        if n.sleep_start is not None and n.sleep_end is not None
    ]


def heatmap(db: DbSession, user: User, today: date) -> list[dict]:
    nights = sleep_service.recent_nights(db, user, HEATMAP_DAYS, today)
    return [
        {
            "night_of": n.night_of,
            "total_sleep_minutes": n.total_sleep_minutes,
            "efficiency": round(n.efficiency, 3),
        }
        for n in nights
    ]


def regularity(db: DbSession, user: User, today: date) -> insights.Regularity | None:
    nights = sleep_service.recent_nights(db, user, HEATMAP_DAYS, today)
    return insights.regularity([m for _, m in _midpoints(nights)])


def social_jetlag(db: DbSession, user: User, today: date) -> insights.SocialJetlag | None:
    nights = sleep_service.recent_nights(db, user, HEATMAP_DAYS, today)
    return insights.social_jetlag(_midpoints(nights))


def _recommendations(db: DbSession, user: User, today: date) -> list[BedtimeRecommendation]:
    since = today - timedelta(days=HEATMAP_DAYS)
    return list(
        db.scalars(
            select(BedtimeRecommendation)
            .where(
                BedtimeRecommendation.user_id == user.id,
                BedtimeRecommendation.day > since,
            )
            .order_by(BedtimeRecommendation.day)
        )
    )


def adherence(db: DbSession, user: User, today: date) -> dict:
    rows = _recommendations(db, user, today)
    followed = [(r.day, r.followed) for r in rows]

    nights = {n.night_of: n for n in sleep_service.recent_nights(db, user, HEATMAP_DAYS, today)}
    series = []
    for row in rows:
        night = nights.get(row.day)
        series.append(
            {
                "day": row.day,
                "recommended": row.bedtime,
                # La hora real de acostarse solo existe si el reloj la trajo; si no, la
                # comparación se queda a medias y el frontend lo dibuja como hueco.
                "actual": night.bed_at.time() if night and night.bed_at else None,
                "followed": row.followed,
            }
        )

    return {
        "streak": insights.current_streak(followed),
        "rate": insights.adherence_rate(followed),
        "series": series,
    }
