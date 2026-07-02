"""Settings schemas"""
from typing import Optional
from pydantic import BaseModel, Field


class SettingsUpdate(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50)
    height_cm: Optional[float] = Field(None, gt=50, lt=250)
    gender: Optional[str] = Field(None, pattern="^(male|female)$")
    birth_year: Optional[int] = Field(None, ge=1920, le=2020)
    target_weight_kg: Optional[float] = Field(None, gt=20, lt=300)
    weekly_loss_rate_kg: Optional[float] = Field(None, ge=0, le=5)
    daily_calorie_target: Optional[int] = Field(None, ge=500, le=10000)
    theme_mode: Optional[str] = Field(None, pattern="^(light|dark|auto)$")
    sunset_lat: Optional[float] = Field(None, ge=-90, le=90)
    sunset_lng: Optional[float] = Field(None, ge=-180, le=180)
    mi_fit_enabled: Optional[bool] = None
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = Field(None, max_length=300)
    openai_model: Optional[str] = None


class SettingsResponse(BaseModel):
    id: int
    nickname: str
    height_cm: float
    gender: str
    birth_year: int
    target_weight_kg: float
    weekly_loss_rate_kg: float
    daily_calorie_target: int
    theme_mode: str
    sunset_lat: Optional[float]
    sunset_lng: Optional[float]
    mi_fit_enabled: bool
    openai_base_url: str
    openai_model: str

    model_config = {"from_attributes": True}
