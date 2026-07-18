"""Debug and summarize arbitrary ComfyUI values."""

import torch
from comfy_api.latest import io
from ..categories import DIAGNOSTICS


def analyze_value(any_input) -> str:
    text_output = "None"
    try:
        if isinstance(any_input, torch.Tensor):
            shape = any_input.shape
            text_output = (
                f"Type: Tensor\nShape: {list(shape)}\n"
                f"Dtype: {any_input.dtype}\nDevice: {any_input.device}\n"
            )
            if any_input.ndim == 4:
                if shape[3] <= 4 and shape[1] > 8 and shape[2] > 8:
                    batch, height, width, channels = shape
                    ratio = width / height if height > 0 else 0
                    text_output += (
                        "\n--- IMAGE DETECTED ---\n"
                        f"Resolution: {width}x{height}\n"
                        f"Aspect Ratio: {ratio:.2f}\n"
                        f"Batch Size: {batch}\nChannels: {channels}"
                    )
                elif shape[1] <= 4 and shape[2] > 8 and shape[3] > 8:
                    batch, _channels, height, width = shape
                    text_output += (
                        "\n--- RAW LATENT/NCHW ---\n"
                        f"Latent Size: {width}x{height}\n"
                        f"Pixel Res (~8x): {width * 8}x{height * 8}\n"
                        f"Batch Size: {batch}"
                    )
            elif any_input.ndim == 3:
                batch, height, width = shape
                text_output += (
                    "\n--- MASK DETECTED ---\n"
                    f"Resolution: {width}x{height}\nBatch Size: {batch}"
                )
        elif isinstance(any_input, dict) and "samples" in any_input:
            samples = any_input["samples"]
            if isinstance(samples, torch.Tensor):
                batch, _channels, height, width = samples.shape
                ratio = width / height if height > 0 else 0
                text_output = (
                    f"Type: LATENT (Dict)\nShape: {list(samples.shape)}\n"
                    "\n--- RESOLUTION INFO ---\n"
                    f"Latent Size: {width}x{height}\n"
                    f"Pixel Res (8x): {width * 8}x{height * 8}\n"
                    f"Aspect Ratio: {ratio:.2f}\nBatch Size: {batch}"
                )
            else:
                text_output = "Type: LATENT (Dict)\nError: 'samples' is not a tensor."
        elif isinstance(any_input, list):
            text_output = f"Type: List\nLength: {len(any_input)}\n"
            if any_input:
                text_output += f"Sample[0]: {str(any_input[0])[:50]}..."
        elif isinstance(any_input, (int, float, bool, str)):
            text_output = f"Type: {type(any_input).__name__}\nValue: {any_input}"
        else:
            raw = str(any_input)
            text_output = f"Type: {type(any_input)}\n"
            text_output += f"Value: {raw[:200]}..." if raw else "Empty"
    except Exception as exc:
        text_output = f"Error analyzing data: {exc}"
    return text_output


class OutputAnyDebugDataNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="OutputAnyDebugDataNode",
            display_name="Debug Data (Any Input)",
            category=DIAGNOSTICS,
            inputs=[io.AnyType.Input("any_input")],
            outputs=[io.String.Output(display_name="debug_text")],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, any_input) -> io.NodeOutput:
        text = analyze_value(any_input)
        return io.NodeOutput(text, ui={"text": [text]})


__all__ = ["OutputAnyDebugDataNode", "analyze_value"]
