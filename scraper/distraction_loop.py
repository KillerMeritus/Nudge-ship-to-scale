"""
distraction_loop.py — Background thread that checks if the user is distracted.

Runs every 10 seconds. Reads settings dynamically each cycle:
  - distraction_detection_enabled (on/off)
  - distraction_cooldown_seconds (per-app-per-task alert gap)
  - distraction_whitelist (user-defined apps to ignore)

Requires an active task (via GET /timer/active-task) to run.
Appends rich, detailed log statements to both the console and scraper/data/distraction.log.
"""

import time
import json
import urllib.request
import urllib.error
import threading
from datetime import datetime
from pathlib import Path

from scraper.ai.ai_client import classify_activity
from scraper.whitelist import is_whitelisted

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

CURRENT_FILE = DATA_DIR / "current_activity.json"
SETTINGS_FILE = ROOT.parent / "backend" / "data" / "settings.json"
LOG_FILE = DATA_DIR / "distraction.log"

_cooldowns = {}
_distraction_thread = None
_running = False


# ── Unified Logger ────────────────────────────────────────────────────────────

def _log(message: str, level: str = "INFO"):
    """Log a message to the console and to scraper/data/distraction.log with timestamps."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [{level}] [distraction_loop] {message}"
    
    # 1. Output to standard stdout for immediate terminal visibility
    print(formatted)
    
    # 2. Append to persistent log file
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception as e:
        print(f"[{timestamp}] [ERROR] Failed to write to log file: {e}")


# ── Settings reader ───────────────────────────────────────────────────────────

def _read_settings() -> dict:
    """Read settings.json — returns defaults on any failure."""
    try:
        if SETTINGS_FILE.exists():
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return {}
    except Exception as e:
        _log(f"Failed to read settings.json: {e}", "WARNING")
        return {}


# ── Active task check ─────────────────────────────────────────────────────────

def _check_active_task():
    try:
        req = urllib.request.Request("http://127.0.0.1:8080/timer/active-task")
        with urllib.request.urlopen(req, timeout=3) as res:
            data = json.loads(res.read().decode())
            return data
    except Exception as e:
        _log(f"Failed to check active task from backend: {e}", "DEBUG")
        return None


# ── Alert sender ──────────────────────────────────────────────────────────────

def _send_alert(alert_data):
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8080/distraction/alert",
            data=json.dumps(alert_data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3) as res:
            resp_data = json.loads(res.read().decode())
            _log(f"✓ Alert successfully received by backend: {resp_data}", "SUCCESS")
    except Exception as e:
        _log(f"❌ Failed to send alert to backend: {e}", "ERROR")


# ── Main loop ─────────────────────────────────────────────────────────────────

# Tracks the last evaluation decision per (app_name + window_title + task_id) combo.
# Also records the time of the last evaluation so we can force a re-check every
# N minutes even when nothing changes (prevents a wrong AI verdict sticking forever).
_last_checked_state = {"app_name": None, "window_title": None, "task_id": None}
_RECHECK_INTERVAL_S = 300  # re-evaluate even identical windows every 5 minutes

def _loop():
    global _last_checked_state
    _log("Background thread started successfully. Active checking begins...", "INFO")
    
    while _running:
        time.sleep(10)
        
        try:
            # ── 0. Read settings ──────────────────────────────────────────
            settings = _read_settings()

            # Check if distraction detection is enabled
            enabled = settings.get("distraction_detection_enabled", True)
            if not enabled:
                _log("Checking skipped: Distraction detection is disabled in settings.", "DEBUG")
                continue

            cooldown_seconds = settings.get("distraction_cooldown_seconds", 180)
            user_whitelist = settings.get("distraction_whitelist", [])

            # ── 1. Check active task ──────────────────────────────────────
            task = _check_active_task()
            if not task:
                _log("Checking skipped: No active task currently running (Start a task/timer in Nudge to activate detection).", "INFO")
                continue

            # ── 2. Read current_activity.json ─────────────────────────────
            if not CURRENT_FILE.exists():
                _log(f"Checking skipped: Activity snapshot file missing ({CURRENT_FILE.name}). Scraper might be initializing.", "WARNING")
                continue
            
            try:
                with open(CURRENT_FILE, "r", encoding="utf-8") as f:
                    activity = json.load(f)
            except Exception as e:
                _log(f"Checking skipped: Failed to parse {CURRENT_FILE.name}: {e}", "WARNING")
                continue
            
            app_name = activity.get("app_name", "")
            window_title = activity.get("window_title", "")
            text_elements = activity.get("text_elements", [])
            
            _log(f"Current Activity detected — App: '{app_name}' | Title: '{window_title}' | Task: '{task['title']}'", "INFO")

            # ── 3. Skip communication apps ────────────────────────────────
            comm_apps = ["zoom", "google meet", "microsoft teams", "slack", "webex", "discord"]
            if app_name.lower() in comm_apps:
                _log(f"Decision: Ignored '{app_name}' because it is classified as a whitelisted collaboration tool.", "INFO")
                continue
                
            # ── 4. Skip whitelisted apps (hardcoded + user-defined) ───────
            if is_whitelisted(app_name):
                _log(f"Decision: Ignored '{app_name}' because it is in the system default whitelist.", "INFO")
                continue

            # Check user-defined whitelist (case-insensitive partial match)
            app_lower = app_name.lower()
            matching_whitelist_item = next((w for w in user_whitelist if w and w.lower() in app_lower), None)
            if matching_whitelist_item:
                _log(f"Decision: Ignored '{app_name}' because it matched user whitelist keyword: '{matching_whitelist_item}'.", "INFO")
                continue

            # ── 5. Deduplicate: skip if same non-distracting window (with time-based re-eval)
            # Key includes both app AND window title — switching to a different file/tab
            # in the same app must always trigger a fresh AI call.
            combo_key = f"{app_name}:{task['id']}"
            dedup_key = f"{app_name}::{window_title}::{task['id']}"
            
            same_window = (dedup_key == _last_checked_state.get("dedup_key"))
            last_eval_time = _last_checked_state.get("last_eval_time", 0)
            time_since_eval = time.time() - last_eval_time
            due_for_recheck = time_since_eval >= _RECHECK_INTERVAL_S
            
            if same_window and not due_for_recheck:
                if not _last_checked_state.get("was_distracted"):
                    _log(
                        f"Decision: Skipped re-evaluation of '{app_name}' (same window, last checked "
                        f"{int(time_since_eval)}s ago, recheck due in {int(_RECHECK_INTERVAL_S - time_since_eval)}s).",
                        "DEBUG"
                    )
                    continue
                else:
                    _log(f"Deduplication: Same distracting window '{app_name}', checking cooldown.", "DEBUG")
            elif same_window and due_for_recheck:
                _log(f"Re-evaluating '{app_name}' — same window but {int(time_since_eval)}s have passed (periodic recheck).", "INFO")

            # ── 6. Call AI classifier ─────────────────────────────────────
            ai_model = settings.get("ai_model", "gemini").lower()
            _log(f"Calling AI classifier ({ai_model}) to analyze app activity against task context...", "INFO")
            
            result = classify_activity(task["title"], app_name, window_title, text_elements)
            if not result:
                _log(f"❌ AI classification call failed or returned an unparseable response. Verify your settings, internet connection, and API keys.", "ERROR")
                continue

            is_distracted = bool(result.get("is_distracted"))
            _last_checked_state["app_name"] = app_name
            _last_checked_state["window_title"] = window_title
            _last_checked_state["task_id"] = task["id"]
            _last_checked_state["was_distracted"] = is_distracted
            _last_checked_state["dedup_key"] = dedup_key
            _last_checked_state["last_eval_time"] = time.time()

            _log(f"AI decision complete: is_distracted={is_distracted} (Confidence: {result.get('confidence')})", "INFO")
            _log(f"AI Category: '{result.get('distraction_category')}' | Severity: '{result.get('severity')}' | Reason: '{result.get('reason')}'", "INFO")

            # ── 7. Not distracted → done ──────────────────────────────────
            if not is_distracted:
                _log(f"Decision: User is in focus. Keep up the good work!", "INFO")
                continue

            # ── 8. Check cooldown (user-configurable) ─────────────────────
            last_alert = _cooldowns.get(combo_key, 0)
            now = time.time()
            if now - last_alert < cooldown_seconds:
                remaining = int(cooldown_seconds - (now - last_alert))
                _log(f"Decision: Distraction detected but suppressed. Cooldown is active for '{app_name}' on task '{task['title']}' ({remaining}s remaining of {cooldown_seconds}s limit).", "INFO")
                continue
                
            # ── 9. Send alert to backend ──────────────────────────────────
            _log(f"⚠️ Distraction validated! Preparing alert notification payload for app '{app_name}'...", "WARNING")
            alert_data = {
                "task_id": task["id"],
                "task_title": task["title"],
                "app_name": app_name,
                "window_title": window_title,
                "reason": result.get("reason", ""),
                "distraction_category": result.get("distraction_category", "other"),
                "severity": result.get("severity", "medium")
            }
            
            _send_alert(alert_data)
            
            # ── 10. Update cooldown ───────────────────────────────────────
            _cooldowns[combo_key] = now
            _log(f"✓ Alert payload successfully posted to backend. Cooldown reset for '{app_name}'.", "INFO")
            
        except Exception as e:
            _log(f"Unexpected Loop error: {e}", "ERROR")


def start_distraction_loop():
    global _distraction_thread, _running
    if _running:
        return
    _running = True
    _distraction_thread = threading.Thread(target=_loop, daemon=True)
    _distraction_thread.start()
    _log("Distraction detection background service initialized.", "INFO")
