from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from typing import List
from schemas import UserResponse

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/users", response_model=List[UserResponse])
async def get_all_users(
        db: Session=Depends(get_db)
):
    students = db.query(User).all()
    return students