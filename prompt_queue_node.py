# ComfyUI custom node: Prompt Queue
# Place this file in: ComfyUI/custom_nodes/comfyui-prompt-queue/prompt_queue_node.py

from typing import Dict, Any, Tuple, List

class PromptQueue:
    """
    A text node that outputs the next line from a multiline prompt on each run.
    - Connect the output to a text encoder (e.g., CLIP Text Encode).
    - Each queued generation advances to the next line.
    - Resets when the prompt text changes, or when reset_trigger changes.
    """

    def __init__(self):
        # Per-node instance state, keyed by the node's unique id (provided by ComfyUI)
        self._state: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts": ("STRING", {
                    "multiline": True,
                    "default": "",
                }),
            },
            "optional": {
                # What to do when we hit the end of the list
                "on_end": (["empty", "repeat_last", "loop"], {"default": "empty"}),
                # Clean-up options
                "strip_lines": ("BOOLEAN", {"default": True}),
                "skip_empty_lines": ("BOOLEAN", {"default": True}),
                # Change this number (e.g., 0 -> 1) to reset to the first line
                "reset_trigger": ("INT", {"default": 0, "min": 0, "max": 2**31 - 1}),
            },
            "hidden": {
                # Unique node id injected by ComfyUI for per-node persistent state
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "next_line"
    CATEGORY = "flow-assistor"

    # Force recomputation each time the graph runs so we advance properly across queue items
    def IS_CHANGED(self, *args, **kwargs):
        return True

    def _get_state(self, unique_id: str) -> Dict[str, Any]:
        if unique_id not in self._state:
            self._state[unique_id] = {
                "index": 0,
                "lines": [],
                "last_conf": None,       # tracks prompts + options for auto-reset on change
                "reset_trigger": None,   # last seen reset trigger
            }
        return self._state[unique_id]

    @staticmethod
    def _prepare_lines(prompts: str, strip_lines: bool, skip_empty: bool) -> List[str]:
        text = prompts.replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")
        if strip_lines:
            lines = [ln.strip() for ln in lines]
        if skip_empty:
            lines = [ln for ln in lines if ln != ""]
        return lines

    def next_line(
        self,
        prompts: str,
        on_end: str = "empty",
        strip_lines: bool = True,
        skip_empty_lines: bool = True,
        reset_trigger: int = 0,
        unique_id: str = "",
    ) -> Tuple[str]:
        st = self._get_state(unique_id)

        # Build the canonical config snapshot to detect changes that should reset the cursor
        current_conf = (prompts, strip_lines, skip_empty_lines)

        # If the prompt text or line-processing options changed, rebuild and reset index
        if st["last_conf"] != current_conf:
            st["lines"] = self._prepare_lines(prompts, strip_lines, skip_empty_lines)
            st["index"] = 0
            st["last_conf"] = current_conf

        # Manual reset when reset_trigger changes
        if st["reset_trigger"] != reset_trigger:
            st["index"] = 0
            st["reset_trigger"] = reset_trigger

        lines = st["lines"]
        n = len(lines)

        # No lines available -> return empty string
        if n == 0:
            return ("",)

        idx = st["index"]

        # Decide what to output based on index and on_end policy
        if idx >= n:
            if on_end == "loop":
                idx = idx % n
            elif on_end == "repeat_last":
                idx = n - 1
            else:  # "empty"
                return ("",)

        text_out = lines[idx]

        # Advance the index for the next run
        next_idx = st["index"] + 1
        if next_idx >= n:
            if on_end == "loop":
                st["index"] = 0
            elif on_end == "repeat_last":
                # park just past the end so we keep returning the last line
                st["index"] = n
            else:  # "empty": mark as exhausted
                st["index"] = n
        else:
            st["index"] = next_idx

        return (text_out,)


# Required mappings so ComfyUI can discover the node
NODE_CLASS_MAPPINGS = {
    "PromptQueue": PromptQueue,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptQueue": "Prompt Queue",
}