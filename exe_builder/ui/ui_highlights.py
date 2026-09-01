from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGraphicsDropShadowEffect

from .styles import Colors


def flash_delete_highlight(*widgets, duration_ms=350):
    _flash_highlight(
        *widgets,
        color=Colors.DELETE_HIGHLIGHT_GLOW,
        property_name="deleteHighlight",
        timer_name="_delete_highlight_timer",
        duration_ms=duration_ms,
    )


def flash_add_highlight(*widgets, duration_ms=350):
    _flash_highlight(
        *widgets,
        color=Colors.ADD_HIGHLIGHT_GLOW,
        property_name="addHighlight",
        timer_name="_add_highlight_timer",
        duration_ms=duration_ms,
    )


def _flash_highlight(*widgets, color, property_name, timer_name, duration_ms):
    for widget in widgets:
        if widget is None:
            continue

        for existing_timer_name in ("_delete_highlight_timer", "_add_highlight_timer"):
            timer = getattr(widget, existing_timer_name, None)
            if timer:
                timer.stop()

        widget.setProperty("deleteHighlight", False)
        widget.setProperty("addHighlight", False)
        widget.setProperty(property_name, True)

        glow = QGraphicsDropShadowEffect(widget)
        glow.setBlurRadius(100)
        glow.setOffset(0, 0)
        glow.setColor(color)
        widget.setGraphicsEffect(glow)

        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

        timer = QTimer(widget)
        timer.setSingleShot(True)
        timer.timeout.connect(
            lambda widget=widget, property_name=property_name: clear_highlight(
                widget,
                property_name,
            )
        )
        setattr(widget, timer_name, timer)
        timer.start(max(duration_ms, 200))


def clear_delete_highlight(widget):
    clear_highlight(widget, "deleteHighlight")


def clear_highlight(widget, property_name):
    if widget.property(property_name) is not True:
        return

    widget.setProperty(property_name, False)
    widget.setGraphicsEffect(None)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
