"""Stateful multiline prompt queue for ComfyUI V3."""

from comfy_api.latest import io
from ..categories import TEXT

from ...runtime_state import with_queue_state


def prepare_lines(prompts: str, strip_lines: bool, skip_empty: bool) -> list[str]:
    lines = str(prompts).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if strip_lines:
        lines = [line.strip() for line in lines]
    if skip_empty:
        lines = [line for line in lines if line != ""]
    return lines


def _new_state() -> dict:
    return {"index": 0, "lines": [], "last_conf": None, "reset_trigger": None}


class PromptQueue(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="PromptQueue",
            display_name="Prompt Queue",
            category=TEXT,
            description="Outputs the next processed line on each workflow execution.",
            inputs=[
                io.String.Input("prompts", multiline=True, default=""),
                io.Combo.Input("on_end", options=["empty", "repeat_last", "loop"], default="empty", optional=True),
                io.Boolean.Input("strip_lines", default=True, optional=True),
                io.Boolean.Input("skip_empty_lines", default=True, optional=True),
                io.Int.Input("reset_trigger", default=0, min=0, max=2**31 - 1, optional=True),
            ],
            outputs=[io.String.Output(display_name="text")],
            hidden=[io.Hidden.unique_id],
            not_idempotent=True,
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return float("nan")

    @classmethod
    def execute(
        cls,
        prompts,
        on_end="empty",
        strip_lines=True,
        skip_empty_lines=True,
        reset_trigger=0,
    ) -> io.NodeOutput:
        node_id = getattr(cls.hidden, "unique_id", "unknown")

        def next_value(state: dict) -> str:
            config = (str(prompts), bool(strip_lines), bool(skip_empty_lines))
            if state["last_conf"] != config:
                state["lines"] = prepare_lines(*config)
                state["index"] = 0
                state["last_conf"] = config
            if state["reset_trigger"] != int(reset_trigger):
                state["index"] = 0
                state["reset_trigger"] = int(reset_trigger)

            lines = state["lines"]
            if not lines:
                return ""

            count = len(lines)
            index = state["index"]
            if index >= count:
                if on_end == "loop":
                    index %= count
                elif on_end == "repeat_last":
                    index = count - 1
                else:
                    return ""

            output = lines[index]
            next_index = state["index"] + 1
            if next_index >= count:
                if on_end == "loop":
                    state["index"] = 0
                else:
                    state["index"] = count
            else:
                state["index"] = next_index
            return output

        value = with_queue_state("prompt", node_id, _new_state, next_value)
        return io.NodeOutput(value)


__all__ = ["PromptQueue", "prepare_lines"]
