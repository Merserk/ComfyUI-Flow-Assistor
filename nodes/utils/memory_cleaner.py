"""VRAM/RAM cleanup passthrough node for ComfyUI V3."""

import gc

import torch
from comfy_api.latest import io
from ..categories import UTILS
import comfy.model_management as mm


def _free_ram() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        if hasattr(torch.cuda, "ipc_collect"):
            torch.cuda.ipc_collect()


class VRAMRAMCleanerNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        template = io.MatchType.Template("flow_assistor_cleaner")
        return io.Schema(
            node_id="VRAMRAMCleanerNode",
            display_name="VRAM/RAM Cleaner",
            category=UTILS,
            inputs=[
                io.MatchType.Input("any_model", template=template),
                io.Combo.Input(
                    "mode",
                    options=["Current", "Others", "All"],
                    default="Current",
                ),
            ],
            outputs=[io.MatchType.Output(template=template, display_name="any_model")],
            not_idempotent=True,
        )

    @classmethod
    def execute(cls, any_model, mode) -> io.NodeOutput:
        try:
            if mode == "All":
                mm.unload_all_models()
                mm.soft_empty_cache()
                _free_ram()
            elif mode == "Current":
                mm.unload_model_cloned(any_model)
                mm.soft_empty_cache()
                _free_ram()
            elif mode == "Others":
                mm.unload_all_models()
                mm.soft_empty_cache()
                _free_ram()
                try:
                    mm.load_models_gpu([any_model])
                except Exception as exc:
                    print(f"[VRAM Cleaner] Could not force-load the retained object: {exc}")
        except Exception as exc:
            print(f"[VRAM Cleaner] Error during cleanup: {exc}")
        return io.NodeOutput(any_model)


__all__ = ["VRAMRAMCleanerNode"]
