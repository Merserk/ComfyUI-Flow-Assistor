import { app } from "/scripts/app.js";
import { ComfyWidgets } from "/scripts/widgets.js";

// Displays input text on the node (pysssss-style)

app.registerExtension({
  name: "FlowAssistor.DisplayText",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    // Must match your python mapping key exactly:
    // NODE_CLASS_MAPPINGS = { "DisplayText": DisplayText }
    if (nodeData.name !== "DisplayText") return;

    function populate(textPayload) {
      if (this.widgets) {
        // On some frontends there is a hidden converted-widget at inputs[0].widget
        const isConvertedWidget = +!!this.inputs?.[0].widget;
        for (let i = isConvertedWidget; i < this.widgets.length; i++) {
          this.widgets[i].onRemove?.();
        }
        this.widgets.length = isConvertedWidget;
      }

      // Normalize to arrays
      let v = textPayload;
      if (!(v instanceof Array)) v = [v];

      // v may contain nested lists, normalize like pysssss
      const blocks = [...v];
      if (!blocks[0]) blocks.shift();

      for (let list of blocks) {
        if (!(list instanceof Array)) list = [list];
        for (const line of list) {
          const w = ComfyWidgets["STRING"](
            this,
            "text_" + (this.widgets?.length ?? 0),
            ["STRING", { multiline: true }],
            app
          ).widget;

          w.inputEl.readOnly = true;
          w.inputEl.style.opacity = 0.75;
          w.value = line ?? "";
        }
      }

      requestAnimationFrame(() => {
        const sz = this.computeSize();
        if (sz[0] < this.size[0]) sz[0] = this.size[0];
        if (sz[1] < this.size[1]) sz[1] = this.size[1];
        this.onResize?.(sz);
        app.graph.setDirtyCanvas(true, false);
      });
    }

    // When executed, show the text
    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      onExecuted?.apply(this, arguments);

      // robust: some builds put it on message.text, some under message.ui.text
      const payload = message?.text ?? message?.ui?.text;
      populate.call(this, payload);
    };

    // Persist between reloads (reads widgets_values)
    const VALUES = Symbol();
    const configure = nodeType.prototype.configure;
    nodeType.prototype.configure = function () {
      this[VALUES] = arguments[0]?.widgets_values;
      return configure?.apply(this, arguments);
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      onConfigure?.apply(this, arguments);
      const widgets_values = this[VALUES];
      if (widgets_values?.length) {
        requestAnimationFrame(() => {
          // Similar handling to pysssss for the converted widget
          populate.call(
            this,
            widgets_values.slice(+(widgets_values.length > 1 && this.inputs?.[0].widget))
          );
        });
      }
    };
  },
});