"""Check-in del final del día: el formulario y su versión conversacional."""
from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import RateLimiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.checkin import CheckinStreamIn
from app.schemas.sleep import CheckinIn
from app.services import checkin_service, sleep_service

router = APIRouter(prefix="/api/checkin", tags=["checkin"])

# Cada mensaje son dos llamadas al LLM (respuesta + extracción) y las pagamos
# nosotros. Más generoso que el de login porque conversar es el uso normal.
_stream_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS * 4,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)
_write_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS * 2,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)


def _sse(event: dict) -> bytes:
    return f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n".encode("utf-8")


@router.put("", dependencies=[Depends(_write_rate_limiter)])
def put_checkin(
    payload: CheckinIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Check-in por formulario. Existe además del chat a propósito: hay noches en las
    que nadie quiere conversar, y perder el dato por eso sería absurdo."""
    day = payload.day or date.today()
    fields = payload.model_dump(exclude={"day"}, exclude_unset=True)
    checkin = sleep_service.upsert_checkin(db, user, day, fields)
    return {"day": checkin.day, "saved": sorted(fields)}


@router.post("/stream", dependencies=[Depends(_stream_rate_limiter)])
def stream_checkin(
    payload: CheckinStreamIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Conversación del check-in por SSE."""
    today = date.today()

    def event_source() -> Iterator[bytes]:
        for event in checkin_service.stream_checkin(
            db, user, today, payload.message, payload.history
        ):
            yield _sse(event)
        yield b"data: [DONE]\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
