import time

class AnyType(str):
    """A special type that compares equal to everything, allowing any connection."""
    def __ne__(self, __value: object) -> bool:
        return False

any_type = AnyType("*")


class AddDelay:
    """
    Adds a delay (sleep) in seconds, then passes the input through unchanged.
    Default delay = 6.0 seconds.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": (any_type,),
                "delay": ("FLOAT", {
                    "default": 6.0,
                    "min": 0.0,
                    "max": 3600.0,
                    "step": 0.1
                }),
            }
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "run"
    CATEGORY = "flow-assistor"

    def run(self, input, delay=6.0):
        try:
            d = float(delay)
        except Exception:
            d = 6.0

        if d > 0:
            time.sleep(d)

        return (input,)


NODE_CLASS_MAPPINGS = {
    "AddDelay": AddDelay,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AddDelay": "Add Delay",
}