"""Une el histórico de la base de datos con las métricas puras de `app.domain.insights`."""
from __future__ import annotations

from collections.abc import Callable
from datetime import date, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.domain import insights
from app.models.sleep import BedtimeRecommendation, Checkin, DailyMetrics, SleepNight
from app.models.user import User
from app.services import sleep_service

# Ocho semanas: suficiente para que se vea un patrón en la cuadrícula sin que la
# pantalla se convierta en un año de píxeles diminutos.
HEATMAP_DAYS = 56

# Las asociaciones necesitan más noches que el heatmap para que las comparaciones
# tengan algo detrás.
ASSOCIATION_WINDOW_DAYS = 90


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


FACTOR_RULES: dict[str, Callable[[Checkin, DailyMetrics | None], bool]] = {
    "cafe_tarde": lambda c, _: c.last_caffeine is not None and c.last_caffeine >= time(16, 0),
    "muchos_cafes": lambda c, _: c.coffees >= 3,
    "alcohol": lambda c, _: bool(c.alcohol or c.alcohol_units),
    "cannabis": lambda c, _: c.cannabis_days_ago == 0,
    "ejercicio": lambda c, m: max(c.exercise_minutes, m.exercise_minutes if m else 0) >= 30,
    "siesta": lambda c, _: c.nap_minutes >= 20,
    "cena_tarde": lambda c, _: c.last_meal is not None and c.last_meal >= time(22, 0),
    "animo_bajo": lambda c, _: c.mood is not None and c.mood <= 2,
}


def associations(db: DbSession, user: User, today: date) -> list[insights.FactorAssociation]:
    """Qué acompaña a las buenas y a las malas noches de esta persona.

    Empareja el check-in del día D con la noche del día D: `night_of` es la fecha en
    que uno se acuesta, así que el café de esa tarde y esa noche son el mismo día.
    """
    nights = sleep_service.recent_nights(db, user, ASSOCIATION_WINDOW_DAYS, today)
    if not nights:
        return []

    days = [n.night_of for n in nights]
    checkins = {
        c.day: c
        for c in db.scalars(
            select(Checkin).where(Checkin.user_id == user.id, Checkin.day.in_(days))
        )
    }
    metrics = {
        m.day: m
        for m in db.scalars(
            select(DailyMetrics).where(DailyMetrics.user_id == user.id, DailyMetrics.day.in_(days))
        )
    }

    samples: list[tuple[set[str], int, float]] = []
    for night in nights:
        checkin = checkins.get(night.night_of)
        if checkin is None:
            # Sin check-in no se sabe qué pasó ese día; contarla como "sin el factor"
            # inventaría datos y sesgaría todas las comparaciones.
            continue
        present = {
            key for key, rule in FACTOR_RULES.items() if rule(checkin, metrics.get(night.night_of))
        }
        samples.append((present, night.total_sleep_minutes, night.efficiency))

    return insights.associations(samples)


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
