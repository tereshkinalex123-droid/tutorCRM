from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import User
from config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

password_hash = PasswordHash.recommended()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return password_hash.hash(password)

async def get_user(db: AsyncSession, login: str) -> User | None:
    result = await db.execute(select(User).where(User.login == login))
    return result.scalar_one_or_none()

async def authenticate_user(
    db: AsyncSession, login: str, password: str
) -> User | None:
    user = await get_user(db, login)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(
    login: str
) -> str:
    to_encode = {"sub": login}
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=settings.algorithm)
        login: str | None = payload.get("sub")
        if login is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    user = await get_user(db, login)
    if user is None:
        raise credentials_exception
    return user