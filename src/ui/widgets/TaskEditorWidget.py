from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import *
from qgis.core import *

from typing import *
from dataclasses import replace as dtReplace
from enum import Enum
from uuid import UUID, uuid4

from ...domain.tasks import Task
from ...domain.schema import Schema
from ...domain.taskspatial import (isWaypointField, isWaypointListField,
                                   waypointListType, waypointType)
from ...mission.MissionContext import MissionContext
from ...mission.MissionDocument import MissionDocument
from ...model.SchemaBasedModel import SchemaBasedModel

# from ..tasksUi import TaskUiRegistry

from .AutomaticFormWidget import AutomaticFormWidget
from .WaypointFormWidget import WaypointFormWidget
from .WaypointTableWidget import WaypointTableWidget

__all__ = ['TaskEditorWidget']

class TaskEditorWidget(AutomaticFormWidget):
    _editors: list[QWidget]

    def __init__(self, taskCls: Type[Task], missionContext: MissionContext,
                 parent: QWidget | None = None):
        schema = taskCls.schema()
        scalarFields = [
            spec for spec in schema.fields
            if not isWaypointField(spec) and not isWaypointListField(spec)
        ]
        self._model = SchemaBasedModel(
            Schema(scalarFields), longHeaders = True)
        super().__init__(self._model, parent)

        self._taskCls = taskCls
        self._editors = []

        self.setContentsMargins(0, 0, 0, 0)

        self._formLayout = QFormLayout(self)
        self._formLayout.setContentsMargins(0, 0, 0, 0)
        self._formLayout.setLabelAlignment(
            Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self._formLayout.setFormAlignment(Qt.AlignTop)

        scalarColumns = {
            spec.name: column for column, spec in enumerate(scalarFields)
        }
        for spec in schema.fields:
            waypointCls = waypointType(spec.baseType)
            waypointListCls = waypointListType(spec.baseType)

            if waypointCls is None and waypointListCls is None:
                self._addScalarField(spec, scalarColumns[spec.name])
                continue

            label = QLabel(spec.header() + ":", self)
            self._formLayout.addRow(label, None)

            editor: QWidget
            if waypointCls is not None:
                editor = WaypointFormWidget(taskCls, spec.name, waypointCls,
                                            missionContext, self)
                editor.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
                self._formLayout.addRow(editor)
            else:
                assert(waypointListCls is not None)
                editor = WaypointTableWidget(taskCls, spec.name, waypointListCls,
                                             missionContext, self)
                editor.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
                self._formLayout.addRow(editor)

            self._editors.append(editor)

        self._mapper.toFirst()

        # Respect edit mode
        missionContext.editModeChanged.connect(self.setEditMode)

    def _addScalarField(self, spec, column: int):
        label = QLabel(self)
        label.setText(spec.header() + ":")

        field = self.createEditorWidget(self, spec.type())
        self._formLayout.addRow(label, field)

        if issubclass(spec.type(), Enum):
            self._mapper.addMapping(field, column, b"currentText")
            # field.editTextChanged.connect(self._mapper.submit) # connects on field change (not suitable for manual keyboard input)
            field.lineEdit().editingFinished.connect(self._mapper.submit) # connects on fiel change (enter/focus out)
        else:
            self._mapper.addMapping(field, column)

    def bind(self, doc: MissionDocument, taskUuid: UUID):
        task = doc.index.taskByUuid(taskUuid)
        assert(task)
        assert(isinstance(task, self._taskCls))
        self._model.setItems([task])
        self._mapper.toFirst()

        for editor in self._editors:
            editor.bind(doc, taskUuid)

    def unbind(self):
        self._model.setItems([])

        for editor in self._editors:
            editor.unbind()

    def _setFieldWidgetEditMode(self, fieldWidget: QWidget, editMode: bool):
        match fieldWidget:
            case WaypointFormWidget() | WaypointTableWidget():
                # They handle edit mode changes themselves
                pass
            case _:
                # Normal editor widgets
                super()._setFieldWidgetEditMode(fieldWidget, editMode)
