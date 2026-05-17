#!/usr/bin/env python3
"""
mac_scraper.py — Gets active window info on macOS using AppleScript via osascript.
Also extracts deep UI text elements using Accessibility API (AXUIElement).
Returns: { app_name, window_title, text_elements }
"""

import subprocess

# Try to import accessibility frameworks for depth-8 text scraping
try:
    import AppKit
    import ApplicationServices
    _HAS_AX = True
except ImportError:
    _HAS_AX = False

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

def get_active_window() -> dict:
    script = '''
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
    end tell

    set windowTitle to ""
    set windowUrl to ""

    try
        if frontApp is "Google Chrome" then
            tell application "Google Chrome"
                if (count of windows) > 0 then
                    set windowTitle to title of active tab of front window
                    set windowUrl to URL of active tab of front window
                end if
            end tell
        else if frontApp is "Brave Browser" then
            tell application "Brave Browser"
                if (count of windows) > 0 then
                    set windowTitle to title of active tab of front window
                    set windowUrl to URL of active tab of front window
                end if
            end tell
        else if frontApp is "Safari" then
            tell application "Safari"
                if (count of windows) > 0 then
                    set windowTitle to name of front document
                    set windowUrl to URL of front document
                end if
            end tell
        else
            tell application "System Events"
                try
                    set windowTitle to name of front window of application process frontApp
                end try
            end tell
        end if
    end try

    return frontApp & "|||" & windowTitle & "|||" & windowUrl
    '''
    
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            parts = result.stdout.strip().split("|||")
            app_name = parts[0] if parts[0] else "Unknown"
            window_title = parts[1] if len(parts) > 1 and parts[1] and parts[1] != "missing value" else app_name
            url = parts[2] if len(parts) > 2 and parts[2] != "missing value" else ""
            
            if url:
                window_title = f"{window_title} [{url}]"
                
            # Get text elements from accessibility tree (Depth 8)
            text_elements = get_text_elements(depth=8)
                
            return {
                "app_name": app_name,
                "window_title": window_title,
                "text_elements": text_elements,
            }
    except Exception as e:
        return _fallback(str(e))

    return _fallback("osascript failed or returned non-zero")

def _fallback(reason: str = "osascript not available") -> dict:
    """Return basic info using basic AppleScript as a fallback."""
    try:
        script = 'tell application "System Events" to get name of first process whose frontmost is true'
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
        app_name = result.stdout.strip() or "Unknown"
    except Exception:
        app_name = "Unknown"

    return {
        "app_name": app_name,
        "window_title": app_name,
        "text_elements": [],
        "_fallback_reason": reason,
    }
