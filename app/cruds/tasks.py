from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Task
from schemas.task import TaskCreate, TaskUpdate


async def get_all_tasks(
    db: AsyncSession, tutor_id: int, is_completed: Optional[bool] = None
) -> list[Task]:
    stmt = select(Task).where(Task.tutor_id == tutor_id)
    if is_completed is not None:
        stmt = stmt.where(Task.is_completed == is_completed)
    stmt = stmt.order_by(Task.date.asc().nulls_last())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_task(
    db: AsyncSession, task_id: int, tutor_id: int
) -> Task | None:
    stmt = select(Task).where(Task.id == task_id, Task.tutor_id == tutor_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_task(
    db: AsyncSession, task_in: TaskCreate, tutor_id: int
) -> Task:
    task = Task(**task_in.model_dump(), tutor_id=tutor_id)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(
    db: AsyncSession, task: Task, task_in: TaskUpdate
) -> Task:
    update_data = task_in.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(task, key, val)
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    await db.delete(task)
    await db.commit()