"""User settings model."""
from datetime import datetime

from sqlalchemy import Integer, Float, ForeignKey, String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1, unique=True, index=True)
    # Profile
    nickname: Mapped[str] = mapped_column(String(50), default="我")
    height_cm: Mapped[float] = mapped_column(Float, default=170.0)
    gender: Mapped[str] = mapped_column(String(10), default="male")
    birth_year: Mapped[int] = mapped_column(Integer, default=1990)

    # Goals
    target_weight_kg: Mapped[float] = mapped_column(Float, default=65.0)
    weekly_loss_rate_kg: Mapped[float] = mapped_column(Float, default=0.5)
    daily_calorie_target: Mapped[int] = mapped_column(Integer, default=2000)

    # Theme
    theme_mode: Mapped[str] = mapped_column(
        String(20), default="auto"
    )  # light | dark | auto
    sunset_lat: Mapped[float] = mapped_column(Float, nullable=True)  # for sunset calc
    sunset_lng: Mapped[float] = mapped_column(Float, nullable=True)

    # Device integration
    mi_fit_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # OpenAI
    openai_api_key: Mapped[str] = mapped_column(String(200), nullable=True)
    openai_base_url: Mapped[str] = mapped_column(String(300), default="https://api.openai.com/v1")
    openai_model: Mapped[str] = mapped_column(String(50), default="gpt-4o")

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    def __repr__(self):
        return f"<UserSettings {self.nickname}>"
