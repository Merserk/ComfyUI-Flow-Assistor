# Import other nodes.

try:
    from .camera_angle_control_node import NODE_CLASS_MAPPINGS as CAM_CLASSES, NODE_DISPLAY_NAME_MAPPINGS as CAM_DISPLAY
except ImportError:
    CAM_CLASSES, CAM_DISPLAY = {}, {}

try:
    from .prompt_queue_node import NODE_CLASS_MAPPINGS as QUEUE_CLASSES, NODE_DISPLAY_NAME_MAPPINGS as QUEUE_DISPLAY
except ImportError:
    QUEUE_CLASSES, QUEUE_DISPLAY = {}, {}

try:
    from .prompt_queue_folder_node import NODE_CLASS_MAPPINGS as FOLDER_CLASSES, NODE_DISPLAY_NAME_MAPPINGS as FOLDER_DISPLAY
except ImportError:
    FOLDER_CLASSES, FOLDER_DISPLAY = {}, {}

try:
    from .resolution_select_node import NODE_CLASS_MAPPINGS as RES_CLASSES, NODE_DISPLAY_NAME_MAPPINGS as RES_DISPLAY
except ImportError:
    RES_CLASSES, RES_DISPLAY = {}, {}

try:
    from .image_resolution_fit_node import NODE_CLASS_MAPPINGS as FIT_CLASSES, NODE_DISPLAY_NAME_MAPPINGS as FIT_DISPLAY
except ImportError:
    FIT_CLASSES, FIT_DISPLAY = {}, {}

try:
    from .multiplication_node import NODE_CLASS_MAPPINGS as MULT_CLASSES, NODE_DISPLAY_NAME_MAPPINGS as MULT_DISPLAY
except ImportError:
    MULT_CLASSES, MULT_DISPLAY = {}, {}

try:
    from .clean_gpu_node import NODE_CLASS_MAPPINGS as CLEAN_CLASSES, NODE_DISPLAY_NAME_MAPPINGS as CLEAN_DISPLAY
except ImportError:
    CLEAN_CLASSES, CLEAN_DISPLAY = {}, {}

try:
    from .bypass_node import NODE_CLASS_MAPPINGS as FLOW_CLASSES, NODE_DISPLAY_NAME_MAPPINGS as FLOW_DISPLAY
except ImportError:
    FLOW_CLASSES, FLOW_DISPLAY = {}, {}

# Any passthrough nodes
try:
    from .any_passthrough_nodes import NODE_CLASS_MAPPINGS as ANYPT_CLASSES, NODE_DISPLAY_NAME_MAPPINGS as ANYPT_DISPLAY
except ImportError:
    ANYPT_CLASSES, ANYPT_DISPLAY = {}, {}

# Delay node
try:
    from .delay_node import NODE_CLASS_MAPPINGS as DELAY_CLASSES, NODE_DISPLAY_NAME_MAPPINGS as DELAY_DISPLAY
except ImportError:
    DELAY_CLASSES, DELAY_DISPLAY = {}, {}

# Display text node
try:
    from .display_text_node import NODE_CLASS_MAPPINGS as DT_CLASSES, NODE_DISPLAY_NAME_MAPPINGS as DT_DISPLAY
except ImportError:
    DT_CLASSES, DT_DISPLAY = {}, {}

# CLIP Text Enrichment node
try:
    from .clip_text_enrichment_node import NODE_CLASS_MAPPINGS as ENRICH_CLASSES, NODE_DISPLAY_NAME_MAPPINGS as ENRICH_DISPLAY
except ImportError:
    ENRICH_CLASSES, ENRICH_DISPLAY = {}, {}

# Combine all mappings
NODE_CLASS_MAPPINGS = {
    **CAM_CLASSES,
    **QUEUE_CLASSES,
    **FOLDER_CLASSES,
    **RES_CLASSES,
    **FIT_CLASSES,
    **MULT_CLASSES,
    **CLEAN_CLASSES,
    **FLOW_CLASSES,
    **ANYPT_CLASSES,
    **DELAY_CLASSES,
    **DT_CLASSES,
    **ENRICH_CLASSES,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **CAM_DISPLAY,
    **QUEUE_DISPLAY,
    **FOLDER_DISPLAY,
    **RES_DISPLAY,
    **FIT_DISPLAY,
    **MULT_DISPLAY,
    **CLEAN_DISPLAY,
    **FLOW_DISPLAY,
    **ANYPT_DISPLAY,
    **DELAY_DISPLAY,
    **DT_DISPLAY,
    **ENRICH_DISPLAY,
}

WEB_DIRECTORY = "./web"

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]