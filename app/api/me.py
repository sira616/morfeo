from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import AuthUserOut, MeOut, ProfileIn
from app.services import audit_service

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=MeOut)
def get_me(user: User = Depends(get_current_user)):
    return AuthUserOut.from_user(user)


@router.patch("", response_model=MeOut)
def patch_me(payload: ProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Actualización parcial: solo se escriben los campos presentes.

    Con `exclude_unset` un cliente que manda `{"sleep_need_minutes": 450}` no borra la
    hora de despertar que ya tenía guardada.
    """
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, field, value)
    user.onboarding_done = True
    db.commit()
    db.refresh(user)
    audit_service.record(db, user, "profile", ", ".join(sorted(payload.model_dump(exclude_unset=True))))
    return AuthUserOut.from_user(user)
