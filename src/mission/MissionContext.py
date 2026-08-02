from pathlib import Path
from uuid import UUID, uuid4
import json

from qgis.PyQt.QtCore import pyqtSlot, pyqtSignal, QObject
from qgis.core import QgsProject, QgsPointXY
from qgis.utils import iface

from .MissionMapManager import MissionMapManager
from .MissionDocument import MissionDocument
from ..domain.missionplan import MissionPlan
from ..domain.tasks import PendingWaypointTask


__all__ = ["MissionContext"]

class MissionContext(QObject):
    missionLoaded = pyqtSignal(MissionDocument)
    firstMissionLoaded = pyqtSignal(MissionDocument)
    activeMissionChanged = pyqtSignal(MissionDocument)

    editModeChanged = pyqtSignal(bool)
    editingStarted = pyqtSignal()
    editingAboutToFinish = pyqtSignal()
    editingFinished = pyqtSignal()

    beforeTaskAdded = pyqtSignal(UUID, int)
    taskAdded = pyqtSignal(UUID, int)
    taskDeleted = pyqtSignal(UUID, int)

    _missionDocuments: dict[UUID, MissionDocument]
    _activeDocument: UUID | None
    mapManager: MissionMapManager

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self._missionDocuments = {}
        self._activeDocument = None
        self.mapManager = MissionMapManager(self)
        self.mapManager.initialWaypointPicked.connect(self.onInitialWaypointPicked)

    def _unbindDocument(self, doc: MissionDocument):
        doc.editModeChanged.disconnect(self.editModeChanged)
        doc.editingStarted.disconnect(self.editingStarted)
        doc.editingFinished.disconnect(self.editingFinished)

        doc.beforeTaskAdded.disconnect(self.beforeTaskAdded)
        doc.taskAdded.disconnect(self.taskAdded)
        doc.taskDeleted.disconnect(self.taskDeleted)

    def _bindDocument(self, doc: MissionDocument):
        doc.editModeChanged.connect(self.editModeChanged)
        doc.editingStarted.connect(self.editingStarted)
        doc.editingFinished.connect(self.editingFinished)

        doc.beforeTaskAdded.connect(self.beforeTaskAdded)
        doc.taskAdded.connect(self.taskAdded)
        doc.taskDeleted.connect(self.taskDeleted)

    def activeDocument(self) -> MissionDocument | None:
        if self._activeDocument is None:
            return None
        return self._missionDocuments.get(self._activeDocument)

    def newMission(self, description: str, path: str | Path):
        # TODO: Bit hacky
        p = Path(path)
        plan = MissionPlan(
            name = "seq",
            description = description
        )
        with p.open('w') as fp:
            json.dump(plan.toJson(), fp, indent = 4)

        self.loadMissionFromFile(p)

    def loadMissionFromFile(self, path: str | Path):
        # TODO: check if already loaded
        doc = MissionDocument.fromFile(Path(path), self)
        self._missionDocuments[doc.plan.uuid] = doc

        if len(self._missionDocuments) == 1:
            # First mission plan
            self.firstMissionLoaded.emit(doc)

        self.missionLoaded.emit(doc)

    def saveMission(self):
        doc = self.activeDocument()
        if doc is None:
            return

        with doc.path.open('w') as fp:
            json.dump(doc.plan.toJson(), fp, indent = 4)

    @pyqtSlot(UUID)
    def changeActiveMission(self, planUuid: UUID):
        doc = self.activeDocument()
        if doc is not None:
            self._unbindDocument(doc)

        assert(planUuid in self._missionDocuments)
        self._activeDocument = planUuid

        doc = self.activeDocument()
        assert(doc)
        self._bindDocument(doc)

        # Activate the corresponding waypoint layer
        iface.setActiveLayer(doc.layerBridge.waypointLayer)

        self.activeMissionChanged.emit(doc)

        # Ensure good state for widgets
        self.editingFinished.emit()
        self.editModeChanged.emit(False)

    @pyqtSlot(PendingWaypointTask, QgsPointXY)
    # TODO: should this be here?
    def onInitialWaypointPicked(self, pendingTask: PendingWaypointTask,
                                point: QgsPointXY):
        doc = self.activeDocument()
        if doc is None:
            # TODO: invalid mapping
            return

        doc.addPendingWaypointTask(pendingTask, point)

    def prepareToFinishEditing(self) -> None:
        self.editingAboutToFinish.emit()

    def cleanup(self) -> None:
        for doc in self._missionDocuments.values():
            doc.layerBridge.cleanup()

        self._missionDocuments.clear()
        self._activeDocument = None
