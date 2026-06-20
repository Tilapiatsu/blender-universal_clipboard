from typing import Protocol


class P_ClipboardHandler(Protocol):
    object_type = ""

    @classmethod
    def copy(cls, context) -> tuple[int, str]: ...

    @classmethod
    def cut(cls, context) -> tuple[int, str]: ...

    @classmethod
    def paste(cls, context) -> tuple[int, str]: ...
