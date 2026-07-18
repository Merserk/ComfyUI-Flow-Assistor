"""CLIP text encoding with built-in enrichment presets."""

from comfy_api.latest import io
from ..categories import TEXT


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


class CLIPTextEncodePromptEnrichment(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="CLIPTextEncodePromptEnrichment",
            display_name="CLIP Text Encode (Prompt Enrichment)",
            category=TEXT,
            inputs=[
                io.Clip.Input("clip"),
                io.String.Input("text", multiline=True, dynamic_prompts=True, default=""),
                io.Combo.Input("preset", options=list(PRESETS), default="None"),
            ],
            outputs=[io.Conditioning.Output()],
        )

    @classmethod
    def execute(cls, clip, text, preset) -> io.NodeOutput:
        final_prompt = str(text).strip() + PRESETS.get(str(preset), "")
        tokens = clip.tokenize(final_prompt)
        conditioning, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
        return io.NodeOutput([[conditioning, {"pooled_output": pooled}]])


__all__ = ["CLIPTextEncodePromptEnrichment", "PRESETS"]
