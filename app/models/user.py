from __future__ import annotations

from datetime import datetime, time
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Time, func
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

    onboarding_done: Mapped[bool] = mapped_column(Boolean, default=False)

    # Acceso al panel de /dev. No se acepta nunca del cliente: lo fija el servidor a
    # partir de ADMIN_USERNAMES (ver app/core/security.py).
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Hora a la que necesita levantarse entre semana. Es el ancla del cálculo: la
    # recomendación se construye hacia atrás desde aquí.
    default_wake_time: Mapped[time] = mapped_column(Time, default=time(7, 0))
    sleep_need_minutes: Mapped[int] = mapped_column(Integer, default=480)

    # Lo que la persona *cree* que tarda en dormirse. Sirve mientras no haya noches
    # medidas; en cuanto las hay, manda el dato del reloj.
    declared_latency_minutes: Mapped[int] = mapped_column(Integer, default=20)

    # Proveedor de wearable conectado ("manual", "fitbit", "oura", "import"...).
    wearable_provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Umbral personal para avisar de una mala racha, por si alguien quiere afinarlo.
    poor_efficiency_threshold: Mapped[float] = mapped_column(Float, default=0.85)
