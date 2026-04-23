from typing import NoReturn
from enum import Enum


__all__ = ["StrEnum"]

class StrEnum(str, Enum):
    __str__ = str.__str__
    __format__ = str.__format__

def assert_never(value: NoReturn) -> NoReturn:
    raise AssertionError(f"Unhandled value: {value!r}")
