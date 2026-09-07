"""
Confirmation flow for CONFIRM_REQUIRED tools (project spec section 14).

    Agent Core wants to run a destructive tool
        -> PendingAction row (awaiting_confirmation)
        -> PWA shows it, human clicks Confirm/Reject
            confirm -> POST /api/actions/{id}/confirm (this file)
            reject  -> POST /api/actions/{id}/reject  (this file)
        -> local PC agent polls GET /api/sync/confirmed-actions (sync.py),
           executes the tool, resumes the paused message pipeline.

Only the human user (PWA) may confirm or reject - the agent never
calls these endpoints.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_user
from app.database.db import get_db
from app.database.models import ActionStatus, Message, MessageStatus, PendingAction
from app.schemas import PendingActionOut

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.get("", response_model=List[PendingActionOut])
def list_actions(
    db: Session = Depends(get_db),
    _user=Depends(require_user),
    status: str | None = "awaiting_confirmation",
) -> list[PendingAction]:
    stmt = select(PendingAction).order_by(PendingAction.created_at.asc())
    if status:
        stmt = stmt.where(PendingAction.status == ActionStatus(status))
    return list(db.execute(stmt).scalars().all())


@router.post("/{action_id}/confirm", response_model=PendingActionOut)
def confirm_action(
    action_id: int, db: Session = Depends(get_db), _user=Depends(require_user)
) -> PendingAction:
    action = db.get(PendingAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Pending action not found.")
    if action.status != ActionStatus.awaiting_confirmation:
        raise HTTPException(
            status_code=409, detail=f"Action is '{action.status.value}', not awaiting confirmation."
        )
    action.status = ActionStatus.confirmed
    db.commit()
    db.refresh(action)
    return action


@router.post("/{action_id}/reject", response_model=PendingActionOut)
def reject_action(
    action_id: int, db: Session = Depends(get_db), _user=Depends(require_user)
) -> PendingAction:
    action = db.get(PendingAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Pending action not found.")
    if action.status != ActionStatus.awaiting_confirmation:
        raise HTTPException(
            status_code=409, detail=f"Action is '{action.status.value}', not awaiting confirmation."
        )
    action.status = ActionStatus.rejected
    action.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(action)

    if action.message_id is not None:
        message = db.get(Message, action.message_id)
        if message is not None and message.status == MessageStatus.processing:
            message.status = MessageStatus.completed
            message.response = "Okay, das habe ich nicht ausgeführt."
            message.processed_at = datetime.now(timezone.utc)
            db.commit()

    return action
