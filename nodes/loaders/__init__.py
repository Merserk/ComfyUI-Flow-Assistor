"""Model and resource loader nodes."""

from .lora_online import LoRAOnlineNode

NODE_CLASSES = (LoRAOnlineNode,)

__all__ = ["LoRAOnlineNode", "NODE_CLASSES"]
