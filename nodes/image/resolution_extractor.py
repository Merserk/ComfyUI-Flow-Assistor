"""Extract image dimensions and produce a matching empty latent."""

import torch
from comfy_api.latest import io
from ..categories import IMAGE


class ImageResolutionExtractorNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ImageResolutionExtractorNode",
            display_name="Image Resolution Extractor",
            category=IMAGE,
            inputs=[io.Image.Input("image")],
            outputs=[
                io.Latent.Output(display_name="latent"),
                io.Int.Output(display_name="width"),
                io.Int.Output(display_name="height"),
                io.Image.Output(display_name="image"),
            ],
        )

    @classmethod
    def execute(cls, image) -> io.NodeOutput:
        batch, height, width = int(image.shape[0]), int(image.shape[1]), int(image.shape[2])
        latent = {"samples": torch.zeros([batch, 4, height // 8, width // 8])}
        return io.NodeOutput(latent, width, height, image)


__all__ = ["ImageResolutionExtractorNode"]
