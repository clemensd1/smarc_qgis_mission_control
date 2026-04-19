from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import *
from qgis.core import *

from ..domain.tasks import Task
from ..domain.missionplan import MissionPlan
from .ItemBasedModel import ItemBasedModel

__all__ = ["TaskListModel"]

class TaskListModel(ItemBasedModel):
    _plan: MissionPlan | None
    _items: list[Task]
    _columns: list[str] = ["Description", "Type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._plan = None

    def setMissionPlan(self, plan: MissionPlan | None):
        self._plan = plan
        self.setItems(plan.tasks if plan else [])

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        # TODO: integration with undo/redo?
        flags = super().flags(index)
        # Only column "Description" is editable
        if index.column() == 0 and self.isEditable():
            flags |= Qt.ItemIsEditable
        else:
            flags &= ~Qt.ItemIsEditable
        return flags

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal \
            and 0 <= section <= len(self._columns):
                return self._columns[section]

        return super().headerData(section, orientation, role)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> str|None:
        if not index.isValid():
            return None

        if role in (Qt.DisplayRole, Qt.EditRole):
            task = self._items[index.row()]
            if index.column() == 0:
                # Description
                return task.description
            elif index.column() == 1:
                # Type
                return str(task.type)

        return None

    def setData(self, index: QModelIndex, value: QVariant,
                role: int = Qt.EditRole) -> bool:
        if role != Qt.EditRole:
            return False

        task = self._items[index.row()]
        col = index.column()
        if col == 0:
            task.description = str(value)
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True
        else:
            # TODO: report an error, this is a bug; only task description can be changed
            pass

        return False
