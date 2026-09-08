from datetime import time

from pydantic import BaseModel, EmailStr, Field

from app.core.passwords import MAX_LENGTH, MIN_LENGTH
from app.models.user import User

MAX_LOGIN_LEN = 255


class UserRegister(BaseModel):
    """El alta pide usuario y contraseña. El email es opcional.

    Nada de campos de perfil aquí: cualquier atributo que el cliente pueda fijar en el
    registro es un atributo que el cliente puede falsear. El perfil se completa
    después, autenticado, contra `/api/me`.
    """

    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=MIN_LENGTH, max_length=MAX_LENGTH)
    email: EmailStr | None = None


class LoginIn(BaseModel):
    """`login` acepta el usuario o el email: quien tiene los dos no debería recordar
    cuál puso."""

    login: str = Field(min_length=1, max_length=MAX_LOGIN_LEN)
    password: str = Field(min_length=1, max_length=MAX_LENGTH)


class AuthUserOut(BaseModel):
    id: str
    username: str
    email: EmailStr | None
    emailVerified: bool
    displayName: str
    onboardingDone: bool
    isAdmin: bool
    defaultWakeTime: time
    sleepNeedMinutes: int
    declaredLatencyMinutes: int
    wearableProvider: str | None

    @classmethod
    def from_user(cls, user: User) -> "AuthUserOut":
        return cls(
            id=str(user.id),
            username=user.username,
            email=user.email,
            emailVerified=user.email_verified,
            displayName=user.display_name or user.username,
            onboardingDone=user.onboarding_done,
            isAdmin=user.is_admin,
            defaultWakeTime=user.default_wake_time,
            sleepNeedMinutes=user.sleep_need_minutes,
            declaredLatencyMinutes=user.declared_latency_minutes,
            wearableProvider=user.wearable_provider,
        )


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    user: AuthUserOut


class RefreshIn(BaseModel):
    refresh_token: str


class RefreshOut(BaseModel):
    access_token: str
    refresh_token: str


class MeOut(AuthUserOut):
    pass


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=MAX_LENGTH)
    new_password: str = Field(min_length=MIN_LENGTH, max_length=MAX_LENGTH)


class EmailIn(BaseModel):
    email: EmailStr


class VerifyEmailIn(BaseModel):
    code: str = Field(min_length=4, max_length=8)


class VerificationStartedOut(BaseModel):
    email: EmailStr
    # False cuando no hay SMTP: el código está en la consola del servidor. Se dice,
    # en vez de dejar a alguien esperando un correo que no va a llegar.
    sent_by_email: bool


class ProfileIn(BaseModel):
    """Preferencias de sueño. Los rangos no son decorativos: una necesidad de sueño de
    dos horas o de veinte convierte la recomendación en un disparate con apariencia
    de dato."""

    display_name: str | None = Field(default=None, max_length=120)
    default_wake_time: time | None = None
    sleep_need_minutes: int | None = Field(default=None, ge=300, le=660)
    declared_latency_minutes: int | None = Field(default=None, ge=0, le=180)
    timezone: str | None = Field(default=None, max_length=64)
