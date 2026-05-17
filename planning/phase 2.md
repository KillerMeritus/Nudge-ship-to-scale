# NUDGE — PHASE 2 FINAL IMPLEMENTATION PLAN
> Version 4.0 | May 2026 | Notion-ready

---

## TEAM

| Person | Code | Owns |
|--------|------|------|
| Person 1 | FE-1 | React UI — all tab changes, contexts, components |
| Person 2 | FE-2 | Tauri shell, desktop notifications, tray, sleep/wake |
| Person 3 | BE-1 | FastAPI — all endpoints, task state, distraction storage |
| Person 4 | BE-2 | Scraper, AI client (Gemini + Ollama), storage pipeline |

---

## FOLDER OWNERSHIP — ZERO OVERLAP RULE

```
nudge/
├── frontend/src/          ← FE-1 only. Nobody else touches this.
├── src-tauri/             ← FE-2 only. Nobody else touches this.
├── backend/               ← BE-1 only. Nobody else touches this.
├── scraper/               ← BE-2 only. Nobody else touches this.
├── API_CONTRACT.md        ← Read-only for everyone. Change only with all 4 present.
└── README.md              ← Anyone can update.
```

If you ever need to change something outside your folder — open an issue and ask. Do not touch another person's files directly.

---

## BRANCH STRATEGY

```
main                        ← protected. PR required. Never commit directly.
├── fe1/phase2-ui           ← FE-1 works here the entire phase
├── fe2/phase2-shell        ← FE-2 works here the entire phase
├── be1/phase2-api          ← BE-1 works here the entire phase
└── be2/phase2-scraper      ← BE-2 works here the entire phase
```

Each person stays on their branch from start to finish. Merges happen at defined checkpoints only — listed at the end of this document.

---

## AI MODEL DECISION — BOTH SUPPORTED

Both Gemini API and Ollama (Gemma) are supported. The user selects which one to use in Settings. This lets the team test both during development and decide later which performs better.

**Gemini mode:**
- Called every 10 seconds while a task is active
- Requires user to provide their own Gemini API key in Settings
- Faster response, cloud-based, uses API quota

**Ollama mode:**
- Called every 10 seconds while a task is active
- Requires Ollama running locally on port 11434 with Gemma pulled
- Fully local, no API cost, slightly slower depending on hardware

**Why every 10 seconds is acceptable:**
The call only happens when a task is actively running — not 24/7. Each call is a small focused prompt, not a large generation. Both clients run in a background thread — a slow or failed call never blocks the scraper loop.

**Distraction philosophy — critical:**
Nudge does NOT use a hardcoded list of distracting apps. The AI decides based on context. If the user is working on a coding task and opens YouTube to watch a tutorial, the AI sees the window title ("React hooks tutorial — YouTube") and the scraped text and correctly determines this is not a distraction. Context-aware judgment is the core value of Nudge. Rule-based blocklists are explicitly not used.

---

---

# PHASE 2 — DAY 0: API CONTRACT + SHARED TYPES

> All 4 people together. Do not split until this is done.
> Nothing gets built until the contract is agreed and written.

- [ ] Agree on all new FastAPI endpoint shapes (listed in BE-1 section)
- [ ] Agree on `current_activity.json` schema
- [ ] Agree on daily log entry schema
- [ ] Agree on AI distraction JSON response format — same format for both Gemini and Ollama
- [ ] Agree on task state machine (Todo → In Progress → Paused → Done)
- [ ] Write all agreed schemas into `API_CONTRACT.md`
- [ ] FE-1 creates mock data files matching every agreed schema — goes in `frontend/src/mocks/`
- [ ] BE-2 creates sample `current_activity.json` and daily log — commit to `scraper/data/samples/`
- [ ] Everyone pulls `main` and confirms they can see the samples before branching

**→ SPLIT. Everyone goes to their own branch after this.**

---

---

# FE-1 — REACT UI
> Branch: `fe1/phase2-ui`
> Folder: `frontend/src/` only

---

## MILESTONE 1 — Contexts and State Architecture

> Fix the tab-switch timer reset bug first. Everything else depends on this.

- [ ] Create `frontend/src/contexts/TimerContext.jsx`
  - [ ] Holds Pomodoro state: status (running/paused/idle), remaining seconds, session type, session count
  - [ ] `setInterval` lives inside this context provider — not in any component
  - [ ] Exposes: `start`, `pause`, `reset`, `status`, `remainingSeconds`, `sessionType`, `sessionCount`
- [ ] Create `frontend/src/contexts/ActiveTaskContext.jsx`
  - [ ] Holds: active task object, elapsed seconds, running/paused state
  - [ ] Elapsed counter `setInterval` lives inside this context — not in any component
  - [ ] Exposes: `startTask`, `pauseTask`, `resumeTask`, `clearTask`, `activeTask`, `elapsedSeconds`, `taskStatus`
- [ ] Wrap both contexts around the entire app in `App.jsx`
- [ ] Remove any timer state that currently lives inside `Timer.jsx` or any tab component
- [ ] Confirm switching tabs does not unmount the context providers

**Self-test before moving on:**
- [ ] Start Pomodoro. Switch all 4 tabs rapidly. Return. Timer has continued.
- [ ] Start a task. Switch all 4 tabs. Return. Elapsed time has continued.
- [ ] Pause Pomodoro. Switch tabs. Return. Still paused at same value.

---

## MILESTONE 2 — Current Task Tab

- [ ] Rename tab label from "Timer" to "Current Task" in `App.jsx` nav
- [ ] Update `Timer.jsx` or rename to `CurrentTask.jsx` — keep internal naming consistent
- [ ] No task running state: show only Pomodoro ring, session label, controls, session counter — same as Phase 1
- [ ] Task running state: show task title above Pomodoro ring, show task elapsed time (MM:SS or HH:MM:SS), Pomodoro ring below
- [ ] Task paused state: show task title, elapsed time frozen, "Paused" label, Resume button
- [ ] Sleep/wake: when app receives wake signal from FE-2, pause active task elapsed timer automatically

**Self-test:**
- [ ] No task running → only Pomodoro visible
- [ ] Task running → title and elapsed time visible above ring
- [ ] Switch tabs 5 times while task running → elapsed time continues
- [ ] Switch tabs 5 times while Pomodoro running → countdown continues
- [ ] Both running simultaneously → both continue independently across tab switches

---

## MILESTONE 3 — Tasks Tab

- [ ] Estimated time field: two separate numeric inputs — hours (0–23) and minutes (0–59)
- [ ] Validation: reject values outside range, both fields optional
- [ ] Display in task list: "Est: 1h 30m" — omit hours if zero, show "Est: 45m"
- [ ] Four controls per task: Start (or Pause/Resume), Edit, Delete, Done toggle
- [ ] Start button: calls `ActiveTaskContext.startTask(task)`, sends `POST /tasks/{id}/start`
- [ ] If another task is already running: auto-pause it first, then start new one
- [ ] Pause button (shown when task running): calls `ActiveTaskContext.pauseTask()`, sends `POST /tasks/{id}/pause`
- [ ] Resume button (shown when task paused): calls `ActiveTaskContext.resumeTask()`, sends `POST /tasks/{id}/resume`
- [ ] Edit button: opens modal with all fields pre-populated including estimated time
- [ ] Delete button: shows inline confirmation — "Delete this task?" with Confirm and Cancel. No `alert()`.
- [ ] Done toggle: if task currently running, stop and clear from Current Task tab first, then mark done
- [ ] Done tasks: Start button removed, only Edit and Delete remain
- [ ] Recurring tasks: when marked done, show subtle "Will reset tomorrow" label

**Self-test:**
- [ ] Create task with 2h 00m → shows "Est: 2h 00m"
- [ ] Create task with 0h 45m → shows "Est: 45m"
- [ ] Create task with no estimate → no estimate shown, no error
- [ ] Start Task A. Start Task B. Task A auto-pauses. Task B starts. Current Task tab shows Task B.
- [ ] Start task → switch to Current Task tab → title and timer visible
- [ ] Edit running task title → title updates in Current Task tab immediately
- [ ] Mark running task Done → Current Task tab clears
- [ ] Delete running task → task removed, Current Task tab clears
- [ ] Delete confirmation cancel → task still in list

---

## MILESTONE 4 — Summary Tab

- [ ] "Generate Now": before calling API check if key or Ollama is configured
- [ ] Gemini selected, no key: inline banner — "No Gemini API key found. Go to Settings." with button that switches to Settings tab
- [ ] Ollama selected, offline: inline error — "Ollama is not running. Start Ollama and try again."
- [ ] Loading state: spinner visible, button disabled during API call
- [ ] Success: display in "AI Insights" section with all structured sections
- [ ] Error (bad key, timeout, model error): user-friendly message — no raw error object or stack trace
- [ ] Summary persists on tab switch — stored in a `SummaryContext`, not wiped on unmount
- [ ] Second generation replaces first — no stacking
- [ ] Export to Markdown: saves displayed summary as `.md` file
- [ ] Poll `GET /distraction/today` every 30 seconds — show live distraction count badge on Summary tab label

**Self-test:**
- [ ] Gemini, no key → error banner with Settings link
- [ ] Ollama offline → clear error message
- [ ] Invalid key → user-friendly error, no stack trace
- [ ] Valid config + data → summary with all sections appears
- [ ] Generate → switch tabs → return → summary still displayed
- [ ] Generate twice → only latest shown
- [ ] Spinner visible during generation, button disabled
- [ ] Export → file saves and opens correctly in text editor

---

## MILESTONE 5 — Settings Tab

- [ ] AI model selector: "Gemini API" and "Local — Ollama (Gemma)"
- [ ] Gemini selected: show API key input, save to settings
- [ ] Ollama selected: show live status — "Ollama running ✓" or "Ollama not found ✗" — polls `GET /settings/ollama-status` every 5 seconds
- [ ] Whitelist input: comma-separated app names, saved to settings, used by scraper
- [ ] Idle threshold input: numeric, default 120 seconds
- [ ] Distraction alert cooldown input: numeric, default 180 seconds

---

## ✅ FE-1 MERGE CHECKPOINT
> All 5 milestones self-tested and passing → open PR to `main`.
> Tag BE-1 to review — confirms API call shapes match contract.
> Do not merge until BE-1 approves.

---

---

# FE-2 — TAURI + DESKTOP SHELL
> Branch: `fe2/phase2-shell`
> Folder: `src-tauri/` only

---

## MILESTONE 1 — Sleep and Wake Detection

> Most important FE-2 addition. Do this first.

- [ ] Detect system sleep event via Tauri power management API or OS-level event
- [ ] On sleep: emit `system-sleep` event to React frontend via Tauri event bridge
- [ ] Detect system wake event
- [ ] On wake: emit `system-wake` event to React frontend
- [ ] On wake: call `POST /scraper/pause` so BE-2 scraper knows system was asleep
- [ ] On wake: send sleep duration to `POST /activity/sleep-gap` — BE-1 inserts gap marker in activity log
- [ ] FE-1 listens for both events and pauses/resumes active task elapsed timer accordingly

**Self-test:**
- [ ] Close laptop lid. Open it. Task elapsed timer was paused during sleep.
- [ ] `system-wake` event reaches React frontend within 2 seconds of wake.
- [ ] Sleep gap appears in activity log via `GET /activity/today`.

---

## MILESTONE 2 — Desktop Notifications

- [ ] Distraction alert: title "Hey, you seem distracted", body includes app name, task name, reason from AI
- [ ] Pomodoro session end: notification + sound (Phase 1 — confirm still working)
- [ ] Break end: notification + sound (Phase 1 — confirm still working)
- [ ] Notification does not steal window focus — system notification only
- [ ] macOS: correct notification permission request on first launch
- [ ] Windows: notifications appear in Action Center

**Self-test:**
- [ ] Manually POST a test distraction alert → notification appears with correct content
- [ ] Pomodoro ends → notification and sound fire
- [ ] Notification does not bring Nudge window to front

---

## MILESTONE 3 — Tray and Menu Bar Updates

- [ ] macOS menu bar: add "Active Task: [task title]" or "No active task"
- [ ] macOS menu bar: add "Distractions today: N"
- [ ] Windows tray: same additions in right-click menu
- [ ] Poll `GET /timer/active-task` every 10 seconds to refresh tray content
- [ ] Start/Pause shortcut in tray controls active task timer, not just Pomodoro

**Self-test:**
- [ ] Start task → tray shows task title within 10 seconds
- [ ] Pause task → tray shows paused state
- [ ] Distraction fires → tray count increments within 10 seconds

---

## MILESTONE 4 — Sidecar and Startup

- [ ] Confirm Tauri sidecar starts both `backend/main.py` and `scraper/main.py` as separate processes
- [ ] Health check: wait for `GET /health` 200 before showing window
- [ ] On quit: gracefully shut down both sidecar processes — no orphan Python processes
- [ ] On wake: check if scraper process is still alive, restart if crashed
- [ ] Launch on startup: confirm still working on both platforms

**Self-test:**
- [ ] Quit app → no Python processes remain in Activity Monitor / Task Manager
- [ ] Sleep and wake → scraper resumes correctly
- [ ] Cold start → window appears only after health check passes

---

## ✅ FE-2 MERGE CHECKPOINT
> Open PR to `main` after FE-1 has already merged.
> FE-2 only touches `src-tauri/` — zero conflicts possible.
> Tag BE-1 to confirm sleep gap endpoint is live before merging.

---

---

# BE-1 — FASTAPI BACKEND
> Branch: `be1/phase2-api`
> Folder: `backend/` only

---

## MILESTONE 1 — Task State Machine Endpoints

- [ ] Update `schemas.py`: add `elapsed_seconds`, `started_at`, `paused_at`, `task_status` (running/paused/idle)
- [ ] `POST /tasks/{id}/start` — set In Progress, record `started_at`, store as active task in memory
- [ ] `POST /tasks/{id}/pause` — record elapsed seconds, set paused, clear active task from memory
- [ ] `POST /tasks/{id}/resume` — resume from stored elapsed seconds, set running
- [ ] `GET /timer/active-task` — return currently active task or `null`
- [ ] Enforce one active task server-side — if new task starts while another active, auto-pause previous
- [ ] When task marked Done: if it was active, clear from active task memory
- [ ] Persist `elapsed_seconds` to `tasks.json` on every pause — survives restart

**Self-test:**
- [ ] Start Task A → `GET /timer/active-task` returns Task A
- [ ] Start Task B → Task A auto-paused, `GET /timer/active-task` returns Task B
- [ ] Mark active task Done → `GET /timer/active-task` returns null
- [ ] Restart app → task still has correct `elapsed_seconds`

---

## MILESTONE 2 — Distraction Endpoints

- [ ] `POST /distraction/alert` — store event in memory list, return `{ "received": true }`
- [ ] `GET /distraction/latest` — return most recent event or `null`
- [ ] `GET /distraction/today` — return all events for today in chronological order
- [ ] `DELETE /distraction/today` — clear today's list
- [ ] Each event includes: `task_id`, `task_title`, `app_name`, `window_title`, `reason`, `distraction_category`, `severity`, `timestamp`
- [ ] Date-aware reset: check on each request if date has changed, reset list if so — not a clock trigger

**Self-test:**
- [ ] POST test event → GET /distraction/latest returns it correctly
- [ ] POST 5 events → GET /distraction/today returns all 5 in order
- [ ] Simulate date change → GET /distraction/today returns empty list

---

## MILESTONE 3 — Activity and Support Endpoints

- [ ] `GET /activity/current` — reads `scraper/data/current_activity.json`, returns contents or `null`
- [ ] `POST /activity/sleep-gap` — receives `{ "slept_at", "woke_at", "duration_seconds" }`, inserts gap marker into in-memory activity log
- [ ] `GET /activity/today` — returns full in-memory activity log including gap markers
- [ ] `GET /settings/ollama-status` — checks if Ollama running on `localhost:11434`, returns `{ "running": true | false }`
- [ ] `POST /scraper/snapshot` — triggers BE-2 to write `daily_log_snapshot.json`
- [ ] `POST /scraper/pause` — signals scraper to pause accumulation (forwarded to scraper process)
- [ ] `POST /scraper/resume` — signals scraper to resume

**Self-test:**
- [ ] Scraper writing `current_activity.json` → GET /activity/current returns correct data
- [ ] POST sleep gap → GET /activity/today shows gap marker at correct timestamp
- [ ] Ollama running → GET /settings/ollama-status returns `{ "running": true }`
- [ ] Ollama stopped → returns `{ "running": false }`, no crash

---

## MILESTONE 4 — Summary Endpoint

- [ ] `POST /summary/generate` — reads `scraper/data/daily_log_snapshot.json`, constructs full prompt with all tasks, durations, and distraction events, calls Gemini or Ollama based on settings
- [ ] `GET /summary/latest` — return last generated summary from memory
- [ ] Gemini, no key → `{ "error": "no_api_key", "message": "Add your Gemini API key in Settings" }` status 400
- [ ] Ollama offline → `{ "error": "ollama_offline", "message": "Ollama is not running on this machine" }` status 503
- [ ] Never return raw 500 — always a structured error object

**Summary prompt structure:**
```
You are a productivity assistant. Generate a structured daily summary.

Tasks worked on today:
{list of tasks with title, elapsed time, start/end times}

Distraction events:
{list with timestamp, task being worked on, app switched to, reason}

Total deep work time: Xh Ym
Total distraction time: Xh Ym

Respond in this exact format:
NUDGE DAILY SUMMARY — {date}

Productivity Score: X.X / 10

What You Worked On:
- {task} — {duration} — {apps used}

Deep Work Time: Xh Ym
Distraction Time: Xh Ym

Distraction Events:
- {time} | Working on: {task} | Switched to: {app} | Duration: {N} mins

Top Distractions:
- {app or pattern}

Biggest Pattern:
- {one specific observation}

One Suggestion for Tomorrow:
- {specific and actionable}
```

**Self-test:**
- [ ] Gemini, no key → 400 with structured error
- [ ] Ollama offline → 503 with clear message
- [ ] Valid config + data → structured summary with all sections
- [ ] No activity data → minimal valid summary, no crash

---

## ✅ BE-1 MERGE CHECKPOINT
> BE-1 merges to `main` first — before anyone else.
> After merging: notify FE-1, FE-2, BE-2 that endpoints are live on main.

---

---

# BE-2 — SCRAPER + AI PIPELINE
> Branch: `be2/phase2-scraper`
> Folder: `scraper/` only

---

## MILESTONE 1 — Storage Pipeline

- [ ] `current_activity.json` — overwrite on every scrape
- [ ] In-memory daily log — list of entries: `app_name`, `window_title`, `text_elements`, `timestamp`, `task_context`
- [ ] Date-aware reset: on every scrape cycle compare current date against date of first log entry. If different: write old log to `scraper/data/previous_day_log.json`, then clear and start fresh. Handles laptop-closed-overnight correctly.
- [ ] Sleep/wake: on `POST /scraper/pause` — stop accumulating, insert `{ "type": "sleep_gap", "started_at": "..." }`. On `POST /scraper/resume` — insert `{ "type": "sleep_gap_end", "ended_at": "..." }`, continue normally.
- [ ] Snapshot on demand: when `POST /scraper/snapshot` called, write full in-memory log to `scraper/data/daily_log_snapshot.json`
- [ ] Idle skip: no mouse/keyboard input for 120 seconds → skip scrape, no entry added
- [ ] Whitelist: read from `backend/data/settings.json` each cycle. If active window in whitelist, skip entirely.

**Schemas:**

`current_activity.json`:
```json
{
  "app_name": "Google Chrome",
  "window_title": "React hooks tutorial - YouTube",
  "text_elements": ["Subscribe", "React Hooks Tutorial", "10M views"],
  "timestamp": "2026-05-13T14:32:00",
  "is_idle": false
}
```

Daily log entry:
```json
{
  "app_name": "Google Chrome",
  "window_title": "React hooks tutorial - YouTube",
  "text_elements": ["Subscribe", "React Hooks Tutorial", "10M views"],
  "timestamp": "2026-05-13T14:32:00",
  "task_context": "Learn React"
}
```

**Self-test:**
- [ ] Switch apps → `current_activity.json` updates within 5 seconds
- [ ] Switch 5 apps over 2 minutes → daily log has 5+ entries
- [ ] Go idle 130 seconds → no entries added. Mouse move → resumes.
- [ ] Open whitelisted app → no update to `current_activity.json`, no AI call
- [ ] Mock date change → old log saved to `previous_day_log.json`, fresh log starts
- [ ] POST /scraper/pause → entries stop, gap marker inserted. POST /scraper/resume → entries continue.
- [ ] POST /scraper/snapshot → `daily_log_snapshot.json` written with full log

---

## MILESTONE 2 — AI Distraction Client (Gemini + Ollama)

> One unified client. Routes to Gemini or Ollama based on settings. Called every 10 seconds while task is active. Runs in background thread — never blocks scraper loop.

- [ ] Create `scraper/ai/ai_client.py`
  - [ ] Reads settings on each call to determine active model — switching in Settings takes effect within 10 seconds, no restart needed
  - [ ] Single method: `classify_activity(task_title, app_name, window_title, text_elements)` → returns dict or `None` on any failure
  - [ ] Routes to `gemini_client.py` or `ollama_client.py` internally

- [ ] Create `scraper/ai/gemini_client.py`
  - [ ] Uses `google-generativeai` SDK
  - [ ] Reads API key from `backend/data/settings.json`
  - [ ] No key → return `None`, log warning once, do not repeat warning every 10 seconds
  - [ ] Timeout: 8 seconds → return `None`, log timeout, continue
  - [ ] HTTP 429 rate limit → back off 30 seconds, then resume

- [ ] Create `scraper/ai/ollama_client.py`
  - [ ] HTTP POST to `http://localhost:11434/api/generate`
  - [ ] Model: Gemma (read from settings)
  - [ ] Ollama not running → return `None`, log warning once
  - [ ] Timeout: 8 seconds → return `None`, continue

- [ ] Shared system prompt for both clients:
```
You are a productivity assistant for the Nudge app.
The user is currently working on a task.
Determine if the user is currently distracted from their task.

User's current task: "{task_title}"
Active application: "{app_name}"
Window title: "{window_title}"
Visible UI text sample: "{text_elements_sample}"

Important rules:
- If the user appears to be researching something related to their task, is_distracted = false
- If the window title or content suggests relevance to the task, is_distracted = false
- Only flag as distracted if the activity is clearly unrelated to the task
- Communication apps (Slack, Zoom, Teams, Email) — is_distracted = false
- When in doubt, return is_distracted = false

Respond ONLY with valid JSON. No text outside the JSON block.

{
  "is_distracted": true | false,
  "confidence": 0.0 to 1.0,
  "reason": "one sentence explanation",
  "distraction_category": "social_media" | "entertainment" | "news" | "gaming" | "unrelated_work" | "communication" | "not_distracted",
  "severity": "low" | "medium" | "high"
}
```

- [ ] Parse JSON response in try/except — return `None` if malformed
- [ ] Strip markdown code fences (` ```json `) before parsing — models sometimes add these

**Self-test:**
- [ ] Gemini, valid key, task active, open Instagram → `is_distracted: true`
- [ ] Gemini, valid key, task active, open MDN docs → `is_distracted: false`
- [ ] Task "Learn React", open "React hooks tutorial — YouTube" → `is_distracted: false` (context-aware)
- [ ] Gemini, no key → `None` returned, warning logged once, no repeated spam
- [ ] Gemini rate limited → backs off 30 seconds, resumes
- [ ] Ollama, running, open Instagram → `is_distracted: true`
- [ ] Ollama offline → `None` returned, scraper continues
- [ ] Malformed JSON response → `None` returned, no crash
- [ ] Switch model in Settings → next call uses new model, no restart needed
- [ ] AI call mocked to take 10 seconds → times out at 8 seconds, scraper loop continues unblocked

---

## MILESTONE 3 — Distraction Detection Loop

- [ ] Background thread runs every 10 seconds while scraper is running
- [ ] On each tick:
  1. Check `GET /timer/active-task` — if no active task or task is paused, skip entirely
  2. Read `current_activity.json`
  3. If app is Zoom, Google Meet, Microsoft Teams → skip, no AI call
  4. If app is on whitelist → skip
  5. Call `ai_client.classify_activity(...)` in background thread
  6. If result is `None` → skip, do not alert
  7. If `is_distracted: false` → skip
  8. If `is_distracted: true` → check cooldown dict: `{ "app_name:task_id": last_alert_timestamp }`
  9. If within 180 seconds of last alert for same combo → skip
  10. If cooldown passed → send `POST /distraction/alert` with full event details
  11. Update cooldown dict with current timestamp
  12. Append event to in-memory daily log as `{ "type": "distraction_event", ... }`

**Self-test:**
- [ ] No active task → no AI calls (confirm via logs)
- [ ] Active task, open Instagram → AI called, alert fires, desktop notification appears
- [ ] Active task, open YouTube tutorial relevant to task → no alert
- [ ] Active task, open Zoom → no AI call, no alert
- [ ] Active task, task paused → open distracting app → no alert
- [ ] Alert fires, stay on distracting app → no second alert for 3 minutes
- [ ] After 3 minutes → second alert fires
- [ ] Return to work app → no alert

---

## ✅ BE-2 MERGE CHECKPOINT
> BE-2 merges after BE-1 is already on main.
> BE-2 only touches `scraper/` — zero conflicts possible.
> After merging: notify FE-1 and FE-2 that AI pipeline is live.

---

---

# MERGE ORDER AND TIMELINE

```
DAY 0
└── All 4 together: API contract, schemas, mock files, samples
    └── Everyone branches off main

DAY 1–3: All 4 work in parallel on their own branches

DAY 3 — MERGE CHECKPOINT 1
└── BE-1 merges to main first
    └── Reason: everyone depends on the API being live
    └── After merge: FE-1, FE-2, BE-2 each pull main into their branch
        → they get new endpoints, no conflicts (different folders)

DAY 4–5: All 4 continue on their branches

DAY 5 — MERGE CHECKPOINT 2
└── BE-2 merges to main
    └── Reason: scraper + AI pipeline must be live for end-to-end testing
    └── After merge: FE-1 and FE-2 pull main into their branches

DAY 6 — MERGE CHECKPOINT 3
└── FE-1 merges to main
    └── BE-1 reviews and approves PR — confirms API call shapes match contract

DAY 6 — MERGE CHECKPOINT 4 (same day, after FE-1)
└── FE-2 merges to main
    └── No review dependency — FE-2 only touches src-tauri/, zero conflicts

DAY 7 — INTEGRATION TESTING
└── All 4 test together on main
└── Bug fixes committed directly to main by whoever owns the affected folder
```

**Why this order prevents conflicts:**
- Each person owns exactly one folder — no file can ever be edited by two people simultaneously
- BE-1 merges first so others can switch from mocks to real API calls
- FE-1 and FE-2 merge last — they depend on both backend services being on main first
- Nobody ever merges another person's branch — only ever your own branch into main

---

---

# TESTING SCENARIOS

> Every scenario must pass before the app is considered done.
> Test on the actual demo machine OS.

---

## TAB AND TIMER PERSISTENCE

- [ ] **PERS-01** Start Pomodoro. Switch all 4 tabs rapidly. Return. Timer has continued.
- [ ] **PERS-02** Start a task. Switch all 4 tabs. Return. Elapsed time has continued.
- [ ] **PERS-03** Pause Pomodoro. Switch tabs. Return. Still shows same paused value.
- [ ] **PERS-04** Both timers running. Switch tabs 3 times. Both have advanced correctly and independently.
- [ ] **PERS-05** Sleep laptop 2 minutes with task running. Wake. Elapsed timer shows correct time — sleep not counted.

---

## TASK CONTROLS

- [ ] **CTRL-01** Create task Est 2h 00m → shows "Est: 2h 00m"
- [ ] **CTRL-02** Create task Est 0h 45m → shows "Est: 45m"
- [ ] **CTRL-03** Create task no estimate → no estimate shown, no error
- [ ] **CTRL-04** Edit task with existing estimate → form pre-filled correctly
- [ ] **CTRL-05** Start Task A. Start Task B. Task A auto-pauses. Current Task tab shows Task B.
- [ ] **CTRL-06** Start task. Switch to Current Task tab. Title and elapsed timer visible.
- [ ] **CTRL-07** Edit running task title. Updates in Current Task tab immediately.
- [ ] **CTRL-08** Mark running task Done. Current Task tab clears to Pomodoro-only view.
- [ ] **CTRL-09** Delete running task. Confirm prompt. Confirm. Task removed. Current Task tab clears.
- [ ] **CTRL-10** Cancel delete. Task still in list.
- [ ] **CTRL-11** Done task shows only Edit and Delete — no Start button.
- [ ] **CTRL-12** Restart app. Task still has correct `elapsed_seconds`.

---

## SCRAPER AND STORAGE

- [ ] **SCRP-01** Switch apps. `current_activity.json` updates within 5 seconds.
- [ ] **SCRP-02** Switch 5 apps over 2 minutes. Daily log has 5+ entries with correct timestamps.
- [ ] **SCRP-03** Go idle 130 seconds. No entries added. Mouse move resumes scraping.
- [ ] **SCRP-04** Open whitelisted app. `current_activity.json` does not update. No AI call.
- [ ] **SCRP-05** Mock date change. Old log saved to `previous_day_log.json`. Fresh log starts.
- [ ] **SCRP-06** Sleep and wake. Gap markers in log with correct timestamps. Timer was not counting during sleep.
- [ ] **SCRP-07** Open Chrome. URL bar text in `text_elements`. Confirms scrape depth sufficient.
- [ ] **SCRP-08** Run scraper 30 minutes with AI calls every 10 seconds. CPU under 15%. No memory leak.

---

## AI CLIENT

- [ ] **AI-01** Gemini. Valid key. Task active. Open Instagram → `is_distracted: true`
- [ ] **AI-02** Gemini. Valid key. Task active. Open MDN → `is_distracted: false`
- [ ] **AI-03** Task "Learn React". Open "React hooks tutorial — YouTube" → `is_distracted: false`. Context-aware working.
- [ ] **AI-04** Gemini. No key. Scraper continues. Warning logged once only.
- [ ] **AI-05** Gemini. Simulate rate limit 429. Backs off 30 seconds, resumes.
- [ ] **AI-06** Ollama. Running. Open Instagram → `is_distracted: true`
- [ ] **AI-07** Ollama. Offline. Scraper continues, no crash.
- [ ] **AI-08** Either model returns malformed JSON. Returns `None`. No crash.
- [ ] **AI-09** Switch Gemini → Ollama in Settings. Next call uses Ollama. No restart.
- [ ] **AI-10** Mock slow response (10 seconds). Times out at 8 seconds. Scraper loop unblocked.

---

## DISTRACTION PIPELINE

- [ ] **DIST-01** No active task. Open any app. No AI call. No alert.
- [ ] **DIST-02** Active task. Open Instagram. Alert fires. Desktop notification with task name and reason.
- [ ] **DIST-03** Active task. Open documentation relevant to task. No alert.
- [ ] **DIST-04** Active task. Open Zoom. No AI call. No alert.
- [ ] **DIST-05** Active task. Open Slack. No alert.
- [ ] **DIST-06** Alert fires. Stay on distracting app. No second alert for 3 minutes.
- [ ] **DIST-07** After 3 minutes on same app. Second alert fires.
- [ ] **DIST-08** Return to work app. No alert.
- [ ] **DIST-09** Task paused. Open distracting app. No alert.
- [ ] **DIST-10** Time from window switch to desktop notification under 20 seconds.

---

## SUMMARY

- [ ] **SUM-01** Gemini, no key. Click Generate Now. Inline error with Settings link. No API call.
- [ ] **SUM-02** Ollama offline. Clear error message. No crash.
- [ ] **SUM-03** Invalid key. User-friendly error. No stack trace.
- [ ] **SUM-04** Valid config. No activity data. Minimal valid summary. No crash.
- [ ] **SUM-05** Valid config. Data present. Summary shows all sections: score, tasks, distractions, suggestion.
- [ ] **SUM-06** Distraction events in summary with correct timestamps and app names.
- [ ] **SUM-07** Generate → switch tabs → return → summary still displayed.
- [ ] **SUM-08** Generate twice → only latest shown.
- [ ] **SUM-09** Spinner visible during generation. Button disabled during call.
- [ ] **SUM-10** Export to Markdown. File saves. Opens correctly in text editor.

---

## END-TO-END SCENARIOS

- [ ] **E2E-01** Create task "Build login page" → Start → work in VS Code → open Instagram → alert fires → return to VS Code → generate summary → summary mentions Instagram at correct time
- [ ] **E2E-02** Create task "Learn React" → Start → open "React hooks tutorial — YouTube" → no alert (context-aware) → generate summary → YouTube shown as productive, not a distraction
- [ ] **E2E-03** Start Task A → work 3 minutes → switch to Task B → Task A auto-pauses → generate summary → both tasks with correct durations
- [ ] **E2E-04** Start task → sleep laptop → wake → elapsed timer correct (sleep not counted) → summary includes sleep gap
- [ ] **E2E-05** Create 3 tasks → work on each → mark one Done → generate summary → all 3 with durations
- [ ] **E2E-06** Start Pomodoro only, no task → no AI calls made → Pomodoro end notification fires
- [ ] **E2E-07** Start task only, no Pomodoro → distraction monitoring works → summary generates correctly
- [ ] **E2E-08** Switch Gemini → Ollama mid-session in Settings → next distraction check uses Ollama, no restart, no crash

---

## PHASE 1 REGRESSION

> Confirm nothing from Phase 1 broke after Phase 2 changes.

- [ ] Create, edit, delete tasks still works
- [ ] Recurring task resets correctly the next day
- [ ] Settings save and persist across full app restart
- [ ] Pomodoro notification fires on session end
- [ ] Sound plays on Pomodoro session end
- [ ] Tray / menu bar icon shows correct timer status
- [ ] Launch on startup toggle works on both platforms
- [ ] Export to Markdown button works from Summary tab

---

*Nudge Phase 2 Implementation Plan — v4.0 | May 2026*
