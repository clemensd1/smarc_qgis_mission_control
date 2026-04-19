from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import *
from qgis.core import *

from typing import *
from uuid import UUID

from ..mission.MissionDocument import MissionDocument
from ..domain.waypoints import Waypoint
from ..domain.tasks import WaypointTask, SingleWaypointTask, MultiWaypointTask
from ..domain.schema import Schema
from .SchemaBasedModel import SchemaBasedModel

__all__ = ["WaypointListModel"]

class WaypointListModel(SchemaBasedModel):
    _doc: MissionDocument | None
    _task: WaypointTask | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._doc = None
        self._task = None

    def bind(self, doc: MissionDocument, taskUuid: UUID):
        task = doc.index.taskByUuid(taskUuid)
        if task is None:
            return
        assert(isinstance(task, WaypointTask))

        self.unbind()

        self._doc = doc
        self._task = task

        match task:
            case SingleWaypointTask(waypoint=waypoint):
                self.setItems([waypoint])
            case MultiWaypointTask(waypoints=waypoints):
                self.setItems(waypoints)
            case _ as unreachable:
                assert_never(unreachable)

        self._doc.waypointChanged.connect(self.onWaypointChanged)
        self._doc.beforeWaypointAdded.connect(self.onBeforeWaypointAdded)
        self._doc.waypointAdded.connect(self.onWaypointAdded)
        self._doc.beforeWaypointDeleted.connect(self.onBeforeWaypointDeleted)
        self._doc.waypointDeleted.connect(self.onWaypointDeleted)

    def unbind(self):
        if self._doc is not None:
            self._doc.waypointChanged.disconnect(self.onWaypointChanged)
            self._doc.beforeWaypointAdded.disconnect(self.onBeforeWaypointAdded)
            self._doc.waypointAdded.disconnect(self.onWaypointAdded)
            self._doc.beforeWaypointDeleted.disconnect(self.onBeforeWaypointDeleted)
            self._doc.waypointDeleted.disconnect(self.onWaypointDeleted)

        self._doc = None
        self._task = None
        self.setItems([])

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        flags = super().flags(index)
        if self.isEditable():
            flags |= Qt.ItemIsEditable
        return flags

    def setData(self, index: QModelIndex, value: QVariant,
                role: int = Qt.EditRole) -> bool:
        # TODO: check reference code for editability
        if role != Qt.EditRole or not self.isEditable():
            return False
        if self._doc is None or self._task is None:
            # TODO: invalid mapping
            return False

        col = index.column()
        wp  = self.item(index.row())

        # Special handling for longitude/latitude which actually influence geometry
        # present on the map layer
        field = wp.schema().fields[col]
        # TODO: assumes all fields are floats...
        if float(value) == field.value(wp):
            # No change! Nothing to do.
            return False

        if field.name in ('latitude', 'longitude'):
            if field.name == 'latitude':
                latitude = float(value)
                longitude = wp.longitude
            else:
                latitude = wp.latitude
                longitude = float(value)

            # TODO: have it return bool as status
            self._doc.setWaypointPosition(wp.uuid, latitude, longitude)
            return True
        else:
            # TODO: have it return bool as status
            self._doc.setWaypointField(wp.uuid, col, float(value))
            return True

    @pyqtSlot(UUID)
    def onWaypointChanged(self, waypointUuid: UUID):
        if self._doc is None or self._task is None:
            return

        task = self._doc.index.taskByWaypointUuid(waypointUuid)
        if task is None or task.uuid != self._task.uuid:
            # Change to a task not managed by this model
            return

        match self._task:
            case MultiWaypointTask():
                waypointIndex = self._doc.index.indexForWaypointUuid(waypointUuid)
                if waypointIndex is None:
                    # TODO: invalid mapping
                    return
            case SingleWaypointTask():
                waypointIndex = 0

        waypointSchema = self._task.waypointClass.schema()

        idxStart = self.index(waypointIndex, 0)
        idxEnd = self.index(waypointIndex, len(waypointSchema.fields) - 1)
        self.dataChanged.emit(idxStart, idxEnd, [Qt.DisplayRole, Qt.EditRole])

    @pyqtSlot(UUID, UUID, int)
    def onBeforeWaypointAdded(self, taskUuid: UUID, waypointUuid: UUID, index: int):
        if self._doc is None or self._task is None:
            return

        if taskUuid != self._task.uuid:
            # Change to a task not managed by this model
            return

        self.beginInsertRows(QModelIndex(), index, index)

    @pyqtSlot(UUID)
    def onWaypointAdded(self, waypointUuid: UUID):
        if self._doc is None or self._task is None:
            return

        task = self._doc.index.taskByWaypointUuid(waypointUuid)
        if task is None or task.uuid != self._task.uuid:
            # Change to a task not managed by this model
            return

        self.endInsertRows()

    @pyqtSlot(UUID)
    def onBeforeWaypointDeleted(self, waypointUuid: UUID):
        if self._doc is None or self._task is None:
            return

        task = self._doc.index.taskByWaypointUuid(waypointUuid)
        if task is None or task.uuid != self._task.uuid:
            # Change to a task not managed by this model
            return

        match self._task:
            case MultiWaypointTask():
                waypointIndex = self._doc.index.indexForWaypointUuid(waypointUuid)
                if waypointIndex is None:
                    # TODO: invalid mapping
                    return
            case SingleWaypointTask():
                waypointIndex = 0

        self.beginRemoveRows(QModelIndex(), waypointIndex, waypointIndex)

    @pyqtSlot(UUID, UUID, int)
    def onWaypointDeleted(self, taskUuid: UUID, waypointUuid: UUID, index: int):
        if self._doc is None or self._task is None:
            return

        if taskUuid != self._task.uuid:
            # Change to a task not managed by this model
            return

        self.endRemoveRows()
