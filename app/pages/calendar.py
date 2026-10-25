# app/pages/calendar.py (or app/routers/calendar.py)
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import User
from schemas.calendar import CalendarFeedResponse
import cruds.calendar as crud

router = APIRouter()


@router.get("", response_model=CalendarFeedResponse)
async def get_calendar_feed(
    start: Optional[datetime] = Query(None, description="Start date (ISO format, e.g., YYYY-MM-DDT00:00:00Z)"),
    end: Optional[datetime] = Query(None, description="End date (ISO format, e.g., YYYY-MM-DDT00:00:00Z)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    # 1. Graceful fallback if omitted/None
    if not start:
        start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    elif start.tzinfo is None:
        # If user passed a naive datetime like "2026-10-10", attach UTC:
        start = start.replace(tzinfo=timezone.utc)

    if not end:
        # End of current month
        if start.month == 12:
            end = datetime(start.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(start.year, start.month + 1, 1, tzinfo=timezone.utc)
    elif end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    # 2. Validation: logical range check
    if end <= start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The 'end' date must be strictly after the 'start' date.",
        )

    # 3. Prevent massive queries (e.g. asking for 10 years at once)
    max_range = timedelta(days=93)  # Max ~3 months
    if (end - start) > max_range:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 93 days (3 months).",
        )

    # 4. Fetch the events from CRUD
    lessons, tasks = await crud.get_calendar_events(
        db, tutor_id=current_user.id, start_date=start, end_date=end
    )

    # 5. Return the validated schema (Fixes the ResponseValidationError!)
    return CalendarFeedResponse(
        lessons=lessons,
        tasks=tasks,
    )