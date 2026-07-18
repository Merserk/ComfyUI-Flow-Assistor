"""Output-node text display with workflow persistence."""

from typing import Any

from comfy_api.latest import io
from ..categories import TEXT

from ...runtime_state import normalize_node_id


def _unwrap_list(value: Any) -> Any:
    while isinstance(value, list) and len(value) == 1:
        value = value[0]
    return value


def _persist_text(text: Any, unique_id: Any, extra_pnginfo: Any) -> None:
    node_id = normalize_node_id(unique_id)
    metadata = _unwrap_list(extra_pnginfo)
    if not isinstance(metadata, dict):
        return
    workflow = metadata.get("workflow")
    if not isinstance(workflow, dict) or not isinstance(workflow.get("nodes"), list):
        return
    node = next((item for item in workflow["nodes"] if str(item.get("id")) == node_id), None)
    if node is not None:
        node["widgets_values"] = [text]


class DisplayText(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="DisplayText",
            display_name="Show Text",
            category=TEXT,
            inputs=[io.String.Input("text", force_input=True)],
            outputs=[],
            hidden=[io.Hidden.unique_id],
            is_input_list=True,
            is_output_node=True,
            not_idempotent=True,
        )

    @classmethod
    def execute(cls, text) -> io.NodeOutput:
        unique_id = getattr(cls.hidden, "unique_id", None)
        extra_pnginfo = getattr(cls.hidden, "extra_pnginfo", None)
        try:
            _persist_text(text, unique_id, extra_pnginfo)
        except Exception:
            pass
        return io.NodeOutput(ui={"text": text})


__all__ = ["DisplayText"]
