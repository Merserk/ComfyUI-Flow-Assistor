<h1 align="center">
    ComfyUI-Flow-Assistor
    <br>
    <sub><sup><i>Essential utility nodes for ComfyUI</i></sup></sub>
</h1>

<p align="center">
  <img width="100%" alt="image" src="https://github.com/user-attachments/assets/c9306ce8-96b0-4535-91f7-144f2ac27840" />
</p>

<br>

# Get Started

## Install

1. Install the great [ComfyUI](https://github.com/comfyanonymous/ComfyUI).
2. Clone this repo into `custom_nodes`:
    ```bash
    cd ComfyUI/custom_nodes
    git clone https://github.com/Merserk/ComfyUI-Flow-Assistor.git
    ```
3. Start up ComfyUI.

<br>

## 🛠️ The Nodes

### 1. 📝 Prompt Queue
**Iterate through prompt lines one by one.**

Instead of randomizing a list, this node strictly follows the order of your text. It is perfect for testing specific prompt variations or storytelling sequences.

> **How it works:**  
> Paste a multi-line list of prompts. Every time you queue a generation, the node outputs the *next* line in the list.

<details>
<summary><b>🔻 Click for Parameters & Features</b></summary>

| Parameter | Description |
| :--- | :--- |
| **Prompts** | The multi-line text input. |
| **On End** | Behavior when the list finishes: `empty` (stop outputting), `repeat_last` (keep sending the last line), or `loop` (start over). |
| **Reset Trigger** | Change this integer value to force the queue back to line 1. |
| **Strip / Skip** | Automatically cleans up whitespace and ignores empty lines. |

</details>

---

### 2. 📂 Prompt Queue (From Folder)
**Batch processing made simple.**

Stop copying and pasting. Point this node to a folder on your computer, and it will read text files (`.txt`, `.json`, etc.) one by one.

> **Use Case:**  
> Great for processing wildcards, long metadata files, or batch-generating images based on a library of text descriptions stored locally.

<details>
<summary><b>🔻 Click for Parameters & Features</b></summary>

| Parameter | Description |
| :--- | :--- |
| **Folder Path** | The absolute path to your directory (e.g., `C:/Prompts`). |
| **Extensions** | Comma-separated list of file types to read (default: `txt, json`). |
| **On End** | `empty` (returns empty string), `loop` (starts at first file), `hold_last` (repeats last file). |
| **Outputs** | Returns both the **content** of the file and the **filename**. |

</details>

---

### 3. 🎥 Camera Angle Control
**Professional camera descriptions without the hassle.**

Generating specific camera angles in Stable Diffusion can be hit-or-miss. This node constructs precise camera prompts based on rotation, height, depth, and focal length.

**Three Output Modes:**
1. **Natural:** "camera rotated slightly to the right, camera raised high angle..."
2. **Technical:** "rotation 45.0°, vertical up 30.0..."
3. **Keywords:** "right side view, high angle, close-up..."

<details>
<summary><b>🔻 Click for Parameters & Features</b></summary>

*   **Rotation:** Pan the camera around the subject (Front → Side → Rear).
*   **Vertical:** Move the camera up or down (Bird's Eye → Eye Level → Worm's Eye).
*   **Depth:** Push in or pull out (Macro → Close-up → Wide Shot).
*   **Focal Length:** Simulate lens compression (24mm Wide Angle to 600mm Super Telephoto).
*   **Prefix/Suffix:** Add extra framing text easily.

</details>

---

### 4. 📐 Resolution Selector (Groups)
**Standardized resolutions with aspect ratios.**

Stop guessing pixel dimensions. This node groups resolutions by Megapixel count (0.25MP to 4MP) and provides standard aspect ratios (1:1, 16:9, 4:3, 21:9, etc.).

> **Logic:**  
> Select a resolution from the dropdown, then **Enable** the switch for that group. The node prioritizes the highest enabled quality group (e.g., if both 1MP and 4MP are enabled, it uses 4MP).

<details>
<summary><b>🔻 Click for Available Resolutions</b></summary>

*   **0.25MP:** SD 1.5 style small generations.
*   **0.6MP:** Intermediate sizes.
*   **1MP (Default):** Standard SDXL / SD 1.5 Hi-Res.
*   **2MP - 4MP:** High-resolution upscaling targets.
*   **Aspect Ratios:** Covers 1:1, 4:3, 3:4, 3:2, 2:3, 16:9, 9:16, 21:9, 9:21.

</details>

---

### 5. 🖼️ Image Resolution Fit
**Resize images while keeping aspect ratio.**

Allows you to resize an input image to a specific Megapixel target (e.g., 1MP, 2MP) without distorting it. The node automatically calculates the correct width and height to preserve the original shape and rounds dimensions to multiples of 8.

> **Use Case:**  
> Perfect for Image-to-Image workflows where you want to upscale or downscale a source image to a standard generation size (like 1024x1024 total pixels) but don't want to crop or stretch it.

<details>
<summary><b>🔻 Click for Parameters & Features</b></summary>

| Parameter | Description |
| :--- | :--- |
| **Resolution Select** | Choose the target Megapixel count (0.25MP to 4MP). |
| **Logic** | Calculates `sqrt(target_pixels / current_pixels)` to scale both dimensions equally. |
| **Outputs** | Returns the resized **Image**, a matching empty **Latent**, and the new **Width/Height**. |

</details>

---

### 6. ✖️ Multiplication (Dual & Latent)
**Mathematical scaling for custom upscaling.**

Takes two integer inputs (like Width and Height) and an optional Latent, and multiplies them by a float factor.

> **Use Case:**  
> Use this for "1.5x Upscales" or "2x Hires Fix". Connect your base width/height, set the multiplier to `1.5`, and feed the output into your latent upscaler or resize node.

<details>
<summary><b>🔻 Click for Parameters & Features</b></summary>

| Parameter | Description |
| :--- | :--- |
| **Multiplier** | The scaling factor (e.g., `1.5` or `2.0`). |
| **Inputs** | Accepts two Integers (`value_1`, `value_2`) and a `Latent`. |
| **Outputs** | Returns the multiplied integers and the bilinearly interpolated latent. |

</details>

---

### 7. 🧹 VRAM/RAM Cleaner
**Manage your resources mid-workflow.**

A "Pass-through" node that can connect to **any** input (Model, VAE, Image, etc.). It passes the data through unchanged but triggers a garbage collection and VRAM flush event when executed.

> **Modes:**  
> 1. **Current:** Unloads the specific model passing through the node.  
> 2. **Others:** Unloads everything else, keeping only the passing model in VRAM.  
> 3. **All:** Unloads everything to system RAM (clean slate).

---

### 8. 🎮 Flow Control (Sidecar Bypass)
**Toggle nodes On/Off remotely.**

A control panel that connects to up to 4 other nodes. This acts as a "Sidecar" — it does not sit in the flow of data, but rather controls the logic of the connected nodes.

> **How it works:**
> 1. Connect a node (e.g., a KSampler or ControlNet) to an `input` slot.
> 2. Toggle the switch on this node.
> 3. **Off (BYPASS):** Forces the connected node into Bypass mode (purple).
> 4. **Active:** Forces the connected node into Always/Normal mode.

---

### 9. 🔀 Any Passthrough
**Universal rerouting tools.**

Use these to clean up "spaghetti" wires or create fallback logic. These nodes accept **any** connection type (Model, Image, String, Latent, etc.).

*   **Any Passthrough (6 → 1):** Takes up to 6 inputs. Outputs the **first** one that is not null. Great for fallback defaults.
*   **Any Passthrough (1 → 6):** Takes 1 input and duplicates it to 6 outputs. Great for organizing wires from a single source.

---

### 10. ⏱️ Add Delay
**Pause execution for debugging.**

A simple node that connects to any data type, waits for a specified number of seconds, and then passes the data through unchanged. Useful for timing API calls or debugging complex flows.

---

### 11. 📺 Show Text
**Display text directly on the graph.**

Connect any string output (like the `Prompt Queue` or `Camera Angle Control`) to this node. It will display the text content inside a widget box on the node itself. Useful for verifying what is actually being sent to your CLIP encoder.

<br>

## 🚀 Workflow Examples

### The "Storyteller" Batch
1. Create a text file with 10 different scenes describing a story.
2. Use **Prompt Queue** to paste them in.
3. Connect output to your CLIP Text Encode.
4. Set "Batch Count" in ComfyUI to 10.
5. Hit Queue. You get 10 images, one for each scene, in order.

### The "Cinematographer"
1. Connect **Camera Angle Control** to a text concatenator or CLIP Encode.
2. Set Output Format to `Natural`.
3. Set Focal Length to `85mm` (Portrait) and Depth to `Close-up`.
4. Resulting Prompt: *"85.0mm portrait lens with compression, camera very close, close-up"* appended to your main prompt.

### The "Smart Upscaler"
1. Connect your base `Width` and `Height` to **Multiplication (Dual)**.
2. Set Multiplier to `1.5`.
3. Connect the output `Result 1` and `Result 2` to a "Latent Upscale" node.
4. This dynamically calculates a 1.5x resolution regardless of your starting aspect ratio.

<br>

## 🤝 Contributing

If you have ideas for new flow-assisting nodes or improvements to existing ones, feel free to open an issue or submit a pull request!

## 📄 License
AGPL-3.0 License. Feel free to use this in any project, personal or commercial.