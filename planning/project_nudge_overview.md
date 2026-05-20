---
name: project-nudge-overview
description: "Full architecture and layer breakdown of the Nudge desktop productivity app — React+Tauri FE, FastAPI BE, Python scraper, Ollama/Gemini AI"
metadata: 
  node_type: memory
  type: project
---

Nudge is a privacy-first macOS/Windows desktop productivity app with Pomodoro timer, task tracking, AI distraction detection, and daily AI-generated summaries. All data stays on-device.

**Why:** User is building/maintaining this app as part of the Asscent / Ship-to-scale project.

**How to apply:** Use this architecture context when the user asks about any feature across the 4 layers.

## 4-Layer Architecture

| Layer | Dir | Tech |
|-------|-----|------|
| FE-1 — React UI | `src/` | React 19, Vite, Tailwind, Tauri JS APIs |
| FE-2 — Desktop Shell | `src-tauri/` | Rust, Tauri 2.x |
| BE-1 — API Server | `backend/` | FastAPI, Pydantic, JSON file storage |
| BE-2 — Activity Monitor | `scraper/` | Python, pyobjc/pywin32, Ollama/Gemini |

## Key Files
- `src/App.jsx` — 4-tab shell (Timer, Tasks, Summary, Settings)
- `src/api/client.js` — Centralized API client; `USE_MOCKS` toggle for offline dev
- `src/contexts/` — TimerContext, ActiveTaskContext, SummaryContext
- `backend/main.py` — FastAPI app, CORS for Tauri/Vite, recurring task reset on startup
- `backend/state.py` — Shared active-task state across routers
- `backend/routers/summary.py` — AI summary (Gemini 2.0 Flash or Ollama)
- `backend/routers/distraction.py` — Distraction alert ingestion
- `scraper/distraction_loop.py` — Background thread, AI classification, 180s cooldown
- `scraper/ai/ai_client.py` — Factory: Gemini vs Ollama based on live settings
- `src-tauri/src/main.rs` — Tray menu, update_tray_timer command, system-wake event

## Data Files (gitignored)
- `backend/data/tasks.json`, `backend/data/settings.json`
- `scraper/data/current_activity.json` (live snapshot), `scraper/data/daily_log.json`
- `scraper/data/control.json` — IPC from BE-1 → BE-2 (pause/resume/snapshot)

## AI Integration
- Distraction classification: every 10s in background thread, calls Gemini or Ollama
- Summary generation: on-demand, reads daily_log_snapshot.json + tasks + distraction alerts
- Model switch is live — both features read `ai_model` setting on each call
- Default: Ollama with qwen2.5:0.5b; Gemini key stored in settings.json (plaintext)
