from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import User
from schemas.task import TaskCreate, TaskResponse, TaskUpdate
import cruds.tasks as crud

router = APIRouter()


@router.get("/", response_model=list[TaskResponse])
async def get_tasks(
    is_completed: Optional[bool] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_all_tasks(
        db, tutor_id=current_user.id, is_completed=is_completed
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await crud.get_task(db, task_id=task_id, tutor_id=current_user.id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await crud.create_task(db, task_in=task_in, tutor_id=current_user.id)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await crud.get_task(db, task_id=task_id, tutor_id=current_user.id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return await crud.update_task(db, task=task, task_in=task_in)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await crud.get_task(db, task_id=task_id, tutor_id=current_user.id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    await crud.delete_task(db, task=task)
    return None