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

from app.auth import require_agent
from app.database.db import get_db
from app.database.models import Message, MessageStatus
from app.schemas import MessageOut, SyncCompleteRequest, SyncFailRequest

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
    stmt = (
        select(Message)
        .where(Message.status == MessageStatus.pending)
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
    message.processed_at = datetime.now(timezone.utc)
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
