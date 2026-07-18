"""HTTP route registration for Flow Assistor's V3 extension lifecycle."""

from __future__ import annotations

from typing import Any, Callable

from server import PromptServer

from .nodes.loaders.lora_online import open_lora_folder_handler
from .nodes.image.visual_marquee import submit_crop_handler


_ROUTES: tuple[tuple[str, str, Callable[..., Any]], ...] = (
    ("POST", "/flow_assistor/open_lora_folder", open_lora_folder_handler),
    ("POST", "/flow_assistor/submit_crop", submit_crop_handler),
    ("POST", "/api/flow_assistor/submit_crop", submit_crop_handler),
)
_REGISTERED = False


def _route_table_contains(route_table: Any, method: str, path: str) -> bool:
    for item in getattr(route_table, "_items", ()):
        item_method = str(getattr(item, "method", "")).upper()
        item_path = getattr(item, "path", None)
        if item_method == method and item_path == path:
            return True
    return False


def _app_contains(app: Any, method: str, path: str) -> bool:
    try:
        for route in app.router.routes():
            if str(getattr(route, "method", "")).upper() != method:
                continue
            resource = getattr(route, "resource", None)
            canonical = getattr(resource, "canonical", None)
            if canonical == path:
                return True
    except Exception:
        return False
    return False


def register_routes() -> None:
    """Register routes once from ``ComfyExtension.on_load``."""
    global _REGISTERED
    if _REGISTERED:
        return

    server = PromptServer.instance
    route_table = getattr(server, "routes", None)
    app = getattr(server, "app", None)

    for method, path, handler in _ROUTES:
        if route_table is not None and _route_table_contains(route_table, method, path):
            continue
        if app is not None and _app_contains(app, method, path):
            continue

        if route_table is not None:
            route_table.route(method, path)(handler)
        elif app is not None:
            app.router.add_route(method, path, handler)
        else:
            raise RuntimeError("PromptServer is not ready for route registration")

    _REGISTERED = True


__all__ = ["register_routes"]
