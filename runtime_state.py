"""Concurrency-safe runtime state for V3 classmethod-based nodes.

ComfyUI V3 sanitizes node classes and does not expose persistent node instances.
State that must survive between executions is therefore stored here and keyed by
ComfyUI's hidden unique node id.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any


_MAX_STATES = 2048
_MAX_IDLE_SECONDS = 24 * 60 * 60
_LOCK = threading.RLock()
_QUEUE_STATES: dict[tuple[str, str], dict[str, Any]] = {}


def normalize_node_id(value: Any) -> str:
    """Normalize V3 hidden values, including list-wrapped list-input values."""
    while isinstance(value, (list, tuple)) and value:
        value = value[0]
    text = "" if value is None else str(value).strip()
    return text or "unknown"


def _cleanup_locked(now: float) -> None:
    if len(_QUEUE_STATES) <= _MAX_STATES:
        stale = [
            key
            for key, state in _QUEUE_STATES.items()
            if now - float(state.get("last_access", now)) > _MAX_IDLE_SECONDS
        ]
    else:
        ordered = sorted(
            _QUEUE_STATES,
            key=lambda key: float(_QUEUE_STATES[key].get("last_access", 0.0)),
        )
        stale = ordered[: max(1, len(_QUEUE_STATES) - _MAX_STATES)]

    for key in stale:
        _QUEUE_STATES.pop(key, None)


def with_queue_state(
    namespace: str,
    node_id: Any,
    factory: Callable[[], dict[str, Any]],
    operation: Callable[[dict[str, Any]], Any],
) -> Any:
    """Run an operation atomically against a node-specific mutable state."""
    key = (namespace, normalize_node_id(node_id))
    now = time.monotonic()
    with _LOCK:
        state = _QUEUE_STATES.get(key)
        if state is None:
            state = factory()
            _QUEUE_STATES[key] = state
        state["last_access"] = now
        result = operation(state)
        _cleanup_locked(now)
        return result


def clear_runtime_state() -> None:
    """Clear all state; intended for tests and explicit extension reloads."""
    with _LOCK:
        _QUEUE_STATES.clear()


__all__ = ["clear_runtime_state", "normalize_node_id", "with_queue_state"]
