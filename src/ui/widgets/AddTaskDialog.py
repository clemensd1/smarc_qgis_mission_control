from qgis.PyQt.QtWidgets import QWidget, QDialog

from ...domain.tasks import Task, TaskType, TaskRegistry

from ..generated.AddTaskDialogUi import Ui_AddTaskDialog

__all__ = ["AddTaskDialog"]


class AddTaskDialog(QDialog, Ui_AddTaskDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setupUi(self)

        # Populate task type list
        for typeName in map(str, TaskType):
            self.taskType.addItem(typeName)

        # Disable resizing, ensuring size provided in QtDesigner
        self.setFixedSize(self.size())

    def description(self) -> str:
        return self.taskDescription.text().strip()

    def type(self) -> TaskType:
        return TaskType(self.taskType.currentText())
