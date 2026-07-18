"""Grouped resolution selector for ComfyUI V3."""

import torch
from comfy_api.latest import io
from ..categories import IMAGE


RESOLUTIONS = {
    "025mp": [
        "512x512 (1:1)", "576x432 (4:3)", "432x576 (3:4)", "624x416 (3:2)",
        "416x624 (2:3)", "680x384 (16:9)", "384x680 (9:16)", "784x336 (21:9)", "336x784 (9:21)",
    ],
    "06mp": [
        "768x768 (1:1)", "896x672 (4:3)", "672x896 (3:4)", "936x624 (3:2)",
        "624x936 (2:3)", "1024x576 (16:9)", "576x1024 (9:16)", "1176x504 (21:9)", "504x1176 (9:21)",
    ],
    "1mp": [
        "1024x1024 (1:1)", "1152x864 (4:3)", "864x1152 (3:4)", "1216x832 (3:2)",
        "832x1216 (2:3)", "1344x768 (16:9)", "768x1344 (9:16)", "1536x640 (21:9)", "640x1536 (9:21)",
    ],
    "2mp": [
        "1408x1408 (1:1)", "1632x1216 (4:3)", "1216x1632 (3:4)", "1728x1152 (3:2)",
        "1152x1728 (2:3)", "1920x1080 (16:9)", "1080x1920 (9:16)", "2176x928 (21:9)", "928x2176 (9:21)",
    ],
    "3mp": [
        "1728x1728 (1:1)", "2000x1496 (4:3)", "1496x2000 (3:4)", "2112x1408 (3:2)",
        "1408x2112 (2:3)", "2304x1296 (16:9)", "1296x2304 (9:16)", "2640x1136 (21:9)", "1136x2640 (9:21)",
    ],
    "4mp": [
        "2048x2048 (1:1)", "2304x1728 (4:3)", "1728x2304 (3:4)", "2448x1632 (3:2)",
        "1632x2448 (2:3)", "2688x1512 (16:9)", "1512x2688 (9:16)", "3072x1312 (21:9)", "1312x3072 (9:21)",
    ],
}


class ResolutionSelectNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ResolutionSelectNode",
            display_name="Resolution Selector (Groups)",
            category=IMAGE,
            inputs=[
                io.Combo.Input("res_025mp", options=RESOLUTIONS["025mp"], default="512x512 (1:1)"),
                io.Boolean.Input("use_025mp", default=False, label_on="Active (0.25MP)", label_off="Inactive"),
                io.Combo.Input("res_06mp", options=RESOLUTIONS["06mp"], default="768x768 (1:1)"),
                io.Boolean.Input("use_06mp", default=False, label_on="Active (0.6MP)", label_off="Inactive"),
                io.Combo.Input("res_1mp", options=RESOLUTIONS["1mp"], default="1024x1024 (1:1)"),
                io.Boolean.Input("use_1mp", default=True, label_on="Active (1MP)", label_off="Inactive"),
                io.Combo.Input("res_2mp", options=RESOLUTIONS["2mp"], default="1408x1408 (1:1)"),
                io.Boolean.Input("use_2mp", default=False, label_on="Active (2MP)", label_off="Inactive"),
                io.Combo.Input("res_3mp", options=RESOLUTIONS["3mp"], default="1728x1728 (1:1)"),
                io.Boolean.Input("use_3mp", default=False, label_on="Active (3MP)", label_off="Inactive"),
                io.Combo.Input("res_4mp", options=RESOLUTIONS["4mp"], default="2048x2048 (1:1)"),
                io.Boolean.Input("use_4mp", default=False, label_on="Active (4MP)", label_off="Inactive"),
                io.Int.Input("batch_size", default=1, min=1, max=64),
            ],
            outputs=[
                io.Latent.Output(display_name="latent"),
                io.Int.Output(display_name="width"),
                io.Int.Output(display_name="height"),
            ],
        )

    @classmethod
    def execute(
        cls,
        res_025mp,
        use_025mp,
        res_06mp,
        use_06mp,
        res_1mp,
        use_1mp,
        res_2mp,
        use_2mp,
        res_3mp,
        use_3mp,
        res_4mp,
        use_4mp,
        batch_size,
    ) -> io.NodeOutput:
        selected = res_1mp
        for enabled, value in (
            (use_025mp, res_025mp),
            (use_06mp, res_06mp),
            (use_1mp, res_1mp),
            (use_2mp, res_2mp),
            (use_3mp, res_3mp),
            (use_4mp, res_4mp),
        ):
            if enabled:
                selected = value
                break
        try:
            width, height = (int(value) for value in str(selected).split(" ", 1)[0].split("x"))
        except (TypeError, ValueError):
            width = height = 1024
        latent = {"samples": torch.zeros([int(batch_size), 4, height // 8, width // 8])}
        return io.NodeOutput(latent, width, height)


__all__ = ["RESOLUTIONS", "ResolutionSelectNode"]
