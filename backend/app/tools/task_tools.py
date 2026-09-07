from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Task, TaskPriority, TaskStatus, utcnow
from app.tools.base import Tool, ToolResult, ToolSecurity


class CreateTaskTool(Tool):
    name = "create_task"
    description = "Create a new task/todo item, optionally with a due date and priority."
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            "due_at": {"type": "string", "format": "date-time"},
        },
        "required": ["title"],
    }
    security = ToolSecurity.SAFE

    async def execute(self, db: Session, title: str, description: str | None = None,
                       priority: str = "medium", due_at: str | None = None, **_) -> ToolResult:
        try:
            due_dt = datetime.fromisoformat(due_at) if due_at else None
            task = Task(
                title=title,
                description=description,
                priority=TaskPriority(priority) if priority else TaskPriority.medium,
                due_at=due_dt,
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return ToolResult(success=True, data={"id": task.id, "title": task.title})
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            return ToolResult(success=False, error=str(exc))


class ListTasksTool(Tool):
    name = "list_tasks"
    description = "List tasks, optionally filtered by status (pending/completed/cancelled)."
    parameters = {
        "type": "object",
        "properties": {"status": {"type": "string", "enum": ["pending", "completed", "cancelled"]}},
    }
    security = ToolSecurity.SAFE

    async def execute(self, db: Session, status: str | None = None, **_) -> ToolResult:
        stmt = select(Task).order_by(Task.created_at.desc())
        if status:
            stmt = stmt.where(Task.status == TaskStatus(status))
        tasks = db.execute(stmt).scalars().all()
        data = [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status.value,
                "priority": t.priority.value,
                "due_at": t.due_at.isoformat() if t.due_at else None,
            }
            for t in tasks
        ]
        return ToolResult(success=True, data=data)


class CompleteTaskTool(Tool):
    name = "complete_task"
    description = "Mark a task as completed by its id."
    parameters = {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}
    security = ToolSecurity.SAFE

    async def execute(self, db: Session, task_id: int, **_) -> ToolResult:
        task = db.get(Task, task_id)
        if task is None:
            return ToolResult(success=False, error=f"Task {task_id} not found.")
        task.status = TaskStatus.completed
        task.completed_at = utcnow()
        db.commit()
        return ToolResult(success=True, data={"id": task.id, "status": task.status.value})


class DeleteTaskTool(Tool):
    name = "delete_task"
    description = "Delete a task by its id."
    parameters = {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}
    # Destructive - the agent may never run this automatically (see
    # project spec section 14). The human user can still delete tasks
    # directly through the authenticated REST endpoint / UI; this only
    # blocks the LLM-driven autonomous tool call until a confirmation
    # UI exists (see project spec section 30/14).
    security = ToolSecurity.CONFIRM_REQUIRED

    async def execute(self, db: Session, task_id: int, **_) -> ToolResult:
        task = db.get(Task, task_id)
        if task is None:
            return ToolResult(success=False, error=f"Task {task_id} not found.")
        db.delete(task)
        db.commit()
        return ToolResult(success=True, data={"id": task_id, "deleted": True})
