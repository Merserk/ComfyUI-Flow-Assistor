"""Interactive marquee node using V3 async execution and external state."""

from __future__ import annotations

import asyncio
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from PIL import Image
from aiohttp import web

import comfy.utils
import folder_paths
from comfy_api.latest import io
from ..categories import IMAGE
from server import PromptServer

from ...runtime_state import normalize_node_id
from ...v3_types import TileData

WAIT_TIMEOUT_SECONDS = 600
_STATE_LOCK = threading.RLock()


@dataclass
class _PendingSelection:
    token: str
    loop: asyncio.AbstractEventLoop
    future: asyncio.Future[dict[str, Any]]
    created: float


_STATE: dict[str, _PendingSelection] = {}


def _safe_filename_component(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return safe[:96] or uuid.uuid4().hex


def _begin_wait(node_id: str) -> tuple[str, asyncio.Future[dict[str, Any]]]:
    loop = asyncio.get_running_loop()
    token = uuid.uuid4().hex
    future: asyncio.Future[dict[str, Any]] = loop.create_future()
    with _STATE_LOCK:
        previous = _STATE.pop(node_id, None)
        _STATE[node_id] = _PendingSelection(token, loop, future, time.monotonic())
    if previous is not None and not previous.future.done():
        previous.loop.call_soon_threadsafe(
            previous.future.set_exception,
            RuntimeError("[VisualMarquee] Superseded by a newer execution."),
        )
    return token, future


def _finish_wait(node_id: str, token: str) -> None:
    with _STATE_LOCK:
        pending = _STATE.get(node_id)
        if pending is not None and pending.token == token:
            _STATE.pop(node_id, None)


def _set_payload(node_id: str, token: str, payload: dict[str, Any]) -> tuple[bool, str]:
    with _STATE_LOCK:
        pending = _STATE.get(node_id)
        if pending is None:
            return False, f"No active selection for node_id={node_id}"
        if token != pending.token:
            return False, f"Token mismatch for node_id={node_id}"
        if pending.future.done():
            return False, f"Selection for node_id={node_id} is already complete"
        loop = pending.loop
        future = pending.future

    def complete() -> None:
        if not future.done():
            future.set_result(payload)

    loop.call_soon_threadsafe(complete)
    return True, "ok"


async def submit_crop_handler(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        raw_node_id = data.get("node_id")
        node_id = normalize_node_id(raw_node_id) if raw_node_id is not None and str(raw_node_id).strip() else ""
        token = str(data.get("token", "")).strip()
        action = str(data.get("action", "submit")).strip().lower()
        crop_data = data.get("crop_data")

        if not node_id:
            return web.json_response({"status": "error", "message": "Missing node_id"}, status=400)
        if not token:
            return web.json_response({"status": "error", "message": "Missing token"}, status=400)
        if action not in {"submit", "cancel"}:
            return web.json_response({"status": "error", "message": "Invalid action"}, status=400)
        if action == "submit" and not isinstance(crop_data, dict):
            return web.json_response(
                {"status": "error", "message": "crop_data must be an object"},
                status=400,
            )

        payload = {"__action__": action}
        if action == "submit":
            payload["crop_data"] = crop_data
        ok, message = _set_payload(node_id, token, payload)
        if not ok:
            return web.json_response({"status": "error", "message": message}, status=409)
        return web.json_response({"status": "success", "action": action})
    except Exception as exc:
        print(f"[VisualMarquee] API error: {exc}")
        return web.json_response({"status": "error", "message": str(exc)}, status=500)


class VisualMarqueeSelection(io.ComfyNode):
    """Pause execution until a browser crop selection is submitted or cancelled."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="VisualMarqueeSelection",
            display_name="Visual Marquee (Interactive)",
            category=IMAGE,
            description="Interactively select a crop in the browser and return image, mask, and TILE_DATA.",
            inputs=[
                io.Image.Input("image"),
                io.Int.Input("max_resolution", default=1024, min=512, max=4096),
                io.Boolean.Input("original_size", default=True),
                io.Boolean.Input("force_multiple_of_8", default=True),
            ],
            outputs=[
                io.Image.Output(display_name="cropped_image"),
                io.Mask.Output(display_name="mask"),
                TileData.Output(display_name="tile_data"),
            ],
            hidden=[io.Hidden.unique_id],
            not_idempotent=True,
        )

    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        del kwargs
        return float("nan")

    @classmethod
    async def execute(
        cls,
        image,
        max_resolution,
        original_size=True,
        force_multiple_of_8=True,
    ) -> io.NodeOutput:
        node_id = normalize_node_id(getattr(cls.hidden, "unique_id", None)) or uuid.uuid4().hex
        output_dir = folder_paths.get_temp_directory()
        os.makedirs(output_dir, exist_ok=True)

        image_array = 255.0 * image[0].detach().cpu().numpy()
        image_array = np.clip(image_array, 0, 255).astype(np.uint8)
        preview = Image.fromarray(image_array)
        filename = f"marquee_preview_{_safe_filename_component(node_id)}.png"
        full_path = os.path.join(output_dir, filename)
        await asyncio.to_thread(preview.save, full_path)

        token, future = _begin_wait(node_id)
        PromptServer.instance.send_sync(
            "flow_assistor_marquee_show",
            {
                "node_id": node_id,
                "token": token,
                "filename": filename,
                "max_resolution": int(max_resolution),
                "original_size": bool(original_size),
            },
        )

        try:
            payload = await asyncio.wait_for(future, timeout=WAIT_TIMEOUT_SECONDS)
        except asyncio.TimeoutError as exc:
            raise TimeoutError("[VisualMarquee] Timed out waiting for selection.") from exc
        finally:
            _finish_wait(node_id, token)
            try:
                await asyncio.to_thread(os.remove, full_path)
            except FileNotFoundError:
                pass
            except OSError as exc:
                print(f"[VisualMarquee] Could not remove preview {full_path}: {exc}")

        if payload.get("__action__") == "cancel":
            raise RuntimeError("[VisualMarquee] Cancelled by user.")
        crop_data = payload.get("crop_data")
        if not isinstance(crop_data, dict):
            raise RuntimeError("[VisualMarquee] crop_data missing or invalid.")

        image_height, image_width = int(image.shape[1]), int(image.shape[2])
        x = int(round(float(crop_data.get("x", 0))))
        y = int(round(float(crop_data.get("y", 0))))
        width = int(round(float(crop_data.get("w", 512))))
        height = int(round(float(crop_data.get("h", 512))))

        x = max(0, min(x, image_width - 1))
        y = max(0, min(y, image_height - 1))
        width = max(1, min(width, image_width - x))
        height = max(1, min(height, image_height - y))
        cropped = image[:, y : y + height, x : x + width, :]

        if original_size:
            final_image = cropped
            output_width, output_height = width, height
        else:
            scale = float(max_resolution) / float(max(width, height))
            output_width = max(1, int(round(width * scale)))
            output_height = max(1, int(round(height * scale)))
            if force_multiple_of_8:
                output_width = max(8, (output_width // 8) * 8)
                output_height = max(8, (output_height // 8) * 8)
            samples = cropped.movedim(-1, 1)
            resized = comfy.utils.common_upscale(
                samples,
                output_width,
                output_height,
                "lanczos",
                "disabled",
            )
            final_image = resized.movedim(1, -1)

        mask = torch.ones(
            (final_image.shape[0], final_image.shape[1], final_image.shape[2]),
            dtype=torch.float32,
            device=final_image.device,
        )
        tile_data = {
            "original_bbox": (x, y, width, height),
            "target_size": (int(output_width), int(output_height)),
            "original_image_shape": (image_height, image_width),
            "original_size_mode": bool(original_size),
        }
        return io.NodeOutput(final_image, mask, tile_data)


__all__ = [
    "VisualMarqueeSelection",
    "submit_crop_handler",
    "_begin_wait",
    "_set_payload",
    "_finish_wait",
]
