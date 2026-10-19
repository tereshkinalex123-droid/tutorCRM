from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from models import HomeworkStatus


class HomeworkBase(BaseModel):
    student_id: int
    lesson_id: Optional[int] = None
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: HomeworkStatus = HomeworkStatus.PENDING


class HomeworkCreate(HomeworkBase):
    pass


class HomeworkUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[HomeworkStatus] = None
    grade: Optional[int] = Field(None, ge=1, le=10)
    feedback: Optional[str] = None


class HomeworkResponse(HomeworkBase):
    id: int
    grade: Optional[int] = None
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
