"""Exercise Records API"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from app.models.exercise import ExerciseActivityDetail, ExerciseRecord
from app.models.user import User
from app.schemas.exercise import (
    ExerciseCreate, ExerciseResponse, DailyExerciseSummary,
)

router = APIRouter()


@router.post("/", response_model=ExerciseResponse, status_code=201)
def create_exercise(data: ExerciseCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = ExerciseRecord(
        user_id=user.id,
        exercise_type=data.exercise_type,
        duration_minutes=data.duration_minutes,
        calories_burned=data.calories_burned,
        steps=data.steps,
        distance_km=data.distance_km,
        avg_heart_rate=data.avg_heart_rate,
        note=data.note,
        source="manual",
        recorded_at=data.recorded_at or datetime.now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=list[ExerciseResponse])
def list_exercises(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    since = datetime.now() - timedelta(days=days)
    stmt = (
        select(ExerciseRecord)
        .where(ExerciseRecord.user_id == user.id, ExerciseRecord.recorded_at >= since)
        .order_by(desc(ExerciseRecord.recorded_at))
    )
    return db.execute(stmt).scalars().all()


@router.get("/summary/today", response_model=DailyExerciseSummary)
def get_today_summary(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Get today's exercise summary"""
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = (
        select(ExerciseRecord)
        .where(ExerciseRecord.user_id == user.id, ExerciseRecord.recorded_at >= today_start)
        .order_by(desc(ExerciseRecord.recorded_at))
    )
    records = db.execute(stmt).scalars().all()

    return DailyExerciseSummary(
        date=today_start.strftime("%Y-%m-%d"),
        total_calories_burned=sum(r.calories_burned for r in records),
        total_steps=sum(r.steps or 0 for r in records),
        total_duration_min=sum(r.duration_minutes for r in records),
        activities=[ExerciseResponse.model_validate(r) for r in records],
    )


@router.get("/{record_id}", response_model=ExerciseResponse)
def get_exercise(record_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = db.get(ExerciseRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(404, "Record not found")
    return record


@router.get("/{record_id}/detail")
def get_exercise_detail(record_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = db.get(ExerciseRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(404, "Record not found")

    detail = db.execute(
        select(ExerciseActivityDetail).where(
            ExerciseActivityDetail.user_id == user.id,
            ExerciseActivityDetail.exercise_record_id == record_id
        )
    ).scalar_one_or_none()
    if not detail:
        raise HTTPException(404, "Exercise detail not found")

    track_points = detail.track_points_json or []
    samples = detail.samples_json or []
    heart_rates = [
        value
        for value in [p.get("heart_rate") for p in track_points] + [s.get("heart_rate") for s in samples]
        if value
    ]
    speeds = [
        value * 3.6
        for value in [p.get("speed_mps") for p in track_points] + [s.get("speed_mps") for s in samples]
        if value is not None
    ]

    return {
        "record": ExerciseResponse.model_validate(record).model_dump(mode="json"),
        "track_points": track_points,
        "samples": samples,
        "raw_report": detail.raw_report_json,
        "sport_report": detail.sport_report_json,
        "recovery_rate": detail.recovery_rate_json,
        "summary": {
            "gps_points": len([p for p in track_points if p.get("latitude") and p.get("longitude")]),
            "sample_points": len(samples),
            "heart_rate_min": min(heart_rates) if heart_rates else None,
            "heart_rate_avg": round(sum(heart_rates) / len(heart_rates)) if heart_rates else None,
            "heart_rate_max": max(heart_rates) if heart_rates else None,
            "speed_max_kmh": round(max(speeds), 2) if speeds else None,
        },
    }


@router.delete("/{record_id}", status_code=204)
def delete_exercise(record_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    record = db.get(ExerciseRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(404, "Record not found")
    detail = db.execute(
        select(ExerciseActivityDetail).where(
            ExerciseActivityDetail.user_id == user.id,
            ExerciseActivityDetail.exercise_record_id == record_id
        )
    ).scalar_one_or_none()
    if detail:
        db.delete(detail)
    db.delete(record)
    db.commit()
