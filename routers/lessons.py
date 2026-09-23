from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import User
from schemas import LessonCreate, LessonResponse, LessonUpdate
import cruds.lessons as crud

router = APIRouter()

@router.get("/", response_model=list[LessonResponse])
async def get_lessons(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_all_lessons(db, tutor_id=current_user.id)

@router.get("/student/{student_id}", response_model=list[LessonResponse])
async def get_student_lessons(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_student_lessons(
        db, tutor_id=current_user.id, student_id=student_id
    )

@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lesson = await crud.get_lesson(db, lesson_id=lesson_id, tutor_id=current_user.id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    return lesson


@router.post("/", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    lesson_in: LessonCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await crud.create_lesson(db, lesson_in=lesson_in, tutor_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.patch("/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: int,
    lesson_in: LessonUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lesson = await crud.get_lesson(db, lesson_id=lesson_id, tutor_id=current_user.id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    return await crud.update_lesson(db, lesson=lesson, lesson_in=lesson_in)


@router.delete("/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lesson = await crud.get_lesson(db, lesson_id=lesson_id, tutor_id=current_user.id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    await crud.delete_lesson(db, lesson=lesson)
    return None