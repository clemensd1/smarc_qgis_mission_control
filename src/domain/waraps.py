from dataclasses import dataclass
from uuid import UUID
from .schema import SchemaMixin, Column

from typing import Annotated

@dataclass
class WaraPsAvailableTask:
    name: str
    signals: list[str]

@dataclass
class WaraPsExecutingTask(SchemaMixin):
    description: Annotated[str, Column('Description')]
    type: Annotated[str, Column('Type')]
    status: Annotated[str, Column('Status')]

    uuid: UUID
