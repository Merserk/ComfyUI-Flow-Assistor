"""ComfyUI V3 extension entrypoint and node inventory."""

from comfy_api.latest import ComfyExtension, io

from .nodes import NODE_CLASSES
from .routes import register_routes
from .runtime_state import clear_runtime_state


class FlowAssistorExtension(ComfyExtension):
    async def on_load(self) -> None:
        clear_runtime_state()
        register_routes()

    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return list(NODE_CLASSES)


async def comfy_entrypoint() -> FlowAssistorExtension:
    return FlowAssistorExtension()


__all__ = ["FlowAssistorExtension", "NODE_CLASSES", "comfy_entrypoint"]
