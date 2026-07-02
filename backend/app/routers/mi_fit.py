"""Mi Fitness sync API."""
from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from app.models.user import User
from app.services.mi_fit_service import (
    backfill_mi_fit_details,
    continue_mi_fit_login,
    get_mi_fit_status,
    import_mi_fit_activities,
    list_mi_fit_activities,
    logout_mi_fit,
    start_mi_fit_login,
    sync_mi_fit_data,
    test_mi_fit_connection,
)

router = APIRouter()


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class ContinueLoginRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


class ImportRequest(BaseModel):
    activity_ids: list[str] = Field(default_factory=list)


@router.get("/status")
def status(user: User = Depends(current_user)):
    return get_mi_fit_status(user.id)


@router.post("/login")
def login(data: LoginRequest, user: User = Depends(current_user)):
    return start_mi_fit_login(user.id, data.email.strip(), data.password)


@router.post("/login/continue")
def continue_login(data: ContinueLoginRequest, user: User = Depends(current_user)):
    return continue_mi_fit_login(user.id, data.session_id)


@router.post("/logout")
def logout(user: User = Depends(current_user)):
    return logout_mi_fit(user.id)


@router.post("/test")
async def test_mi_fit(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return await test_mi_fit_connection(db, user.id)


@router.get("/activities")
def activities(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return list_mi_fit_activities(db, user.id, days=days, limit=limit)


@router.post("/import")
def import_activities(data: ImportRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return import_mi_fit_activities(db, user.id, data.activity_ids)


@router.post("/sync")
def sync_mi_fit(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=300),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return sync_mi_fit_data(db, user.id, days=days, limit=limit)


@router.post("/backfill-details")
def backfill_details(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return backfill_mi_fit_details(db, user.id)
