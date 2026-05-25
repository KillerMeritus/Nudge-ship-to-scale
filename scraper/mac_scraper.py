#!/usr/bin/env python3
"""
mac_scraper.py — Gets active window info on macOS using AppleScript via osascript.
Also extracts deep UI text elements using Accessibility API (AXUIElement).
Returns: { app_name, window_title, text_elements }

Resilience strategy:
  - Two-stage AppleScript: first get app name (fast, reliable), then get
    browser tab title/URL (slower, may time out with many tabs).
  - Caches last successful window title so timeouts don't destroy context.
  - Always attempts AX text element collection even on partial fallback.
"""

import subprocess

# Try to import accessibility frameworks for depth-8 text scraping
try:
    import AppKit
    import ApplicationServices
    _HAS_AX = True
except ImportError:
    _HAS_AX = False

# ── Cache: last successful scrape per app ─────────────────────────────────────
# Key = app_name, Value = {"window_title": str, "url": str}
# Prevents timeouts from wiping out useful context for the AI.
_last_good: dict = {}

_SCRIPT_TIMEOUT = 8  # seconds (up from 5)


def get_text_elements(depth=8) -> list:
    """Extracts text elements from the currently focused window up to `depth` levels deep."""
    if not _HAS_AX:
        return []
        
    try:
        workspace = AppKit.NSWorkspace.sharedWorkspace()
        active_app = workspace.frontmostApplication()
        pid = active_app.processIdentifier()
        app_ref = ApplicationServices.AXUIElementCreateApplication(pid)
        
        elements = set()
        
        def traverse(element, current_depth):
            if current_depth > depth:
                return
                
            err, role = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXRole", None)
            if err != 0 or not role:
                return
                
            # Try to grab value
            err, val = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXValue", None)
            if err == 0 and val and isinstance(val, str) and val.strip():
                elements.add(val.strip())
            else:
                # Try to grab title
                err, title = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXTitle", None)
                if err == 0 and title and isinstance(title, str) and title.strip():
                    elements.add(title.strip())
            
            # Recurse through children
            err, children = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXChildren", None)
            if err == 0 and children:
                # Limit the number of children to avoid freezing on massive lists
                for child in list(children)[:50]: 
                    traverse(child, current_depth + 1)

        err, window = ApplicationServices.AXUIElementCopyAttributeValue(app_ref, "AXFocusedWindow", None)
        if err == 0 and window:
            traverse(window, 1)
        else:
            err, window = ApplicationServices.AXUIElementCopyAttributeValue(app_ref, "AXMainWindow", None)
            if err == 0 and window:
                traverse(window, 1)
                
        return list(elements)
    except Exception:
        return []


# ── Stage 1: Get frontmost app name (fast, reliable) ─────────────────────────

def _get_frontmost_app() -> str:
    """Return the name of the frontmost application. Rarely fails."""
    script = 'tell application "System Events" to get name of first process whose frontmost is true'
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5,
        )
        name = result.stdout.strip()
        return name if name else "Unknown"
    except Exception:
        return "Unknown"


# ── Stage 2: Get browser tab title + URL (slower, may time out) ──────────────

_BROWSER_SCRIPTS = {
    "Google Chrome": '''
        tell application "Google Chrome"
            if (count of windows) > 0 then
                return (title of active tab of front window) & "|||" & (URL of active tab of front window)
            end if
        end tell
        return "|||"
    ''',
    "Brave Browser": '''
        tell application "Brave Browser"
            if (count of windows) > 0 then
                return (title of active tab of front window) & "|||" & (URL of active tab of front window)
            end if
        end tell
        return "|||"
    ''',
    "Safari": '''
        tell application "Safari"
            if (count of windows) > 0 then
                return (name of front document) & "|||" & (URL of front document)
            end if
        end tell
        return "|||"
    ''',
    "Arc": '''
        tell application "Arc"
            if (count of windows) > 0 then
                return (title of active tab of front window) & "|||" & (URL of active tab of front window)
            end if
        end tell
        return "|||"
    ''',
    "Firefox": '''
        tell application "System Events"
            tell process "Firefox"
                try
                    return name of front window & "|||"
                end try
            end tell
        end tell
        return "|||"
    ''',
}

_GENERIC_WINDOW_SCRIPT = '''
    tell application "System Events"
        try
            return name of front window of application process "{app}" & "|||"
        end try
    end tell
    return "|||"
'''


def _get_window_details(app_name: str) -> tuple[str, str]:
    """
    Return (window_title, url) for the given app.
    Falls back to cached data on timeout. Returns ("", "") on total failure.
    """
    if app_name in _BROWSER_SCRIPTS:
        script = _BROWSER_SCRIPTS[app_name]
    else:
        script = _GENERIC_WINDOW_SCRIPT.format(app=app_name.replace('"', '\\"'))

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=_SCRIPT_TIMEOUT,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split("|||")
            title = parts[0] if parts[0] and parts[0] != "missing value" else ""
            url = parts[1].strip() if len(parts) > 1 and parts[1].strip() != "missing value" else ""

            # Cache successful result
            if title:
                _last_good[app_name] = {"window_title": title, "url": url}

            return title, url

    except subprocess.TimeoutExpired:
        print(f"[mac_scraper] Window detail script timed out for {app_name} — using cached data.")
    except Exception as e:
        print(f"[mac_scraper] Window detail error for {app_name}: {e}")

    # Fall back to cache
    cached = _last_good.get(app_name, {})
    return cached.get("window_title", ""), cached.get("url", "")


# ── Public entry point ────────────────────────────────────────────────────────

def get_active_window() -> dict:
    """
    Two-stage scrape:
      1. Get the frontmost app name (fast, almost never fails)
      2. Get window title + URL (may time out for browsers with many tabs)
         → falls back to cached data from the last successful scrape
      3. Always collect text_elements via Accessibility API (separate path)
    """
    # Stage 1 — app name
    app_name = _get_frontmost_app()

    # Stage 2 — window details (with cache fallback)
    window_title, url = _get_window_details(app_name)

    if not window_title:
        window_title = app_name  # last-resort: use app name as title

    if url:
        window_title = f"{window_title} [{url}]"

    # Stage 3 — text elements (Accessibility API, separate code path)
    text_elements = get_text_elements(depth=8)

    return {
        "app_name": app_name,
        "window_title": window_title,
        "text_elements": text_elements,
    }
