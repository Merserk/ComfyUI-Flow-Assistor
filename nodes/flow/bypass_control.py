"""Frontend-operated sidecar bypass controller."""

from comfy_api.latest import io
from ..categories import FLOW


class BypassControl(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        inputs = []
        for index in range(1, 5):
            inputs.extend(
                [
                    io.AnyType.Input(f"input_{index}", optional=True),
                    io.String.Input(
                        f"label_{index}",
                        default=f"Group {index}",
                        multiline=False,
                        optional=True,
                    ),
                    io.Boolean.Input(
                        f"active_{index}",
                        default=True,
                        label_on="Active",
                        label_off="BYPASS",
                        optional=True,
                    ),
                ]
            )
        return io.Schema(
            node_id="BypassControl",
            display_name="Flow Control (Sidecar Bypass)",
            category=FLOW,
            description="Controls the bypass mode of four connected upstream nodes in the frontend.",
            inputs=inputs,
            outputs=[],
            is_output_node=True,
            not_idempotent=True,
        )

    @classmethod
    def execute(cls, **kwargs) -> io.NodeOutput:
        return io.NodeOutput()


__all__ = ["BypassControl"]
