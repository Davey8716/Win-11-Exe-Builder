from PySide6.QtCore import QObject, QEvent, QTimer, QPoint
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QLabel

from .path_hover_text import build_path_hover_text
from .styles import TOOLTIP_STYLE


class PathHover(QObject):
    def __init__(self, widget, delay=350, help_text="", help_enabled_getter=None):
        super().__init__(widget)
        self.widget = widget
        self.delay = delay
        self.help_text = help_text
        self.help_enabled_getter = help_enabled_getter
        self.tip_window = None

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.show)

        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.widget:
            if event.type() == QEvent.Enter:
                self.schedule()
            elif event.type() in {
                QEvent.Leave,
                QEvent.MouseButtonPress,
                QEvent.FocusOut,
                QEvent.Hide,
                QEvent.WindowDeactivate,
            }:
                self.hide()
        return super().eventFilter(obj, event)

    def schedule(self):
        self.timer.stop()
        self.timer.start(self.delay)

    def show(self):
        text_getter = getattr(self.widget, "text", None)
        if not callable(text_getter):
            return

        raw_text = text_getter().strip()
        tooltip_text = build_path_hover_text(
            raw_text,
            self.help_text,
            self._should_include_help_text(),
        )
        if not tooltip_text:
            return

        if self.tip_window is not None:
            if self.tip_window.text() == tooltip_text:
                return
            self.hide()

        self.tip_window = QLabel(tooltip_text, None)
        self.tip_window.setWindowFlags(
            Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.tip_window.setStyleSheet(TOOLTIP_STYLE)
        self.tip_window.adjustSize()

        pos = self.widget.mapToGlobal(QPoint(40, 25))
        self.tip_window.move(pos)
        self.tip_window.show()

    def hide(self):
        self.timer.stop()
        if self.tip_window:
            self.tip_window.close()
            self.tip_window = None

    def _should_include_help_text(self):
        if not self.help_text or self.help_enabled_getter is None:
            return False

        return bool(self.help_enabled_getter())


def attach_path_hovers(app):
    tooltips_enabled = lambda: getattr(app, "tooltips_enabled", True)

    app._path_hovers = [
        PathHover(
            app.python_entry_input,
            help_text=(
                "Displays the full path to the Python interpreter.\n"
                "That will be used for building EXEs.\n"
                "This is read only.\n"
                "Once a path has been set the navigation is locked to where pyton interpreters are.\n"
            ),
            help_enabled_getter=tooltips_enabled,
        ),
        PathHover(
            app.icon_path_input,
            help_text="File path to Icon if used.",
            help_enabled_getter=tooltips_enabled,
        ),
        PathHover(
            app.script_path_input,
            help_text="File path to python script folder and file.",
            help_enabled_getter=tooltips_enabled,
        ),
        PathHover(
            app.output_path_input,
            help_text="File path to the EXE output folder.",
            help_enabled_getter=tooltips_enabled,
        ),
    ]
