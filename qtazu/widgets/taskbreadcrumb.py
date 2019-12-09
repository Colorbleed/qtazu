from Qt import QtWidgets, QtGui, QtCore

import gazu


class TaskBreadcrumb(QtWidgets.QLabel):
    """Simple Breadcrumb label for a Task"""

    task_changed = QtCore.Signal(dict)

    def __init__(self, parent=None, task=None):
        super(TaskBreadcrumb, self).__init__(parent)

        # Support HTML
        self.setTextFormat(QtCore.Qt.RichText)

        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.setFont(font)

        # todo: Implement useful functionality for when any of the breadcrumb
        #       links are clicked
        #self.linkActivated.connect(self._on_link_clicked)

        self._task = None

        if task is not None:
            self.set_task(task)

    def set_task(self, task):
        task = gazu.task.get_task(task)
        self._task = task

        # Define understandable label for Task
        link = '<a href="{url}" style="color: {color}; text-decoration:none;">'
        link += '{txt}</a>'

        entity_type = link.format(
            url="#entity_type",
            color="#BBB",
            txt=task["entity_type"]["name"]
        )
        entity = link.format(
            url="#entity",
            color=task["task_type"]["color"],
            txt=task["entity"]["name"]
        )
        task = link.format(
            url="#task",
            color="#BBB",
            txt=task["task_type"]["name"]
        )

        label = " / ".join([entity_type, entity, task])

        self.setText(label)
        self.task_changed.emit(task)

    def get_task(self):
        """Return current task"""
        return self._task