from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class LessonsSummary(BaseModel):
    the_nearest_lesson: NearestLessonItem | None
    this_week_lessons_count: int

class PaymentSummary(BaseModel):
    income_dynamic: Decimal
    month_sum: Decimal
    revenue_forecast: Decimal

class DebtorStudentResponse(BaseModel):
    student_id: int
    student_name: str
    balance: Decimal
    days_since_last_lesson: Optional[int] = None
    date_of_last_study: Optional[date] = None
    urgency_level: str  # "HIGH" or "MEDIUM"

    model_config = ConfigDict(from_attributes=True)


class StudentsSummary(BaseModel):
    active_students_this_month: int
    active_students_last_month: int
    delta: int
    delta_pct: Optional[float] = None
    red_zone_students: int


class NearestLessonItem(BaseModel):
    id: int
    student_id: int
    topic: str
    date: datetime
    duration_minutes: int
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    students: StudentsSummary
    lessons: LessonsSummary
    income: PaymentSummary
    debtors: List[DebtorStudentResponse]

    model_config = ConfigDict(from_attributes=True)