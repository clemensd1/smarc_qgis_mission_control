from qgis.PyQt.QtCore import Qt, QVariant, QModelIndex
from qgis.PyQt.QtWidgets import QWidget

from ..domain.schema import Schema
from .ItemBasedModel import ItemBasedModel

__all__ = ["SchemaBasedModel"]

class SchemaBasedModel(ItemBasedModel): # TODO: integrate with undo/redo stack
    _schema: Schema
    _longHeaders: bool

    def __init__(self, schema: Schema, longHeaders: bool,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._schema = schema
        self._longHeaders = longHeaders

    def schema(self) -> Schema:
        # Keep consistent API with QGIS
        return self._schema

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._schema.fields)

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal \
                and 0 <= section < self.columnCount():
            spec = self._schema.fields[section]
            return spec.header(preferLong = self._longHeaders)

        return super().headerData(section, orientation, role)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> str | None:
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None

        item = self._items[index.row()]
        spec = self._schema.fields[index.column()]
        # TODO: always str?
        return str(spec.value(item))

    def setData(self, index: QModelIndex, value: QVariant,
                role: int = Qt.EditRole) -> bool:
        if role != Qt.EditRole:
            return False

        item = self._items[index.row()]

        # retrieve the field specification for schema object
        spec = self._schema.fields[index.column()]
        # retrieve original value (->type)
        original = spec.value(item)

        # cast the incoming object to the original type # TODO: move type checks to MissionDocument after undo/redo stack implementation
        try:
            typed_value = spec.type()(value) # instead of type(original)(value)
        except (ValueError, TypeError):
            return False  # reject invalid input

        spec.setValue(item, typed_value)
        # TODO: or [role]?
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])

        return True
