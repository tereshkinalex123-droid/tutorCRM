from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Tuple
from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Lesson, Payment, PaymentStatus, Student, StudentStatus


RED_ZONE_AFTER_DAYS = 14


def month_bounds(year: int, month: int) -> Tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = (
        datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    )
    return start, end


def prev_month(year: int, month: int) -> Tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def week_bounds(now: datetime) -> Tuple[datetime, datetime]:
    start = now - timedelta(days=now.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return start, end


async def get_students_summary(db: AsyncSession, tutor_id: int, now: datetime) -> Dict[str, Any]:
    cur_start, cur_end = month_bounds(now.year, now.month)
    p_year, p_month = prev_month(now.year, now.month)
    prev_start, prev_end = month_bounds(p_year, p_month)

    stmt_curr = (
        select(func.count(distinct(Lesson.student_id)))
        .join(Student, Student.id == Lesson.student_id)
        .where(Student.tutor_id == tutor_id, Lesson.date >= cur_start, Lesson.date < cur_end)
    )
    current = (await db.execute(stmt_curr)).scalar_one()

    stmt_prev = (
        select(func.count(distinct(Lesson.student_id)))
        .join(Student, Student.id == Lesson.student_id)
        .where(Student.tutor_id == tutor_id, Lesson.date >= prev_start, Lesson.date < prev_end)
    )
    previous = (await db.execute(stmt_prev)).scalar_one()

    delta = current - previous
    delta_pct = round((delta / previous) * 100, 1) if previous else None

    # Red zone calculation
    cutoff = (now - timedelta(days=RED_ZONE_AFTER_DAYS)).date()
    red_stmt = (
        select(func.count(Student.id))
        .where(
            Student.tutor_id == tutor_id,
            Student.status == StudentStatus.ACTIVE,
            Student.date_of_last_study.is_not(None),
            Student.date_of_last_study < cutoff,
        )
    )
    red_zone = (await db.execute(red_stmt)).scalar_one()

    return {
        "active_students_this_month": current,
        "active_students_last_month": previous,
        "delta": delta,
        "delta_pct": delta_pct,
        "red_zone_students": red_zone,
    }


async def get_lessons_summary(db: AsyncSession, tutor_id: int, now: datetime) -> Dict[str, Any]:
    stmt_nearest = (
        select(Lesson)
        .where(Lesson.tutor_id == tutor_id, Lesson.date >= now)
        .order_by(Lesson.date.asc())
        .limit(1)
    )
    nearest = (await db.execute(stmt_nearest)).scalar_one_or_none()

    start, end = week_bounds(now)
    stmt_week = (
        select(func.count())
        .select_from(Lesson)
        .where(Lesson.tutor_id == tutor_id, Lesson.date >= start, Lesson.date < end)
    )
    this_week = (await db.execute(stmt_week)).scalar_one()

    return {
        "the_nearest_lesson": nearest,
        "this_week_lessons_count": this_week,
    }


async def get_income_summary(db: AsyncSession, tutor_id: int, now: datetime) -> Dict[str, Any]:
    cur_start, cur_end = month_bounds(now.year, now.month)
    p_year, p_month = prev_month(now.year, now.month)
    prev_start, prev_end = month_bounds(p_year, p_month)

    stmt_cur = (
        select(func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
        .where(
            Payment.tutor_id == tutor_id,
            Payment.status == PaymentStatus.PAID,
            Payment.paid_date >= cur_start,
            Payment.paid_date < cur_end,
        )
    )
    cur_income = (await db.execute(stmt_cur)).scalar_one()

    stmt_prev = (
        select(func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
        .where(
            Payment.tutor_id == tutor_id,
            Payment.status == PaymentStatus.PAID,
            Payment.paid_date >= prev_start,
            Payment.paid_date < prev_end,
        )
    )
    prev_income = (await db.execute(stmt_prev)).scalar_one()

    stmt_forecast = (
        select(func.coalesce(func.sum(Lesson.price), Decimal("0.00")))
        .where(
            Lesson.tutor_id == tutor_id,
            Lesson.date >= now,
            Lesson.date < cur_end,
        )
    )
    forecast = (await db.execute(stmt_forecast)).scalar_one()

    return {
        "month_sum": cur_income,
        "income_dynamic": cur_income - prev_income,
        "revenue_forecast": forecast,
    }


async def get_debtors_summary(
    db: AsyncSession,
    tutor_id: int,
    overdue_days_threshold: int,
    debt_threshold: Decimal,
) -> List[Dict[str, Any]]:
    today = date.today()
    cutoff_date = today - timedelta(days=overdue_days_threshold)
    neg_threshold = -abs(debt_threshold)
    high_urgency = neg_threshold * Decimal("1.5")

    stmt = (
        select(Student)
        .where(
            Student.tutor_id == tutor_id,
            Student.status == StudentStatus.ACTIVE,
            or_(
                (Student.balance < Decimal("0.00")) & (Student.date_of_last_study <= cutoff_date),
                Student.balance <= neg_threshold,
            ),
        )
        .order_by(Student.balance.asc())
    )
    students = (await db.execute(stmt)).scalars().all()

    debtors = []
    for s in students:
        days_passed = (today - s.date_of_last_study).days if s.date_of_last_study else None
        urgency = "HIGH" if ((days_passed and days_passed > overdue_days_threshold * 2) or s.balance <= high_urgency) else "MEDIUM"

        debtors.append({
            "student_id": s.id,
            "student_name": s.name,
            "balance": s.balance,
            "days_since_last_lesson": days_passed,
            "date_of_last_study": s.date_of_last_study,
            "urgency_level": urgency,
        })
    return debtors