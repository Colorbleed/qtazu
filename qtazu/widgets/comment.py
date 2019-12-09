import os
import logging
import tempfile
import platform

import gazu
from Qt import QtWidgets, QtCore, QtGui

from .screenmarquee import ScreenMarquee
from .taskbreadcrumb import TaskBreadcrumb

# Use NSURL as a workaround to pyside/Qt4 bug QTBUG40449
# behaviour for dragging and dropping on OSx
platform_system = platform.system()
if platform_system == 'Darwin':
    from Foundation import NSURL

PLACEHOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "res", "icon", "camera.png")


log = logging.getLogger(__name__)


class ClickableLabel(QtWidgets.QLabel):
    """Label that emits click event signal when pressed"""
    clicked = QtCore.Signal(QtGui.QMouseEvent)

    def mousePressEvent(self, event):
        self.clicked.emit(event)
        return super(ClickableLabel, self).mousePressEvent(event)


class DragDropLabel(ClickableLabel):
    """A clickable label that allows to (drag and) drop files."""
    dropped = QtCore.Signal(list)

    def __init__(self):
        super(DragDropLabel, self).__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):

        if event.mimeData().hasUrls():
            # Ensure the file is copied and not moved
            # from where it was dragged
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()

            files = []
            for url in event.mimeData().urls():
                if platform_system == 'Darwin':
                    # Workaround for OSx dragging and dropping QTBUG40449
                    ns_url = NSURL.URLWithString_(str(url.toString()))
                    fname = str(ns_url.filePathURL().path())
                else:
                    fname = str(url.toLocalFile())
                files.append(fname)

        if files:
            self.dropped.emit(files)


class CommentWidget(QtWidgets.QDialog):
    """A CG-Wire comment widget

    This includes the ability to take Screenshots from the widget
    by default, to disable use `set_allow_screenshot(False)`

    If you are using this Widget in another interface that has its
    own submit button then use `set_button_visibility(False)` and
    trigger `submit()` from your surrounding widget.

    """

    StatusRole = QtCore.Qt.UserRole + 1

    screenshot_started = QtCore.Signal()
    screenshot_ended = QtCore.Signal()

    def __init__(self, task_id=None, parent=None):
        super(CommentWidget, self).__init__(parent)

        # Breadcrumbs
        breadcrumbs = TaskBreadcrumb()

        # Thumbnail
        thumbnail_label = QtWidgets.QLabel("Take a screenshot:")
        thumbnail = DragDropLabel()
        thumbnail.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                QtWidgets.QSizePolicy.Expanding)
        thumbnail.setAlignment(QtCore.Qt.AlignCenter)
        thumbnail.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        thumbnail.setToolTip("Left-click to take new screenshot")
        thumbnail.setStyleSheet("QLabel { background-color : #333333; }")
        thumbnail.setMinimumSize(240, 160)
        thumbnail.clicked.connect(self.on_thumbnail_clicked)
        thumbnail.dropped.connect(self.on_thumbnail_dropped)

        # Whenever we drop an attachment that cannot be previewed as image
        # then we display the "path" to the file - to ensure we read as
        # much as possible of it let it word wrap.
        thumbnail.setWordWrap(True)

        pixmap = QtGui.QPixmap()
        pixmap.load(PLACEHOLDER)
        thumbnail.setPixmap(pixmap)

        # Comment
        comment_label = QtWidgets.QLabel("Comment:")
        comment = QtWidgets.QTextEdit()
        comment.setTabChangesFocus(True)

        # Task Status
        status = QtWidgets.QComboBox()
        # force custom list view so we can customize item stylesheet
        # todo: avoid this hack for forcing our style change?
        view = QtWidgets.QListView()
        view.setSpacing(4)
        status.setView(view)
        status.setStyleSheet(
            "QComboBox QAbstractItemView::item { padding: 3px; }"
        )

        # Create buttons
        submit_button = QtWidgets.QPushButton("Submit")
        submit_button.clicked.connect(self.submit)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(submit_button)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(breadcrumbs)
        main_layout.addWidget(thumbnail_label)
        main_layout.addWidget(thumbnail)
        main_layout.addWidget(comment_label)
        main_layout.addWidget(comment)
        main_layout.addWidget(status)
        main_layout.addLayout(buttons_layout)

        self.breadcrumbs = breadcrumbs
        self.thumbnail_label = thumbnail_label
        self.thumbnail = thumbnail
        self.status = status
        self.comment = comment
        self.buttons = [submit_button]

        self._close_on_submit = True
        self._allow_screenshot = True
        self._screenshot = None # Pixmap storage for screenshot
        self._attachment = None

        self.setWindowTitle("Submit comment to CG-Wire")
        self.resize(350, 400)

        self.refresh_all_task_statuses()

        # Set the task
        if task_id is not None:
            self.set_task(task_id)

    def set_task(self, task_id):

        self.breadcrumbs.set_task(task_id)

        task = self.breadcrumbs.get_task()
        current_state = gazu.task.get_task_status(task)

        # Set the status combobox to the current state of this task
        index = self.status.findText(current_state['name'])
        self.status.setCurrentIndex(index)

    def get_task(self):
        return self.breadcrumbs.get_task()

    def refresh_all_task_statuses(self):
        """Refresh all available task statuses"""

        self.status.clear()

        for state in gazu.task.all_task_statuses():
            self.status.addItem(state['name'])
            index = self.status.count()-1
            self.status.setItemData(index, state, self.StatusRole)

            # Use color from the status
            color = QtGui.QColor(state['color'])

            # The "Todo" status is not user-defined and always returns the
            # bright online White Theme color which is near pure white.
            # So for that status we force the dark theme's grey.
            if state['name'] == "Todo":
                color = QtGui.QColor("#5F626A")

            self.status.setItemData(index, color, QtCore.Qt.BackgroundRole)

            # Force white text
            self.status.setItemData(index,
                                    QtGui.QColor("white"),
                                    QtCore.Qt.ForegroundRole)

    def set_close_on_submit(self, value):
        self._close_on_submit = value

    def set_thumbnail_visible(self, value):
        """Set thumbnail visibility

        Disabling this also implicitly disables the screenshot feature
        since screenshotting is only possible by clicking the thumbnail.

        """
        self.thumbnail_label.setVisible(value)
        self.thumbnail.setVisible(value)

    def set_button_visible(self, value):
        """Set submit button visibility"""
        for widget in self.buttons:
            widget.setVisible(value)

    def set_attachment(self, path):
        """Set the attachment.

        Args:
            path (str): This should be a valid path that can be
                used as preview attachment for the comment.

        """
        assert os.path.exists(path), \
            "Attachment path does not exist: %s" % path
        self._attachment = path

        # Clear screenshot to be sure
        self._screenshot = None

        # Update thumbnail
        self._refresh_thumbnail()

    def _refresh_thumbnail(self):

        # Ensure cleared
        #self.thumbnail.setText("")

        def scale_to_fit(pixmap):
            """helper to scale pixmap to fit thumbnail"""
            return pixmap.scaled(self.thumbnail.size(),
                                 QtCore.Qt.KeepAspectRatio,
                                 QtCore.Qt.SmoothTransformation)

        if self._allow_screenshot and self._screenshot:
            scaled = scale_to_fit(self._screenshot)
            self.thumbnail.setPixmap(scaled)
        elif self._attachment:
            path = self._attachment
            assert os.path.exists(path), "File does not exist: %s" % path
            pixmap = QtGui.QPixmap(path)

            if pixmap.isNull():
                # If the attachment is not an image that we can preview
                # then just display the name as text and clear the pixmap
                self.thumbnail.setText(path)
            else:
                scaled = scale_to_fit(pixmap)
                self.thumbnail.setPixmap(scaled)
        else:
            # No screenshot or attachment, thus no need to resize thumbnail
            return

    def on_thumbnail_dropped(self, files):
        if not files:
            return

        # Just use first file for now
        path = files[0]
        self.set_attachment(path)

    # region Screenshot functionality
    def set_allow_screenshot(self, value):
        self._allow_screenshot = bool(value)

        # todo: don't mess with labeling here?
        if value:
            self.thumbnail_label.setText("Take a screenshot:")
        else:
            self.thumbnail_label.setText("Thumbnail:")

    def on_thumbnail_clicked(self, event):
        if not self._allow_screenshot:
            return

        if event.button() == QtCore.Qt.LeftButton:
            self.shoot_screen()

    def resizeEvent(self, event):
        # If we require a resize or update on the pixmap, update thumbnail
        if not self.thumbnail.pixmap() or \
                self.thumbnail.size() != self.thumbnail.pixmap().size():
            self._refresh_thumbnail()

    def _screenshot_to_attachment(self):
        """Save current Screenshot pixmap as temp .png preview attachment"""

        # Save temporary image file
        has_screenshot = bool(self._screenshot)
        if has_screenshot:
            filepath = tempfile.NamedTemporaryFile(prefix="screenshot_",
                                                   suffix=".png",
                                                   delete=False).name
            self._screenshot.save(filepath)
            self.set_attachment(filepath)
            self._screenshot = None     # clear screenshot pixmap
            return filepath

    def shoot_screen(self):
        """Trigger the shoot screenshot functionality"""

        if not self._allow_screenshot:
            # Do nothing
            log.warning("shoot_screen() does nothing when "
                        "screenshots are set to not allowed")
            return

        # Garbage collect any existing image first.
        self._screenshot = None
        self.hide()
        self.screenshot_ended.emit()

        # Perform screenshot
        pixmap = ScreenMarquee.capture_pixmap()
        if pixmap:
            self._attachment = None
            self._screenshot = pixmap
            self._refresh_thumbnail()

        self.show()
        self.screenshot_ended.emit()
    # endregion

    def submit(self):
        """Submit the comment to CG-Wire"""

        if self._allow_screenshot:
            # If we have no attachment but there is a screenshot
            # then use the screenshot as attachment.
            if not self._attachment and self._screenshot:
                self._screenshot_to_attachment()

        # Get current values
        task = self.breadcrumbs.get_task()
        status = self.status.itemData(self.status.currentIndex(),
                                      self.StatusRole)
        comment_text = self.comment.toPlainText()

        # Submit comment
        comment = gazu.task.add_comment(task,
                                        status,
                                        comment=comment_text)
        log.info("Submitted comment: %s", comment)

        # Upload preview and attach to comment
        has_preview = bool(self._attachment)
        if has_preview:
            filepath = self._attachment
            assert os.path.exists(filepath), \
                "File does not exist: %s" % filepath

            preview = gazu.task.add_preview(task, comment, filepath)
            log.info("Submitted preview: %s", preview)

            # Clear the attachment
            self._attachment = None

        if self._close_on_submit:
            # Close after submission for now to avoid confusion
            # todo: if not closing add message that submission succeeded
            self.close()


if __name__ == '__main__':

    app = QtWidgets.QApplication.instance()
    screenshot = ScreenshotWidget()
    screenshot.show()

    # Use Widget without screenshot+thumbnail elsewhere
    screenshot = ScreenshotWidget()
    screenshot.set_button_visible(False)
    screenshot.set_allow_screenshot(False)
    screenshot.set_thumbnail_visible(False)
