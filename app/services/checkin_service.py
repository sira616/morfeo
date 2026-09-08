"""Check-in conversacional: el LLM entrevista y extrae, el motor calcula.

La salida del modelo nunca entra en la base de datos tal cual: pasa por el mismo
esquema Pydantic que el formulario manual (`CheckinIn`). Un modelo que alucine
`nap_minutes: 900` se queda fuera igual que lo haría un cliente malicioso.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import date

from pydantic import ValidationError
from sqlalchemy.orm import Session as DbSession

from app.llm import router as llm_router
from app.llm.prompts.checkin import EXTRACTION_SYSTEM_PROMPT, build_interview_prompt
from app.models.user import User
from app.schemas.checkin import CheckinTurn
from app.schemas.sleep import CheckinIn
from app.services import sleep_service

# Claves que el extractor puede tocar. Cualquier otra que devuelva el modelo se
# descarta sin más: la lista blanca la fija el código, no la respuesta del LLM.
EXTRACTABLE_FIELDS = (
    "mood",
    "energy",
    "perceived_stress",
    "nap_minutes",
    "last_caffeine",
    "alcohol",
    "wake_target",
)

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def _flatten(history: list[CheckinTurn], message: str) -> str:
    lines = [f"{'Tú' if t.role == 'user' else 'Asistente'}: {t.content}" for t in history]
    lines.append(f"Tú: {message}")
    return "\n".join(lines)


def extract_fields(conversation: str) -> dict:
    """Pasa la conversación a campos. Devuelve `{}` si el modelo no coopera.

    Un check-in sin extraer no es un error que merezca romper la petición: el motor
    funciona igual con los datos del reloj, solo que con menos contexto.
    """
    try:
        raw = llm_router.generate(EXTRACTION_SYSTEM_PROMPT, conversation)
    except Exception:
        return {}

    match = _JSON_BLOCK.search(raw or "")
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}

    candidate = {k: v for k, v in parsed.items() if k in EXTRACTABLE_FIELDS and v is not None}
    try:
        # Misma validación que el formulario: rangos, formatos de hora y tipos.
        validated = CheckinIn(**candidate)
    except ValidationError:
        return {}
    return {k: getattr(validated, k) for k in candidate}


def stream_checkin(
    db: DbSession, user: User, day: date, message: str, history: list[CheckinTurn]
) -> Iterator[dict]:
    """Emite la conversación por SSE y persiste lo extraído al cerrar el turno.

    Los eventos van etiquetados por nodo (igual que el chat del que sale esta
    plantilla) para que el frontend pueda mostrar en qué punto está sin adivinarlo.
    """
    turn = len(history) // 2 + 1
    conversation = _flatten(history, message)

    known = {}
    checkin = sleep_service.upsert_checkin(db, user, day, {})
    for field in EXTRACTABLE_FIELDS:
        value = getattr(checkin, field, None)
        if value not in (None, 0, False):
            known[field] = value

    yield {"node": "context", "data": {"turn": turn, "known": sorted(known)}}

    system_prompt = build_interview_prompt(known, turn)
    reply = ""
    for chunk in llm_router.stream(system_prompt, conversation):
        reply += chunk
        yield {"node": "reply", "data": {"chunk": chunk}}

    extracted = extract_fields(conversation + f"\nAsistente: {reply}")
    if extracted:
        sleep_service.upsert_checkin(db, user, day, extracted)
    sleep_service.upsert_checkin(
        db, user, day, {"transcript": conversation, "extracted": json.dumps(extracted, default=str)}
    )

    yield {"node": "extracted", "data": {"fields": {k: str(v) for k, v in extracted.items()}}}
