"""
gemini_client.py — Gemini 2.0 Flash REST client for distraction classification.

Uses httpx sync (no async — scraper is threaded, not async).
Reads API key from backend/data/settings.json each call so the user can
update it without restarting the scraper.
"""

import json
import time
from pathlib import Path

import httpx

from scraper.ai.prompts import SYSTEM_PROMPT, build_prompt

_SETTINGS_FILE = Path(__file__).parent.parent.parent / "backend" / "data" / "settings.json"

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

_TIMEOUT = 8.0   # seconds
_BACKOFF  = 30.0  # seconds to wait after 429

# Warn-once flags
_warned_no_key  = False
_next_retry_at  = 0.0  # epoch after which Gemini calls are allowed again


def _api_key() -> str | None:
    try:
        data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        return data.get("gemini_api_key") or None
    except Exception:
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
            print("[gemini] No API key found in settings.json (gemini_api_key). Gemini disabled.")
            _warned_no_key = True
        return None

    # Reset warn flag if key appears (user filled it in)
    _warned_no_key = False

    # Respect backoff after 429
    now = time.time()
    if now < _next_retry_at:
        return None

    prompt = build_prompt(task_title, app_name, window_title, text_elements)

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 256},
    }

    try:
        resp = httpx.post(
            f"{_GEMINI_URL}?key={key}",
            json=payload,
            timeout=_TIMEOUT,
        )

        if resp.status_code == 429:
            print(f"[gemini] Rate-limited (429) — backing off {_BACKOFF}s.")
            _next_retry_at = time.time() + _BACKOFF
            return None

        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    except httpx.TimeoutException:
        print("[gemini] Request timed out.")
        return None
    except Exception as e:
        print(f"[gemini] Error: {e}")
        return None
