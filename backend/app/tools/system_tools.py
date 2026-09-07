from __future__ import annotations

import platform
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.tools.base import Tool, ToolResult, ToolSecurity


class GetCurrentTimeTool(Tool):
    name = "get_current_time"
    description = "Get the current date and time (UTC)."
    parameters = {"type": "object", "properties": {}}
    security = ToolSecurity.SAFE

    async def execute(self, db: Session | None = None, **_) -> ToolResult:
        now = datetime.now(timezone.utc)
        return ToolResult(success=True, data={"utc_iso": now.isoformat()})


class GetSystemStatusTool(Tool):
    name = "get_system_status"
    description = "Get basic status info about the machine JARVIS is running on."
    parameters = {"type": "object", "properties": {}}
    security = ToolSecurity.SAFE

    async def execute(self, db: Session | None = None, **_) -> ToolResult:
        data = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "machine": platform.machine(),
        }
        return ToolResult(success=True, data=data)
