from pydantic import BaseModel
from decimal import Decimal
from .lesson import LessonResponse

class LessonsSummary(BaseModel):
    the_nearest_lesson: LessonResponse | None
    this_week_lessons: int

class PaymentSummary(BaseModel):
    income_dynamic: Decimal
    month_sum: Decimal
    revenue_forecast: Decimal
