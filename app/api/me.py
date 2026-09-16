from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.avatar import AvatarError, normalize_avatar
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import AuthUserOut, MeOut, ProfileIn
from app.services import audit_service

router = APIRouter(prefix="/api/me", tags=["me"])

# Campos donde `null` significa "bórralo", no "no lo toques". Para el resto, mandar
# null es no mandarlo: no se puede borrar la hora de despertar dejándola vacía. Estos
# sí se vacían a propósito —quitar el horario de finde, el emoji, el objetivo, el año
# de nacimiento o la foto— y sin esta lista no habría forma de volver atrás una vez
# puestos.
CLEARABLE_PROFILE_FIELDS = {
    "weekend_wake_time", "avatar_emoji", "goal", "birth_year", "avatar_image"
}


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

    # La foto no se guarda tal cual: se valida y se re-normaliza (mime real por magic
    # bytes, nada de SVG, tope de tamaño). Se hace antes de tocar nada para que una foto
    # mala no deje el resto del patch a medias. Ver app/core/avatar.py.
    if enviados.get("avatar_image") is not None:
        try:
            enviados["avatar_image"] = normalize_avatar(enviados["avatar_image"])
        except AvatarError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            )

    for field, value in enviados.items():
        if value is not None or field in CLEARABLE_PROFILE_FIELDS:
            setattr(user, field, value)
    user.onboarding_done = True
    db.commit()
    db.refresh(user)
    # El data URL de la foto no entra en el registro: abultaría y no aporta. Se apunta
    # el nombre del campo, como el resto.
    audit_service.record(db, user, "profile", ", ".join(sorted(enviados)))
    return AuthUserOut.from_user(user)
