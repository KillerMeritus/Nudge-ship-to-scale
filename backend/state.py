"""
backend/state.py — Shared in-memory state accessed by multiple routers.

Keeping active-task state here avoids circular imports between
tasks.py (which sets the active task) and timer.py (which exposes it).
"""

from __future__ import annotations

_active_task: dict | None = None


def get_active_task() -> dict | None:
    """Return the currently running task dict, or None."""
    return _active_task


def set_active_task(task: dict | None) -> None:
    """Set or clear the globally active task."""
    global _active_task
    _active_task = task
