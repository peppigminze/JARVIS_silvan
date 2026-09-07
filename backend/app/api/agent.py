from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_agent, require_user
from app.config import get_settings
from app.database.db import get_db
from app.database.models import AgentHeartbeat, Message, MessageStatus
from app.llm.factory import get_llm_provider
from app.schemas import HeartbeatOut, SystemStatusOut

router = APIRouter(tags=["agent"])

# PC counts as "online" if the last heartbeat was within this window.
HEARTBEAT_TIMEOUT_SECONDS = 30


@router.post("/api/agent/heartbeat", response_model=HeartbeatOut)
def heartbeat(
    db: Session = Depends(get_db),
    _agent=Depends(require_agent),
    agent_name: str = "default",
) -> AgentHeartbeat:
    hb = db.query(AgentHeartbeat).filter(AgentHeartbeat.agent_name == agent_name).first()
    now = datetime.now(timezone.utc)
    if hb is None:
        hb = AgentHeartbeat(agent_name=agent_name, last_seen=now)
        db.add(hb)
    else:
        hb.last_seen = now
    db.commit()
    db.refresh(hb)
    return hb


@router.get("/api/status", response_model=SystemStatusOut)
async def system_status(
    db: Session = Depends(get_db),
    _user=Depends(require_user),
) -> SystemStatusOut:
    settings = get_settings()
    hb = db.query(AgentHeartbeat).filter(AgentHeartbeat.agent_name == "default").first()

    pc_online = False
    if hb is not None:
        age = datetime.now(timezone.utc) - hb.last_seen.replace(tzinfo=timezone.utc)
        pc_online = age < timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)

    pending_count = db.execute(
        select(func.count()).select_from(Message).where(Message.status == MessageStatus.pending)
    ).scalar_one()

    llm_available = None
    if pc_online:
        # Only probe the LLM if the PC is even online, to avoid a slow
        # health check dragging down every status poll while offline.
        try:
            provider = get_llm_provider(settings)
            llm_available = await provider.health_check()
        except Exception:  # noqa: BLE001
            llm_available = False

    return SystemStatusOut(
        pc_online=pc_online,
        last_seen=hb.last_seen if hb else None,
        pending_messages=pending_count,
        llm_provider=settings.LLM_PROVIDER,
        llm_available=llm_available,
    )
