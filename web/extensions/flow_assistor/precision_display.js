import { app } from "/scripts/app.js";
import { ComfyWidgets } from "/scripts/widgets.js";

const DETECTOR_NODE_IDS = new Set([
  "RuntimePrecisionModel",
  "RuntimePrecisionCLIP",
  "RuntimePrecisionVAE",
]);

const PREVIEW_WIDGET_NAME = "precision_report_preview";
const WAITING_TEXT = "Run this node to display the active runtime precision.";

app.registerExtension({
  name: "FlowAssistor.PrecisionDetector.Display",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (!DETECTOR_NODE_IDS.has(nodeData.name)) return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      onNodeCreated?.apply(this, arguments);

      if (this.widgets?.some((widget) => widget.name === PREVIEW_WIDGET_NAME)) {
        return;
      }

      const previewWidget = ComfyWidgets.STRING(
        this,
        PREVIEW_WIDGET_NAME,
        ["STRING", { multiline: true, default: WAITING_TEXT }],
        app,
      ).widget;

      previewWidget.label = "Runtime precision";
      previewWidget.value = WAITING_TEXT;
      previewWidget.options ??= {};
      previewWidget.options.read_only = true;
      previewWidget.options.serialize = false;
      previewWidget.options.minNodeSize = [400, 220];
      previewWidget.serialize = false;

      const inputElement = previewWidget.element ?? previewWidget.inputEl;
      if (inputElement) {
        inputElement.readOnly = true;
        inputElement.setAttribute("aria-label", "Runtime precision report");
      }

      const width = Math.max(this.size?.[0] ?? 0, 400);
      const height = Math.max(this.size?.[1] ?? 0, 220);
      this.setSize?.([width, height]);
    };

    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      onExecuted?.apply(this, arguments);

      const previewWidget = this.widgets?.find(
        (widget) => widget.name === PREVIEW_WIDGET_NAME,
      );
      if (!previewWidget) return;

      const text = message?.text ?? "";
      previewWidget.value = Array.isArray(text) ? text.join("\n\n") : String(text);
      this.setDirtyCanvas?.(true, true);
    };
  },
});
