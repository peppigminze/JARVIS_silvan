"""
Sync worker for the local PC agent.

Loop (see project spec sections 3, 14, 19):
    poll GET /api/sync/pending
        -> for each message:
            run the JARVIS Agent Core pipeline locally
            (local LLM + local tools + local DB)
        -> POST /api/sync/complete  (or /api/sync/fail on error)

This process is what actually "does the work" while the PWA/backend
may be reachable from anywhere. If the PC is off, nothing here runs -
messages simply stay 'pending' in the backend until this worker comes
back online and polls again.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# The agent reuses the backend's app package directly (Agent Core, LLM
# provider, tool registry, DB session) since for V1 both processes run
# on the same machine against the same SQLite database. Only the
# message queue itself (pending/complete/fail, heartbeat) goes over
# HTTP, which is what would let this worker talk to a remote backend
# later without changes to the Agent Core.
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(REPO_ROOT))

from app.agent.core import JarvisAgent  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database.db import init_db, session_scope  # noqa: E402
from app.llm.base import LLMUnavailableError  # noqa: E402
from app.llm.factory import get_llm_provider  # noqa: E402
from app.tools.defaults import build_default_registry  # noqa: E402

from agent.client import BackendClient  # noqa: E402

logger = logging.getLogger("jarvis.agent.sync_worker")


class SyncWorker:
    def __init__(self, client: BackendClient):
        self.client = client
        settings = get_settings()
        self.jarvis = JarvisAgent(llm=get_llm_provider(settings), tools=build_default_registry())

    async def poll_once(self) -> int:
        """Fetch and process one batch of pending messages.
        Returns how many messages were processed."""
        try:
            pending = await self.client.get_pending_messages()
        except Exception as exc:  # noqa: BLE001
            logger.error("Could not reach backend for pending messages: %s", exc)
            return 0

        if not pending:
            return 0

        logger.info("Found %d pending message(s).", len(pending))
        for msg in pending:
            await self._process_one(msg)
        return len(pending)

    async def _process_one(self, msg: dict) -> None:
        message_id = msg["id"]
        content = msg["content"]
        logger.info("Processing message %s", message_id)
        try:
            with session_scope() as db:
                reply = await self.jarvis.run_pipeline(db, content)
            await self.client.complete_message(message_id, reply)
            logger.info("Message %s completed.", message_id)
        except LLMUnavailableError:
            logger.error("Local LLM is unavailable while processing message %s", message_id)
            await self._safe_fail(message_id, "Local LLM is unavailable.")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error processing message %s", message_id)
            await self._safe_fail(message_id, "Die Aktion konnte nicht ausgeführt werden.")

    async def _safe_fail(self, message_id: int, error: str) -> None:
        try:
            await self.client.fail_message(message_id, error)
        except Exception as exc:  # noqa: BLE001
            logger.error("Could not report failure for message %s to backend: %s", message_id, exc)

    async def run_forever(self, poll_interval: float) -> None:
        init_db()
        logger.info("Sync worker started. Polling every %.1fs.", poll_interval)
        while True:
            await self.poll_once()
            await asyncio.sleep(poll_interval)
