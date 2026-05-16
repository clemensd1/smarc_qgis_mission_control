from pathlib import Path

from qgis.PyQt.QtCore import QObject, Qt, QSize, pyqtSlot
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDialog, QSizePolicy, QWidget, QMessageBox
from qgis.gui import QgisInterface
# from qgis.core import QgsProject

from .context.FleetContext import FleetContext
from .mission.MissionContext import MissionContext
from .ui.widgets.MissionControlDockWidget import MissionControlDockWidget
from .ui.widgets.MqttConnectionDialog import MqttConnectionDialog


class SMaRCMissionControlPlugin(QObject):
    def __init__(self, iface: QgisInterface):
        super().__init__()
        self.iface = iface
        self.menu = None
        self.toolbar = None
        self.toolbarSpacer = None
        self.mqttAction = None
        self.mqttButton = None
        self.missionControlDock = None
        self.missionControlAction = None

        # set path and path to svg files
        self.plugin_dir = Path(__file__).parent
        self.smarc_icon_slim = QIcon(
            str(self.plugin_dir / "ui" / "svg" / "smarclogo-slim.png")
        )
        self.smarc_icon = QIcon(
            str(self.plugin_dir / "ui" / "svg" / "smarclogo1.png")
        )

        self.fleetContext = FleetContext(self)
        self.missionContext = MissionContext(self)

        # TODO: this is a hack to easily access the plugin instance
        iface.smarcmcp = self
    
    def initGui(self):
        """Called when the plugin is activated."""

        self.menu = self.iface.pluginMenu().addMenu(
            self.smarc_icon,
            "&SMaRC Mission Control",
        ) # filename to custom icon should not contain special characters

        self.toolbar = self.iface.addToolBar("SMaRC Mission Control")
        self.toolbar.setObjectName("SMaRC Mission Control")
        self.toolbar.setIconSize(QSize(84, 24)) # default is (24,24)

        self.missionControlDock = MissionControlDockWidget(
            self.missionContext,
            self.fleetContext,
            self.iface.mainWindow(),
        )
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.missionControlDock)
        self.missionControlDock.hide()

        self.missionControlAction = self.missionControlDock.toggleViewAction()
        self.missionControlAction.setIcon(
            self.smarc_icon_slim
        )
        self.missionControlAction.setText("Open Mission Control")
        self.menu.addAction(self.missionControlAction)
        self.menu.addSeparator()
        self.toolbar.addAction(self.missionControlAction)
        
        # Spacer
        self.toolbarSpacer = QWidget(self.iface.mainWindow())
        self.toolbarSpacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(self.toolbarSpacer)

        # Mqtt button
        self.mqttAction = QAction("MQTT", self.iface.mainWindow())
        self.mqttAction.setToolTip("Connect to MQTT broker")
        self.mqttAction.triggered.connect(self.onMqttActionClicked)
        self.toolbar.addAction(self.mqttAction)
        self.mqttButton = self.toolbar.widgetForAction(self.mqttAction)
        self.set_mqtt_button_style(False) # set color feedback of MQTT button to "disconnected"
        

    def unload(self):
        """Called when the plugin is deactivated."""
        self.fleetContext.mqtt.disconnect()

        # TODO: can be cleaner
        # qgs = QgsProject.instance()
        # for doc in self.missionContext._missionDocuments.values():
        #     qgs.removeMapLayer(doc.layerBridge.waypointLayer)

        # qgs.removeMapLayer(self.fleetContext.mapManager._waypointLayer)

        # TODO: move into mapManager (as to not reach into _vehicles here)
        # TODO: implement self.fleetContext.mapManager.cleanup()
        for vehicle in self.fleetContext.mapManager._vehicles.values():
            self.iface.mapCanvas().scene().removeItem(vehicle.trackRubberBand)

        if self.menu is not None:
            self.iface.pluginMenu().removeAction(self.menu.menuAction())
            self.menu.deleteLater()
            self.menu = None

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

        self.missionControlAction = None
        self.mqttButton = None
        self.iface.smarcmcp = None

    def set_mqtt_button_style(self, connected: bool):
        if not self.mqttButton:
            return

        background = "#d9ead3" if connected else "#f6c7b3"

        self.mqttButton.setStyleSheet(f"""
            background-color: {background};
            color: black;
            border-radius: 4px;
            padding: 4px 10px;
            font: bold 10px;
            font-family: Arial;
        """)

    @pyqtSlot(bool)
    def onMqttActionClicked(self, checked: bool):
        dialog = MqttConnectionDialog(self.iface.mainWindow())
        dialog.connectRequested.connect(self._onMqttConnect)
        dialog.disconnectRequested.connect(self._onMqttDisconnect)
        dialog.exec()

    def _onMqttConnect(self, ip, port, user, pw, ctx):
        try:
            # TODO: subscribing to certain context other than #
            self.fleetContext.mqtt.connect(ip, port, user, pw, ctx)
            self.set_mqtt_button_style(self.fleetContext.mqtt._connected)
        except Exception as e:
            self.set_mqtt_button_style(False)
            QMessageBox.warning(
                self.iface.mainWindow(),
                "MQTT connection failed",
                str(e),
            )
            return

    def _onMqttDisconnect(self):
        self.fleetContext.mqtt.disconnect()
        self.set_mqtt_button_style(self.fleetContext.mqtt._connected)