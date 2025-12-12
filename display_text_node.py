# display_text_node.py
class DisplayText:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    INPUT_IS_LIST = True

    # NO OUTPUTS:
    RETURN_TYPES = ()
    FUNCTION = "notify"
    OUTPUT_NODE = True

    CATEGORY = "flow-assistor"

    def notify(self, text, unique_id=None, extra_pnginfo=None):
        # Persist text into workflow so it remains visible after reload
        if unique_id is not None and extra_pnginfo is not None:
            try:
                if isinstance(extra_pnginfo, list) and extra_pnginfo and isinstance(extra_pnginfo[0], dict):
                    workflow = extra_pnginfo[0].get("workflow")
                    if workflow and isinstance(workflow.get("nodes"), list):
                        node = next((x for x in workflow["nodes"] if str(x.get("id")) == str(unique_id[0])), None)
                        if node is not None:
                            node["widgets_values"] = [text]
            except Exception:
                pass

        # Send payload for the JS to display
        return {"ui": {"text": text}, "result": ()}


NODE_CLASS_MAPPINGS = {
    "DisplayText": DisplayText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DisplayText": "Show Text",
}