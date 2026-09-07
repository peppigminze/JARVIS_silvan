"""
Simple persistent memory layer.

V1 has NO vector database / embeddings. Search is a plain SQL
LIKE-based keyword match. This is intentionally simple - the
MemoryStore interface (save / search / get / delete) is stable, so a
later version can swap the implementation for an embeddings/vector
search backend without changing any caller.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import DEFAULT_MEMORY_TYPE, MEMORY_TYPES, MemoryEntry


class MemoryStore:
    def __init__(self, db: Session):
        self.db = db

    def save(
        self, content: str, category: Optional[str] = None, memory_type: str = DEFAULT_MEMORY_TYPE
    ) -> MemoryEntry:
        if memory_type not in MEMORY_TYPES:
            memory_type = DEFAULT_MEMORY_TYPE
        entry = MemoryEntry(content=content, category=category, memory_type=memory_type)
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get(self, memory_id: int) -> Optional[MemoryEntry]:
        return self.db.get(MemoryEntry, memory_id)

    def search(self, query: str, limit: int = 5) -> Sequence[MemoryEntry]:
        """Very simple keyword search across memory content.

        Splits the query into words and returns memories containing
        any of them, most recent first. This is a placeholder for a
        future embeddings-based semantic search.
        """
        query = (query or "").strip()
        if not query:
            return self.list_recent(limit=limit)

        words = [w for w in query.lower().split() if len(w) > 2]
        if not words:
            return self.list_recent(limit=limit)

        stmt = select(MemoryEntry)
        conditions = [MemoryEntry.content.ilike(f"%{w}%") for w in words]
        from sqlalchemy import or_

        stmt = stmt.where(or_(*conditions)).order_by(MemoryEntry.updated_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def list_recent(self, limit: int = 5) -> Sequence[MemoryEntry]:
        stmt = select(MemoryEntry).order_by(MemoryEntry.updated_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def list_all(self) -> Sequence[MemoryEntry]:
        stmt = select(MemoryEntry).order_by(MemoryEntry.updated_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def delete(self, memory_id: int) -> bool:
        entry = self.get(memory_id)
        if entry is None:
            return False
        self.db.delete(entry)
        self.db.commit()
        return True
