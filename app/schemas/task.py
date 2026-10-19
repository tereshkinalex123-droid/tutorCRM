from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from models import TaskPriority

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    date: Optional[datetime] = Field(None, description="Format: YYYY-MM-DD HH:MM (e.g., 2026-10-01 15:30)")
    is_completed: bool = False

class TaskCreate(TaskBase):
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
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    date: Optional[datetime] = None
    due_date: Optional[date] = None
    is_completed: Optional[bool] = None

class TaskResponse(TaskBase):
    id: int
    tutor_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("date")
    def format_date(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M")