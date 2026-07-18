"""Download and apply a LoRA using ComfyUI V3 asynchronous execution."""

from __future__ import annotations

import asyncio
import gc
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import aiohttp
import torch
from aiohttp import web

import comfy.sd
import comfy.utils
import folder_paths
from comfy_api.latest import ComfyAPI, io
from ..categories import LOADERS


_API = ComfyAPI()
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://civitai.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}
_CHUNK_SIZE = 1024 * 1024


def get_target_folder() -> str:
    lora_root = folder_paths.get_folder_paths("loras")[0]
    return os.path.join(lora_root, "Flow-Assistor-LoRA")


async def open_lora_folder_handler(request: web.Request) -> web.Response:
    del request
    target_dir = get_target_folder()
    os.makedirs(target_dir, exist_ok=True)
    try:
        if os.name == "nt":
            await asyncio.to_thread(os.startfile, target_dir)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            await asyncio.to_thread(subprocess.Popen, ["open", target_dir])
        else:
            await asyncio.to_thread(subprocess.Popen, ["xdg-open", target_dir])
        return web.json_response({"status": "success"})
    except Exception as exc:
        return web.json_response({"status": "error", "message": str(exc)}, status=500)


def get_filename_from_content_disposition(value: str | None) -> str | None:
    if not value:
        return None
    utf8_match = re.search(r"filename\*=UTF-8''([^;]+)", value, flags=re.IGNORECASE)
    if utf8_match:
        return unquote(utf8_match.group(1).strip())
    plain_match = re.search(r'filename="?([^";]+)"?', value, flags=re.IGNORECASE)
    return plain_match.group(1).strip() if plain_match else None


def sanitize_filename(filename: str) -> str:
    filename = os.path.basename(unquote(filename)).strip()
    filename = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "", filename)
    filename = filename.strip(" .") or "online_lora_unknown.safetensors"
    if not filename.lower().endswith((".safetensors", ".pt", ".pth", ".ckpt")):
        filename += ".safetensors"
    return filename


async def resolve_civitai_url(session: aiohttp.ClientSession, url: str) -> str:
    match = re.search(r"civitai\.com/models/(\d+)", url)
    if not match:
        return url

    model_id = match.group(1)
    version_match = re.search(r"modelVersionId=(\d+)", url)
    target_version_id = int(version_match.group(1)) if version_match else None
    api_url = f"https://civitai.com/api/v1/models/{model_id}"
    try:
        async with session.get(api_url) as response:
            response.raise_for_status()
            data = await response.json()
        versions = data.get("modelVersions") or []
        if not versions:
            return url
        selected = versions[0]
        if target_version_id is not None:
            selected = next(
                (version for version in versions if int(version.get("id", -1)) == target_version_id),
                selected,
            )
        return selected.get("downloadUrl") or url
    except Exception as exc:
        print(f"[LoRA Online] Civitai resolution warning: {exc}")
        return url


def _fallback_filename(url: str) -> str:
    path_name = os.path.basename(urlparse(url).path)
    return sanitize_filename(path_name or "online_lora_unknown.safetensors")


async def _set_progress(value: int, max_value: int) -> None:
    try:
        await _API.execution.set_progress(value=value, max_value=max_value, preview_image=None)
    except Exception:
        # Progress is advisory and must not make a download fail.
        pass


async def download_file(
    session: aiohttp.ClientSession,
    url: str,
    destination: str,
    force: bool = False,
) -> str:
    final_url = await resolve_civitai_url(session, url)
    os.makedirs(destination, exist_ok=True)

    async with session.get(final_url, allow_redirects=True) as response:
        response.raise_for_status()
        filename = get_filename_from_content_disposition(response.headers.get("content-disposition"))
        if not filename:
            filename = _fallback_filename(str(response.url or final_url))
        filename = sanitize_filename(filename)
        file_path = os.path.join(destination, filename)
        partial_path = file_path + ".part"

        if os.path.exists(file_path) and not force:
            return file_path

        total_size = int(response.headers.get("content-length", "0") or 0)
        progress_max = total_size if total_size > 0 else 1
        written = 0
        try:
            with open(partial_path, "wb") as handle:
                async for chunk in response.content.iter_chunked(_CHUNK_SIZE):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    written += len(chunk)
                    await _set_progress(min(written, progress_max), progress_max)
            os.replace(partial_path, file_path)
            await _set_progress(progress_max, progress_max)
            return file_path
        except BaseException:
            try:
                os.remove(partial_path)
            except FileNotFoundError:
                pass
            raise


def _load_lora(model, file_path: str, strength_model: float):
    lora = comfy.utils.load_torch_file(file_path, safe_load=True)
    model_lora, _ = comfy.sd.load_lora_for_models(model, None, lora, strength_model, 0)
    return model_lora, lora


def _delete_download(file_path: str, lora_object) -> None:
    del lora_object
    gc.collect()
    if hasattr(torch, "cuda"):
        torch.cuda.empty_cache()
    try:
        Path(file_path).unlink(missing_ok=True)
    except Exception as exc:
        print(f"[LoRA Online] Could not delete file: {exc}")


class LoRAOnlineNode(io.ComfyNode):
    """Download a LoRA URL, apply it to a model, and optionally keep the file."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="LoRAOnlineNode",
            display_name="LoRA Online",
            category=LOADERS,
            description="Downloads a LoRA from a direct or Civitai URL and applies it to the model.",
            inputs=[
                io.Model.Input("model"),
                io.String.Input("url", default="", multiline=False),
                io.Float.Input("strength_model", default=1.0, min=-10.0, max=10.0, step=0.01),
                io.Boolean.Input(
                    "save_model",
                    default=True,
                    label_on="Save to Disk",
                    label_off="Delete after Gen",
                ),
                io.Boolean.Input("force_redownload", default=False, optional=True),
            ],
            outputs=[io.Model.Output(display_name="model")],
            not_idempotent=True,
        )

    @classmethod
    async def execute(
        cls,
        model,
        url,
        strength_model,
        save_model,
        force_redownload=False,
    ) -> io.NodeOutput:
        del cls
        clean_url = str(url).strip()
        if not clean_url:
            return io.NodeOutput(model)

        destination = get_target_folder()
        timeout = aiohttp.ClientTimeout(total=None, connect=30, sock_read=120)
        try:
            async with aiohttp.ClientSession(headers=_HEADERS, timeout=timeout) as session:
                file_path = await download_file(
                    session,
                    clean_url,
                    destination,
                    force=bool(force_redownload),
                )
        except Exception as exc:
            print(f"[LoRA Online] Download failed: {exc}")
            return io.NodeOutput(model)

        try:
            model_lora, lora_object = await asyncio.to_thread(
                _load_lora,
                model,
                file_path,
                float(strength_model),
            )
        except Exception as exc:
            print(f"[LoRA Online] File is not a valid LoRA: {exc}")
            return io.NodeOutput(model)

        if not save_model:
            await asyncio.to_thread(_delete_download, file_path, lora_object)
        return io.NodeOutput(model_lora)


__all__ = [
    "LoRAOnlineNode",
    "download_file",
    "get_filename_from_content_disposition",
    "get_target_folder",
    "open_lora_folder_handler",
    "resolve_civitai_url",
    "sanitize_filename",
]
