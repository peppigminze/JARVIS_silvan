from __future__ import annotations

from sqlalchemy.orm import Session

from app.memory.store import MemoryStore
from app.tools.base import Tool, ToolResult, ToolSecurity


class SaveMemoryTool(Tool):
    name = "save_memory"
    description = "Save a fact or piece of information JARVIS should remember for later."
    parameters = {
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "category": {"type": "string"},
        },
        "required": ["content"],
    }
    security = ToolSecurity.SAFE

    async def execute(self, db: Session, content: str, category: str | None = None, **_) -> ToolResult:
        store = MemoryStore(db)
        entry = store.save(content=content, category=category)
        return ToolResult(success=True, data={"id": entry.id, "content": entry.content})


class SearchMemoryTool(Tool):
    name = "search_memory"
    description = "Search previously saved memories by keyword."
    parameters = {
        "type": "object",
        "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
        "required": ["query"],
    }
    security = ToolSecurity.SAFE

    async def execute(self, db: Session, query: str, limit: int = 5, **_) -> ToolResult:
        store = MemoryStore(db)
        results = store.search(query, limit=limit)
        data = [{"id": m.id, "content": m.content, "category": m.category} for m in results]
        return ToolResult(success=True, data=data)
