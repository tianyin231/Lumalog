"""Food Record Model"""
from datetime import datetime
import json

from sqlalchemy import Integer, Float, ForeignKey, String, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FoodRecord(Base):
    __tablename__ = "food_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1, index=True)
    meal_type: Mapped[str] = mapped_column(
        String(20), default="snack"
    )  # breakfast | lunch | dinner | snack
    image_path: Mapped[str] = mapped_column(String(500), nullable=True)
    food_items_json: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string
    total_calories: Mapped[int] = mapped_column(Integer, default=0)
    protein_g: Mapped[float] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float] = mapped_column(Float, nullable=True)
    note: Mapped[str] = mapped_column(String(500), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    @property
    def food_items(self) -> list[dict]:
        """Parse food items from JSON string"""
        if self.food_items_json:
            try:
                return json.loads(self.food_items_json)
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    @food_items.setter
    def food_items(self, items: list[dict]):
        self.food_items_json = json.dumps(items, ensure_ascii=False)

    def __repr__(self):
        return f"<FoodRecord {self.meal_type} {self.total_calories}kcal>"
