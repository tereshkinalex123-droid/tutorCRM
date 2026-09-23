from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Lesson, Student, StudentStatus
from schemas import LessonCreate, LessonUpdate


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
    db: AsyncSession, lesson_in: LessonCreate, tutor_id: int
) -> Lesson:
    # ensure the student belongs to this tutor
    student = await db.execute(
        select(Student).where(
            Student.id == lesson_in.student_id,
            Student.tutor_id == tutor_id,
        )
    )
    student = student.scalar_one_or_none()
    if student is None:
        raise ValueError("Student not found for this tutor")

    lesson = Lesson(**lesson_in.model_dump())
    db.add(lesson)

    # keep the cache in sync
    lesson_day = lesson.date.date()
    if (
        student.date_of_last_study is None
        or lesson_day > student.date_of_last_study
    ):
        student.date_of_last_study = lesson_day

    # revive inactive students
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