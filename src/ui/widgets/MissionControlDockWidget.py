from pathlib import Path

from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import *
from qgis.core import *
from qgis.utils import iface

from ...domain.missionplan import MissionPlan
from ...mission.MissionContext import MissionContext
from ...mission.MissionDocument import MissionDocument
from ...context.FleetContext import FleetContext
from ..generated.MissionControlDockWidgetUi import Ui_MissionControlDockWidget
from .MissionPlanWidget import MissionPlanWidget
from .FleetControlWidget import FleetControlWidget
from .LiveViewWidget import LiveViewWidget


class MissionControlDockWidget(QgsDockWidget):
    def __init__(self, missionContext: MissionContext, fleetContext: FleetContext,
                 parent: QWidget | None = None):
        super().__init__(parent)

        self._missionContext = missionContext
        self._fleetContext = fleetContext

        self.ui = Ui_MissionControlDockWidget()
        self.ui.setupUi(self)
        self.setup()

    def setup(self):
        # Setup tabs
        self.ui.tabMissionPlan = MissionPlanWidget(
            self._missionContext,
            self.ui.tabWidget
        )
        self.ui.tabWidget.addTab(self.ui.tabMissionPlan, "")

        self.ui.tabFleetControl = FleetControlWidget(
            self._fleetContext.state,
            self.ui.tabWidget
        )
        # TODO: cleanup
        self.ui.tabFleetControl.uploadMissionPlanRequested.connect(
            lambda receivers: self._fleetContext.mqtt.onPublishMissionPlan(
                self._missionContext.activeDocument().plan,
                receivers
            )
        )
        self.ui.tabFleetControl.emergencyRequested.connect(
            self._fleetContext.mqtt.onEmergencySignal
        )
        self.ui.tabWidget.addTab(self.ui.tabFleetControl, "")

        self.ui.tabLiveView = LiveViewWidget(
            self._fleetContext,
            self.ui.tabWidget
        )
        self.ui.tabWidget.addTab(self.ui.tabLiveView, "")

        # Setup mission plan context
        self._missionContext.firstMissionLoaded.connect(self.onFirstMissionLoaded)
        self._missionContext.missionLoaded.connect(self.onMissionLoaded)
        self._missionContext.activeMissionChanged.connect(
            self.ui.tabMissionPlan.onActiveMissionChanged
        )
        # self._missionContext.loadMissionPlanFromFile(
        #     '/opt/workspace/references/mission-plans/seq-go_out_and_loiter.json'
        # )
        # self._missionContext.loadMissionPlanFromFile(
        #     '/opt/workspace/references/mission-plans/seq-AllTasks.json'
        # )

        # Setup mission plan controls
        self.ui.buttonEditMissionPlan.setIcon(
            QgsApplication.getThemeIcon("mActionToggleEditing.svg")
        )
        self.ui.buttonNewMissionPlan.setIcon(
            QgsApplication.getThemeIcon("mActionFileNew.svg")
        )
        self.ui.buttonOpenMissionPlan.setIcon(
            QgsApplication.getThemeIcon("mActionFileOpen.svg")
        )
        self.ui.buttonSaveMissionPlan.setIcon(
            QgsApplication.getThemeIcon("mActionFileSave.svg")
        )
        self.ui.buttonSaveMissionPlanAs.setIcon(
            QgsApplication.getThemeIcon("mActionFileSaveAs.svg")
        )

        self.ui.buttonEditMissionPlan.toggled.connect(
            self.onEditMissionPlanButtonToggled
        )
        self._missionContext.editModeChanged.connect(self.onEditModeChanged)

        self.ui.buttonNewMissionPlan.clicked.connect(self.onNewMissionPlan)
        self.ui.buttonOpenMissionPlan.clicked.connect(self.onOpenMissionPlan)
        self.ui.buttonSaveMissionPlan.clicked.connect(self.onSaveMissionPlan)
        # self.ui.buttonSaveMissionPlanAs.clicked.connect(self.onSaveMissionPlanAs)

        self.ui.missionPlanComboBox.currentIndexChanged.connect(
            lambda index: self._missionContext.changeActiveMission(
                    self.ui.missionPlanComboBox.itemData(index)
                )
        )

        self.retranslateUi2()

    def retranslateUi2(self):
        _translate = QtCore.QCoreApplication.translate
        self.ui.tabWidget.setTabText(
            self.ui.tabWidget.indexOf(self.ui.tabMissionPlan),
            _translate("MissionControlDockWidget", "Mission Pla&n"),
        )
        self.ui.tabWidget.setTabText(
            self.ui.tabWidget.indexOf(self.ui.tabFleetControl),
            _translate("MissionControlDockWidget", "&Fleet Control"),
        )
        self.ui.tabWidget.setTabText(
            self.ui.tabWidget.indexOf(self.ui.tabLiveView),
            _translate("MissionControlDockWidget", "L&ive View"),
        )

    @pyqtSlot(int)
    def onSelectedMissionPlanChanged(self, index: int):
        self._missionContext.setActiveMissionPlan(index)

    @pyqtSlot(MissionDocument)
    def onFirstMissionLoaded(self, doc: MissionDocument):
        # Enable controls that require at least one mission plan to be loaded
        self.ui.missionPlanComboBox.setEnabled(True)
        self.ui.buttonEditMissionPlan.setEnabled(True)
        self.ui.buttonSaveMissionPlan.setEnabled(True)
        # self.ui.buttonSaveMissionPlanAs.setEnabled(True)

    @pyqtSlot(MissionDocument)
    def onMissionLoaded(self, doc: MissionDocument):
        # TODO: filename as name in combo box
        self.ui.missionPlanComboBox.addItem(doc.path.stem, doc.plan.uuid)
        index = self.ui.missionPlanComboBox.count() - 1
        self.ui.missionPlanComboBox.setCurrentIndex(index)

    @pyqtSlot(bool)
    def onEditMissionPlanButtonToggled(self, state: bool):
        doc = self._missionContext.activeDocument()
        if doc is None:
            return

        if state is True:
            # Start editing
            doc.startEditing()
        else:
            if doc.isModified():
                reply = QMessageBox.question(
                    self,
                    "Mission plan modified",
                    "Save changes to mission plan?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                    QMessageBox.Save
                )
                if reply == QMessageBox.Save:
                    doc.stopEditing(save = True)
                elif reply == QMessageBox.Discard:
                    doc.stopEditing(save = False)
                else:
                    # User changed their mind, restore button state
                    self.ui.buttonEditMissionPlan.setChecked(True)
                    return
            else:
                # No changes anyways
                doc.stopEditing(save = False)

    @pyqtSlot(bool)
    def onEditModeChanged(self, editMode: bool):
        self.ui.missionPlanComboBox.setDisabled(editMode)
        self.ui.fileButtons.setDisabled(editMode)

    @pyqtSlot()
    def onNewMissionPlan(self):
        dialog = QFileDialog(self, "New Mission Plan")
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setDefaultSuffix(".json")
        dialog.setMimeTypeFilters(["application/json", "application/octet-stream"])
        dialog.setModal(True)
        if dialog.exec() != QDialog.Accepted:
            return

        for file in dialog.selectedFiles():
            name = Path(file).stem
            self._missionContext.newMission(name, file)

    @pyqtSlot()
    def onOpenMissionPlan(self):
        dialog = QFileDialog(self, "Open Mission Plan")
        dialog.setOption(QFileDialog.Option.ReadOnly)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setMimeTypeFilters(["application/json", "application/octet-stream"])
        dialog.setModal(True)
        if dialog.exec() != QDialog.Accepted:
            return

        for file in dialog.selectedFiles():
            self._missionContext.loadMissionFromFile(file)

    @pyqtSlot()
    def onSaveMissionPlan(self):
        self._missionContext.saveMission()
        iface.messageBar().pushSuccess(None, "Mission plan saved")
