"""Elige los consejos del día.

Dos decisiones que valen más que el algoritmo:

- **Primero lo que hoy te viene a cuento.** Si anoche tomaste café a las siete, el
  consejo sobre la vida media de la cafeína vale más que el de la temperatura de la
  habitación. Se cogen hasta tres relevantes y se rellena con el resto.
- **Estable durante el día.** La selección se siembra con (usuario, fecha), así que no
  cambia al recargar. Unos consejos que bailan cada vez que entras no se leen: se
  hojean.
"""
from __future__ import annotations

import random
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.content.sleep_tips import (
    SIGNAL_ALCOHOL,
    SIGNAL_CAFFEINE_LATE,
    SIGNAL_HIGH_DEBT,
    SIGNAL_HIGH_LATENCY,
    SIGNAL_IRREGULAR,
    SIGNAL_LATE_EXERCISE,
    SIGNAL_LONG_NAP,
    SIGNAL_LOW_EFFICIENCY,
    SIGNAL_CHRONOTYPE_LARK,
    SIGNAL_CHRONOTYPE_OWL,
    SIGNAL_LOW_MOOD,
    TIPS,
    Tip,
)
from app.domain.bedtime import RESTRICTION_EFFICIENCY_THRESHOLD, RESTRICTION_MIN_NIGHTS
from app.models.sleep import Checkin, DailyMetrics
from app.models.user import User
from app.services import insights_service, sleep_service

TIPS_PER_DAY = 5
MAX_RELEVANT = 3

CAFFEINE_LATE_FROM = time(16, 0)
LATE_EXERCISE_FROM = time(20, 0)
LONG_NAP_MINUTES = 45
HIGH_LATENCY_MINUTES = 30
HIGH_DEBT_MINUTES = 300
IRREGULAR_SCORE = 60


def signals(db: DbSession, user: User, day: date) -> set[str]:
    """Qué le pasa hoy a esta persona, en el vocabulario de `sleep_tips`."""
    found: set[str] = set()

    checkin = db.scalar(select(Checkin).where(Checkin.user_id == user.id, Checkin.day == day))
    if checkin:
        if checkin.last_caffeine and checkin.last_caffeine >= CAFFEINE_LATE_FROM:
            found.add(SIGNAL_CAFFEINE_LATE)
        if checkin.alcohol:
            found.add(SIGNAL_ALCOHOL)
        if checkin.nap_minutes >= LONG_NAP_MINUTES:
            found.add(SIGNAL_LONG_NAP)
        if checkin.mood is not None and checkin.mood <= 2:
            found.add(SIGNAL_LOW_MOOD)

    metrics = db.scalar(
        select(DailyMetrics).where(DailyMetrics.user_id == user.id, DailyMetrics.day == day)
    )
    if (
        metrics
        and metrics.exercise_end
        and metrics.exercise_end >= LATE_EXERCISE_FROM
        and metrics.exercise_intensity in ("moderate", "hard")
    ):
        found.add(SIGNAL_LATE_EXERCISE)

    profile = sleep_service.load_profile(db, user, day)
    if (
        profile.nights_observed >= RESTRICTION_MIN_NIGHTS
        and profile.efficiency < RESTRICTION_EFFICIENCY_THRESHOLD
    ):
        found.add(SIGNAL_LOW_EFFICIENCY)
    if profile.onset_latency_minutes >= HIGH_LATENCY_MINUTES:
        found.add(SIGNAL_HIGH_LATENCY)

    if sleep_service.build_signals(db, user, day).sleep_debt_minutes >= HIGH_DEBT_MINUTES:
        found.add(SIGNAL_HIGH_DEBT)

    reg = insights_service.regularity(db, user, day)
    if reg is not None and reg.score < IRREGULAR_SCORE:
        found.add(SIGNAL_IRREGULAR)

    # El cronotipo no se mide, se declara: entra como una señal más para que su
    # consejo salga priorizado, que es todo lo que promete el perfil.
    if user.chronotype == "buho":
        found.add(SIGNAL_CHRONOTYPE_OWL)
    elif user.chronotype == "alondra":
        found.add(SIGNAL_CHRONOTYPE_LARK)

    return found


def pick(active: set[str], seed: str, count: int = TIPS_PER_DAY) -> list[Tip]:
    """Consejos del día: primero los que aplican, luego relleno estable."""
    rng = random.Random(seed)

    relevant = [t for t in TIPS if t.applies_when and t.applies_when in active]
    rng.shuffle(relevant)
    chosen = relevant[:MAX_RELEVANT]

    rest = [t for t in TIPS if t not in chosen]
    rng.shuffle(rest)
    chosen += rest[: count - len(chosen)]
    return chosen[:count]


def tips_for(db: DbSession, user: User, day: date) -> tuple[list[Tip], set[str]]:
    active = signals(db, user, day)
    return pick(active, seed=f"{user.id}:{day.isoformat()}"), active
