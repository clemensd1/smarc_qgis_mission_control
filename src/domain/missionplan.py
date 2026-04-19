from typing import Any, Self, Annotated
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from .tasks import Task, TaskType, TaskRegistry
from .schema import SchemaMixin, Column, Unit

__all__ = ["MissionPlan"]


@dataclass
class MissionPlan(SchemaMixin):
    # fmt: off
    name        : str
    description : Annotated[str, Column('Description')]
    uuid        : UUID = field(default_factory=uuid4)
    timeout     : Annotated[float, Column('Timeout'), Unit('s')] = 300.0
    tasks       : list[Task] = field(default_factory=list)
    # fmt: on

    @classmethod
    def fromJson(cls, data: dict[str, Any]) -> Self:
        tasks = []
        for c in data["children"]:
            # NOTE: task "name" is actually the type, e.g. move-to
            type = TaskType(c["name"])
            taskCls = TaskRegistry.lookup(type)
            tasks.append(taskCls.fromJson(c))

        return cls(
            # fmt: off
            name        = str(data["name"]),
            description = str(data["description"]),
            uuid        = UUID(data["tst-uuid"]),
            timeout     = float(data["params"].get("timeout", 0)),
            tasks       = tasks,
            # fmt: on
        )

    def toJson(self) -> dict[str, Any]:
        return {
            # fmt: off
            "name"          : self.name,
            "description"   : self.description,
            "tst-uuid"      : str(self.uuid),
            "params"        : {
                "timeout"       : self.timeout,
            },
            "common-params" : {},
            "children"      : [t.toJson() for t in self.tasks]
            # fmt: on
        }
