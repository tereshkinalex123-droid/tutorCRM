from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, distinct, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import Student, Lesson, StudentStatus

RED_ZONE_AFTER_DAYS = 14
INACTIVE_AFTER_DAYS = 30

def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = (
        datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    )
    return start, end


def prev_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


async def count_active_in_range(
    db: AsyncSession,
    tutor_id: int,
    start: datetime,
    end: datetime,
) -> int:
    stmt = (
        select(func.count(distinct(Lesson.student_id)))
        .join(Student, Student.id == Lesson.student_id)
        .where(Student.tutor_id == tutor_id)
        .where(Lesson.date >= start)
        .where(Lesson.date < end)
    )
    return (await db.execute(stmt)).scalar_one()

async def count_red_zone(
    db: AsyncSession,
    tutor_id: int,
    now: datetime
) -> int:
    cutoff = (now - timedelta(days=RED_ZONE_AFTER_DAYS)).date()
    red_zone_stmt = (
        select(func.count(Student.id))
        .where(Student.tutor_id == tutor_id)
        .where(Student.status == StudentStatus.ACTIVE)
        .where(Student.date_of_last_study.is_not(None))
        .where(Student.date_of_last_study < cutoff)
    )
    return (await db.execute(red_zone_stmt)).scalar_one()


async def get_students_dashboard(
    db: AsyncSession,
    tutor_id: int,
) -> dict:
    now = datetime.now(timezone.utc) # or now

    cur_start, cur_end = month_bounds(now.year, now.month)
    p_year, p_month = prev_month(now.year, now.month)
    prev_start, prev_end = month_bounds(p_year, p_month)

    current = await count_active_in_range(db, tutor_id, cur_start, cur_end)
    previous = await count_active_in_range(db, tutor_id, prev_start, prev_end)

    delta = current - previous
    delta_pct = round((delta / previous) * 100, 1) if previous else None

    red_zone = await count_red_zone(db, tutor_id, now)

    return {
        "active_students_this_month": current,
        "active_students_last_month": previous,
        "delta": delta,
        "delta_pct": delta_pct,
        "red_zone_students": red_zone,
    }

# optionally for celery
async def mark_inactive_students(db: AsyncSession, tutor_id: int) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=INACTIVE_AFTER_DAYS)).date()

    stmt = (
        update(Student)
        .where(Student.tutor_id == tutor_id)
        .where(Student.status == StudentStatus.ACTIVE)
        .where(Student.date_of_last_study.is_not(None))
        .where(Student.date_of_last_study < cutoff)
        .values(status=StudentStatus.ARCHIVED)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount

from auth import get_current_user
from database import get_db
from models import User
from fastapi import APIRouter, Depends


router = APIRouter()


@router.get("/")
async def get_students(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_students_dashboard(db, tutor_id=current_user.id)



async def get_income_dashboard():
    #define how to connect real payment system to database models
    pass

async def get_classes_dashboard():
    pass

async def get_dynamic_dashboard():
    pass
