from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CalendarLessonEvent(BaseModel):
    id: int
    title: str
    student_id: int
    student_name: str
    start: datetime
    end: datetime
    duration_minutes: int
    price: Decimal
    type: str  # student or lead
    status: str #SCHEDULED, COMPLETED, or CANCELED

    model_config = ConfigDict(from_attributes=True)


class CalendarTaskEvent(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    priority: str
    is_completed: bool

    model_config = ConfigDict(from_attributes=True)


class CalendarFeedResponse(BaseModel):
    lessons: List[CalendarLessonEvent] = []
    tasks: List[CalendarTaskEvent] = []

    model_config = ConfigDict(from_attributes=True)