import os
from typing import Dict, Any, Tuple, List

class PromptQueueFromFolder:
    """
    A node that scans a local folder for text files (.txt, .json, etc.)
    and outputs their content one by one as a queue.
    """

    def __init__(self):
        # Stores state: current index, last folder path, etc.
        self._state: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {
                    "default": "C:/Prompts", 
                    "multiline": False
                }),
            },
            "optional": {
                # Extensions to look for, comma separated
                "extensions": ("STRING", {"default": "txt, json"}),
                
                # What to do when all files are read
                "on_end": (["empty", "loop", "hold_last"], {"default": "empty"}),
                
                # Change this to force a reset to the first file
                "reset_trigger": ("INT", {"default": 0, "min": 0, "max": 2**31 - 1}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt_text", "filename")
    FUNCTION = "next_file_content"
    CATEGORY = "flow-assistor"

    # We want this node to update on every run
    def IS_CHANGED(self, **kwargs):
        return float("nan")

    def _get_state(self, unique_id: str) -> Dict[str, Any]:
        if unique_id not in self._state:
            self._state[unique_id] = {
                "index": 0,
                "cached_files": [],
                "last_folder": None,
                "last_reset": None,
            }
        return self._state[unique_id]

    def _get_files(self, folder_path: str, extensions: str) -> List[str]:
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return []
        
        # Clean up extensions list (e.g., "txt, json" -> ['.txt', '.json'])
        ext_list = [f".{e.strip().lstrip('.')}" for e in extensions.split(",") if e.strip()]
        if not ext_list:
            ext_list = ['.txt']

        files = []
        try:
            for f in os.listdir(folder_path):
                # Check extension
                _, ext = os.path.splitext(f)
                if ext.lower() in ext_list:
                    files.append(f)
        except Exception as e:
            print(f"[PromptQueueFromFolder] Error listing files: {e}")
            return []

        # Sort alphabetically so 1.txt comes before 2.txt
        files.sort()
        return files

    def next_file_content(
        self,
        folder_path: str,
        extensions: str = "txt, json",
        on_end: str = "empty",
        reset_trigger: int = 0,
        unique_id: str = "",
    ) -> Tuple[str, str]:
        
        st = self._get_state(unique_id)

        # Check if folder path changed or reset trigger changed -> Reset
        if st["last_folder"] != folder_path or st["last_reset"] != reset_trigger:
            st["cached_files"] = self._get_files(folder_path, extensions)
            st["index"] = 0
            st["last_folder"] = folder_path
            st["last_reset"] = reset_trigger
            print(f"[PromptQueueFromFolder] Folder scanned: {len(st['cached_files'])} files found")

        files = st["cached_files"]
        count = len(files)

        # Handle empty folder
        if count == 0:
            return ("", "no_files_found")

        idx = st["index"]

        # Handle End of Queue Logic
        if idx >= count:
            if on_end == "loop":
                idx = 0
                st["index"] = 0
            elif on_end == "hold_last":
                idx = count - 1
            else:  # empty
                return ("", "end_of_list")

        # Get file and read content
        filename = files[idx]
        full_path = os.path.join(folder_path, filename)
        
        content = ""
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            content = f"Error reading file: {str(e)}"
            print(f"[PromptQueueFromFolder] Error reading {filename}: {e}")

        # Prepare index for next run
        next_idx = st["index"] + 1
        
        # Logic to advance index specifically for the NEXT run
        if next_idx >= count:
            if on_end == "loop":
                st["index"] = 0
            elif on_end == "hold_last":
                st["index"] = count - 1  # Keep it at the end
            else:
                st["index"] = count  # Move past end so next time it returns empty
        else:
            st["index"] = next_idx

        return (content, filename)

NODE_CLASS_MAPPINGS = {
    "PromptQueueFromFolder": PromptQueueFromFolder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptQueueFromFolder": "Prompt Queue (From Folder)",
}