from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.supabase_client import get_supabase
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


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
    return user
