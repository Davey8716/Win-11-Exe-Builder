from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import QFont, QPainter, QPalette, QTextLayout, QTextOption
from PySide6.QtWidgets import QLineEdit, QStyle, QStyleOptionFrame


class PathDisplayLineEdit(QLineEdit):
    """A read-only path field that displays up to two wrapped lines."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Rubik UI", 11, QFont.Bold))
        self.setReadOnly(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setFixedHeight(self.two_line_height())
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

    def two_line_height(self):
        """Return the height required for two path lines plus the frame."""
        return self.fontMetrics().lineSpacing() * 2 + 8

    def paintEvent(self, event):
        """Paint a two-line path while retaining QLineEdit's public API."""
        option = QStyleOptionFrame()
        self.initStyleOption(option)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_PanelLineEdit, option, painter, self)

        content_rect = self.style().subElementRect(
            QStyle.SE_LineEditContents, option, self
        ).adjusted(2, 2, -2, -2)
        text = self.text()
        color_role = QPalette.Text
        if not text:
            text = self.placeholderText()
            color_role = QPalette.PlaceholderText
        if not text:
            painter.end()
            return

        # QLabel and QLineEdit do not treat Windows separators as path breaks.
        display_text = text.replace("\\", "\\\u200b").replace("/", "/\u200b")
        text_option = QTextOption(Qt.AlignLeft)
        text_option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        layout = QTextLayout(display_text, self.font())
        layout.setTextOption(text_option)
        layout.beginLayout()
        lines = []
        for _ in range(2):
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(content_rect.width())
            lines.append(line)
        layout.endLayout()

        total_height = sum(line.height() for line in lines)
        y = content_rect.y() + max(0, (content_rect.height() - total_height) / 2)
        painter.setPen(self.palette().color(color_role))
        for line in lines:
            line.draw(painter, QPointF(content_rect.x(), y))
            y += line.height()
        painter.end()
