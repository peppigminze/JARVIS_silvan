"""
Database models.

States (Message.status / used loosely for Task processing too):
    pending -> processing -> completed
                           -> failed
    (any state) -> cancelled
"""
from __future__ import annotations

import enum
import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base, ensure_columns


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MessageStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Message(Base):
    """A chat message sent by the user. Processed asynchronously by the
    local PC agent, which may run while the phone/client is offline."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Client-supplied idempotency key so the PWA offline-queue can retry
    # sends without creating duplicate messages.
    client_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus), default=MessageStatus.pending, nullable=False, index=True
    )
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.pending, nullable=False, index=True
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority), default=TaskPriority.medium, nullable=False
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# Deliberately a plain string (not a SQLAlchemy Enum/CHECK constraint) so
# a future addition to this list never requires a schema migration - see
# app/memory/store.py for how it's used/validated.
MEMORY_TYPES = ("fact", "preference", "project")
DEFAULT_MEMORY_TYPE = "fact"


class MemoryEntry(Base):
    """Long-term memory (project spec section 10). Short-term/conversation
    context is intentionally NOT stored here - it's just the recent
    Message rows for the active conversation, already available without
    a separate table. Only information JARVIS decides is durably
    relevant (a fact, a stated preference, project knowledge) lands
    here via the save_memory tool or the /api/memory endpoint.
    """

    __tablename__ = "memory_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # One of MEMORY_TYPES. Added via an additive migration (see
    # run_migrations() below) so existing memory_entries rows default
    # to "fact" instead of the insert failing or data being lost.
    memory_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DEFAULT_MEMORY_TYPE, server_default=DEFAULT_MEMORY_TYPE
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ActionStatus(str, enum.Enum):
    """Lifecycle of a CONFIRM_REQUIRED tool call the agent wants to run.

    awaiting_confirmation -> confirmed | rejected
    confirmed             -> executing -> completed | failed
    """

    awaiting_confirmation = "awaiting_confirmation"
    confirmed = "confirmed"
    rejected = "rejected"
    executing = "executing"
    completed = "completed"
    failed = "failed"


class PendingAction(Base):
    """A tool call the agent planned but must not run automatically
    (security = CONFIRM_REQUIRED, see app/tools/base.py). Created by the
    JARVIS Agent Core when it pauses mid-pipeline; resolved by the human
    user via /api/actions/{id}/confirm|reject, then picked up and
    executed by the local PC agent, which resumes the paused pipeline.

    This is a new table, so it carries no migration risk for existing
    databases - ActionStatus's CHECK constraint is created fresh.
    """

    __tablename__ = "pending_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id"), nullable=True, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    # JSON-encoded so we don't need a schema-per-tool table.
    arguments_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    # Prior tool observations from this pipeline run, so execution can
    # resume a multi-step plan exactly where it paused.
    observations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus), default=ActionStatus.awaiting_confirmation, nullable=False, index=True
    )
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def arguments(self) -> dict:
        return json.loads(self.arguments_json or "{}")

    @arguments.setter
    def arguments(self, value: dict) -> None:
        self.arguments_json = json.dumps(value or {})

    @property
    def observations(self) -> list:
        return json.loads(self.observations_json or "[]")

    @observations.setter
    def observations(self, value: list) -> None:
        self.observations_json = json.dumps(value or [])

    @property
    def result(self):
        return json.loads(self.result_json) if self.result_json else None

    @result.setter
    def result(self, value) -> None:
        self.result_json = json.dumps(value, default=str) if value is not None else None


class AgentHeartbeat(Base):
    """Single-row-per-agent table used to determine PC online/offline
    status. In V1 there is exactly one agent ("default")."""

    __tablename__ = "agent_heartbeats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String(64), unique=True, default="default")
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def run_migrations() -> None:
    """Additive, idempotent column migrations for tables that predate a
    field (see ensure_columns() in app/database/db.py). Called from
    init_db() after create_all(), so brand-new databases already have
    every column via the model definitions and this is a no-op for them.
    """
    ensure_columns(
        "memory_entries",
        {"memory_type": f"VARCHAR(32) NOT NULL DEFAULT '{DEFAULT_MEMORY_TYPE}'"},
    )
