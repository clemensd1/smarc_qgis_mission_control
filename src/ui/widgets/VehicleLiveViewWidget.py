from math import degrees
from functools import partial

from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import *
from qgis.core import *
from qgis.utils import iface

from ...context.FleetState import VehicleState
from ..generated.VehicleLiveViewWidgetUi import Ui_VehicleLiveViewWidget


class VehicleLiveViewWidget(QWidget):
    showOnMapChanged = pyqtSignal(str, bool)
    mapColorChanged = pyqtSignal(str, QColor)
    lookAtRequested = pyqtSignal(str)

    def __init__(self, vehicleTopic: str, parent: QWidget | None = None):
        super().__init__(parent)

        self._vehicleTopic = vehicleTopic

        self.ui = Ui_VehicleLiveViewWidget()
        self.ui.setupUi(self)

        self.setup()

    def setup(self):
        self.ui.vehicleNameLabel.setText(self._vehicleTopic.split('/')[-1])
        self.ui.statusLabel.setText('Online')

        self.ui.lookAtButton.setIcon(
            # QgsApplication.getThemeIcon("gpsicons/mActionRecenter.svg")
            QgsApplication.getThemeIcon("cursors/mCapturePoint.svg")
        )
        self.ui.lookAtButton.clicked.connect(self.onLookAtClicked)

        # Actually render the bottom border
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.ui.showOnMapCheckBox.toggled.connect(self.onShowOnMapChanged)
        self.ui.mapColorButton.colorChanged.connect(self.onMapColorChanged)

    def updateState(self, state: VehicleState):
        if state.latitude is not None:
            self.ui.latValueLabel.setText(f'{state.latitude:.5f}°')
        else:
            self.ui.latValueLabel.setText('?')
        if state.longitude is not None:
            self.ui.lonValueLabel.setText(f'{state.longitude:.5f}°')
        else:
            self.ui.lonValueLabel.setText('?')
        if state.heading is not None:
            self.ui.headingValueLabel.setText(f'{state.heading:.1f}°')
        else:
            self.ui.headingValueLabel.setText('?')

        if state.depth is not None:
            self.ui.depthValueLabel.setText(f'{state.depth:.1f} m')
        else:
            self.ui.depthValueLabel.setText('?')
        if state.altitude is not None:
            self.ui.altitudeValueLabel.setText(f'{state.altitude:.1f} m')
        else:
            self.ui.altitudeValueLabel.setText('?')
        if state.speed is not None:
            self.ui.speedValueLabel.setText(f'{state.speed:.1f} m/s')
        else:
            self.ui.speedValueLabel.setText('?')

        if state.course is not None:
            self.ui.courseValueLabel.setText(f'{state.course:.1f}°')
        else:
            self.ui.courseValueLabel.setText('?')
        if state.roll is not None:
            # roll is in radians
            self.ui.rollValueLabel.setText(f'{degrees(state.roll):.1f}°')
        else:
            self.ui.rollValueLabel.setText('?')
        if state.pitch is not None:
            # pitch is in radians
            self.ui.pitchValueLabel.setText(f'{degrees(state.pitch):.1f}°')
        else:
            self.ui.pitchValueLabel.setText('?')

        if state.executingTasks is not None:
            if len(state.executingTasks):
                self.ui.taskValueLabel.setText(state.executingTasks[0].type)
            else:
                self.ui.taskValueLabel.setText('-')
        else:
            self.ui.taskValueLabel.setText('?')

    @pyqtSlot(bool)
    def onShowOnMapChanged(self, state: bool):
        self.showOnMapChanged.emit(self._vehicleTopic, state)

    @pyqtSlot(QColor)
    def onMapColorChanged(self, color: QColor):
        self.mapColorChanged.emit(self._vehicleTopic, color)

    @pyqtSlot()
    def onLookAtClicked(self):
        self.lookAtRequested.emit(self._vehicleTopic)
