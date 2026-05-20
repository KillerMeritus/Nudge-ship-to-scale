#!/usr/bin/env python3
"""
NUDGE SCRAPER — main.py
Entry point. Detects platform, runs the appropriate scraper in a loop.

Run with: python3 scraper/main.py
"""

import os
import sys
import time
import json
import platform
from pathlib import Path
from datetime import datetime

# ── PATHS ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

CURRENT_FILE       = DATA_DIR / "current_activity.json"
BACKEND_TASKS_FILE = ROOT.parent / "backend" / "data" / "tasks.json"
# Per-process temp file lives in the same directory so os.replace() is atomic
# (rename across filesystems is not). PID suffix avoids clashes if two scraper
# instances run accidentally.
CURRENT_TMP   = DATA_DIR / f"current_activity.json.{os.getpid()}.tmp"
DAILY_LOG_FILE = DATA_DIR / "daily_log.json"


def _write_current_atomic(entry: dict) -> None:
    """
    Write current_activity.json atomically.

    Why: readers (FastAPI /activity/current) hit this file every poll. A naive
    write_text() truncates and re-writes in place — a crash mid-write, or a
    read that lands between truncate and flush, yields invalid JSON. We write
    to a sibling tmp file, fsync, then os.replace() onto the target. os.replace
    is atomic on POSIX and Windows when src/dst are on the same volume:
    readers see either the old complete file or the new complete file.
    """
    data = json.dumps(entry, ensure_ascii=False)
    # Open with explicit fd so we can fsync before the rename — protects
    # against the rename surviving a power loss while the data does not.
    fd = os.open(CURRENT_TMP, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        # Best-effort cleanup of the tmp file; never mask the original error.
        try:
            CURRENT_TMP.unlink(missing_ok=True)
        except Exception:
            pass
        raise
    os.replace(CURRENT_TMP, CURRENT_FILE)

# ── PLATFORM DETECTION ────────────────────────────────────────────────────────
PLATFORM = platform.system()   # "Darwin" | "Windows" | "Linux"

if PLATFORM == "Darwin":
    from scraper.mac_scraper import get_active_window
elif PLATFORM == "Windows":
    from scraper.windows_scraper import get_active_window
else:
    print(f"[scraper] Unsupported platform: {PLATFORM}")
    sys.exit(1)

from scraper.idle_detector import is_idle
from scraper.whitelist import is_whitelisted

# ── ACTIVE TASK CONTEXT ───────────────────────────────────────────────────────
# Cached so we read tasks.json at most once every 10 s instead of every tick.
_task_cache: dict = {"title": None, "expires": 0.0}


def _active_task_title() -> str | None:
    """
    Return the title of whichever task is currently 'In Progress', or None.

    Reads backend/data/tasks.json directly — same machine, no HTTP round-trip.
    Result is cached for 10 seconds so a 5 s poll loop doesn't hammer the file.
    """
    now = time.time()
    if now < _task_cache["expires"]:
        return _task_cache["title"]

    title = None
    try:
        if BACKEND_TASKS_FILE.exists():
            tasks = json.loads(BACKEND_TASKS_FILE.read_text(encoding="utf-8"))
            for task in tasks:
                if task.get("status") == "In Progress":
                    title = task.get("title")
                    break
    except Exception:
        pass  # tasks.json missing or malformed — treat as no active task

    _task_cache["title"] = title
    _task_cache["expires"] = now + 10.0
    return title


# ── DAILY LOG ─────────────────────────────────────────────────────────────────
_daily_log: list = []


def _date_aware_reset() -> None:
    """
    Compare today's date against the date of the FIRST entry in the log.
    If they differ, the calendar day has rolled over (overnight, or laptop
    closed across midnight) — save the old log and start fresh.

    Using the first entry's date (not a startup-time variable) means this
    works correctly even if the scraper runs for multiple days without a
    restart, and after sleep/wake cycles where the process kept running.
    """
    global _daily_log
    if not _daily_log:
        return  # nothing logged yet — nothing to compare

    first_ts = _daily_log[0].get("timestamp", "")
    first_date = first_ts[:10]          # "2026-05-17"
    today = datetime.now().strftime("%Y-%m-%d")

    if first_date and first_date != today:
        # Save to an archive directory instead of a single previous_day_log.json
        archive_dir = DATA_DIR / "logs"
        archive_dir.mkdir(exist_ok=True)
        archive_file = archive_dir / f"{first_date}.json"
        
        archive_file.write_text(
            json.dumps(_daily_log, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _daily_log = []
        DAILY_LOG_FILE.write_text("[]", encoding="utf-8")
        print(f"[scraper] Date rolled over ({first_date} → {today}) — archived log to logs/{archive_file.name}.")


def _flush_log():
    DAILY_LOG_FILE.write_text(
        json.dumps(_daily_log, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
POLL_INTERVAL = 5  # seconds

from scraper.distraction_loop import start_distraction_loop

def main():
    start_distraction_loop()
    print(f"[scraper] Starting on {PLATFORM}. Polling every {POLL_INTERVAL}s.")
    while True:
        try:
            _date_aware_reset()

            if is_idle():
                print("[scraper] Idle — skipping.")
                time.sleep(POLL_INTERVAL)
                continue

            activity = get_active_window()

            if is_whitelisted(activity.get("app_name", "")):
                print(f"[scraper] Whitelisted: {activity['app_name']}")
                time.sleep(POLL_INTERVAL)
                continue

            entry = {
                **activity,
                "timestamp": datetime.now().isoformat(),
                "task_context": _active_task_title(),
            }

            # Write current snapshot atomically — readers must never see a
            # half-written file. See _write_current_atomic() for rationale.
            _write_current_atomic(entry)

            # Append to daily log
            _daily_log.append(entry)
            _flush_log()

            bg_apps = ", ".join(w['app_name'] for w in entry.get("background_windows", [])[:5])
            print(
                f"[scraper] {entry['app_name']} | "
                f"els:{len(entry.get('text_elements', []))} | "
                f"task:{entry.get('task_context') or '-'} | "
                f"bg:[{bg_apps}]"
            )

        except KeyboardInterrupt:
            print("[scraper] Stopped.")
            break
        except Exception as e:
            print(f"[scraper] Error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
