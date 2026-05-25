"""
distraction_loop.py — Background thread that checks if the user is distracted.

Runs every 10 seconds. Reads settings dynamically each cycle:
  - distraction_detection_enabled (on/off)
  - distraction_cooldown_seconds (per-app-per-task alert gap)
  - distraction_whitelist (user-defined apps to ignore)

Requires an active task (via GET /timer/active-task) to run.
"""

import time
import json
import urllib.request
import urllib.error
import threading
from pathlib import Path

from scraper.ai.ai_client import classify_activity
from scraper.whitelist import is_whitelisted

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
CURRENT_FILE = DATA_DIR / "current_activity.json"
SETTINGS_FILE = ROOT.parent / "backend" / "data" / "settings.json"

_cooldowns = {}
_distraction_thread = None
_running = False


# ── Settings reader ───────────────────────────────────────────────────────────

def _read_settings() -> dict:
    """Read settings.json — returns defaults on any failure."""
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ── Active task check ─────────────────────────────────────────────────────────

def _check_active_task():
    try:
        req = urllib.request.Request("http://127.0.0.1:8080/timer/active-task")
        with urllib.request.urlopen(req, timeout=3) as res:
            data = json.loads(res.read().decode())
            return data
    except Exception:
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
            pass
    except Exception as e:
        print(f"[distraction_loop] Failed to send alert: {e}")


# ── Main loop ─────────────────────────────────────────────────────────────────

_last_checked_state = {"app_name": None, "window_title": None, "task_id": None}

def _loop():
    global _last_checked_state
    print("[distraction_loop] Started background thread.")
    while _running:
        time.sleep(10)
        
        try:
            # ── 0. Read settings ──────────────────────────────────────────
            settings = _read_settings()

            # Check if distraction detection is enabled
            if not settings.get("distraction_detection_enabled", True):
                continue

            cooldown_seconds = settings.get("distraction_cooldown_seconds", 180)
            user_whitelist = settings.get("distraction_whitelist", [])

            # ── 1. Check active task ──────────────────────────────────────
            task = _check_active_task()
            if not task:
                # No active task — distraction detection requires one.
                # This is by design: we need task context for AI classification.
                continue

            # ── 2. Read current_activity.json ─────────────────────────────
            if not CURRENT_FILE.exists():
                continue
            
            with open(CURRENT_FILE, "r", encoding="utf-8") as f:
                activity = json.load(f)
            
            app_name = activity.get("app_name", "")
            window_title = activity.get("window_title", "")
            text_elements = activity.get("text_elements", [])
            
            # ── 3. Skip communication apps ────────────────────────────────
            comm_apps = ["zoom", "google meet", "microsoft teams", "slack", "webex", "discord"]
            if app_name.lower() in comm_apps:
                continue
                
            # ── 4. Skip whitelisted apps (hardcoded + user-defined) ───────
            if is_whitelisted(app_name):
                continue

            # Check user-defined whitelist (case-insensitive partial match)
            app_lower = app_name.lower()
            if any(w.lower() in app_lower for w in user_whitelist if w):
                continue

            # ── 5. Deduplicate: skip if same non-distracting window ───────
            combo_key = f"{app_name}:{task['id']}"
            same_window = (
                app_name == _last_checked_state["app_name"] and
                window_title == _last_checked_state["window_title"] and
                task["id"] == _last_checked_state["task_id"]
            )
            if same_window and not _last_checked_state.get("was_distracted"):
                continue

            # ── 6. Call AI classifier ─────────────────────────────────────
            print(f"[distraction_loop] Classifying: {app_name} | {window_title[:60]} | task: {task['title']}")
            result = classify_activity(task["title"], app_name, window_title, text_elements)
            if not result:
                print(f"[distraction_loop] AI returned None — classification failed.")
                continue

            is_distracted = bool(result.get("is_distracted"))
            _last_checked_state["app_name"] = app_name
            _last_checked_state["window_title"] = window_title
            _last_checked_state["task_id"] = task["id"]
            _last_checked_state["was_distracted"] = is_distracted

            print(f"[distraction_loop] AI result: distracted={is_distracted}, "
                  f"confidence={result.get('confidence')}, "
                  f"category={result.get('distraction_category')}, "
                  f"severity={result.get('severity')}")

            # ── 7. Not distracted → done ──────────────────────────────────
            if not is_distracted:
                continue

            # ── 8. Check cooldown (user-configurable) ─────────────────────
            last_alert = _cooldowns.get(combo_key, 0)
            now = time.time()
            if now - last_alert < cooldown_seconds:
                remaining = int(cooldown_seconds - (now - last_alert))
                print(f"[distraction_loop] Distracted by {app_name}, but in {cooldown_seconds}s cooldown ({remaining}s left).")
                continue
                
            # ── 9. Send alert to backend ──────────────────────────────────
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
            print(f"[distraction_loop] ✓ ALERT FIRED: {app_name} during '{task['title']}' "
                  f"(severity={result.get('severity')}, category={result.get('distraction_category')})")
            
        except Exception as e:
            print(f"[distraction_loop] Loop error: {e}")


def start_distraction_loop():
    global _distraction_thread, _running
    if _running:
        return
    _running = True
    _distraction_thread = threading.Thread(target=_loop, daemon=True)
    _distraction_thread.start()
