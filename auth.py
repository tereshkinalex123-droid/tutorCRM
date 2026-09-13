from datetime import datetime, timedelta, timezone
from typing import Annotated
import os
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from database import get_db
from models import User

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "temporary_secret_key_change_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") #dependency that extracts the raw jwt token from the request's header

password_hash = PasswordHash.recommended()




# Helpers
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def get_user(db: Session, login: str) -> User | None:
    return db.query(User).filter(User.login == login).first()


def authenticate_user(db: Session, login: str, password: str) -> User | None:
    user = get_user(db, login)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(login: str, expires_delta: timedelta | None = None) -> str:
    to_encode = {"sub": login}
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Dependency for security
def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)],
        db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        login: str | None = payload.get("sub")
        if login is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    user = get_user(db, login)
    if user is None:
        raise credentials_exception
    return user
