// Robust import for different ComfyUI builds (bare specifiers may fail)
let app;
try {
  ({ app } = await import("/scripts/app.js"));
} catch (e) {
  // fallback for some older/mounted layouts
  ({ app } = await import("../../scripts/app.js"));
}

const MODE_ALWAYS = (globalThis.LiteGraph?.ALWAYS ?? 0);
const MODE_BYPASS = 4;

console.log("[Flow-Assistor] bypass_control.js loaded");

app.registerExtension({
  name: "FlowAssistor.BypassControl",

  nodeCreated(node) {
    if (!isBypassControlNode(node)) return;
    setupBypassControl(node);
  },

  loadedGraphNode(node) {
    if (!isBypassControlNode(node)) return;
    setupBypassControl(node);
  },
});

function isBypassControlNode(node) {
  return node?.type === "BypassControl" || node?.comfyClass === "BypassControl";
}

function setupBypassControl(node) {
  if (node.__flowAssistorBypassSetup) return;
  node.__flowAssistorBypassSetup = true;

  const channels = [1, 2, 3, 4].map((n) => ({
    n,
    widgetName: `active_${n}`,
    inputName: `input_${n}`,
  }));

  function findChannelObjects(ch) {
    const widget = node.widgets?.find((w) => w.name === ch.widgetName);
    const inputIndex = node.inputs?.findIndex((i) => i.name === ch.inputName);
    return { widget, inputIndex };
  }

  function getLinkInfo(linkId) {
    const link = app.graph?.links?.[linkId];
    if (!link) return null;

    // object OR array link formats
    const origin_id = link.origin_id ?? link[1];
    const target_id = link.target_id ?? link[3];
    return { origin_id, target_id };
  }

  function setNodeMode(targetNode, mode) {
    if (typeof targetNode.setMode === "function") {
      targetNode.setMode(mode);
    } else {
      targetNode.mode = mode;
      targetNode.onModeChange?.(mode);
    }
  }

  function updateFromChannel(ch) {
    const { widget, inputIndex } = findChannelObjects(ch);
    if (!widget) return;
    if (inputIndex == null || inputIndex < 0) return;

    const input = node.inputs?.[inputIndex];
    const linkId = input?.link;
    if (linkId == null) return;

    const info = getLinkInfo(linkId);
    if (!info?.origin_id) return;

    // bypass/enable the upstream node feeding this input
    const targetNode = app.graph.getNodeById(info.origin_id);
    if (!targetNode) return;

    const desiredMode = widget.value ? MODE_ALWAYS : MODE_BYPASS;
    if (targetNode.mode === desiredMode) return;

    setNodeMode(targetNode, desiredMode);
    app.graph.setDirtyCanvas(true, true);
  }

  // widget toggles
  for (const ch of channels) {
    const { widget } = findChannelObjects(ch);
    if (!widget) continue;

    const oldCb = widget.callback;
    widget.callback = function () {
      oldCb?.apply(this, arguments);
      setTimeout(() => updateFromChannel(ch), 0);
    };

    setTimeout(() => updateFromChannel(ch), 0);
  }

  // cable connect/disconnect
  const oldOcc = node.onConnectionsChange;
  node.onConnectionsChange = function (type, index) {
    oldOcc?.apply(this, arguments);

    if (type !== (globalThis.LiteGraph?.INPUT ?? 1)) return;

    for (const ch of channels) {
      const { inputIndex } = findChannelObjects(ch);
      if (inputIndex === index) {
        setTimeout(() => updateFromChannel(ch), 0);
        break;
      }
    }
  };
}