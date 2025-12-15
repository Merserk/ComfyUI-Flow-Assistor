import torch
import torch.nn.functional as F
import comfy.utils


class TileManager:
    """
    Optional: Standard non-interactive crop node (placeholder).
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mask": ("MASK",),
                "padding": ("INT", {"default": 64}),
                "target_size": ("INT", {"default": 1024}),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "TILE_DATA")
    FUNCTION = "create_tile"
    CATEGORY = "flow-assistor/tiling"

    def create_tile(self, image, mask, padding, target_size):
        return (image, mask, {})


class TileCompositor:
    """
    Pastes the processed tile back onto the original image using TILE_DATA.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_image": ("IMAGE", {"tooltip": "The original image"}),
                "processed_tile": ("IMAGE", {"tooltip": "The result from the sampler"}),
                "tile_data": ("TILE_DATA",),
            },
            "optional": {
                "feather": ("INT", {"default": 16, "min": 0, "max": 100}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("composite_image",)
    FUNCTION = "merge_tile"
    CATEGORY = "flow-assistor/tiling"

    def merge_tile(self, base_image, processed_tile, tile_data, feather=16):
        if not tile_data or "original_bbox" not in tile_data:
            print("[TileCompositor] Invalid tile_data. Returning base image.")
            return (base_image,)

        x, y, w, h = tile_data["original_bbox"]

        # Ensure device/dtype consistency
        base_device = base_image.device
        base_dtype = base_image.dtype
        processed_tile = processed_tile.to(device=base_device, dtype=base_dtype)

        # Resize processed tile back to original crop size if needed
        if int(processed_tile.shape[2]) != int(w) or int(processed_tile.shape[1]) != int(h):
            samples = processed_tile.movedim(-1, 1)  # [B, C, H, W]
            upscaled = comfy.utils.common_upscale(samples, int(w), int(h), "lanczos", "disabled")
            restored_tile = upscaled.movedim(1, -1)
        else:
            restored_tile = processed_tile

        output_image = base_image.clone()
        B, H, W, C = output_image.shape

        composite_mask = torch.zeros((B, H, W), dtype=torch.float32, device=base_device)
        composite_mask[:, y:y + h, x:x + w] = 1.0

        if feather > 0:
            m = composite_mask.unsqueeze(1)  # [B,1,H,W]
            k = int(feather) * 2 + 1
            m = F.avg_pool2d(m, kernel_size=k, stride=1, padding=int(feather))
            composite_mask = m.squeeze(1)

        bg_crop = output_image[:, y:y + h, x:x + w, :]
        mask_crop = composite_mask[:, y:y + h, x:x + w].unsqueeze(-1).to(dtype=base_dtype)

        merged_crop = restored_tile * mask_crop + bg_crop * (1.0 - mask_crop)
        output_image[:, y:y + h, x:x + w, :] = merged_crop

        return (output_image,)


NODE_CLASS_MAPPINGS = {
    "TileManager": TileManager,
    "TileCompositor": TileCompositor,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TileManager": "Tile Manager (Crop)",
    "TileCompositor": "Tile Compositor (Merge)",
}