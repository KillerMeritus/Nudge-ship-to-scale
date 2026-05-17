# plan

# PROJECT NUDGE — COMPLETE FEATURE SPECIFICATION

### Version 2.0 | May 2026

### For use with any AI model or developer

---

## SECTION 1 — PROJECT CONTEXT

Nudge is a privacy-first desktop productivity application for macOS and Windows. It combines a Pomodoro timer, task manager, AI-powered distraction detection, and daily activity summarisation into one unified tool. The core philosophy is that your data stays on your device. Everything runs locally except for an optional user-provided Gemini API key for AI features.

This document is the single source of truth for building Nudge. Any AI model or developer reading this should use it as the definitive reference and not contradict any decision without explicitly flagging it as a suggested change with a clear rationale.

---

## SECTION 2 — TECH STACK

### Frontend

- Framework: React
- Styling: Plain CSS modules — no Tailwind, no component library
- Charts: Chart.js
- Navigation: Single page app — no React Router, no tab routing. All views rendered conditionally on one page
- Theme: Dark mode only, fixed — no toggle, no system detection

### Backend

- Language: Python
- API framework: FastAPI
- Phase 1: REST only
- Phase 2: Add WebSocket for real-time distraction alerts and live activity feed
- No database in Phase 1 — all state kept in memory or simple JSON files
- Phase 2 onwards: SQLite with SQLAlchemy ORM

### Desktop Shell

- Tauri + React
- System tray icon on Windows via pystray
- Menu bar icon on macOS via rumps
- Full window accessible from tray/menu bar click
- Both tray icon and full window available simultaneously

### AI

- Phase 1: Gemini API — user provides their own personal Gemini API key in settings. No Ollama, no local model in Phase 1
- Phase 2: Migrate to fully local model via Ollama (Gemma as default). User can choose from Gemma, Mistral, Phi in settings

### Activity Monitoring

- Phase 1: Window title tracking via Python script running in background, connected to FastAPI via REST API. Captures app name and window title every 5 seconds
- Phase 2: Upgrade to full UI scrape using Accessibility API (macOS) and uiautomation (Windows) at depth 8, plus screenshot-based content extraction — already built and tested in Python, ready to integrate

### Notifications

- plyer for cross-platform desktop notification popups
- Sound notification on Pomodoro session end (both work and break)

### User Account

- Optional account structure planned for future cloud sync
- Phase 1 is fully local — no login required to use the app

### Startup

- Nudge launches automatically on system startup by default
- User can disable this in settings

---

## SECTION 3 — PHASE 1 FEATURES

Phase 1 is the basic version. No database, no local LLM, no background monitoring beyond a lightweight window title script. Ship it fast, get it working, then build on it.

---

### Feature 1 — Pomodoro Timer

**Default settings:**
- Work session: 25 minutes
- Short break: 5 minutes
- Long break: user decides — configurable in settings (suggested default: 15 minutes after 4 cycles)

**Behaviour:**
- Global timer — one timer for the entire app, not linked to a specific task
- Standalone — independent of the task list
- Pomodoro sessions are NOT tracked historically — it is a pure timer with no history or analytics
- When a work session ends: desktop notification popup + sound alert
- When a break ends: desktop notification popup + sound alert
- Long break is optional — user sets whether they want it and after how many cycles in settings
- No distraction blocking during Pomodoro — Nudge only notifies, never blocks apps or websites

**UI elements:**
- Large circular or ring countdown timer display
- Current session label: “Focus”, “Short Break”, “Long Break”
- Start / Pause / Reset buttons
- Session count indicator (e.g. Pomodoro 2 of 4)
- Settings button to configure durations and long break preference

---

### Feature 2 — CRUD Task Manager

---

**Task fields:**
- Title (required, text)
- Description (optional, plain text — no markdown, no rich text)
- Estimated time (optional, hours and minutes — e.g. 1h 30m)
- Priority (required — Low, Medium, High)
- Tags (optional — user types comma-separated tags)
- Status (Todo, In Progress, Done)
- Recurring flag (optional — user can mark a task as recurring)

**Display:**
- Simple vertical list view — no kanban, no calendar
- Drag to reorder manually within the list
- No due dates on tasks
- Flat list — no projects, no categories, no grouping
- All tasks shown in one list including completed ones — no automatic archiving
- Completed tasks shown with a strikethrough or faded style but remain in the list
- User can manually delete tasks

**Task behaviour:**
- No sub-tasks in Phase 1 — planned for Phase 2
- Recurring tasks: user marks a task as recurring — when marked done, it reappears in the list automatically the next day
- When a task is marked done: just mark it, no time tracking, no comparison against estimated time
- No time tracking per task in Phase 1

**CRUD operations:**
- Create: click add task button, fill fields in an inline form or modal
- Read: all tasks visible in the list
- Update: click task to edit any field inline or in a modal
- Delete: swipe or click delete button on each task

---

### Feature 3 — Basic FastAPI Backend

**Architecture:**
- FastAPI server running on localhost port 8080
- Python script running as a background process monitoring window titles
- Script sends current activity data to FastAPI endpoint
- React frontend polls FastAPI every 5 seconds to get current activity
- All state stored in memory — no database in Phase 1
- Tasks stored as a JSON file on disk (simple read/write, no SQLite)

**REST endpoints for Phase 1:**

```
GET  /health                  → server is alive check
GET  /activity/current        → current app name + window title
GET  /tasks                   → all tasks
POST /tasks                   → create new task
PUT  /tasks/{id}              → update task
DELETE /tasks/{id}            → delete task
POST /timer/start             → start Pomodoro session
POST /timer/pause             → pause timer
POST /timer/reset             → reset timer
GET  /timer/status            → current timer state and time remaining
POST /summary/generate        → trigger Gemini API call to generate summary
GET  /summary/latest          → get the most recently generated summary
GET  /settings                → get user settings
POST /settings                → save user settings (including Gemini API key)
```

**No WebSockets in Phase 1.** React polls REST endpoints on a fixed interval. WebSockets added in Phase 2 for real-time distraction alerts and live activity feed.

---

## SECTION 4 — PHASE 2 FEATURES

Phase 2 adds the intelligence layer. This is where Nudge becomes genuinely differentiated.

---

### Feature 1 — Distraction Detection

**How it works:**
- Python background script upgraded from simple window title polling to full UI scrape at depth 8 using Accessibility API (macOS) and uiautomation (Windows)
- Phase 2 also adds screenshot-based content extraction — already built and tested in Python, ready to integrate
- Script runs 24 hours a day, 7 days a week — not just during Pomodoro sessions
- Every 30 seconds, the script analyses current activity against a learned baseline of what productive work looks like for this user
- If distraction is detected: fires a desktop notification popup via plyer
- No sound on distraction alert — notification only
- No app blocking — notify only, user decides what to do

**What counts as a distraction:**
- Gemini API (Phase 1) or local LLM (Phase 2) analyses the window title and URL and compares it against the user’s current stated task or general productive patterns
- Examples: YouTube, social media, news sites, games — all flagged when user has active tasks
- Context-aware: if user is researching and opens a relevant article, it should not flag as distraction

**WebSocket upgrade:**
- In Phase 2, FastAPI adds a WebSocket endpoint for distraction alerts
- Python script sends alert → FastAPI broadcasts via WebSocket → React receives and shows notification instantly without polling

---

### Feature 2 — Daily Summary and Documentation

**Trigger:** On demand only — user clicks a “Generate Summary” button. No automatic end-of-day generation.

**Data source:** Window title activity log collected by background script throughout the day, stored in SQLite (added in Phase 2).

**AI:** Gemini API in Phase 1 transition, local Gemma via Ollama in full Phase 2.

**Format:** Structured sections with both a productivity score and qualitative content:

```
NUDGE DAILY SUMMARY — [Date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Productivity Score: 7.4 / 10

What You Worked On:
- [specific tasks and apps detected]

Deep Work Time: X hours Y minutes
Distraction Time: X hours Y minutes

Top Distractions:
- [specific apps or sites]

Biggest Distraction Pattern:
- [e.g. "You switched to YouTube consistently after 40 minutes of coding"]

One Suggestion for Tomorrow:
- [specific, actionable]
```

**Export:** User can export the summary as a Markdown file (.md) to any location on their device.

**Storage:** Summaries saved to SQLite in Phase 2 so user can view past summaries.

---

## SECTION 5 — FUTURE PLANS

### Notion Integration

Sync level not yet decided. Options under consideration: full two-way sync, push-only (completed tasks sent to Notion), or read-only (pull tasks from Notion into Nudge). Decision deferred to when Phase 2 is complete.

### Todo App Enhancements

Sub-tasks under parent tasks. More advanced task organisation. Possibly a separate dedicated todo view.

### Local LLM Migration

Move from Gemini API to fully local models via Ollama. User chooses from Gemma, Mistral, Phi in settings. No data leaves device. This is the Phase 2 AI upgrade.

### Opt-in Cloud AI Bridge

User explicitly selects a session record and chooses to share it with Claude or another cloud model for deeper analysis. Two-click confirmation before any data leaves the device.

### Real-time Avatar

Conversational AI presence in the bottom-right corner of the screen. Knows the user’s goals, watches progress, intervenes when distracted. Powered by local LLM with optional voice via Whisper (STT) and Piper TTS.

### Multiple Local Model Options

Support for Gemma, Mistral, Phi, LLaMA. User selects based on their hardware capability.

---

## SECTION 6 — UI STRUCTURE

### App Window — Dark Mode Only

**Top navigation bar (single page — no routing):**
- Timer tab
- Tasks tab
- Summary tab
- Settings tab

All tabs render on the same page by conditionally showing/hiding components. No URL changes.

**Timer tab:** Pomodoro timer UI — countdown ring, session label, controls, session counter.

**Tasks tab:** Full task list with add button, drag handles, status toggles, priority indicators, tag display.

**Summary tab:** Generate button, latest summary display with score and sections, export to Markdown button, past summaries list (Phase 2).

**Settings tab:**
- Gemini API key input (Phase 1)
- Local model selector — Gemma, Mistral, Phi (Phase 2)
- Pomodoro durations — work, short break, long break
- Long break after N cycles toggle
- Launch on startup toggle
- Distraction detection toggle (on/off)
- Idle threshold setting (default 120 seconds)

### System Tray / Menu Bar

**macOS menu bar:** Nudge icon with dropdown showing:
- Current activity (app + window title)
- Timer status and time remaining
- Start/Pause timer shortcut
- Open Nudge window
- Quit

**Windows system tray:** Same options in right-click context menu.

---

## SECTION 7 — DATA ARCHITECTURE

### Phase 1 — No Database

Tasks: stored as a single JSON file at a fixed local path. Read on app start, written on every change.

Settings: stored as a separate JSON file including Gemini API key.

Activity log: kept in memory only during the session. Lost on app restart. No persistence in Phase 1.

Timer state: kept in memory. Resets on restart.

### Phase 2 — SQLite + SQLAlchemy

Four tables:

activity_log: id, timestamp, app_name, window_title, url, ui_context, duration_seconds, is_idle

daily_summary: id, date, summary_text, productivity_score, deep_work_minutes, created_at

tasks: id, title, description, estimated_hours, estimated_minutes, priority, tags, status, is_recurring, created_at, completed_at

settings: id, key, value

---

## SECTION 8 — ACTIVITY MONITORING ARCHITECTURE

### Phase 1

A lightweight Python script polls the active window every 5 seconds using:
- macOS: NSWorkspace + Quartz via pyobjc
- Windows: pywin32 + psutil

Script sends current app name and window title to FastAPI via a REST POST request every 5 seconds. FastAPI stores the latest activity in memory and serves it to React via GET /activity/current.

No browser extension in Phase 1. No file watching in Phase 1.

### Phase 2 Upgrade

Python script upgraded to:
- UI Automation scrape at depth 8 on window change (not on fixed interval)
- macOS: Accessibility API via pyobjc
- Windows: uiautomation library
- Browser extension added for exact URL tracking
- File watcher added via watchdog library
- Screenshot-based content extraction integrated — already built and tested, ready to plug in
- All data written to SQLite
- FastAPI adds WebSocket endpoint for real-time push to React

---

## SECTION 9 — INSTRUCTIONS FOR AI MODELS READING THIS DOCUMENT

This is the complete and authoritative specification for Project Nudge as of May 2026. When helping build, extend, or improve Nudge, always follow these facts:

The product is called Nudge. It is a desktop app for macOS and Windows built with Tauri + React frontend and FastAPI Python backend.

Phase 1 has no database — JSON files only. Phase 2 adds SQLite.

Phase 1 uses Gemini API with user’s own API key — not Ollama, not a local model. Phase 2 migrates to local Gemma via Ollama.

Phase 1 has no background monitoring beyond a simple window title tracker connected to FastAPI via REST. Phase 2 adds full UI scrape, browser extension, file watcher, and screenshot extraction.

The Pomodoro timer is global, standalone, not linked to tasks, and has no historical tracking in Phase 1.

Tasks are flat list only — no projects, no sub-tasks in Phase 1. No due dates. Drag to reorder. Fields are title, description, estimated time (hours and minutes), priority, tags, status, recurring flag.

Completed tasks stay visible in the list with a visual indicator. User deletes manually.

Distraction detection runs 24/7 in Phase 2. Phase 1 has basic window tracking only. Alerts are desktop notification popups only — no blocking, no sound.

Daily summary is on-demand only. Format is structured sections plus a productivity score out of 10. Exported as Markdown.

UI is single page, dark mode only, React with plain CSS modules, Chart.js for charts.

FastAPI uses REST in Phase 1, adds WebSocket in Phase 2.

Nudge launches on startup by default. User can disable in settings.

No user login in Phase 1. Optional account structure planned for future cloud sync.

Notion integration sync level not yet decided — defer this decision.

Do not suggest adding a database to Phase 1. Do not suggest switching from Gemini API to a local model in Phase 1. Do not suggest adding routing to the React app. Do not suggest Tailwind or any component library — plain CSS modules only. Do not suggest due dates on tasks in Phase 1.

---