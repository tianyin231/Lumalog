"""Food Records API"""
import os
import uuid
from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from app.models.food import FoodRecord
from app.models.user import User
from app.upload_paths import upload_dir, upload_path_from_url, upload_url
from app.schemas.food import (
    FoodCreate, FoodUpdate, FoodResponse,
    DailyCalorieSummary,
)

router = APIRouter()


@router.post("/", response_model=FoodResponse, status_code=201)
def create_food(
    data: FoodCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
):
    record = FoodRecord(
        user_id=user.id,
        meal_type=data.meal_type,
        image_path=data.image_path,
        total_calories=data.total_calories,
        protein_g=data.protein_g,
        carbs_g=data.carbs_g,
        fat_g=data.fat_g,
        note=data.note,
        recorded_at=data.recorded_at or datetime.now(),
    )
    record.food_items = [item.model_dump() for item in data.food_items]
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/upload", response_model=FoodResponse, status_code=201)
async def upload_food_image(
    image: UploadFile = File(...),
    meal_type: str = Form("snack"),
    recorded_at: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Upload a food image (without AI analysis - just save)"""
    # Validate meal_type
    if meal_type not in ("breakfast", "lunch", "dinner", "snack"):
        raise HTTPException(400, "Invalid meal_type")

    # Save image
    ext = os.path.splitext(image.filename or ".jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = upload_dir("food") / filename

    content = await image.read()
    with open(filepath, "wb") as f:
        f.write(content)

    record = FoodRecord(
        user_id=user.id,
        meal_type=meal_type,
        image_path=upload_url("food", filename),
        recorded_at=datetime.fromisoformat(recorded_at) if recorded_at else datetime.now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=list[FoodResponse])
def list_foods(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    since = datetime.now() - timedelta(days=days)
    stmt = (
        select(FoodRecord)
        .where(FoodRecord.user_id == user.id, FoodRecord.recorded_at >= since)
        .order_by(desc(FoodRecord.recorded_at))
    )
    return db.execute(stmt).scalars().all()


@router.get("/summary", response_model=list[DailyCalorieSummary])
def get_calorie_summary(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Get daily calorie summary for the last N days"""
    since = datetime.now() - timedelta(days=days)
    stmt = (
        select(FoodRecord)
        .where(FoodRecord.user_id == user.id, FoodRecord.recorded_at >= since)
        .order_by(desc(FoodRecord.recorded_at))
    )
    records = db.execute(stmt).scalars().all()

    # Group by date
    daily: dict[str, dict] = {}
    for r in records:
        date_key = r.recorded_at.strftime("%Y-%m-%d")
        if date_key not in daily:
            daily[date_key] = {"breakfast": 0, "lunch": 0, "dinner": 0, "snack": 0, "total": 0}
        daily[date_key][r.meal_type] += r.total_calories
        daily[date_key]["total"] += r.total_calories

    return [
        DailyCalorieSummary(
            date=date_key,
            total_calories=data["total"],
            breakfast=data["breakfast"],
            lunch=data["lunch"],
            dinner=data["dinner"],
            snack=data["snack"],
        )
        for date_key, data in sorted(daily.items())
    ]


@router.get("/{record_id}", response_model=FoodResponse)
def get_food(record_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = db.get(FoodRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(404, "Record not found")
    return record


@router.put("/{record_id}", response_model=FoodResponse)
def update_food(record_id: int, data: FoodUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = db.get(FoodRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(404, "Record not found")

    if data.meal_type is not None:
        record.meal_type = data.meal_type
    if data.food_items is not None:
        record.food_items = [item.model_dump() for item in data.food_items]
    if data.total_calories is not None:
        record.total_calories = data.total_calories
    if data.protein_g is not None:
        record.protein_g = data.protein_g
    if data.carbs_g is not None:
        record.carbs_g = data.carbs_g
    if data.fat_g is not None:
        record.fat_g = data.fat_g
    if data.note is not None:
        record.note = data.note

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=204)
def delete_food(record_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = db.get(FoodRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(404, "Record not found")
    # Delete image file if exists
    if record.image_path:
        filepath = upload_path_from_url(record.image_path)
        if filepath and filepath.exists():
            filepath.unlink()
    db.delete(record)
    db.commit()
