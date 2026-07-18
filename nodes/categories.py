"""Canonical ComfyUI category paths for Flow Assistor nodes."""

ROOT = "flow-assistor"
FLOW = f"{ROOT}/flow"
TEXT = f"{ROOT}/text"
IMAGE = f"{ROOT}/image"
LOADERS = f"{ROOT}/loaders"
SAMPLING = f"{ROOT}/sampling"
DIAGNOSTICS = f"{ROOT}/diagnostics"
UTILS = f"{ROOT}/utils"

ALL_CATEGORIES = frozenset({
    FLOW,
    TEXT,
    IMAGE,
    LOADERS,
    SAMPLING,
    DIAGNOSTICS,
    UTILS,
})

__all__ = [
    "ROOT",
    "FLOW",
    "TEXT",
    "IMAGE",
    "LOADERS",
    "SAMPLING",
    "DIAGNOSTICS",
    "UTILS",
    "ALL_CATEGORIES",
]
