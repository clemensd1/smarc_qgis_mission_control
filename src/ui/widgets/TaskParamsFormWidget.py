from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import *
from qgis.core import *

from typing import Type

from ...domain.tasks import Task
from ...model.SchemaBasedModel import SchemaBasedModel
from ..generated.TaskParamsFormWidgetUi import Ui_TaskParamsFormWidget
from .AutomaticFormWidget import AutomaticFormWidget

__all__ = ['TaskParamsFormWidget']

class TaskParamsFormWidget(AutomaticFormWidget):
    _taskCls: Type[Task]
    _model: SchemaBasedModel

    def __init__(self, taskCls: Type[Task], parent: QWidget | None = None):
        self._model = SchemaBasedModel(taskCls.schema(), longHeaders = True)
        super().__init__(self._model, parent)

        self._taskCls = taskCls

        self.ui = Ui_TaskParamsFormWidget()
        self.ui.setupUi(self)

        self.buildForm(self.ui.taskParamsForm)

    def bind(self, doc, taskUuid):
        # TODO:
        task = doc.index.taskByUuid(taskUuid)
        assert(task)
        assert(isinstance(task, self._taskCls))
        self._model.setItems([task])
        self._mapper.toFirst()

    def unbind(self):
        self._model.setItems([])
