"""Cliente Ollama — LLM local o Ollama Cloud, "modo privacidad" (Fase 3 del roadmap original).

Misma interfaz que `app.llm.cloud` (`generate`/`stream`) para que `app.llm.router`
pueda alternar entre uno y otro sin tocar a los llamadores. Sirve tanto para un
Ollama local (`OLLAMA_BASE_URL=http://localhost:11434`, sin API key) como para
Ollama Cloud (`OLLAMA_BASE_URL=https://ollama.com/api`, con `OLLAMA_API_KEY`) —
mismo endpoint `/api/chat` en ambos casos.
"""
import json
from collections.abc import Iterator

import httpx

from app.core.config import settings


def _messages(system_prompt: str, user_message: str) -> list[dict]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]


def _headers() -> dict:
    if settings.OLLAMA_API_KEY:
        return {"Authorization": f"Bearer {settings.OLLAMA_API_KEY}"}
    return {}


def generate(system_prompt: str, user_message: str) -> str:
    response = httpx.post(
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        json={"model": settings.OLLAMA_MODEL, "messages": _messages(system_prompt, user_message), "stream": False},
        headers=_headers(),
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def stream(system_prompt: str, user_message: str) -> Iterator[str]:
    with httpx.stream(
        "POST",
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        json={"model": settings.OLLAMA_MODEL, "messages": _messages(system_prompt, user_message), "stream": True},
        headers=_headers(),
        timeout=120,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content
            if chunk.get("done"):
                break
