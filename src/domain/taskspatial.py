from typing import Any, Iterator, get_args, get_origin
from uuid import UUID

from .schema import FieldSpec
from .tasks import Task
from .waypoints import Waypoint


def waypointType(annotation: Any) -> type[Waypoint] | None:
    if isinstance(annotation, type) and issubclass(annotation, Waypoint):
        return annotation
    return None


def waypointListType(annotation: Any) -> type[Waypoint] | None:
    if get_origin(annotation) is not list:
        return None

    args = get_args(annotation)
    if len(args) != 1:
        return None
    return waypointType(args[0])


def isWaypointField(spec: FieldSpec) -> bool:
    return waypointType(spec.baseType) is not None


def isWaypointListField(spec: FieldSpec) -> bool:
    return waypointListType(spec.baseType) is not None


def iterTaskWaypoints(task: Task) -> Iterator[Waypoint]:
    for spec in task.schema().fields:
        if isWaypointField(spec):
            yield spec.value(task)
        elif isWaypointListField(spec):
            yield from spec.value(task)


def locateTaskWaypoint(task: Task, waypointUuid: UUID) \
        -> tuple[str, int | None, Waypoint] | None:
    for spec in task.schema().fields:
        if isWaypointField(spec):
            waypoint = spec.value(task)
            if waypoint.uuid == waypointUuid:
                return spec.name, None, waypoint
        elif isWaypointListField(spec):
            for index, waypoint in enumerate(spec.value(task)):
                if waypoint.uuid == waypointUuid:
                    return spec.name, index, waypoint
    return None


def waypointListFields(taskCls: type[Task]) -> list[FieldSpec]:
    return [
        spec for spec in taskCls.schema().fields
        if isWaypointListField(spec)
    ]
