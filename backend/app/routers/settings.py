"""User Settings API"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from app.models.settings import UserSettings
from app.models.user import User
from app.schemas.settings import SettingsUpdate, SettingsResponse

router = APIRouter()


def get_or_create_settings(db: Session, user_id: int) -> UserSettings:
    s = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not s:
        s = UserSettings(user_id=user_id)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


@router.get("/", response_model=SettingsResponse)
def get_settings(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
):
    return get_or_create_settings(db, user.id)


@router.put("/", response_model=SettingsResponse)
def update_settings(
    data: SettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
):
    settings = get_or_create_settings(db, user.id)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)

    db.commit()
    db.refresh(settings)
    return settings
