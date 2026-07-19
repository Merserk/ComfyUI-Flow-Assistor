import { app } from "/scripts/app.js";

const PREVIEW_PROPERTY = "caption_creator_preview";
const EMPTY_PREVIEW = "Caption preview appears here after execution.";

function asCaption(value) {
  return String(value ?? "");
}

function normalizeCaptions(payload) {
  if (payload == null) return [];
  if (Array.isArray(payload)) return payload.map(asCaption);
  return [asCaption(payload)];
}

function normalizeLegacyText(payload) {
  if (payload == null) return [];
  if (!Array.isArray(payload)) return [asCaption(payload)];

  // Older Caption Creator releases sent a bare string in the UI payload. Some
  // ComfyUI builds expanded it into an array of characters during transport.
  // Rejoin that legacy shape so saved workflows remain readable after upgrade.
  if (payload.length > 1 && payload.every((item) => typeof item === "string" && item.length <= 1)) {
    return [payload.join("")];
  }
  if (payload.length === 1) return [asCaption(payload[0])];
  return payload.map(asCaption);
}

function extractCaptions(message) {
  const explicit = message?.captions ?? message?.ui?.captions;
  if (explicit != null) return normalizeCaptions(explicit);

  const legacy = message?.text ?? message?.ui?.text;
  return normalizeLegacyText(legacy);
}

function formatPreview(captions) {
  if (captions.length === 0) return EMPTY_PREVIEW;
  if (captions.length === 1) return captions[0];
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
  textarea.value = node.properties?.[PREVIEW_PROPERTY] || EMPTY_PREVIEW;
  textarea.placeholder = EMPTY_PREVIEW;
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

function updatePreview(node, captions) {
  const textarea = ensurePreview(node);
  const value = formatPreview(captions);
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
      const captions = extractCaptions(message);
      if (captions.length > 0) updatePreview(this, captions);
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      onConfigure?.apply(this, arguments);
      const stored = this.properties?.[PREVIEW_PROPERTY];
      if (stored) updatePreview(this, [stored]);
      else ensurePreview(this);
    };
  },
});
