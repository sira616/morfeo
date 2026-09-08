"""Siembra datos de ejemplo para una cuenta ya registrada.

Escribe directamente en la base de datos y no por la API, a propósito: sesenta noches
seguidas por HTTP chocan con el rate limiting, que está ahí por buenos motivos y no
debería relajarse para poblar una demo.

    venv\\Scripts\\python.exe scripts/sembrar_demo.py tu@email.com [dias]

Las noches malas acompañan al alcohol y al café tarde, así que las asociaciones del
historial tienen algo real que encontrar en vez de ruido.
"""
from __future__ import annotations

import datetime
import random
import sys
from pathlib import Path

# Ejecutable como `python scripts/sembrar_demo.py` sin instalar el paquete ni exportar
# PYTHONPATH: el script vive en scripts/ y el paquete cuelga de la raíz del repo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.sleep import Checkin, SleepNight  # noqa: E402
from app.models.user import User  # noqa: E402

DEFAULT_DAYS = 60


def seed(username: str, days: int = DEFAULT_DAYS, seed_value: int = 3) -> None:
    rng = random.Random(seed_value)
    today = datetime.date.today()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username.strip().lower()))
        if user is None:
            raise SystemExit(f"No existe la cuenta '{username}'. Créala primero.")

        # Idempotente: volver a sembrar no duplica ni mezcla dos tiradas del generador.
        db.execute(delete(SleepNight).where(SleepNight.user_id == user.id))
        db.execute(delete(Checkin).where(Checkin.user_id == user.id))

        for i in range(1, days + 1):
            night_of = today - datetime.timedelta(days=i)
            alcohol = rng.random() < 0.25
            late_coffee = rng.random() < 0.40
            exercise = rng.random() < 0.35

            slept = 420 - (55 if alcohol else 0) - (30 if late_coffee else 0)
            slept += 25 if exercise else 0
            slept += rng.randint(-18, 18)
            latency = 25 + rng.randint(0, 25) + (10 if late_coffee else 0)
            in_bed = int(slept / (0.80 + rng.uniform(-0.05, 0.08)))

            # Los fines de semana se trasnocha: da forma a la regularidad.
            offset = 23 * 60 + 5
            offset += 65 if night_of.weekday() in (4, 5) else rng.randint(-20, 20)
            start = datetime.datetime.combine(night_of, datetime.time()) + datetime.timedelta(
                minutes=offset
            )

            db.add(
                SleepNight(
                    user_id=user.id,
                    night_of=night_of,
                    source="demo",
                    bed_at=start,
                    sleep_start=start + datetime.timedelta(minutes=latency),
                    sleep_end=start + datetime.timedelta(minutes=latency + slept),
                    total_sleep_minutes=slept,
                    time_in_bed_minutes=in_bed,
                    onset_latency_minutes=latency,
                )
            )
            db.add(
                Checkin(
                    user_id=user.id,
                    day=night_of,
                    mood=rng.randint(2, 5),
                    coffees=rng.randint(0, 4),
                    alcohol=alcohol,
                    alcohol_units=rng.randint(1, 4) if alcohol else 0,
                    last_caffeine=datetime.time(18, 30) if late_coffee else datetime.time(10, 30),
                    exercise_minutes=rng.choice([35, 50, 60]) if exercise else 0,
                    exercise_intensity="moderate" if exercise else "none",
                    nap_minutes=rng.choice([0, 0, 0, 25]),
                    meals=3,
                    last_meal=rng.choice(
                        [datetime.time(20, 30), datetime.time(21, 15), datetime.time(22, 30)]
                    ),
                )
            )

        # El check-in de hoy trae señales activas para que se vean los consejos
        # relevantes y las notas del motor nada más entrar.
        db.add(
            Checkin(
                user_id=user.id,
                day=today,
                mood=3,
                coffees=3,
                last_caffeine=datetime.time(17, 30),
                cannabis_days_ago=3,
                meals=3,
                last_meal=datetime.time(21, 0),
                nap_minutes=0,
            )
        )

        user.default_wake_time = datetime.time(7, 0)
        user.sleep_need_minutes = 480
        user.declared_latency_minutes = 30
        user.onboarding_done = True
        db.commit()

    print(f"Sembradas {days} noches y {days + 1} check-ins para {username}.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/sembrar_demo.py syreta [dias]")
    seed(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_DAYS)
