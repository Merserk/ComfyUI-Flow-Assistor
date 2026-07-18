"""Generate precise image captions with ComfyUI's native Qwen3-VL encoder support."""

from __future__ import annotations

import asyncio
import gc
import os
import re
from pathlib import Path
from typing import Any

import aiohttp
import torch

import comfy.sd
import folder_paths
from comfy_api.latest import ComfyAPI, io

from ..categories import IMAGE_CAPTION


_MODEL_SPECS = {
    "int8": {
        "filename": "qwen3vl_4b_int8_convrot.safetensors",
        "url": (
            "https://huggingface.co/Merserk/qwen3vl-4b-int8-convrot/resolve/main/"
            "qwen3vl_4b_int8_convrot.safetensors"
        ),
    },
    "int4": {
        "filename": "qwen3vl_4b_int4_convrot.safetensors",
        "url": (
            "https://huggingface.co/Merserk/qwen3vl-4b-int4-convrot/resolve/main/"
            "qwen3vl_4b_int4_convrot.safetensors"
        ),
    },
}
_MODEL_SUBFOLDER = "flow-assistor"
_DOWNLOAD_CHUNK_SIZE = 8 * 1024 * 1024
_DOWNLOAD_HEADERS = {"User-Agent": "ComfyUI-Flow-Assistor/2.1 Caption-Creator"}

_API = ComfyAPI()
_MODEL_LOCK = asyncio.Lock()
_CACHED_MODEL_PATH: Path | None = None
_CACHED_CLIP: Any = None


class CaptionCreatorError(RuntimeError):
    """Raised when Caption Creator cannot validate, load, or run its model."""


def _text_encoder_root() -> Path:
    paths = [Path(path) for path in folder_paths.get_folder_paths("text_encoders")]
    if not paths:
        raise CaptionCreatorError("ComfyUI has no registered text_encoders model directory.")

    for path in paths:
        if path.name.lower() == "text_encoders":
            return path
    return paths[0]


def _model_directory() -> Path:
    return _text_encoder_root() / _MODEL_SUBFOLDER


def _model_path(model_precision: str) -> Path:
    try:
        filename = _MODEL_SPECS[str(model_precision)]["filename"]
    except KeyError as exc:
        supported = ", ".join(_MODEL_SPECS)
        raise CaptionCreatorError(
            f"Unsupported model_precision {model_precision!r}. Choose one of: {supported}."
        ) from exc
    return _model_directory() / filename


async def _set_progress(value: int, max_value: int) -> None:
    try:
        await _API.execution.set_progress(
            value=value,
            max_value=max_value,
            preview_image=None,
        )
    except Exception:
        # Progress reporting is advisory and must not make captioning fail.
        pass


async def _download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f"{target.name}.part")
    partial.unlink(missing_ok=True)

    timeout = aiohttp.ClientTimeout(total=None, connect=60, sock_read=120)
    downloaded = 0
    expected_size: int | None = None

    try:
        print(f"[Caption Creator] Downloading {target.name} to {target.parent}", flush=True)
        async with aiohttp.ClientSession(headers=_DOWNLOAD_HEADERS, timeout=timeout) as session:
            async with session.get(url, allow_redirects=True) as response:
                response.raise_for_status()
                expected_size_header = response.headers.get("Content-Length")
                if expected_size_header:
                    try:
                        expected_size = int(expected_size_header)
                    except ValueError:
                        expected_size = None

                progress_max = expected_size if expected_size and expected_size > 0 else 1
                with partial.open("wb") as output:
                    async for chunk in response.content.iter_chunked(_DOWNLOAD_CHUNK_SIZE):
                        if not chunk:
                            continue
                        output.write(chunk)
                        downloaded += len(chunk)
                        await _set_progress(min(downloaded, progress_max), progress_max)

                    output.flush()
                    os.fsync(output.fileno())

        if downloaded == 0:
            raise CaptionCreatorError(f"Downloaded file is empty: {url}")
        if expected_size is not None and downloaded != expected_size:
            raise CaptionCreatorError(
                f"Incomplete download for {target.name}: received {downloaded} "
                f"of {expected_size} bytes."
            )

        os.replace(partial, target)
        final_progress = expected_size if expected_size and expected_size > 0 else 1
        await _set_progress(final_progress, final_progress)
        print(f"[Caption Creator] Download complete: {target}", flush=True)
    except BaseException as exc:
        partial.unlink(missing_ok=True)
        if isinstance(exc, (CaptionCreatorError, asyncio.CancelledError)):
            raise
        if not isinstance(exc, Exception):
            raise
        raise CaptionCreatorError(f"Failed to download {target.name}: {exc}") from exc


async def _ensure_model(model_precision: str, auto_download: bool) -> Path:
    model_precision = str(model_precision)
    target = _model_path(model_precision)
    if target.is_file() and target.stat().st_size > 0:
        return target

    if not auto_download:
        raise CaptionCreatorError(
            f"Missing {model_precision} caption model: {target}\n"
            "Enable auto_download or place the selected model at this path."
        )

    spec = _MODEL_SPECS[model_precision]
    await _download_file(spec["url"], target)
    if not target.is_file() or target.stat().st_size == 0:
        raise CaptionCreatorError(f"Model download did not produce a valid file: {target}")
    return target


def _release_cached_clip() -> None:
    global _CACHED_MODEL_PATH, _CACHED_CLIP

    old_clip = _CACHED_CLIP
    _CACHED_MODEL_PATH = None
    _CACHED_CLIP = None
    if old_clip is None:
        return

    del old_clip
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _load_clip_from_path(model_path: Path, model_precision: str):
    clip_types = getattr(comfy.sd, "CLIPType", None)
    clip_type = getattr(clip_types, "KREA2", None)
    if clip_type is None:
        raise CaptionCreatorError(
            "Caption Creator requires a current ComfyUI build with CLIPType.KREA2 "
            "and native Qwen3-VL ConvRot support."
        )

    try:
        return comfy.sd.load_clip(
            ckpt_paths=[str(model_path)],
            embedding_directory=folder_paths.get_folder_paths("embeddings"),
            clip_type=clip_type,
            model_options={},
        )
    except Exception as exc:
        raise CaptionCreatorError(
            f"Failed to load the {model_precision} Qwen3-VL ConvRot model with "
            f"ComfyUI's native text-encoder loader: {exc}. Update ComfyUI if this "
            "model format is not supported by your installation."
        ) from exc


async def _load_clip(model_precision: str, auto_download: bool):
    global _CACHED_MODEL_PATH, _CACHED_CLIP

    async with _MODEL_LOCK:
        model_path = await _ensure_model(model_precision, auto_download)
        if _CACHED_CLIP is not None and _CACHED_MODEL_PATH == model_path:
            return _CACHED_CLIP

        _release_cached_clip()
        clip = _load_clip_from_path(model_path, model_precision)
        _CACHED_MODEL_PATH = model_path
        _CACHED_CLIP = clip
        return clip


def _build_prompt(words: int) -> str:
    words = int(words)
    if words < 0 or words > 300:
        raise CaptionCreatorError("words must be between 0 and 300.")
    if words == 0:
        return (
            "Generate one ultra-precise detailed sentence describing only the visible image "
            "without guessing. Include all clearly visible details. No extra text."
        )
    return (
        "Generate one ultra-precise detailed sentence describing only the visible image. "
        f"Use close to {words} words without guessing. "
        "Include all clearly visible details. No extra text."
    )


def _max_generation_tokens(words: int) -> int:
    if int(words) == 0:
        return 512
    return max(96, min(1024, int(words) * 2 + 64))


def _clean_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = text.replace("<|assistant|>", " ").replace("<|end|>", " ")
    text = re.sub(r"^\s*(?:assistant|caption)\s*:\s*", "", text, flags=re.IGNORECASE)
    text = " ".join(text.split()).strip()
    if not text:
        raise CaptionCreatorError("The model generated empty text.")
    return text


def _validate_image_batch(image: Any) -> Any:
    ndim = getattr(image, "ndim", None)
    if ndim == 3:
        image = image.unsqueeze(0)
        ndim = image.ndim
    if ndim != 4:
        shape = list(getattr(image, "shape", []))
        raise CaptionCreatorError(
            f"Expected a ComfyUI IMAGE tensor with shape [B,H,W,C], got {shape}."
        )
    if int(image.shape[0]) < 1:
        raise CaptionCreatorError("Caption Creator received an empty image batch.")
    if int(image.shape[-1]) < 3:
        raise CaptionCreatorError(
            f"Expected at least 3 image channels, got shape {list(image.shape)}."
        )
    return image[..., :3]


def _generate_one(clip: Any, image: Any, prompt: str, max_length: int) -> str:
    try:
        tokens = clip.tokenize(
            prompt,
            image=image,
            skip_template=False,
            min_length=1,
            thinking=False,
        )
        generated_ids = clip.generate(
            tokens,
            do_sample=False,
            max_length=max_length,
        )
        return _clean_text(clip.decode(generated_ids))
    except CaptionCreatorError:
        raise
    except Exception as exc:
        raise CaptionCreatorError(f"Caption generation failed: {exc}") from exc


class CaptionCreator(io.ComfyNode):
    """Caption one image or every image in a batch with a local Qwen3-VL model."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="CaptionCreator",
            display_name="Caption Creator",
            category=IMAGE_CAPTION,
            description=(
                "Creates a precise caption for each input image with a native Qwen3-VL "
                "ConvRot text encoder. Batch captions are returned on separate lines."
            ),
            inputs=[
                io.Image.Input("image", tooltip="A ComfyUI IMAGE tensor; batches are supported."),
                io.Combo.Input(
                    "model_precision",
                    options=["int8", "int4"],
                    default="int8",
                    tooltip="Choose the Qwen3-VL ConvRot model precision to load.",
                ),
                io.Boolean.Input(
                    "auto_download",
                    default=True,
                    tooltip=(
                        "Download a missing model into models/text_encoders/flow-assistor."
                    ),
                ),
                io.Int.Input(
                    "words",
                    default=100,
                    min=0,
                    max=300,
                    step=1,
                    display_mode=io.NumberDisplay.slider,
                    tooltip=(
                        "Approximate words per caption. Set to 0 for an unrestricted "
                        "detailed sentence."
                    ),
                ),
            ],
            outputs=[io.String.Output(display_name="text")],
        )

    @classmethod
    async def execute(
        cls,
        image: Any,
        model_precision: str = "int8",
        auto_download: bool = True,
        words: int = 100,
    ) -> io.NodeOutput:
        del cls
        image_batch = _validate_image_batch(image)
        prompt = _build_prompt(words)
        max_length = _max_generation_tokens(words)
        clip = await _load_clip(str(model_precision), bool(auto_download))

        captions = [
            _generate_one(clip, image_batch[index : index + 1], prompt, max_length)
            for index in range(int(image_batch.shape[0]))
        ]
        return io.NodeOutput("\n".join(captions))


__all__ = [
    "CaptionCreator",
    "CaptionCreatorError",
]
