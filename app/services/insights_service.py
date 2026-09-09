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


# --- Informe de la semana ---------------------------------------------------------


def _factors_of(checkin: Checkin, metrics: DailyMetrics | None) -> set[str]:
    return {key for key, rule in FACTOR_RULES.items() if rule(checkin, metrics)}


def _minutes_of(moment) -> int:
    return moment.hour * 60 + moment.minute


def weekly(db: DbSession, user: User, today: date, offset: int = 0) -> dict:
    """Las últimas siete noches contra las siete anteriores.

    `offset` retrocede semanas enteras: 0 son las siete noches que acaban hoy, 1 las
    siete anteriores. La ventana es **móvil**, no la semana del calendario, y esa es
    la decisión de producto de esta ruta: un informe que solo cuadra los domingos hay
    que acordarse de mirarlo el domingo. Este dice algo cualquier día.
    """
    end = today - timedelta(days=offset * insights.WEEK_NIGHTS)
    start = end - timedelta(days=insights.WEEK_NIGHTS - 1)

    nights = sleep_service.recent_nights(db, user, insights.WEEK_NIGHTS, end)
    earlier = sleep_service.recent_nights(
        db, user, insights.WEEK_NIGHTS, end - timedelta(days=insights.WEEK_NIGHTS)
    )

    current = insights.week_stats(
        [n.total_sleep_minutes for n in nights],
        [n.efficiency for n in nights],
        [m for _, m in _midpoints(nights)],
    )
    previous = insights.week_stats(
        [n.total_sleep_minutes for n in earlier],
        [n.efficiency for n in earlier],
        [m for _, m in _midpoints(earlier)],
    )

    shift = None
    if current.mean_midpoint_minutes is not None and previous.mean_midpoint_minutes is not None:
        shift = insights.circular_delta(
            current.mean_midpoint_minutes, previous.mean_midpoint_minutes
        )

    rows = {
        r.day: r
        for r in db.scalars(
            select(BedtimeRecommendation).where(
                BedtimeRecommendation.user_id == user.id,
                BedtimeRecommendation.day >= start,
                BedtimeRecommendation.day <= end,
            )
        )
    }
    checkins = {
        c.day: c
        for c in db.scalars(
            select(Checkin).where(
                Checkin.user_id == user.id, Checkin.day >= start, Checkin.day <= end
            )
        )
    }
    metrics = {
        m.day: m
        for m in db.scalars(
            select(DailyMetrics).where(
                DailyMetrics.user_id == user.id, DailyMetrics.day >= start, DailyMetrics.day <= end
            )
        )
    }

    midpoints = dict(_midpoints(nights))
    detail = []
    kept = measured = 0
    for night in nights:
        row = rows.get(night.night_of)
        in_window = None
        # Solo se puede decir si se cumplió la ventana cuando hay las dos cosas: la
        # recomendación de ese día y la hora real a la que se metió en la cama. Sin la
        # segunda —que muchos importadores no traen— la noche queda en blanco, no en
        # "no cumplida".
        if row is not None and night.bed_at is not None:
            in_window = insights.within_window(
                _minutes_of(night.bed_at), _minutes_of(row.window_start), _minutes_of(row.window_end)
            )
            measured += 1
            kept += int(in_window)

        detail.append(
            {
                "night_of": night.night_of,
                "total_sleep_minutes": night.total_sleep_minutes,
                "efficiency": round(night.efficiency, 3),
                "midpoint_minutes": midpoints.get(night.night_of),
                "recommended": row.bedtime if row else None,
                "actual": night.bed_at.time() if night.bed_at else None,
                "in_window": in_window,
                "followed": row.followed if row else None,
            }
        )

    samples = [
        (_factors_of(checkins[n.night_of], metrics.get(n.night_of)), n.total_sleep_minutes)
        for n in nights
        if n.night_of in checkins
    ]
    factors = insights.worst_night_factors(samples)

    debt, debt_before = sleep_service.debt_detail(db, user, end)
    debt_delta = debt.minutes - debt_before if debt_before is not None else None

    by_sleep = sorted(nights, key=lambda n: n.total_sleep_minutes)
    answered = [r for r in rows.values() if r.followed is not None]

    return {
        "start": start,
        "end": end,
        "offset": offset,
        "current": current.__dict__,
        "previous": previous.__dict__,
        "sleep_delta_minutes": (
            current.mean_sleep_minutes - previous.mean_sleep_minutes
            if current.mean_sleep_minutes is not None and previous.mean_sleep_minutes is not None
            else None
        ),
        "efficiency_delta": (
            round(current.mean_efficiency - previous.mean_efficiency, 3)
            if current.mean_efficiency is not None and previous.mean_efficiency is not None
            else None
        ),
        "midpoint_shift_minutes": shift,
        "regularity_delta_minutes": (
            current.sd_midpoint_minutes - previous.sd_midpoint_minutes
            if current.sd_midpoint_minutes is not None and previous.sd_midpoint_minutes is not None
            else None
        ),
        "debt_minutes": debt.minutes,
        "debt_delta_minutes": debt_delta,
        "nights": detail,
        "best_night": by_sleep[-1].night_of if by_sleep else None,
        "worst_night": by_sleep[0].night_of if by_sleep else None,
        "window_kept": kept,
        "window_measured": measured,
        "followed": sum(1 for r in answered if r.followed),
        "answered": len(answered),
        "recommended": len(rows),
        "worst_night_factors": [f.__dict__ for f in factors],
        "highlights": insights.weekly_highlights(
            current=current,
            previous=previous,
            midpoint_shift_minutes=shift,
            factors=factors,
            window_kept=kept,
            window_measured=measured,
            debt_delta_minutes=debt_delta,
        ),
    }
