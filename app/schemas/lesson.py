from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from models import LessonType


class LessonBase(BaseModel):
    student_id: int
    date: datetime = Field(..., description="Format: YYYY-MM-DD HH:MM (e.g., 2026-10-01 15:30)")
    duration_minutes: int = Field(60, gt=0, le=480)
    topic: str = Field(..., min_length=2, max_length=255)
    type: LessonType = LessonType.STUDENT
    price: Decimal = Field(Decimal("0.00"), ge=0)

class LessonCreate(LessonBase):
    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, value):
        if isinstance(value, str):
            clean_val = value.strip()
            try:
                dt = datetime.fromisoformat(clean_val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError as e:
                raise ValueError(f"Invalid date format: {e}. Example: '2026-10-01 15:30'")
        return value

class LessonUpdate(BaseModel):
    date: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, gt=0, le=480)
    topic: Optional[str] = Field(None, min_length=2, max_length=255)
    type: Optional[LessonType] = None
    price: Optional[Decimal] = Field(None, ge=0)

class LessonResponse(LessonBase):
    id: int
    tutor_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("date")
    def format_date(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M")