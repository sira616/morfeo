from collections.abc import Iterator

from anthropic import Anthropic

from app.core.config import settings

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def generate(system_prompt: str, user_message: str) -> str:
    if not settings.ANTHROPIC_API_KEY:
        return (
            "[modo demo sin ANTHROPIC_API_KEY configurada] "
            "Aquí iría la conversación del check-in. El cálculo de la hora no depende de esto: "
            "lo hace app/domain/bedtime.py y funciona igual sin modelo. "
            "Configura ANTHROPIC_API_KEY en tu .env para obtener respuestas reales del modelo."
        )

    response = _get_client().messages.create(
        model=settings.LLM_CLOUD_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def stream(system_prompt: str, user_message: str) -> Iterator[str]:
    if not settings.ANTHROPIC_API_KEY:
        demo_text = (
            "[modo demo sin ANTHROPIC_API_KEY configurada] "
            "Aquí iría la conversación del check-in. El cálculo de la hora no depende de esto: "
            "lo hace app/domain/bedtime.py y funciona igual sin modelo. "
            "Configura ANTHROPIC_API_KEY en tu .env para obtener respuestas reales del modelo."
        )
        chunk_size = max(1, len(demo_text) // 3)
        for i in range(0, len(demo_text), chunk_size):
            yield demo_text[i : i + chunk_size]
        return

    with _get_client().messages.stream(
        model=settings.LLM_CLOUD_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    ) as stream_ctx:
        yield from stream_ctx.text_stream
