from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import *
from qgis.core import *

from .MqttService import MqttService
from .FleetState import FleetState
from .FleetMapManager import FleetMapManager

class FleetContext(QObject):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self.mqtt = MqttService(self)
        self.state = FleetState(self.mqtt, self)
        self.mapManager = FleetMapManager(self.state, self)
