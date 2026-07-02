"""Weight schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class WeightCreate(BaseModel):
    weight_kg: float = Field(..., gt=20, lt=300, description="体重(kg)")
    body_fat_pct: Optional[float] = Field(None, ge=1, le=60)
    note: Optional[str] = Field(None, max_length=500)
    recorded_at: Optional[datetime] = None


class WeightUpdate(BaseModel):
    weight_kg: Optional[float] = Field(None, gt=20, lt=300)
    body_fat_pct: Optional[float] = Field(None, ge=1, le=60)
    note: Optional[str] = Field(None, max_length=500)


class WeightResponse(BaseModel):
    id: int
    weight_kg: float
    bmi: Optional[float]
    body_fat_pct: Optional[float]
    note: Optional[str]
    source: str
    recorded_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class WeightStats(BaseModel):
    current_weight: Optional[float]
    start_weight: Optional[float]
    weight_change: Optional[float]
    avg_7days: Optional[float]
    min_weight: Optional[float]
    max_weight: Optional[float]
    bmi: Optional[float]
    days_tracked: int
    trend_direction: str  # "down" | "up" | "stable"


class WeightTrendPoint(BaseModel):
    date: str
    weight: float
    bmi: Optional[float]
    smoothed: Optional[float]
