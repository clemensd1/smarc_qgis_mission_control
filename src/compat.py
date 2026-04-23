from enum import Enum


__all__ = ["StrEnum"]

class StrEnum(str, Enum):
    __str__ = str.__str__
    __format__ = str.__format__
