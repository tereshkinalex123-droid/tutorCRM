from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from models import StudentStatus, StudentTag
from .lesson import LessonResponse
from .homework import HomeworkResponse

class StudentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    contacts: Optional[str] = Field(None, max_length=255)
    subject: Optional[str] = Field(None, max_length=100)
    problems: Optional[str] = None
    notes: Optional[str] = None
    status: StudentStatus = StudentStatus.ACTIVE
    tag: StudentTag = StudentTag.INDIVIDUAL
    date_of_join: date = Field(default_factory=date.today)
    date_of_last_study: Optional[date] = None


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    contacts: Optional[str] = Field(None, max_length=255)
    subject: Optional[str] = Field(None, max_length=100)
    problems: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[StudentStatus] = None
    tag: Optional[StudentTag] = None
    date_of_join: Optional[date] = None
    date_of_last_study: Optional[date] = None


class StudentResponse(StudentBase):
    id: int
    tutor_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentDetailResponse(StudentResponse):
    lessons: List["LessonResponse"] = []
    homeworks: List["HomeworkResponse"] = []