"""Registro, sesiones y verificación de email.

Reglas que se repiten aquí y conviene tener a mano:

- El nombre de usuario se normaliza a minúsculas antes de tocar la base de datos.
- Las respuestas de error no distinguen "no existe" de "contraseña incorrecta", ni al
  entrar ni al pedir un código: decir cuál de las dos falla convierte el formulario en
  un buscador de cuentas.
"""
from __future__ import annotations

import random
import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session as DbSession

from app.core import passwords, tokens
from app.models.auth import EmailVerification, RefreshToken
from app.models.user import User

USERNAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{1,30})[a-z0-9]$")
USERNAME_HELP = (
    "El usuario va de 3 a 32 caracteres: letras, números, punto, guion o guion bajo, "
    "empezando y acabando por letra o número."
)

VERIFICATION_CODE_MINUTES = 15
MAX_VERIFICATION_ATTEMPTS = 5


class AuthError(Exception):
    """Fallo esperado, con mensaje apto para enseñar a quien lo provocó."""


def normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if not USERNAME_PATTERN.match(normalized):
        raise AuthError(USERNAME_HELP)
    return normalized


def find_by_login(db: DbSession, login: str) -> User | None:
    """Busca por usuario o por email: el formulario acepta cualquiera de los dos."""
    value = login.strip().lower()
    return db.scalar(select(User).where(or_(User.username == value, User.email == value)))


def create_user(
    db: DbSession, username: str, password: str, email: str | None = None
) -> User:
    normalized = normalize_username(username)
    normalized_email = email.strip().lower() if email and email.strip() else None

    if db.scalar(select(User).where(User.username == normalized)):
        raise AuthError("Ese nombre de usuario ya está cogido.")
    if normalized_email and db.scalar(select(User).where(User.email == normalized_email)):
        raise AuthError("Ese email ya está en uso.")

    user = User(
        id=str(uuid.uuid4()),
        username=normalized,
        email=normalized_email,
        # Sin email no hay nada que verificar, así que la cuenta nace resuelta en vez
        # de arrastrar un aviso que nunca se va a poder quitar.
        email_verified=normalized_email is None,
        password_hash=passwords.hash_password(password),
        display_name=username.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: DbSession, login: str, password: str) -> User:
    user = find_by_login(db, login)
    if user is None or not passwords.verify(password, user.password_hash):
        raise AuthError("Usuario o contraseña incorrectos.")

    # Subir el coste de Argon2 con el tiempo sin obligar a nadie a cambiar de clave.
    if passwords.needs_rehash(user.password_hash):
        user.password_hash = passwords.hash_password(password)
        db.commit()
    return user


# --- Sesiones -------------------------------------------------------------------


def issue_session(db: DbSession, user: User) -> tuple[str, str]:
    access = tokens.issue_access(user.id)
    refresh = tokens.issue_refresh(user.id)
    db.add(
        RefreshToken(
            jti=refresh.jti,
            user_id=user.id,
            expires_at=refresh.expires_at.replace(tzinfo=None),
        )
    )
    db.commit()
    return access.token, refresh.token


def rotate_session(db: DbSession, refresh_token: str) -> tuple[str, str]:
    """Canjea un refresh por una pareja nueva y anula el anterior.

    La rotación importa: sin ella, un refresh robado sirve treinta días en paralelo a
    la sesión legítima y nadie se entera.
    """
    try:
        payload = tokens.decode(refresh_token, tokens.REFRESH)
    except tokens.TokenError as exc:
        raise AuthError(str(exc))

    row = db.scalar(select(RefreshToken).where(RefreshToken.jti == payload["jti"]))
    if row is None or row.revoked or row.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise AuthError("Sesión caducada o revocada. Vuelve a entrar.")

    user = db.get(User, payload["sub"])
    if user is None:
        raise AuthError("Sesión caducada o revocada. Vuelve a entrar.")

    access = tokens.issue_access(user.id)
    refresh = tokens.issue_refresh(user.id)
    row.revoked = True
    row.replaced_by = refresh.jti
    db.add(
        RefreshToken(
            jti=refresh.jti,
            user_id=user.id,
            expires_at=refresh.expires_at.replace(tzinfo=None),
        )
    )
    db.commit()
    return access.token, refresh.token


def revoke(db: DbSession, refresh_token: str) -> None:
    """Cierra una sesión. Un token ya inválido no es un error: el objetivo era que
    dejara de servir, y ya no sirve."""
    try:
        payload = tokens.decode(refresh_token, tokens.REFRESH)
    except tokens.TokenError:
        return
    db.execute(
        update(RefreshToken).where(RefreshToken.jti == payload["jti"]).values(revoked=True)
    )
    db.commit()


def revoke_all(db: DbSession, user: User) -> int:
    """Cierra todas las sesiones. Se usa al cambiar la contraseña: si alguien te la
    había robado, cambiarla sin echarlo de sus sesiones no sirve de nada."""
    result = db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )
    db.commit()
    return result.rowcount or 0


def change_password(db: DbSession, user: User, current: str, new: str) -> None:
    if not passwords.verify(current, user.password_hash):
        raise AuthError("La contraseña actual no es correcta.")
    if current == new:
        raise AuthError("La contraseña nueva es igual que la anterior.")
    user.password_hash = passwords.hash_password(new)
    db.commit()
    revoke_all(db, user)


# --- Verificación de email ------------------------------------------------------


def start_email_verification(db: DbSession, user: User, email: str) -> str:
    """Crea un código y devuelve el email al que va. El código no sale de aquí."""
    normalized = email.strip().lower()
    existing = db.scalar(select(User).where(User.email == normalized, User.id != user.id))
    if existing:
        raise AuthError("Ese email ya está en uso.")

    # Los códigos anteriores dejan de valer: si no, pedir uno nuevo dejaría vivos
    # todos los viejos y multiplicaría las oportunidades de acertar.
    db.execute(
        update(EmailVerification)
        .where(EmailVerification.user_id == user.id, EmailVerification.used.is_(False))
        .values(used=True)
    )

    code = f"{random.SystemRandom().randrange(10**6):06d}"
    db.add(
        EmailVerification(
            user_id=user.id,
            email=normalized,
            code=code,
            expires_at=(
                datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_CODE_MINUTES)
            ).replace(tzinfo=None),
        )
    )
    user.email = normalized
    user.email_verified = False
    db.commit()
    return code


def verify_email(db: DbSession, user: User, code: str) -> None:
    row = db.scalar(
        select(EmailVerification)
        .where(EmailVerification.user_id == user.id, EmailVerification.used.is_(False))
        .order_by(EmailVerification.created_at.desc())
    )
    if row is None:
        raise AuthError("No hay ningún código pendiente. Pide uno nuevo.")
    if row.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise AuthError("El código ha caducado. Pide uno nuevo.")
    if row.attempts >= MAX_VERIFICATION_ATTEMPTS:
        raise AuthError("Demasiados intentos con este código. Pide uno nuevo.")

    row.attempts += 1
    if row.code != code.strip():
        db.commit()
        raise AuthError("El código no coincide.")

    row.used = True
    user.email_verified = True
    user.email = row.email
    db.commit()
