"""
Settings router — read/write settings.json via settings_store.

Phase 2 additions:
  GET /settings/ollama-status  — live check if Ollama is running on port 11434
  New fields: ai_model, ollama_model, distraction_cooldown_seconds
"""

import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.storage.settings_store import load_settings, save_settings as _save

router = APIRouter(prefix="/settings", tags=["settings"])

OLLAMA_URL = "http://localhost:11434"


class SettingsUpdate(BaseModel):
    # Phase 1 fields
    gemini_api_key: Optional[str] = None

    work_start_time: Optional[str] = None
    work_end_time: Optional[str] = None

    work_duration_minutes: Optional[int] = None
    short_break_minutes: Optional[int] = None
    long_break_minutes: Optional[int] = None
    long_break_after_cycles: Optional[int] = None

    long_break_enabled: Optional[bool] = None
    launch_on_startup: Optional[bool] = None
    distraction_detection_enabled: Optional[bool] = None

    idle_threshold_seconds: Optional[int] = None
    distraction_whitelist: Optional[list[str]] = None

    # Phase 2 fields
    ai_model: Optional[str] = None                    # "gemini" | "ollama"
    ollama_model: Optional[str] = None                # "gemma" (default)
    distraction_cooldown_seconds: Optional[int] = None  # default 180


@router.get("")
async def get_settings():
    return load_settings()


@router.post("")
async def update_settings(body: SettingsUpdate):
    current = load_settings()
    updates = body.model_dump(exclude_none=True)
    current.update(updates)
    _save(current)
    logger.info("Settings updated — fields: %s", list(updates.keys()))
    return current


@router.get("/ollama-status")
async def get_ollama_status():
    """
    Checks if Ollama is running locally on port 11434.
    FE-1 polls this every 5 seconds when 'Local — Ollama' is selected in Settings.
    Never raises — always returns { "running": true | false }.
    """
    try:
        with urllib.request.urlopen(OLLAMA_URL, timeout=2):
            return {"running": True}
    except Exception:
        return {"running": False}
