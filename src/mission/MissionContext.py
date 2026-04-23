from pathlib import Path
from uuid import UUID, uuid4
import json

from qgis.PyQt.QtCore import pyqtSlot, pyqtSignal, QObject
from qgis.core import QgsPointXY

from .MissionMapManager import MissionMapManager
from .MissionDocument import MissionDocument
from ..domain.missionplan import MissionPlan
from ..domain.tasks import *


__all__ = ["MissionContext"]

class MissionContext(QObject):
    missionLoaded = pyqtSignal(MissionDocument)
    firstMissionLoaded = pyqtSignal(MissionDocument)
    activeMissionChanged = pyqtSignal(MissionDocument)

    editModeChanged = pyqtSignal(bool)
    editingStarted = pyqtSignal()
    editingFinished = pyqtSignal()

    taskListModified = pyqtSignal()

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
        doc.taskListModified.disconnect(self.taskListModified)

    def _bindDocument(self, doc: MissionDocument):
        doc.editModeChanged.connect(self.editModeChanged)
        doc.editingStarted.connect(self.editingStarted)
        doc.editingFinished.connect(self.editingFinished)
        doc.taskListModified.connect(self.taskListModified)

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

        self.activeMissionChanged.emit(doc)

        # Ensure good state for widgets
        self.editingFinished.emit()
        self.editModeChanged.emit(False)

    @pyqtSlot(SingleWaypointTask.Pending, QgsPointXY)
    # TODO: should this be here?
    def onInitialWaypointPicked(self, pendingTask: SingleWaypointTask.Pending,
                                point: QgsPointXY):
        doc = self.activeDocument()
        if doc is None:
            # TODO: invalid mapping
            return

        doc.addSingleWaypointTask(pendingTask, point)
