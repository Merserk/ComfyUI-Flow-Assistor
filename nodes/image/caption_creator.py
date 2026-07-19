"""Generate factual image captions with ComfyUI's native Qwen3-VL support."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import gc
import os
import time
from pathlib import Path
from typing import Any

import aiohttp
import torch
import torch.nn.functional as F

import comfy.model_management as model_management
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
_DOWNLOAD_HEADERS = {"User-Agent": "ComfyUI-Flow-Assistor/2.4.1 Caption-Creator"}

# This is only an emergency guard against a model that never emits its stop
# token. It is intentionally fixed and independent of the requested word count.
_GENERATION_TOKEN_CEILING = 512
_CAPTION_MAX_EDGE = 784
_VISION_ALIGNMENT = 28  # Qwen patch_size (14) * merge_size (2).

# Qwen3-VL Instruct-style sampling. These conservative defaults avoid the
# broad token distribution that caused numeric and short-token loops in v2.4.
# The fixed seed keeps identical inputs reproducible.
_GENERATION_OPTIONS = {
    "do_sample": True,
    "temperature": 0.70,
    "top_k": 20,
    "top_p": 0.80,
    "min_p": 0.0,
    "repetition_penalty": 1.0,
    "presence_penalty": 0.0,
    "seed": 0,
}

_API = ComfyAPI()
_MODEL_LOCK = asyncio.Lock()
_CACHED_MODEL_PATH: Path | None = None
_CACHED_CLIP: Any = None


class CaptionCreatorError(RuntimeError):
    """Raised when Caption Creator cannot validate, load, or run its model."""


@dataclass(frozen=True)
class _ResidencyInfo:
    execution_device: str
    current_device: str
    offload_device: str
    residency: str
    dynamic_vram: bool
    free_memory_before: int | None
    loaded_memory: int | None
    model_memory: int | None
    accelerator_name: str
    full_load_error: str | None = None


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

    patcher = getattr(old_clip, "patcher", None)
    unload = getattr(model_management, "unload_model_and_clones", None)
    if patcher is not None and callable(unload):
        try:
            unload(patcher)
        except Exception:
            # Deleting the last strong reference still lets ComfyUI's model
            # finalizer release the model; explicit unloading is best-effort.
            pass

    del old_clip
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _load_clip_from_path(
    model_path: Path,
    model_precision: str,
    *,
    model_options: dict[str, Any] | None = None,
):
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
            model_options=model_options or {},
        )
    except Exception as exc:
        raise CaptionCreatorError(
            f"Failed to load the {model_precision} Qwen3-VL ConvRot model with "
            f"ComfyUI's native text-encoder loader: {exc}. Update ComfyUI if this "
            "model format is not supported by your installation."
        ) from exc


def _preferred_initial_model_options(model_path: Path) -> dict[str, Any]:
    """Prefer constructing the text encoder on the configured accelerator.

    ComfyUI normally constructs large text encoders on their offload device and
    moves/stages them later. When there is comfortable headroom, initial GPU
    construction avoids the misleading ``current: cpu`` state and an extra
    first-use transfer. The normal ComfyUI path remains the fallback.
    """

    try:
        device = model_management.text_encoder_device()
    except Exception:
        return {}
    if _device_type(device) == "cpu":
        return {}

    free_memory = _safe_free_memory(device)
    try:
        file_size = int(model_path.stat().st_size)
    except OSError:
        return {}
    # Keep room for the visual prefill, KV cache, CUDA context, and allocator
    # fragmentation. The file size is a conservative proxy for quantized weight
    # memory and is available before the model is instantiated.
    reserve = max(int(1.5 * 1024**3), int(file_size * 0.25))
    required = int(file_size * 1.15) + reserve
    if free_memory is not None and free_memory < required:
        print(
            "[Caption Creator] GPU-first model construction skipped because "
            f"{_format_mib(free_memory)} is free and approximately "
            f"{_format_mib(required)} is preferred; using managed loading.",
            flush=True,
        )
        return {}

    print(
        f"[Caption Creator] Loading the caption model directly on {device}.",
        flush=True,
    )
    return {"load_device": device, "initial_device": device}


async def _load_clip(model_precision: str, auto_download: bool):
    global _CACHED_MODEL_PATH, _CACHED_CLIP

    async with _MODEL_LOCK:
        model_path = await _ensure_model(model_precision, auto_download)
        if _CACHED_CLIP is not None and _CACHED_MODEL_PATH == model_path:
            return _CACHED_CLIP

        _release_cached_clip()
        initial_options = _preferred_initial_model_options(model_path)
        try:
            clip = _load_clip_from_path(
                model_path,
                model_precision,
                model_options=initial_options,
            )
        except CaptionCreatorError as accelerator_exc:
            if not initial_options:
                raise
            print(
                "[Caption Creator] Direct accelerator construction failed; "
                f"falling back to ComfyUI-managed loading: {accelerator_exc}",
                flush=True,
            )
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            clip = _load_clip_from_path(model_path, model_precision, model_options={})

        _CACHED_MODEL_PATH = model_path
        _CACHED_CLIP = clip
        return clip


def _normalize_words(words: int) -> int:
    words = int(words)
    if words < 0:
        raise CaptionCreatorError("words must be between 0 and 200.")
    if words > 200:
        print(
            f"[Caption Creator] Legacy words value {words} exceeds the new maximum; "
            "using 200.",
            flush=True,
        )
        return 200
    return words


def _build_prompt(words: int) -> str:
    words = _normalize_words(words)
    if words == 0:
        return (
            "Describe this image in one concise plain English paragraph. "
            "State only clearly visible details. Output only the caption."
        )
    return (
        f"Describe this image in about {words} words. Use one plain English paragraph. "
        "State only clearly visible details. Output only the caption."
    )


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


def _aligned_downscale_dimension(value: int, scale: float) -> int:
    scaled = max(1, int(round(value * scale)))
    if scaled < _VISION_ALIGNMENT:
        return min(value, scaled)
    aligned = max(_VISION_ALIGNMENT, (scaled // _VISION_ALIGNMENT) * _VISION_ALIGNMENT)
    return min(value, aligned)


def _prepare_caption_image(image_batch: Any) -> tuple[Any, tuple[int, int], tuple[int, int]]:
    height = int(image_batch.shape[1])
    width = int(image_batch.shape[2])
    original_size = (width, height)
    longest_edge = max(width, height)
    if longest_edge <= _CAPTION_MAX_EDGE:
        return image_batch, original_size, original_size

    scale = _CAPTION_MAX_EDGE / float(longest_edge)
    target_height = _aligned_downscale_dimension(height, scale)
    target_width = _aligned_downscale_dimension(width, scale)

    bchw = image_batch.permute(0, 3, 1, 2)
    try:
        resized = F.interpolate(
            bchw,
            size=(target_height, target_width),
            mode="bilinear",
            align_corners=False,
            antialias=True,
        )
    except TypeError:  # Older PyTorch builds do not expose the antialias argument.
        resized = F.interpolate(
            bchw,
            size=(target_height, target_width),
            mode="bilinear",
            align_corners=False,
        )
    resized = resized.permute(0, 2, 3, 1).contiguous()
    return resized, original_size, (target_width, target_height)


def _safe_call_int(owner: Any, method_name: str) -> int | None:
    method = getattr(owner, method_name, None)
    if not callable(method):
        return None
    try:
        return int(method())
    except Exception:
        return None


def _safe_free_memory(device: Any) -> int | None:
    try:
        return int(model_management.get_free_memory(device))
    except Exception:
        return None


def _device_type(device: Any) -> str:
    return str(getattr(device, "type", str(device).split(":", 1)[0])).lower()


def _current_model_device(patcher: Any) -> str:
    for owner in (patcher, getattr(patcher, "model", None)):
        if owner is None:
            continue
        method = getattr(owner, "current_loaded_device", None)
        if callable(method):
            try:
                value = method()
                if value is not None:
                    return str(value)
            except Exception:
                pass

    model = getattr(patcher, "model", None)
    device = getattr(model, "device", None)
    if device is not None:
        return str(device)

    parameters = getattr(model, "parameters", None)
    if callable(parameters):
        try:
            return str(next(parameters()).device)
        except Exception:
            pass
    return "unknown"


def _accelerator_name(device: Any) -> str:
    if _device_type(device) == "cuda" and torch.cuda.is_available():
        try:
            index = getattr(device, "index", None)
            if index is None:
                index = torch.cuda.current_device()
            return torch.cuda.get_device_name(index)
        except Exception:
            return "CUDA GPU"
    return str(device)


def _estimated_inference_memory(clip: Any, tokens: Any) -> int:
    estimator = getattr(getattr(clip, "cond_stage_model", None), "memory_estimation_function", None)
    patcher = getattr(clip, "patcher", None)
    device = getattr(patcher, "load_device", None)
    if not callable(estimator) or device is None:
        return 0
    try:
        return max(0, int(estimator(tokens, device=device)))
    except Exception:
        return 0


def _prefer_accelerator_residency(clip: Any, tokens: Any) -> _ResidencyInfo:
    patcher = getattr(clip, "patcher", None)
    if patcher is None:
        return _ResidencyInfo(
            execution_device="unknown",
            current_device="unknown",
            offload_device="unknown",
            residency="unknown",
            dynamic_vram=False,
            free_memory_before=None,
            loaded_memory=None,
            model_memory=None,
            accelerator_name="unknown",
            full_load_error="CLIP patcher is unavailable",
        )

    execution_device = getattr(patcher, "load_device", torch.device("cpu"))
    offload_device = getattr(patcher, "offload_device", torch.device("cpu"))
    free_before = _safe_free_memory(execution_device)
    dynamic_method = getattr(patcher, "is_dynamic", None)
    try:
        dynamic_vram = bool(dynamic_method()) if callable(dynamic_method) else False
    except Exception:
        dynamic_vram = False

    full_load_error: str | None = None
    if _device_type(execution_device) != "cpu":
        memory_required = _estimated_inference_memory(clip, tokens)
        try:
            model_management.load_models_gpu(
                [patcher],
                memory_required=memory_required,
                force_full_load=True,
            )
        except Exception as exc:
            full_load_error = str(exc)
            print(
                "[Caption Creator] Full accelerator residency was unavailable; "
                f"falling back to ComfyUI-managed dynamic loading: {exc}",
                flush=True,
            )
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            try:
                model_management.load_models_gpu(
                    [patcher],
                    memory_required=memory_required,
                )
            except Exception as fallback_exc:
                raise CaptionCreatorError(
                    "Failed to load the caption model onto the configured execution device "
                    f"{execution_device}: {fallback_exc}"
                ) from fallback_exc

    loaded_memory = _safe_call_int(patcher, "loaded_size")
    model_memory = _safe_call_int(patcher, "model_size")
    full_resident = bool(
        loaded_memory is not None
        and model_memory is not None
        and model_memory > 0
        and loaded_memory >= int(model_memory * 0.98)
    )

    if _device_type(execution_device) == "cpu":
        residency = "cpu"
    elif full_resident:
        residency = "full_accelerator"
        # The patcher may support dynamic loading, but it is not actively
        # offloading when the complete model is resident on the accelerator.
        dynamic_vram = False
    else:
        residency = "dynamic_accelerator_offload"

    current_device = _current_model_device(patcher)
    # Dynamic quantized patchers can report the storage device even when every
    # weight is resident on the execution device. Loaded-size accounting is the
    # more reliable indicator in that case.
    if full_resident and _device_type(execution_device) != "cpu":
        current_device = str(execution_device)

    return _ResidencyInfo(
        execution_device=str(execution_device),
        current_device=current_device,
        offload_device=str(offload_device),
        residency=residency,
        dynamic_vram=dynamic_vram,
        free_memory_before=free_before,
        loaded_memory=loaded_memory,
        model_memory=model_memory,
        accelerator_name=_accelerator_name(execution_device),
        full_load_error=full_load_error,
    )


def _format_mib(value: int | None) -> str:
    if value is None:
        return "unknown"
    return f"{value / (1024 * 1024):.0f} MiB"


def _log_residency(info: _ResidencyInfo, model_precision: str) -> None:
    print(
        "[Caption Creator] "
        f"precision={model_precision}, execution_device={info.execution_device}, "
        f"current_device={info.current_device}, offload_device={info.offload_device}, "
        f"residency={info.residency}, dynamic_vram={str(info.dynamic_vram).lower()}, "
        f"accelerator={info.accelerator_name}, "
        f"free_before={_format_mib(info.free_memory_before)}, "
        f"model_loaded={_format_mib(info.loaded_memory)}/{_format_mib(info.model_memory)}",
        flush=True,
    )


def _generated_token_count(generated_ids: Any) -> int:
    shape = getattr(generated_ids, "shape", None)
    if shape is not None:
        try:
            if len(shape) > 0:
                return int(shape[-1])
        except Exception:
            pass
    try:
        return int(len(generated_ids))
    except Exception:
        return 0


def _generate_one(
    clip: Any,
    image: Any,
    words: int,
    model_precision: str,
    *,
    log_device: bool,
) -> str:
    prompt = _build_prompt(words)

    try:
        with torch.inference_mode():
            try:
                tokens = clip.tokenize(
                    prompt,
                    image=image,
                    skip_template=False,
                    min_length=1,
                    thinking=False,
                )
            except TypeError as exc:
                raise CaptionCreatorError(
                    "Caption Creator requires a current ComfyUI tokenizer that supports "
                    "thinking=False for Qwen3-VL. Update ComfyUI."
                ) from exc

            residency = _prefer_accelerator_residency(clip, tokens)
            if log_device:
                _log_residency(residency, model_precision)

            started = time.perf_counter()
            try:
                generated_ids = clip.generate(
                    tokens,
                    max_length=_GENERATION_TOKEN_CEILING,
                    **_GENERATION_OPTIONS,
                )
            except TypeError as exc:
                raise CaptionCreatorError(
                    "Caption Creator requires a current ComfyUI generation API with sampling, "
                    "repetition_penalty, presence_penalty, and min_p support. Update ComfyUI."
                ) from exc
            duration = time.perf_counter() - started
            decoded_text = clip.decode(generated_ids)
    except CaptionCreatorError:
        raise
    except Exception as exc:
        raise CaptionCreatorError(f"Caption generation failed: {exc}") from exc

    if not isinstance(decoded_text, str):
        raise CaptionCreatorError(
            "The model decoder returned a non-text value instead of a caption."
        )
    if decoded_text == "":
        raise CaptionCreatorError("The model stopped before generating caption text.")

    token_count = _generated_token_count(generated_ids)
    hit_ceiling = token_count >= _GENERATION_TOKEN_CEILING
    print(
        "[Caption Creator] "
        f"generation_tokens={token_count}, duration={duration:.2f}s, "
        f"hit_ceiling={str(hit_ceiling).lower()}",
        flush=True,
    )
    return decoded_text


class CaptionCreator(io.ComfyNode):
    """Caption one image or every image in a batch with a local Qwen3-VL model."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="CaptionCreator",
            display_name="Caption Creator",
            category=IMAGE_CAPTION,
            description=(
                "Creates a factual caption for each input image with a native Qwen3-VL "
                "ConvRot text encoder. Thinking is disabled and decoded text is returned unchanged."
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
                    max=200,
                    step=1,
                    display_mode=io.NumberDisplay.slider,
                    tooltip=(
                        "Approximate words per caption, not a hard limit. Set to 0 for an "
                        "unrestricted detailed caption."
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
        words = _normalize_words(words)
        image_batch = _validate_image_batch(image)
        caption_batch, original_size, caption_size = _prepare_caption_image(image_batch)
        clip = await _load_clip(str(model_precision), bool(auto_download))

        print(
            f"[Caption Creator] image={original_size[0]}x{original_size[1]}, "
            f"caption_input={caption_size[0]}x{caption_size[1]}, "
            f"batch={int(caption_batch.shape[0])}",
            flush=True,
        )

        captions = [
            _generate_one(
                clip,
                caption_batch[index : index + 1],
                words,
                str(model_precision),
                log_device=index == 0,
            )
            for index in range(int(caption_batch.shape[0]))
        ]
        text = "\n".join(captions)
        return io.NodeOutput(text, ui={"captions": captions})


__all__ = [
    "CaptionCreator",
    "CaptionCreatorError",
]
