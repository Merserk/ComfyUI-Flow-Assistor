"""Workflow control nodes."""

from .bypass_control import BypassControl
from .delay import AddDelay
from .passthrough import AnyPassthrough1to6, AnyPassthrough6to1

NODE_CLASSES = (
    AnyPassthrough6to1,
    AnyPassthrough1to6,
    BypassControl,
    AddDelay,
)

__all__ = [
    "AnyPassthrough6to1",
    "AnyPassthrough1to6",
    "BypassControl",
    "AddDelay",
    "NODE_CLASSES",
]
