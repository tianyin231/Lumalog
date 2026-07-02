"""Weight Records API"""
from datetime import datetime, timedelta
from statistics import mean
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from app.models.weight import WeightRecord
from app.models.settings import UserSettings
from app.models.user import User
from app.schemas.weight import (
    WeightCreate, WeightUpdate, WeightResponse,
    WeightStats, WeightTrendPoint,
)

router = APIRouter()


def calc_bmi(weight_kg: float, height_cm: float) -> float:
    """Calculate BMI"""
    height_m = height_cm / 100
    return round(weight_kg / (height_m * height_m), 1)


def get_settings(db: Session, user_id: int) -> UserSettings:
    """Get or create the single user settings"""
    s = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not s:
        s = UserSettings(user_id=user_id)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


@router.post("/", response_model=WeightResponse, status_code=201)
def create_weight(
    data: WeightCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
):
    settings = get_settings(db, user.id)
    bmi = calc_bmi(data.weight_kg, settings.height_cm)

    record = WeightRecord(
        user_id=user.id,
        weight_kg=data.weight_kg,
        bmi=bmi,
        body_fat_pct=data.body_fat_pct,
        note=data.note,
        source="manual",
        recorded_at=data.recorded_at or datetime.now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=list[WeightResponse])
def list_weights(
    days: int = Query(90, ge=1, le=3650),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    since = datetime.now() - timedelta(days=days)
    stmt = (
        select(WeightRecord)
        .where(WeightRecord.user_id == user.id, WeightRecord.recorded_at >= since)
        .order_by(desc(WeightRecord.recorded_at))
    )
    return db.execute(stmt).scalars().all()


@router.get("/trend", response_model=list[WeightTrendPoint])
def get_weight_trend(
    days: int = Query(90, ge=7, le=3650),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Get weight trend data with 7-day moving average for charting"""
    since = datetime.now() - timedelta(days=days)
    stmt = (
        select(WeightRecord)
        .where(WeightRecord.user_id == user.id, WeightRecord.recorded_at >= since)
        .order_by(asc(WeightRecord.recorded_at))
    )
    records = db.execute(stmt).scalars().all()

    points = []
    weights = [r.weight_kg for r in records]

    for i, r in enumerate(records):
        # 7-day simple moving average
        window = weights[max(0, i - 3):i + 4]  # ±3 days
        smoothed = round(mean(window), 1) if window else None

        points.append(WeightTrendPoint(
            date=r.recorded_at.strftime("%Y-%m-%d"),
            weight=r.weight_kg,
            bmi=r.bmi,
            smoothed=smoothed,
        ))

    return points


@router.get("/stats", response_model=WeightStats)
def get_weight_stats(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Get aggregated weight statistics"""
    settings = get_settings(db, user.id)

    stmt = (
        select(WeightRecord)
        .where(WeightRecord.user_id == user.id)
        .order_by(asc(WeightRecord.recorded_at))
    )
    records = db.execute(stmt).scalars().all()

    if not records:
        return WeightStats(
            current_weight=None, start_weight=None, weight_change=None,
            avg_7days=None, min_weight=None, max_weight=None,
            bmi=None, days_tracked=0, trend_direction="stable",
        )

    current = records[-1].weight_kg
    first = records[0].weight_kg
    change = round(current - first, 1)

    # Last 7 days average
    week_ago = datetime.now() - timedelta(days=7)
    recent = [r.weight_kg for r in records if r.recorded_at >= week_ago]
    avg7 = round(mean(recent), 1) if recent else None

    all_weights = [r.weight_kg for r in records]

    # Trend direction
    if len(all_weights) >= 7:
        first_week_avg = mean(all_weights[:min(7, len(all_weights))])
        last_week_avg = mean(all_weights[-min(7, len(all_weights)):])
        diff = last_week_avg - first_week_avg
        if diff < -0.3:
            direction = "down"
        elif diff > 0.3:
            direction = "up"
        else:
            direction = "stable"
    else:
        direction = "stable"

    return WeightStats(
        current_weight=current,
        start_weight=first,
        weight_change=change,
        avg_7days=avg7,
        min_weight=min(all_weights),
        max_weight=max(all_weights),
        bmi=calc_bmi(current, settings.height_cm),
        days_tracked=len(records),
        trend_direction=direction,
    )


@router.get("/{record_id}", response_model=WeightResponse)
def get_weight(record_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = db.get(WeightRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(404, "Record not found")
    return record


@router.put("/{record_id}", response_model=WeightResponse)
def update_weight(record_id: int, data: WeightUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = db.get(WeightRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(404, "Record not found")

    if data.weight_kg is not None:
        record.weight_kg = data.weight_kg
        settings = get_settings(db, user.id)
        record.bmi = calc_bmi(data.weight_kg, settings.height_cm)
    if data.body_fat_pct is not None:
        record.body_fat_pct = data.body_fat_pct
    if data.note is not None:
        record.note = data.note

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=204)
def delete_weight(record_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = db.get(WeightRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(404, "Record not found")
    db.delete(record)
    db.commit()
