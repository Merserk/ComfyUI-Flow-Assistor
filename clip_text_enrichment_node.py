import torch

class CLIPTextEncodePromptEnrichment:
    """
    A CLIP Text Encode node that includes a built-in library of style presets.
    It appends high-quality descriptors to the end of the user's prompt 
    before encoding to conditioning.
    """

    def __init__(self):
        pass

    # The library of presets. 
    # Starts with ", " to ensure separation from the main prompt.
    PRESETS = {
        "None": "",
        "Anime Style": ", masterpiece, best quality, anime key visual, vibrant colors, crisp lines, high fidelity, 4k resolution",
        "Photographic": ", photorealistic, raw photo, 8k uhd, dslr, soft lighting, high quality, film grain, Fujifilm XT3",
        "Cinematic": ", cinematic lighting, movie still, 70mm, anamorphic lens, depth of field, color graded, ray tracing, epic composition",
        "Digital Art": ", digital art, trending on artstation, detailed digital painting, concept art, sharp focus, illustration, vivid colors",
        "Cyberpunk": ", cyberpunk, neon lights, synthwave, futuristic, high tech, dark atmosphere, chromatic aberration, night city",
        "Fantasy Painting": ", oil painting, fantasy art, intricate details, magical atmosphere, texture, epic composition, golden hour, matte painting",
        "Monochrome/Noir": ", black and white, noir, high contrast, dramatic lighting, monochrome photography, shadows, film noir",
        "3D Render": ", 3d render, octane render, unreal engine 5, physically based rendering, studio lighting, hyper detailed, 8k",
        "Vintage Film": ", analog film, faded film, kodak portra 400, grain, vintage aesthetic, polaroid, light leak, nostalgic, lo-fi",
        "Dark Fantasy": ", dark fantasy, gothic atmosphere, eldritch, gloomy, ominous, masterpiece, intricate details, nightmare, horror theme",
        "Line Art / Manga": ", manga style, monochrome, ink sketch, line art, hatching, sharp lines, high contrast, graphic novel, highly detailed",
        "Architecture / Interior": ", architectural photography, modern interior, interior design, unreal engine 5, ray tracing, ambient occlusion, luxury, bright",
        "Crisp / Sharp Focus": ", sharp focus, highly detailed, crisp lines, 8k, hdr, distinct features, high contrast, hyperdetailed",
        "Huge Scene / Epic Scale": ", wide angle, establishing shot, massive scale, panoramic view, epic atmosphere, distant horizon, grand scenery, matte painting",
        "White Background / Asset": ", simple white background, no background, isolated subject, product shot, studio lighting, clean background, minimal",
        "Macro / Extreme Close-up": ", macro photography, extreme close-up, depth of field, bokeh, intricate textures, detailed iris, magnification",
        "Vibrant / Pop Colors": ", vibrant colors, vivid saturation, colorful, neon accents, high contrast, psychedelic, bright, rainbow",
        "Pastel / Soft / Dreamy": ", pastel colors, soft lighting, dreamy, kawaii, light colors, low contrast, ethereal, watercolor style",
        "Low Key / Dark Mood": ", low key lighting, dark atmosphere, mysterious, shadows, silhouette, rim lighting, chiaroscuro, moody",
    }

    @classmethod
    def INPUT_TYPES(cls):
        # Convert dictionary keys to a list for the dropdown
        # Sorting guarantees a consistent order in the UI
        preset_list = list(cls.PRESETS.keys())
        
        return {
            "required": {
                "clip": ("CLIP", ),
                "text": ("STRING", {
                    "multiline": True, 
                    "dynamicPrompts": True, 
                    "default": ""
                }),
                "preset": (preset_list, {"default": "None"}),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    FUNCTION = "encode_with_enrichment"
    CATEGORY = "flow-assistor"

    def encode_with_enrichment(self, clip, text, preset):
        # 1. Get the enrichment string
        enrichment = self.PRESETS.get(preset, "")
        
        # 2. Combine prompts
        # We strip the original text to remove trailing whitespace before appending
        final_prompt = text.strip() + enrichment
        
        # 3. Standard CLIP Encoding Logic
        # This mirrors the internal logic of the default CLIPTextEncode node
        tokens = clip.tokenize(final_prompt)
        cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
        
        # Output format required by ComfyUI
        return ([[cond, {"pooled_output": pooled}]], )

NODE_CLASS_MAPPINGS = {
    "CLIPTextEncodePromptEnrichment": CLIPTextEncodePromptEnrichment,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CLIPTextEncodePromptEnrichment": "CLIP Text Encode (Prompt Enrichment)",
}