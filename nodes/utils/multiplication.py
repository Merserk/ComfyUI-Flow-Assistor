"""Scale two integer values and an optional latent."""

import torch
import torch.nn.functional as functional
from comfy_api.latest import io
from ..categories import UTILS


class MultiplicationNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MultiplicationNode",
            display_name="Multiplication (Dual & Latent)",
            category=UTILS,
            inputs=[
                io.Float.Input("multiplier", default=2.0, step=0.1, min=0.1, max=100.0),
                io.Int.Input("value_1", default=0, min=0, max=9_999_999, force_input=True, optional=True),
                io.Int.Input("value_2", default=0, min=0, max=9_999_999, force_input=True, optional=True),
                io.Latent.Input("samples", optional=True),
            ],
            outputs=[
                io.Int.Output(display_name="result_1"),
                io.Int.Output(display_name="result_2"),
                io.Latent.Output(display_name="latent"),
            ],
        )

    @classmethod
    def execute(cls, multiplier, value_1=0, value_2=0, samples=None) -> io.NodeOutput:
        factor = float(multiplier)
        out_1 = int(round(int(value_1 or 0) * factor))
        out_2 = int(round(int(value_2 or 0) * factor))
        out_latent = None
        if samples is not None:
            out_latent = samples.copy()
            tensor = out_latent["samples"]
            new_h = int(round(tensor.shape[2] * factor))
            new_w = int(round(tensor.shape[3] * factor))
            if new_h > 0 and new_w > 0:
                out_latent["samples"] = functional.interpolate(
                    tensor,
                    size=(new_h, new_w),
                    mode="bilinear",
                    align_corners=False,
                )
            else:
                out_latent = samples
        if out_latent is None:
            out_latent = {"samples": torch.zeros((1, 4, 1, 1))}
        return io.NodeOutput(out_1, out_2, out_latent)


__all__ = ["MultiplicationNode"]
