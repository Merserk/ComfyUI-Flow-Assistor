"""Sampler and sigma-processing nodes."""

from .detail_enhance import UltimateDetailSamplerNode, UltimateDetailSigmasNode

NODE_CLASSES = (
    UltimateDetailSamplerNode,
    UltimateDetailSigmasNode,
)

__all__ = [
    "UltimateDetailSamplerNode",
    "UltimateDetailSigmasNode",
    "NODE_CLASSES",
]
