"""Resize images to a megapixel tier while retaining aspect ratio."""

import math

import torch
import comfy.utils
from comfy_api.latest import io
from ..categories import IMAGE


RESOLUTION_OPTIONS = [
    "0.25 MP (Reference: 512x512)",
    "0.60 MP (Reference: 768x768)",
    "1.00 MP (Reference: 1024x1024)",
    "2.00 MP (Reference: 1408x1408)",
    "3.00 MP (Reference: 1728x1728)",
    "4.00 MP (Reference: 2048x2048)",
]


class ImageResolutionFitNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ImageResolutionFitNode",
            display_name="Image Resolution Fit",
            category=IMAGE,
            inputs=[
                io.Image.Input("image"),
                io.Combo.Input(
                    "resolution_select",
                    options=RESOLUTION_OPTIONS,
                    default="1.00 MP (Reference: 1024x1024)",
                ),
            ],
            outputs=[
                io.Latent.Output(display_name="latent"),
                io.Int.Output(display_name="width"),
                io.Int.Output(display_name="height"),
                io.Image.Output(display_name="image"),
            ],
        )

    @classmethod
    def execute(cls, image, resolution_select) -> io.NodeOutput:
        input_h, input_w = int(image.shape[1]), int(image.shape[2])
        try:
            reference = str(resolution_select).split("Reference: ", 1)[1].split(")", 1)[0]
            ref_w, ref_h = (int(value) for value in reference.split("x"))
            target_pixels = ref_w * ref_h
        except (IndexError, TypeError, ValueError):
            target_pixels = 1024 * 1024

        current_pixels = input_w * input_h
        scale = math.sqrt(target_pixels / current_pixels) if current_pixels else 1.0
        new_w = max(8, round((input_w * scale) / 8) * 8)
        new_h = max(8, round((input_h * scale) / 8) * 8)

        samples = image.movedim(-1, 1)
        resized = comfy.utils.common_upscale(samples, new_w, new_h, "lanczos", "disabled").movedim(1, -1)
        latent = {"samples": torch.zeros([int(image.shape[0]), 4, new_h // 8, new_w // 8])}
        return io.NodeOutput(latent, new_w, new_h, resized)


__all__ = ["ImageResolutionFitNode", "RESOLUTION_OPTIONS"]
