"""Exercise schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ExerciseCreate(BaseModel):
    exercise_type: str = Field(..., pattern="^(walk|run|cycle|swim|gym|yoga|other)$")
    duration_minutes: int = Field(0, ge=0)
    calories_burned: int = Field(0, ge=0)
    steps: Optional[int] = None
    distance_km: Optional[float] = None
    avg_heart_rate: Optional[int] = None
    note: Optional[str] = Field(None, max_length=500)
    recorded_at: Optional[datetime] = None


class ExerciseResponse(BaseModel):
    id: int
    exercise_type: str
    duration_minutes: int
    calories_burned: int
    steps: Optional[int]
    distance_km: Optional[float]
    avg_heart_rate: Optional[int]
    source: str
    note: Optional[str]
    recorded_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class DailyExerciseSummary(BaseModel):
    date: str
    total_calories_burned: int
    total_steps: int
    total_duration_min: int
    activities: List[ExerciseResponse]
