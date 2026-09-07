from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
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
) -> list:
    store = MemoryStore(db)
    if q:
        return list(store.search(q, limit=50))
    return list(store.list_all())


@router.post("", response_model=MemoryOut)
def create_memory(
    payload: MemoryCreate, db: Session = Depends(get_db), _user=Depends(require_user)
):
    store = MemoryStore(db)
    return store.save(content=payload.content, category=payload.category)
