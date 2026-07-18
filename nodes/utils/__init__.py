"""General utility nodes."""

from .memory_cleaner import VRAMRAMCleanerNode
from .multiplication import MultiplicationNode

NODE_CLASSES = (
    VRAMRAMCleanerNode,
    MultiplicationNode,
)

__all__ = [
    "VRAMRAMCleanerNode",
    "MultiplicationNode",
    "NODE_CLASSES",
]
