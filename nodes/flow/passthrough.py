"""Generic passthrough nodes implemented with native ComfyUI V3 types."""

from comfy_api.latest import io
from ..categories import FLOW


class AnyPassthrough6to1(io.ComfyNode):
    """Output the first connected value from up to six unrelated inputs."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="AnyPassthrough6to1",
            display_name="Any Passthrough (6 → 1)",
            category=FLOW,
            inputs=[
                io.AnyType.Input(f"input{i}", optional=True)
                for i in range(1, 7)
            ],
            outputs=[io.AnyType.Output(display_name="output")],
        )

    @classmethod
    def execute(
        cls,
        input1=None,
        input2=None,
        input3=None,
        input4=None,
        input5=None,
        input6=None,
    ) -> io.NodeOutput:
        for value in (input1, input2, input3, input4, input5, input6):
            if value is not None:
                return io.NodeOutput(value)
        return io.NodeOutput(None)


class AnyPassthrough1to6(io.ComfyNode):
    """Duplicate one value to six outputs while retaining its connected type."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        template = io.MatchType.Template("flow_assistor_passthrough")
        return io.Schema(
            node_id="AnyPassthrough1to6",
            display_name="Any Passthrough (1 → 6)",
            category=FLOW,
            inputs=[io.MatchType.Input("input", template=template)],
            outputs=[
                io.MatchType.Output(template=template, display_name=f"out{i}")
                for i in range(1, 7)
            ],
        )

    @classmethod
    def execute(cls, input) -> io.NodeOutput:
        return io.NodeOutput(input, input, input, input, input, input)


__all__ = ["AnyPassthrough6to1", "AnyPassthrough1to6"]
