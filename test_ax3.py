import AppKit
import ApplicationServices
import sys

def get_text_elements(depth=8):
    workspace = AppKit.NSWorkspace.sharedWorkspace()
    active_app = workspace.frontmostApplication()
    pid = active_app.processIdentifier()
    app_ref = ApplicationServices.AXUIElementCreateApplication(pid)
    
    elements = []
    
    def traverse(element, current_depth):
        if current_depth > depth:
            return
            
        err, role = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXRole", None)
        if err != 0 or not role:
            return
            
        err, val = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXValue", None)
        if err == 0 and val and isinstance(val, str) and val.strip():
            elements.append(val.strip())
        else:
            err, title = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXTitle", None)
            if err == 0 and title and isinstance(title, str) and title.strip():
                elements.append(title.strip())
        
        err, children = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXChildren", None)
        if err == 0 and children:
            for child in children:
                traverse(child, current_depth + 1)

    try:
        err, window = ApplicationServices.AXUIElementCopyAttributeValue(app_ref, "AXFocusedWindow", None)
        if err == 0 and window:
            traverse(window, 1)
        else:
            err, window = ApplicationServices.AXUIElementCopyAttributeValue(app_ref, "AXMainWindow", None)
            if err == 0 and window:
                traverse(window, 1)
    except Exception as e:
        pass
        
    return list(set(elements))

print(get_text_elements())
