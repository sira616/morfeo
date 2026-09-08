from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import tokens
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def is_admin_username(username: str) -> bool:
    return username.strip().lower() in {
        u.strip().lower() for u in settings.ADMIN_USERNAMES if u.strip()
    }


def sync_admin_flag(db: Session, user: User) -> User:
    """Pone al día `is_admin` desde ADMIN_USERNAMES.

    Se llama también al entrar y al registrarse, no solo en las peticiones
    autenticadas: si no, la respuesta del login diría `isAdmin: false` para un
    administrador y el frontend escondería el panel hasta el siguiente refresco.
    """
    admin = is_admin_username(user.username)
    if user.is_admin != admin:
        user.is_admin = admin
        db.commit()
        db.refresh(user)
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Valida el access token y devuelve la cuenta.

    Sin credencial responde 401 y no 403: el frontend distingue ambos códigos para
    decidir si toca refrescar el token o mandar al login.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la credencial",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_exception

    try:
        payload = tokens.decode(credentials.credentials, tokens.ACCESS)
    except tokens.TokenError:
        raise credentials_exception

    user = db.get(User, payload["sub"])
    if user is None:
        # Token con firma válida pero de una cuenta borrada.
        raise credentials_exception

    # El rol se recalcula en cada petición en vez de quedarse congelado en la fila:
    # así quitar a alguien de ADMIN_USERNAMES le retira el acceso al reiniciar, sin
    # tener que tocar la base de datos.
    return sync_admin_flag(db, user)


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Puerta del panel de /dev.

    Responde 404 y no 403 a quien no es admin: un 403 confirma que la ruta existe y
    que hay algo detrás que merece la pena buscar.
    """
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return user
