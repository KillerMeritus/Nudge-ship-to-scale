# Distraction Alert System — Full Audit & Fix Plan

## Status Summary

The distraction alert system is **~85% built** across all 4 layers. The code is architecturally sound, but there are **3 critical blockers** and **4 minor gaps** preventing it from working end-to-end.

---

## What's Already Done ✅

### Layer 1 — Scraper (BE-2) `scraper/`
| Component | Status | File |
|---|---|---|
| macOS window scraper | ✅ Working | [mac_scraper.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/mac_scraper.py) |
| Windows scraper | ✅ Written | [windows_scraper.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/windows_scraper.py) |
| Activity polling loop (5s) | ✅ Working | [main.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/main.py) |
| Atomic file write | ✅ Working | [main.py L31-58](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/main.py#L31-L58) |
| Privacy whitelist | ✅ Working | [whitelist.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/whitelist.py) |
| Idle detection (macOS/Windows) | ✅ Working | [idle_detector.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/idle_detector.py) |
| Daily log with date-aware reset | ✅ Working | [main.py L106-148](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/main.py#L106-L148) |
| Distraction loop thread (10s) | ✅ Written | [distraction_loop.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/distraction_loop.py) |
| Per-app-per-task cooldown (180s) | ✅ Written | [distraction_loop.py L99-120](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/distraction_loop.py#L99-L120) |
| Communication app skip | ✅ Written | [distraction_loop.py L66-67](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/distraction_loop.py#L66-L67) |

### Layer 2 — AI Classification `scraper/ai/`
| Component | Status | File |
|---|---|---|
| Factory (Gemini/Ollama switch) | ✅ Working | [ai_client.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/ai/ai_client.py) |
| Response parser (fence stripping, validation) | ✅ Working | [ai_client.py L31-58](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/ai/ai_client.py#L31-L58) |
| Gemini 2.0 Flash client | ✅ Working | [gemini_client.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/ai/gemini_client.py) |
| Ollama local client | ✅ Working | [ollama_client.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/ai/ollama_client.py) |
| Prompt templates | ✅ Working | [prompts.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/ai/prompts.py) |
| Rate-limiting (429 backoff) | ✅ Working | [gemini_client.py L61-64](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/ai/gemini_client.py#L61-L64) |

### Layer 3 — Backend API (BE-1) `backend/`
| Component | Status | File |
|---|---|---|
| `POST /distraction/alert` (receive alerts) | ✅ Working | [distraction.py L60-74](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/backend/routers/distraction.py#L60-L74) |
| `GET /distraction/latest` | ✅ Working | [distraction.py L77-81](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/backend/routers/distraction.py#L77-L81) |
| `GET /distraction/today` | ✅ Working | [distraction.py L84-91](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/backend/routers/distraction.py#L84-L91) |
| `GET /distraction/today/count` | ✅ Working | [distraction.py L104-111](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/backend/routers/distraction.py#L104-L111) |
| `DELETE /distraction/today` | ✅ Working | [distraction.py L94-101](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/backend/routers/distraction.py#L94-L101) |
| `POST /distraction/alerts/seen` | ✅ Working | [distraction.py L114-120](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/backend/routers/distraction.py#L114-L120) |
| `GET /timer/active-task` | ✅ Working | [timer.py L120-129](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/backend/routers/timer.py#L120-L129) |
| In-memory deque store (200 max) | ✅ Working | [distraction.py L28-29](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/backend/routers/distraction.py#L28-L29) |
| Day-rollover auto-reset | ✅ Working | [distraction.py L33-43](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/backend/routers/distraction.py#L33-L43) |

### Layer 4 — Frontend (FE-1 + FE-2) `src/` + `src-tauri/`
| Component | Status | File |
|---|---|---|
| In-app toast (polls `/distraction/latest`) | ✅ Working | [DistractionToast.jsx](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/src/components/DistractionToast/DistractionToast.jsx) |
| Sidebar distraction badge (polls count) | ✅ Working | [App.jsx L26-44](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/src/App.jsx#L26-L44) |
| Badge display on Summary tab | ✅ Working | [App.jsx L73-81](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/src/App.jsx#L73-L81) |
| Severity-based toast styling | ✅ Working | [DistractionToast.jsx L42-53](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/src/components/DistractionToast/DistractionToast.jsx#L42-L53) |
| Native OS notification (Rust tray poller) | ✅ Written | [lib.rs L374-457](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/src-tauri/src/lib.rs#L374-L457) |
| Tray menu distraction counter | ✅ Written | [lib.rs L78-79](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/src-tauri/src/lib.rs#L78-L79) |

---

## Critical Blockers 🚨

### 🔴 Blocker 1 — osascript Timeout Kills Scraping Data

**Evidence:** The [current_activity.json](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/data/current_activity.json) on disk right now contains:
```json
{
  "app_name": "Google Chrome",
  "window_title": "Google Chrome",
  "text_elements": [],
  "_fallback_reason": "Command ... timed out after 5 seconds"
}
```

**Impact:** When `osascript` times out (common on macOS with Chrome), the scraper falls back to a **bare-bones result** with:
- `window_title` = just the app name (no tab title, no URL)
- `text_elements` = `[]` (empty)

The distraction loop then feeds this to the AI, which gets: `"App: Google Chrome, Window: Google Chrome, text: (none)"`. That's **not enough context** for the AI to distinguish YouTube from GitHub — it will almost always return `is_distracted: false` because it can't tell what the user is actually looking at.

**Root Cause:** The AppleScript approach in [mac_scraper.py L69-109](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/mac_scraper.py#L69-L109) sends a large multi-branch script via `osascript`. On macOS Sequoia+, `osascript` frequently takes >5s to execute when Chrome has many tabs open, or when Accessibility permissions are being re-negotiated.

**Fix:**
- Split the AppleScript into separate focused scripts (one for app name, one for Chrome tab title/URL)
- Increase timeout from 5s to 8s
- Cache the last successful window title and reuse it on timeout instead of falling back to bare app name
- Also ensure Accessibility API (`get_text_elements`) is called even on fallback, since it uses a separate code path via `pyobjc`

---

### 🔴 Blocker 2 — `distraction_detection_enabled` Setting Is Never Checked

**Evidence:** `grep -r "distraction_detection_enabled" scraper/` returns **zero hits**.

**Impact:** Even when the user toggles distraction detection OFF in Settings, the distraction loop keeps running and firing alerts. Conversely, the UI toggle gives a false sense of control.

More importantly, the distraction loop in [distraction_loop.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/distraction_loop.py) **never reads settings at all** — it doesn't check:
- `distraction_detection_enabled` (on/off toggle)
- `distraction_cooldown_seconds` (user-configurable cooldown — hardcoded to 180s on L102)
- `distraction_whitelist` (user-defined app whitelist — only the hardcoded `whitelist.py` is checked)

**Fix:** At the top of each `_loop()` iteration, read `settings.json` and:
1. Skip the entire cycle if `distraction_detection_enabled` is `false`
2. Use `distraction_cooldown_seconds` instead of hardcoded `180`
3. Merge `distraction_whitelist` with the hardcoded list when checking `is_whitelisted()`

---

### 🔴 Blocker 3 — Distraction Loop Gets No Active Task from `/timer/active-task`

**Evidence:** In [distraction_loop.py L19-26](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/distraction_loop.py#L19-L26), `_check_active_task()` calls `GET http://127.0.0.1:8080/timer/active-task`, which returns the task dict set by [state.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/backend/state.py). But the response only has a task if `state.set_active_task()` was called — which only happens when the user clicks **Start** on a task in the UI.

**Impact:** If the user hasn't explicitly started a task (or has paused it), `_check_active_task()` returns `None` → the entire distraction loop iteration is skipped via `continue` on [L52](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/distraction_loop.py#L52). **No AI classification ever runs. No alerts ever fire.**

This is the **single biggest reason** distraction alerts aren't working — users must have an actively running task for the system to engage.

**Fix Options:**

> [!IMPORTANT]
> **Design Decision Required:** Should distraction detection work only during active task sessions, or should it also run during Pomodoro focus sessions even without a specific task started?

- **Option A (Recommended):** Keep the requirement but make it more visible. Add a UI hint like *"Start a task to enable distraction detection"* on the timer page. This is the designed behavior per the spec.
- **Option B:** Allow detection without an active task by using a generic "Focus Time" label when no task is set but the Pomodoro timer is running in focus mode.

---

## Minor Gaps ⚠️

### 1. Settings UI Missing Controls for Distraction Detection

The [Settings.jsx](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/src/components/Settings/Settings.jsx) component is missing UI controls for:
- `distraction_detection_enabled` toggle
- `distraction_cooldown_seconds` input
- `distraction_whitelist` input (add/remove apps)

These settings exist in the backend ([settings_store.py L23-29](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/backend/storage/settings_store.py#L23-L29)) but have no UI to change them.

### 2. No `httpx` Dependency Check in Scraper

The [gemini_client.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/ai/gemini_client.py) and [ollama_client.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/ai/ollama_client.py) both `import httpx`. If `httpx` isn't installed in the scraper's environment, the AI clients silently fail.

### 3. Current AI Model Is Set to `ollama` But Ollama May Not Be Running

The [settings.json](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/backend/data/settings.json) has `"ai_model": "ollama"`. If Ollama is not installed/running on the machine, every AI classification call returns `None`, and **no distraction is ever detected**.

### 4. API Client Missing Distraction Methods

The frontend [client.js](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/src/api/client.js) doesn't have `getDistractionCount()`, `getDistractions()`, or `clearDistractions()` methods. The App.jsx uses raw `fetch()` calls instead. This is a consistency issue, not a blocker.

---

## Proposed Fix Plan (Priority Order)

### Phase 1 — Make It Work (Critical Path)

#### [MODIFY] [mac_scraper.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/mac_scraper.py)
- Split AppleScript into smaller focused scripts
- Increase timeout to 8s
- Cache last successful window title/URL for reuse on timeout
- Ensure `text_elements` are collected even on partial fallback

#### [MODIFY] [distraction_loop.py](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/scraper/distraction_loop.py)
- Read `settings.json` each loop iteration
- Check `distraction_detection_enabled` before running
- Use `distraction_cooldown_seconds` from settings (not hardcoded 180)
- Merge `distraction_whitelist` from settings with hardcoded whitelist
- Add structured logging for debugging (which step was reached, what the AI returned)

---

### Phase 2 — Settings UI

#### [MODIFY] [Settings.jsx](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/src/components/Settings/Settings.jsx)
- Add "Distraction Detection" toggle (`distraction_detection_enabled`)
- Add cooldown seconds input (`distraction_cooldown_seconds`)
- Add whitelist tag input (`distraction_whitelist`)

---

### Phase 3 — Polish

#### [MODIFY] [client.js](file:///Users/viveksarathe/Desktop/Asscent%20/Ship-to-scale/src/api/client.js)
- Add `getDistractionCount()`, `getDistractions()`, `clearDistractions()` methods
- Refactor `App.jsx` and `DistractionToast.jsx` to use the API client

---

## Verification Plan

### Automated Tests
- Run `python3 -c "from scraper.ai.ai_client import classify_activity; print(classify_activity('Write README', 'YouTube', 'Funny Cats - YouTube', ['Subscribe', 'Like']))"` to verify AI classification works end-to-end
- Run `python3 -m py_compile scraper/distraction_loop.py` to verify syntax
- Run `npm run build` to verify frontend compiles

### Manual Verification
1. Start a task in the Nudge UI
2. Switch to YouTube or Twitter
3. Wait 10-15 seconds
4. Observe: in-app toast should appear, native macOS notification should fire, sidebar badge should increment
5. Toggle distraction detection OFF in settings → alerts should stop
