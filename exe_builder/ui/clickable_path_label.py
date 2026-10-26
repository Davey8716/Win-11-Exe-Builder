"""Read-only summary labels that can open their valid filesystem paths."""

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel


class ClickablePathLabel(QLabel):
    """A QLabel that emits a raw, valid path when it is left-clicked."""

    pathActivated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path = ""
        self.setCursor(Qt.ArrowCursor)

    def set_path(self, path):
        self._path = str(path or "").replace("\u200b", "").strip()
        self.setCursor(
            Qt.PointingHandCursor if self._path and os.path.exists(self._path)
            else Qt.ArrowCursor
        )

    def path(self):
        return self._path

    def mouseReleaseEvent(self, event):
        if (
            event.button() == Qt.LeftButton
            and self._path
            and os.path.exists(self._path)
        ):
            self.pathActivated.emit(self._path)
            event.accept()
            return
        super().mouseReleaseEvent(event)
