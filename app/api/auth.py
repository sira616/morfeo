from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.passwords import PasswordPolicyError
from app.core.rate_limit import RateLimiter
from app.core.security import get_current_user, sync_admin_flag
from app.models.user import User
from app.schemas.auth import (
    AuthUserOut,
    ChangePasswordIn,
    EmailIn,
    LoginIn,
    RefreshIn,
    RefreshOut,
    TokenPair,
    UserRegister,
    VerificationStartedOut,
    VerifyEmailIn,
)
from app.services import audit_service, auth_service, email_service
from app.services.auth_service import AuthError

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Estas rutas emiten o cambian credenciales, así que llevan límite: sin él, probar
# contraseñas contra este backend le sale gratis a quien lo intente.
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
_verification_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)


@router.post(
    "/register",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_register_rate_limiter)],
)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Alta con usuario y contraseña. El email es opcional.

    Devuelve ya la sesión: obligar a iniciar sesión justo después de registrarse es un
    paso que no aporta nada y que se olvida a mitad.
    """
    try:
        user = auth_service.create_user(db, payload.username, payload.password, payload.email)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    if user.email:
        code = auth_service.start_email_verification(db, user, user.email)
        email_service.send_verification_code(user.email, code)

    sync_admin_flag(db, user)
    access, refresh = auth_service.issue_session(db, user)
    audit_service.record(db, user, "register", f"usuario {user.username}")
    return TokenPair(access_token=access, refresh_token=refresh, user=AuthUserOut.from_user(user))


@router.post("/login", response_model=TokenPair, dependencies=[Depends(_login_rate_limiter)])
def login(payload: LoginIn, db: Session = Depends(get_db)):
    try:
        user = auth_service.authenticate(db, payload.login, payload.password)
    except AuthError:
        # Mismo mensaje para "no existe" y "contraseña mal": distinguirlos convierte el
        # formulario en un buscador de cuentas.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contraseña incorrectos."
        )

    sync_admin_flag(db, user)
    access, refresh = auth_service.issue_session(db, user)
    audit_service.record(db, user, "login")
    return TokenPair(access_token=access, refresh_token=refresh, user=AuthUserOut.from_user(user))


@router.post("/refresh", response_model=RefreshOut, dependencies=[Depends(_refresh_rate_limiter)])
def refresh(payload: RefreshIn, db: Session = Depends(get_db)):
    try:
        access, new_refresh = auth_service.rotate_session(db, payload.refresh_token)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    return RefreshOut(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshIn, db: Session = Depends(get_db)):
    auth_service.revoke(db, payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cambia la contraseña y cierra todas las sesiones.

    Cerrarlas es el punto: si alguien te la había robado, cambiarla sin echarlo de sus
    sesiones abiertas no le quita el acceso.
    """
    try:
        auth_service.change_password(db, user, payload.current_password, payload.new_password)
    except PasswordPolicyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    audit_service.record(db, user, "password", "cambio de contraseña")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/email",
    response_model=VerificationStartedOut,
    dependencies=[Depends(_verification_rate_limiter)],
)
def start_email_verification(
    payload: EmailIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Asocia un email a la cuenta y manda el código.

    El código no viaja en la respuesta: si lo hiciera, verificar un email sería un
    trámite que cualquiera puede completar sin acceso a ese correo.
    """
    try:
        code = auth_service.start_email_verification(db, user, payload.email)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    sent = email_service.send_verification_code(payload.email, code)
    audit_service.record(db, user, "email", "código de confirmación enviado")
    return VerificationStartedOut(email=payload.email, sent_by_email=sent)


@router.post(
    "/email/verify",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_verification_rate_limiter)],
)
def verify_email(
    payload: VerifyEmailIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    try:
        auth_service.verify_email(db, user, payload.code)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    audit_service.record(db, user, "email", "email verificado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
