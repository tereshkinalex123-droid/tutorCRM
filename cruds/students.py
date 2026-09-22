from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Student
from schemas import StudentCreate, StudentUpdate


async def get_students(db: AsyncSession, tutor_id: int) -> list[Student]:
    result = await db.execute(
        select(Student).where(Student.tutor_id == tutor_id)
    )
    return list(result.scalars().all())

async def get_student(
    db: AsyncSession, student_id: int, tutor_id: int
) -> Student | None:
    result = await db.execute(
        select(Student)
        .options(
            selectinload(Student.lessons),
            selectinload(Student.homeworks),
        )
        .where(Student.id == student_id, Student.tutor_id == tutor_id))
    return result.scalar_one_or_none()


async def create_student(
    db: AsyncSession, student_in: StudentCreate, tutor_id: int
) -> Student:
    new_student = Student(
        **student_in.model_dump(),
        tutor_id=tutor_id,
    )
    db.add(new_student)
    await db.commit()
    await db.refresh(new_student)
    return new_student


async def update_student(
    db: AsyncSession, student: Student, student_in: StudentUpdate
) -> Student:
    update_data = student_in.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(student, key, val)
    await db.commit()
    await db.refresh(student)
    return student


async def delete_student(db: AsyncSession, student: Student) -> None:
    await db.delete(student)
    await db.commit()