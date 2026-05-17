#!/usr/bin/env python3
"""
windows_scraper.py — Gets active window info on Windows.

Phase 2 additions:
  - text_elements via uiautomation (depth-8, 500 ms hard budget, ≤80 items)
  - chat_with field: who the user is chatting to in WhatsApp/Telegram/Slack/Discord
  - Notion/Obsidian: page body text surfaces through the general AX traversal
"""

import re
import time
from typing import Optional

# Titles that belong to system chrome, not real user windows
_SYSTEM_TITLES = {
    "", "program manager", "windows shell experience host",
    "windows input experience", "snipping tool overlay",
    "action center", "start", "search", "task switching",
    "nvidia geforce overlay", "amd radeon overlay",
}

try:
    import win32gui
    import win32process
    import psutil
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False

try:
    import uiautomation as auto
    _HAS_UIAUT = True
except ImportError:
    _HAS_UIAUT = False


# ---------------------------------------------------------------------------
# Text element extraction — general AX traversal
# ---------------------------------------------------------------------------

def _extract_text_elements(
    max_elements: int = 80,
    time_budget_ms: int = 500,
    max_text_len: int = 200,
) -> list[str]:
    """
    Walk the foreground window's accessibility tree and collect visible text.

    Hard limits on both time and element count so this never blocks the scrape
    loop regardless of how large the target window's AX tree is.
    Electron apps (Notion, WhatsApp, Discord) expose their DOM through this
    same interface, so page content and message text surface naturally.
    """
    if not _HAS_UIAUT:
        return []

    deadline = time.monotonic() + time_budget_ms / 1000.0
    collected: list[str] = []
    seen: set[str] = set()

    def visit(ctrl, depth: int) -> None:
        if time.monotonic() > deadline or len(collected) >= max_elements:
            return
        if depth > 8:
            return

        try:
            name = (ctrl.Name or "").strip()[:max_text_len]
            if len(name) >= 2 and name not in seen:
                seen.add(name)
                collected.append(name)

            # EditControl and DocumentControl carry actual typed/rendered text
            # in their Value pattern — grab that too when available.
            if ctrl.ControlTypeName in ("EditControl", "DocumentControl"):
                try:
                    val = ctrl.GetValuePattern().Value.strip()[:max_text_len]
                    if len(val) >= 2 and val not in seen:
                        seen.add(val)
                        collected.append(val)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            # Cap fan-out per level so a single row of 200 toolbar buttons
            # doesn't eat the entire time budget.
            for child in ctrl.GetChildren()[:30]:
                if time.monotonic() > deadline:
                    return
                visit(child, depth + 1)
        except Exception:
            pass

    try:
        window = auto.GetForegroundControl()
        if window is not None:
            visit(window, 0)
    except Exception:
        pass

    return collected


# ---------------------------------------------------------------------------
# Chat context — who is the user talking to?
# ---------------------------------------------------------------------------

# Apps where we want to surface the conversation partner
_CHAT_APPS = {"whatsapp", "telegram", "slack", "discord"}

# Strings that appear as AX names in chat apps but are NOT contact/channel names
_CHAT_NOISE = {
    "whatsapp", "new chat", "search", "archived", "starred messages",
    "status", "calls", "chats", "notifications", "settings", "back",
    "menu", "attach", "emoji", "send", "more options",
}


def _chat_context_from_title(app_lower: str, window_title: str) -> Optional[str]:
    """
    Parse the window title for apps that embed the contact/channel name in it.

    Telegram  → title IS the contact name, may have "(3) " unread prefix
    Slack     → "#general | Workspace Name"
    Discord   → "Discord - Server / #channel" or "Discord - #channel"
    WhatsApp  → "WhatsApp" — useless, handled by AX fallback below
    """
    t = window_title.strip()

    if "telegram" in app_lower:
        # Strip leading unread badge: "(3) John Doe" → "John Doe"
        cleaned = re.sub(r"^\(\d+\)\s*", "", t).strip()
        return cleaned if cleaned and cleaned.lower() not in ("telegram", "") else None

    if "slack" in app_lower:
        # "#general | Workspace" → "#general"
        if "|" in t:
            left = t.split("|")[0].strip()
            return left or None
        return None

    if "discord" in app_lower:
        # "Discord - Server / #channel" → "#channel"
        # "Discord - #channel"          → "#channel"
        if " - " in t:
            right = t.split(" - ", 1)[1].strip()
            # Take last segment if there's a slash (server / channel)
            if "/" in right:
                right = right.split("/")[-1].strip()
            return right or None
        return None

    return None  # WhatsApp title is always "WhatsApp" — fall through to AX


def _chat_context_from_ax(budget_ms: int = 300) -> Optional[str]:
    """
    AX-tree fallback for WhatsApp (and any chat app whose title is uninformative).

    Does a shallow BFS (depth ≤ 4) looking for the first substantial text element
    that is not a known UI label. In WhatsApp Electron the contact/group name sits
    in the conversation header as a TextControl or GroupControl directly under the
    top-level pane — it is typically the first meaningful text we encounter.
    """
    if not _HAS_UIAUT:
        return None

    deadline = time.monotonic() + budget_ms / 1000.0

    try:
        window = auto.GetForegroundControl()
        if window is None:
            return None

        queue = [(window, 0)]
        while queue:
            if time.monotonic() > deadline:
                break
            ctrl, depth = queue.pop(0)
            if depth > 4:
                continue

            try:
                name = (ctrl.Name or "").strip()
                ctrl_type = ctrl.ControlTypeName

                if ctrl_type in ("TextControl", "GroupControl", "PaneControl"):
                    if (
                        len(name) > 1
                        and name.lower() not in _CHAT_NOISE
                        and not name.isdigit()
                    ):
                        return name

                for child in ctrl.GetChildren():
                    queue.append((child, depth + 1))
            except Exception:
                continue

    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# Background window enumeration
# ---------------------------------------------------------------------------

def _get_background_windows(foreground_hwnd: int) -> list[dict]:
    """
    Return titles of all visible, non-minimised windows except the foreground one.

    Why: the scraper only deep-scrapes the foreground window, but the AI needs
    to know everything the user has open — e.g. VS Code in the background while
    Chrome is foreground. win32gui.EnumWindows is fast (< 5 ms) and requires
    no elevated privileges.

    VS Code note: VS Code exposes almost nothing via UIA (its editor is a
    custom canvas renderer). The window title alone — "filename — project —
    Visual Studio Code" — is the best signal available without a VS Code
    extension. We surface it here so the AI always knows what file is open.
    """
    if not _HAS_WIN32:
        return []

    results: list[dict] = []

    def _cb(hwnd, _):
        if hwnd == foreground_hwnd:
            return True                          # skip the foreground window
        if not win32gui.IsWindowVisible(hwnd):
            return True                          # skip invisible windows
        title = win32gui.GetWindowText(hwnd).strip()
        if not title or title.lower() in _SYSTEM_TITLES:
            return True                          # skip system chrome
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            app = psutil.Process(pid).name().replace(".exe", "")
        except Exception:
            app = "Unknown"
        results.append({"app_name": app, "window_title": title})
        return True

    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:
        pass

    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def get_active_window() -> dict:
    if not _HAS_WIN32:
        return {
            "app_name": "Unknown",
            "window_title": "Unknown",
            "text_elements": [],
            "_fallback_reason": "pywin32/psutil not installed",
        }

    try:
        hwnd = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        app_name = proc.name().replace(".exe", "")
        app_lower = app_name.lower()

        text_elements = _extract_text_elements(
            max_elements=80,
            time_budget_ms=500,
            max_text_len=200,
        )

        result: dict = {
            "app_name": app_name,
            "window_title": window_title or app_name,
            "text_elements": text_elements,
            # All other visible windows the user has open — gives the AI full
            # context even when VS Code / Notion / etc. are in the background.
            "background_windows": _get_background_windows(hwnd),
        }

        # For chat apps surface who the user is talking to.
        # Try window-title parse first (fast, no AX call needed).
        # Fall back to shallow AX BFS for apps like WhatsApp whose title
        # never carries the contact name.
        if any(chat in app_lower for chat in _CHAT_APPS):
            chat_with = _chat_context_from_title(app_lower, window_title)
            if not chat_with:
                chat_with = _chat_context_from_ax(budget_ms=300)
            if chat_with:
                result["chat_with"] = chat_with

        return result

    except Exception as e:
        return {
            "app_name": "Unknown",
            "window_title": "Unknown",
            "text_elements": [],
            "_error": str(e),
        }
