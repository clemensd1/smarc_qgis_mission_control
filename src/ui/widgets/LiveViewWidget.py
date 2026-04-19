from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import *
from qgis.core import *
from qgis.utils import iface

from ...context.FleetContext import FleetContext
from ..generated.LiveViewWidgetUi import Ui_LiveViewWidget
from .VehicleLiveViewWidget import VehicleLiveViewWidget


class LiveViewWidget(QWidget):
    _fleetContext: FleetContext
    _vehicles: dict[str, VehicleLiveViewWidget]

    def __init__(self, fleetContext: FleetContext,
                 parent: QWidget | None = None):
        super().__init__(parent)

        self._fleetContext = fleetContext
        self._vehicles = {}

        self.ui = Ui_LiveViewWidget()
        self.ui.setupUi(self)
        self.setupUi2()

        self._fleetContext.state.vehicleDiscovered.connect(self.onVehicleDiscovered)
        self._fleetContext.state.vehicleUpdated.connect(self.onVehicleUpdated)
        self._fleetContext.state.vehicleExpired.connect(self.onVehicleExpired)

    def setupUi2(self):
        # Align items in the scroll area to the top
        self.ui.vehicleListVLayout.setAlignment(Qt.AlignTop)

        self.ui.vehicleListScrollArea.viewport().setAutoFillBackground(False)
        self.ui.vehicleListScrollArea.widget().setAutoFillBackground(False)

    @pyqtSlot(str)
    def onVehicleDiscovered(self, vehicleTopic: str):
        if not vehicleTopic in self._vehicles:
            widget = VehicleLiveViewWidget(
                vehicleTopic,
                self.ui.vehicleList
            )

            # Set initial button color
            state = self._fleetContext.state.vehicleState(vehicleTopic)
            if state is not None:
                widget.ui.mapColorButton.setColor(state.mapColor)

            # Connect signals
            widget.mapColorChanged.connect(
                self._fleetContext.mapManager.onMapColorChanged
            )
            widget.showOnMapChanged.connect(
                self._fleetContext.mapManager.onShowOnMapChanged
            )
            widget.lookAtRequested.connect(
                self._fleetContext.mapManager.onLookAtRequested
            )

            self._vehicles[vehicleTopic] = widget
            self.ui.vehicleListVLayout.addWidget(widget)

    @pyqtSlot(str)
    def onVehicleUpdated(self, vehicleTopic: str):
        state = self._fleetContext.state.vehicleState(vehicleTopic)
        assert(state)
        self._vehicles[vehicleTopic].updateState(state)

    @pyqtSlot(str)
    def onVehicleExpired(self, vehicleTopic: str):
        ...

