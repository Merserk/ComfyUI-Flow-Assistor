"""Camera-angle prompt-description node for ComfyUI V3."""

from comfy_api.latest import io
from ..categories import TEXT


def _rotation_to_text(rotation: float, precise: bool) -> str:
    if -10 < rotation < 10:
        text = "front view, looking at camera, symmetrical face"
    else:
        side = "right" if rotation > 0 else "left"
        absolute = abs(rotation)
        if absolute < 40:
            text = f"slight {side} angle, looking slightly away"
        elif absolute < 70:
            text = f"three-quarter view from {side}, 3/4 angle"
        elif absolute < 110:
            text = f"{side} side view, profile shot, from side"
        elif absolute < 160:
            text = f"view from behind {side}, looking away from camera, dorsal view"
        else:
            text = "back view, view from behind, from back"
    if precise and abs(rotation) > 0:
        text += f" (angle {rotation:.1f}°)"
    return text


def _vertical_to_text(vertical: float, precise: bool) -> str:
    if -10 < vertical < 10:
        text = "eye level shot"
    elif vertical >= 10:
        if vertical < 40:
            text = "slightly high angle, looking down"
        elif vertical < 80:
            text = "high angle, from above"
        else:
            text = "bird's eye view, overhead shot, top down view"
    elif vertical > -40:
        text = "slightly low angle, looking up"
    elif vertical > -80:
        text = "low angle, from below"
    else:
        text = "worm's eye view, ground level shot, extreme low angle"
    if precise and abs(vertical) > 0:
        text += f" (vertical angle {vertical:.1f})"
    return text


def _depth_to_text(depth: float, precise: bool) -> str:
    if -10 < depth < 10:
        text = "medium shot, mid shot"
    elif depth >= 10:
        if depth < 40:
            text = "close-up shot"
        elif depth < 75:
            text = "extreme close-up, face focus"
        else:
            text = "macro photography, extreme detail"
    elif depth > -40:
        text = "medium full shot, knees up"
    elif depth > -75:
        text = "full body shot, wide shot"
    else:
        text = "extreme wide shot, distant view, establishing shot"
    if precise and abs(depth) > 0:
        text += f" (zoom level {depth:.1f})"
    return text


def _focal_length_to_text(focal: float, precise: bool) -> str:
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
    if precise:
        text += f" ({focal:.1f}mm)"
    return text


class CameraAngleControl(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        number = io.NumberDisplay.number
        return io.Schema(
            node_id="CameraAngleControl",
            display_name="Camera Angle Control",
            category=TEXT,
            description="Generates camera viewpoint, elevation, distance, and lens prompt text.",
            inputs=[
                io.Boolean.Input(
                    "precise_mode",
                    default=True,
                    tooltip="Include exact numbers alongside viewpoint keywords.",
                ),
                io.Boolean.Input("enable_rotation", default=False, optional=True),
                io.Float.Input("rotation_value", default=0.0, min=-180.0, max=180.0, step=5.0, display_mode=number, optional=True),
                io.Boolean.Input("enable_vertical", default=False, optional=True),
                io.Float.Input("vertical_value", default=0.0, min=-100.0, max=100.0, step=5.0, display_mode=number, optional=True),
                io.Boolean.Input("enable_depth", default=False, optional=True),
                io.Float.Input("depth_value", default=0.0, min=-100.0, max=100.0, step=5.0, display_mode=number, optional=True),
                io.Boolean.Input("enable_focal_length", default=False, optional=True),
                io.Float.Input("focal_length_value", default=50.0, min=0.0, max=600.0, step=5.0, display_mode=number, optional=True),
            ],
            outputs=[io.String.Output(display_name="camera_description")],
        )

    @classmethod
    def execute(
        cls,
        precise_mode=True,
        enable_rotation=False,
        rotation_value=0.0,
        enable_vertical=False,
        vertical_value=0.0,
        enable_depth=False,
        depth_value=0.0,
        enable_focal_length=False,
        focal_length_value=50.0,
    ) -> io.NodeOutput:
        parts: list[str] = []
        if enable_rotation:
            parts.append(_rotation_to_text(float(rotation_value), bool(precise_mode)))
        if enable_vertical:
            parts.append(_vertical_to_text(float(vertical_value), bool(precise_mode)))
        if enable_depth:
            parts.append(_depth_to_text(float(depth_value), bool(precise_mode)))
        if enable_focal_length:
            parts.append(_focal_length_to_text(float(focal_length_value), bool(precise_mode)))
        return io.NodeOutput(", ".join(parts))


__all__ = ["CameraAngleControl"]
