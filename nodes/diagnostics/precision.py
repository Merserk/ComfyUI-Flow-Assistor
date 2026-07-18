"""Runtime precision inspection nodes for ComfyUI.

The detection logic is derived from ComfyUI-Precision-Detector and adapted to
ComfyUI's V3 extension API while preserving the original node identifiers and report format.
"""

import re

import torch
from comfy_api.latest import io
from ..categories import DIAGNOSTICS


_DTYPE_LABELS = {
    torch.float64: "FP64",
    torch.float32: "FP32",
    torch.float16: "FP16",
    torch.bfloat16: "BF16",
    torch.complex128: "COMPLEX128",
    torch.complex64: "COMPLEX64",
    torch.int64: "INT64",
    torch.int32: "INT32",
    torch.int16: "INT16",
    torch.int8: "INT8",
    torch.uint64: "UINT64",
    torch.uint32: "UINT32",
    torch.uint16: "UINT16",
    torch.uint8: "UINT8",
    torch.bool: "BOOL",
}

for _torch_name, _label in (
    ("complex32", "COMPLEX32"),
    ("float4_e2m1fn_x2", "FP4 E2M1FN (packed x2)"),
    ("float8_e4m3fn", "FP8 E4M3FN"),
    ("float8_e4m3fnuz", "FP8 E4M3FNUZ"),
    ("float8_e5m2", "FP8 E5M2"),
    ("float8_e5m2fnuz", "FP8 E5M2FNUZ"),
    ("float8_e8m0fnu", "FP8 E8M0FNU"),
):
    if hasattr(torch, _torch_name):
        _DTYPE_LABELS[getattr(torch, _torch_name)] = _label


def _dtype_label(dtype):
    if dtype is None:
        return None
    try:
        if dtype in _DTYPE_LABELS:
            return _DTYPE_LABELS[dtype]
    except TypeError:
        pass

    name = str(dtype).removeprefix("torch.")
    integer_match = re.fullmatch(r"(u?int)(\d+)", name)
    if integer_match:
        return f"{integer_match.group(1).upper()}{integer_match.group(2)}"

    packed_match = re.fullmatch(r"(q?u?int|bits)(\d+)(?:x(\d+))?", name)
    if packed_match:
        base, bits, count = packed_match.groups()
        label = f"{base.upper()}{bits}"
        return f"{label} (packed x{count})" if count else label

    float_match = re.fullmatch(r"float(\d+)(?:_(.+))?", name)
    if float_match:
        bits, variant = float_match.groups()
        label = f"FP{bits}"
        if variant:
            label = f"{label} {variant.upper().replace('_X', ' (packed x')}"
            if " (packed x" in label:
                label += ")"
        return label

    complex_match = re.fullmatch(r"complex(\d+)", name)
    if complex_match:
        return f"COMPLEX{complex_match.group(1)}"

    return name.upper().replace("_", " ")


def _quantization_base(value):
    name = str(value)
    normalized = re.sub(r"[^a-z0-9]", "", name.lower())
    if "convrotw4a4" in normalized or normalized == "w4a4":
        return "INT4 / ConvRot W4A4"
    if "nvfp4" in normalized:
        return "NVFP4"
    if "mxfp8" in normalized:
        return "MXFP8"
    if "tensorwiseint8" in normalized or normalized == "int8tensorwise":
        return "INT8"
    if "e4m3fnuz" in normalized:
        return "FP8 E4M3FNUZ"
    if "e5m2fnuz" in normalized:
        return "FP8 E5M2FNUZ"
    if "e4m3fn" in normalized or "e4m3" in normalized:
        return "FP8 E4M3FN"
    if "e5m2" in normalized:
        return "FP8 E5M2"
    if "e8m0" in normalized:
        return "FP8 E8M0FNU"
    if normalized in {"tensorcorefp8layout", "fp8", "float8"}:
        return "FP8 E4M3FN"
    if "fp8" in normalized or "float8" in normalized:
        return "FP8"
    if "nf4" in normalized:
        return "NF4"
    if "e2m1" in normalized or "fp4" in normalized or "float4" in normalized:
        return "FP4 E2M1FN"
    if "int4" in normalized:
        return "INT4"
    if "int8" in normalized:
        return "INT8"
    return name


def _safe_attribute(obj, attribute):
    try:
        return getattr(obj, attribute, None)
    except Exception:
        return None


def _value_name(value):
    return value.__name__ if isinstance(value, type) else str(value)


def _quantization_facts(obj):
    raw_values = set()
    layout_names = set()
    for attribute in ("quant_format", "layout_type", "layout_cls", "_layout_cls"):
        value = _safe_attribute(obj, attribute)
        if value is None:
            continue
        name = _value_name(value)
        raw_values.add(name)
        if "layout" in attribute.lower() or "layout" in name.lower():
            layout_names.add(name)

    if not raw_values:
        return {}

    facts = {_quantization_base(value): set() for value in raw_values}
    details = {f"layout {name}" for name in layout_names}

    storage_dtype = _safe_attribute(obj, "storage_dtype")
    storage_label = _dtype_label(storage_dtype)
    if storage_label is not None:
        if "INT4 / ConvRot W4A4" in facts and storage_label == "INT8":
            details.add("storage INT8 (packed INT4)")
        else:
            details.add(f"storage {storage_label}")

    logical_label = _dtype_label(_safe_attribute(obj, "dtype"))
    if logical_label is not None and logical_label != storage_label:
        details.add(f"logical {logical_label}")

    params = _safe_attribute(obj, "params")
    if params is None:
        params = _safe_attribute(obj, "_params")
    linear_dtype = _safe_attribute(params, "linear_dtype")
    if linear_dtype is not None:
        details.add(f"kernel {_dtype_label(linear_dtype) or str(linear_dtype).upper()}")

    for value in facts.values():
        value.update(details)
    return facts


def _merge_quantization_facts(destination, source):
    for quant_format, details in source.items():
        destination.setdefault(quant_format, set()).update(details)


def _runtime_weight_info(module):
    if not isinstance(module, torch.nn.Module):
        return set(), {}

    weight_formats = set()
    quantization = {}

    for parameter in module.parameters():
        parameter_facts = _quantization_facts(parameter)
        if parameter_facts:
            weight_formats.update(parameter_facts)
            _merge_quantization_facts(quantization, parameter_facts)
        else:
            label = _dtype_label(parameter.dtype)
            if label is not None:
                weight_formats.add(label)

    for child in module.modules():
        child_facts = _quantization_facts(child)
        weight_formats.update(child_facts)
        _merge_quantization_facts(quantization, child_facts)

    return weight_formats, quantization


def _format_weight_formats(formats):
    if not formats:
        return "UNKNOWN (no runtime parameters exposed)"
    values = sorted(formats)
    if len(values) == 1:
        return values[0]
    return f"Mixed ({', '.join(values)})"


def _format_quantization(quantization):
    if not quantization:
        return "None"
    values = []
    for quant_format in sorted(quantization):
        details = sorted(quantization[quant_format])
        values.append(
            f"{quant_format} ({'; '.join(details)})" if details else quant_format
        )
    return ", ".join(values)


def _device_label(device):
    return "UNKNOWN" if device is None else str(device)


def _manual_cast_policy(patcher):
    object_patches = getattr(patcher, "object_patches", None)
    if isinstance(object_patches, dict) and "manual_cast_dtype" in object_patches:
        return object_patches["manual_cast_dtype"], True, True

    model = getattr(patcher, "model", None)
    if model is not None and hasattr(model, "manual_cast_dtype"):
        return model.manual_cast_dtype, True, False

    return None, False, False


def _model_active_dtype(patcher):
    model = getattr(patcher, "model", None)
    manual_cast, manual_cast_exposed, is_override = _manual_cast_policy(patcher)
    if manual_cast is not None:
        return manual_cast, manual_cast, manual_cast_exposed

    if model is not None and not is_override:
        get_dtype_inference = getattr(model, "get_dtype_inference", None)
        if callable(get_dtype_inference):
            inference_dtype = get_dtype_inference()
            if inference_dtype is not None:
                return inference_dtype, manual_cast, manual_cast_exposed

    if model is not None:
        get_dtype = getattr(model, "get_dtype", None)
        if callable(get_dtype):
            weight_dtype = get_dtype()
            if weight_dtype is not None:
                return weight_dtype, manual_cast, manual_cast_exposed

    model_dtype = getattr(patcher, "model_dtype", None)
    if callable(model_dtype):
        weight_dtype = model_dtype()
        if weight_dtype is not None:
            return weight_dtype, manual_cast, manual_cast_exposed

    return None, manual_cast, manual_cast_exposed


def _cast_policy_label(dtype, exposed):
    if not exposed:
        return "UNKNOWN (not exposed by input object)"
    if dtype is None:
        return "None (runtime weights used directly)"
    return _dtype_label(dtype)


def model_precision_report(model):
    root_model = getattr(model, "model", None)
    active_dtype, manual_cast, manual_cast_exposed = _model_active_dtype(model)
    weight_formats, quantization = _runtime_weight_info(root_model)

    active = _dtype_label(active_dtype)
    if active is None:
        active = "UNKNOWN (input does not expose a ComfyUI inference dtype)"

    return "\n".join((
        f"Active compute: {active}",
        f"Runtime weights: {_format_weight_formats(weight_formats)}",
        f"Quantization: {_format_quantization(quantization)}",
        f"Manual cast: {_cast_policy_label(manual_cast, manual_cast_exposed)}",
        f"Load device: {_device_label(getattr(model, 'load_device', None))}",
        f"Offload device: {_device_label(getattr(model, 'offload_device', None))}",
    ))


def clip_precision_report(clip):
    patcher = getattr(clip, "patcher", None)
    root_model = getattr(clip, "cond_stage_model", None)
    if root_model is None and patcher is not None:
        root_model = getattr(patcher, "model", None)

    active_dtype, manual_cast, manual_cast_exposed = _model_active_dtype(patcher)
    weight_formats, quantization = _runtime_weight_info(root_model)

    active = _dtype_label(active_dtype)
    if active is None:
        active = "UNKNOWN (input does not expose a ComfyUI text-encoder compute dtype)"

    return "\n".join((
        f"Active compute: {active}",
        f"Runtime weights: {_format_weight_formats(weight_formats)}",
        f"Quantization: {_format_quantization(quantization)}",
        f"Manual cast: {_cast_policy_label(manual_cast, manual_cast_exposed)}",
        f"Load device: {_device_label(getattr(patcher, 'load_device', None))}",
        f"Offload device: {_device_label(getattr(patcher, 'offload_device', None))}",
    ))


def vae_precision_report(vae):
    root_model = getattr(vae, "first_stage_model", None)
    patcher = getattr(vae, "patcher", None)
    active_dtype = getattr(vae, "vae_dtype", None)
    weight_formats, quantization = _runtime_weight_info(root_model)

    active = _dtype_label(active_dtype)
    if active is None:
        active = "UNKNOWN (input does not expose vae_dtype)"

    output_dtype = None
    vae_output_dtype = getattr(vae, "vae_output_dtype", None)
    if callable(vae_output_dtype):
        output_dtype = vae_output_dtype()

    return "\n".join((
        f"Active compute: {active}",
        f"Runtime weights: {_format_weight_formats(weight_formats)}",
        f"Quantization: {_format_quantization(quantization)}",
        f"Manual cast: None (VAE module loaded as {active})",
        f"Output tensor: {_dtype_label(output_dtype) or 'UNKNOWN'}",
        f"Load device: {_device_label(getattr(vae, 'device', getattr(patcher, 'load_device', None)))}",
        f"Offload device: {_device_label(getattr(patcher, 'offload_device', None))}",
    ))


class RuntimePrecisionModel(io.ComfyNode):
    """Report diffusion-model compute, weight, quantization, and device details."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="RuntimePrecisionModel",
            display_name="Detect Model Precision",
            category=DIAGNOSTICS,
            description="Reports the diffusion model precision policy selected by ComfyUI.",
            inputs=[io.Model.Input("model")],
            outputs=[io.String.Output(display_name="precision_report")],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, model) -> io.NodeOutput:
        report = model_precision_report(model)
        return io.NodeOutput(report, ui={"text": [report]})


class RuntimePrecisionCLIP(io.ComfyNode):
    """Report CLIP/text-encoder compute, weight, quantization, and device details."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="RuntimePrecisionCLIP",
            display_name="Detect CLIP Precision",
            category=DIAGNOSTICS,
            description="Reports the CLIP/text-encoder precision policy selected by ComfyUI.",
            inputs=[io.Clip.Input("clip")],
            outputs=[io.String.Output(display_name="precision_report")],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, clip) -> io.NodeOutput:
        report = clip_precision_report(clip)
        return io.NodeOutput(report, ui={"text": [report]})


class RuntimePrecisionVAE(io.ComfyNode):
    """Report VAE compute, weight, output, quantization, and device details."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="RuntimePrecisionVAE",
            display_name="Detect VAE Precision",
            category=DIAGNOSTICS,
            description="Reports the VAE precision policy selected by ComfyUI.",
            inputs=[io.Vae.Input("vae")],
            outputs=[io.String.Output(display_name="precision_report")],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, vae) -> io.NodeOutput:
        report = vae_precision_report(vae)
        return io.NodeOutput(report, ui={"text": [report]})


__all__ = [
    "RuntimePrecisionModel",
    "RuntimePrecisionCLIP",
    "RuntimePrecisionVAE",
    "model_precision_report",
    "clip_precision_report",
    "vae_precision_report",
]
