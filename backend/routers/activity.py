"""
Activity router — reads latest scrape from scraper/data/current_activity.json.

Phase 2 additions:
  POST /activity/sleep-gap  — FE-2 calls on system wake to insert a gap marker
  GET  /activity/today      — returns full in-memory activity log + gap markers
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/activity", tags=["activity"])

SCRAPER_FILE = Path(__file__).parents[2] / "scraper" / "data" / "current_activity.json"

MOCK_ACTIVITY = {
    "app_name": "Terminal",
    "window_title": "nudge — backend — zsh",
    "text_elements": [],
    "is_idle": False,
}

# ── IN-MEMORY LOG (gap markers + supplemental entries) ────────────────────────
_activity_log: list = []


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class SleepGap(BaseModel):
    slept_at: str           # ISO timestamp when system slept
    woke_at: str            # ISO timestamp when system woke
    duration_seconds: int   # total sleep duration


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.get("/current")
async def get_current_activity():
    if SCRAPER_FILE.exists():
        try:
            data = json.loads(SCRAPER_FILE.read_text(encoding="utf-8"))
            return data
        except Exception as e:
            logger.warning("Could not read current_activity.json: %s — falling back to mock.", e)
    # Scraper not running yet — return mock
    return {**MOCK_ACTIVITY, "timestamp": datetime.now().isoformat()}


@router.post("/sleep-gap", status_code=201)
async def record_sleep_gap(body: SleepGap):
    """
    Called by FE-2 (Tauri) on system wake.
    Inserts a gap marker into the in-memory activity log so the
    daily summary knows the system was asleep during that window.
    """
    gap = {
        "type": "sleep_gap",
        "slept_at": body.slept_at,
        "woke_at": body.woke_at,
        "duration_seconds": body.duration_seconds,
        "timestamp": datetime.now().isoformat(),
    }
    _activity_log.append(gap)
    logger.info(
        "Sleep gap recorded — slept: %s, woke: %s, duration: %ds",
        body.slept_at, body.woke_at, body.duration_seconds,
    )
    return {"recorded": True, "gap": gap}


@router.get("/today")
async def get_today_activity():
    """
    Returns the in-memory activity log.
    Includes sleep gap markers inserted by FE-2.
    The scraper's own daily_log.json is the primary data source for summaries;
    this endpoint supplements it with gap metadata.
    """
    return _activity_log
