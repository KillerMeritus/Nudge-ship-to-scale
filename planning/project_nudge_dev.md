---
name: project-nudge-dev
description: Dev startup commands and workflow for the Nudge app (4 terminal processes needed)
metadata: 
  node_type: memory
  type: project
---

Dev requires 4 processes. Start in order:

**Why:** Backend must be up before frontend; scraper runs independently.

**How to apply:** When user asks how to run or start the project, give these commands.

1. **Backend** (BE-1): `source backend/.venv/bin/activate && python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8080 --reload`
2. **Scraper** (BE-2): `python3 -m scraper.main`
3. **Desktop app** (FE-1 + FE-2): `npm run tauri dev`
4. **Frontend only** (offline): `npm run dev` — set `USE_MOCKS = true` in `src/api/client.js`

API docs available at: http://127.0.0.1:8080/docs

Branch strategy: FE-1 → `fe1/*`, FE-2 → `fe2/*`, BE-1 → `be1/*`, BE-2 → `be2/*`
