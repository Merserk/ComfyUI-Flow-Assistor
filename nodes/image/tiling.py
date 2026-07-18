"""Tiling helpers migrated to the ComfyUI V3 node API."""

import torch
import torch.nn.functional as F

import comfy.utils
from comfy_api.latest import io
from ..categories import IMAGE

from ...v3_types import TileData


class TileManager(io.ComfyNode):
    """Placeholder tile source that preserves the current workflow contract."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="TileManager",
            display_name="Tile Manager (Crop)",
            category=IMAGE,
            description="Passes an image and mask through with an empty TILE_DATA payload.",
            inputs=[
                io.Image.Input("image"),
                io.Mask.Input("mask"),
                io.Int.Input("padding", default=64),
                io.Int.Input("target_size", default=1024),
            ],
            outputs=[
                io.Image.Output(display_name="image"),
                io.Mask.Output(display_name="mask"),
                TileData.Output(display_name="tile_data"),
            ],
        )

    @classmethod
    def execute(cls, image, mask, padding, target_size) -> io.NodeOutput:
        del padding, target_size
        return io.NodeOutput(image, mask, {})


class TileCompositor(io.ComfyNode):
    """Paste a processed tile back into its source image."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="TileCompositor",
            display_name="Tile Compositor (Merge)",
            category=IMAGE,
            description="Merges a processed tile into the original image using TILE_DATA.",
            inputs=[
                io.Image.Input("base_image", tooltip="The original image."),
                io.Image.Input("processed_tile", tooltip="The result from the sampler."),
                TileData.Input("tile_data"),
                io.Int.Input("feather", default=16, min=0, max=100, optional=True),
            ],
            outputs=[io.Image.Output(display_name="composite_image")],
        )

    @classmethod
    def execute(cls, base_image, processed_tile, tile_data, feather=16) -> io.NodeOutput:
        if not tile_data or "original_bbox" not in tile_data:
            print("[TileCompositor] Invalid tile_data. Returning base image.")
            return io.NodeOutput(base_image)

        x, y, w, h = (int(value) for value in tile_data["original_bbox"])
        base_device = base_image.device
        base_dtype = base_image.dtype
        processed_tile = processed_tile.to(device=base_device, dtype=base_dtype)

        if int(processed_tile.shape[2]) != w or int(processed_tile.shape[1]) != h:
            samples = processed_tile.movedim(-1, 1)
            upscaled = comfy.utils.common_upscale(samples, w, h, "lanczos", "disabled")
            restored_tile = upscaled.movedim(1, -1)
        else:
            restored_tile = processed_tile

        output_image = base_image.clone()
        batch, image_height, image_width, _ = output_image.shape

        x = max(0, min(x, image_width - 1))
        y = max(0, min(y, image_height - 1))
        w = max(1, min(w, image_width - x))
        h = max(1, min(h, image_height - y))
        restored_tile = restored_tile[:, :h, :w, :]

        composite_mask = torch.zeros(
            (batch, image_height, image_width),
            dtype=torch.float32,
            device=base_device,
        )
        composite_mask[:, y : y + h, x : x + w] = 1.0

        if feather > 0:
            mask_4d = composite_mask.unsqueeze(1)
            radius = int(feather)
            kernel = radius * 2 + 1
            mask_4d = F.avg_pool2d(mask_4d, kernel_size=kernel, stride=1, padding=radius)
            composite_mask = mask_4d.squeeze(1)

        background_crop = output_image[:, y : y + h, x : x + w, :]
        mask_crop = composite_mask[:, y : y + h, x : x + w].unsqueeze(-1).to(dtype=base_dtype)
        merged_crop = restored_tile * mask_crop + background_crop * (1.0 - mask_crop)
        output_image[:, y : y + h, x : x + w, :] = merged_crop
        return io.NodeOutput(output_image)


__all__ = ["TileManager", "TileCompositor"]
