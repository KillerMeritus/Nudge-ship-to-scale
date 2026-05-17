"""
Summary router — calls Gemini API or local Ollama (Gemma) with today's
activity snapshot + task data + distraction events.
Returns a structured daily summary.

Latest summary kept in memory (resets on server restart, by design).

Phase 2 changes:
  - Reads daily_log_snapshot.json (written by BE-2 on /scraper/snapshot)
  - Includes task elapsed times and distraction events in the prompt
  - Supports both Gemini and Ollama based on settings.ai_model
  - Correct structured error responses:
      no_api_key    → 400
      ollama_offline → 503
"""

import logging
logger = logging.getLogger(__name__)

import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException
from backend.storage.settings_store import load_settings
from backend.storage.task_store import load_tasks

router = APIRouter(prefix="/summary", tags=["summary"])

# ── IN-MEMORY STORAGE ────────────────────────────────────────────────────────
_latest_summary = {
    "summary": None,
    "score": None,
    "generated_at": None,
}

# Snapshot file written by BE-2 on POST /scraper/snapshot
SNAPSHOT_FILE = Path(__file__).parents[2] / "scraper" / "data" / "daily_log_snapshot.json"
# Fallback to live log if no snapshot exists yet
DAILY_LOG_FILE = Path(__file__).parents[2] / "scraper" / "data" / "daily_log.json"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


# ── PROMPT BUILDER ────────────────────────────────────────────────────────────

def _build_prompt(activity_log: list, tasks: list, distractions: list) -> str:
    tasks_text = "\n".join(
        f"- {t['title']} | elapsed: {t.get('elapsed_seconds', 0) // 60}m"
        f" | status: {t.get('status', '?')}"
        for t in tasks
    ) or "No tasks recorded today."

    dist_text = "\n".join(
        f"- {d.get('timestamp', '')} | Working on: {d.get('task_title', '?')}"
        f" | Switched to: {d.get('app_name', '?')}"
        f" | {d.get('reason', '')}"
        for d in distractions
    ) or "No distractions recorded."

    activity_text = "\n".join(
        f"- {e.get('timestamp', '')}: {e.get('app_name', '')} — {e.get('window_title', '')}"
        for e in activity_log[:100]   # cap at 100 entries to stay within token limits
    ) or "No activity data captured."

    today = datetime.now().strftime("%Y-%m-%d")

    return f"""You are a productivity assistant. Generate a structured daily summary.

Tasks worked on today:
{tasks_text}

Distraction events:
{dist_text}

Activity log sample:
{activity_text}

Respond in this exact format:
NUDGE DAILY SUMMARY — {today}

Productivity Score: X.X / 10

What You Worked On:
- {{task}} — {{duration}} — {{apps used}}

Deep Work Time: Xh Ym
Distraction Time: Xh Ym

Distraction Events:
- {{time}} | Working on: {{task}} | Switched to: {{app}} | Duration: {{N}} mins

Top Distractions:
- {{app or pattern}}

Biggest Pattern:
- {{one specific observation}}

One Suggestion for Tomorrow:
- {{specific and actionable}}

SCORE: X.X"""


# ── AI CLIENTS ────────────────────────────────────────────────────────────────

def _extract_score(text: str) -> tuple[str, float]:
    """Pull SCORE: X.X from the end of the text, strip it, return (clean_text, score)."""
    score = 5.0
    for line in reversed(text.splitlines()):
        if line.strip().startswith("SCORE:"):
            try:
                score = float(line.split(":")[1].strip())
            except Exception:
                pass
            text = text[:text.rfind("SCORE:")].strip()
            break
    return text, score


def _call_gemini(prompt: str, api_key: str) -> tuple[str, float]:
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{GEMINI_URL}?key={api_key}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            logger.warning("Gemini quota exceeded (429).")
            raise HTTPException(
                status_code=429,
                detail="Gemini quota exceeded. Try again later or switch to Ollama."
            )
        logger.error("Gemini HTTP error: %s", e.code)
        raise HTTPException(status_code=502, detail=f"Gemini API error: {e.code}")

    text = (
        result["candidates"][0]["content"]["parts"][0]["text"].strip()
    )
    return _extract_score(text)


def _call_ollama(prompt: str, model: str) -> tuple[str, float]:
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            text = result.get("response", "").strip()
    except Exception as e:
        logger.error("Ollama call failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail={"error": "ollama_offline", "message": "Ollama is not running on this machine"}
        )
    return _extract_score(text)


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_summary():
    settings = load_settings()
    ai_model = settings.get("ai_model", "gemini")

    # ── Load activity log ──────────────────────────────────────────────────────
    # Prefer snapshot (stable copy) over live log
    activity_log = []
    source_file = SNAPSHOT_FILE if SNAPSHOT_FILE.exists() else DAILY_LOG_FILE
    if source_file.exists():
        try:
            activity_log = json.loads(source_file.read_text(encoding="utf-8"))
            logger.info("Loaded %d activity entries from %s.", len(activity_log), source_file.name)
        except Exception as e:
            logger.warning("Could not read activity log (%s): %s", source_file.name, e)

    # ── Load tasks and distractions ───────────────────────────────────────────
    tasks = load_tasks()
    try:
        from backend.routers.distraction import _alerts
        distractions = list(_alerts)
    except Exception:
        distractions = []

    # ── Handle no activity data ────────────────────────────────────────────────
    if not activity_log:
        logger.warning("Summary requested but no activity data found.")
        placeholder = (
            f"NUDGE DAILY SUMMARY — {datetime.now().strftime('%Y-%m-%d')}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "No activity data yet.\n\n"
            "Make sure the scraper is running, then click 'Generate' again."
        )
        _latest_summary["summary"] = placeholder
        _latest_summary["score"] = None
        _latest_summary["generated_at"] = datetime.now().isoformat()
        return dict(_latest_summary)

    prompt = _build_prompt(activity_log, tasks, distractions)

    # ── Call AI ────────────────────────────────────────────────────────────────
    if ai_model == "ollama":
        ollama_model = settings.get("ollama_model", "gemma")
        logger.info("Generating summary via Ollama (%s).", ollama_model)
        summary_text, score = _call_ollama(prompt, ollama_model)
    else:
        # Default: Gemini
        api_key = settings.get("gemini_api_key", "").strip()
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail={"error": "no_api_key", "message": "Add your Gemini API key in Settings"}
            )
        logger.info("Generating summary via Gemini.")
        summary_text, score = _call_gemini(prompt, api_key)

    _latest_summary["summary"] = summary_text
    _latest_summary["score"] = score
    _latest_summary["generated_at"] = datetime.now().isoformat()
    logger.info("Summary generated via %s — score: %s", ai_model, score)
    return dict(_latest_summary)


@router.get("/latest")
async def get_latest_summary():
    return dict(_latest_summary)