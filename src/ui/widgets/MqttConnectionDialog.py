from qgis.PyQt.QtWidgets import QWidget, QDialog
from qgis.PyQt.QtCore import pyqtSignal

from ..generated.MqttConnectionDialogUi import Ui_MqttConnectionDialog

__all__ = ["MqttConnectionDialog"]


class MqttConnectionDialog(QDialog):
    connectRequested = pyqtSignal(str, int, str, str, str)
    disconnectRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.ui = Ui_MqttConnectionDialog()
        self.ui.setupUi(self)

        # Disable resizing, ensuring size provided in QtDesigner
        self.setFixedSize(self.size())

        # Wire callbacks to connect/disconnect buttons
        self.ui.connectButton.clicked.connect(self._onConnect)
        self.ui.disconnectButton.clicked.connect(self._onDisconnect)
        self.ui.closeButton.clicked.connect(self.reject)

    def ip(self) -> str:
        return self.ui.lineEditIp.text().strip()

    def port(self) -> int:
        return int(self.ui.lineEditPort.text().strip())

    def username(self) -> str | None:
        value = self.ui.lineEditUsername.text().strip()
        return value if value else None

    def password(self) -> str | None:
        value = self.ui.lineEditPassword.text().strip()
        return value if value else None

    def context(self) -> str:
        return self.ui.lineEditContext.text().strip()

    def _onConnect(self):
        self.connectRequested.emit(
            self.ip(), self.port(), self.username(), self.password(), self.context()
        )

    def _onDisconnect(self):
        self.disconnectRequested.emit()