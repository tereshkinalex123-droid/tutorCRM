from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from models import PaymentStatus, PaymentMethod


class PaymentBase(BaseModel):
    student_id: int
    paid_date: datetime = Field(..., description="Format: YYYY-MM-DD HH:MM (e.g., 2026-10-01 15:30)")
    amount: Decimal = Field(Decimal("0.00"), ge=0)
    status: PaymentStatus = PaymentStatus.PENDING
    method: PaymentMethod = PaymentMethod.CASH
    stripe_session_id: Optional[str] = Field(None, min_length=2, max_length=255)

class PaymentCreate(PaymentBase):
    @field_validator("paid_date", mode="before")
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

class PaymentUpdate(BaseModel):
    paid_date: Optional[datetime] = Field(None, description="Format: YYYY-MM-DD HH:MM (e.g., 2026-10-01 15:30)")
    amount: Optional[Decimal] = None
    status: Optional[PaymentStatus] = None
    method: Optional[PaymentMethod] = None
    stripe_session_id: Optional[str] = Field(None, min_length=2, max_length=255)

class PaymentResponse(PaymentBase):
    id: int
    tutor_id: int
    student_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("paid_date")
    def format_date(self, dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M")

class PaymentLinkResponse(BaseModel):
    checkout_url: str
    session_id: str
    amount: Decimal
