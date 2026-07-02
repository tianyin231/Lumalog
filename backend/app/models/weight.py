"""Weight Record Model"""
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WeightRecord(Base):
    __tablename__ = "weight_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1, index=True)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    bmi: Mapped[float] = mapped_column(Float, nullable=True)
    body_fat_pct: Mapped[float] = mapped_column(Float, nullable=True)
    note: Mapped[str] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual | import
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self):
        return f"<WeightRecord {self.weight_kg}kg @ {self.recorded_at}>"
