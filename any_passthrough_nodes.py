class AnyType(str):
    """A special type that compares equal to everything, allowing any connection."""
    def __ne__(self, __value: object) -> bool:
        return False

any_type = AnyType("*")


class AnyPassthrough6to1:
    """
    Up to 6 ANY inputs -> 1 ANY output.
    Outputs the first connected (non-None) input in priority order.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "input1": (any_type,),
                "input2": (any_type,),
                "input3": (any_type,),
                "input4": (any_type,),
                "input5": (any_type,),
                "input6": (any_type,),
            }
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "passthrough"
    CATEGORY = "flow-assistor"

    def passthrough(self, input1=None, input2=None, input3=None, input4=None, input5=None, input6=None):
        for v in (input1, input2, input3, input4, input5, input6):
            if v is not None:
                return (v,)
        return (None,)


class AnyPassthrough1to6:
    """
    1 ANY input -> 6 ANY outputs.
    Duplicates the same value to all outputs.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": (any_type,),
            }
        }

    RETURN_TYPES = (any_type, any_type, any_type, any_type, any_type, any_type)
    RETURN_NAMES = ("out1", "out2", "out3", "out4", "out5", "out6")
    FUNCTION = "passthrough"
    CATEGORY = "flow-assistor"

    def passthrough(self, input):
        return (input, input, input, input, input, input)


NODE_CLASS_MAPPINGS = {
    "AnyPassthrough6to1": AnyPassthrough6to1,
    "AnyPassthrough1to6": AnyPassthrough1to6,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AnyPassthrough6to1": "Any Passthrough (6 → 1)",
    "AnyPassthrough1to6": "Any Passthrough (1 → 6)",
}