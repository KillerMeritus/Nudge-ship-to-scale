"""
Tasks router — full CRUD backed by tasks.json via task_store.

Phase 2 additions:
  - elapsed_seconds, task_status, started_at fields on every task
  - POST /tasks/{id}/start   — mark running, auto-pause any other active task
  - POST /tasks/{id}/pause   — accumulate elapsed time, clear active task
  - POST /tasks/{id}/resume  — resume from stored elapsed, auto-pause others
"""

import logging
logger = logging.getLogger(__name__)

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.storage.task_store import load_tasks, save_tasks
from backend import state

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: str = ""
    estimated_hours: int = 0
    estimated_minutes: int = Field(default=0, ge=0, le=59)
    priority: str = "Medium"          # "Low" | "Medium" | "High"
    tags: list[str] = []
    status: str = "Todo"              # "Todo" | "In Progress" | "Done"
    is_recurring: bool = False
    # Phase 2 fields
    elapsed_seconds: int = 0
    task_status: str = "idle"         # "idle" | "running" | "paused"
    started_at: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    estimated_hours: Optional[int] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=0, le=59)
    priority: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None
    is_recurring: Optional[bool] = None
    # Phase 2 fields
    elapsed_seconds: Optional[int] = None
    task_status: Optional[str] = None


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _accumulate_elapsed(task: dict) -> dict:
    """If task is currently marked running, add wall-clock time since started_at."""
    if task.get("task_status") == "running" and task.get("started_at"):
        try:
            started = datetime.fromisoformat(task["started_at"])
            delta = (datetime.now() - started).total_seconds()
            task["elapsed_seconds"] = int(task.get("elapsed_seconds", 0) + delta)
        except (ValueError, TypeError):
            pass
    return task


def _pause_task_in_list(tasks: list, task_id: str) -> list:
    """Find a task by id in the list, accumulate elapsed time, mark paused."""
    idx = next((i for i, t in enumerate(tasks) if t["id"] == task_id), None)
    if idx is not None:
        tasks[idx] = _accumulate_elapsed(tasks[idx])
        tasks[idx]["task_status"] = "paused"
        tasks[idx]["started_at"] = None
        logger.info("Auto-paused task: %s", task_id)
    return tasks


# ── CRUD ENDPOINTS ────────────────────────────────────────────────────────────

@router.get("")
async def get_tasks():
    return load_tasks()


@router.post("", status_code=201)
async def create_task(body: TaskCreate):
    tasks = load_tasks()
    new_task = {
        "id": str(uuid.uuid4()),
        **body.model_dump(),
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
    }
    tasks.append(new_task)
    save_tasks(tasks)
    logger.info("Task created: %s [%s]", new_task["id"], new_task["title"])
    return new_task


@router.put("/{task_id}")
async def update_task(task_id: str, body: TaskUpdate):
    tasks = load_tasks()
    idx = next((i for i, t in enumerate(tasks) if t["id"] == task_id), None)
    if idx is None:
        logger.warning("Task not found for update: %s", task_id)
        raise HTTPException(status_code=404, detail="Task not found")

    updates = body.model_dump(exclude_none=True)
    task = tasks[idx]
    task.update(updates)

    # Set completed_at when status flips to Done
    if updates.get("status") == "Done" and task.get("completed_at") is None:
        task["completed_at"] = datetime.now().isoformat()
        # Clear active task if this was the running one
        if state.get_active_task() and state.get_active_task()["id"] == task_id:
            task = _accumulate_elapsed(task)
            task["task_status"] = "idle"
            task["started_at"] = None
            state.set_active_task(None)
    elif updates.get("status") != "Done":
        task["completed_at"] = None

    tasks[idx] = task
    save_tasks(tasks)
    logger.info("Task updated: %s — fields: %s", task_id, list(updates.keys()))
    return task


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    tasks = load_tasks()
    new_tasks = [t for t in tasks if t["id"] != task_id]
    if len(new_tasks) == len(tasks):
        logger.warning("Task not found for delete: %s", task_id)
        raise HTTPException(status_code=404, detail="Task not found")

    # Clear active task if this task was running
    if state.get_active_task() and state.get_active_task()["id"] == task_id:
        state.set_active_task(None)
        logger.info("Active task cleared (deleted): %s", task_id)

    save_tasks(new_tasks)
    logger.info("Task deleted: %s", task_id)
    return {"deleted": True}


# ── TASK STATE MACHINE ENDPOINTS (Phase 2) ────────────────────────────────────

@router.post("/{task_id}/start")
async def start_task(task_id: str):
    """
    Mark a task as running.
    If another task is already running, auto-pause it first.
    Enforces one active task at a time server-side.
    """
    tasks = load_tasks()
    idx = next((i for i, t in enumerate(tasks) if t["id"] == task_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[idx]

    if task.get("status") == "Done":
        raise HTTPException(status_code=400, detail="Cannot start a completed task")

    # Auto-pause whatever is currently active (if different task)
    current_active = state.get_active_task()
    if current_active and current_active["id"] != task_id:
        tasks = _pause_task_in_list(tasks, current_active["id"])

    # Start the requested task
    task = tasks[idx]  # re-fetch in case list was mutated above
    task["task_status"] = "running"
    task["status"] = "In Progress"
    task["started_at"] = datetime.now().isoformat()
    tasks[idx] = task
    save_tasks(tasks)

    state.set_active_task(task)
    logger.info("Task started: %s [%s]", task_id, task["title"])
    return task


@router.post("/{task_id}/pause")
async def pause_task(task_id: str):
    """
    Pause a running task. Accumulates elapsed time and persists to tasks.json.
    """
    tasks = load_tasks()
    idx = next((i for i, t in enumerate(tasks) if t["id"] == task_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[idx]
    task = _accumulate_elapsed(task)
    task["task_status"] = "paused"
    task["started_at"] = None
    tasks[idx] = task
    save_tasks(tasks)

    # Clear global active task if this was it
    if state.get_active_task() and state.get_active_task()["id"] == task_id:
        state.set_active_task(None)

    logger.info("Task paused: %s — elapsed: %ds", task_id, task.get("elapsed_seconds", 0))
    return task


@router.post("/{task_id}/resume")
async def resume_task(task_id: str):
    """
    Resume a paused task from its stored elapsed_seconds.
    Auto-pauses any currently running task first.
    """
    tasks = load_tasks()
    idx = next((i for i, t in enumerate(tasks) if t["id"] == task_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[idx]

    if task.get("status") == "Done":
        raise HTTPException(status_code=400, detail="Cannot resume a completed task")

    # Auto-pause any currently active different task
    current_active = state.get_active_task()
    if current_active and current_active["id"] != task_id:
        tasks = _pause_task_in_list(tasks, current_active["id"])

    # Resume
    task = tasks[idx]
    task["task_status"] = "running"
    task["started_at"] = datetime.now().isoformat()
    tasks[idx] = task
    save_tasks(tasks)

    state.set_active_task(task)
    logger.info("Task resumed: %s [%s] from %ds", task_id, task["title"], task.get("elapsed_seconds", 0))
    return task
