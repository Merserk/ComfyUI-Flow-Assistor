import comfy.model_management as mm
import gc
import torch

# This special class makes the node accept any link and connect to any input
# by tricking the validator into thinking the types always match.
class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False

# Create a single instance to use everywhere
any_type = AnyType("*")

class VRAMRAMCleanerNode:
    """
    A node to manage VRAM/RAM usage during workflow execution.
    It passes the input through unchanged but performs cleanup operations based on the selected mode.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # Use any_type instead of the string "*"
                "any_model": (any_type,), 
                "mode": (["Current", "Others", "All"], {"default": "Current"}),
            },
        }

    # Return the special any_type so it can connect to VAE, CLIP, MODEL, etc.
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("any_model",)
    FUNCTION = "clean_vram"
    CATEGORY = "flow-assistor"

    def clean_vram(self, any_model, mode):
        
        # Helper to force garbage collection for RAM
        def free_ram():
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()

        try:
            if mode == "All":
                # Unload everything
                mm.unload_all_models()
                mm.soft_empty_cache()
                free_ram()

            elif mode == "Current":
                # Attempt to unload the specific model passed in
                # comfy.model_management.unload_model_cloned handles ModelPatcher objects
                mm.unload_model_cloned(any_model)
                mm.soft_empty_cache()
                free_ram()

            elif mode == "Others":
                # Unload everything FIRST
                mm.unload_all_models()
                mm.soft_empty_cache()
                free_ram()
                
                # Then try to load the passed model back to GPU immediately
                try:
                    mm.load_models_gpu([any_model])
                except Exception as e:
                    # Some objects (like simple VAEs) might not need explicit loading or differ in API
                    # We log but don't crash, as the model is still in RAM
                    print(f"[VRAM Cleaner] Note: Could not force load model to GPU (might be already loaded or handled differently): {e}")

        except Exception as e:
            print(f"[VRAM Cleaner] Error during cleanup: {e}")

        # Always pass the data forward unchanged
        return (any_model,)

# Registration
NODE_CLASS_MAPPINGS = {
    "VRAMRAMCleanerNode": VRAMRAMCleanerNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VRAMRAMCleanerNode": "VRAM/RAM Cleaner",
}