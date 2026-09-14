from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import AuthUserOut, MeOut, ProfileIn
from app.services import audit_service

router = APIRouter(prefix="/api/me", tags=["me"])

# Campos donde `null` significa "bórralo", no "no lo toques". Para el resto, mandar
# null es no mandarlo: no se puede borrar la hora de despertar dejándola vacía. Estos
# sí se vacían a propósito —quitar el horario de finde, el emoji, el objetivo o el año
# de nacimiento— y sin esta lista no habría forma de volver atrás una vez puestos.
CLEARABLE_PROFILE_FIELDS = {"weekend_wake_time", "avatar_emoji", "goal", "birth_year"}


@router.get("", response_model=MeOut)
def get_me(user: User = Depends(get_current_user)):
    return AuthUserOut.from_user(user)


@router.patch("", response_model=MeOut)
def patch_me(payload: ProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Actualización parcial: solo se escriben los campos presentes.

    Con `exclude_unset` un cliente que manda `{"sleep_need_minutes": 450}` no borra la
    hora de despertar que ya tenía guardada. La única sutileza es qué hacer con un
    `null` explícito: para casi todo es "no lo toques", pero para los campos vaciables
    es "bórralo" (ver CLEARABLE_PROFILE_FIELDS).
    """
    enviados = payload.model_dump(exclude_unset=True)
    for field, value in enviados.items():
        if value is not None or field in CLEARABLE_PROFILE_FIELDS:
            setattr(user, field, value)
    user.onboarding_done = True
    db.commit()
    db.refresh(user)
    audit_service.record(db, user, "profile", ", ".join(sorted(enviados)))
    return AuthUserOut.from_user(user)
