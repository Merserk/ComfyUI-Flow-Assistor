"""Image, latent-resolution, tiling, and interactive selection nodes."""

from .latent_resolution_extractor import ImageLatentResolutionExtractorNode
from .resolution_extractor import ImageResolutionExtractorNode
from .resolution_fit import ImageResolutionFitNode
from .resolution_selector import ResolutionSelectNode
from .tiling import TileCompositor, TileManager
from .visual_marquee import VisualMarqueeSelection

NODE_CLASSES = (
    ResolutionSelectNode,
    ImageResolutionFitNode,
    ImageResolutionExtractorNode,
    ImageLatentResolutionExtractorNode,
    TileManager,
    TileCompositor,
    VisualMarqueeSelection,
)

__all__ = [
    "ResolutionSelectNode",
    "ImageResolutionFitNode",
    "ImageResolutionExtractorNode",
    "ImageLatentResolutionExtractorNode",
    "TileManager",
    "TileCompositor",
    "VisualMarqueeSelection",
    "NODE_CLASSES",
]
