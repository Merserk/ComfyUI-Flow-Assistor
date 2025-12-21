import os
import requests
import re
import folder_paths
import comfy.utils
import comfy.sd
import gc
import torch
import sys
import subprocess
from tqdm import tqdm
from aiohttp import web
from server import PromptServer

# --------------------------------------------------------------------------------
# API Route to Open Folder
# --------------------------------------------------------------------------------
def get_target_folder():
    lora_root = folder_paths.get_folder_paths("loras")[0]
    return os.path.join(lora_root, "Flow-Assistor-LoRA")

@PromptServer.instance.routes.post("/flow_assistor/open_lora_folder")
async def open_lora_folder_handler(request):
    target_dir = get_target_folder()
    
    # Create if doesn't exist so we don't error out
    os.makedirs(target_dir, exist_ok=True)

    try:
        if os.name == 'nt': # Windows
            os.startfile(target_dir)
        elif sys.platform == 'darwin': # macOS
            subprocess.Popen(['open', target_dir])
        else: # Linux
            subprocess.Popen(['xdg-open', target_dir])
        
        return web.json_response({"status": "success"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)


# --------------------------------------------------------------------------------
# Node Definition
# --------------------------------------------------------------------------------
class LoRAOnlineNode:
    """
    Downloads a LoRA from a URL (Civitai, Tensor.art, etc.) and applies it to the model.
    Automatically resolves Civitai Model Page URLs to Download URLs.
    """

    def __init__(self):
        # Fake browser headers to avoid 403 Forbidden
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": "https://civitai.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "url": ("STRING", {"default": "", "multiline": False}),
                "strength_model": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01}),
                # Renamed from hold_model to save_model
                "save_model": ("BOOLEAN", {"default": True, "label_on": "Save to Disk", "label_off": "Delete after Gen"}),
            },
            "optional": {
                "force_redownload": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "process"
    CATEGORY = "flow-assistor/loaders"

    def resolve_civitai_url(self, url):
        """
        Converts a Civitai Model Page URL -> Download URL via their Public API.
        """
        # Regex to find model ID from URL
        match = re.search(r'civitai\.com/models/(\d+)', url)
        
        if not match:
            return url # Not a model page URL, assume it's a direct link

        model_id = match.group(1)
        print(f"[LoRA Online] Detected Civitai Model ID: {model_id}")

        # check for specific version request in query string (?modelVersionId=...)
        version_match = re.search(r'modelVersionId=(\d+)', url)
        target_version_id = int(version_match.group(1)) if version_match else None

        api_url = f"https://civitai.com/api/v1/models/{model_id}"
        
        try:
            print(f"[LoRA Online] Querying API: {api_url}")
            r = requests.get(api_url, headers=self.headers, timeout=10)
            r.raise_for_status()
            data = r.json()

            if "modelVersions" not in data or len(data["modelVersions"]) == 0:
                print("[LoRA Online] Error: No model versions found in API response.")
                return url

            # Logic: Find specific version or default to the first (latest)
            selected_version = data["modelVersions"][0] # Default to latest
            
            if target_version_id:
                for v in data["modelVersions"]:
                    if v["id"] == target_version_id:
                        selected_version = v
                        break
            
            download_url = selected_version.get("downloadUrl")
            if download_url:
                print(f"[LoRA Online] Resolved Download URL: {download_url}")
                return download_url
            
        except Exception as e:
            print(f"[LoRA Online] API Resolution Warning: {e}. Falling back to original URL.")
        
        return url

    def get_filename_from_cd(self, cd):
        """Extract filename from Content-Disposition header."""
        if not cd:
            return None
        fname = re.findall(r'filename="?([^"]+)"?', cd)
        if len(fname) == 0:
            return None
        return fname[0]

    def download_file(self, url, dest_folder, force=False):
        # 1. Resolve URL if it's a Civitai Page
        final_url = self.resolve_civitai_url(url)

        session = requests.Session()
        session.headers.update(self.headers)
        
        try:
            # 2. Start Request (Stream=True to get headers first)
            print(f"[LoRA Online] Connecting to: {final_url}")
            with session.get(final_url, stream=True, allow_redirects=True, timeout=30) as response:
                response.raise_for_status()
                
                # 3. Determine Filename
                content_disposition = response.headers.get('content-disposition')
                filename = self.get_filename_from_cd(content_disposition)
                
                if not filename:
                    if "civitai.com" in final_url:
                        filename = response.url.split("/")[-1]
                        if "?" in filename: filename = filename.split("?")[0]
                    else:
                        filename = os.path.basename(final_url)
                    
                    if not filename or "." not in filename:
                        filename = "online_lora_unknown.safetensors"

                # Sanitize
                filename = re.sub(r'[\\/*?:"<>|]', "", filename)
                if not filename.endswith(".safetensors") and not filename.endswith(".pt"):
                    filename += ".safetensors"

                file_path = os.path.join(dest_folder, filename)

                # 4. Check if already exists
                if os.path.exists(file_path) and not force:
                    print(f"[LoRA Online] File exists, skipping download: {filename}")
                    return file_path

                # 5. Download Content
                total_size = int(response.headers.get('content-length', 0))
                print(f"[LoRA Online] Downloading {filename}...")
                
                with open(file_path, 'wb') as f, tqdm(
                    desc=filename,
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar:
                    for chunk in response.iter_content(chunk_size=8192):
                        size = f.write(chunk)
                        bar.update(size)
                        
                return file_path
                
        except Exception as e:
            print(f"[LoRA Online] Fatal Download Error: {e}")
            raise e

    def process(self, model, url, strength_model, save_model, force_redownload=False):
        if not url or not url.strip():
            print("[LoRA Online] No URL provided. Passing model through.")
            return (model,)

        target_dir = get_target_folder()
        os.makedirs(target_dir, exist_ok=True)

        try:
            file_path = self.download_file(url.strip(), target_dir, force=force_redownload)
        except Exception as e:
            print(f"!!! [LoRA Online] Failed to load LoRA: {e}")
            return (model,)
        
        # Load LoRA
        print(f"[LoRA Online] Loading LoRA: {os.path.basename(file_path)}")
        try:
            # We load the lora into memory
            lora = comfy.utils.load_torch_file(file_path, safe_load=True)
            # Apply it to the model (this merges weights, so we don't need 'lora' object afterwards)
            model_lora, _ = comfy.sd.load_lora_for_models(model, None, lora, strength_model, 0)
        except Exception as e:
            print(f"!!! [LoRA Online] File is corrupted or not a LoRA: {e}")
            return (model,)

        # CLEANUP LOGIC
        if not save_model:
            # 1. Delete the python object to remove the reference
            del lora
            
            # 2. Force Garbage Collection to release the OS file handle (Windows fix)
            gc.collect()
            if hasattr(torch, "cuda"):
                torch.cuda.empty_cache()

            # 3. Attempt deletion
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"[LoRA Online] Successfully deleted: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"[LoRA Online] Warning: Could not delete file (OS lock): {e}")

        return (model_lora,)

NODE_CLASS_MAPPINGS = {
    "LoRAOnlineNode": LoRAOnlineNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoRAOnlineNode": "LoRA Online",
}