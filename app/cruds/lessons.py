from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select, text
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Lesson, Student, StudentStatus
from ..schemas.lesson import LessonUpdate, LessonCreate


async def get_all_lessons(
    db: AsyncSession, tutor_id: int
) -> list[Lesson]:
    result = await db.execute(
        select(Lesson)
        .join(Student, Student.id == Lesson.student_id)
        .where(Student.tutor_id == tutor_id)
    )
    return list(result.scalars().all())

async def get_student_lessons(
    db: AsyncSession, tutor_id: int, student_id: int
):
    result = await db.execute(
        select(Lesson)
        .join(Student, Student.id == Lesson.student_id)
        .where(Student.tutor_id == tutor_id, Student.id == student_id)
    )

    return list(result.scalars().all())

async def get_lesson(
    db: AsyncSession, lesson_id: int, tutor_id: int
) -> Lesson | None:
    result = await db.execute(
        select(Lesson)
        .join(Student, Student.id == Lesson.student_id)
        .where(Lesson.id == lesson_id, Student.tutor_id == tutor_id)
    )
    return result.scalar_one_or_none()

from app.exceptions import LessonOverlapError, LessonTimeError, StudentNotFoundError
from ..cruds.students import get_student
from sqlalchemy.exc import IntegrityError
from services.students import change_student_data
from zoneinfo import ZoneInfo
from ..models import User

async def _flush_or_raise(db: AsyncSession) -> None:
    try:
        await db.flush()
    except IntegrityError as exc:
        msg = str(exc.orig)
        if "no_overlapping_lessons" in msg:
            raise LessonOverlapError() from exc
        if "lesson_end_after_start" in msg:
            raise LessonTimeError() from exc
        raise

async def create_lesson(db: AsyncSession, lesson_in: LessonCreate, tutor: User) -> Lesson:
    student = await get_student(db, student_id=lesson_in.student_id, tutor_id=tutor.id)
    if student is None:
        raise StudentNotFoundError(lesson_in.student_id)

    lesson = Lesson(**lesson_in.model_dump(), tutor_id=tutor.id)
    db.add(lesson)

    lesson_day = lesson_in.starts_at.astimezone(ZoneInfo(tutor.timezone)).date()
    changes = change_student_data(lesson_day, student.date_of_last_study, student.status)
    for key, val in changes.items():
        setattr(student, key, val)   # чтобы без коммита

    await _flush_or_raise(db)
    return lesson

async def update_lesson(db: AsyncSession, lesson: Lesson, lesson_in: LessonUpdate) -> Lesson:
    for key, val in lesson_in.model_dump(exclude_unset=True).items():
        setattr(lesson, key, val)

    if lesson.starts_at >= lesson.ends_at:      
        raise LessonTimeError()

    await _flush_or_raise(db)
    return lesson


async def delete_lesson(db: AsyncSession, lesson: Lesson) -> None:
    await db.delete(lesson)
    await db.commit()