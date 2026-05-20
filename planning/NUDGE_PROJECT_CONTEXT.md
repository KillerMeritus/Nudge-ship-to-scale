# Nudge Project — Complete Context & Architecture

## Project Overview

**Nudge** is a privacy-first macOS/Windows desktop productivity app with:
- Pomodoro timer (25m focus / 5m short break / 15m long break)
- Task management (CRUD with time tracking)
- AI-powered distraction detection (Gemini or local Ollama)
- Daily AI-generated summaries with productivity score
- System tray integration
- All user data stays on-device (no cloud)

---

## 4-Layer Architecture

| Layer | Directory | Technology |
|-------|-----------|------------|
| **FE-1** — React UI | `src/` | React 19, Vite, Tailwind CSS, Tauri JS APIs |
| **FE-2** — Desktop Shell | `src-tauri/` | Rust, Tauri 2.x, system tray menu |
| **BE-1** — API Server | `backend/` | FastAPI, Pydantic, JSON file storage, FileLock |
| **BE-2** — Activity Monitor | `scraper/` | Python, pyobjc (macOS) / pywin32 (Windows), AI clients |

---

## Frontend Layer (FE-1): React UI

### Main App Shell
**File:** `src/App.jsx`
- Tab-based navigation (no React Router)
- 4 tabs: Timer, Tasks, Summary, Settings
- Sidebar with distraction badge on Summary tab
- Receives `setActiveTab` prop for programmatic navigation (e.g., Settings.jsx → Settings when API key missing)

### Components

**CurrentTask.jsx** (Timer tab)
- Circular timer display (MM:SS or HH:MM:SS format)
- Pomodoro mode selector buttons (only when no task active): Focus (25m) / Short Break (5m) / Long Break (15m)
- Play / Pause / Reset / Skip controls
- Active task display with elapsed time vs. estimated
- "Coming Up Next" sidebar (3 upcoming todo tasks)
- Tray menu integration: updates tray label every tick
- Listens for tray-emitted events (start/pause from system tray menu)

**TaskList.jsx** (Tasks tab)
- Add new task form: title + hours/minutes estimate
- Full task CRUD:
  - Checkbox toggle (Todo ↔ Done)
  - Inline edit title and time estimate
  - Delete with confirmation
  - Start/Pause/Resume buttons
- Active task highlighted with left border + background
- Time tracking: elapsed vs. estimated
- Tasks sorted with active task at top

**Summary.jsx** (Summary tab)
- Display generated AI summary (markdown formatted)
- Productivity score (0-10)
- Status indicator (Waiting / Done)
- "Generate Now" button with loading state
- "Export to Markdown" button
- Error banner with "Go to Settings" link if API key missing

**Settings.jsx** (Settings tab)
- **AI Configuration**: Model selection dropdown
  - Gemini: API key input (password field)
  - Ollama: Connection info for local model
- **System Settings**: Launch on startup toggle (syncs with Tauri autostart plugin)
- **Work Hours**: Start/end time pickers (scraper respects this)
- Save button with success alert

### State Management (React Context)

**TimerContext.jsx**
- State: `status` ("running"/"paused"/"idle"), `sessionType` ("focus"/"short_break"/"long_break"), `remainingSeconds`, `elapsedSeconds`, `sessionCount`
- Methods: `start()`, `pause()`, `reset()`, `changeMode()`, `skip()`
- Auto-advances session type: focus → short break → long break
- Long break every 4 cycles (configurable `long_break_after_cycles`)

**ActiveTaskContext.jsx**
- State: `activeTask` (full task object), `elapsedSeconds`, `taskStatus` ("idle"/"running"/"paused")
- Methods: `startTask(taskId)`, `pauseTask()`, `resumeTask()`, `clearTask()`
- Listens for 'system-wake' event from Tauri (auto-pauses on wake from sleep)
- Makes HTTP calls: POST `/tasks/{id}/start`, `/pause`, `/resume`

**SummaryContext.jsx**
- State: `summaryData` (markdown + score), `isGenerating` (boolean), `error` (string or null)
- Method: `generateSummary()` — calls POST `/summary/generate`

### API Client

**File:** `src/api/client.js`

**Mock Mode** (toggle `USE_MOCKS = false` to switch to live backend)
- All endpoints have fallback mock data matching the API contract
- Useful for frontend-only development without running backend
- Toggle value controls live vs. mock behavior

**Endpoints:**
- `getHealth()` → GET `/health`
- `getCurrentActivity()` → GET `/activity/current`
- `getTasks()` → GET `/tasks`
- `createTask(task)` → POST `/tasks`
- `updateTask(id, changes)` → PUT `/tasks/{id}`
- `deleteTask(id)` → DELETE `/tasks/{id}`
- `startTask(id)` → POST `/tasks/{id}/start`
- `pauseTask(id)` → POST `/tasks/{id}/pause`
- `resumeTask(id)` → POST `/tasks/{id}/resume`
- `getTimerStatus()` → GET `/timer/status`
- `startTimer()` → POST `/timer/start`
- `pauseTimer()` → POST `/timer/pause`
- `resetTimer()` → POST `/timer/reset`
- `generateSummary()` → POST `/summary/generate`
- `getLatestSummary()` → GET `/summary/latest`
- `getSettings()` → GET `/settings`
- `saveSettings(changes)` → POST `/settings`
- `getDistractionCount()` → GET `/distraction/today/count`

### Utilities

**notify.js** — Native desktop notifications
- Presets: POMODORO_COMPLETE, DEEP_WORK_STARTED, SUMMARY_GENERATED
- Wraps Tauri notification plugin
- Graceful fallback and permission handling

**sound.js** — Web Audio API synthesized tones
- No external audio files (zero latency)
- Three tone presets (pomodoro, deep_work, summary)
- Sine wave oscillators with attack/decay envelope
- Graceful fallback if AudioContext unavailable

### Styling

**global.css**
- Tailwind CSS base + custom utilities
- Material Symbols Outlined icon configuration
- Webkit scrollbar styling
- Full-height root layout

**tailwind.config.js**
- Material You color palette (custom colors)
- Font stack: Newsreader (serif), Inter (UI), Material Symbols
- Custom components for buttons, cards, inputs

---

## Desktop Shell Layer (FE-2): Tauri

### Rust Code

**File:** `src-tauri/src/main.rs`

**Tauri Commands:**
- `update_tray_timer(label: String)` — Update tray menu text with timer display (HH:MM:SS)

**Tray Menu:**
- "Start Focus" button → emits 'tray-start-focus' event to frontend
- "Pause Timer" button → emits 'tray-pause-timer' event to frontend

**Event Listeners:**
- Listens for 'system-wake' event (on wake from sleep) → auto-pauses active task via `pauseTask()`

**Plugins:**
- Autostart plugin integration (Settings.jsx manages via POST `/settings`)
- Notification plugin integration (notify.js uses this)
- Opener plugin (open external links)

### Build Configuration

**tauri.conf.json**
- App name, version, description
- Window configuration (size, position, icons)
- Security rules and capabilities
- Build targets (macOS, Windows)

---

## Backend Layer (BE-1): FastAPI Server

### Entry Point

**File:** `backend/main.py`

- FastAPI app named "Nudge API" listening on `127.0.0.1:8080`
- CORS middleware allows:
  - Tauri dev: `http://localhost:1420`
  - Vite dev: `http://localhost:5173`
  - Tauri production: `tauri://localhost`
- Lifespan context manager (startup/shutdown hooks)
- **Startup hook:** Resets recurring tasks marked "Done" from previous dates to "Todo"
- Includes 8 routers via APIRouter

### Routers & Endpoints

#### **tasks.py** (`/tasks`)
- **GET** `/tasks` — List all tasks
- **POST** `/tasks` — Create new task (auto-assigns UUID, sets created_at)
- **PUT** `/tasks/{task_id}` — Update task (partial or full update)
- **DELETE** `/tasks/{task_id}` — Delete task
- **POST** `/tasks/{task_id}/start` — Mark as running (auto-pauses other active task), record started_at
- **POST** `/tasks/{task_id}/pause` — Pause, accumulate elapsed_seconds, clear started_at
- **POST** `/tasks/{task_id}/resume` — Resume from paused state, update started_at

**Task Schema:**
```
{
  id: UUID,
  title: string,
  description: string,
  estimated_hours: int,
  estimated_minutes: int,
  priority: "Low" | "Medium" | "High",
  tags: list[string],
  status: "Todo" | "In Progress" | "Done",
  is_recurring: boolean,
  elapsed_seconds: int,
  task_status: "idle" | "running" | "paused",
  started_at: datetime | null,
  created_at: datetime,
  completed_at: datetime | null
}
```

**Key Behavior:** Only one task can be "running" at a time. Starting a task auto-pauses the previously active task.

#### **timer.py** (`/timer`)
- **POST** `/timer/start` — Start Pomodoro timer (focus session)
- **POST** `/timer/pause` — Pause timer (accumulates elapsed time)
- **POST** `/timer/reset` — Reset to idle, zero elapsed
- **POST** `/timer/skip` — Skip to next session type
- **GET** `/timer/status` — Current timer state

**Timer State Response:**
```
{
  status: "running" | "paused" | "idle",
  session_type: "focus" | "short_break" | "long_break",
  remaining_seconds: int,
  elapsed_seconds: int,
  session_count: int
}
```

**Configuration (from settings):**
- work_duration_minutes (default 25)
- short_break_minutes (default 5)
- long_break_minutes (default 15)
- long_break_after_cycles (default 4)

**Design Note:** Timer state is in-memory and resets on server restart (by design — no persistence).

#### **summary.py** (`/summary`)
- **POST** `/summary/generate` — Generate AI-powered daily summary
- **GET** `/summary/latest` — Get last generated summary

**Process:**
1. Calls POST `/scraper/snapshot` to ensure BE-2 writes daily_log_snapshot.json
2. Reads activity log from `scraper/data/daily_log_snapshot.json` (or fallback to daily_log.json)
3. Reads tasks and distraction events from today
4. Builds prompt with:
   - Task titles + elapsed times
   - Distraction list with timestamps
   - Raw activity (first 100 entries)
5. Calls either **Gemini 2.0 Flash** or **local Ollama** based on settings
6. Extracts productivity score from response (regex: "SCORE: X.X")
7. Returns Markdown-formatted summary with score badge

**Response:**
```
{
  summary: string (markdown),
  score: float (0-10),
  generated_at: datetime
}
```

**AI Configuration:**
- ai_model: "gemini" | "ollama"
- gemini_api_key: string (stored in plaintext in settings.json)
- ollama_model: string (default "qwen2.5:0.5b")

#### **distraction.py** (`/distraction`)
- **POST** `/distraction/alert` — Receive distraction alert from BE-2 scraper
- **GET** `/distraction/latest` — Get most recent alert
- **GET** `/distraction/today` — All alerts for today (newest first)
- **GET** `/distraction/today/count` — Count of alerts today
- **DELETE** `/distraction/today` — Clear today's alerts
- **POST** `/distraction/alerts/seen` — Mark all alerts as seen

**Alert Schema:**
```
{
  id: UUID,
  task_id: UUID | null,
  task_title: string | null,
  app_name: string,
  window_title: string,
  reason: string,
  distraction_category: "social_media" | "entertainment" | "news" | "gaming" | "unrelated_work",
  severity: "low" | "medium" | "high",
  timestamp: datetime,
  seen: boolean
}
```

**Storage:** In-memory deque (max 200 alerts per day) with auto-reset on date change.

#### **settings.py** (`/settings`)
- **GET** `/settings` — Get all settings
- **POST** `/settings` — Update settings (partial merge)
- **GET** `/settings/ollama-status` — Health check for Ollama at localhost:11434

**Settings Schema:**
```
{
  # Pomodoro
  work_duration_minutes: int,
  short_break_minutes: int,
  long_break_minutes: int,
  long_break_after_cycles: int,
  long_break_enabled: boolean,
  
  # Work Hours
  work_start_time: string (HH:MM),
  work_end_time: string (HH:MM),
  
  # Distraction
  distraction_detection_enabled: boolean,
  idle_threshold_seconds: int,
  distraction_whitelist: list[string],
  distraction_cooldown_seconds: int,
  
  # AI
  gemini_api_key: string,
  ai_model: "gemini" | "ollama",
  ollama_model: string,
  
  # System
  launch_on_startup: boolean
}
```

**Persistence:** Loaded from / saved to `backend/data/settings.json` (FileLock-protected).

#### **activity.py** (`/activity`)
- **GET** `/activity/current` — Latest activity snapshot from scraper
- **POST** `/activity/sleep-gap` — Record system sleep/wake gap (FE-2 calls on wake)
- **GET** `/activity/today` — In-memory activity log with sleep gap markers

**Data Source:** Reads from `scraper/data/current_activity.json` (live snapshot).

#### **scraper_control.py** (`/scraper`)
- **POST** `/scraper/snapshot` — Tell BE-2 to write daily_log_snapshot.json
- **POST** `/scraper/pause` — Pause scraper (on system sleep)
- **POST** `/scraper/resume` — Resume scraper (on system wake)

**Mechanism:** Writes command to `scraper/data/control.json` for BE-2 to read and execute.

#### **health.py** (`/health`)
- **GET** `/health` → `{"status": "ok"}`

### Storage Layer

**File:** `backend/storage/task_store.py`
- Load/save tasks from/to `backend/data/tasks.json`
- Uses FileLock for safe concurrent access
- Functions: `load_tasks()`, `save_tasks(tasks)`

**File:** `backend/storage/settings_store.py`
- Load/save settings from/to `backend/data/settings.json`
- Uses FileLock
- Functions: `load_settings()`, `save_settings(settings)`

### Shared State

**File:** `backend/state.py`
- Global `active_task_state` (dict): tracks the currently running task
- Methods: `set_active_task(task_id)`, `get_active_task()`, `clear_active_task()`
- Prevents race conditions between multiple routers accessing active task

---

## Scraper Layer (BE-2): Activity Monitor

### Entry Point

**File:** `scraper/main.py`

**Responsibilities:**
1. Poll active window every 5 seconds (configurable POLL_INTERVAL)
2. Capture: app name, window title, visible text elements
3. Write atomic snapshot to `scraper/data/current_activity.json` (for real-time reads)
4. Log daily activity to `scraper/data/daily_log.json` (for summary generation)
5. Monitor for distractions in background thread (`distraction_loop.py`)
6. Handle platform differences (macOS vs. Windows)
7. Respect control signals from BE-1 via `scraper/data/control.json`
8. Roll over logs on new calendar day (handles sleep/wake cycles)

**Design Pattern:** Atomic writes use temp file + fsync + `os.replace()` to ensure readers never see partial JSON.

### Platform-Specific Scrapers

#### **mac_scraper.py** (macOS)
- **Active app name:** AppleScript via `osascript`
- **Window title:** Accessibility API (special handling for Chrome/Safari/Firefox to extract URLs)
- **Text elements:** Deep Accessibility API (AXUIElement) traversal
  - Traverses AX tree up to 8 levels deep
  - Extracts AXValue and AXTitle attributes
  - Caps children at 50 per level to avoid freezing UI
  - Fallback to basic AppleScript if deep scraping fails

#### **windows_scraper.py** (Windows)
- **Active window:** win32gui + psutil
- **Text elements:** uiautomation with depth-8 traversal, 500ms budget, max 80 items
  - Walks foreground window AX tree
  - Collects EditControl and DocumentControl values (typed text, document content)
  - Hard time and element count limits prevent blocking
  - Naturally surfaces Electron app content (Notion, VS Code, Discord)
- **Background windows:** Enumerate all visible non-foreground windows (shows context)
- **Chat context extraction:** For WhatsApp/Telegram/Slack/Discord
  - Title parsing first (fast)
  - Fallback to shallow AX BFS if title doesn't carry contact name

### Idle Detection

**File:** `idle_detector.py`

- **macOS:** `ioreg -c IOHIDSystem` parsing for HIDIdleTime (nanoseconds → seconds)
- **Windows:** Windows API `GetLastInputInfo()` / `GetTickCount()`
- Configurable threshold (default 120 seconds from settings)

### Sensitive App Filtering

**File:** `whitelist.py`

Blocks these apps from activity logging (privacy):
- Password managers: 1Password, Bitwarden, Keychain, LastPass, Dashlane
- System: SecurityAgent, UserNotificationCenter, System Preferences/Settings
- Banking: Bank of America, Chase, Wells Fargo
- Case-insensitive partial matching

### Distraction Detection Loop

**File:** `distraction_loop.py`

**Background thread** (runs every 10 seconds):
1. Check if user has active task via `GET /timer/active-task`
2. Read current activity from `scraper/data/current_activity.json`
3. Skip communication apps (Zoom, Meet, Teams, Slack, Webex)
4. Skip whitelisted apps
5. Call AI classifier via `ai_client.classify_activity()` (Gemini or Ollama)
6. If distracted + not in cooldown (180s default), fire alert via `POST /distraction/alert`
7. Implement per-app-per-task cooldown to avoid spam

**Cooldown:** 180 seconds per app per task (configurable in settings).

### AI Integration

**File:** `scraper/ai/ai_client.py` (Factory Pattern)

**Entry point:** `classify_activity(current_activity, task_title)`
- Reads `ai_model` setting dynamically (switches between Gemini/Ollama live)
- Delegates to either `gemini_client.py` or `ollama_client.py`
- Validates response has required keys: `is_distracted`, `confidence`, `reason`, `distraction_category`, `severity`
- Strips markdown fences (```json ... ```)

#### **gemini_client.py** (Gemini 2.0 Flash)
- **URL:** `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent`
- **API Key:** Read from `backend/data/settings.json` on each call
- **Temperature:** 0.1, **Max tokens:** 256
- **System instruction:** "You are a productivity assistant..."
- **User prompt:** Task context + app/window/text info
- **Timeout:** 8 seconds
- **Rate-limiting:** Respects 429 errors with 30s backoff
- Uses httpx sync (no async)

#### **ollama_client.py** (Local Ollama)
- **URL:** `http://localhost:11434/api/generate`
- **Model:** Read from settings (default: `qwen2.5:0.5b`)
- **Temperature:** 0.1, **Max tokens:** 256
- **Timeout:** 30 seconds
- Merged system + user prompt sent as single prompt
- Warns once on startup if Ollama not running, then stays quiet

#### **prompts.py** (Prompt Templates)

**System Prompt:**
Instructs model to determine if current app/window is distraction from task, classify by category (social_media, entertainment, unrelated_work, communication, browsing, other), assign severity (low, medium, high), return valid JSON only.

**Input Prompt Format:**
```
Task: {task_title}
Active app: {app_name}
Window title: {window_title}
Visible text elements:
  - {text_element_1}
  - {text_element_2}
  ...
```

**Expected JSON Response:**
```json
{
  "is_distracted": boolean,
  "confidence": float (0-1),
  "reason": string,
  "distraction_category": string,
  "severity": string
}
```

---

## Data Persistence

### File Locations (all gitignored)

**Backend Data:**
- `backend/data/tasks.json` — Task list persistence
- `backend/data/settings.json` — User settings (includes Gemini API key in plaintext ⚠️)

**Scraper Data:**
- `scraper/data/current_activity.json` — Atomic snapshot (live window + text)
- `scraper/data/daily_log.json` — Chronological activity log (append-only)
- `scraper/data/previous_day_log.json` — Archived log from previous day
- `scraper/data/control.json` — IPC commands from BE-1 → BE-2

### Example Data Structures

**tasks.json:**
```json
[
  {
    "id": "uuid-1",
    "title": "Implement feature X",
    "status": "In Progress",
    "estimated_hours": 2,
    "estimated_minutes": 30,
    "elapsed_seconds": 3600,
    "task_status": "running",
    "started_at": "2026-05-18T10:30:00",
    ...
  }
]
```

**current_activity.json:**
```json
{
  "app_name": "Google Chrome",
  "window_title": "Claude Code - Anthropic",
  "text_elements": ["import React", "function App() {", ...],
  "timestamp": "2026-05-18T14:22:45"
}
```

**daily_log.json:**
```json
[
  {
    "app_name": "VS Code",
    "window_title": "main.py",
    "timestamp": "2026-05-18T09:00:00",
    "text_elements": [...]
  },
  ...
]
```

**control.json:**
```json
{
  "command": "pause" | "resume" | "snapshot",
  "executed": false
}
```

---

## Key Data Flows

### Task Lifecycle
```
FE-1 creates task → tasks.json
FE-1 clicks "Start" → POST /tasks/{id}/start
BE-1 updates shared state → active_task
BE-2 scraper reads active task title from tasks.json
FE-1 polls GET /timer/active-task to display running task + elapsed time
FE-1 clicks "Pause" → POST /tasks/{id}/pause
BE-1 accumulates elapsed_seconds, clears active state
FE-1 clicks "Done" → PUT /tasks/{id} (status=Done)
BE-1 sets completed_at timestamp
```

### Distraction Detection Lifecycle
```
BE-2 scraper polls window every 5s
→ captures window + text elements
→ writes atomic snapshot to current_activity.json
FE-1 polls GET /activity/current for display
BE-2 appends to daily_log.json
BE-2 distraction_loop thread (every 10s):
  → checks GET /timer/active-task
  → reads current_activity.json
  → calls AI classifier (Gemini or Ollama)
  → if distracted + cooldown expired
  → POSTs /distraction/alert
FE-1 polls GET /distraction/today/count for badge updates
```

### Summary Generation Lifecycle
```
FE-1 clicks "Generate Summary"
→ POST /summary/generate:
  → BE-1 calls POST /scraper/snapshot
  → BE-2 writes daily_log_snapshot.json
  → BE-1 reads snapshot + tasks + distraction alerts
  → builds prompt with context
  → calls Gemini or Ollama
  → extracts score, formats Markdown
  → caches in memory, returns to FE-1
FE-1 displays Markdown summary + score badge
```

---

## Critical Integration Points

1. **`backend/state.py`** — Shared active task prevents race conditions between task start/pause/resume endpoints and timer display

2. **`scraper/main.py._write_current_atomic()`** — Temp file + fsync + os.replace() ensures readers never see partial JSON during writes

3. **`scraper/data/control.json`** — IPC channel from BE-1 → BE-2 allows FE-2 and BE-1 to orchestrate scraper (pause/resume on sleep/wake)

4. **AI model switch is live** — Both distraction classification and summary generation read `ai_model` setting on each call (no restart needed)

5. **`src/api/client.js` USE_MOCKS toggle** — Allows FE-1 development without running BE-1

6. **Atomic writes in scraper** — Ensures concurrent reads from FE-1 and BE-1 don't see corrupted JSON

7. **Date rollover in scraper** — Compares first log entry date against today, archives previous log, starts fresh (handles sleep/wake correctly)

8. **Cooldown mechanism** — Per-app-per-task (180s default) prevents distraction alert spam

9. **Recurring task reset** — BE-1 startup hook resets completed recurring tasks from previous dates

---

## Development Workflow

### Branch Strategy
- **FE-1** (React UI): `fe1/*` branches
- **FE-2** (Tauri Desktop): `fe2/*` branches
- **BE-1** (FastAPI): `be1/*` branches
- **BE-2** (Scraper): `be2/*` branches

### Startup (4 Terminal Windows Required)

**1. Backend Server (BE-1):**
```bash
source backend/.venv/bin/activate
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8080 --reload
```

**2. Activity Scraper (BE-2):**
```bash
python3 -m scraper.main
```

**3. Desktop App (FE-1 + FE-2):**
```bash
npm run tauri dev
```

**4. Frontend Only (Offline Dev, FE-1 only):**
```bash
# Set USE_MOCKS = true in src/api/client.js
npm run dev
```

### API Documentation
When BE-1 is running: http://127.0.0.1:8080/docs (Swagger UI)

---

## Technology Stack Summary

| Layer | Frontend | Backend | Desktop |
|-------|----------|---------|---------|
| **Runtime** | Node.js (Vite) | Python 3.10+ | Rust (Tauri) |
| **Framework** | React 19 | FastAPI 0.115 | Tauri 2.x |
| **Styling** | Tailwind 3.4 | — | — |
| **State** | React Context | In-memory + JSON | — |
| **HTTP** | Fetch API | Uvicorn 0.30 | — |
| **Platform** | macOS / Windows | macOS / Windows | macOS / Windows |

---

## Security Notes

⚠️ **Plaintext API Keys:** Gemini API key stored in `backend/data/settings.json` in plaintext. Consider encrypting for production.

⚠️ **Accessibility Permissions:** macOS requires Accessibility permissions granted to app bundle. Windows UI Automation may require admin privileges in some contexts.

⚠️ **Local Storage:** All data stored on-device in JSON files. No encryption at rest (design choice for privacy-first approach).

---

This documentation was generated on **2026-05-18** from complete codebase exploration.
