from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User, Student
from typing import List
from schemas import UserResponse, StudentResponse
from auth import get_current_user
from routers.auth import router as auth_router
from routers.students import router as students_router

app = FastAPI()
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(students_router, prefix="/students", tags=["students"])

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/users", response_model=List[UserResponse])
async def get_all_users(
        db: Session=Depends(get_db)
):
    students = db.query(User).all()
    return students

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    return user



@app.get("{user_id}/students", response_model=List[StudentResponse])
async def get_students(
    user_id: int,
    db: Session = Depends(get_db)):
    students = db.query(Student).filter(Student.tutor_id == user_id).all()
    return students

@app.get("/items/")
async def read_items(current_user: User = Depends(get_current_user)):
    return {"username" : current_user.name}

