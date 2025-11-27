import torch
import comfy.utils
import math

class ImageResolutionFitNode:
    """
    A node that fits an input image to a specific Megapixel count (MP) while strictly
    preserving the original aspect ratio.
    
    - Inputs: Image, MP Selection.
    - Outputs: Resized Image, Latent (matching size), Width, Height.
    
    The selection menu shows the 'Base' resolution (e.g., 1024x1024) for reference, 
    but the actual output will adjust dimensions to match the input image's shape.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        # The menu only shows the MP tier and the square reference size.
        # The logic will handle aspect ratio calculation automatically.
        resolutions = [
            "0.25 MP (Reference: 512x512)",
            "0.60 MP (Reference: 768x768)",
            "1.00 MP (Reference: 1024x1024)",
            "2.00 MP (Reference: 1408x1408)",
            "3.00 MP (Reference: 1728x1728)",
            "4.00 MP (Reference: 2048x2048)",
        ]

        return {
            "required": {
                "image": ("IMAGE",),
                "resolution_select": (resolutions, {"default": "1.00 MP (Reference: 1024x1024)"}),
            },
        }

    RETURN_TYPES = ("LATENT", "INT", "INT", "IMAGE")
    RETURN_NAMES = ("latent", "width", "height", "image")
    FUNCTION = "apply_resolution_fit"
    CATEGORY = "flow-assistor"

    def apply_resolution_fit(self, image, resolution_select):
        # 1. Get current image dimensions
        # Image shape is [Batch, Height, Width, Channels]
        input_h, input_w = image.shape[1], image.shape[2]
        
        # 2. Determine target pixel count from selection
        # We parse the "Reference: WxH" part to get the target total pixels
        try:
            # Extract "512x512" from "0.25 MP (Reference: 512x512)"
            ref_part = resolution_select.split("Reference: ")[1].split(")")[0]
            ref_w, ref_h = map(int, ref_part.split("x"))
            target_pixel_count = ref_w * ref_h
        except Exception as e:
            print(f"[ImageResolutionFitNode] Error parsing '{resolution_select}', defaulting to 1MP.")
            target_pixel_count = 1024 * 1024

        # 3. Calculate scaling factor to preserve aspect ratio
        # current_pixels = input_w * input_h
        # scale = sqrt(target_pixels / current_pixels)
        current_pixel_count = input_w * input_h
        if current_pixel_count == 0:
            scale_factor = 1.0
        else:
            scale_factor = math.sqrt(target_pixel_count / current_pixel_count)

        # 4. Calculate new dimensions & round to nearest 8 (for safe latent sizes)
        new_w = int(input_w * scale_factor)
        new_h = int(input_h * scale_factor)

        # Round to multiple of 8
        new_w = round(new_w / 8) * 8
        new_h = round(new_h / 8) * 8

        # Safety check to prevent 0 dimensions
        new_w = max(8, new_w)
        new_h = max(8, new_h)

        # 5. Resize Image (Lanczos)
        # comfy.utils.common_upscale expects [Batch, Channels, Height, Width] logic internally usually, 
        # but the wrapper handles (B,H,W,C) inputs by permuting if needed or we permute here.
        # Standard Comfy pattern:
        samples = image.movedim(-1, 1)  # [B, H, W, C] -> [B, C, H, W]
        resized_samples = comfy.utils.common_upscale(
            samples, new_w, new_h, "lanczos", "disabled"
        )
        resized_image = resized_samples.movedim(1, -1)  # [B, C, H, W] -> [B, H, W, C]

        # 6. Create Empty Latent matching the new size
        batch_size = image.shape[0]
        # Latent dimensions are 1/8th of pixel dimensions
        latent_tensor = torch.zeros([batch_size, 4, new_h // 8, new_w // 8])

        return (
            {"samples": latent_tensor},
            new_w,
            new_h,
            resized_image
        )

NODE_CLASS_MAPPINGS = {
    "ImageResolutionFitNode": ImageResolutionFitNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageResolutionFitNode": "Image Resolution Fit",
}