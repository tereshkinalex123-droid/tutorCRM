from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from models import StudentStatus, StudentTag, HomeworkStatus, TimeCategory, TaskPriority

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserWithToken(BaseModel):
    user: UserResponse
    token: Token

class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    login: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)

class UserResponse(UserBase):
    id: int
    balance: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True) #pydantic can read the data from sqlalchemy models


class LessonBase(BaseModel):
    student_id: int = Field(..., )
    date: datetime = Field(...,  )
    duration_minutes: int = Field(60, gt=0, le=480)
    topic: str = Field(..., min_length=2, max_length=255)

    price: Decimal = Field(Decimal("0.00"), ge=0)
    is_paid: bool = Field(False, description="Has the tutor received payment?")

    grade: Optional[int] = Field(None, ge=1, le=10)

class LessonCreate(LessonBase):
    pass

class LessonUpdate(BaseModel):
    date: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, gt=0, le=480)
    topic: Optional[str] = Field(None, min_length=2, max_length=255)
    price: Optional[Decimal] = Field(None, ge=0)
    is_paid: Optional[bool] = None
    grade: Optional[int] = Field(None, ge=1, le=10)


class LessonResponse(LessonBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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


class StudentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    contacts: Optional[str] = Field(None, max_length=255)
    subject: Optional[str] = Field(None, max_length=100)
    problems: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)
    status: StudentStatus = StudentStatus.IN_TRIAL
    tag: StudentTag = Field(None)

class StudentCreate(StudentBase):
    date_of_join: date = Field(default_factory=date.today)

class StudentUpdate(StudentBase):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    absences: Optional[int] = Field(None, ge=0)

class StudentResponse(StudentBase):
    id: int
    tutor_id: int
    absences: int
    date_of_join: date
    date_of_last_study: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class StudentDetailResponse(StudentResponse):
    lessons: List["LessonResponse"] = []
    homeworks: List["HomeworkResponse"] = []



class TimeEntryBase(BaseModel):
    category: TimeCategory = TimeCategory.LESSON
    duration_minutes: int
    logged_date: date = Field(default_factory=date.today)

class TimeEntryCreate(TimeEntryBase):
    logged_date: datetime

class TimeEntryUpdate(BaseModel):
    category: Optional[TimeCategory] = None
    duration_minutes: Optional[int] = Field(None, gt=0, le=1440)
    logged_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=500)

class TimeEntryResponse(TimeEntryBase):
    id: int
    tutor_id: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime



class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[date] = None
    is_completed: bool = False

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[date] = None
    is_completed: Optional[bool] = None

class TaskResponse(TaskBase):
    id: int
    tutor_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)