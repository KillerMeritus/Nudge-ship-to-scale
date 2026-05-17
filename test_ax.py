import AppKit
import ApplicationServices

def test():
    workspace = AppKit.NSWorkspace.sharedWorkspace()
    active_app = workspace.frontmostApplication()
    pid = active_app.processIdentifier()
    print("PID:", pid)
    
    app_ref = ApplicationServices.AXUIElementCreateApplication(pid)
    print("AppRef:", app_ref)
    
    err, window = ApplicationServices.AXUIElementCopyAttributeValue(app_ref, "AXFocusedWindow", None)
    print("FocusedWindow err:", err, window)

test()
