"""
Application control tools (project spec section 13). Listing running
processes is read-only (SAFE). Opening/closing a process can affect
unsaved work or launch arbitrary programs, so both require confirmation
(project spec section 14) - open_application additionally passes
through the same command denylist as run_command, since a shell launch
string is just as powerful as a shell command.
"""
from __future__ import annotations

import asyncio
import subprocess

import psutil
from sqlalchemy.orm import Session

from app.tools.base import Tool, ToolResult, ToolSecurity
from app.tools.command_safety import is_blocked_command

MAX_PROCESS_LIST = 200


class ListRunningApplicationsTool(Tool):
    name = "list_running_applications"
    description = "List currently running processes (name and PID)."
    parameters = {"type": "object", "properties": {}}
    security = ToolSecurity.SAFE

    async def execute(self, db: Session | None = None, **_) -> ToolResult:
        processes = []
        for proc in psutil.process_iter(["pid", "name"]):
            processes.append({"pid": proc.info["pid"], "name": proc.info["name"]})
            if len(processes) >= MAX_PROCESS_LIST:
                break
        return ToolResult(success=True, data=processes)


class OpenApplicationTool(Tool):
    name = "open_application"
    description = (
        "Launch a program on the user's PC (e.g. 'notepad.exe' or a full path). "
        "Requires confirmation."
    )
    parameters = {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
    security = ToolSecurity.CONFIRM_REQUIRED

    async def execute(self, db: Session | None = None, command: str = "", **_) -> ToolResult:
        blocked_reason = is_blocked_command(command)
        if blocked_reason:
            return ToolResult(success=False, error=f"Refused - matches a blocked pattern ({blocked_reason}).")
        try:
            proc = subprocess.Popen(command, shell=True)
        except OSError as exc:
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=True, data={"launched": command, "pid": proc.pid})


class CloseApplicationTool(Tool):
    name = "close_application"
    description = "Close a running application by PID or process name. Requires confirmation."
    parameters = {
        "type": "object",
        "properties": {"pid": {"type": "integer"}, "name": {"type": "string"}},
    }
    security = ToolSecurity.CONFIRM_REQUIRED

    async def execute(
        self, db: Session | None = None, pid: int | None = None, name: str | None = None, **_
    ) -> ToolResult:
        if pid is None and not name:
            return ToolResult(success=False, error="Provide either 'pid' or 'name'.")

        targets: list[psutil.Process] = []
        if pid is not None:
            try:
                targets = [psutil.Process(pid)]
            except psutil.NoSuchProcess:
                return ToolResult(success=False, error=f"No process with PID {pid}.")
        else:
            targets = [
                p
                for p in psutil.process_iter(["name"])
                if (p.info["name"] or "").lower() == name.lower()
            ]
            if not targets:
                return ToolResult(success=False, error=f"No running process named '{name}'.")

        closed: list[int] = []
        for proc in targets:
            try:
                proc.terminate()
                closed.append(proc.pid)
            except psutil.NoSuchProcess:
                continue

        # Give terminated processes a brief moment before reporting, so
        # a caller listing processes right after sees them gone.
        await asyncio.sleep(0.2)
        return ToolResult(success=True, data={"closed_pids": closed})
