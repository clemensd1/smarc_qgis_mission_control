from dataclasses import dataclass, field
from uuid import UUID

from ..domain.missionplan import MissionPlan
from ..domain.waypoints import Waypoint
from ..domain.tasks import Task
from ..domain.taskspatial import iterTaskWaypoints


@dataclass
class MissionIndex:
    waypointMap: dict[UUID, Waypoint] = field(default_factory=dict)
    taskMap: dict[UUID, Task] = field(default_factory=dict)
    waypointTaskMap: dict[UUID, UUID] = field(default_factory=dict)

    @classmethod
    def fromMissionPlan(cls, plan: MissionPlan) -> 'MissionIndex':
        index = cls()
        for task in plan.tasks:
            index.registerTask(task)

        return index

    def waypointByUuid(self, waypointUuid: UUID) -> Waypoint | None:
        return self.waypointMap.get(waypointUuid)

    def taskByUuid(self, taskUuid: UUID) -> Task | None:
        return self.taskMap.get(taskUuid)

    def taskByWaypointUuid(self, waypointUuid: UUID) -> Task | None:
        taskUuid = self.waypointTaskMap.get(waypointUuid)
        if taskUuid is None:
            return None

        return self.taskMap.get(taskUuid)

    def registerTask(self, task: Task):
        self.taskMap[task.uuid] = task
        for waypoint in iterTaskWaypoints(task):
            self.waypointMap[waypoint.uuid] = waypoint
            self.waypointTaskMap[waypoint.uuid] = task.uuid

    def forgetTask(self, taskUuid: UUID):
        task = self.taskByUuid(taskUuid)
        if task is None:
            # TODO: invalid mapping
            return

        for waypoint in iterTaskWaypoints(task):
            del self.waypointMap[waypoint.uuid]
            del self.waypointTaskMap[waypoint.uuid]

        del self.taskMap[taskUuid]

    def registerWaypoint(self, taskUuid: UUID, waypoint: Waypoint):
        task = self.taskByUuid(taskUuid)
        if task is None:
            # TODO: invalid mapping
            return

        self.waypointMap[waypoint.uuid] = waypoint
        self.waypointTaskMap[waypoint.uuid] = taskUuid

    def forgetWaypoint(self, waypointUuid: UUID):
        task = self.taskByWaypointUuid(waypointUuid)
        if task is None:
            # TODO: invalid mapping
            return

        del self.waypointMap[waypointUuid]
        del self.waypointTaskMap[waypointUuid]
