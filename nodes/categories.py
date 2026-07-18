"""Canonical ComfyUI category paths for Flow Assistor nodes."""

ROOT = "flow-assistor"
FLOW = f"{ROOT}/flow"
TEXT = f"{ROOT}/text"
IMAGE = f"{ROOT}/image"
IMAGE_CAPTION = f"{IMAGE}/caption"
LOADERS = f"{ROOT}/loaders"
SAMPLING = f"{ROOT}/sampling"
DIAGNOSTICS = f"{ROOT}/diagnostics"
UTILS = f"{ROOT}/utils"

ALL_CATEGORIES = frozenset({
    FLOW,
    TEXT,
    IMAGE,
    IMAGE_CAPTION,
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
    "IMAGE_CAPTION",
    "LOADERS",
    "SAMPLING",
    "DIAGNOSTICS",
    "UTILS",
    "ALL_CATEGORIES",
]
