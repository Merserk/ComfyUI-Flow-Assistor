# Import other nodes. Using try-except blocks to prevent crashes if
# sibling files are missing during testing/installation.

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

# Combine all mappings
NODE_CLASS_MAPPINGS = {
    **CAM_CLASSES, 
    **QUEUE_CLASSES, 
    **FOLDER_CLASSES, 
    **RES_CLASSES,
    **FIT_CLASSES,
    **MULT_CLASSES,
    **CLEAN_CLASSES
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **CAM_DISPLAY, 
    **QUEUE_DISPLAY, 
    **FOLDER_DISPLAY, 
    **RES_DISPLAY,
    **FIT_DISPLAY,
    **MULT_DISPLAY,
    **CLEAN_DISPLAY
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']