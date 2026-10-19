from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from auth import get_current_user
from database import get_db
from models import User
from schemas.student import (
    StudentResponse,
    StudentCreate,
    StudentDetailResponse,
    StudentUpdate,
)
import cruds.students as crud

router = APIRouter()


@router.get("/", response_model=List[StudentResponse])
async def get_students(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_students(db, tutor_id=current_user.id)


@router.get("/{student_id}", response_model=StudentDetailResponse)
async def get_student(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    student = await crud.get_student(
        db, student_id=student_id, tutor_id=current_user.id
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    return student


@router.post(
    "/{user_id}/student",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_student(
    student_in: StudentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.create_student(
        db, student_in=student_in, tutor_id=current_user.id
    )


@router.patch("/{user_id}/student", response_model=StudentResponse)
async def update_student(
    student_id: int,
    student_in: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    student = await crud.get_student(
        db, student_id=student_id, tutor_id=current_user.id
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    return await crud.update_student(db, student=student, student_in=student_in)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    student = await crud.get_student(
        db, student_id=student_id, tutor_id=current_user.id
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    await crud.delete_student(db, student=student)
    return None