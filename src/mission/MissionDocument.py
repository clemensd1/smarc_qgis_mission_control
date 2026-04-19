from uuid import UUID, uuid4
from typing import Self, Any, assert_never
from pathlib import Path
import json

from qgis.PyQt.QtCore import pyqtSlot, pyqtSignal, QObject
from qgis.PyQt.QtWidgets import QUndoCommand
from qgis.core import QgsPointXY

from ..domain.missionplan import MissionPlan
from ..domain.waypoints import Waypoint
from ..domain.tasks import *
from .MissionIndex import MissionIndex
from .MissionLayerBridge import MissionLayerBridge
from .MissionUndoCommand import *


class MissionDocument(QObject):
    # TODO: move these three signals to MissionContext
    editModeChanged = pyqtSignal(bool)
    editingStarted = pyqtSignal()
    editingFinished = pyqtSignal()

    # TODO: remove
    taskListModified = pyqtSignal()

    # TODO: not very precise
    missionChanged = pyqtSignal()

    beforeTaskAdded = pyqtSignal(UUID, int)
    taskAdded = pyqtSignal(UUID)
    beforeTaskDeleted = pyqtSignal(UUID)
    taskDeleted = pyqtSignal(UUID, int)
    # TODO: not very precise
    taskChanged = pyqtSignal(UUID)

    beforeWaypointAdded = pyqtSignal(UUID, UUID, int)
    waypointAdded = pyqtSignal(UUID)
    beforeWaypointDeleted = pyqtSignal(UUID)
    waypointDeleted = pyqtSignal(UUID, UUID, int)
    # TODO: not very precise
    waypointChanged = pyqtSignal(UUID)

    plan: MissionPlan
    path: Path
    index: MissionIndex
    layerBridge: MissionLayerBridge
    _keepalive_undo: list[MissionUndoCommand]

    def __init__(self, plan: MissionPlan, path: str | Path,
                 parent: QObject | None = None):
        super().__init__(parent)

        self.plan = plan
        self.path = Path(path)
        self.index = MissionIndex.fromMissionPlan(plan)
        self.layerBridge = MissionLayerBridge(plan, self)
        self._keepalive_undo = []

    @classmethod
    def fromFile(cls, path: str | Path, parent: QObject | None = None) -> Self:
        p = Path(path)
        with p.open() as fp:
            plan = MissionPlan.fromJson(json.load(fp))
        return cls(plan, p, parent)

    def isModified(self) -> bool:
        return (self.layerBridge.waypointLayer.isEditable()
                and self.layerBridge.waypointLayer.isModified())

    def startEditing(self):
        self.layerBridge.waypointLayer.startEditing()

        self.editingStarted.emit()
        self.editModeChanged.emit(True)

    def stopEditing(self, save: bool):
        if save:
            self.layerBridge.waypointLayer.commitChanges()
        else:
            self.layerBridge.waypointLayer.rollBack()

        # Drop keepalive command references
        self._keepalive_undo = []

        self.editingFinished.emit()
        self.editModeChanged.emit(False)

    def setMissionField(self, fieldId: int, value: Any):
        oldValue = self.plan.schema().fields[fieldId].value(self.plan)
        if str(value) == str(oldValue):
            # TODO: string comparison is suboptimal
            # No change has occurred
            return

        cmd = SetMissionFieldUndoCommand(self, fieldId, value, oldValue)
        with self.layerBridge.customEditCommand("Modify mission"):
            self._keepalive_undo.append(cmd)
            self.layerBridge.waypointLayer.undoStack().push(cmd)

    def _setMissionField(self, fieldId: int, value: Any):
        self.plan.schema().fields[fieldId].setValue(self.plan, value)
        self.missionChanged.emit()

    # TODO: accept index in addTask?
    def addTask(self, taskType: TaskType, description: str,
                taskUuid: UUID | None = None) -> None:
        taskCls = TaskRegistry.lookup(taskType)
        if issubclass(taskCls, SingleWaypointTask):
            req = SingleWaypointTask.Pending(
                taskCls=taskCls,
                description=description,
                taskUuid=taskUuid or uuid4(),
                waypointUuid=uuid4(),
            )
            # TODO: get mapManager from parent
            self.parent().mapManager.pickInitialWaypoint(req)
        else:
            task = taskCls(description=description)
            cmd = AddTaskUndoCommand(self, task)

            text = f"Add task {taskType} ({description})"
            with self.layerBridge.customEditCommand(text):
                self._keepalive_undo.append(cmd)
                self.layerBridge.waypointLayer.undoStack().push(cmd)

    def addSingleWaypointTask(self, pendingTask: SingleWaypointTask.Pending,
                              point: QgsPointXY) -> None:
        waypoint = pendingTask.taskCls.waypointClass(
            latitude=point.y(),
            longitude=point.x(),
            uuid=pendingTask.waypointUuid
        )
        task = pendingTask.taskCls(
            description=pendingTask.description,
            waypoint=waypoint,
            uuid=pendingTask.taskUuid
        )
        print(task, task.uuid)

        feat = self.layerBridge._waypointToFeature(task.uuid, waypoint)
        cmd = AddTaskUndoCommand(self, task)

        text = f"Add task {task.type} ({task.description})"
        with self.layerBridge.customEditCommand(text):
            self.layerBridge.waypointLayer.addFeature(feat)
            self._keepalive_undo.append(cmd)
            self.layerBridge.waypointLayer.undoStack().push(cmd)

    def _addTaskAt(self, task: Task, index: int):
        self.plan.tasks.insert(index, task)
        self.index.registerTask(task)
        self.taskListModified.emit()

    def deleteTaskAt(self, index: int):
        try:
            task = self.plan.tasks[index]
        except IndexError:
            # TODO: invalid index
            return

        if isinstance(task, SingleWaypointTask):
            # Handled in deleteWaypoint
            self.deleteWaypoint(task.waypoint.uuid)
            return

        cmd = DeleteTaskUndoCommand(self, task)

        text = f"Delete task {task.type} ({task.description})"
        with self.layerBridge.customEditCommand(text):
            if isinstance(task, MultiWaypointTask):
                while len(task.waypoints):
                    self.deleteWaypoint(task.waypoints[0].uuid)
            self._keepalive_undo.append(cmd)
            self.layerBridge.waypointLayer.undoStack().push(cmd)

    def _deleteTaskAt(self, index: int):
        task = self.plan.tasks.pop(index)
        self.index.forgetTask(task.uuid)
        self.taskListModified.emit()

    # TODO: move task to a specific index
    # def moveTask(self, taskUuid: UUID, index: int): ...
    def setTaskField(self, taskUuid: UUID, fieldId: int, value: Any):
        # TODO: undo/redo
        task = self.index.taskByUuid(taskUuid)
        if task is None:
            # TODO: invalid mapping
            return

        task.schema().fields[fieldId].setValue(task, value)

    # TODO: accept index?
    # TODO: other waypoint parameters
    def addWaypoint(self, taskUuid: UUID, latitude: float, longitude: float,
                    waypointUuid: UUID | None = None) -> None:
        task = self.index.taskByUuid(taskUuid)
        if task is None:
            # TODO: invalid mapping
            return

        assert(isinstance(task, MultiWaypointTask))

        waypoint = task.waypointClass(
            latitude = latitude,
            longitude = longitude,
            uuid = waypointUuid or uuid4()
        )

        feat = self.layerBridge._waypointToFeature(taskUuid, waypoint)
        cmd = AddWaypointUndoCommand(self, task, waypoint)

        with self.layerBridge.customEditCommand("Add waypoint"):
            self.layerBridge.waypointLayer.addFeature(feat)
            self._keepalive_undo.append(cmd)
            self.layerBridge.waypointLayer.undoStack().push(cmd)

        # task.waypoints.append(waypoint)
        # self.index.registerWaypoint(taskUuid, waypoint)

    def _addTaskWaypointAt(self, task: MultiWaypointTask, waypoint: Waypoint,
                           index: int) -> None:
        self.beforeWaypointAdded.emit(task.uuid, waypoint.uuid, index)
        task.waypoints.insert(index, waypoint)
        self.index.registerWaypoint(task.uuid, waypoint)
        self.waypointAdded.emit(waypoint.uuid)

    def deleteWaypoint(self, waypointUuid: UUID):
        task = self.index.taskByWaypointUuid(waypointUuid)
        if task is None:
            # TODO: invalid mapping
            return

        assert(isinstance(task, WaypointTask))

        waypoint = self.index.waypointByUuid(waypointUuid)
        assert(isinstance(waypoint, task.waypointClass))

        fid = self.layerBridge.featureIdForWaypointUuid(waypointUuid)
        assert(fid is not None)

        cmd: MissionUndoCommand
        match task:
            case SingleWaypointTask():
                # Deleting a whole task!
                cmd = DeleteTaskUndoCommand(self, task)
                text = "Delete task"
            case MultiWaypointTask():
                # Just deleting a waypoint from a list
                cmd = DeleteWaypointUndoCommand(self, task, waypoint)
                text = "Delete waypoint"
            case _ as unreachable:
                assert_never(unreachable)

        with self.layerBridge.customEditCommand(text):
            self.layerBridge.waypointLayer.deleteFeature(fid)
            self._keepalive_undo.append(cmd)
            self.layerBridge.waypointLayer.undoStack().push(cmd)

    def _deleteTaskWaypointAt(self, task: MultiWaypointTask, index: int) -> None:
        waypoint = task.waypoints[index]
        self.beforeWaypointDeleted.emit(waypoint.uuid)
        task.waypoints.pop(index)
        self.index.forgetWaypoint(waypoint.uuid)
        self.waypointDeleted.emit(task.uuid, waypoint.uuid, index)

    def setWaypointPosition(self, waypointUuid: UUID, latitude: float,
                            longitude: float):
        waypoint = self.index.waypointByUuid(waypointUuid)
        if waypoint is None:
            # TODO: invalid mapping
            return

        cmd = SetWaypointPositionUndoCommand(self, waypoint, latitude, longitude)
        with self.layerBridge.customEditCommand("Move waypoint"):
            self.layerBridge.moveWaypointFeature(waypointUuid, latitude, longitude)
            self._keepalive_undo.append(cmd)
            self.layerBridge.waypointLayer.undoStack().push(cmd)

    def _setWaypointPosition(self, waypoint: Waypoint, latitude: float,
                             longitude: float):
        waypoint.latitude = latitude
        waypoint.longitude = longitude
        self.waypointChanged.emit(waypoint.uuid)

    def setWaypointField(self, waypointUuid: UUID, fieldId: int, value: Any):
        waypoint = self.index.waypointByUuid(waypointUuid)
        if waypoint is None:
            # TODO: invalid mapping
            return

        # TODO: Location should be changed via setWaypointPosition
        assert(fieldId > 1)

        oldValue = waypoint.schema().fields[fieldId].value(waypoint)
        cmd = SetWaypointFieldUndoCommand(self, waypoint, fieldId, value, oldValue)
        with self.layerBridge.customEditCommand("Modify waypoint"):
            self._keepalive_undo.append(cmd)
            self.layerBridge.waypointLayer.undoStack().push(cmd)

    def _setWaypointField(self, waypoint: Waypoint, fieldId: int, value: Any):
        waypoint.schema().fields[fieldId].setValue(waypoint, value)
        self.waypointChanged.emit(waypoint.uuid)
