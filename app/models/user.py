from __future__ import annotations

from datetime import datetime, time
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """Cuenta y preferencias de sueño.

    La identidad es el **nombre de usuario**, no el email: esto se usa entre un par de
    personas en una red doméstica, y obligar a dar un correo para entrar en tu propia
    app de sueño no aporta nada.

    El email es opcional y sirve para una sola cosa: recuperar la contraseña. Mientras
    no se verifique, la cuenta funciona igual; lo que no funciona es la recuperación,
    porque mandar un código a una dirección sin confirmar es mandárselo a cualquiera.

    Lo *observado* del sueño (eficiencia y latencia reales) no vive aquí: se recalcula
    desde `sleep_nights` en cada recomendación, para que no haya dos fuentes de verdad.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Se guarda en minúsculas: "Syreta" y "syreta" no pueden ser dos cuentas.
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Madrid")

    # --- Personalización visible ---
    # Un color de una paleta fija (no rueda libre: así el avatar siempre contrasta con
    # el texto) y un emoji opcional. Es lo único puramente cosmético del modelo.
    avatar_color: Mapped[str] = mapped_column(String(7), default="#4fd6a0")
    avatar_emoji: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    # Foto de perfil como data URL ya normalizado (ver app/core/avatar.py). Se guarda
    # el texto entero y no bytes+mime aparte: es una sola persona con una foto pequeña,
    # y así la salida es echarlo tal cual. `None` = sin foto, cae al color+emoji/inicial.
    avatar_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Frase corta que la persona se pone como objetivo. No entra en ningún cálculo: se
    # enseña y ya. Sirve para recordarse el porqué, que es lo que sostiene un hábito.
    goal: Mapped[Optional[str]] = mapped_column(String(140), nullable=True)

    # Cronotipo declarado: "alondra" | "intermedio" | "buho". NO cambia la cuenta —esa
    # se ancla en tu hora real de despertar, que ya recoge tu ritmo— sino el tono de los
    # consejos y algún texto. Fingir que mueve la hora sería inventarse ciencia.
    chronotype: Mapped[str] = mapped_column(String(16), default="intermedio")

    # Año de nacimiento, no la edad: la edad caduca cada cumpleaños y habría que
    # reescribirla; el año no. `None` = no dado. Es opcional y de momento solo informa
    # (la necesidad de sueño de referencia cambia poco entre adultos), pero deja la
    # puerta abierta a ajustar el valor por defecto para adolescentes o mayores.
    birth_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    onboarding_done: Mapped[bool] = mapped_column(Boolean, default=False)

    # Acceso al panel de /dev. No se acepta nunca del cliente: lo fija el servidor a
    # partir de ADMIN_USERNAMES (ver app/core/security.py).
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Hora a la que necesita levantarse entre semana. Es el ancla del cálculo: la
    # recomendación se construye hacia atrás desde aquí.
    default_wake_time: Mapped[time] = mapped_column(Time, default=time(7, 0))

    # Hora de despertar los fines de semana. `None` = igual que entre semana. Se aplica
    # a las noches cuya mañana cae en sábado o domingo (la noche del viernes despierta
    # en sábado, así que ya cuenta como finde). Cambiar de horario el finde es de lo que
    # más desajusta el sueño; tener el dato deja que la recomendación lo tenga en cuenta
    # en vez de recomendar la hora de diario un domingo.
    weekend_wake_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    sleep_need_minutes: Mapped[int] = mapped_column(Integer, default=480)

    # Lo que la persona *cree* que tarda en dormirse. Sirve mientras no haya noches
    # medidas; en cuanto las hay, manda el dato del reloj.
    declared_latency_minutes: Mapped[int] = mapped_column(Integer, default=20)

    # Proveedor de wearable conectado ("manual", "fitbit", "oura", "import"...).
    wearable_provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Umbral personal para avisar de una mala racha, por si alguien quiere afinarlo.
    poor_efficiency_threshold: Mapped[float] = mapped_column(Float, default=0.85)
