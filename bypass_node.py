import sys

class AnyType(str):
    """A special type that compares equal to everything, allowing any connection."""
    def __ne__(self, __value: object) -> bool:
        return False

any_type = AnyType("*")

class BypassControl:
    """
    A 4-channel Sidecar Bypass Controller.
    
    - Connect a node to an input slot.
    - Toggle the switch.
    - OFF = Forces the connected node to BYPASS (Purple) mode.
    - ON = Sets the connected node to ALWAYS (Normal) mode.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                # --- Channel 1 ---
                "input_1": (any_type,),
                "label_1": ("STRING", {"default": "Group 1", "multiline": False}),
                "active_1": ("BOOLEAN", {"default": True, "label_on": "Active", "label_off": "BYPASS"}),

                # --- Channel 2 ---
                "input_2": (any_type,),
                "label_2": ("STRING", {"default": "Group 2", "multiline": False}),
                "active_2": ("BOOLEAN", {"default": True, "label_on": "Active", "label_off": "BYPASS"}),

                # --- Channel 3 ---
                "input_3": (any_type,),
                "label_3": ("STRING", {"default": "Group 3", "multiline": False}),
                "active_3": ("BOOLEAN", {"default": True, "label_on": "Active", "label_off": "BYPASS"}),

                # --- Channel 4 ---
                "input_4": (any_type,),
                "label_4": ("STRING", {"default": "Group 4", "multiline": False}),
                "active_4": ("BOOLEAN", {"default": True, "label_on": "Active", "label_off": "BYPASS"}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "process_logic"
    CATEGORY = "flow-assistor"
    
    # We mark this as an Output node so ComfyUI always considers it 'used'
    OUTPUT_NODE = True

    def process_logic(self, **kwargs):
        # The logic is handled purely in frontend JavaScript.
        # This python method is just a placeholder to keep the graph valid.
        return ()

NODE_CLASS_MAPPINGS = {
    "BypassControl": BypassControl,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BypassControl": "Flow Control (Sidecar Bypass)",
}