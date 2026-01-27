// Robust import for different ComfyUI builds
let app;
try {
    ({ app } = await import("/scripts/app.js"));
} catch (e) {
    ({ app } = await import("../../scripts/app.js"));
}

console.log("[Flow-Assistor] resolution_groups.js loaded");

app.registerExtension({
    name: "flow_assistor.resolution_groups",

    // Logic for new nodes created by user
    async nodeCreated(node, app) {
        setupResolutionGroups(node);
    },

    // Logic for nodes loaded from graph
    async loadedGraphNode(node, app) {
        setupResolutionGroups(node);
    },
});

function setupResolutionGroups(node) {
    if (node.comfyClass !== "ResolutionSelectNode") return;

    if (node._invoked_setup_res_groups) return;
    node._invoked_setup_res_groups = true;

    const useWidgets = node.widgets?.filter((w) => w.name && w.name.startsWith("use_"));
    if (!useWidgets || useWidgets.length === 0) return;

    console.log(`[Flow-Assistor] Setting up Resolution Selector logic for node ${node.id}`);

    for (const w of useWidgets) {
        const originalCallback = w.callback;
        w.callback = function (value) {
            // Execute original callback first
            if (originalCallback) {
                originalCallback.apply(this, arguments);
            }

            // If turned ON, turn others OFF
            if (value === true) {
                let changed = false;
                for (const other of useWidgets) {
                    if (other !== w && other.value === true) {
                        other.value = false;
                        // We do NOT call other.callback here to avoid potential recursion or double-events,
                        // assuming simple boolean widgets. If they had side effects, we might need to, 
                        // but for standard widgets .value = false is enough for state.
                        changed = true;
                    }
                }

                if (changed) {
                    // Force a redraw
                    if (app.graph) {
                        app.graph.setDirtyCanvas(true, true);
                    }
                }
            }
        };
    }
}
