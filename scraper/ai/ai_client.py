"""
ai_client.py — Unified distraction classification entry point.

Reads ai_model from settings each call so the user can switch between
"gemini" and "ollama" live without restarting the scraper.

classify_activity() returns a validated dict or None.
"""

import json
import re
from pathlib import Path
from typing import Optional

_SETTINGS_FILE = Path(__file__).parent.parent.parent / "backend" / "data" / "settings.json"

_REQUIRED_KEYS = {"is_distracted", "confidence", "reason", "distraction_category", "severity"}

# Regex to strip ```json ... ``` fences that some models wrap responses in
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _read_ai_model() -> str:
    try:
        data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        return (data.get("ai_model") or "gemini").lower()
    except Exception:
        return "gemini"


def _parse_response(raw: str) -> Optional[dict]:
    if not raw:
        return None

    # Strip markdown fences if present
    m = _FENCE_RE.search(raw)
    text = m.group(1) if m else raw.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Try to find first {...} block in the string
        start = text.find("{")
        end   = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            result = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None

    if not isinstance(result, dict):
        return None

    if not _REQUIRED_KEYS.issubset(result.keys()):
        return None

    return result


def classify_activity(
    task_title: str,
    app_name: str,
    window_title: str,
    text_elements: list[str],
) -> Optional[dict]:
    """
    Classify whether the current foreground activity is a distraction.

    Returns a dict with keys: is_distracted, confidence, reason,
    distraction_category, severity — or None if classification failed.
    """
    model = _read_ai_model()

    if model == "ollama":
        from scraper.ai import ollama_client
        raw = ollama_client.call(task_title, app_name, window_title, text_elements)
    else:
        # Default to Gemini
        from scraper.ai import gemini_client
        raw = gemini_client.call(task_title, app_name, window_title, text_elements)

    return _parse_response(raw)
