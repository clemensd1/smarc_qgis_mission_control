from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import *
from qgis.core import *

from .context.FleetContext import FleetContext
from .mission.MissionContext import MissionContext
from .ui.widgets.MissionControlDockWidget import MissionControlDockWidget
from .ui.widgets.MqttConnectionDialog import MqttConnectionDialog


class SMaRCMissionControlPlugin(QObject):
    def __init__(self, iface: QgisInterface):
        super().__init__()
        self.iface = iface
        self.toolbar = None
        self.toolbarSpacer = None
        self.mqttAction = None
        self.missionControlDock = None
        self.missionControlAction = None

        self.fleetContext = FleetContext(self)
        self.missionContext = MissionContext(self)

        # TODO: this is a hack to easily access the plugin instance
        iface.smarcmcp = self

    def initGui(self):
        """Called when the plugin is activated."""
        self.toolbar = self.iface.addToolBar("SMaRC Mission Control")
        self.toolbar.setObjectName("SMaRC Mission Control")

        self.missionControlDock = MissionControlDockWidget(
            self.missionContext,
            self.fleetContext,
            self.iface.mainWindow(),
        )
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.missionControlDock)
        self.missionControlDock.hide()

        self.missionControlAction = self.missionControlDock.toggleViewAction()
        self.missionControlAction.setIcon(
            QgsApplication.getThemeIcon("mLayoutItemTable.svg")
        )
        self.missionControlAction.setText(self.tr("Open Mission Control"))
        self.toolbar.addAction(self.missionControlAction)

        # Spacer
        self.toolbarSpacer = QWidget(self.iface.mainWindow())
        self.toolbarSpacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(self.toolbarSpacer)

        self.mqttAction = QAction(self.tr('MQTT'), self.iface.mainWindow())
        self.mqttAction.triggered.connect(self.onMqttActionClicked)
        self.toolbar.addAction(self.mqttAction)

        self.iface.addPluginToMenu("SMaRC Mission Control", self.missionControlAction)
        # self.iface.addPluginToMenu("MQTT Connection", self.mqttAction)

    def unload(self):
        """Called when the plugin is deactivated."""
        self.fleetContext.mqtt.disconnect()

        # TODO: can be cleaner
        qgs = QgsProject.instance()
        # for doc in self.missionContext._missionDocuments.values():
        #     qgs.removeMapLayer(doc.layerBridge.waypointLayer)

        # qgs.removeMapLayer(self.fleetContext.mapManager._waypointLayer)

        for vehicle in self.fleetContext.mapManager._vehicles.values():
            self.iface.mapCanvas().scene().removeItem(vehicle.trackRubberBand)

        if self.missionControlAction is not None:
            self.iface.removePluginMenu(
                "SMaRC Mission Control", self.missionControlAction
            )
            self.missionControlAction = None

        if self.mqttAction is not None:
            self.mqttAction.deleteLater()
            self.mqttAction = None
        #     self.iface.removePluginMenu(
        #         "SMaRC Mission Control", self.mqttAction
        #     )

        if self.toolbarSpacer is not None:
            self.toolbarSpacer.deleteLater()
            self.toolbarSpacer = None

        if self.missionControlDock is not None:
            self.missionControlDock.deleteLater()
            self.missionControlDock = None

        if self.toolbar is not None:
            self.toolbar.deleteLater()
            self.toolbar = None

        self.iface.smarcmcp = None

    @pyqtSlot(bool)
    def onMqttActionClicked(self, checked: bool):
        dialog = MqttConnectionDialog(self.iface.mainWindow())
        if dialog.exec() != QDialog.Accepted:
            return

        self.fleetContext.mqtt.connect(dialog.ip(), dialog.port(), dialog.username(),
                                       dialog.password(), dialog.context())
