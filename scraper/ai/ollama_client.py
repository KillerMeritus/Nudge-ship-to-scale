"""
ollama_client.py — Local Ollama client for distraction classification.

Sends a single prompt (system + user merged) to localhost:11434/api/generate.
Falls back silently when Ollama is not running — warn once, then stay quiet.
"""

import json
from pathlib import Path
from datetime import datetime
import httpx

from scraper.ai.prompts import SYSTEM_PROMPT, build_prompt

_SETTINGS_FILE = Path(__file__).parent.parent.parent / "backend" / "data" / "settings.json"
_LOG_FILE = Path(__file__).parent.parent / "data" / "distraction.log"

_OLLAMA_URL = "http://localhost:11434/api/generate"
_TIMEOUT    = 30.0   # seconds

_warned_offline = False


def _log(message: str, level: str = "INFO"):
    """Log a message to the console and to distraction.log with timestamps."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [{level}] [ollama_client] {message}"
    print(formatted)
    try:
        _LOG_FILE.parent.mkdir(exist_ok=True)
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception as e:
        print(f"[{timestamp}] [ERROR] Failed to write to log file: {e}")


def _model_name() -> str:
    try:
        if _SETTINGS_FILE.exists():
            data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            return data.get("ollama_model") or "gemma3:1b"
        return "gemma3:1b"
    except Exception:
        return "gemma3:1b"


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

    model = _model_name()
    prompt = SYSTEM_PROMPT + "\n\n" + build_prompt(
        task_title, app_name, window_title, text_elements
    )

    payload = {
        "model":  model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1, "num_predict": 256},
    }

    _log(f"Sending request to local Ollama API (Model: '{model}', Timeout: {_TIMEOUT}s)...", "INFO")
    try:
        resp = httpx.post(_OLLAMA_URL, json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
        
        _warned_offline = False  # reset if Ollama comes back online
        raw_text = resp.json().get("response", "")
        _log(f"Received response from local Ollama: {raw_text.strip()[:100]}...", "DEBUG")
        return raw_text

    except httpx.ConnectError:
        if not _warned_offline:
            _log("Ollama API is not reachable at localhost:11434. Please start Ollama desktop application to use local AI models.", "ERROR")
            _warned_offline = True
        return None
    except httpx.TimeoutException:
        _log(f"Request timed out after {_TIMEOUT} seconds. Ensure Ollama isn't hung loading or running the model '{model}'.", "ERROR")
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            _log(f"Model not found (404) in Ollama! You likely need to run: 'ollama pull {model}' in your terminal.", "ERROR")
        else:
            _log(f"HTTP error from Ollama: {e.response.status_code} - {e.response.text}", "ERROR")
        return None
    except Exception as e:
        _log(f"Unexpected error calling local Ollama API: {e}", "ERROR")
        return None
