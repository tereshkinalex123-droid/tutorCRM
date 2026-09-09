from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    login: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)

class UserResponse(UserBase):
    id: int
    balance: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True) #pydantic can read the data from sqlalchemy models