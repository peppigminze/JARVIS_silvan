"""
Sync endpoints used exclusively by the local PC agent (agent/).

Flow (see project spec sections 3, 4, 14):
    GET  /api/sync/pending   - agent fetches pending messages
                                (server flips them to 'processing' so
                                a crashed/duplicate agent poll can't
                                grab the same message twice)
    POST /api/sync/complete  - agent reports a successful result
    POST /api/sync/fail      - agent reports a failure
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from sqlalchemy import or_

from app.auth import require_agent
from app.database.db import get_db
from app.database.models import ActionStatus, Message, MessageStatus, PendingAction
from app.schemas import (
    ActionCompleteRequest,
    ActionFailRequest,
    MessageOut,
    PendingActionCreate,
    PendingActionOut,
    SyncCompleteRequest,
    SyncFailRequest,
    SyncRetryRequest,
)

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.get("/pending", response_model=List[MessageOut])
def get_pending(
    db: Session = Depends(get_db),
    _agent=Depends(require_agent),
    limit: int = 10,
) -> list[Message]:
    """Atomically claim pending messages by flipping them to 'processing'.

    This prevents the sync worker from processing the same message
    twice if it polls again before finishing (simple locking, see
    project spec section 14).
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(Message)
        .where(
            Message.status == MessageStatus.pending,
            or_(Message.next_retry_at.is_(None), Message.next_retry_at <= now),
        )
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    messages = list(db.execute(stmt).scalars().all())
    for m in messages:
        m.status = MessageStatus.processing
    db.commit()
    for m in messages:
        db.refresh(m)
    return messages


@router.post("/complete", response_model=MessageOut)
def complete_message(
    payload: SyncCompleteRequest,
    db: Session = Depends(get_db),
    _agent=Depends(require_agent),
) -> Message:
    message = db.get(Message, payload.message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    message.response = payload.response
    message.status = MessageStatus.completed
    message.error = None
    message.processed_by = payload.processed_by
    message.observations = payload.observations
    message.processed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return message


@router.post("/retry", response_model=MessageOut)
def retry_message(
    payload: SyncRetryRequest,
    db: Session = Depends(get_db),
    _agent=Depends(require_agent),
) -> Message:
    """Requeue a message after a transient failure (e.g. the local LLM
    was unreachable) instead of failing it permanently - see
    agent/sync_worker.py for the retry-vs-give-up decision and
    MESSAGE_MAX_RETRIES/MESSAGE_RETRY_BACKOFF_SECONDS in app/config.py."""
    message = db.get(Message, payload.message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    message.status = MessageStatus.pending
    message.retry_count = payload.retry_count
    message.next_retry_at = payload.next_retry_at
    message.error = payload.error
    db.commit()
    db.refresh(message)
    return message


@router.post("/fail", response_model=MessageOut)
def fail_message(
    payload: SyncFailRequest,
    db: Session = Depends(get_db),
    _agent=Depends(require_agent),
) -> Message:
    message = db.get(Message, payload.message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found.")
    message.status = MessageStatus.failed
    message.error = payload.error
    message.processed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return message


# ---------------------------------------------------------------- Confirmed actions
#
# The confirmation flow (see api/actions.py + project spec section 14):
#   agent pauses a pipeline on a CONFIRM_REQUIRED tool
#       -> POST /api/sync/actions            (create, still processing the message)
#   human confirms via the PWA               -> api/actions.py::confirm_action
#   agent claims the confirmed action here    -> GET  /api/sync/confirmed-actions
#   agent executes the tool locally, resumes the paused pipeline, then:
#       -> POST /api/sync/actions/{id}/complete   (tool ran, pipeline may still continue)
#       -> POST /api/sync/actions/{id}/fail       (tool execution raised)


@router.post("/actions", response_model=PendingActionOut)
def create_pending_action(
    payload: PendingActionCreate,
    db: Session = Depends(get_db),
    _agent=Depends(require_agent),
) -> PendingAction:
    """Agent-side: persist a paused pipeline step awaiting human confirmation."""
    action = PendingAction(message_id=payload.message_id, tool_name=payload.tool_name)
    action.arguments = payload.arguments
    action.observations = payload.observations
    db.add(action)

    if payload.message_id is not None:
        message = db.get(Message, payload.message_id)
        if message is not None:
            # Stays 'processing' - the PWA cross-references /api/actions for
            # the confirmation prompt (see project spec section 14/30).
            message.response = payload.reply
            message.status = MessageStatus.processing

    db.commit()
    db.refresh(action)
    return action


@router.get("/confirmed-actions", response_model=List[PendingActionOut])
def get_confirmed_actions(
    db: Session = Depends(get_db),
    _agent=Depends(require_agent),
    limit: int = 10,
) -> list[PendingAction]:
    """Atomically claim confirmed actions by flipping them to 'executing',
    mirroring the locking used by GET /api/sync/pending."""
    stmt = (
        select(PendingAction)
        .where(PendingAction.status == ActionStatus.confirmed)
        .order_by(PendingAction.created_at.asc())
        .limit(limit)
    )
    actions = list(db.execute(stmt).scalars().all())
    for a in actions:
        a.status = ActionStatus.executing
    db.commit()
    for a in actions:
        db.refresh(a)
    return actions


@router.post("/actions/{action_id}/complete", response_model=PendingActionOut)
def complete_action(
    action_id: int,
    payload: ActionCompleteRequest,
    db: Session = Depends(get_db),
    _agent=Depends(require_agent),
) -> PendingAction:
    action = db.get(PendingAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Pending action not found.")
    action.status = ActionStatus.completed
    action.result = payload.result
    action.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(action)
    return action


@router.post("/actions/{action_id}/fail", response_model=PendingActionOut)
def fail_action(
    action_id: int,
    payload: ActionFailRequest,
    db: Session = Depends(get_db),
    _agent=Depends(require_agent),
) -> PendingAction:
    action = db.get(PendingAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Pending action not found.")
    action.status = ActionStatus.failed
    action.error = payload.error
    action.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(action)
    return action
