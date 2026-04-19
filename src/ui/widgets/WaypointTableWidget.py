from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import *
from qgis.core import *
from uuid import UUID

from typing import Type
from dataclasses import replace as dtReplace

from ...mission.MissionContext import MissionContext
from ...mission.MissionDocument import MissionDocument
from ...domain.tasks import MultiWaypointTask
from ...model.WaypointListModel import WaypointListModel
from ..generated.WaypointTableWidgetUi import Ui_WaypointTableWidget

__all__ = ['WaypointTableWidget']

class WaypointTableWidget(QWidget):
    _taskCls: Type[MultiWaypointTask]
    _model: WaypointListModel

    addWaypointRequested = pyqtSignal(QAction, int, UUID, bool)
    selectLocationRequested = pyqtSignal(QAction, UUID, bool)

    def __init__(self, taskCls: Type[MultiWaypointTask], missionContext: MissionContext,
                 parent: QWidget|None = None):
        super().__init__(parent)

        self._taskCls = taskCls
        self._missionContext = missionContext

        schema = taskCls.waypointClass.schema()
        self._model = WaypointListModel(schema, longHeaders = False)

        self.ui = Ui_WaypointTableWidget()
        self.ui.setupUi(self)

        self.setup()

    def setup(self):
        # Model setup
        self.ui.waypointTable.setModel(self._model)
        # self.ui.waypointTable.selectionModel().selectionChanged.connect(
        #     self.onWaypointSelected)

        # Respect edit mode
        self._missionContext.editModeChanged.connect(
            self.onEditModeChanged
        )

        # Handling of the waypoint map tools
        self.addWaypointRequested.connect(
            self._missionContext.mapManager.onAddWaypointRequested
        )
        self.selectLocationRequested.connect(
            self._missionContext.mapManager.onSelectLocationRequested
        )

        # Waypoint Table
        self.ui.waypointTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.ui.waypointTable.verticalHeader().setSectionResizeMode(
            QHeaderView.Fixed
        )
        self.ui.waypointTable.verticalHeader().setDefaultAlignment(
            Qt.AlignRight
        )

        # Button "Add Waypoint"
        addWaypointAction = QAction(
            QgsApplication.getThemeIcon("symbologyAdd.svg"),
            "..."
        )
        addWaypointAction.setCheckable(self.ui.buttonAddWaypoint.isCheckable())
        addWaypointAction.toggled.connect(self.onAddWaypointToggled)
        self.ui.buttonAddWaypoint.setDefaultAction(addWaypointAction)

        # Button "Remove Waypoint"
        self.ui.buttonRemoveWaypoint.setIcon(
            QgsApplication.getThemeIcon('symbologyRemove.svg')
        )
        # Button "Move Waypoint"
        self.ui.buttonMoveWaypoint.setIcon(
            QgsApplication.getThemeIcon('mActionPanTo.svg')
        )
        # Button "Move Up"
        self.ui.buttonMoveWaypointUp.setIcon(
            QgsApplication.getThemeIcon('mActionArrowUp.svg')
        )
        # Button "Move Down"
        self.ui.buttonMoveWaypointDown.setIcon(
            QgsApplication.getThemeIcon('mActionArrowDown.svg')
        )

    def bind(self, doc: MissionDocument, taskUuid: UUID):
        self._model.bind(doc, taskUuid)

    def unbind(self):
        self._model.unbind()

    @pyqtSlot(bool)
    def onEditModeChanged(self, editMode: bool):
        self._model.setEditable(editMode)
        self.ui.waypointTableSideBar.setEnabled(editMode)

    @pyqtSlot(bool)
    def onAddWaypointToggled(self, state: bool):
        assert(self._model._task)
        self.addWaypointRequested.emit(
            self.ui.buttonAddWaypoint.defaultAction(),
            self._model.rowCount(), # add after last waypoint
            self._model._task.uuid,
            state
        )

    @pyqtSlot(bool)
    def onSelectLocationToggled(self, state: bool):
        self.selectLocationRequested.emit(
            self.ui.buttonMoveWaypoint.defaultAction(),
            self._model.item(0).uuid,
            state
        )
