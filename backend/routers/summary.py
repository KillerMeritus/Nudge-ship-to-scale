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
import os
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
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

def _dedup_distractions(distractions: list) -> list:
    if not distractions:
        return []
    
    unique_dist = []
    for d in distractions:
        # Check if same app and window title as the last one
        if unique_dist and unique_dist[-1].get('app_name') == d.get('app_name') and unique_dist[-1].get('window_title') == d.get('window_title'):
            unique_dist[-1]['count'] = unique_dist[-1].get('count', 1) + 1
        else:
            new_d = d.copy()
            new_d['count'] = 1
            unique_dist.append(new_d)
            
    # Sort by count to show top distractions
    unique_dist.sort(key=lambda x: x.get('count', 0), reverse=True)
    return unique_dist

def _build_ai_prompt(activity_log: list, tasks: list, distractions: list) -> str:
    tasks_text = "\n".join(
        f"- {t['title']} ({t.get('elapsed_seconds', 0) // 60} min, {t.get('status', '?')})"
        for t in tasks
    ) or "No tasks recorded."

    unique_dist = _dedup_distractions(distractions)[:10]
    dist_text = "\n".join(
        f"- {d.get('app_name', '?')}: \"{d.get('window_title', '')[:70]}\" (x{d.get('count', 1)} times)"
        for d in unique_dist
    ) or "None."

    # Sample activity: first 5 and last 5 entries to show start/end of day
    sample = activity_log[:5] + activity_log[-5:] if len(activity_log) > 10 else activity_log
    activity_text = "\n".join(
        f"- {e.get('app_name', '')}: {e.get('window_title', '')[:60]}"
        for e in sample
    ) or "No activity data."

    return f"""You are a productivity coach. Write a concise daily summary (under 200 words) using ONLY the data provided below. Use actual task names and app names — no placeholders. Do not repeat instructions or add meta-commentary.

Structure your response in exactly this order:

**Opening Hook** — 1-2 sentences naming the user's main focus today.

**Core Takeaways**
- Use 3-5 bullet points. **Bold** key phrases. Cover tasks done and top distractions.

**Final Verdict** — 1 sentence wrapping up the day.

End your entire response with this line and nothing after it:
SCORE: X.X

---
TASKS:
{tasks_text}

TOP DISTRACTIONS:
{dist_text}

ACTIVITY SAMPLE:
{activity_text}
"""

def _build_final_markdown(tasks: list, distractions: list, ai_insights: str, score: float) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Since AI is generating the full structured summary now, we just prepend the title and score
    return f"""## NUDGE DAILY SUMMARY ({today})

**Productivity Score:** {score} / 10

{ai_insights.strip()}
"""


# ── SCORE EXTRACTOR ───────────────────────────────────────────────────────────

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


# ── AI CLIENTS ────────────────────────────────────────────────────────────────

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


def _call_ollama(prompt: str, model: str = "gemma") -> tuple[str, float]:
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
    except urllib.error.URLError as e:
        logger.error("Ollama call failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail={"error": "ollama_offline", "message": "Ollama is not running on this machine"}
        )
    except Exception as e:
        logger.error("Ollama unexpected error: %s", e)
        raise HTTPException(
            status_code=503,
            detail={"error": "ollama_offline", "message": "Ollama is not running on this machine"}
        )
    return _extract_score(text)


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_summary():
    settings = load_settings()
    ai_model = settings.get("ai_model", "gemini").strip().lower()

    # ── Load activity log ──────────────────────────────────────────────────────
    # Prefer snapshot (stable copy) over live log
    activity_log = []
    today_str = datetime.now().strftime("%Y-%m-%d")
    source_file = SNAPSHOT_FILE if SNAPSHOT_FILE.exists() else DAILY_LOG_FILE
    if source_file.exists():
        try:
            full_log = json.loads(source_file.read_text(encoding="utf-8"))
            activity_log = [e for e in full_log if e.get("timestamp", "").startswith(today_str)]
            logger.info("Loaded %d activity entries from %s for today.", len(activity_log), source_file.name)
        except Exception as e:
            logger.warning("Could not read activity log (%s): %s", source_file.name, e)

    # ── Load tasks and distractions ───────────────────────────────────────────
    all_tasks = load_tasks()
    tasks = []
    for t in all_tasks:
        if t.get("status") != "Done":
            tasks.append(t)
        else:
            completed_at = str(t.get("completed_at", ""))
            if completed_at.startswith(today_str):
                tasks.append(t)
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

    prompt = _build_ai_prompt(activity_log, tasks, distractions)

    # ── Call AI ────────────────────────────────────────────────────────────────
    if ai_model == "ollama":
        ollama_model = settings.get("ollama_model", "gemma")
        logger.info("Generating summary via Ollama (%s).", ollama_model)
        try:
            summary_text, score = _call_ollama(prompt, ollama_model)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Ollama generation failed: %s", e)
            raise HTTPException(status_code=503, detail={"error": "ollama_offline", "message": str(e)})
    else:
        # Default: Gemini
        api_key = settings.get("gemini_api_key", "").strip()
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail={"error": "no_api_key", "message": "Add your Gemini API key in Settings"}
            )
        logger.info("Generating summary via Gemini.")
        try:
            summary_text, score = _call_gemini(prompt, api_key)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Gemini generation failed: %s", e)
            raise HTTPException(status_code=502, detail=f"Failed to generate summary: {str(e)}")

    final_markdown = _build_final_markdown(tasks, distractions, summary_text, score)

    _latest_summary["summary"] = final_markdown
    _latest_summary["score"] = score
    _latest_summary["generated_at"] = datetime.now().isoformat()
    logger.info("Summary generated via %s — score: %s", ai_model, score)
    return dict(_latest_summary)


@router.get("/latest")
async def get_latest_summary():
    return dict(_latest_summary)


class SummaryExportRequest(BaseModel):
    markdown: str


def get_downloads_path() -> Path:
    # macOS / Linux default
    downloads = Path.home() / "Downloads"
    if downloads.exists() and downloads.is_dir():
        return downloads
    
    # Windows registry lookup
    if os.name == "nt":
        try:
            import winreg
            sub_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
            downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                location = winreg.QueryValueEx(key, downloads_guid)[0]
                win_downloads = Path(location)
                if win_downloads.exists() and win_downloads.is_dir():
                    return win_downloads
        except Exception as e:
            logger.warning("Failed to look up Windows Downloads folder from registry: %s", e)
            
    # Fallback to home directory
    return Path.home()


@router.post("/export")
async def export_summary(req: SummaryExportRequest):
    try:
        downloads_dir = get_downloads_path()
        today = datetime.now().strftime("%Y-%m-%d")
        
        base_name = f"nudge-summary-{today}"
        ext = ".md"
        file_path = downloads_dir / f"{base_name}{ext}"
        
        counter = 1
        while file_path.exists():
            file_path = downloads_dir / f"{base_name} ({counter}){ext}"
            counter += 1
            
        file_path.write_text(req.markdown, encoding="utf-8")
        logger.info("Successfully exported summary to %s", file_path)
        return {
            "success": True,
            "filepath": str(file_path),
            "filename": file_path.name
        }
    except Exception as e:
        logger.error("Failed to write summary export file: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )