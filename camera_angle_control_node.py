# ComfyUI custom node: Camera Angle Control
# Place this file in: ComfyUI/custom_nodes/comfyui-camera-angle-control/camera_angle_control_node.py

from typing import Tuple

class CameraAngleControl:
    """
    A node that generates camera angle descriptions for image generation prompts.
    - Outputs text descriptions of camera rotation, position, and focal length.
    - Connect the output to a text encoder or combine with other prompts.
    - Text inputs with arrow/scroll controls move in steps of 5, but allow any precise value.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                # Camera Rotation (horizontal pan)
                "enable_rotation": ("BOOLEAN", {"default": False}),
                "rotation_value": ("FLOAT", {
                    "default": 0.0,
                    "min": -180.0,
                    "max": 180.0,
                    "step": 5.0,
                    "display": "number",
                }),
                
                # Camera Vertical Movement
                "enable_vertical": ("BOOLEAN", {"default": False}),
                "vertical_value": ("FLOAT", {
                    "default": 0.0,
                    "min": -100.0,
                    "max": 100.0,
                    "step": 5.0,
                    "display": "number",
                }),
                
                # Camera Depth Movement (forward/backward)
                "enable_depth": ("BOOLEAN", {"default": False}),
                "depth_value": ("FLOAT", {
                    "default": 0.0,
                    "min": -100.0,
                    "max": 100.0,
                    "step": 5.0,
                    "display": "number",
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
                
                # Output format
                "output_format": (["natural", "technical", "keywords"], {"default": "natural"}),
                
                # Optional prefix/suffix
                "prefix": ("STRING", {
                    "multiline": False,
                    "default": "",
                }),
                "suffix": ("STRING", {
                    "multiline": False,
                    "default": "",
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("camera_description",)
    FUNCTION = "generate_camera_description"
    CATEGORY = "flow-assistor"

    def _rotation_to_text(self, rotation: float, format_type: str) -> str:
        """Convert rotation value to descriptive text."""
        if format_type == "technical":
            return f"rotation {rotation:.1f}°"
        elif format_type == "keywords":
            if rotation == 0:
                return "front view"
            elif rotation > 0:
                if rotation <= 45:
                    return "slight right angle"
                elif rotation <= 90:
                    return "right side view"
                elif rotation <= 135:
                    return "right back angle"
                else:
                    return "rear view"
            else:  # rotation < 0
                if rotation >= -45:
                    return "slight left angle"
                elif rotation >= -90:
                    return "left side view"
                elif rotation >= -135:
                    return "left back angle"
                else:
                    return "rear view"
        else:  # natural
            if rotation == 0:
                return "camera facing forward"
            elif rotation > 0:
                if rotation <= 30:
                    return f"camera rotated slightly to the right ({rotation:.1f}°)"
                elif rotation <= 90:
                    return f"camera rotated to the right side ({rotation:.1f}°)"
                elif rotation <= 150:
                    return f"camera rotated to the right rear ({rotation:.1f}°)"
                else:
                    return f"camera facing backward ({rotation:.1f}°)"
            else:
                rotation_abs = abs(rotation)
                if rotation_abs <= 30:
                    return f"camera rotated slightly to the left ({rotation_abs:.1f}°)"
                elif rotation_abs <= 90:
                    return f"camera rotated to the left side ({rotation_abs:.1f}°)"
                elif rotation_abs <= 150:
                    return f"camera rotated to the left rear ({rotation_abs:.1f}°)"
                else:
                    return f"camera facing backward ({rotation_abs:.1f}°)"

    def _vertical_to_text(self, vertical: float, format_type: str) -> str:
        """Convert vertical position to descriptive text."""
        if format_type == "technical":
            direction = "up" if vertical > 0 else "down"
            return f"vertical {direction} {abs(vertical):.1f}"
        elif format_type == "keywords":
            if vertical == 0:
                return "eye level"
            elif vertical > 0:
                if vertical <= 30:
                    return "slightly high angle"
                elif vertical <= 70:
                    return "high angle"
                else:
                    return "bird's eye view"
            else:
                vertical_abs = abs(vertical)
                if vertical_abs <= 30:
                    return "slightly low angle"
                elif vertical_abs <= 70:
                    return "low angle"
                else:
                    return "worm's eye view"
        else:  # natural
            if vertical == 0:
                return "camera at eye level"
            elif vertical > 0:
                if vertical <= 20:
                    return f"camera slightly above ({vertical:.1f})"
                elif vertical <= 50:
                    return f"camera raised high angle ({vertical:.1f})"
                else:
                    return f"camera from above, bird's eye view ({vertical:.1f})"
            else:
                vertical_abs = abs(vertical)
                if vertical_abs <= 20:
                    return f"camera slightly below ({vertical_abs:.1f})"
                elif vertical_abs <= 50:
                    return f"camera lowered low angle ({vertical_abs:.1f})"
                else:
                    return f"camera from below, worm's eye view ({vertical_abs:.1f})"

    def _depth_to_text(self, depth: float, format_type: str) -> str:
        """Convert depth/distance to descriptive text."""
        if format_type == "technical":
            direction = "forward" if depth > 0 else "backward"
            return f"depth {direction} {abs(depth):.1f}"
        elif format_type == "keywords":
            if depth == 0:
                return "medium shot"
            elif depth > 0:
                if depth <= 30:
                    return "close-up"
                elif depth <= 70:
                    return "extreme close-up"
                else:
                    return "macro shot"
            else:
                depth_abs = abs(depth)
                if depth_abs <= 30:
                    return "medium wide shot"
                elif depth_abs <= 70:
                    return "wide shot"
                else:
                    return "extreme wide shot"
        else:  # natural
            if depth == 0:
                return "camera at normal distance"
            elif depth > 0:
                if depth <= 25:
                    return f"camera moved closer ({depth:.1f})"
                elif depth <= 60:
                    return f"camera very close, close-up ({depth:.1f})"
                else:
                    return f"camera extremely close, macro ({depth:.1f})"
            else:
                depth_abs = abs(depth)
                if depth_abs <= 25:
                    return f"camera pulled back ({depth_abs:.1f})"
                elif depth_abs <= 60:
                    return f"camera far back, wide shot ({depth_abs:.1f})"
                else:
                    return f"camera very far back, extreme wide ({depth_abs:.1f})"

    def _focal_length_to_text(self, focal: float, format_type: str) -> str:
        """Convert focal length to descriptive text."""
        if format_type == "technical":
            return f"{focal:.1f}mm lens"
        elif format_type == "keywords":
            if focal < 24:
                return "ultra wide lens"
            elif focal < 35:
                return "wide angle lens"
            elif focal < 70:
                return "standard lens"
            elif focal < 135:
                return "portrait lens"
            elif focal < 300:
                return "telephoto lens"
            else:
                return "super telephoto lens"
        else:  # natural
            if focal < 24:
                return f"ultra wide angle {focal:.1f}mm lens with distortion"
            elif focal < 35:
                return f"wide angle {focal:.1f}mm lens"
            elif focal < 70:
                return f"standard {focal:.1f}mm lens, natural perspective"
            elif focal < 135:
                return f"{focal:.1f}mm portrait lens with compression"
            elif focal < 300:
                return f"{focal:.1f}mm telephoto lens with strong compression"
            else:
                return f"{focal:.1f}mm super telephoto lens, extreme compression"

    def generate_camera_description(
        self,
        enable_rotation: bool = False,
        rotation_value: float = 0.0,
        enable_vertical: bool = False,
        vertical_value: float = 0.0,
        enable_depth: bool = False,
        depth_value: float = 0.0,
        enable_focal_length: bool = False,
        focal_length_value: float = 50.0,
        output_format: str = "natural",
        prefix: str = "",
        suffix: str = "",
    ) -> Tuple[str]:
        
        parts = []
        
        # Build description based on enabled settings
        if enable_rotation:
            parts.append(self._rotation_to_text(rotation_value, output_format))
        
        if enable_vertical:
            parts.append(self._vertical_to_text(vertical_value, output_format))
        
        if enable_depth:
            parts.append(self._depth_to_text(depth_value, output_format))
        
        if enable_focal_length:
            parts.append(self._focal_length_to_text(focal_length_value, output_format))
        
        # Combine parts based on format
        if output_format == "keywords":
            description = ", ".join(parts)
        else:
            description = ", ".join(parts)
        
        # Add prefix and suffix if provided
        result_parts = []
        if prefix.strip():
            result_parts.append(prefix.strip())
        if description:
            result_parts.append(description)
        if suffix.strip():
            result_parts.append(suffix.strip())
        
        # Join with appropriate separator
        if output_format == "keywords":
            final_text = ", ".join(result_parts)
        else:
            final_text = ", ".join(result_parts)
        
        return (final_text,)


# Required mappings so ComfyUI can discover the node
NODE_CLASS_MAPPINGS = {
    "CameraAngleControl": CameraAngleControl,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CameraAngleControl": "Camera Angle Control",
}