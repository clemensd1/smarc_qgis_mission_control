from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import *
from qgis.core import *

from typing import *
from dataclasses import replace as dtReplace
from uuid import UUID, uuid4

from ...domain.tasks import Task, SingleWaypointTask, MultiWaypointTask
from ...domain.schema import Schema
from ...mission.MissionContext import MissionContext
from ...mission.MissionDocument import MissionDocument

# from ..tasksUi import TaskUiRegistry

from .TaskParamsFormWidget import TaskParamsFormWidget
from .WaypointFormWidget import WaypointFormWidget
from .WaypointTableWidget import WaypointTableWidget

__all__ = ['TaskEditorWidget']

class TaskEditorWidget(QWidget):
    paramsWidget: TaskParamsFormWidget | None
    waypointWidget: WaypointFormWidget | WaypointTableWidget | None

    def __init__(self, taskCls: Type[Task], missionContext: MissionContext,
                 parent: QWidget | None = None):
        super().__init__(parent)

        self.paramsWidget = None
        self.waypointWidget = None

        if len(taskCls.schema().fields):
            # Task has parameters
            self.paramsWidget = TaskParamsFormWidget(taskCls, self)

        # Build waypoint view
        if issubclass(taskCls, SingleWaypointTask):
            self.waypointWidget = WaypointFormWidget(taskCls, missionContext, self)
        elif issubclass(taskCls, MultiWaypointTask):
            self.waypointWidget = WaypointTableWidget(taskCls, missionContext, self)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(0, 0, 0, 0)

        self._separator = None
        if self.paramsWidget is not None:
            # Task has at least parameters
            self._layout.addWidget(self.paramsWidget)
            if self.waypointWidget is not None:
                # Task has parameters and waypoint data
                self._separator = self.buildSeparatorWidget()
                self._layout.addWidget(self._separator)
                self._layout.addWidget(self.waypointWidget)
                # Make sure waypoint area takes up most space
                self._layout.setStretch(2, 1)
        elif self.waypointWidget is not None:
            # Task has only waypoint data
            self._layout.addWidget(self.waypointWidget)
        else:
            # Task has neither parameters nor waypoint data
            # TODO: warn? or is this OK?
            pass

        self._taskCls = taskCls

    def buildSeparatorWidget(self) -> QFrame:
        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        return sep

    def bind(self, doc: MissionDocument, taskUuid: UUID):
        if self.paramsWidget:
            self.paramsWidget.bind(doc, taskUuid)
        if self.waypointWidget:
            self.waypointWidget.bind(doc, taskUuid)

    def unbind(self):
        if self.paramsWidget:
            self.paramsWidget.unbind()
        if self.waypointWidget:
            self.waypointWidget.unbind()
