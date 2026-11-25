from datetime import datetime
from typing import List
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Lesson, Task
from ..schemas.calendar import CalendarLessonEvent, CalendarTaskEvent


async def get_calendar_events(
    db: AsyncSession,
    tutor_id: int,
    start_date: datetime,
    end_date: datetime,
) -> tuple[List[CalendarLessonEvent], List[CalendarTaskEvent]]:
    stmt_lessons = (
        select(Lesson)
        .options(selectinload(Lesson.student))
        .where(
            Lesson.tutor_id == tutor_id,
            Lesson.starts_at < end_date,
            Lesson.ends_at > start_date,
        )
        .order_by(Lesson.starts_at.asc())
    )
    result_lessons = await db.execute(stmt_lessons)
    raw_lessons = result_lessons.scalars().all()

    lesson_events = [
        CalendarLessonEvent(
            id=l.id,
            title=f"{l.topic} ({l.student.name})",
            student_id=l.student_id,
            student_name=l.student.name,
            start=l.starts_at,
            end=l.ends_at,
            duration_minutes=int((l.ends_at - l.starts_at).total_seconds() // 60),
            price=l.price,
            type=l.type.value,
            status=l.status,
        )
        for l in raw_lessons
    ]

    stmt_tasks = (
        select(Task)
        .where(
            Task.tutor_id == tutor_id,
            or_(
                (Task.date >= start_date) & (Task.date <= end_date),
                (Task.due_date >= start_date) & (Task.due_date <= end_date),
            ),
        )
        .order_by(Task.date.asc().nulls_last())
    )
    result_tasks = await db.execute(stmt_tasks)
    raw_tasks = result_tasks.scalars().all()

    task_events = [
        CalendarTaskEvent(
            id=t.id,
            title=t.title,
            description=t.description,
            date=t.date,
            due_date=t.due_date,
            priority=t.priority.value,
            is_completed=t.is_completed,
        )
        for t in raw_tasks
    ]

    return lesson_events, task_events