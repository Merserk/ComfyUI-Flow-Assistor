<h1 align="center">
    ComfyUI-Flow-Assistor
    <br>
    <sub><sup><i>Essential utility nodes for ComfyUI</i></sup></sub>
</h1>

<p align="center">
  <img width="100%" alt="ComfyUI-Flow-Assistor" src="https://github.com/user-attachments/assets/c9306ce8-96b0-4535-91f7-144f2ac27840" />
</p>

<br>

# Get Started

## Install

1. Install [ComfyUI](https://github.com/comfyanonymous/ComfyUI).
2. Clone this repository into `ComfyUI/custom_nodes`:

   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/Merserk/ComfyUI-Flow-Assistor.git
   ```

3. Restart ComfyUI.

> **Requirements:** Python 3.10+ and a current ComfyUI build with the V3 node API (`comfy_api.latest`). Caption Creator additionally requires native `CLIPType.KREA2` and Qwen3-VL ConvRot support. Version `2.1.0` is V3-only.

All 26 nodes are organized under:

```text
flow-assistor/
├── diagnostics/
├── flow/
├── image/
│   └── caption/
├── loaders/
├── sampling/
├── text/
└── utils/
```

<br>

## 🛠️ The Nodes

### 1. 📝 Prompt Queue
**Output prompt lines in sequence.**

Paste a multi-line prompt list and receive the next usable line on every queue. Supports `empty`, `repeat_last`, and `loop`, plus reset, whitespace stripping, and empty-line skipping.

---

### 2. 📂 Prompt Queue (From Folder)
**Read prompt files one by one.**

Loads supported files from a selected folder in deterministic filename order and outputs both the file content and filename. Supports extension filters, reset, loop, empty, and hold-last behavior.

---

### 3. 🎥 Camera Angle Control
**Build consistent camera-direction prompts.**

Create natural, technical, or keyword-style descriptions from rotation, vertical position, subject distance, and focal length controls.

---

### 4. 🎨 CLIP Text Encode (Prompt Enrichment)
**CLIP encoding with 20 built-in style presets.**

Adds a selected preset—such as Cinematic, Anime, Cyberpunk, Line Art, Dark Fantasy, or White Background—to your prompt before creating conditioning.

---

### 5. 📺 Show Text
**Display incoming text directly on the graph.**

Useful for checking prompt queues, generated camera descriptions, filenames, and other string outputs without opening the console.

---

### 6. ✍️ Caption Creator
**Generate detailed captions from images with a local Qwen3-VL model.**

Accepts one image or an image batch and returns one precise caption per image, separated by newlines. Choose the `int8` or `int4` ConvRot model and set an approximate caption length from 1–300 words; `words = 0` requests an unrestricted detailed sentence.

Missing models can be downloaded automatically and are stored in:

```text
ComfyUI/models/text_encoders/flow-assistor/
```

Disable `auto_download` to manage the model files manually. Caption Creator checks for ComfyUI's native `CLIPType.KREA2` support and reports a clear upgrade error when the installed text-encoder loader is too old for the selected format.

---

### 7. 📐 Resolution Selector (Groups)
**Choose standard dimensions by megapixel group.**

Includes common aspect ratios from `0.25MP` through `4MP`, returns width, height, and an empty latent, and supports batch sizes up to 64.

---

### 8. 🖼️ Image Resolution Tools
**Inspect or fit image and latent dimensions.**

- **Image Resolution Fit** — Resizes an image toward a selected megapixel target while preserving aspect ratio.
- **Image Resolution Extractor** — Outputs width, height, matching latent, and the unchanged image.
- **Image Latent Resolution Extractor** — Reads the effective pixel resolution from latent samples.

---

### 9. 🖱️ Visual Marquee (Interactive)
**Pause, select, and process one image region.**

Opens an interactive crop selector in the browser and returns the cropped image, mask, and shared `TILE_DATA` metadata. Crops can remain at original size or be resized to a chosen maximum resolution.

---

### 10. 🧩 Tile Tools
**Support crop-and-merge workflows.**

- **Tile Manager (Crop)** — Preserves the current image, mask, and `TILE_DATA` workflow contract.
- **Tile Compositor (Merge)** — Places a processed tile back into the original image, automatically resizing it when needed and optionally feathering the edges.

---

### 11. ☁️ LoRA Online
**Load a LoRA directly from a URL.**

Accepts direct file links or Civitai model URLs, downloads asynchronously, applies the LoRA to the model, and can either keep the file or delete it after loading.

---

### 12. 💎 Detail Enhancer
**Adjust sampling to emphasize fine detail.**

- **Detail Enhancer (Ultimate)** — Wraps a sampler.
- **Detail Enhancer (Sigmas)** — Modifies a sigma schedule directly.

Both provide enhancement strength, texture boost, and start/end percentage controls.

---

### 13. 🔀 Any Passthrough
**Universal rerouting helpers.**

- **Any Passthrough (6 → 1)** — Returns the first connected non-null input.
- **Any Passthrough (1 → 6)** — Duplicates one input to six matching outputs.

---

### 14. 🎮 Flow Control (Sidecar Bypass)
**Control connected nodes without placing the controller in the data path.**

Use the frontend switches to change connected nodes between normal execution and bypass mode.

---

### 15. ⏱️ Add Delay
**Wait before passing data onward.**

Adds an asynchronous delay while preserving the connected data type. Useful for timing, interactive workflows, and debugging.

---

### 16. 🧹 VRAM/RAM Cleaner
**Run memory cleanup during a workflow.**

Passes the connected object through unchanged and provides three modes: clean the current object, unload other models, or unload everything.

---

### 17. ✖️ Multiplication (Dual & Latent)
**Scale dimensions and optional latent data.**

Multiplies two integer inputs by a shared factor and resizes an optional latent with the same multiplier.

---

### 18. 🐞 Debug Data (Any Input)
**Inspect almost any connected value.**

Outputs readable information such as Python type, tensor shape, dtype, device, image resolution, batch size, and latent pixel resolution.

---

### 19. 🔬 Precision Detectors
**Inspect active model precision at runtime.**

- **Detect Model Precision**
- **Detect CLIP Precision**
- **Detect VAE Precision**

These nodes report compute dtype, stored weight dtype, mixed precision, and supported quantized layouts when detectable.

<br>

## 🚀 Workflow Examples

### The Storyteller
Connect **Prompt Queue** to your text-conditioning workflow, set ComfyUI's batch count to the number of prompt lines, and generate each scene in order.

### Interactive Detail Refinement
Send an image through **Visual Marquee**, process the selected crop, then reconnect it to **Tile Compositor** with the original image and `tile_data`.

### Dynamic Upscaling
Extract width and height, pass them through **Multiplication**, and use the results for a proportional latent or image upscale.

<br>

## 🤝 Contributing

Ideas, bug reports, and pull requests are welcome. Please keep node IDs and workflow-facing input/output contracts stable whenever possible.

## 📄 License

MIT License. Precision Detector attribution is included in [`NOTICE`](NOTICE).
