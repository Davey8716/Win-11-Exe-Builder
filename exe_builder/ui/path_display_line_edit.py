from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QLineEdit


class PathDisplayLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self._reset_view_to_start)

    def set_display_path(self, text):
        self.setText(text)
        self._schedule_reset()

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_reset()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_reset()

    def _schedule_reset(self):
        self._reset_timer.start(0)

    def _reset_view_to_start(self):
        self.deselect()
        self.setCursorPosition(0)
        self.home(False)
