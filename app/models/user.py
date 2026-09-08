from __future__ import annotations

from datetime import time
from typing import Optional

from sqlalchemy import Boolean, Float, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """Perfil de la app. El id es el UUID de auth.users en Supabase: las credenciales
    (contraseña, verificación de email, MFA) las gestiona Supabase Auth, no esta tabla.

    Los campos de sueño son las preferencias declaradas por la persona. Lo *observado*
    (eficiencia real, latencia real) no vive aquí: se recalcula desde `sleep_nights`
    en cada recomendación, para que no haya dos fuentes de verdad que se desincronicen.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Madrid")

    onboarding_done: Mapped[bool] = mapped_column(Boolean, default=False)

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
