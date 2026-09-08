"""Entrada de datos: noches, métricas del día e importación de exportaciones."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import RateLimiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.sleep import DailyMetricsIn, ImportIn, NightOut, NightsIn
from app.services import sleep_service
from app.wearables.base import DaySample, NightSample
from app.wearables.fileimport import ImportError_, parse_nights

router = APIRouter(prefix="/api/sleep", tags=["sleep"])

# Estas rutas escriben filas y, en el caso de la importación, parsean un fichero
# grande. Sin límite, una cuenta válida puede llenar la base de datos sin tope.
_write_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS * 2,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)
_import_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)

MAX_HISTORY_DAYS = 365


def _to_sample(night) -> NightSample:
    return NightSample(
        night_of=night.night_of,
        total_sleep_minutes=night.total_sleep_minutes,
        time_in_bed_minutes=night.time_in_bed_minutes,
        bed_at=night.bed_at,
        sleep_start=night.sleep_start,
        sleep_end=night.sleep_end,
        onset_latency_minutes=night.onset_latency_minutes,
        awakenings=night.awakenings,
        deep_minutes=night.deep_minutes,
        rem_minutes=night.rem_minutes,
        light_minutes=night.light_minutes,
        resting_hr=night.resting_hr,
        hrv_ms=night.hrv_ms,
    )


@router.post("/nights", status_code=status.HTTP_201_CREATED, dependencies=[Depends(_write_rate_limiter)])
def put_nights(
    payload: NightsIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Alta o actualización de noches. Idempotente por fecha."""
    written = sleep_service.upsert_nights(
        db, user, [_to_sample(n) for n in payload.nights], source="manual"
    )
    return {"written": written}


@router.get("/nights", response_model=list[NightOut])
def list_nights(
    days: int = Query(default=30, ge=1, le=MAX_HISTORY_DAYS),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    nights = sleep_service.recent_nights(db, user, days, date.today())
    return [
        NightOut(
            night_of=n.night_of,
            total_sleep_minutes=n.total_sleep_minutes,
            time_in_bed_minutes=n.time_in_bed_minutes,
            onset_latency_minutes=n.onset_latency_minutes,
            awakenings=n.awakenings,
            bed_at=n.bed_at,
            sleep_start=n.sleep_start,
            sleep_end=n.sleep_end,
            deep_minutes=n.deep_minutes,
            rem_minutes=n.rem_minutes,
            light_minutes=n.light_minutes,
            resting_hr=n.resting_hr,
            hrv_ms=n.hrv_ms,
            source=n.source,
            efficiency=round(n.efficiency, 3),
        )
        for n in nights
    ]


@router.post("/import", dependencies=[Depends(_import_rate_limiter)])
def import_export(
    payload: ImportIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Carga la exportación de un reloj (JSON o CSV).

    Los errores de formato salen con el número de fila y qué falta: el usuario está
    mapeando columnas a mano y un 400 genérico no le sirve de nada.
    """
    try:
        nights = parse_nights(payload.content, payload.format)
    except ImportError_ as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    written = sleep_service.upsert_nights(db, user, nights, source="import")
    user.wearable_provider = user.wearable_provider or "import"
    db.commit()
    return {"written": written, "from": nights[0].night_of if nights else None}


@router.post("/metrics", status_code=status.HTTP_201_CREATED, dependencies=[Depends(_write_rate_limiter)])
def put_metrics(
    payload: DailyMetricsIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if payload.day > date.today() + timedelta(days=1):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se pueden registrar métricas de un día futuro",
        )
    sleep_service.upsert_day(
        db,
        user,
        DaySample(
            day=payload.day,
            steps=payload.steps,
            exercise_minutes=payload.exercise_minutes,
            exercise_intensity=payload.exercise_intensity,
            exercise_end=payload.exercise_end,
            stress_avg=payload.stress_avg,
            resting_hr=payload.resting_hr,
            hrv_ms=payload.hrv_ms,
        ),
        source=payload.source,
    )
    return {"ok": True}
