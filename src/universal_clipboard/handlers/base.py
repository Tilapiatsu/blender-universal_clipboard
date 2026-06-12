from typing import Protocol


class P_ClipboardHandler(Protocol):
    object_type = ""

    @classmethod
    def copy(cls, context): ...

    @classmethod
    def cut(cls, context): ...

    @classmethod
    def paste(cls, context): ...
