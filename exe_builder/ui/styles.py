import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

from PySide6.QtGui import QColor, QFont
from . import qt_resources_rc  # noqa: F401


class Colors:
    WHITE = QColor(255, 255, 255)
    BLACK = QColor(0, 0, 0)
    WINDOW = QColor(40, 40, 50)
    TITLE_BG = QColor(74, 111, 168)
    PANEL_BG = QColor(58, 72, 96)
    POPUP_BG = QColor(58, 72, 96)
    BORDER_MID = QColor(0, 0, 0)
    BORDER_DARK = QColor(0, 0, 0)
    SCRIPT_POPUP_BORDER = QColor(0, 0, 0)
    SUCCESS = QColor(17, 189, 39)
    SUCCESS_PRESSED = QColor(22, 212, 46)
    ERROR = QColor(255, 0, 0)
    CANCEL = QColor(255, 0, 0)
    MUTED_TEXT = QColor(255, 255, 255)
    MUTED_BORDER = QColor(0, 0, 0)
    DISABLED_BG = QColor(60, 60, 60)
    BUILD_DISABLED_BG = QColor(60, 60, 60)
    BUILD_DISABLED_TEXT = QColor(170, 170, 170)
    COMBO_DISABLED_BG = QColor(60, 60, 60)
    COMBO_DISABLED_TEXT = QColor(170, 170, 170)
    SELECTION_BG = QColor(74, 111, 168)
    INFO = QColor(45, 125, 210)
    WARNING = QColor(230, 162, 60)
    DISABLED_TEXT = QColor(255, 255, 255)
    TOOLTIP_BG = QColor(40, 40, 50)
    TOOLTIP_BORDER = QColor(0, 0, 0)

    TEXT_LIGHT = QColor(255, 255, 255)
    TEXT_DARK = QColor(255, 255, 255)
    SURFACE_HOVER = QColor(93, 107, 131)
    SURFACE_SELECTED_HOVER = QColor(96, 133, 190)
    DANGER_HOVER = QColor(255, 25, 25)
    DELETE_HIGHLIGHT_GLOW = QColor(255, 82, 82)
    ADD_HIGHLIGHT_GLOW = QColor(82, 255, 82)


def qcolor_name(color: QColor) -> str:
    return color.name(QColor.HexRgb)


def build_mode_button_font() -> QFont:
    """Return the typography shared by the build-mode toggle buttons."""
    return QFont("Rubik UI", 11, QFont.Bold)


def apply_build_mode_button_state(
    python_button, dotnet_button, mode: str, building: bool = False
) -> None:
    """Apply normal mode selection or lock both selectors during a build."""
    for button, button_mode in ((python_button, "python"), (dotnet_button, "dotnet")):
        is_active = button_mode == mode
        button.setChecked(is_active)
        is_disabled = building or is_active
        button.setEnabled(not is_disabled)
        button.setStyleSheet(build_disabled_button() if is_disabled else button_base())


def title_frame_minimum_width(
    text_width: int,
    side_control_width: int,
    horizontal_margins: int,
    safety_padding: int = 16,
) -> int:
    """Return a title-frame width that leaves room for balanced side controls."""
    return (
        text_width
        + (side_control_width * 2)
        + horizontal_margins
        + safety_padding
    )


def _windows_colorref(color: QColor) -> int:
    return color.red() | (color.green() << 8) | (color.blue() << 16)


def apply_native_title_bar_style(
    window,
    caption: QColor = Colors.WINDOW,
    text: QColor = Colors.WHITE,
    border: QColor = Colors.WINDOW,
) -> None:
    if sys.platform != "win32":
        return

    try:
        hwnd = int(window.winId())
        dark_mode = ctypes.c_int(1)
        caption_color = ctypes.c_uint(_windows_colorref(caption))
        text_color = ctypes.c_uint(_windows_colorref(text))
        border_color = ctypes.c_uint(_windows_colorref(border))

        attributes = [
            (20, dark_mode),
            (35, caption_color),
            (36, text_color),
            (34, border_color),
        ]

        for attribute, value in attributes:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                ctypes.c_uint(attribute),
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
    except (AttributeError, OSError, TypeError, ValueError):
        return


def apply_build_options_title_bar_style(dialog) -> None:
    """Apply the Global Build Options dialog's native Windows caption colours."""
    apply_native_title_bar_style(
        dialog,
        caption=Colors.PANEL_BG,
        border=Colors.PANEL_BG,
    )


def _resource_path(relative_path: str) -> Path:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base_dir / relative_path


def _stylesheet_url(relative_path: str) -> str:
    return _resource_path(relative_path).resolve().as_posix()


SCROLLBAR_UP_ARROW_ICON = ":/icons/Icons/scroll_up_white.svg"
SCROLLBAR_DOWN_ARROW_ICON = ":/icons/Icons/scroll_down_white.svg"
CHECKBOX_CHECK_BLACK_ICON = _stylesheet_url("Icons/check_black.svg")
CHECKBOX_CHECK_DISABLED_ICON = _stylesheet_url("Icons/check_disabled.svg")

UTILITY_ICON_BUTTON_SIZE = (35, 35)
UTILITY_ICON_RENDER_SIZE = (18, 18)
DELETE_BUTTON_TEXT = ""
DELETE_BUTTON_ICON = _resource_path("Icons/utility_delete.svg")
DELETE_BUTTON_ICON_SIZE = UTILITY_ICON_RENDER_SIZE
DELETE_ALL_BUTTON_TEXT = ""
DELETE_ALL_BUTTON_ICON = _resource_path("Icons/utility_delete_all.svg")
DELETE_ALL_BUTTON_ICON_SIZE = UTILITY_ICON_RENDER_SIZE
REFRESH_BUTTON_TEXT = ""
REFRESH_BUTTON_ICON = _resource_path("Icons/utility_refresh.svg")
REFRESH_BUTTON_ICON_SIZE = UTILITY_ICON_RENDER_SIZE


def combo_box_scrollbar_style() -> str:
    return vertical_scrollbar_style("QComboBox QAbstractItemView")


def combo_box_popup_style(owner_selector: str = "QAbstractItemView") -> str:
    return f"""
    {owner_selector} {{
        background-color: {qcolor_name(Colors.PANEL_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        selection-background-color: {qcolor_name(Colors.SELECTION_BG)};
        font-family: "Rubik UI";
        font-size: 15px;
        font-weight: bold;
        border-radius: 4px;
    }}

    {owner_selector}::item {{
        text-align: center;
    }}

    {vertical_scrollbar_style(owner_selector)}

    {owner_selector} QScrollBar:vertical,
    {owner_selector} QScrollBar::handle,
    {owner_selector} QScrollBar::sub-line:vertical,
    {owner_selector} QScrollBar::add-line:vertical {{
        border: 2px solid {qcolor_name(Colors.BLACK)};
    }}
"""


def vertical_scrollbar_style(owner_selector: str) -> str:
    return f"""
    {owner_selector} QScrollBar {{
        background-color: {qcolor_name(Colors.PANEL_BG)};
    }}

    {owner_selector} QScrollBar:vertical {{
        background-color: {qcolor_name(Colors.PANEL_BG)};
        width: 18px;
        margin: 18px 0 18px 0;
    }}

    {owner_selector} QScrollBar:horizontal {{
        background-color: {qcolor_name(Colors.PANEL_BG)};
    }}

    {owner_selector} QScrollBar::handle {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
        border-radius: 4px;
    }}

    {owner_selector} QScrollBar::sub-line:vertical,
    {owner_selector} QScrollBar::add-line:vertical {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
        border-radius: 4px;
        height: 18px;
    }}

    {owner_selector} QScrollBar::sub-line:vertical {{
        subcontrol-origin: margin;
        subcontrol-position: top;
    }}

    {owner_selector} QScrollBar::add-line:vertical {{
        subcontrol-origin: margin;
        subcontrol-position: bottom;
    }}

    {owner_selector} QScrollBar::up-arrow:vertical,
    {owner_selector} QScrollBar::down-arrow:vertical {{
        background-color: transparent;
        color: {qcolor_name(Colors.WHITE)};
        width: 10px;
        height: 10px;
    }}

    {owner_selector} QScrollBar::up-arrow:vertical {{
        image: url({SCROLLBAR_UP_ARROW_ICON});
    }}

    {owner_selector} QScrollBar::down-arrow:vertical {{
        image: url({SCROLLBAR_DOWN_ARROW_ICON});
    }}

    {owner_selector} QScrollBar::add-page,
    {owner_selector} QScrollBar::sub-page {{
        background-color: {qcolor_name(Colors.PANEL_BG)};
    }}
"""


def disabled_scrollbar_style(owner_selector: str) -> str:
    return f"""
    {owner_selector} QScrollBar:disabled,
    {owner_selector} QScrollBar:vertical:disabled,
    {owner_selector} QScrollBar:horizontal:disabled {{
        background-color: {qcolor_name(Colors.BUILD_DISABLED_BG)};
    }}

    {owner_selector} QScrollBar::handle:disabled {{
        background-color: {qcolor_name(Colors.BUILD_DISABLED_BG)};
        border-radius: 4px;
    }}

    {owner_selector} QScrollBar::sub-line:disabled,
    {owner_selector} QScrollBar::add-line:disabled {{
        background-color: {qcolor_name(Colors.BUILD_DISABLED_BG)};
    }}

    {owner_selector} QScrollBar::up-arrow:disabled,
    {owner_selector} QScrollBar::down-arrow:disabled,
    {owner_selector} QScrollBar::left-arrow:disabled,
    {owner_selector} QScrollBar::right-arrow:disabled {{
        background-color: transparent;
        image: none;
        color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
    }}

    {owner_selector} QScrollBar::add-page:disabled,
    {owner_selector} QScrollBar::sub-page:disabled {{
        background-color: {qcolor_name(Colors.BUILD_DISABLED_BG)};
    }}
"""


def button_base(border_width: int = 3) -> str:
    return f"""
        QPushButton {{
            background-color: {qcolor_name(Colors.TITLE_BG)};
            color: {qcolor_name(Colors.TEXT_LIGHT)};
            border: 2px solid {qcolor_name(Colors.BLACK)};
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {qcolor_name(Colors.SURFACE_SELECTED_HOVER)};
        }}
    """


def button_with_border(border_color: QColor, border_width: int = 4) -> str:
    return f"""
        QPushButton {{
            background-color: {qcolor_name(Colors.TITLE_BG)};
            color: {qcolor_name(Colors.TEXT_LIGHT)};
            border: 2px solid {qcolor_name(Colors.BLACK)};
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {qcolor_name(Colors.SURFACE_SELECTED_HOVER)};
        }}
    """


def filled_button(background_color: QColor, border_width: int = 4, radius: int = 4) -> str:
    hover_color = Colors.SUCCESS_PRESSED if background_color == Colors.SUCCESS else background_color
    if background_color in (Colors.ERROR, Colors.CANCEL):
        hover_color = Colors.DANGER_HOVER
    return f"""
        QPushButton {{
            background-color: {qcolor_name(background_color)};
            color: {qcolor_name(Colors.TEXT_LIGHT)};
            border: 2px solid {qcolor_name(Colors.BLACK)};
            border-radius: {radius}px;
        }}
        QPushButton:hover {{
            background-color: {qcolor_name(hover_color)};
        }}
    """


def build_disabled_button(radius: int = 4) -> str:
    return f"""
        QPushButton {{
            background-color: {qcolor_name(Colors.BUILD_DISABLED_BG)};
            color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
            border: 2px solid {qcolor_name(Colors.BLACK)};
            border-radius: {radius}px;
        }}
        QPushButton:hover {{
            background-color: {qcolor_name(Colors.BUILD_DISABLED_BG)};
        }}
    """


def utility_icon_button_style() -> str:
    return button_base(border_width=4)


def utility_icon_button_disabled_style(building: bool) -> str:
    return build_disabled_button() if building else utility_icon_button_style()


ENV_SYNC_BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
    }}
    QPushButton:hover {{
        background-color: {qcolor_name(Colors.SURFACE_SELECTED_HOVER)};
    }}
    QPushButton:pressed {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
    }}
    QPushButton:disabled {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
    }}
    QPushButton:disabled:hover {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
    }}
"""


def build_disabled_checkbox() -> str:
    return f"""
        QCheckBox {{
            color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
        }}
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            background-color: {qcolor_name(Colors.DISABLED_BG)};
            border: 2px solid {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
            border-radius: 3px;
        }}
        QCheckBox::indicator:checked {{
            background-color: {qcolor_name(Colors.DISABLED_BG)};
            border: 2px solid {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
            image: url({CHECKBOX_CHECK_DISABLED_ICON});
        }}
        QCheckBox:disabled {{
            color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
        }}
    """


def required_selection_checkbox() -> str:
    """Style an enabled checkbox whose required selection is missing."""
    return f"""
        QCheckBox {{
            color: {qcolor_name(Colors.ERROR)};
        }}
    """


def build_disabled_checkbox_without_checkmark() -> str:
    return f"""
        QCheckBox {{
            color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
        }}
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            background-color: {qcolor_name(Colors.DISABLED_BG)};
            border: 2px solid {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
            border-radius: 3px;
        }}
        QCheckBox::indicator:checked {{
            background-color: {qcolor_name(Colors.DISABLED_BG)};
            border: 2px solid {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
            image: none;
        }}
        QCheckBox::indicator:checked:disabled {{
            background-color: {qcolor_name(Colors.DISABLED_BG)};
            border: 2px solid {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
            image: none;
        }}
        QCheckBox:disabled {{
            color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
        }}
    """


APPEND_PY_VERSION_STYLE = f"""
    QPushButton {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
    }}

    QPushButton:checked {{
        background-color: {qcolor_name(Colors.SUCCESS)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
    }}

    QPushButton:pressed {{
        background-color: {qcolor_name(Colors.SUCCESS_PRESSED)};
    }}

    QPushButton:disabled {{
        color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
        background-color: {qcolor_name(Colors.BUILD_DISABLED_BG)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
    }}
"""

APPEND_PY_VERSION_INITIAL_STYLE = APPEND_PY_VERSION_STYLE.replace("3px", "1px")

COMBO_BOX_STYLE = f"""
    QComboBox {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
        padding: 3px;
        font-weight:bold;
        font-size: 15px;
    }}

    QComboBox::drop-down {{
        border: none;
        background: {qcolor_name(Colors.WHITE)};
        padding: 10px;
    }}

    QComboBox::down-arrow {{
        background-color: {qcolor_name(Colors.WHITE)};
    }}

    QComboBox::drop-down:disabled,
    QComboBox::down-arrow:disabled {{
        background-color: {qcolor_name(Colors.COMBO_DISABLED_BG)};
        color: {qcolor_name(Colors.COMBO_DISABLED_TEXT)};
    }}

    {combo_box_popup_style("QComboBox QAbstractItemView")}

    QComboBox:disabled,
    QComboBox:disabled QLineEdit {{
        background-color: {qcolor_name(Colors.COMBO_DISABLED_BG)};
        color: {qcolor_name(Colors.COMBO_DISABLED_TEXT)};
        border-radius: 4px;
    }}
"""

COMBO_BOX_LINE_EDIT_STYLE = f"""
    QLineEdit {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        border: none;
        border-radius: 4px;
        padding-left: 18px;
        padding-right: 8px;
        font-family: "Rubik UI";
        font-size: 15px;
        font-weight: bold;
    }}

    QLineEdit:disabled {{
        background-color: {qcolor_name(Colors.COMBO_DISABLED_BG)};
        color: {qcolor_name(Colors.COMBO_DISABLED_TEXT)};
        border-radius: 4px;
    }}
"""

ENV_SYNC_STATUS_LINE_STYLE = f"""
    QLineEdit {{
        background-color: {qcolor_name(Colors.PANEL_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
        padding: 3px 8px;
        font-weight: bold;
    }}

    QLineEdit:read-only,
    QLineEdit:disabled {{
        background-color: {qcolor_name(Colors.PANEL_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
    }}
"""

ENV_SYNC_SCROLL_AREA_STYLE = f"""
    QScrollArea {{
        background-color: {qcolor_name(Colors.PANEL_BG)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
    }}

    QScrollArea QWidget {{
        background-color: {qcolor_name(Colors.PANEL_BG)};
    }}

    {vertical_scrollbar_style("QScrollArea")}

    QScrollArea QScrollBar:vertical,
    QScrollArea QScrollBar::handle,
    QScrollArea QScrollBar::sub-line:vertical,
    QScrollArea QScrollBar::add-line:vertical {{
        border: 2px solid {qcolor_name(Colors.BLACK)};
    }}
"""

ENV_SYNC_SCROLL_AREA_DISABLED_STYLE = f"""
    QScrollArea {{
        background-color: {qcolor_name(Colors.PANEL_BG)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
    }}

    QScrollArea QWidget {{
        background-color: {qcolor_name(Colors.PANEL_BG)};
    }}

    {vertical_scrollbar_style("QScrollArea")}
    {disabled_scrollbar_style("QScrollArea")}
"""

MAIN_FRAME_STYLE = f"""
    QFrame#configurationFrame,
    QWidget#configurationFrame {{
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 6px;
        background-color: {qcolor_name(Colors.PANEL_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
    }}
    QLabel {{
        color: {qcolor_name(Colors.TEXT_LIGHT)};
    }}
    QCheckBox {{
        color: {qcolor_name(Colors.TEXT_LIGHT)};
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        background-color: {qcolor_name(Colors.WHITE)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 3px;
    }}
    QCheckBox::indicator:checked {{
        background-color: {qcolor_name(Colors.WHITE)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        image: url({CHECKBOX_CHECK_BLACK_ICON});
    }}
"""

BUILD_DISABLED_MAIN_FRAME_STYLE = f"""
    QFrame#configurationFrame,
    QWidget#configurationFrame {{
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 6px;
        background-color: {qcolor_name(Colors.BUILD_DISABLED_BG)};
        color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
    }}
    QLabel {{
        color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
    }}
    QCheckBox {{
        color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
    }}
"""

BUILD_OPTIONS_FRAME_STYLE = f"""
    QFrame {{
        border: none;
        border-radius: 6px;
        background-color: {qcolor_name(Colors.WINDOW)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
    }}
    QLabel {{
        color: {qcolor_name(Colors.TEXT_LIGHT)};
    }}
    QCheckBox {{
        color: {qcolor_name(Colors.TEXT_LIGHT)};
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        background-color: {qcolor_name(Colors.WHITE)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 3px;
    }}
    QCheckBox::indicator:checked {{
        background-color: {qcolor_name(Colors.WHITE)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        image: url({CHECKBOX_CHECK_BLACK_ICON});
    }}
"""

BUILD_OPTIONS_DIALOG_STYLE = f"""
    QDialog {{
        background-color: {qcolor_name(Colors.PANEL_BG)};
    }}
    QDialog QCheckBox {{
        color: {qcolor_name(Colors.TEXT_LIGHT)};
    }}
    QDialog QCheckBox:disabled {{
        color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
    }}
    QDialog QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        background-color: {qcolor_name(Colors.WHITE)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 3px;
    }}
    QDialog QCheckBox::indicator:checked {{
        background-color: {qcolor_name(Colors.WHITE)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        image: url({CHECKBOX_CHECK_BLACK_ICON});
    }}
    QDialogButtonBox QPushButton {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
        font-weight: bold;
    }}
    QDialogButtonBox QPushButton:hover {{
        background-color: {qcolor_name(Colors.SURFACE_SELECTED_HOVER)};
    }}
"""

TITLE_FRAME_STYLE = f"""
    QFrame {{
        border: none;
        border-radius: 4px;
        background-color: {qcolor_name(Colors.WINDOW)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
    }}
    QLabel {{
        color: {qcolor_name(Colors.TEXT_LIGHT)};
    }}
"""

APP_TITLE_CONTAINER_STYLE = f"""
    QFrame#appTitleFrame {{
        border: none;
        border-radius: 0px;
        background-color: {qcolor_name(Colors.WINDOW)};
    }}
"""

APP_TITLE_LABEL_STYLE = f"""
    QLabel#appTitleLabel {{
        border: none;
        background-color: transparent;
        color: {qcolor_name(Colors.TEXT_LIGHT)};
    }}
"""

CENTER_DIVIDER_STYLE = f"""
    QFrame#centerDivider {{
        background-color: {qcolor_name(Colors.WHITE)};
        border: none;
    }}
"""

BUILD_DISABLED_TITLE_FRAME_STYLE = f"""
    QFrame {{
        border: none;
        border-radius: 4px;
        background-color: {qcolor_name(Colors.WINDOW)};
        color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
    }}
    QLabel {{
        color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
    }}
"""


def status_text_style(text_color: QColor, border_width: int = 3) -> str:
    return f"""
        QTextEdit {{
            background-color: {qcolor_name(Colors.PANEL_BG)};
            color: {qcolor_name(text_color)};
            border: none;
        }}
    """


def line_edit_style(text_color: QColor, border_color: QColor = Colors.WINDOW) -> str:
    return f"""
        QLineEdit {{
            background-color: {qcolor_name(Colors.PANEL_BG)};
            color: {qcolor_name(text_color)};
            border: 2px solid {qcolor_name(Colors.BLACK)};
            border-radius: 4px;
        }}
    """


def build_disabled_line_edit_style() -> str:
    return f"""
        QLineEdit {{
            background-color: {qcolor_name(Colors.PANEL_BG)};
            color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
            border: 2px solid {qcolor_name(Colors.BLACK)};
            border-radius: 4px;
        }}
    """


def env_sync_disabled_status_line_style() -> str:
    return f"""
        QLineEdit {{
            background-color: {qcolor_name(Colors.PANEL_BG)};
            color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
            border: 2px solid {qcolor_name(Colors.BLACK)};
            border-radius: 4px;
        }}
    """


SCRIPT_PICKER_FRAME_STYLE = f"""
    QFrame {{
        border: none;
        border-radius: 6px;
        background-color: {qcolor_name(Colors.POPUP_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
    }}
"""

SCRIPT_PICKER_LABEL_STYLE = f"""
    QLabel {{
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        font-family: "Rubik UI";
        font-size: 13px;
        font-weight: bold;
    }}
"""

SCRIPT_PICKER_DROPDOWN_STYLE = f"""
    QComboBox {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
        padding: 4px 8px;
        font-family: "Rubik UI";
        font-size: 13px;
        font-weight: bold;
    }}

    QComboBox::drop-down {{
        border: none;
        background-color: {qcolor_name(Colors.WHITE)};
        border-top-right-radius: 4px;
        border-bottom-right-radius: 4px;
        width: 28px;
    }}

    QComboBox::down-arrow {{
        background-color: {qcolor_name(Colors.WHITE)};
    }}

    QComboBox QAbstractItemView {{
        background-color: {qcolor_name(Colors.PANEL_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        selection-background-color: {qcolor_name(Colors.SELECTION_BG)};
        font-family: "Rubik UI";
        font-size: 13px;
        font-weight: bold;
        border: none;
    }}

    {combo_box_scrollbar_style()}
"""

SCRIPT_PICKER_CONFIRM_STYLE = f"""
    QPushButton {{
        background-color: {qcolor_name(Colors.SUCCESS)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
        padding: 6px 10px;
        font-family: "Rubik UI";
        font-size: 13px;
        font-weight: bold;
    }}

    QPushButton:hover {{
        background-color: {qcolor_name(Colors.SUCCESS_PRESSED)};
    }}

    QPushButton:pressed {{
        background-color: {qcolor_name(Colors.SUCCESS_PRESSED)};
    }}
"""

CONFIRMATION_MESSAGE_BOX_STYLE = f"""
    QMessageBox {{
        background-color: {qcolor_name(Colors.POPUP_BG)};
        border: none;
        border-radius: 6px;
    }}

    QMessageBox QLabel {{
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        font-family: "Rubik UI";
        font-size: 13px;
        font-weight: bold;
    }}

    QMessageBox QPushButton {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
        min-width: 80px;
        min-height: 28px;
        padding: 4px 12px;
        font-family: "Rubik UI";
        font-size: 13px;
        font-weight: bold;
    }}

    QMessageBox QPushButton:hover {{
        background-color: {qcolor_name(Colors.SURFACE_SELECTED_HOVER)};
    }}

    QMessageBox QPushButton:pressed {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
    }}
"""

RECENT_DELETE_MESSAGE_BOX_STYLE = CONFIRMATION_MESSAGE_BOX_STYLE

TOOLTIP_STYLE = f"""
    QLabel {{
        background-color: {qcolor_name(Colors.TOOLTIP_BG)};
        color: {qcolor_name(Colors.WHITE)};
        border: 2px solid {qcolor_name(Colors.TOOLTIP_BORDER)};
        padding: 6px;
        border-radius: 6px;
        font-family: "Rubik";
        font-size: 15px;
    }}
"""
