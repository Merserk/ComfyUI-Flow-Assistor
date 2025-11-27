import torch

class ResolutionSelectNode:
    """
    Resolution Selector (Groups).
    Layout: Resolution Dropdown -> Enable Switch.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        
        # --- DATA LISTS ---
        res_025 = [
            "512x512 (1:1)", "576x432 (4:3)", "432x576 (3:4)", "624x416 (3:2)", 
            "416x624 (2:3)", "680x384 (16:9)", "384x680 (9:16)", "784x336 (21:9)", "336x784 (9:21)"
        ]
        res_06 = [
            "768x768 (1:1)", "896x672 (4:3)", "672x896 (3:4)", "936x624 (3:2)", 
            "624x936 (2:3)", "1024x576 (16:9)", "576x1024 (9:16)", "1176x504 (21:9)", "504x1176 (9:21)"
        ]
        res_1 = [
            "1024x1024 (1:1)", "1152x864 (4:3)", "864x1152 (3:4)", "1216x832 (3:2)", 
            "832x1216 (2:3)", "1344x768 (16:9)", "768x1344 (9:16)", "1536x640 (21:9)", "640x1536 (9:21)"
        ]
        res_2 = [
            "1408x1408 (1:1)", "1632x1216 (4:3)", "1216x1632 (3:4)", "1728x1152 (3:2)", 
            "1152x1728 (2:3)", "1920x1080 (16:9)", "1080x1920 (9:16)", "2176x928 (21:9)", "928x2176 (9:21)"
        ]
        res_3 = [
            "1728x1728 (1:1)", "2000x1496 (4:3)", "1496x2000 (3:4)", "2112x1408 (3:2)", 
            "1408x2112 (2:3)", "2304x1296 (16:9)", "1296x2304 (9:16)", "2640x1136 (21:9)", "1136x2640 (9:21)"
        ]
        res_4 = [
            "2048x2048 (1:1)", "2304x1728 (4:3)", "1728x2304 (3:4)", "2448x1632 (3:2)", 
            "1632x2448 (2:3)", "2688x1512 (16:9)", "1512x2688 (9:16)", "3072x1312 (21:9)", "1312x3072 (9:21)"
        ]

        return {
            "required": {
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 64}),
                
                # We swap the order here:
                # 1. Dropdown
                # 2. Boolean Switch (using custom labels to indicate it controls the above)
                
                # --- 0.25MP ---
                "res_025mp": (res_025, {"default": "512x512 (1:1)"}),
                "use_025mp": ("BOOLEAN", {"default": False, "label_on": "Active (0.25MP)", "label_off": "Inactive"}),

                # --- 0.6MP ---
                "res_06mp": (res_06, {"default": "768x768 (1:1)"}),
                "use_06mp": ("BOOLEAN", {"default": False, "label_on": "Active (0.6MP)", "label_off": "Inactive"}),

                # --- 1MP (Default) ---
                "res_1mp": (res_1, {"default": "1024x1024 (1:1)"}),
                "use_1mp": ("BOOLEAN", {"default": True, "label_on": "Active (1MP)", "label_off": "Inactive"}),

                # --- 2MP ---
                "res_2mp": (res_2, {"default": "1408x1408 (1:1)"}),
                "use_2mp": ("BOOLEAN", {"default": False, "label_on": "Active (2MP)", "label_off": "Inactive"}),

                # --- 3MP ---
                "res_3mp": (res_3, {"default": "1728x1728 (1:1)"}),
                "use_3mp": ("BOOLEAN", {"default": False, "label_on": "Active (3MP)", "label_off": "Inactive"}),

                # --- 4MP ---
                "res_4mp": (res_4, {"default": "2048x2048 (1:1)"}),
                "use_4mp": ("BOOLEAN", {"default": False, "label_on": "Active (4MP)", "label_off": "Inactive"}),
            },
        }

    RETURN_TYPES = ("LATENT", "INT", "INT")
    RETURN_NAMES = ("latent", "width", "height")
    FUNCTION = "generate_empty_latent"
    CATEGORY = "flow-assistor"

    def generate_empty_latent(
        self, batch_size, 
        res_025mp, use_025mp,
        res_06mp, use_06mp,
        res_1mp, use_1mp,
        res_2mp, use_2mp,
        res_3mp, use_3mp,
        res_4mp, use_4mp
    ):
        # Priority Logic: Check top to bottom.
        selected_res_string = "1024x1024" # Safe default

        if use_025mp:
            selected_res_string = res_025mp
        elif use_06mp:
            selected_res_string = res_06mp
        elif use_1mp:
            selected_res_string = res_1mp
        elif use_2mp:
            selected_res_string = res_2mp
        elif use_3mp:
            selected_res_string = res_3mp
        elif use_4mp:
            selected_res_string = res_4mp
        else:
            # If nothing active, default to 1MP input
            selected_res_string = res_1mp

        # Parse the string
        try:
            # "1024x1024 (1:1)" -> "1024x1024"
            dim_part = selected_res_string.split(" ")[0]
            w_str, h_str = dim_part.split("x")
            width = int(w_str)
            height = int(h_str)
        except:
            width = 1024
            height = 1024

        latent = torch.zeros([batch_size, 4, height // 8, width // 8])
        return ({"samples": latent}, width, height)

NODE_CLASS_MAPPINGS = {
    "ResolutionSelectNode": ResolutionSelectNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ResolutionSelectNode": "Resolution Selector (Groups)",
}