import torch
import torch.nn.functional as F

class MultiplicationNode:
    """
    A mathematical node that takes two integer inputs (like Width and Height) 
    and an optional Latent, multiplies/scales them by a factor, and outputs the results.
    
    - Inputs: Multiplier (Float), Value 1 (Int), Value 2 (Int), Latent (Optional).
    - Outputs: Result 1 (Int), Result 2 (Int), Resized Latent.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # The multiplication factor (e.g., 2.0 = double)
                "multiplier": ("FLOAT", {"default": 2.0, "step": 0.1, "min": 0.1, "max": 100.0}),
            },
            "optional": {
                # ForceInput=True removes the widget box and requires a connection
                "value_1": ("INT", {"default": 0, "min": 0, "max": 9999999, "forceInput": True}),
                "value_2": ("INT", {"default": 0, "min": 0, "max": 9999999, "forceInput": True}),
                "samples": ("LATENT",),
            }
        }

    RETURN_TYPES = ("INT", "INT", "LATENT")
    RETURN_NAMES = ("result_1", "result_2", "latent")
    FUNCTION = "apply_multiplication"
    CATEGORY = "flow-assistor"

    def apply_multiplication(self, multiplier, value_1=0, value_2=0, samples=None):
        # 1. Calculate Integer Outputs
        out_1 = int(round(value_1 * multiplier))
        out_2 = int(round(value_2 * multiplier))
        
        # 2. Calculate Latent Output
        out_latent = None
        
        if samples is not None:
            # Clone the dictionary so we don't modify the original
            lat = samples.copy()
            s = lat["samples"] # Shape is [Batch, 4, Height, Width]
            
            # Calculate new dimensions
            # Latent height/width are 1/8th of pixel height/width
            current_h, current_w = s.shape[2], s.shape[3]
            new_h = int(round(current_h * multiplier))
            new_w = int(round(current_w * multiplier))
            
            # Upscale using bilinear interpolation (standard for latents)
            if new_h > 0 and new_w > 0:
                upscaled = F.interpolate(
                    s, size=(new_h, new_w), mode="bilinear", align_corners=False
                )
                lat["samples"] = upscaled
                out_latent = lat
            else:
                out_latent = samples # Fallback if dimensions result in 0
        
        # If no latent was connected, return an empty dummy latent 
        # to prevent crashes if the output slot is connected blindly
        if out_latent is None:
            # Create a 1x1 dummy latent
            out_latent = {"samples": torch.zeros((1, 4, 1, 1))}

        return (out_1, out_2, out_latent)

# Registration
NODE_CLASS_MAPPINGS = {
    "MultiplicationNode": MultiplicationNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MultiplicationNode": "Multiplication (Dual & Latent)",
}