from pydantic import BaseModel, Field

# El mensaje viaja al LLM: su longitud es coste directo en tokens de entrada y no hay
# uso legítimo que necesite más. Sin tope, una sola petición dispara la factura.
MAX_MESSAGE_LEN = 2000
MAX_TURNS = 12


class CheckinTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_LEN)


class CheckinStreamIn(BaseModel):
    """Una vuelta de la conversación de la tarde.

    El historial lo manda el cliente en vez de guardarlo en servidor: el check-in es
    corto, se agota en una sesión y así no hay estado de conversación que expirar.
    El tope de turnos evita que alguien lo use como chat ilimitado.
    """

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LEN)
    history: list[CheckinTurn] = Field(default_factory=list, max_length=MAX_TURNS)
