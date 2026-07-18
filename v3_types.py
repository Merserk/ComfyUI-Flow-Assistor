"""Shared ComfyUI V3 socket types used by Flow Assistor nodes."""

from comfy_api.latest import io


TileData = io.Custom("TILE_DATA")


__all__ = ["TileData"]
