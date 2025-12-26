# ComfyUI custom node: Camera Angle Control
# Place this file in: ComfyUI/custom_nodes/comfyui-camera-angle-control/camera_angle_control_node.py

from typing import Tuple

class CameraAngleControl:
    """
    A node that generates camera angle descriptions for image generation prompts.
    
    FEATURES:
    - Precise Mode: Appends exact degree values for fine-tuning.
    - Strong Keywords: Uses photography terms (Profile, High Angle) to prevent AI from confusing rotation with image flipping.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "precise_mode": ("BOOLEAN", {"default": True, "tooltip": "Include exact numbers (e.g. '77°') alongside keywords."}),
            },
            "optional": {
                # Camera Rotation (Horizontal Pan)
                "enable_rotation": ("BOOLEAN", {"default": False}),
                "rotation_value": ("FLOAT", {
                    "default": 0.0,
                    "min": -180.0,
                    "max": 180.0,
                    "step": 5.0,
                    "display": "number", # 0=Front, 90=Right, 180=Back, -90=Left
                }),
                
                # Camera Vertical Movement (Elevation)
                "enable_vertical": ("BOOLEAN", {"default": False}),
                "vertical_value": ("FLOAT", {
                    "default": 0.0,
                    "min": -100.0,
                    "max": 100.0,
                    "step": 5.0,
                    "display": "number", # >0 = High Angle, <0 = Low Angle
                }),
                
                # Camera Depth Movement (Zoom/Distance)
                "enable_depth": ("BOOLEAN", {"default": False}),
                "depth_value": ("FLOAT", {
                    "default": 0.0,
                    "min": -100.0,
                    "max": 100.0,
                    "step": 5.0,
                    "display": "number", # >0 = Close, <0 = Far
                }),
                
                # Focal Length
                "enable_focal_length": ("BOOLEAN", {"default": False}),
                "focal_length_value": ("FLOAT", {
                    "default": 50.0,
                    "min": 0.0,
                    "max": 600.0,
                    "step": 5.0,
                    "display": "number",
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("camera_description",)
    FUNCTION = "generate_camera_description"
    CATEGORY = "flow-assistor"

    def _rotation_to_text(self, rotation: float, precise: bool) -> str:
        """
        Maps degrees to strong viewpoint keywords + optional precise degrees.
        """
        text = ""
        # Handle the center
        if -10 < rotation < 10:
            text = "front view, looking at camera, symmetrical face"
        else:
            # Determine Left vs Right
            side = "right" if rotation > 0 else "left"
            abs_rot = abs(rotation)

            # Map ranges to keywords
            if 10 <= abs_rot < 40:
                text = f"slight {side} angle, looking slightly away"
            elif 40 <= abs_rot < 70:
                text = f"three-quarter view from {side}, 3/4 angle"
            elif 70 <= abs_rot < 110:
                text = f"{side} side view, profile shot, from side"
            elif 110 <= abs_rot < 160:
                text = f"view from behind {side}, looking away from camera, dorsal view"
            else:
                text = "back view, view from behind, from back"

        if precise and abs(rotation) > 0:
            text += f" (angle {rotation:.1f}°)"
            
        return text

    def _vertical_to_text(self, vertical: float, precise: bool) -> str:
        """
        Maps -100 to 100 to vertical camera angles.
        """
        text = ""
        if -10 < vertical < 10:
            text = "eye level shot"
        
        elif vertical >= 10:
            if vertical < 40:
                text = "slightly high angle, looking down"
            elif vertical < 80:
                text = "high angle, from above"
            else:
                text = "bird's eye view, overhead shot, top down view"
        
        else: # vertical <= -10
            if vertical > -40:
                text = "slightly low angle, looking up"
            elif vertical > -80:
                text = "low angle, from below"
            else:
                text = "worm's eye view, ground level shot, extreme low angle"

        if precise and abs(vertical) > 0:
            text += f" (vertical angle {vertical:.1f})"

        return text

    def _depth_to_text(self, depth: float, precise: bool) -> str:
        """
        Maps -100 to 100 to shot framing/distance.
        """
        text = ""
        if -10 < depth < 10:
            text = "medium shot, mid shot"
        
        elif depth >= 10:
            if depth < 40:
                text = "close-up shot"
            elif depth < 75:
                text = "extreme close-up, face focus"
            else:
                text = "macro photography, extreme detail"
        
        else: # depth <= -10
            if depth > -40:
                text = "medium full shot, knees up"
            elif depth > -75:
                text = "full body shot, wide shot"
            else:
                text = "extreme wide shot, distant view, establishing shot"

        if precise and abs(depth) > 0:
            text += f" (zoom level {depth:.1f})"

        return text

    def _focal_length_to_text(self, focal: float, precise: bool) -> str:
        """
        Maps mm to lens characteristics.
        """
        text = ""
        if focal < 20:
            text = "fisheye lens, distorted perspective"
        elif focal < 35:
            text = "wide angle lens, expanded background"
        elif focal < 70:
            text = "standard lens, natural perspective"
        elif focal < 110:
            text = "portrait photography, shallow depth of field"
        elif focal < 300:
            text = "telephoto lens, compressed perspective, bokeh"
        else:
            text = "super telephoto lens, extreme compression, blurred background"
            
        # Precise always adds the mm for focal length as it is standard terminology
        if precise:
            text += f" ({focal:.1f}mm)"
        else:
            # Even in non-precise mode, adding mm is usually helpful for lens logic, 
            # but we respect the toggle if user wants pure keywords.
            pass
            
        return text

    def generate_camera_description(
        self,
        precise_mode: bool = True,
        enable_rotation: bool = False,
        rotation_value: float = 0.0,
        enable_vertical: bool = False,
        vertical_value: float = 0.0,
        enable_depth: bool = False,
        depth_value: float = 0.0,
        enable_focal_length: bool = False,
        focal_length_value: float = 50.0,
    ) -> Tuple[str]:
        
        parts = []
        
        # 1. Rotation
        if enable_rotation:
            parts.append(self._rotation_to_text(rotation_value, precise_mode))
        
        # 2. Vertical
        if enable_vertical:
            parts.append(self._vertical_to_text(vertical_value, precise_mode))
        
        # 3. Depth
        if enable_depth:
            parts.append(self._depth_to_text(depth_value, precise_mode))
        
        # 4. Focal Length
        if enable_focal_length:
            parts.append(self._focal_length_to_text(focal_length_value, precise_mode))
        
        final_text = ", ".join(parts)
        
        return (final_text,)


# Required mappings so ComfyUI can discover the node
NODE_CLASS_MAPPINGS = {
    "CameraAngleControl": CameraAngleControl,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CameraAngleControl": "Camera Angle Control",
}