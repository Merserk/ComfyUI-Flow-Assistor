"""Prompt, text, and camera-description nodes."""

from .camera_angle import CameraAngleControl
from .display_text import DisplayText
from .prompt_enrichment import CLIPTextEncodePromptEnrichment
from .prompt_queue import PromptQueue
from .prompt_queue_folder import PromptQueueFromFolder

NODE_CLASSES = (
    PromptQueue,
    PromptQueueFromFolder,
    CLIPTextEncodePromptEnrichment,
    DisplayText,
    CameraAngleControl,
)

__all__ = [
    "PromptQueue",
    "PromptQueueFromFolder",
    "CLIPTextEncodePromptEnrichment",
    "DisplayText",
    "CameraAngleControl",
    "NODE_CLASSES",
]
