import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

app.registerExtension({
  name: "FlowAssistor.LoRAOnline",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "LoRAOnlineNode") return;

    // Add a button to open the folder
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      onNodeCreated?.apply(this, arguments);

      const btn = this.addWidget("button", "Open LoRA Save Folder", null, () => {
        api.fetchApi("/flow_assistor/open_lora_folder", {
            method: "POST",
          })
          .then((response) => {
            if (!response.ok) {
              console.error("[LoRA Online] Failed to open folder:", response.statusText);
              alert("Failed to open folder. Check console.");
            }
          })
          .catch((error) => {
            console.error("[LoRA Online] API Error:", error);
          });
      });
      
      // Optional: Style the button slightly smaller or distinct if supported
      btn.serialize = false; 
    };
  },
});