"""Food schemas"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FoodItem(BaseModel):
    name: str
    calories: int = 0
    portion: Optional[str] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None


class FoodCreate(BaseModel):
    meal_type: str = Field("snack", pattern="^(breakfast|lunch|dinner|snack)$")
    image_path: Optional[str] = None
    food_items: List[FoodItem] = []
    total_calories: int = 0
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    note: Optional[str] = Field(None, max_length=500)
    recorded_at: Optional[datetime] = None


class FoodUpdate(BaseModel):
    meal_type: Optional[str] = Field(None, pattern="^(breakfast|lunch|dinner|snack)$")
    food_items: Optional[List[FoodItem]] = None
    total_calories: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    note: Optional[str] = None


class FoodResponse(BaseModel):
    id: int
    meal_type: str
    image_path: Optional[str]
    food_items: List[FoodItem] = []
    total_calories: int
    protein_g: Optional[float]
    carbs_g: Optional[float]
    fat_g: Optional[float]
    note: Optional[str]
    recorded_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class AIAnalysisResult(BaseModel):
    image_path: Optional[str] = None
    food_items: List[FoodItem]
    total_calories: int
    total_protein: Optional[float] = None
    total_carbs: Optional[float] = None
    total_fat: Optional[float] = None
    analysis_note: Optional[str] = None


class DailyCalorieSummary(BaseModel):
    date: str
    total_calories: int
    breakfast: int = 0
    lunch: int = 0
    dinner: int = 0
    snack: int = 0
