from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
)
from database import get_db
from schemas import Token, UserCreate, UserWithToken
import cruds.users as crud

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(login=user.login)
    return Token(access_token=access_token, token_type="bearer")


@router.post(
    "/register",
    response_model=UserWithToken,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserWithToken:
    existing = await crud.get_user_by_login(db, user.login)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that login already exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_user = await crud.create_user(
        db,
        login=user.login,
        name=user.name,
        hashed_password=get_password_hash(user.password),
    )

    access_token = create_access_token(login=new_user.login)

    return UserWithToken(
        user=new_user,
        token=Token(access_token=access_token, token_type="bearer"),
    )