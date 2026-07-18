"""Non-blocking delay passthrough node."""

import asyncio

from comfy_api.latest import io
from ..categories import FLOW


class AddDelay(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        template = io.MatchType.Template("flow_assistor_delay")
        return io.Schema(
            node_id="AddDelay",
            display_name="Add Delay",
            category=FLOW,
            description="Waits asynchronously, then returns the input unchanged.",
            inputs=[
                io.MatchType.Input("input", template=template),
                io.Float.Input(
                    "delay",
                    default=6.0,
                    min=0.0,
                    max=3600.0,
                    step=0.1,
                ),
            ],
            outputs=[io.MatchType.Output(template=template, display_name="output")],
            not_idempotent=True,
        )

    @classmethod
    async def execute(cls, input, delay=6.0) -> io.NodeOutput:
        try:
            seconds = max(0.0, float(delay))
        except (TypeError, ValueError):
            seconds = 6.0
        if seconds:
            await asyncio.sleep(seconds)
        return io.NodeOutput(input)


__all__ = ["AddDelay"]
