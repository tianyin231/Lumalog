"""Exercise Record Model"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Float, String, DateTime, JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExerciseRecord(Base):
    __tablename__ = "exercise_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1, index=True)
    exercise_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # walk | run | cycle | swim | gym | yoga | other
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    calories_burned: Mapped[int] = mapped_column(Integer, default=0)
    steps: Mapped[int] = mapped_column(Integer, nullable=True)
    distance_km: Mapped[float] = mapped_column(Float, nullable=True)
    avg_heart_rate: Mapped[int] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(
        String(30), default="manual"
    )  # manual | mi_fit | zepp
    source_id: Mapped[str] = mapped_column(String(100), nullable=True)  # external ID
    note: Mapped[str] = mapped_column(String(500), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self):
        return f"<ExerciseRecord {self.exercise_type} {self.calories_burned}kcal>"


class ExerciseActivityDetail(Base):
    __tablename__ = "exercise_activity_details"
    __table_args__ = (UniqueConstraint("user_id", "source", "source_id", name="uq_exercise_detail_user_source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1, index=True)
    exercise_record_id: Mapped[int] = mapped_column(ForeignKey("exercise_records.id"), index=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    track_points_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    samples_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    raw_report_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    raw_detail_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    sport_report_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    recovery_rate_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
