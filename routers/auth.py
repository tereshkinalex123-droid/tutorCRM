from schemas import UserWithToken, Token, UserCreate
from fastapi import APIRouter, Depends, HTTPException, status
from auth import authenticate_user, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_db
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from models import User


router = APIRouter()


@router.post("/token", response_model=Token)
def login(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        login=user.login,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return Token(access_token=access_token, token_type="bearer")

@router.post("/register", response_model=UserWithToken, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)) -> UserWithToken:
    if db.query(User).filter(User.login == user.login).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that login already exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    new_user = User(
        login=user.login,
        name=user.name,
        hashed_password=get_password_hash(user.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(
        login=new_user.login,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return UserWithToken(
        user=new_user,
        token=Token(access_token=access_token, token_type="bearer")
    )