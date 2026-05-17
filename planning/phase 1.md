# NUDGE — IMPLEMENTATION PLAN v2.0
### Team of 4 | May 2026
### Built for hackathon delivery — Phase 1 priority

---

## TEAM ASSIGNMENTS

| Person | Role | Branch Prefix |
|--------|------|---------------|
| FE-1 | React UI — Timer, Tasks, Summary tabs | `fe1/` |
| FE-2 | Tauri shell, system tray, desktop setup | `fe2/` |
| BE-1 | FastAPI server, all REST endpoints, JSON storage | `be1/` |
| BE-2 | Python scraper, Ollama/Gemma integration, distraction detection | `be2/` |

---

## FILE STRUCTURE

```
nudge/
├── src-tauri/                        ← FE-2 owns entirely
│   ├── src/
│   │   └── main.rs
│   ├── tauri.conf.json
│   ├── Cargo.toml
│   └── icons/
│
├── frontend/                         ← FE-1 owns entirely
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx                   ← tab switching logic lives here
│   │   ├── api/
│   │   │   └── client.js             ← all fetch calls to FastAPI (FE-1 writes this)
│   │   ├── components/
│   │   │   ├── Timer/
│   │   │   │   ├── Timer.jsx
│   │   │   │   └── Timer.module.css
│   │   │   ├── Tasks/
│   │   │   │   ├── TaskList.jsx
│   │   │   │   ├── TaskItem.jsx
│   │   │   │   ├── TaskForm.jsx
│   │   │   │   └── Tasks.module.css
│   │   │   ├── Summary/
│   │   │   │   ├── Summary.jsx
│   │   │   │   └── Summary.module.css
│   │   │   └── Settings/
│   │   │       ├── Settings.jsx
│   │   │       └── Settings.module.css
│   │   └── styles/
│   │       └── global.css
│   ├── index.html
│   └── package.json
│
├── backend/                          ← BE-1 owns entirely
│   ├── main.py                       ← FastAPI app entry point
│   ├── routers/
│   │   ├── tasks.py
│   │   ├── timer.py
│   │   ├── summary.py
│   │   ├── activity.py
│   │   └── settings.py
│   ├── models/
│   │   └── schemas.py                ← Pydantic models for request/response
│   ├── storage/
│   │   ├── task_store.py             ← JSON read/write with file locking
│   │   └── settings_store.py
│   ├── data/
│   │   ├── tasks.json                ← gitignored
│   │   └── settings.json             ← gitignored
│   └── requirements.txt
│
├── scraper/                          ← BE-2 owns entirely
│   ├── main.py                       ← entry point, runs the loop
│   ├── windows_scraper.py            ← uiautomation based (Windows)
│   ├── mac_scraper.py                ← pyobjc based (macOS)
│   ├── idle_detector.py              ← detects and skips idle periods
│   ├── whitelist.py                  ← apps excluded from scraping
│   ├── ai/
│   │   └── ollama_client.py          ← talks to local Gemma via Ollama
│   └── data/
│       ├── current_activity.json     ← overwritten each scrape (gitignored)
│       └── daily_log.json            ← in-memory, flushed to this at midnight (gitignored)
│
├── .gitignore
├── README.md
└── API_CONTRACT.md                   ← agreed by all 4 on Day 1, never changed without team discussion
```

---

## API CONTRACT
### Agreed on Day 1 — frozen until all 4 sign off on a change

All endpoints run on `http://localhost:8080`

```
GET   /health
      Response: { "status": "ok" }

GET   /activity/current
      Response: {
        "app_name": "Google Chrome",
        "window_title": "YouTube - Google Chrome",
        "text_elements": ["Watch History", "Trending", ...],
        "timestamp": "2026-05-13T10:23:00"
      }

GET   /tasks
      Response: [ { task object }, ... ]

POST  /tasks
      Body: { "title": "", "description": "", "estimated_hours": 0,
              "estimated_minutes": 0, "priority": "Medium",
              "tags": [], "status": "Todo", "is_recurring": false }
      Response: { task object with id }

PUT   /tasks/{id}
      Body: any updatable fields
      Response: { updated task object }

DELETE /tasks/{id}
      Response: { "deleted": true }

POST  /timer/start
      Response: { "status": "running", "session_type": "focus" }

POST  /timer/pause
      Response: { "status": "paused", "remaining_seconds": 900 }

POST  /timer/reset
      Response: { "status": "idle" }

GET   /timer/status
      Response: {
        "status": "running" | "paused" | "idle",
        "session_type": "focus" | "short_break" | "long_break",
        "remaining_seconds": 1200,
        "session_count": 2
      }

POST  /summary/generate
      Response: { "summary": "...", "score": 7.4 }

GET   /summary/latest
      Response: { "summary": "...", "score": 7.4, "generated_at": "..." }

GET   /settings
      Response: { settings object }

POST  /settings
      Body: { settings fields }
      Response: { updated settings object }
```

---

## PHASE 0 — DAY 1 SETUP
### All 4 people | Before any feature work

**Goal:** Everyone can run the project locally. No blockers.

**Tasks:**

- [ ] Create GitHub repo, set branch protection on `main` — requires PR to merge
- [ ] Write `API_CONTRACT.md` together — all 4 agree on request/response shapes before splitting
- [ ] FE-2: scaffold Tauri project, confirm it builds and opens a window
- [ ] BE-1: scaffold FastAPI, confirm `/health` returns 200
- [ ] FE-1: scaffold React inside Tauri frontend folder, confirm it renders in the Tauri window
- [ ] BE-2: confirm `uiautomation` (Windows) or `pyobjc` (macOS) installs and the scraper script returns any output
- [ ] Add `.gitignore` — must include `data/*.json`, `__pycache__`, `node_modules`, `target/`
- [ ] Write `README.md` with how to run each part locally

**Merge point:** Everyone pushes their scaffold to their own branch, then one PR to `main` merges all four scaffolds. Confirm it runs before moving to Phase 1.

---

## PHASE 1A — CORE FEATURES (PARALLEL WORK)
### All 4 work independently on their branches

**Target:** Basic working app — tasks, timer, scraper sending data.

---

### FE-1 — React UI
Branch: `fe1/core-ui`

- [ ] Global CSS — dark mode variables, base styles, font
- [ ] App.jsx — tab state, conditional rendering of four tabs
- [ ] Timer tab — ring countdown display, session label, Start/Pause/Reset buttons, session counter
- [ ] Tasks tab — vertical list, TaskForm modal for create/edit, status toggle, priority indicator, tag display, delete button
- [ ] Summary tab — Generate button, summary display area with score and sections, Export to Markdown button
- [ ] Settings tab — Pomodoro duration inputs, long break toggle, startup toggle, distraction toggle, idle threshold, whitelist input
- [ ] api/client.js — all fetch functions to FastAPI endpoints (use the contract, do not invent new shapes)

**FE-1 note:** Use mock data returned from api/client.js functions during this phase. Do not wait for BE-1 to finish. Mock returns the same shape as the API contract.

---

### FE-2 — Tauri + Desktop Shell
Branch: `fe2/tauri-shell`

- [ ] Configure Tauri window — title, size, resizable, dark titlebar
- [ ] Configure FastAPI sidecar — Tauri spawns backend/main.py on app start, kills it on quit
- [ ] Health check on startup — Tauri waits for `/health` to return 200 before showing the window
- [ ] macOS menu bar icon via rumps — show current app name, timer status, Start/Pause shortcut, Open Window, Quit
- [ ] Windows system tray icon via pystray — same options in right-click menu
- [ ] Launch on startup — platform-specific startup registration, toggleable via settings
- [ ] Sound notification — play sound file on Pomodoro session end (work and break)
- [ ] Desktop notification — plyer popup on session end and distraction alert

**FE-2 note:** The sidecar setup is the most critical and most likely to cause integration issues. Get this working first before anything else.

---

### BE-1 — FastAPI Backend
Branch: `be1/core-api`

- [ ] FastAPI app setup on port 8080, CORS configured for localhost
- [ ] `/health` endpoint
- [ ] Task CRUD — all four endpoints, JSON file storage with file locking (`filelock` library)
- [ ] Timer state — in-memory, all four endpoints
- [ ] Settings storage — read/write settings.json
- [ ] `/activity/current` — reads from `scraper/data/current_activity.json` (BE-2 writes this file)
- [ ] `/summary/generate` — reads daily log from memory (BE-2 owns the log), calls Ollama, returns formatted summary
- [ ] `/summary/latest` — returns last generated summary from memory
- [ ] Pydantic schemas for all request and response bodies
- [ ] Recurring task logic — on app startup, check tasks.json for recurring tasks marked done yesterday, reset their status

**BE-1 note:** For `/activity/current` and `/summary/generate` to work you need BE-2's files. During this phase, create mock versions of `current_activity.json` and a mock daily log so you can develop and test independently.

---

### BE-2 — Scraper + AI
Branch: `be2/scraper-ai`

- [ ] Platform detection — if Windows use `uiautomation`, if macOS use `pyobjc`
- [ ] windows_scraper.py — walk active window at depth 8, extract only elements with meaningful text, filter out empty/short strings
- [ ] mac_scraper.py — equivalent using Accessibility API
- [ ] whitelist.py — hardcoded list of excluded apps (1Password, Bitwarden, banking apps, system password prompts)
- [ ] idle_detector.py — detect mouse/keyboard inactivity, skip scrape if idle beyond threshold (default 120 seconds)
- [ ] Trigger logic — scrape on window focus change AND every 30 seconds
- [ ] Write current scrape to `scraper/data/current_activity.json` — overwrite each time
- [ ] Accumulate each scrape entry (app name, window title, filtered text, timestamp) into in-memory daily log list
- [ ] Midnight reset — clear in-memory daily log at midnight, start fresh
- [ ] ollama_client.py — HTTP client to local Ollama API, sends prompt with daily log, receives summary text
- [ ] Distraction detection — after each scrape, compare current app/window against user's active task from tasks.json, if mismatch send POST to `/distraction/alert` (BE-1 adds this endpoint)
- [ ] Expose daily log via a simple internal endpoint or shared file so BE-1 can read it for summary generation

**BE-2 note:** The scraper runs as a completely separate Python process. It does not import from backend/. It communicates only by writing to JSON files and calling FastAPI endpoints.

---

## PHASE 1B — INTEGRATION
### First merge point — all 4 branches come together

**When to do this:** When each person has their core work functional in isolation.

**Steps:**

1. BE-1 opens PR to `main` first — backend must be up before frontend connects
2. BE-2 opens PR to `main` — scraper must be running for activity endpoint to work
3. FE-2 opens PR to `main` — Tauri shell with sidecar
4. FE-1 opens PR to `main` last — replace mock api/client.js calls with real ones pointing to live FastAPI

**Integration checklist:**
- [ ] Tauri window opens, FastAPI sidecar starts, `/health` returns 200
- [ ] React renders in Tauri window with no console errors
- [ ] Scraper runs alongside, writes `current_activity.json`
- [ ] Timer tab — start, pause, reset all work against live API
- [ ] Tasks tab — create, edit, delete, status toggle all work against live API
- [ ] Activity current shows real app name from scraper
- [ ] Settings save and persist across app restart
- [ ] Distraction notification fires when switching to a non-task-related window
- [ ] Summary generates via Ollama and displays in Summary tab

**Conflicts to watch:**
- Only BE-1 writes to `backend/` — no one else touches that folder
- Only BE-2 writes to `scraper/` — no one else touches that folder
- Only FE-1 writes to `frontend/src/` — no one else touches that folder
- Only FE-2 writes to `src-tauri/` — no one else touches that folder
- `API_CONTRACT.md` is read-only unless all 4 agree

---

## PHASE 1C — POLISH + DEMO PREP
### Final phase before hackathon demo

**Goal:** No broken states during demo, good first impression.

**All 4:**
- [ ] Run the full app end-to-end on a clean machine — fix anything that requires manual setup
- [ ] Write a one-command startup script — single command starts FastAPI + scraper + Tauri
- [ ] Test on both macOS and Windows if possible (at minimum on the demo machine OS)
- [ ] Distraction notification — confirm it fires and looks good
- [ ] Summary output — confirm Ollama/Gemma returns a clean structured summary
- [ ] Export to Markdown — confirm file saves correctly
- [ ] Sound on Pomodoro end — confirm it plays

**FE-1:**
- [ ] Polish all four tabs — spacing, alignment, empty states, loading states
- [ ] Error state if FastAPI is not running — show a clear message instead of blank screen

**FE-2:**
- [ ] Confirm tray/menu bar icon works on demo machine OS
- [ ] Test startup on login behaviour

**BE-1:**
- [ ] Handle edge cases — empty task list, no summary yet, timer already running
- [ ] Add basic logging so errors are visible during demo

**BE-2:**
- [ ] Test scraper on apps the demo will use — VS Code, Chrome, Slack
- [ ] Confirm whitelist works — password manager should never appear in activity

---

## GIT WORKFLOW RULES

**Branch naming:**
- `fe1/feature-name`
- `fe2/feature-name`
- `be1/feature-name`
- `be2/feature-name`

**Never commit directly to `main`.** Always open a PR. At least one other person reviews before merge.

**Commit often within your branch.** Small commits are easier to debug.

**If you need something from another person's area** — open an issue or message them. Do not edit their files directly.

**`API_CONTRACT.md` is sacred.** Any change needs all 4 to agree before it goes in.

---

## DEPENDENCY MAP
### Who is blocked by whom

```
FE-1 needs BE-1 endpoints live → use mocks until Phase 1B
FE-2 needs BE-1 /health to exist → mock it with a simple script if needed
BE-1 needs BE-2's current_activity.json → mock it with a static file until Phase 1B
BE-1 needs BE-2's daily log → agree on shared file path on Day 1
BE-2 needs BE-1's task list to do distraction comparison → read tasks.json directly (same machine)
```

The only hard dependency that cannot be mocked is the Tauri sidecar — FE-2 must confirm the backend starts correctly as a sidecar process during Phase 1B.

---

## WHAT IS NOT BEING BUILT

To avoid scope creep during the hackathon, the following are explicitly out of scope:

- Browser extension — not needed, scraper handles browser content directly
- SQLite database — JSON files only in Phase 1
- WebSockets — REST polling only
- Local LLM model selection UI — Gemma via Ollama only, no model switcher
- Notion integration — deferred post-hackathon
- Sub-tasks — Phase 2
- Cloud sync or user accounts — Phase 2
- Screenshot-based extraction — Phase 2

---

*Last updated: May 2026 | Nudge Implementation Plan v2.0*
