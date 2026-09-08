from datetime import time

from pydantic import BaseModel, EmailStr, Field

from app.models.user import User


class UserRegister(BaseModel):
    """El alta solo acepta email y contraseña.

    Nada de campos de perfil aquí: cualquier atributo que el cliente pueda fijar en el
    registro es un atributo que el cliente puede falsear. El perfil se completa después,
    autenticado, contra `/api/me`.
    """

    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr

    model_config = {"from_attributes": True}


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AuthUserOut(BaseModel):
    id: str
    email: EmailStr
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
            email=user.email,
            displayName=user.display_name or user.email.split("@")[0],
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


class ProfileIn(BaseModel):
    """Preferencias de sueño. Los rangos no son decorativos: una necesidad de sueño de
    dos horas o de veinte convierte la recomendación en un disparate con apariencia
    de dato."""

    display_name: str | None = Field(default=None, max_length=120)
    default_wake_time: time | None = None
    sleep_need_minutes: int | None = Field(default=None, ge=300, le=660)
    declared_latency_minutes: int | None = Field(default=None, ge=0, le=180)
    timezone: str | None = Field(default=None, max_length=64)
