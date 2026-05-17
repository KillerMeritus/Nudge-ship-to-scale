"""
Distraction router — receives alerts from BE-2 scraper when the active
window doesn't match the user's current task.

Phase 2 schema — each alert contains:
  task_id, task_title, app_name, window_title,
  reason, distraction_category, severity, timestamp

Endpoints:
  POST   /distraction/alert    ← BE-2 scraper calls this
  GET    /distraction/latest   ← most recent alert or null
  GET    /distraction/today    ← all alerts for today (newest first)
  DELETE /distraction/today    ← clear today's list
  POST   /distraction/alerts/seen  ← mark all as seen (FE-1 calls after displaying)
"""

import logging
from collections import deque
from datetime import datetime, date as _date
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/distraction", tags=["distraction"])

# ── IN-MEMORY STORE ───────────────────────────────────────────────────────────
_MAX_ALERTS = 200
_alerts: deque = deque(maxlen=_MAX_ALERTS)
_current_date: str = _date.today().isoformat()


def _check_date_reset() -> None:
    """
    Reset the alert list if the calendar date has changed.
    Called at the top of every endpoint — no clock trigger needed.
    """
    global _current_date
    today = _date.today().isoformat()
    if today != _current_date:
        _alerts.clear()
        _current_date = today
        logger.info("Date changed to %s — distraction alerts reset.", today)


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class DistractionAlert(BaseModel):
    task_id: str
    task_title: str
    app_name: str
    window_title: str
    reason: str
    distraction_category: str   # "social_media"|"entertainment"|"news"|"gaming"|"unrelated_work"
    severity: str               # "low" | "medium" | "high"


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.post("/alert", status_code=201)
async def receive_alert(body: DistractionAlert):
    """Called by BE-2 scraper whenever a distraction is detected."""
    _check_date_reset()
    entry = {
        **body.model_dump(),
        "timestamp": datetime.now().isoformat(),
        "seen": False,
    }
    _alerts.appendleft(entry)   # newest first
    logger.info(
        "Distraction alert: %s (%s) — task: %s — severity: %s",
        body.app_name, body.window_title, body.task_title, body.severity,
    )
    return {"received": True}


@router.get("/latest")
async def get_latest_distraction():
    """Returns the most recent distraction alert, or null if none today."""
    _check_date_reset()
    return _alerts[0] if _alerts else None


@router.get("/today")
async def get_today_distractions():
    """
    Returns all distraction alerts for today, newest first.
    FE-1 polls this every 30 seconds to update the badge count on the Summary tab.
    """
    _check_date_reset()
    return list(_alerts)


@router.delete("/today")
async def clear_today_distractions():
    """Clear today's distraction list (hard reset)."""
    _check_date_reset()
    count = len(_alerts)
    _alerts.clear()
    logger.info("Today's distraction alerts cleared (%d removed).", count)
    return {"cleared": count}


@router.post("/alerts/seen")
async def mark_alerts_seen():
    """Mark all current alerts as seen. FE-1 calls after displaying them."""
    _check_date_reset()
    for alert in _alerts:
        alert["seen"] = True
    return {"marked": len(_alerts)}
