from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_user
from app.database.db import get_db
from app.database.models import Task, TaskStatus
from app.schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=List[TaskOut])
def list_tasks(
    db: Session = Depends(get_db),
    _user=Depends(require_user),
    status: str | None = None,
) -> list[Task]:
    stmt = select(Task).order_by(Task.created_at.desc())
    if status:
        stmt = stmt.where(Task.status == TaskStatus(status))
    return list(db.execute(stmt).scalars().all())


@router.get("/due-reminders", response_model=List[TaskOut])
def due_reminders(
    db: Session = Depends(get_db),
    _user=Depends(require_user),
    within_seconds: int = 90,
) -> list[Task]:
    """Reminders the scheduler (app/scheduler.py) fired recently, i.e.
    last_notified_at is within the last `within_seconds`. The PWA polls
    this to show a notification (project spec section 31); the window
    just needs to comfortably exceed the scheduler's own poll interval
    so a client polling every few seconds never misses one."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=within_seconds)
    stmt = select(Task).where(Task.last_notified_at.is_not(None), Task.last_notified_at >= cutoff)
    return list(db.execute(stmt).scalars().all())


@router.post("", response_model=TaskOut)
def create_task(
    payload: TaskCreate, db: Session = Depends(get_db), _user=Depends(require_user)
) -> Task:
    task = Task(
        title=payload.title,
        description=payload.description,
        notes=payload.notes,
        priority=payload.priority,
        due_at=payload.due_at,
        reminder_enabled=payload.reminder_enabled and payload.due_at is not None,
        recurrence=payload.recurrence if payload.due_at is not None else "none",
    )
    task.tags = payload.tags
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_user),
) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(task, field, value)

    if data.get("status") == TaskStatus.completed and task.completed_at is None:
        task.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int, db: Session = Depends(get_db), _user=Depends(require_user)
) -> dict:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    db.delete(task)
    db.commit()
    return {"id": task_id, "deleted": True}
