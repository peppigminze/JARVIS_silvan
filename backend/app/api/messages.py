from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_user
from app.database.db import get_db
from app.database.models import Message
from app.schemas import MessageCreate, MessageOut

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.post("", response_model=MessageOut)
def create_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_user),
) -> Message:
    """
    Store a new chat message as 'pending'.

    This endpoint intentionally does NOT call the LLM directly - actual
    processing happens asynchronously via the local PC agent's sync
    worker, so the API responds instantly even if the PC is offline or
    busy (see project spec section 19).
    """
    if payload.client_id:
        existing = db.query(Message).filter(Message.client_id == payload.client_id).first()
        if existing:
            return existing

    message = Message(content=payload.content, client_id=payload.client_id)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("", response_model=List[MessageOut])
def list_messages(
    db: Session = Depends(get_db),
    _user=Depends(require_user),
    limit: int = 50,
) -> list[Message]:
    stmt = select(Message).order_by(Message.created_at.desc()).limit(limit)
    messages = list(db.execute(stmt).scalars().all())
    messages.reverse()
    return messages
