"""Read-only summary labels that can open their valid filesystem paths."""

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QLabel

from .styles import Colors


class ClickablePathLabel(QLabel):
    """A QLabel that emits a raw, valid path when it is left-clicked."""

    pathActivated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path = ""
        self._path_hover_glow = None
        self.setCursor(Qt.ArrowCursor)

    def set_path(self, path):
        self._path = str(path or "").replace("\u200b", "").strip()
        self.setCursor(
            Qt.PointingHandCursor if self._path and os.path.exists(self._path)
            else Qt.ArrowCursor
        )
        self._set_hover_glow(
            self.underMouse() and bool(self._path) and os.path.exists(self._path)
        )

    def path(self):
        return self._path

    def enterEvent(self, event):
        self._set_hover_glow(bool(self._path) and os.path.exists(self._path))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_hover_glow(False)
        super().leaveEvent(event)

    def _set_hover_glow(self, enabled):
        """Highlight valid summary paths so their click action is discoverable."""
        if enabled and self._path_hover_glow is None:
            glow = QGraphicsDropShadowEffect(self)
            glow.setBlurRadius(28)
            glow.setOffset(0, 0)
            glow.setColor(Colors.PATH_HOVER_GLOW)
            self.setGraphicsEffect(glow)
            self._path_hover_glow = glow
        elif not enabled and self._path_hover_glow is not None:
            if self.graphicsEffect() is self._path_hover_glow:
                self.setGraphicsEffect(None)
            self._path_hover_glow = None

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
