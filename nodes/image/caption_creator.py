"""Generate factual image captions with ComfyUI's native Qwen3-VL support."""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from dataclasses import dataclass
import gc
import os
import re
from pathlib import Path
from typing import Any

import aiohttp
import torch
import torch.nn.functional as F

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
_DOWNLOAD_HEADERS = {"User-Agent": "ComfyUI-Flow-Assistor/2.2 Caption-Creator"}

# This is an emergency guard against a model that never emits its stop token.
# It is intentionally fixed and is not derived from the requested word count.
_GENERATION_TOKEN_CEILING = 1024
_CAPTION_MAX_EDGE = 1024
_VISION_ALIGNMENT = 28  # Qwen patch_size (14) * merge_size (2).

_PRIMARY_GENERATION = {
    "do_sample": True,
    "temperature": 0.35,
    "top_k": 24,
    "top_p": 0.82,
    "min_p": 0.04,
    "repetition_penalty": 1.16,
    "presence_penalty": 0.12,
    "seed": 42,
}
_RETRY_GENERATION = {
    "do_sample": True,
    "temperature": 0.25,
    "top_k": 16,
    "top_p": 0.72,
    "min_p": 0.06,
    "repetition_penalty": 1.24,
    "presence_penalty": 0.22,
    "seed": 314159,
}

_API = ComfyAPI()
_MODEL_LOCK = asyncio.Lock()
_CACHED_MODEL_PATH: Path | None = None
_CACHED_CLIP: Any = None

_WORD_RE = re.compile(r"\b[\w'-]+\b", flags=re.UNICODE)
_SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+[\"')\]]*|$)", flags=re.DOTALL)
_END_PUNCTUATION_RE = re.compile(r"[.!?][\"')\]]*$")
_COMMON_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "there",
        "this",
        "to",
        "with",
    }
)


class CaptionCreatorError(RuntimeError):
    """Raised when Caption Creator cannot validate, load, or run its model."""


@dataclass(frozen=True)
class _GenerationResult:
    text: str
    token_count: int
    hit_ceiling: bool
    issues: tuple[str, ...]
    score: float


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


def _build_prompt(words: int, *, strict_retry: bool = False) -> str:
    words = _normalize_words(words)
    length_instruction = (
        "Include all useful clearly visible detail; there is no required word count."
        if words == 0
        else f"Use close to {words} words, but finish the current sentence naturally before stopping."
    )
    retry_instruction = (
        " Be especially concise: do not repeat any noun phrase, clause, sentence, or detail."
        if strict_retry
        else ""
    )
    return (
        "Write one factual image-caption paragraph using complete sentences. "
        "Describe only details directly visible in the image. Do not guess identity, exact location, "
        "intent, relationships, hidden events, or details that cannot be seen. "
        "Mention each visible detail once, without restating or rephrasing it. "
        f"{length_instruction}{retry_instruction} "
        "End after a complete sentence. Return only the caption, with no heading, label, analysis, "
        "or extra commentary."
    )


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


def _model_device(clip: Any) -> str:
    patcher = getattr(clip, "patcher", None)
    device = getattr(patcher, "load_device", None)
    if device is None:
        device = getattr(patcher, "current_device", None)
    return str(device if device is not None else "ComfyUI-managed/unknown")


def _normalized_words(text: str) -> list[str]:
    return [match.group(0).casefold() for match in _WORD_RE.finditer(text)]


def _normalize_fragment(text: str) -> str:
    return " ".join(_normalized_words(text))


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_RE.findall(text) if part.strip()]


def _find_repeated_ngram_start(text: str) -> int | None:
    matches = list(_WORD_RE.finditer(text))
    words = [match.group(0).casefold() for match in matches]
    if len(words) < 18:
        return None

    candidates: list[int] = []
    for ngram_size in range(12, 5, -1):
        positions: dict[tuple[str, ...], list[int]] = defaultdict(list)
        for index in range(len(words) - ngram_size + 1):
            key = tuple(words[index : index + ngram_size])
            positions[key].append(index)
        for occurrences in positions.values():
            non_overlapping: list[int] = []
            for index in occurrences:
                if not non_overlapping or index >= non_overlapping[-1] + ngram_size:
                    non_overlapping.append(index)
            if len(non_overlapping) >= 3:
                candidates.append(matches[non_overlapping[1]].start())
        if candidates:
            break
    return min(candidates) if candidates else None


def _quality_issues(text: str, *, hit_ceiling: bool = False) -> tuple[str, ...]:
    issues: list[str] = []
    words = _normalized_words(text)

    if hit_ceiling:
        issues.append("token_ceiling")
    if not _END_PUNCTUATION_RE.search(text.strip()):
        issues.append("incomplete_sentence")

    sentences = [_normalize_fragment(sentence) for sentence in _split_sentences(text)]
    substantial_sentences = [sentence for sentence in sentences if len(sentence.split()) >= 5]
    if len(substantial_sentences) != len(set(substantial_sentences)):
        issues.append("repeated_sentence")

    clauses = [
        _normalize_fragment(clause)
        for clause in re.split(r"[,;:]\s*", text)
        if len(_normalized_words(clause)) >= 6
    ]
    if len(clauses) != len(set(clauses)):
        issues.append("repeated_clause")

    if _find_repeated_ngram_start(text) is not None:
        issues.append("repeated_ngram")

    if len(words) >= 55:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.34:
            issues.append("low_vocabulary_diversity")

        content_counts = Counter(word for word in words if word not in _COMMON_WORDS and len(word) > 2)
        if content_counts:
            most_common_count = content_counts.most_common(1)[0][1]
            if most_common_count >= 9 and most_common_count / len(words) > 0.11:
                issues.append("excessive_word_repetition")

    return tuple(dict.fromkeys(issues))


def _remove_duplicate_sentences(text: str) -> str:
    seen: set[str] = set()
    output: list[str] = []
    for sentence in _split_sentences(text):
        normalized = _normalize_fragment(sentence)
        if len(normalized.split()) >= 5 and normalized in seen:
            continue
        if normalized:
            seen.add(normalized)
        output.append(sentence)
    return " ".join(output).strip()


def _trim_at_duplicate_clause(text: str) -> str:
    parts = re.split(r"((?:,|;|:)\s*)", text)
    seen: set[str] = set()
    output: list[str] = []
    index = 0
    while index < len(parts):
        clause = parts[index]
        separator = parts[index + 1] if index + 1 < len(parts) else ""
        normalized = _normalize_fragment(clause)
        if len(normalized.split()) >= 6 and normalized in seen:
            break
        if normalized:
            seen.add(normalized)
        output.append(clause)
        output.append(separator)
        index += 2
    return "".join(output).rstrip(" ,;:")


def _finish_at_sentence_boundary(text: str) -> str:
    text = text.strip(" ,;:")
    if not text:
        return text
    if _END_PUNCTUATION_RE.search(text):
        return text

    boundaries = list(re.finditer(r"[.!?][\"')\]]*", text))
    if boundaries:
        end = boundaries[-1].end()
        prefix = text[:end].strip()
        if len(_normalized_words(prefix)) >= max(5, int(len(_normalized_words(text)) * 0.4)):
            return prefix

    # A usable caption without punctuation is preferable to an empty output.
    return f"{text}."


def _sanitize_candidate(text: str) -> str:
    text = _clean_text(text)
    # Remove exact sentence/clause loops before the broader n-gram fallback so a
    # repeated clause is cut at its delimiter rather than in the middle of words.
    text = _remove_duplicate_sentences(text)
    text = _trim_at_duplicate_clause(text)
    repeated_start = _find_repeated_ngram_start(text)
    if repeated_start is not None:
        text = text[:repeated_start].rstrip(" ,;:")
    text = " ".join(text.split()).strip()
    text = _finish_at_sentence_boundary(text)
    if not text:
        raise CaptionCreatorError("The model generated only repeated or unusable text.")
    return text


def _candidate_score(text: str, issues: tuple[str, ...], words_target: int, hit_ceiling: bool) -> float:
    score = 100.0 - 24.0 * len(issues)
    if hit_ceiling:
        score -= 20.0
    if _END_PUNCTUATION_RE.search(text):
        score += 8.0
    word_count = len(_normalized_words(text))
    if words_target > 0 and word_count > 0:
        relative_distance = abs(word_count - words_target) / max(words_target, 1)
        score -= min(12.0, relative_distance * 8.0)
    return score


def _generate_attempt(
    clip: Any,
    image: Any,
    prompt: str,
    generation_options: dict[str, Any],
    words_target: int,
) -> _GenerationResult:
    try:
        with torch.inference_mode():
            tokens = clip.tokenize(
                prompt,
                image=image,
                skip_template=False,
                min_length=1,
                thinking=False,
            )
            generated_ids = clip.generate(
                tokens,
                max_length=_GENERATION_TOKEN_CEILING,
                **generation_options,
            )
            raw_text = _clean_text(clip.decode(generated_ids))
    except CaptionCreatorError:
        raise
    except TypeError as exc:
        raise CaptionCreatorError(
            "Caption Creator requires a current ComfyUI generation API with sampling, "
            "repetition_penalty, presence_penalty, and min_p support. Update ComfyUI."
        ) from exc
    except Exception as exc:
        raise CaptionCreatorError(f"Caption generation failed: {exc}") from exc

    token_count = len(generated_ids)
    hit_ceiling = token_count >= _GENERATION_TOKEN_CEILING
    raw_issues = _quality_issues(raw_text, hit_ceiling=hit_ceiling)
    sanitized = _sanitize_candidate(raw_text)
    sanitized_issues = _quality_issues(sanitized, hit_ceiling=hit_ceiling)
    issues = tuple(dict.fromkeys((*raw_issues, *sanitized_issues)))
    return _GenerationResult(
        text=sanitized,
        token_count=token_count,
        hit_ceiling=hit_ceiling,
        issues=issues,
        score=_candidate_score(sanitized, issues, words_target, hit_ceiling),
    )


def _needs_retry(result: _GenerationResult) -> bool:
    retry_reasons = {
        "token_ceiling",
        "incomplete_sentence",
        "repeated_sentence",
        "repeated_clause",
        "repeated_ngram",
        "low_vocabulary_diversity",
        "excessive_word_repetition",
    }
    return any(issue in retry_reasons for issue in result.issues)


def _generate_one(clip: Any, image: Any, words: int) -> str:
    primary = _generate_attempt(
        clip,
        image,
        _build_prompt(words),
        _PRIMARY_GENERATION,
        words,
    )
    if not _needs_retry(primary):
        return primary.text

    print(
        "[Caption Creator] Retrying a degenerated caption ("
        + ", ".join(primary.issues)
        + ").",
        flush=True,
    )
    retry = _generate_attempt(
        clip,
        image,
        _build_prompt(words, strict_retry=True),
        _RETRY_GENERATION,
        words,
    )
    return max((primary, retry), key=lambda candidate: candidate.score).text


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
                "ConvRot text encoder. The word setting is an approximate target, not a cutoff."
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
            f"[Caption Creator] precision={model_precision}, device={_model_device(clip)}, "
            f"image={original_size[0]}x{original_size[1]}, "
            f"caption_input={caption_size[0]}x{caption_size[1]}",
            flush=True,
        )

        captions = [
            _generate_one(clip, caption_batch[index : index + 1], words)
            for index in range(int(caption_batch.shape[0]))
        ]
        text = "\n".join(captions)
        return io.NodeOutput(text, ui={"text": captions})


__all__ = [
    "CaptionCreator",
    "CaptionCreatorError",
]
