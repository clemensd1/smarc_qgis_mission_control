from typing import assert_never
from enum import StrEnum
from uuid import UUID
from dataclasses import dataclass
from contextlib import contextmanager

from qgis.PyQt.QtCore import pyqtSlot, pyqtSignal, QObject, QVariant
from qgis.core import QgsProject, QgsField, QgsFeature, QgsVectorLayer, QgsGeometry, QgsPointXY

from ..domain.missionplan import MissionPlan
from ..domain.waypoints import Waypoint
from ..domain.tasks import Task, SingleWaypointTask, MultiWaypointTask


__all__ = ["MissionLayerBridge"]

@dataclass
class JournalEntry:
    fid: int

@dataclass
class FeatureAddedEntry(JournalEntry):
    taskUuid: UUID
    waypointUuid: UUID
    latitude: float
    longitude: float

@dataclass
class FeatureDeletedEntry(JournalEntry):
    ...

@dataclass
class FeatureMovedEntry(JournalEntry):
    latitude: float
    longitude: float

class MissionLayerBridge(QObject):
    class State(StrEnum):
        DEFAULT = 'default'
        QGIS_EDIT_COMMAND = 'qgis-edit-command'
        CUSTOM_EDIT_COMMAND = 'custom-edit-command'
        REPLAYING_QGIS_COMMAND = 'replaying-qgis-command'

    waypointMoved = pyqtSignal(UUID, QgsPointXY)
    waypointAdded = pyqtSignal(UUID, UUID, QgsPointXY)
    waypointDeleted = pyqtSignal(UUID)

    _fidToWaypointUuid: dict[int, UUID]
    _waypointUuidToFid: dict[UUID, int]
    _state: State
    _journal: list[JournalEntry]

    waypointLayer: QgsVectorLayer
    trackLayer: QgsVectorLayer


    def __init__(self, plan: MissionPlan, parent: QObject | None = None) -> None:
        super().__init__(parent)

        self._fidToWaypointUuid = {}
        self._waypointUuidToFid = {}
        self._state = self.State.DEFAULT
        self._journal = []

        self._initializeLayers(plan.uuid)
        self._populateLayers(plan)

    def _initializeLayers(self, planUuid: UUID) -> None:
        # Setup waypoint layer
        qgs = QgsProject.instance()
        # Remove any stale layers
        matching = qgs.mapLayersByName(f'SMaRCMissionWaypoints-{planUuid}')
        qgs.removeMapLayers([l.id() for l in matching])

        # Setup our layer
        self.waypointLayer = QgsVectorLayer(
            'point?crs=epsg:4326',
            f'SMaRCMissionWaypoints-{planUuid}',
            'memory'
        )
        self.waypointLayer.dataProvider().addAttributes([
            QgsField('task-uuid', QVariant.String),
            QgsField('waypoint-uuid', QVariant.String),
            QgsField('tolerance', QVariant.Double)
        ])
        self.waypointLayer.updateFields()

        qgs.addMapLayer(self.waypointLayer)

        self.waypointLayer.featureAdded.connect(self.onFeatureAdded)
        self.waypointLayer.featureDeleted.connect(self.onFeatureDeleted)
        self.waypointLayer.geometryChanged.connect(self.onGeometryChanged)

        self.waypointLayer.editCommandStarted.connect(self.onEditCommandStarted)
        self.waypointLayer.editCommandEnded.connect(self.onEditCommandEnded)

    def _populateLayers(self, plan: MissionPlan) -> None:
        for task in plan.tasks:
            self._importTask(task)

    def _importTask(self, task: Task) -> None:
        match task:
            case SingleWaypointTask(waypoint=waypoint):
                self._importWaypoint(task.uuid, waypoint)
            case MultiWaypointTask(waypoints=waypoints):
                for waypoint in waypoints:
                    self._importWaypoint(task.uuid, waypoint)
            case _:
                # Task has no waypoints, which currently means no map presence
                ...

    def _importWaypoint(self, taskUuid: UUID, waypoint: Waypoint) -> None:
        feat = self._waypointToFeature(taskUuid, waypoint)
        self.waypointLayer.dataProvider().addFeature(feat)

        self._fidToWaypointUuid[feat.id()] = waypoint.uuid
        self._waypointUuidToFid[waypoint.uuid] = feat.id()

    def _waypointToFeature(self, taskUuid: UUID, waypoint: Waypoint) -> QgsFeature:
        feat = QgsFeature(self.waypointLayer.fields())
        point = QgsPointXY(waypoint.longitude, waypoint.latitude)
        geom = QgsGeometry.fromPointXY(point)
        feat.setGeometry(geom)
        feat.setAttribute('task-uuid', str(taskUuid))
        feat.setAttribute('waypoint-uuid', str(waypoint.uuid))

        return feat

    def featureIdForWaypointUuid(self, waypointUuid: UUID) -> int | None:
        return self._waypointUuidToFid.get(waypointUuid)

    def waypointUuidForFeatureId(self, featureId: int) -> UUID | None:
        return self._fidToWaypointUuid.get(featureId)

    @pyqtSlot(str)
    def onEditCommandStarted(self, text: str):
        print('onEditCommandStarted', text)
        if self._state is self.State.DEFAULT:
            self._state = self.State.QGIS_EDIT_COMMAND

    @pyqtSlot('QgsFeatureId')
    def onFeatureAdded(self, fid: int) -> None:
        print('onFeatureAdded', fid)
        feat = self.waypointLayer.getFeature(fid)
        waypointUuid = UUID(feat.attribute('waypoint-uuid'))

        self._fidToWaypointUuid[fid] = waypointUuid
        self._waypointUuidToFid[waypointUuid] = fid

        match self._state:
            case self.State.DEFAULT:
                ...
            case self.State.QGIS_EDIT_COMMAND:
                taskUuid = UUID(feat.attribute('task-uuid'))
                point = feat.geometry().asPoint()
                entry = FeatureAddedEntry(fid, taskUuid, waypointUuid, point.y(), point.x())
                self._journal.append(entry)
            case self.State.CUSTOM_EDIT_COMMAND:
                ...
            case self.State.REPLAYING_QGIS_COMMAND:
                ...
            case _ as unreachable:
                assert_never(unreachable)

    @pyqtSlot('QgsFeatureId', QgsGeometry)
    def onGeometryChanged(self, fid: int, geom: QgsGeometry) -> None:
        print('onGeometryChanged', fid, geom)

        match self._state:
            case self.State.DEFAULT:
                ...
            case self.State.QGIS_EDIT_COMMAND:
                feat = self.waypointLayer.getFeature(fid)
                point = feat.geometry().asPoint()
                entry = FeatureMovedEntry(fid, point.y(), point.x())
                self._journal.append(entry)
            case self.State.CUSTOM_EDIT_COMMAND:
                ...
            case self.State.REPLAYING_QGIS_COMMAND:
                ...
            case _ as unreachable:
                assert_never(unreachable)

    @pyqtSlot('QgsFeatureId')
    def onFeatureDeleted(self, fid: int) -> None:
        print('onFeatureDeleted', fid)

        match self._state:
            case self.State.DEFAULT:
                ...
            case self.State.QGIS_EDIT_COMMAND:
                entry = FeatureDeletedEntry(fid)
                self._journal.append(entry)
            case self.State.CUSTOM_EDIT_COMMAND:
                ...
            case self.State.REPLAYING_QGIS_COMMAND:
                ...
            case _ as unreachable:
                assert_never(unreachable)

        waypointUuid = self.waypointUuidForFeatureId(fid)
        assert(waypointUuid)
        # if waypointUuid is not None:
        del self._waypointUuidToFid[waypointUuid]
        del self._fidToWaypointUuid[fid]

    @pyqtSlot()
    def onEditCommandEnded(self):
        print('onEditCommandEnded')
        if self._state is not self.State.QGIS_EDIT_COMMAND:
            return

        if not len(self._journal):
            self._state = self.State.DEFAULT
            return

        self._state = self.State.REPLAYING_QGIS_COMMAND

        # Get rid of the command which just happened
        self.waypointLayer.undoStack().undo()

        # TODO: more specific text
        self.waypointLayer.beginEditCommand("Modify waypoints")

        waypointUuid: UUID | None
        for entry in self._journal:
            print(entry)
            match entry:
                case FeatureAddedEntry(fid, taskUuid, waypointUuid, latitude, longitude):
                    assert(waypointUuid)
                    self.parent().addWaypoint(taskUuid, latitude, longitude, waypointUuid)
                case FeatureDeletedEntry(fid):
                    waypointUuid = self.waypointUuidForFeatureId(fid)
                    assert(waypointUuid is not None)
                    self.parent().deleteWaypoint(waypointUuid)
                case FeatureMovedEntry(fid, latitude, longitude):
                    waypointUuid = self.waypointUuidForFeatureId(fid)
                    assert(waypointUuid is not None)
                    self.parent().setWaypointPosition(waypointUuid, latitude, longitude)

        self._journal = []
        self._state = self.State.DEFAULT

        self.waypointLayer.endEditCommand()

    @contextmanager
    def customEditCommand(self, text: str):
        oldState = self._state
        self._state = self.State.CUSTOM_EDIT_COMMAND
        self.waypointLayer.beginEditCommand(text)
        try:
            yield
        except:
            self.waypointLayer.destroyEditCommand()
            raise
        else:
            self.waypointLayer.endEditCommand()
        finally:
            self._state = oldState

    def moveWaypointFeature(self, waypointUuid: UUID, latitude: float,
                            longitude: float):
        fid = self.featureIdForWaypointUuid(waypointUuid)
        if fid is None:
            # TODO: Invalid mapping
            return

        # TODO: confirm editable?
        point = QgsPointXY(longitude, latitude)
        self.waypointLayer.changeGeometry(fid, QgsGeometry.fromPointXY(point))
