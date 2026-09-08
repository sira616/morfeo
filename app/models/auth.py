from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RefreshToken(Base):
    """Sesiones abiertas, una fila por refresh emitido.

    El access token es sin estado y no se puede revocar; el refresh sí, y por eso vive
    aquí. Sin esta tabla, cerrar sesión sería una mentira: el token seguiría sirviendo
    para pedir accesos nuevos hasta caducar.

    Se guarda el `jti`, no el token: si alguien lee la base de datos, no se lleva
    credenciales usables.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)

    issued_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Qué lo sustituyó al rotar. Deja el rastro para ver una cadena de sesión entera.
    replaced_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class EmailVerification(Base):
    """Código de confirmación de email, de un solo uso y con caducidad.

    Solo existe cuando alguien añade un email a su cuenta. Las cuentas sin email —que
    son las normales aquí— no pasan por esto.
    """

    __tablename__ = "email_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    email: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(8))

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    # Tope de intentos: sin él, seis dígitos se sacan a fuerza bruta en un rato.
    attempts: Mapped[int] = mapped_column(Integer, default=0)
