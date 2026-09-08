from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from supabase_auth.errors import AuthApiError

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import RateLimiter
from app.core.security import bearer_scheme
from app.core.supabase_client import get_supabase, get_supabase_admin
from app.models.user import User
from app.schemas.auth import (
    AuthUserOut,
    LoginIn,
    RefreshIn,
    RefreshOut,
    TokenPair,
    UserOut,
    UserRegister,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Supabase Auth aplica sus propios límites, pero solo a partir de la petición que
# nos llega: sin este bucket, un atacante puede lanzar fuerza bruta contra este
# backend a coste cero para él y consumiendo nuestra cuota de Supabase.
_register_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS, window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS
)
_login_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS, window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS
)
# El refresh lo dispara el propio cliente al expirar el access y puede haber varias
# pestañas a la vez, así que un límite tan bajo como el de login cortaría sesiones
# legítimas. Se protege igualmente porque emite credenciales.
_refresh_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS * 4,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_register_rate_limiter)],
)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    try:
        resp = get_supabase().auth.sign_up({"email": payload.email, "password": payload.password})
    except AuthApiError as exc:
        raise HTTPException(status_code=400, detail=exc.message)
    if resp.user is None:
        raise HTTPException(status_code=400, detail="No se pudo crear el usuario")

    user = User(id=resp.user.id, email=payload.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair, dependencies=[Depends(_login_rate_limiter)])
def login(payload: LoginIn, db: Session = Depends(get_db)):
    try:
        resp = get_supabase().auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except AuthApiError as exc:
        if exc.code == "email_not_confirmed":
            raise HTTPException(status_code=403, detail="Confirma tu email antes de iniciar sesión")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    if resp.session is None or resp.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    user = db.get(User, resp.user.id)
    if user is None:
        user = User(id=resp.user.id, email=resp.user.email)
        db.add(user)
        db.commit()
        db.refresh(user)

    return TokenPair(
        access_token=resp.session.access_token,
        refresh_token=resp.session.refresh_token,
        user=AuthUserOut.from_user(user),
    )


@router.post("/refresh", response_model=RefreshOut, dependencies=[Depends(_refresh_rate_limiter)])
def refresh(payload: RefreshIn):
    try:
        resp = get_supabase().auth.refresh_session(payload.refresh_token)
    except AuthApiError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado")
    if resp.session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado")

    return RefreshOut(access_token=resp.session.access_token, refresh_token=resp.session.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    if credentials is not None:
        try:
            get_supabase_admin().auth.admin.sign_out(credentials.credentials)
        except AuthApiError:
            pass  # token ya inválido/expirado: no hay nada que revocar
    return Response(status_code=status.HTTP_204_NO_CONTENT)
