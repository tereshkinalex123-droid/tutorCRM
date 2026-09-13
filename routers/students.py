from schemas import UserWithToken, Token, UserCreate
from fastapi import APIRouter, Depends, HTTPException, status
from auth import authenticate_user, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from database import get_db
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Annotated, List
from fastapi.security import OAuth2PasswordRequestForm
from models import Student, User
from schemas import StudentResponse, StudentCreate, StudentDetailResponse, StudentUpdate

router = APIRouter()

@router.get("/", response_model=List[StudentResponse])
async def get_students(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)):

    students = db.query(Student).filter(Student.tutor_id == current_user.id).all()

    return students

@router.get("/{student_id}", response_model=StudentDetailResponse)
async def get_student(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)):

    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == current_user.id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    return student

@router.post("{user_id}/student", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    student_in: StudentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)):

    new_student = Student(
        **student_in.model_dump(),
        tutor_id=current_user.id
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return new_student

@router.patch("{user_id}/student", response_model=StudentResponse)
async def update_student(
        student_id: int,
        student_in: StudentUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)):

    student = (
        db.query(Student)
        .filter(Student.id == student_id, Student.tutor_id == current_user.id)
        .first()
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    update_data = student_in.model_dump()
    for key, val in update_data.items():
        setattr(student, key, val)
    db.commit()
    db.refresh(student)

    return student

@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    student = (
        db.query(Student)
        .filter(Student.id == student_id, Student.tutor_id == current_user.id)
        .first()
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    db.delete(student)
    db.commit()
    return None
