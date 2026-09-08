"""
Read-only settings overview for the PWA Settings page (project spec
section 30). Everything here is derived from server-side configuration
(.env) - the endpoint never accepts writes, so there is no way for the
PWA (or a compromised client) to change security-relevant config like
ALLOWED_DIRECTORIES or tool confirmation policy over the network. To
change settings, edit .env and restart the backend/agent.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_user
from app.config import get_settings
from app.schemas import SettingsOut, WakeOnLanInfo

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings_overview(_user=Depends(require_user)) -> SettingsOut:
    settings = get_settings()

    wake_on_lan = WakeOnLanInfo(
        configured=bool(settings.WAKE_ON_LAN_MAC),
        mac_address=settings.WAKE_ON_LAN_MAC or None,
        broadcast=settings.WAKE_ON_LAN_BROADCAST,
        port=settings.WAKE_ON_LAN_PORT,
        command=(
            f"python wake_pc.py {settings.WAKE_ON_LAN_MAC} "
            f"--broadcast {settings.WAKE_ON_LAN_BROADCAST} --port {settings.WAKE_ON_LAN_PORT}"
            if settings.WAKE_ON_LAN_MAC
            else None
        ),
    )

    return SettingsOut(
        llm_provider=settings.LLM_PROVIDER,
        local_llm_model=settings.LOCAL_LLM_MODEL,
        local_llm_base_url=settings.LOCAL_LLM_BASE_URL,
        cloud_llm_enabled=settings.CLOUD_LLM_ENABLED,
        cloud_llm_model=settings.CLOUD_LLM_MODEL if settings.CLOUD_LLM_ENABLED else None,
        allowed_directories=settings.allowed_directories_list,
        message_max_retries=settings.MESSAGE_MAX_RETRIES,
        wake_on_lan=wake_on_lan,
    )
