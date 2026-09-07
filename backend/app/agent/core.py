"""
JARVIS Agent Core.

Pipeline (see project spec section 7):
    receive_message()
    understand()
    plan()
    select_tools()
    execute_tools()
    generate_response()
    save_memory()

V1 does not have real LLM function-calling for every local model, so
tool selection uses a small JSON protocol: the model is asked to
reply with a JSON object describing which tool (if any) to call, and
a natural-language reply. This keeps JARVIS provider-agnostic and
works with any local chat model, not just ones with native tool use.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.database.models import Message, MessageStatus
from app.llm.base import ChatMessage, LLMProvider, LLMUnavailableError
from app.memory.store import MemoryStore
from app.tools.base import ToolResult
from app.tools.registry import ToolRegistry

logger = logging.getLogger("jarvis.agent")


SYSTEM_PROMPT_TEMPLATE = """You are JARVIS, a helpful local-first personal AI assistant.

You can optionally use exactly one tool per message if it helps fulfil the
user's request. Available tools:

{tool_list}

Relevant memories about the user (may be empty):
{memories}

Respond with ONLY a single JSON object, no other text, in this exact shape:
{{
  "tool": "<tool_name or null>",
  "arguments": {{}},
  "reply": "<short natural-language reply to the user>"
}}

If no tool is needed, set "tool" to null and just answer in "reply".
Always fill "reply" - it is what the user will see if no tool result
needs to be summarized afterwards.
"""

FINAL_ANSWER_PROMPT_TEMPLATE = """You are JARVIS. You just executed the tool "{tool_name}" for the
user's request: "{user_message}"

Tool result (JSON): {tool_result}

Write a short, natural, friendly final reply to the user summarizing what
happened. Do not mention JSON or internal tool names explicitly. Reply with
plain text only.
"""


@dataclass
class PlanDecision:
    tool: Optional[str]
    arguments: dict
    reply: str


class JarvisAgent:
    def __init__(self, llm: LLMProvider, tools: ToolRegistry):
        self.llm = llm
        self.tools = tools

    # ---------------------------------------------------------- 1. receive

    def receive_message(self, db: Session, content: str, client_id: str | None = None) -> Message:
        """Persist an incoming message as 'pending'. Idempotent on client_id."""
        if client_id:
            existing = db.query(Message).filter(Message.client_id == client_id).first()
            if existing:
                return existing

        message = Message(content=content, client_id=client_id, status=MessageStatus.pending)
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    # ---------------------------------------------------------- 2. understand

    def understand(self, db: Session, content: str) -> dict:
        """Gather context: relevant memories for this message."""
        store = MemoryStore(db)
        memories = store.search(content, limit=5)
        return {"memories": [m.content for m in memories]}

    # ---------------------------------------------------------- 3. plan

    async def plan(self, content: str, context: dict) -> PlanDecision:
        tool_list = "\n".join(
            f"- {t.name}: {t.description} (parameters: {json.dumps(t.parameters)})"
            for t in self.tools.list_tools()
        )
        memories = "\n".join(f"- {m}" for m in context.get("memories", [])) or "(none)"

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(tool_list=tool_list, memories=memories)
        messages: list[ChatMessage] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ]

        raw = await self.llm.chat(messages, temperature=0.2)
        return self._parse_plan(raw)

    def _parse_plan(self, raw: str) -> PlanDecision:
        text = raw.strip()
        # Be defensive: some local models wrap JSON in ```json fences.
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            data = json.loads(text)
            tool = data.get("tool") or None
            arguments = data.get("arguments") or {}
            reply = data.get("reply") or ""
            return PlanDecision(tool=tool, arguments=arguments, reply=reply)
        except (json.JSONDecodeError, AttributeError):
            # Model didn't follow the JSON protocol - fall back to treating
            # the whole output as a plain reply with no tool call.
            logger.warning("Could not parse plan JSON, falling back to plain reply.")
            return PlanDecision(tool=None, arguments={}, reply=raw.strip())

    # ---------------------------------------------------------- 4. select_tools

    def select_tools(self, decision: PlanDecision):
        if not decision.tool:
            return None
        tool = self.tools.get(decision.tool)
        if tool is None:
            logger.warning("Model requested unknown tool '%s'", decision.tool)
            return None
        if not self.tools.is_executable_automatically(decision.tool):
            logger.info("Tool '%s' requires confirmation - skipping in V1.", decision.tool)
            return None
        return tool

    # ---------------------------------------------------------- 5. execute_tools

    async def execute_tools(self, db: Session, tool, arguments: dict) -> Optional[ToolResult]:
        if tool is None:
            return None
        try:
            return await tool.execute(db=db, **arguments)
        except TypeError as exc:
            logger.error("Tool '%s' called with bad arguments: %s", tool.name, exc)
            return ToolResult(success=False, error=f"Invalid arguments for tool '{tool.name}'.")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Tool '%s' raised an unexpected error", tool.name)
            return ToolResult(success=False, error="Die Aktion konnte nicht ausgeführt werden.")

    # ---------------------------------------------------------- 6. generate_response

    async def generate_response(
        self, content: str, decision: PlanDecision, tool_result: Optional[ToolResult]
    ) -> str:
        if tool_result is None:
            return decision.reply or "..."

        if not tool_result.success:
            return f"Die Aktion konnte nicht ausgeführt werden: {tool_result.error}"

        prompt = FINAL_ANSWER_PROMPT_TEMPLATE.format(
            tool_name=decision.tool,
            user_message=content,
            tool_result=json.dumps(tool_result.data, default=str),
        )
        try:
            summary = await self.llm.chat(
                [
                    {"role": "system", "content": "You write short, friendly assistant replies."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )
            return summary.strip()
        except LLMUnavailableError:
            # Tool already succeeded - degrade gracefully to a plain summary
            # instead of failing the whole message.
            return f"Erledigt. Ergebnis: {json.dumps(tool_result.data, default=str)}"

    # ---------------------------------------------------------- 7. save_memory

    def save_memory(self, db: Session, content: str, category: str | None = None) -> None:
        """Explicit helper for callers that want to persist a memory
        directly (the LLM can also do this itself via the save_memory
        tool during planning)."""
        MemoryStore(db).save(content=content, category=category)

    # ---------------------------------------------------------- pipeline (content-only)

    async def run_pipeline(self, db: Session, content: str) -> str:
        """Run understand -> plan -> select_tools -> execute_tools ->
        generate_response for a piece of text and return the final reply.

        This is used by the local PC agent worker (agent/sync_worker.py),
        which receives message *content* over HTTP from the sync backend
        rather than owning a live Message ORM row itself. Raises
        LLMUnavailableError if the local LLM cannot be reached.
        """
        context = self.understand(db, content)
        decision = await self.plan(content, context)
        tool = self.select_tools(decision)
        tool_result = await self.execute_tools(db, tool, decision.arguments)
        return await self.generate_response(content, decision, tool_result)

    # ---------------------------------------------------------- orchestration

    async def process(self, db: Session, message: Message) -> Message:
        """Run the full pipeline for a single pending message and persist
        the result. Never raises - all failure modes are captured on the
        Message row as status='failed' with a human-readable error."""

        message.status = MessageStatus.processing
        db.commit()

        try:
            context = self.understand(db, message.content)
            decision = await self.plan(message.content, context)
            tool = self.select_tools(decision)
            tool_result = await self.execute_tools(db, tool, decision.arguments)
            final_reply = await self.generate_response(message.content, decision, tool_result)

            message.response = final_reply
            message.status = MessageStatus.completed
            message.processed_at = datetime.now(timezone.utc)
            message.error = None
        except LLMUnavailableError as exc:
            logger.error("LLM unavailable while processing message %s: %s", message.id, exc)
            message.status = MessageStatus.failed
            message.error = "Local LLM is unavailable."
            message.processed_at = datetime.now(timezone.utc)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error while processing message %s", message.id)
            message.status = MessageStatus.failed
            message.error = "Die Aktion konnte nicht ausgeführt werden."
            message.processed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(message)
        return message
