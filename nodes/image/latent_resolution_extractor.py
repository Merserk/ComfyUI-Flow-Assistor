"""Extract pixel dimensions from a latent tensor."""

from comfy_api.latest import io
from ..categories import IMAGE


class ImageLatentResolutionExtractorNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ImageLatentResolutionExtractorNode",
            display_name="Image Latent Resolution Extractor",
            category=IMAGE,
            inputs=[io.Latent.Input("samples")],
            outputs=[
                io.Latent.Output(display_name="latent"),
                io.Int.Output(display_name="width"),
                io.Int.Output(display_name="height"),
            ],
        )

    @classmethod
    def execute(cls, samples) -> io.NodeOutput:
        latent = samples["samples"]
        return io.NodeOutput(samples, int(latent.shape[3] * 8), int(latent.shape[2] * 8))


__all__ = ["ImageLatentResolutionExtractorNode"]
