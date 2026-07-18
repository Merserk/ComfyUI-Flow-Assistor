"""Image analysis, resolution, tiling, and interactive selection nodes."""

from .caption_creator import CaptionCreator
from .latent_resolution_extractor import ImageLatentResolutionExtractorNode
from .resolution_extractor import ImageResolutionExtractorNode
from .resolution_fit import ImageResolutionFitNode
from .resolution_selector import ResolutionSelectNode
from .tiling import TileCompositor, TileManager
from .visual_marquee import VisualMarqueeSelection

NODE_CLASSES = (
    CaptionCreator,
    ResolutionSelectNode,
    ImageResolutionFitNode,
    ImageResolutionExtractorNode,
    ImageLatentResolutionExtractorNode,
    TileManager,
    TileCompositor,
    VisualMarqueeSelection,
)

__all__ = [
    "CaptionCreator",
    "ResolutionSelectNode",
    "ImageResolutionFitNode",
    "ImageResolutionExtractorNode",
    "ImageLatentResolutionExtractorNode",
    "TileManager",
    "TileCompositor",
    "VisualMarqueeSelection",
    "NODE_CLASSES",
]
