import torch

class ImageResolutionExtractorNode:
    """
    A node that extracts the resolution (Width/Height) from an input image
    and creates a matching empty latent.
    
    Unlike the 'Fit' node, this does not resize the image; it simply passes 
    the original image through and calculates dimensions from it.
    
    - Inputs: Image.
    - Outputs: Latent (empty, matching size), Width, Height, Image (Passthrough).
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("LATENT", "INT", "INT", "IMAGE")
    RETURN_NAMES = ("latent", "width", "height", "image")
    FUNCTION = "extract_resolution"
    CATEGORY = "flow-assistor"

    def extract_resolution(self, image):
        # Image shape is [Batch, Height, Width, Channels]
        batch_size = image.shape[0]
        height = image.shape[1]
        width = image.shape[2]
        
        # Create Empty Latent matching the input size
        # Latent dimensions are 1/8th of pixel dimensions.
        # We use standard floor division.
        latent_tensor = torch.zeros([batch_size, 4, height // 8, width // 8])

        return (
            {"samples": latent_tensor},
            width,
            height,
            image
        )

NODE_CLASS_MAPPINGS = {
    "ImageResolutionExtractorNode": ImageResolutionExtractorNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageResolutionExtractorNode": "Image Resolution Extractor",
}