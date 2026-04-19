from uuid import UUID

from qgis.PyQt.QtCore import Qt, pyqtSlot, QItemSelection
from qgis.PyQt.QtWidgets import QWidget, QHeaderView, QAbstractItemDelegate, QDialog, QDataWidgetMapper
from qgis.core import QgsApplication

from ...mission.MissionContext import MissionContext
from ...mission.MissionDocument import MissionDocument
from ...domain.missionplan import MissionPlan
from ...domain.tasks import TaskRegistry, TaskType, SingleWaypointTask
from ...model.TaskListModel import TaskListModel
from ...model.MissionParamsModel import MissionParamsModel
from ..generated.MissionPlanWidgetUi import Ui_MissionPlanWidget
from .TaskEditorWidget import TaskEditorWidget
from .AddTaskDialog import AddTaskDialog


class MissionPlanWidget(QWidget):
    taskEditors: dict[TaskType, TaskEditorWidget]

    _missionContext: MissionContext

    def __init__(self, missionContext: MissionContext,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._model = MissionParamsModel(self)
        self._missionContext = missionContext
        self._mapper = QDataWidgetMapper()
        self._mapper.setModel(self._model)
        self.taskEditors = {}

        self.ui = Ui_MissionPlanWidget()
        self.ui.setupUi(self)

        self.setup()

    def setup(self) -> None:
        self.taskListModel = TaskListModel()
        self.ui.taskList.setModel(self.taskListModel)

        self._mapper.addMapping(self.ui.missionPlanDescription, 0)
        self._mapper.addMapping(self.ui.missionPlanTimeout, 1)

        # Respect edit mode
        self._missionContext.editModeChanged.connect(self.onEditModeChanged)

        # Signals for refreshing the task list
        # TODO
        def resetTaskList():
            self.taskListModel.beginResetModel()
            self.taskListModel.endResetModel()
            self.onTaskSelectionChanged(None, None)

        self._missionContext.taskListModified.connect(resetTaskList)

        # Setup icons for the task buttons
        self.ui.buttonAddTask.setIcon(QgsApplication.getThemeIcon("symbologyAdd.svg"))
        self.ui.buttonRemoveTask.setIcon(
            QgsApplication.getThemeIcon("symbologyRemove.svg")
        )
        self.ui.buttonMoveTaskUp.setIcon(
            QgsApplication.getThemeIcon("mActionArrowUp.svg")
        )
        self.ui.buttonMoveTaskDown.setIcon(
            QgsApplication.getThemeIcon("mActionArrowDown.svg")
        )

        # Setup event handling for task buttons
        self.ui.buttonAddTask.clicked.connect(self.onAddTask)
        self.ui.buttonRemoveTask.clicked.connect(self.onRemoveTask)

        # Setup the task table
        self.ui.taskList.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ui.taskList.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.ui.taskList.verticalHeader().setDefaultAlignment(Qt.AlignRight)

        self.ui.taskList.selectionModel().selectionChanged.connect(
            self.onTaskSelectionChanged
        )

        # Create and setup task editor widgets
        for type in TaskType:
            editor = TaskEditorWidget(
                TaskRegistry.lookup(type),
                self._missionContext,
                self.ui.taskEditorStack
            )
            self.taskEditors[type] = editor
            self.ui.taskEditorStack.addWidget(editor)

    @pyqtSlot(MissionDocument)
    def onActiveMissionChanged(self, doc: MissionDocument) -> None:
        # TODO: accept doc like other models
        self.taskListModel.setMissionPlan(doc.plan)
        self._model.bind(doc)
        self._mapper.toFirst()
        # Reset task button states
        self.onTaskSelectionChanged(None, None)

    @pyqtSlot(bool)
    def onEditModeChanged(self, editMode: bool) -> None:
        self.ui.missionPlanParameters.setEnabled(editMode)
        self.ui.taskListSidebar.setEnabled(editMode)

        self.taskListModel.setEditable(editMode)
        self._model.setEditable(editMode)
        # Close current cell editor, if present. This is primarily for the Description
        # field
        cellEditor = self.ui.taskList.focusWidget()
        if cellEditor is not None:
            self.ui.taskList.closeEditor(cellEditor, QAbstractItemDelegate.NoHint)

    @pyqtSlot(QItemSelection, QItemSelection)
    def onTaskSelectionChanged(self, selected: QItemSelection | None,
                               deselected: QItemSelection | None) -> None:
        sel = self.ui.taskList.selectionModel()
        rows = sel.selectedRows()

        # Enable/disable task list buttons as needed
        self.ui.buttonRemoveTask.setEnabled(bool(rows))
        self.ui.buttonMoveTaskUp.setEnabled(bool(rows) and rows[0].row() > 0)
        self.ui.buttonMoveTaskDown.setEnabled(bool(rows) \
            and rows[-1].row() < len(self.taskListModel.items()) - 1)

        if len(rows) > 1:
            self.activateEditorForTask(None)
        elif len(rows) == 0:
            self.activateEditorForTask(None)
        else:
            task = self.taskListModel.item(rows[0].row())
            self.activateEditorForTask(task)

    @pyqtSlot()
    def onAddTask(self):
        doc = self._missionContext.activeDocument()
        if doc is None:
            # TODO: invalid mapping
            return

        dialog = AddTaskDialog()
        if dialog.exec() != QDialog.Accepted:
            return

        doc.addTask(dialog.type(), dialog.description())

    @pyqtSlot()
    def onRemoveTask(self):
        doc = self._missionContext.activeDocument()
        if doc is None:
            # TODO: invalid mapping
            return

        rows = self.ui.taskList.selectionModel().selectedRows()
        for row in rows:
            index = rows[0].row()
            doc.deleteTaskAt(index)

    def activateEditorForTask(self, task):
        if task is None:
            editor = self.ui.taskEditorStack.currentWidget()
            if editor is not None and editor is not self.ui.defaultTaskEditorPage:
                editor.unbind()
            self.ui.taskEditorStack.setCurrentWidget(self.ui.defaultTaskEditorPage)
        else:
            editor = self.taskEditors[task.type]
            doc = self._missionContext.activeDocument()
            editor.bind(doc, task.uuid)
            self.ui.taskEditorStack.setCurrentWidget(editor)
