import torch

class ImageLatentResolutionExtractorNode:
    """
    A utility node that takes a LATENT (samples) as input and extracts its 
    corresponding pixel resolution (Width and Height).
    
    Standard Stable Diffusion latents are 1/8th the size of the pixel image.
    This node calculates: Pixel Size = Latent Size * 8.
    
    - Input: samples (Latent)
    - Outputs: Latent (Passthrough), Width (Int), Height (Int)
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "samples": ("LATENT",),
            },
        }

    RETURN_TYPES = ("LATENT", "INT", "INT")
    RETURN_NAMES = ("latent", "width", "height")
    FUNCTION = "extract_resolution"
    CATEGORY = "flow-assistor"

    def extract_resolution(self, samples):
        # samples is a dictionary: {'samples': Tensor[Batch, Channels, Height, Width]}
        latent_tensor = samples["samples"]
        
        # Get dimensions from the tensor
        # Shape is [Batch, Channels, H, W]
        l_height = latent_tensor.shape[2]
        l_width = latent_tensor.shape[3]
        
        # Convert to pixel dimensions (Standard SD factor is 8)
        # We assume square pixels
        pixel_width = int(l_width * 8)
        pixel_height = int(l_height * 8)

        return (
            samples,      # Pass the latent through unchanged
            pixel_width,
            pixel_height
        )

# Node Registration
NODE_CLASS_MAPPINGS = {
    "ImageLatentResolutionExtractorNode": ImageLatentResolutionExtractorNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageLatentResolutionExtractorNode": "Image Latent Resolution Extractor",
}