import os
import time
import uuid
import threading
from typing import Any, Dict, Optional, Tuple

import numpy as np
import torch
from PIL import Image
from aiohttp import web

import comfy.utils
import folder_paths
from server import PromptServer

# -----------------------------------------------------------------------------
# Thread-safe, per-node state store
# -----------------------------------------------------------------------------
_STATE_LOCK = threading.Lock()
_STATE: Dict[str, Dict[str, Any]] = {}
# _STATE[node_id] = {"event": Event, "token": str, "data": dict|None, "created": float}

WAIT_TIMEOUT_SECONDS = 600  # 10 minutes


def _get_or_create_state(node_id: str) -> Dict[str, Any]:
    with _STATE_LOCK:
        st = _STATE.get(node_id)
        if st is None:
            st = {
                "event": threading.Event(),
                "token": "",
                "data": None,
                "created": time.time(),
            }
            _STATE[node_id] = st
        return st


def _reset_state_for_run(node_id: str) -> str:
    st = _get_or_create_state(node_id)
    token = uuid.uuid4().hex
    with _STATE_LOCK:
        st["token"] = token
        st["data"] = None
        st["created"] = time.time()
        st["event"].clear()
    return token


def _set_payload(node_id: str, token: str, payload: dict) -> Tuple[bool, str]:
    st = _get_or_create_state(node_id)
    with _STATE_LOCK:
        expected = st.get("token") or ""
        if expected and token != expected:
            return False, f"Token mismatch for node_id={node_id}. expected={expected} got={token}"
        st["data"] = payload
        st["event"].set()
    return True, "ok"


def _pop_payload(node_id: str) -> Optional[dict]:
    with _STATE_LOCK:
        st = _STATE.get(node_id)
        if not st:
            return None
        data = st.get("data")
        _STATE.pop(node_id, None)
        return data


# -----------------------------------------------------------------------------
# API handler
# -----------------------------------------------------------------------------
async def submit_crop_handler(request: web.Request) -> web.Response:
    try:
        json_data = await request.json()

        node_id = str(json_data.get("node_id", "")).strip()
        token = str(json_data.get("token", "")).strip()
        action = str(json_data.get("action", "submit")).strip().lower()
        crop_data = json_data.get("crop_data")

        print(f"[VisualMarquee] API Received: node_id={node_id} token={token} action={action}")

        if not node_id:
            return web.json_response({"status": "error", "message": "Missing node_id"}, status=400)
        if not token:
            return web.json_response({"status": "error", "message": "Missing token"}, status=400)

        if action not in ("submit", "cancel"):
            return web.json_response({"status": "error", "message": "Invalid action"}, status=400)

        if action == "cancel":
            ok, msg = _set_payload(node_id, token, {"__action__": "cancel"})
            if not ok:
                return web.json_response({"status": "error", "message": msg}, status=409)
            return web.json_response({"status": "success", "action": "cancel"})

        # submit
        if not isinstance(crop_data, dict):
            return web.json_response({"status": "error", "message": "crop_data must be an object"}, status=400)

        ok, msg = _set_payload(node_id, token, {"__action__": "submit", "crop_data": crop_data})
        if not ok:
            return web.json_response({"status": "error", "message": msg}, status=409)

        return web.json_response({"status": "success", "action": "submit"})
    except Exception as e:
        print(f"[VisualMarquee] API Error: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)


def _route_exists(app: web.Application, path: str, method: str = "POST") -> bool:
    try:
        for r in app.router.routes():
            if r.method != method:
                continue
            res = getattr(r, "resource", None)
            if res is None:
                continue
            if getattr(res, "canonical", None) == path:
                return True
    except Exception:
        pass
    return False


def _register_routes() -> None:
    if not hasattr(PromptServer.instance, "app"):
        print("[VisualMarquee] PromptServer has no app yet. Routes not registered.")
        return

    app = PromptServer.instance.app

    # Register BOTH paths (ComfyUI frontend variations)
    paths = ["/flow_assistor/submit_crop", "/api/flow_assistor/submit_crop"]
    for p in paths:
        if not _route_exists(app, p, "POST"):
            app.router.add_post(p, submit_crop_handler)
            print(f"[VisualMarquee] API route registered: POST {p}")


_register_routes()


# -----------------------------------------------------------------------------
# Node
# -----------------------------------------------------------------------------
class VisualMarqueeSelection:
    """
    Visual Marquee (Interactive)

    - Shows popup to select area
    - Pauses until confirm or exit/cancel
    - "Original size" (default ON) returns exact selection w/h
    - If Original size OFF, upscale to max_resolution (longest side)
    """

    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "max_resolution": ("INT", {"default": 1024, "min": 512, "max": 4096}),
                # Requested toggle (default enabled)
                "original_size": ("BOOLEAN", {"default": True}),
                # keep old snapping behavior only when upscaling
                "force_multiple_of_8": ("BOOLEAN", {"default": True}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "TILE_DATA")
    RETURN_NAMES = ("cropped_image", "mask", "tile_data")
    FUNCTION = "process"
    CATEGORY = "flow-assistor/interactive"
    OUTPUT_NODE = False

    def IS_CHANGED(self, **kwargs):
        return float("nan")

    def process(
        self,
        image,
        max_resolution,
        original_size=True,
        force_multiple_of_8=True,
        unique_id=None,
        extra_pnginfo=None
    ):
        node_id = str(unique_id).strip() or uuid.uuid4().hex

        # 1) Save preview
        img_tensor = image[0]  # [H, W, C]
        arr = (255.0 * img_tensor.detach().cpu().numpy())
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)

        filename = f"marquee_preview_{node_id}.png"
        full_path = os.path.join(self.output_dir, filename)
        img.save(full_path)

        # 2) Reset state and create token for this run
        token = _reset_state_for_run(node_id)

        # 3) Notify browser (also tell it current mode for display text)
        PromptServer.instance.send_sync("flow_assistor_marquee_show", {
            "node_id": node_id,
            "token": token,
            "filename": filename,
            "max_resolution": int(max_resolution),
            "original_size": bool(original_size),
        })

        print(f"[VisualMarquee] Node {node_id} paused. Waiting... token={token}")

        # 4) Wait
        st = _get_or_create_state(node_id)
        ok = st["event"].wait(timeout=WAIT_TIMEOUT_SECONDS)
        if not ok:
            with _STATE_LOCK:
                _STATE.pop(node_id, None)
            raise TimeoutError("[VisualMarquee] Timed out waiting for selection.")

        payload = _pop_payload(node_id)
        if not isinstance(payload, dict):
            raise RuntimeError("[VisualMarquee] Resume signaled but payload missing/invalid.")

        if payload.get("__action__") == "cancel":
            # Stop whole process
            raise RuntimeError("[VisualMarquee] Cancelled by user.")

        crop_data = payload.get("crop_data")
        if not isinstance(crop_data, dict):
            raise RuntimeError("[VisualMarquee] crop_data missing/invalid.")

        # 5) Parse crop
        img_h, img_w = int(image.shape[1]), int(image.shape[2])

        x = int(round(float(crop_data.get("x", 0))))
        y = int(round(float(crop_data.get("y", 0))))
        w = int(round(float(crop_data.get("w", 512))))
        h = int(round(float(crop_data.get("h", 512))))

        # Clamp
        x = max(0, min(x, img_w - 1))
        y = max(0, min(y, img_h - 1))
        w = max(1, min(w, img_w - x))
        h = max(1, min(h, img_h - y))

        cropped = image[:, y:y + h, x:x + w, :]  # [B, h, w, C]

        # 6) Output size logic
        if original_size:
            final_image = cropped
            out_w, out_h = w, h
        else:
            scale = float(max_resolution) / float(max(w, h))
            out_w = max(1, int(round(w * scale)))
            out_h = max(1, int(round(h * scale)))

            if force_multiple_of_8:
                out_w = max(8, (out_w // 8) * 8)
                out_h = max(8, (out_h // 8) * 8)

            samples = cropped.movedim(-1, 1)  # [B, C, h, w]
            resized = comfy.utils.common_upscale(samples, out_w, out_h, "lanczos", "disabled")
            final_image = resized.movedim(1, -1)  # [B, out_h, out_w, C]

        mask = torch.ones(
            (final_image.shape[0], final_image.shape[1], final_image.shape[2]),
            dtype=torch.float32,
            device=final_image.device
        )

        tile_data = {
            "original_bbox": (x, y, w, h),
            "target_size": (int(out_w), int(out_h)),
            "original_image_shape": (img_h, img_w),
            "original_size_mode": bool(original_size),
        }

        print(f"[VisualMarquee] Resumed: selected={w}x{h} output={out_w}x{out_h} original_size={original_size}")
        return (final_image, mask, tile_data)


NODE_CLASS_MAPPINGS = {
    "VisualMarqueeSelection": VisualMarqueeSelection,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VisualMarqueeSelection": "Visual Marquee (Interactive)",
}