"""Debugging and runtime precision inspection nodes."""

from .debug_data import OutputAnyDebugDataNode
from .precision import RuntimePrecisionCLIP, RuntimePrecisionModel, RuntimePrecisionVAE

NODE_CLASSES = (
    OutputAnyDebugDataNode,
    RuntimePrecisionModel,
    RuntimePrecisionCLIP,
    RuntimePrecisionVAE,
)

__all__ = [
    "OutputAnyDebugDataNode",
    "RuntimePrecisionModel",
    "RuntimePrecisionCLIP",
    "RuntimePrecisionVAE",
    "NODE_CLASSES",
]
