import { app } from "/scripts/app.js";
import { ComfyWidgets } from "/scripts/widgets.js";

// Renders the debug text returned by OutputAnyDebugDataNode directly on the node.

app.registerExtension({
  name: "FlowAssistor.DebugData",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "OutputAnyDebugDataNode") return;

    // Helper to Create or Update the Text Widget
    function populate(text) {
      // 1. Try to find the existing widget to avoid flicker
      const widgetName = "debug_text_msg";
      let w = this.widgets?.find((w) => w.name === widgetName);

      // 2. If it doesn't exist, create it
      if (!w) {
        // ComfyWidgets["STRING"] adds the widget to this.widgets automatically
        const widgetResult = ComfyWidgets["STRING"](
          this,
          widgetName,
          ["STRING", { multiline: true }],
          app
        );
        w = widgetResult.widget;
        
        // Styling to look like a debug console
        w.inputEl.readOnly = true;
        w.inputEl.style.opacity = 0.9;
        w.inputEl.style.backgroundColor = "#222";
        w.inputEl.style.color = "#0f0"; // Matrix green text
        w.inputEl.style.fontFamily = "monospace";
        w.inputEl.style.fontSize = "11px";
        w.inputEl.style.padding = "4px";
      }

      // 3. Update the value
      w.value = text ?? "Waiting for data...";

      // 4. Force Resize to fit content
      requestAnimationFrame(() => {
        const sz = this.computeSize();
        if (sz[0] < this.size[0]) sz[0] = this.size[0];
        if (sz[1] < this.size[1]) sz[1] = this.size[1];
        this.onResize?.(sz);
        app.graph.setDirtyCanvas(true, false);
      });
    }

    // Hook: When the node executes (during prompt run)
    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      onExecuted?.apply(this, arguments);
      // "message.text" comes from the python return {"ui": {"text": ...}}
      // ComfyUI usually sends lists for UI elements
      const text = message?.text?.[0] ?? message?.text ?? "No Data";
      populate.call(this, text);
    };

    // Hook: When the node loads from a workflow (restore saved state)
    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      onConfigure?.apply(this, arguments);
      // Restore the last seen value if it exists in the save file
      if (this.widgets_values && this.widgets_values.length) {
        // The read-only widget usually ends up being the last one in saved values
        // or we just check index 0 if it's the only widget
        const savedText = this.widgets_values[0];
        if (typeof savedText === "string") {
            populate.call(this, savedText);
        }
      }
    };
  },
});