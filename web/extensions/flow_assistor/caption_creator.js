import { app } from "/scripts/app.js";

const PREVIEW_PROPERTY = "caption_creator_preview";

function normalizePayload(payload) {
  let values = payload;
  if (values == null) return [];
  if (!Array.isArray(values)) values = [values];

  const flattened = [];
  for (const value of values) {
    if (Array.isArray(value)) {
      flattened.push(...value.map((item) => String(item ?? "")));
    } else {
      flattened.push(String(value ?? ""));
    }
  }
  return flattened.filter((value) => value.length > 0);
}

function formatPreview(payload) {
  const captions = normalizePayload(payload);
  if (captions.length <= 1) return captions[0] ?? "Caption preview appears here after execution.";
  return captions.map((caption, index) => `[${index + 1}]\n${caption}`).join("\n\n");
}

function resizeNode(node) {
  requestAnimationFrame(() => {
    const computed = node.computeSize?.() ?? node.size;
    const width = Math.max(node.size?.[0] ?? 0, computed?.[0] ?? 0, 360);
    const height = Math.max(node.size?.[1] ?? 0, computed?.[1] ?? 0, 360);
    node.setSize?.([width, height]);
    node.setDirtyCanvas?.(true, true);
    app.graph?.setDirtyCanvas?.(true, false);
  });
}

function ensurePreview(node) {
  if (node.captionCreatorPreviewEl) return node.captionCreatorPreviewEl;

  const textarea = document.createElement("textarea");
  textarea.readOnly = true;
  textarea.value = node.properties?.[PREVIEW_PROPERTY] || "Caption preview appears here after execution.";
  textarea.placeholder = "Caption preview appears here after execution.";
  textarea.style.width = "100%";
  textarea.style.height = "180px";
  textarea.style.minHeight = "120px";
  textarea.style.boxSizing = "border-box";
  textarea.style.resize = "vertical";
  textarea.style.overflow = "auto";
  textarea.style.padding = "10px";
  textarea.style.border = "1px solid var(--border-color, #555)";
  textarea.style.borderRadius = "6px";
  textarea.style.background = "var(--comfy-input-bg, rgba(0, 0, 0, 0.2))";
  textarea.style.color = "var(--input-text, inherit)";
  textarea.style.fontFamily = "monospace";
  textarea.style.fontSize = "12px";
  textarea.style.lineHeight = "1.4";
  textarea.style.opacity = "0.92";

  const widget = node.addDOMWidget?.("caption_preview", "caption_preview", textarea, {
    serialize: false,
    hideOnZoom: false,
  });
  if (widget) {
    widget.serializeValue = async () => undefined;
    widget.computeSize = (width) => [width, Math.max(190, textarea.offsetHeight + 10)];
  }

  if (typeof ResizeObserver !== "undefined") {
    const observer = new ResizeObserver(() => resizeNode(node));
    observer.observe(textarea);
    node.captionCreatorPreviewObserver = observer;

    const onRemoved = node.onRemoved;
    node.onRemoved = function () {
      observer.disconnect();
      return onRemoved?.apply(this, arguments);
    };
  }

  node.captionCreatorPreviewEl = textarea;
  resizeNode(node);
  return textarea;
}

function updatePreview(node, payload) {
  const textarea = ensurePreview(node);
  const value = formatPreview(payload);
  textarea.value = value;
  node.properties ??= {};
  node.properties[PREVIEW_PROPERTY] = value;
  resizeNode(node);
}

app.registerExtension({
  name: "FlowAssistor.CaptionCreatorPreview",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "CaptionCreator") return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);
      ensurePreview(this);
      return result;
    };

    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      onExecuted?.apply(this, arguments);
      const payload = message?.text ?? message?.ui?.text;
      if (payload != null) updatePreview(this, payload);
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      onConfigure?.apply(this, arguments);
      const stored = this.properties?.[PREVIEW_PROPERTY];
      if (stored) updatePreview(this, stored);
      else ensurePreview(this);
    };
  },
});
