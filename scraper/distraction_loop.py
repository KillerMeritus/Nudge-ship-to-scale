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

_cooldowns = {}
_distraction_thread = None
_running = False

def _check_active_task():
    try:
        req = urllib.request.Request("http://127.0.0.1:8080/timer/active-task")
        with urllib.request.urlopen(req, timeout=3) as res:
            data = json.loads(res.read().decode())
            return data
    except Exception:
        return None

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

_last_checked_state = {"app_name": None, "window_title": None, "task_id": None}

def _loop():
    global _last_checked_state
    print("[distraction_loop] Started background thread.")
    while _running:
        time.sleep(10)
        
        try:
            # 1. Check active task
            task = _check_active_task()
            if not task:
                continue

            # 2. Read current_activity.json
            if not CURRENT_FILE.exists():
                continue
            
            with open(CURRENT_FILE, "r", encoding="utf-8") as f:
                activity = json.load(f)
            
            app_name = activity.get("app_name", "")
            window_title = activity.get("window_title", "")
            text_elements = activity.get("text_elements", [])
            
            # 3. Skip communication apps
            if app_name.lower() in ["zoom", "google meet", "microsoft teams", "slack", "webex"]:
                continue
                
            # 4. Skip whitelisted apps
            if is_whitelisted(app_name):
                continue

            # Skip if we already checked this exact window and task
            if (app_name == _last_checked_state["app_name"] and 
                window_title == _last_checked_state["window_title"] and 
                task["id"] == _last_checked_state["task_id"]):
                continue

            # 5. Call AI
            result = classify_activity(task["title"], app_name, window_title, text_elements)
            if not result:
                continue
                
            # Cache the state only after a successful AI call
            _last_checked_state["app_name"] = app_name
            _last_checked_state["window_title"] = window_title
            _last_checked_state["task_id"] = task["id"]
                
            # 7. Check if distracted
            if not result.get("is_distracted"):
                continue
                
            # 8. Check cooldown
            combo_key = f"{app_name}:{task['id']}"
            last_alert = _cooldowns.get(combo_key, 0)
            now = time.time()
            if now - last_alert < 180:
                print(f"[distraction_loop] Distracted by {app_name}, but still in 180s cooldown.")
                continue
                
            # 10. Send alert
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
            
            # 11. Update cooldown
            _cooldowns[combo_key] = now
            print(f"[distraction_loop] Alert fired: {app_name} during '{task['title']}'")
            
        except Exception as e:
            print(f"[distraction_loop] Loop error: {e}")

def start_distraction_loop():
    global _distraction_thread, _running
    if _running:
        return
    _running = True
    _distraction_thread = threading.Thread(target=_loop, daemon=True)
    _distraction_thread.start()
