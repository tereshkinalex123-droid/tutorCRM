from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, distinct, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import Student, Lesson, StudentStatus, Income
from decimal import Decimal

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


@router.get("/students")
async def get_students_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_students_dashboard(db, tutor_id=current_user.id)

from schemas import LessonsSummary, IncomeSummary

async def get_the_nearest_lesson(
    db: AsyncSession,
    tutor_id: int,
    now: datetime | None = None,
) -> Lesson | None:
    if now is None:
        now = datetime.now(timezone.utc)

    stmt = (
        select(Lesson)
        .where(Lesson.tutor_id == tutor_id, Lesson.date >= now)
        .order_by(Lesson.date)
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def week_bounds(now: datetime) -> tuple[datetime, datetime]:
    start = now - timedelta(days=now.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return start, end


async def get_this_week_lessons(
    db: AsyncSession,
    tutor_id: int,
    now: datetime | None = None,
) -> int:
    if now is None:
        now = datetime.now(timezone.utc)

    start, end = week_bounds(now)
    stmt = (
        select(func.count())
        .select_from(Lesson)
        .where(
            Lesson.tutor_id == tutor_id,
            Lesson.date >= start,
            Lesson.date < end,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one()


@router.get("/lessons", response_model=LessonsSummary)
async def get_lessons_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    nearest = await get_the_nearest_lesson(db, tutor_id=current_user.id, now=now)
    this_week = await get_this_week_lessons(db, tutor_id=current_user.id, now=now)

    return LessonsSummary(
        the_nearest_lesson=nearest,
        this_week_lessons=this_week,
    )

async def get_dynamic_dashboard():
    pass

async def get_month_sum(
    db: AsyncSession,
    tutor_id: int
) -> Decimal:
    now = datetime.now(timezone.utc)  # or now

    cur_start, cur_end = month_bounds(now.year, now.month)

    stmt = (select(func.coalesce(func.sum(Income.price), Decimal("0.00")))
    .where(Income.tutor_id == tutor_id)
    .where(Income.paid_date >= cur_start, Income.paid_date < cur_end))

    return (await db.execute(stmt)).scalar_one()

async def get_income_dynamic(
    db: AsyncSession,
    tutor_id: int
) -> Decimal:
    now = datetime.now(timezone.utc)  # or now

    cur_start, cur_end = month_bounds(now.year, now.month)
    p_year, p_month = prev_month(now.year, now.month)
    prev_start, prev_end = month_bounds(p_year, p_month)


    stmt1 = (select(func.coalesce(func.sum(Income.price), Decimal("0.00")))
            .where(Income.tutor_id == tutor_id)
            .where(Income.paid_date >= prev_start, Income.paid_date < prev_end))

    stmt2 = (select(func.coalesce(func.sum(Income.price), Decimal("0.00")))
            .where(Income.tutor_id == tutor_id)
            .where(Income.paid_date >= cur_start, Income.paid_date < cur_end))

    res1 = await db.execute(stmt1)
    prev_income = res1.scalar_one()
    res2 = await db.execute(stmt2)
    cur_income = res2.scalar_one()
    return cur_income - prev_income


@router.get("/incomes", response_model=IncomeSummary)
async def get_income_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    income_dynamic = await get_income_dynamic(db, tutor_id=current_user.id)
    month_sum = await get_month_sum(db, tutor_id=current_user.id)

    return {
        "income_dynamic": income_dynamic,
        "month_sum": month_sum,
    }
