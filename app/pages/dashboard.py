import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import User
from schemas.dashboard import DashboardResponse
import cruds.dashboard as crud

router = APIRouter()


@router.get("", response_model=DashboardResponse)
async def get_complete_dashboard(
    debt_threshold: Decimal = Query(Decimal("100.00"), ge=0, description="Debt threshold for immediate alert"),
    overdue_days: int = Query(7, ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    students_data, lessons_data, income_data, debtors_data = await asyncio.gather(
        crud.get_students_summary(db, tutor_id=current_user.id, now=now),
        crud.get_lessons_summary(db, tutor_id=current_user.id, now=now),
        crud.get_income_summary(db, tutor_id=current_user.id, now=now),
        crud.get_debtors_summary(
            db,
            tutor_id=current_user.id,
            overdue_days_threshold=overdue_days,
            debt_threshold=debt_threshold,
        ),
    )

    return DashboardResponse(
        students=students_data,
        lessons=lessons_data,
        income=income_data,
        debtors=debtors_data,
    )