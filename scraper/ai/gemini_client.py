"""
gemini_client.py — Gemini 2.0 Flash REST client for distraction classification.

Uses httpx sync (no async — scraper is threaded, not async).
Reads API key from backend/data/settings.json each call so the user can
update it without restarting the scraper.
"""

import json
import time
from pathlib import Path
from datetime import datetime
import httpx

from scraper.ai.prompts import SYSTEM_PROMPT, build_prompt

_SETTINGS_FILE = Path(__file__).parent.parent.parent / "backend" / "data" / "settings.json"
_LOG_FILE = Path(__file__).parent.parent / "data" / "distraction.log"

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

_TIMEOUT = 8.0   # seconds
_BACKOFF  = 30.0  # seconds to wait after 429

# Warn-once flags
_warned_no_key  = False
_next_retry_at  = 0.0  # epoch after which Gemini calls are allowed again


def _log(message: str, level: str = "INFO"):
    """Log a message to the console and to distraction.log with timestamps."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [{level}] [gemini_client] {message}"
    print(formatted)
    try:
        _LOG_FILE.parent.mkdir(exist_ok=True)
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception as e:
        print(f"[{timestamp}] [ERROR] Failed to write to log file: {e}")


def _api_key() -> str | None:
    try:
        if _SETTINGS_FILE.exists():
            data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            return data.get("gemini_api_key") or None
        return None
    except Exception as e:
        _log(f"Failed to read settings file for API key: {e}", "WARNING")
        return None


def call(
    task_title: str,
    app_name: str,
    window_title: str,
    text_elements: list[str],
) -> str | None:
    """
    Returns the raw model response string or None on any failure.
    """
    global _warned_no_key, _next_retry_at

    key = _api_key()
    if not key:
        if not _warned_no_key:
            _log("API Key missing! Gemini calls are currently disabled. Please add a 'gemini_api_key' in the Nudge Settings tab.", "ERROR")
            _warned_no_key = True
        return None

    # Reset warn flag if key appears (user filled it in)
    _warned_no_key = False

    # Respect backoff after 429
    now = time.time()
    if now < _next_retry_at:
        remaining = int(_next_retry_at - now)
        _log(f"Skip: Gemini call suppressed due to active rate-limit backoff ({remaining}s remaining).", "WARNING")
        return None

    prompt = build_prompt(task_title, app_name, window_title, text_elements)

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 256},
    }

    _log(f"Sending request to Gemini API (Timeout: {_TIMEOUT}s)...", "INFO")
    try:
        resp = httpx.post(
            f"{_GEMINI_URL}?key={key}",
            json=payload,
            timeout=_TIMEOUT,
        )

        if resp.status_code == 429:
            _log(f"Rate-limited (429) from Gemini API. Backing off for {_BACKOFF} seconds.", "ERROR")
            _next_retry_at = time.time() + _BACKOFF
            return None

        # Check for auth errors or bad requests
        if resp.status_code == 400:
            _log(f"Bad Request (400) from Gemini API. Response: {resp.text}. Check if your prompt content is invalid.", "ERROR")
            return None
        elif resp.status_code == 403:
            _log(f"Forbidden (403) from Gemini API. Your API Key is likely invalid or deactivated. Response: {resp.text}", "ERROR")
            return None

        resp.raise_for_status()
        data = resp.json()
        
        # Validate structure
        candidates = data.get("candidates", [])
        if not candidates or "content" not in candidates[0]:
            _log(f"Empty candidate list received in Gemini API response: {data}", "ERROR")
            return None
            
        raw_text = candidates[0]["content"]["parts"][0]["text"]
        _log(f"Received response from Gemini API: {raw_text.strip()[:100]}...", "DEBUG")
        return raw_text

    except httpx.TimeoutException:
        _log(f"Request timed out after {_TIMEOUT} seconds. Internet connection or API endpoint is slow.", "ERROR")
        return None
    except httpx.HTTPStatusError as e:
        _log(f"HTTP error occurred: {e.response.status_code} - {e.response.text}", "ERROR")
        return None
    except Exception as e:
        _log(f"Unexpected error calling Gemini API: {e}", "ERROR")
        return None
