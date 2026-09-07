"""
Generic tool system + security model.

Security categories (see project spec section 12):
    SAFE             - may run automatically, no confirmation needed
    CONFIRM_REQUIRED - must not run automatically; a human must confirm
                       (not yet wired to a confirmation UI in V1 - any
                       tool in this category simply is not registered
                       yet, see tools listed in section 8/11)
    BLOCKED          - must never run automatically under any circumstance

V1 only implements SAFE tools (tasks, memory, system info). The
framework already supports the other categories so future tools
(open_application, delete_file, run_terminal_command, shutdown_pc,
...) can be added later behind an explicit confirmation step.
"""
from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict


class ToolSecurity(str, enum.Enum):
    SAFE = "SAFE"
    CONFIRM_REQUIRED = "CONFIRM_REQUIRED"
    BLOCKED = "BLOCKED"


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None


class Tool(ABC):
    name: str
    description: str
    # JSON-schema-like description of parameters, used both for
    # documentation and to build the LLM's tool-choice prompt.
    parameters: Dict[str, Any] = field(default_factory=dict)
    security: ToolSecurity = ToolSecurity.SAFE

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        raise NotImplementedError

    def schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "security": self.security.value,
        }
