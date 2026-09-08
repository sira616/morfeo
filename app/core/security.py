from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.supabase_client import get_supabase
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def is_admin_email(email: str) -> bool:
    return email.strip().lower() in {e.strip().lower() for e in settings.ADMIN_EMAILS if e.strip()}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Valida el bearer contra Supabase y devuelve el perfil local.

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
        resp = get_supabase().auth.get_user(credentials.credentials)
    except Exception:
        raise credentials_exception
    if resp is None or resp.user is None:
        raise credentials_exception

    user = db.get(User, resp.user.id)
    if user is None:
        # Red de seguridad: el usuario existe en Supabase pero aún no tiene fila de perfil.
        user = User(id=resp.user.id, email=resp.user.email)
        db.add(user)
        db.commit()
        db.refresh(user)

    # El rol se recalcula en cada petición desde ADMIN_EMAILS en vez de quedarse
    # congelado en la fila: así quitar a alguien de la lista le quita el acceso al
    # reiniciar, sin tener que tocar la base de datos.
    admin = is_admin_email(user.email)
    if user.is_admin != admin:
        user.is_admin = admin
        db.commit()
        db.refresh(user)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Puerta del panel de /dev.

    Responde 404 y no 403 a quien no es admin: un 403 confirma que la ruta existe y
    que hay algo detrás que merece la pena buscar.
    """
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    return user
