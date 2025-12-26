import torch

# Special AnyType to allow any connection
class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False

any_type = AnyType("*")

class OutputAnyDebugDataNode:
    """
    A debug node that accepts ANY input and analyzes it.
    - If IMAGE: Shows resolution (WxH), Aspect Ratio, and Batch Size.
    - If LATENT: Shows Latent Dimensions and equivalent Pixel Resolution (8x).
    - If other: Shows Type and raw string representation.
    
    The result is displayed as text on the node itself (via JS) and output as a string.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "any_input": (any_type,),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("debug_text",)
    FUNCTION = "analyze_data"
    CATEGORY = "flow-assistor/debug"
    OUTPUT_NODE = True

    def analyze_data(self, any_input, unique_id=None, extra_pnginfo=None):
        text_output = "None"
        
        try:
            # 1. Handle Torch Tensors (Images, Masks, Raw Latents)
            if isinstance(any_input, torch.Tensor):
                shape = any_input.shape
                # Basic info
                text_output = f"Type: Tensor\nShape: {list(shape)}\nDtype: {any_input.dtype}\nDevice: {any_input.device}\n"
                
                # Heuristic for IMAGE: [Batch, Height, Width, Channels]
                if any_input.ndim == 4:
                    # Standard Image: Channels at end (usually 3 or 4)
                    if shape[3] <= 4 and shape[1] > 8 and shape[2] > 8:
                        b, h, w, c = shape
                        ar = w / h if h > 0 else 0
                        text_output += f"\n--- IMAGE DETECTED ---\n"
                        text_output += f"Resolution: {w}x{h}\n"
                        text_output += f"Aspect Ratio: {ar:.2f}\n"
                        text_output += f"Batch Size: {b}\n"
                        text_output += f"Channels: {c}"
                    
                    # Raw Latent / NCHW: Channels at dim 1
                    elif shape[1] <= 4 and shape[2] > 8 and shape[3] > 8:
                        b, c, h, w = shape
                        text_output += f"\n--- RAW LATENT/NCHW ---\n"
                        text_output += f"Latent Size: {w}x{h}\n"
                        text_output += f"Pixel Res (~8x): {w*8}x{h*8}\n"
                        text_output += f"Batch Size: {b}"

                # Heuristic for MASK: [Batch, Height, Width]
                elif any_input.ndim == 3:
                     b, h, w = shape
                     text_output += f"\n--- MASK DETECTED ---\n"
                     text_output += f"Resolution: {w}x{h}\n"
                     text_output += f"Batch Size: {b}"

            # 2. Handle Latent Dictionary (Standard ComfyUI Latent Wrapper)
            elif isinstance(any_input, dict) and "samples" in any_input:
                samples = any_input["samples"]
                if isinstance(samples, torch.Tensor):
                    # Shape: [Batch, 4, Height, Width]
                    shape = samples.shape
                    b, c, h, w = shape
                    ar = w / h if h > 0 else 0
                    
                    text_output = f"Type: LATENT (Dict)\nShape: {list(shape)}\n"
                    text_output += f"\n--- RESOLUTION INFO ---\n"
                    text_output += f"Latent Size: {w}x{h}\n"
                    text_output += f"Pixel Res (8x): {w*8}x{h*8}\n"
                    text_output += f"Aspect Ratio: {ar:.2f}\n"
                    text_output += f"Batch Size: {b}"
                else:
                    text_output = f"Type: LATENT (Dict)\nError: 'samples' is not a tensor."

            # 3. Handle Lists
            elif isinstance(any_input, list):
                text_output = f"Type: List\nLength: {len(any_input)}\n"
                if len(any_input) > 0:
                    text_output += f"Sample[0]: {str(any_input[0])[:50]}..."

            # 4. Handle Basic Types
            elif isinstance(any_input, (int, float, bool, str)):
                 text_output = f"Type: {type(any_input).__name__}\nValue: {any_input}"
            
            # 5. Generic Fallback
            else:
                raw_str = str(any_input)
                text_output = f"Type: {type(any_input)}\n"
                text_output += f"Value: {raw_str[:200]}..." if len(raw_str) > 0 else "Empty"

        except Exception as e:
            text_output = f"Error analyzing data: {str(e)}"

        # Return: {"ui": {KEY: [LIST]}, "result": (TUPLE)}
        return {"ui": {"text": [text_output]}, "result": (text_output,)}

NODE_CLASS_MAPPINGS = {
    "OutputAnyDebugDataNode": OutputAnyDebugDataNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OutputAnyDebugDataNode": "Debug Data (Any Input)",
}