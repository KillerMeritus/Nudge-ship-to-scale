"""
Scraper control router — signals the BE-2 scraper process via a shared control file.

The scraper reads scraper/data/control.json at the top of each loop iteration
and acts on the command before clearing it.

Endpoints:
  POST /scraper/snapshot  — tell scraper to write daily_log_snapshot.json
  POST /scraper/pause     — tell scraper to stop accumulating (e.g. system sleep)
  POST /scraper/resume    — tell scraper to resume accumulating (e.g. system wake)
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scraper", tags=["scraper"])

# Control file that the BE-2 scraper reads each poll cycle
CONTROL_FILE = Path(__file__).parents[2] / "scraper" / "data" / "control.json"


def _write_control(command: str) -> None:
    CONTROL_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONTROL_FILE.write_text(
        json.dumps({"command": command, "issued_at": datetime.now().isoformat()},
                   ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Scraper control command issued: %s", command)


@router.post("/snapshot")
async def trigger_snapshot():
    """
    Tells BE-2 to write its current in-memory daily log to
    scraper/data/daily_log_snapshot.json so the summary endpoint
    can read a stable copy without racing the live log writes.
    """
    _write_control("snapshot")
    return {"requested": True, "command": "snapshot"}


@router.post("/pause")
async def pause_scraper():
    """
    Tells BE-2 to stop accumulating activity entries.
    Called by FE-2 on system sleep so idle time is not logged as activity.
    """
    _write_control("pause")
    return {"requested": True, "command": "pause"}


@router.post("/resume")
async def resume_scraper():
    """
    Tells BE-2 to resume accumulating activity entries.
    Called by FE-2 on system wake.
    """
    _write_control("resume")
    return {"requested": True, "command": "resume"}
