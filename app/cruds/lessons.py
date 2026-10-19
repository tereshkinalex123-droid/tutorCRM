from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Lesson, Student, StudentStatus
from schemas.lesson import LessonUpdate, LessonCreate
from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select, text


async def get_all_lessons(
    db: AsyncSession, tutor_id: int
) -> list[Lesson]:
    result = await db.execute(
        select(Lesson)
        .join(Student, Student.id == Lesson.student_id)
        .where(Student.tutor_id == tutor_id)
        .order_by(Lesson.date.desc())
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


async def create_lesson(
    db: AsyncSession,
    lesson_in: LessonCreate,
    tutor_id: int
) -> Lesson:

    stmt_student = select(Student).where(
        Student.id == lesson_in.student_id,
        Student.tutor_id == tutor_id,
    )
    res_student = await db.execute(stmt_student)
    student = res_student.scalar_one_or_none()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found for this tutor"
        )

    new_start = lesson_in.date
    new_end = lesson_in.date + timedelta(minutes=lesson_in.duration_minutes)

    existing_end = Lesson.date + (Lesson.duration_minutes * text("INTERVAL '1 minute'"))

    stmt_conflict = select(Lesson).where(
        Lesson.tutor_id == tutor_id,
        and_(
            Lesson.date < new_end,
            existing_end > new_start,
        )
    )
    res_conflict = await db.execute(stmt_conflict)
    conflict = res_conflict.scalar_one_or_none()

    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Scheduling conflict: You already have a lesson booked"
                   f" from {conflict.date.strftime('%H:%M')}"
                   f" to {(conflict.date + timedelta(minutes=conflict.duration_minutes)).strftime('%H:%M')}."
        )

    lesson = Lesson(**lesson_in.model_dump(), tutor_id=tutor_id)
    db.add(lesson)

    lesson_day = lesson.date.date()
    if student.date_of_last_study is None or lesson_day > student.date_of_last_study:
        student.date_of_last_study = lesson_day

    if student.status == StudentStatus.ARCHIVED:
        student.status = StudentStatus.ACTIVE

    await db.commit()
    await db.refresh(lesson)
    return lesson

async def update_lesson(
    db: AsyncSession, lesson: Lesson, lesson_in: LessonUpdate
) -> Lesson:
    update_data = lesson_in.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(lesson, key, val)
    await db.commit()
    await db.refresh(lesson)
    return lesson


async def delete_lesson(db: AsyncSession, lesson: Lesson) -> None:
    await db.delete(lesson)
    await db.commit()