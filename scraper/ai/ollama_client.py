"""
ollama_client.py — Local Ollama client for distraction classification.

Sends a single prompt (system + user merged) to localhost:11434/api/generate.
Falls back silently when Ollama is not running — warn once, then stay quiet.
"""

import json
from pathlib import Path

import httpx

from scraper.ai.prompts import SYSTEM_PROMPT, build_prompt

_SETTINGS_FILE = Path(__file__).parent.parent.parent / "backend" / "data" / "settings.json"

_OLLAMA_URL = "http://localhost:11434/api/generate"
_TIMEOUT    = 30.0   # seconds

_warned_offline = False


def _model_name() -> str:
    try:
        data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        return data.get("ollama_model") or "gemma"
    except Exception:
        return "gemma"


def call(
    task_title: str,
    app_name: str,
    window_title: str,
    text_elements: list[str],
) -> str | None:
    """
    Returns the raw model response string or None on any failure.
    """
    global _warned_offline

    prompt = SYSTEM_PROMPT + "\n\n" + build_prompt(
        task_title, app_name, window_title, text_elements
    )

    payload = {
        "model":  _model_name(),
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 256},
    }

    try:
        resp = httpx.post(_OLLAMA_URL, json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
        _warned_offline = False  # reset if Ollama comes back online
        return resp.json().get("response")

    except httpx.ConnectError:
        if not _warned_offline:
            print("[ollama] Not reachable at localhost:11434. Start Ollama to enable local AI.")
            _warned_offline = True
        return None
    except httpx.TimeoutException:
        print("[ollama] Request timed out.")
        return None
    except Exception as e:
        print(f"[ollama] Error: {e}")
        return None
