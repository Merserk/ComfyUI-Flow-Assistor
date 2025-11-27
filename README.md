```markdown
# 🌊 ComfyUI Flow Assistor

<p align="center">
  <img src="https://img.shields.io/badge/ComfyUI-Custom_Nodes-blue?style=for-the-badge&logo=python" alt="ComfyUI">
  <img src="https://img.shields.io/github/license/Merserk/ComfyUI-Flow-Assistor?style=for-the-badge" alt="License">
  <br>
  <b>Streamline your batch generation, automate prompt engineering, and manage resolutions with ease.</b>
</p>

<hr>

**ComfyUI Flow Assistor** is a suite of custom nodes designed to handle the "boring" parts of your workflow. Whether you are running complex batch jobs from text files, iterating through prompt variations, or trying to find the perfect camera angle without typing out paragraphs of technical jargon, this pack has you covered.

## 📦 Installation

1. Navigate to your ComfyUI `custom_nodes` directory.
2. Clone this repository:
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/Merserk/ComfyUI-Flow-Assistor.git
   ```
3. Restart ComfyUI.

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

<br>

## 🤝 Contributing

If you have ideas for new flow-assisting nodes or improvements to existing ones, feel free to open an issue or submit a pull request!

## 📄 License
MIT License. Feel free to use this in any project, personal or commercial.
