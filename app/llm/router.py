"""Router LLM local vs cloud (sección 2 de la propuesta).

`settings.LLM_PROVIDER` decide el backend ("cloud" = Claude, "local" = Ollama,
modo privacidad). Los llamadores (`app.services`) solo conocen `generate`/`stream`.
"""
from collections.abc import Iterator

from app.core.config import settings
from app.llm import cloud, local


def generate(system_prompt: str, user_message: str) -> str:
    if settings.LLM_PROVIDER == "local":
        return local.generate(system_prompt, user_message)
    return cloud.generate(system_prompt, user_message)


def stream(system_prompt: str, user_message: str) -> Iterator[str]:
    if settings.LLM_PROVIDER == "local":
        yield from local.stream(system_prompt, user_message)
    else:
        yield from cloud.stream(system_prompt, user_message)
