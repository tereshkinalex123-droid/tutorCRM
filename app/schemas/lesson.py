from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Self
from pydantic import BaseModel, ConfigDict, Field

from ..models import LessonType, LessonStatus
from zoneinfo import ZoneInfo
from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator

class LessonBase(BaseModel):
    student_id: int
    topic: str = Field(..., min_length=2, max_length=255)
    type: LessonType = LessonType.STUDENT
    status: LessonStatus = LessonStatus.SCHEDULED
    price: Decimal = Field(Decimal("0.00"), ge=0)

class LessonCreate(LessonBase):
    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode="after")
    def check_order(self) -> Self:
        if self.starts_at >= self.ends_at:
            raise ValueError("starts_at должно быть строго меньше ends_at")
        return self


class LessonUpdate(BaseModel):
    starts_at: Optional[AwareDatetime] = None
    ends_at: Optional[AwareDatetime] = None
    topic: Optional[str] = Field(None, min_length=2, max_length=255)
    type: Optional[LessonType] = None
    status: Optional[LessonStatus] = None
    price: Optional[Decimal] = Field(None, ge=0)

class LessonResponse(LessonBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tutor_id: int
    starts_at: datetime
    ends_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, lesson: Lesson, tz_name: str) -> Self:
        tz = ZoneInfo(tz_name)
        obj = cls.model_validate(lesson)
        return obj.model_copy(update={
            "starts_at": obj.starts_at.astimezone(tz),
            "ends_at": obj.ends_at.astimezone(tz),
        })