from dataclasses import dataclass, fields
from typing import (get_origin, get_args, get_type_hints,
                    Annotated, Any, Self, Type, Sequence)
from enum import Enum

__all__ = ["Unit", "Column", "FieldSpec", "Schema"]


@dataclass(frozen=True)
class Unit:
    unit: str


@dataclass(frozen=True)
class Column:
    short: str
    long: str | None = None


@dataclass(frozen=True)
class FieldSpec:
    name: str
    baseType: type
    column: Column | None
    unit: Unit | None

    def label(self, preferLong: bool = True) -> str:
        if not self.column:
            return self.name
        if preferLong and self.column.long is not None:
            return self.column.long
        return self.column.short

    def withUnit(self, text: str) -> str:
        if self.unit:
            return f"{text} [{self.unit.unit}]"
        else:
            return text

    def header(self, preferLong = True, unit: bool = True):
        if unit:
            return self.withUnit(self.label(preferLong))
        return self.label(preferLong)

    def type(self) -> type:
        return self.baseType

    def choices(self) -> list[Enum] | None:
        if issubclass(self.baseType, Enum):
            return list(self.baseType)
        return None

    def value(self, obj: object) -> Any:
        return getattr(obj, self.name)

    def setValue(self, obj: object, value: Any):
        setattr(obj, self.name, value)

# TODO: cache somehow
@dataclass(frozen=True)
class Schema:
    fields: Sequence[FieldSpec]

    # TODO: cache
    @classmethod
    def fromDataclass(cls, dtCls) -> Self:
        def unwrapAnnotated(t: Any):
            meta = []
            while get_origin(t) is Annotated:
                t, *rest = get_args(t)
                meta += rest
            return t, meta

        hints = get_type_hints(dtCls, include_extras=True)
        specs = []
        # Iterating using `fields` retains the field order from class definition
        for f in fields(dtCls):
            hint = hints[f.name]
            # Only `Annotated` fields should be considered
            if hint is None or get_origin(hint) is not Annotated:
                continue
            baseType, meta = unwrapAnnotated(hint)
            # Process annotations from inside out, i.e. outermost takes priority
            unit = None
            column = None
            for arg in reversed(meta):
                if isinstance(arg, Column):
                    column = arg
                elif isinstance(arg, Unit):
                    unit = arg

            specs.append(FieldSpec(f.name, baseType, column, unit))

        return cls(specs)

class SchemaMixin:
    """Mixin for classes that are intended to provide a Schema."""
    @classmethod
    def schema(cls) -> Schema:
        """Get a Schema for editing annotated datafields of this class."""
        return Schema.fromDataclass(cls)
