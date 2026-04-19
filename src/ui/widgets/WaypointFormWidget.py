from qgis.PyQt.QtWidgets import QWidget
from qgis.core import QgsApplication, QgsVectorLayer

from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import *
from qgis.core import *

from typing import Type
from uuid import UUID

from ...mission.MissionContext import MissionContext
from ...mission.MissionDocument import MissionDocument
from ...domain.tasks import SingleWaypointTask
from ...model.WaypointListModel import WaypointListModel
from ..generated.WaypointFormWidgetUi import Ui_WaypointFormWidget
from .AutomaticFormWidget import AutomaticFormWidget

__all__ = ['WaypointFormWidget']


class WaypointFormWidget(AutomaticFormWidget):
    _taskCls: Type[SingleWaypointTask]
    _model: WaypointListModel

    selectLocationRequested = pyqtSignal(QAction, UUID, bool)

    def __init__(self, taskCls: Type[SingleWaypointTask],
                 missionContext: MissionContext, parent: QWidget | None = None):
        schema = taskCls.waypointClass.schema()
        self._model = WaypointListModel(schema, longHeaders = True)
        super().__init__(self._model, parent)

        self._taskCls = taskCls
        self._missionContext = missionContext

        self.ui = Ui_WaypointFormWidget()
        self.ui.setupUi(self)

        self.setup()

    def setup(self):
        self.buildForm(self.ui.waypointForm)

        # Respect edit mode
        self._missionContext.editModeChanged.connect(
            self.onEditModeChanged
        )

        # Handling of the waypoint map tools
        # TODO:
        self.selectLocationRequested.connect(
            self._missionContext.mapManager.onSelectLocationRequested
        )

        # Button "Select Location"
        selectLocationAction = QAction(
            QgsApplication.getThemeIcon("mActionPanTo.svg"),
            "..."
        )
        selectLocationAction.setCheckable(self.ui.buttonSelectLocation.isCheckable())
        selectLocationAction.toggled.connect(self.onSelectLocationToggled)
        self.ui.buttonSelectLocation.setDefaultAction(selectLocationAction)
        # self.ui.buttonSelectLocation.clicked.connect(self.onSelectLocationToggled)


    def bind(self, doc: MissionDocument, taskUuid: UUID):
        self._model.bind(doc, taskUuid)
        self._mapper.toFirst()

    def unbind(self):
        self._model.unbind()

    @pyqtSlot(bool)
    def onEditModeChanged(self, editMode: bool):
        self._model.setEditable(editMode)
        self.ui.buttonSelectLocation.setEnabled(editMode)

    @pyqtSlot(bool)
    def onSelectLocationToggled(self, state: bool):
        self.selectLocationRequested.emit(
            self.ui.buttonSelectLocation.defaultAction(),
            self._model.item(0).uuid,
            state
        )
