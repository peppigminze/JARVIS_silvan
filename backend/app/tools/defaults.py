from __future__ import annotations

from app.tools.memory_tools import SaveMemoryTool, SearchMemoryTool
from app.tools.registry import ToolRegistry
from app.tools.system_tools import GetCurrentTimeTool, GetSystemStatusTool
from app.tools.task_tools import CompleteTaskTool, CreateTaskTool, DeleteTaskTool, ListTasksTool


def build_default_registry() -> ToolRegistry:
    """All V1 tools are SAFE. Dangerous PC tools (open_application,
    delete_file, run_terminal_command, shutdown_pc, ...) are
    intentionally NOT registered yet - see project spec section 12."""
    registry = ToolRegistry()
    registry.register(CreateTaskTool())
    registry.register(ListTasksTool())
    registry.register(CompleteTaskTool())
    registry.register(DeleteTaskTool())
    registry.register(SaveMemoryTool())
    registry.register(SearchMemoryTool())
    registry.register(GetCurrentTimeTool())
    registry.register(GetSystemStatusTool())
    return registry
