from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_user
from app.database.db import get_db
from app.memory.store import MemoryStore
from app.schemas import MemoryCreate, MemoryOut

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("", response_model=List[MemoryOut])
def list_memory(
    db: Session = Depends(get_db),
    _user=Depends(require_user),
    q: str | None = None,
    memory_type: str | None = None,
) -> list:
    store = MemoryStore(db)
    entries = list(store.search(q, limit=50)) if q else list(store.list_all())
    if memory_type:
        entries = [e for e in entries if e.memory_type == memory_type]
    return entries


@router.post("", response_model=MemoryOut)
def create_memory(
    payload: MemoryCreate, db: Session = Depends(get_db), _user=Depends(require_user)
):
    store = MemoryStore(db)
    return store.save(content=payload.content, category=payload.category, memory_type=payload.memory_type)


@router.delete("/{memory_id}")
def delete_memory(
    memory_id: int, db: Session = Depends(get_db), _user=Depends(require_user)
) -> dict:
    store = MemoryStore(db)
    if not store.delete(memory_id):
        raise HTTPException(status_code=404, detail="Memory entry not found.")
    return {"id": memory_id, "deleted": True}
