import sys
import json
import os
import ctypes
import threading
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ctypes import wintypes
from exe_builder.controllers.build_controller import BuildController
from exe_builder.controllers.dotnet_publish_controller import (
    DotnetPublishController,
    is_sdk_style_project,
    validate_executable_name,
)
from exe_builder.build.datetime_build_options import (
    ISO_MASS_DATETIME_BUILD_LABEL,
    ISO_MASS_DATETIME_BUILD_SENTINEL,
    MASS_DATETIME_BUILD_LABEL,
    MASS_DATETIME_BUILD_SENTINEL,
    NO_DATETIME_LABEL,
    REGIONAL_DATETIME_DROPDOWN_GROUPS,
    UK_MASS_DATETIME_BUILD_LABEL,
    UK_MASS_DATETIME_BUILD_SENTINEL,
    USA_MASS_DATETIME_BUILD_LABEL,
    USA_MASS_DATETIME_BUILD_SENTINEL,
)
from exe_builder.controllers.environment_sync_controller import EnvironmentSyncController
from exe_builder.ui.path_hover import attach_path_hovers
from exe_builder.ui.tooltips import attach_tooltips
from PySide6.QtCore import QPoint, QSize, Qt, QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton,QFrame,QApplication,QHBoxLayout,QVBoxLayout,QCheckBox,QLineEdit,QHBoxLayout,QGridLayout,QComboBox,QTextEdit,QListView,QListWidget,QScrollArea,QMessageBox,QDialog,QDialogButtonBox,QStackedWidget,QFileDialog,QMenu,QToolButton
from exe_builder.controllers.validation_controller import ValidationController
from exe_builder.controllers.activation_controller import ActivationController
from PySide6.QtGui import QFont, QIcon, QPalette
from PySide6.QtWidgets import QSizePolicy
from exe_builder.controllers.file_pickers import FilePickerController
from exe_builder.ui.path_display_line_edit import PathDisplayLineEdit
from exe_builder.controllers.state_controller import StateController
from exe_builder.controllers.recent_controller import RecentController
from exe_builder.controllers.ui_handlers import UIHandlers
from exe_builder.controllers.json_import_controller import JsonImportController
from exe_builder.controllers.output_folder_monitor import (
    OUTPUT_FOLDER_MONITOR_INTERVAL_MS,
    OutputFolderValidityMonitor,
)
from PySide6.QtGui import QFontMetrics
from PySide6.QtGui import QTextCursor, QTextBlockFormat
from exe_builder.ui.styles import (
    APPEND_PY_VERSION_INITIAL_STYLE,
    APP_TITLE_CONTAINER_STYLE,
    APP_TITLE_LABEL_STYLE,
    BUILD_OPTIONS_DIALOG_STYLE,
    CENTER_DIVIDER_STYLE,
    COMBO_BOX_STYLE,
    COMBO_BOX_LINE_EDIT_STYLE,
    CONFIRMATION_MESSAGE_BOX_STYLE,
    DELETE_ALL_BUTTON_ICON,
    DELETE_ALL_BUTTON_ICON_SIZE,
    DELETE_ALL_BUTTON_TEXT,
    DELETE_BUTTON_ICON,
    DELETE_BUTTON_ICON_SIZE,
    DELETE_BUTTON_TEXT,
    ENV_SYNC_BUTTON_STYLE,
    ENV_SYNC_SCROLL_AREA_STYLE,
    ENV_SYNC_STATUS_LINE_STYLE,
    REFRESH_BUTTON_ICON,
    REFRESH_BUTTON_ICON_SIZE,
    REFRESH_BUTTON_TEXT,
    UTILITY_ICON_BUTTON_SIZE,
    apply_native_title_bar_style,
    apply_build_options_title_bar_style,
    combo_box_popup_style,
    MAIN_FRAME_STYLE,
    TITLE_FRAME_STYLE,
    apply_build_mode_button_state,
    build_disabled_checkbox,
    build_mode_button_font,
    button_base,
    qcolor_name,
    required_selection_checkbox,
    sidebar_menu_button_style,
    status_text_style,
    Colors,
    utility_icon_button_style,
)

APP_FIXED_WIDTH = 850
PYTHON_APP_FIXED_SIZE = (APP_FIXED_WIDTH, 840)
DOTNET_APP_FIXED_SIZE = (APP_FIXED_WIDTH, 866)
NAVIGATION_SIDEBAR_WIDTH = 205
CONTENT_PANE_WIDTH = APP_FIXED_WIDTH - NAVIGATION_SIDEBAR_WIDTH
CONTENT_COLUMN_WIDTH = 599
PATH_DROPDOWN_SIZE = (320, 35)
PAIRED_FRAME_WIDTH = 575
ENV_SYNC_CONTENT_WIDTH = 560
ENV_SYNC_TABLE_PADDING = 6
BUILD_ACTION_FRAME_WIDTH = 450
PROGRESSION_BUTTON_SIZE = (280, 42)
SELECTOR_ROW_MARGINS = (1, 1, 1, 1)
SELECTOR_ROW_SPACING = 4
PATH_ENTRY_ROW_SPACING = 3
SELECTOR_SECTION_ROW_SPACING = 3
SECTION_NAV_STYLE = (
    "QListWidget { background: #19232d; border: 0; padding: 4px 0; "
    "color: #ecf3fa; font: bold 12pt 'Rubik UI'; } "
    "QListWidget::item { height: 38px; padding-left: 14px; border-left: 4px solid transparent; } "
    "QListWidget::item:selected { background: #263a4d; color: white; border-left-color: #4a6fa8; } "
    "QListWidget::item:hover:!selected { background: #24313e; } "
    "QListWidget::item:disabled { color: #71808c; background: transparent; } "
    "QListWidget::item:selected:disabled { color: #71808c; background: transparent; }"
)
SAVED_SETUP_COMBO_BOX_STYLE = COMBO_BOX_STYLE + """
    QComboBox { font: bold 12pt 'Rubik UI'; }
    QComboBox QAbstractItemView { font: bold 12pt 'Rubik UI'; }
"""
SAVED_SETUP_DELETE_MENU_STYLE = f"""
    QToolButton {{
        background-color: {qcolor_name(Colors.TITLE_BG)};
        color: {qcolor_name(Colors.TEXT_LIGHT)};
        border: 2px solid {qcolor_name(Colors.BLACK)};
        border-radius: 4px;
        padding: 2px 10px 2px 2px;
    }}
    QToolButton:hover {{ background-color: {qcolor_name(Colors.SURFACE_SELECTED_HOVER)}; }}
    QToolButton::menu-button {{
        width: 18px;
        border-left: 1px solid {qcolor_name(Colors.BLACK)};
    }}
    QToolButton:disabled {{
        background-color: {qcolor_name(Colors.DISABLED_BG)};
        color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};
    }}
"""

mutex = ctypes.windll.kernel32.CreateMutexW(
    None,
    wintypes.BOOL(True),
    "EXEBUILDER_MUTEX"
)

# ERROR_ALREADY_EXISTS means another instance is running
if ctypes.GetLastError() == 183:
    event = ctypes.windll.kernel32.OpenEventW(
        0x00100002,
        False,
        "EXEBUILDER_ACTIVATE_EVENT"
    )

    if event:
        ctypes.windll.kernel32.SetEvent(event)
    sys.exit(0)

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# -------------------------------------------------------------
#  EXE Builder App
# -------------------------------------------------------------

class EXEBuilderApp(QWidget):
    def __init__(self):
        super().__init__()
        self._is_closing = False

        self._eta_running = False
        self._loading_state = True
        self.building = False

        self.entry_script = None
        self.project_root = None
        self.exe_name_user_modified = False
        
        self.json_import_controller =JsonImportController(self)
        self.recent_controller = RecentController(self)
        self.ui_handlers = UIHandlers(self)
        self.environment_sync_controller = EnvironmentSyncController(self)
        self.build_controller = BuildController(self)
        self.dotnet_publish_controller = DotnetPublishController(self)
        self.validation_controller = ValidationController(self)
        self.state_ctrl = StateController(self)
        self.validator = ValidationController(self)
        self.activation_controller = ActivationController(self)
        self.file_pickers = FilePickerController(self)
        
        # ---------------------------------------------------------
        # SINGLE INSTANCE: Listen for activation events
        # ---------------------------------------------------------

        self.activate_event = ctypes.windll.kernel32.CreateEventW(None,False,False,"EXEBUILDER_ACTIVATE_EVENT")
        threading.Thread(target=self.activation_controller.listen_for_activation,daemon=True).start()

        # ---------------------------------------------------------
        # ALWAYS ON TOP
        # ---------------------------------------------------------

        self.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowCloseButtonHint
            | Qt.WindowStaysOnTopHint
            | Qt.MSWindowsFixedSizeDialogHint
        )
        self.build_process = None
        self.current_build_paths = []
        self.build_btn = None
        self.last_build_seconds = 45
        self.last_build_counter = 0
        
        self.setFixedSize(*PYTHON_APP_FIXED_SIZE)
        self.setWindowTitle(" ")
        self.setContentsMargins(0,0,0,0)
        
        self.close_after_build_enabled = getattr(self, "close_after_build_enabled", True)
        self.minimize_after_build_enabled = getattr(self, "minimize_after_build_enabled", True)
        self.open_output_dir_after_build_enabled = getattr(self, "open_output_dir_after_build_enabled", False)
        self.run_built_app_after_build_enabled = getattr(self, "run_built_app_after_build_enabled", False)
        self.suppress_exit_dialogue_enabled = getattr(self, "suppress_exit_dialogue_enabled", False)
        self.tooltips_enabled = getattr(self, "tooltips_enabled", True)
        self.script_path = getattr(self, "script_path", "")
        self.icon_path = getattr(self, "icon_path", "")
        self.output_path = getattr(self, "output_path", "")
        self.python_path = getattr(self, "python_path", "")
        self.exe_name = getattr(self, "exe_name", "")
        self.build_mode = "python"
        self.guided_flow_enabled = True
        self._completed_python_steps = set()
        self._completed_dotnet_steps = set()
        self.saved_build_setups = []
        self.saved_dotnet_build_setups = []
        self._saved_setup_backup_status_tokens = {"python": 0, "dotnet": 0}
                    
        # =============================================================
        # Title + Build Options
        # =============================================================
        self.title_frame = QFrame()
        self.title_frame.setObjectName("appTitleFrame")
        self.title_frame.setFrameShape(QFrame.NoFrame)
        self.title_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.title_frame.setFixedHeight(44)
        self.title_frame.setStyleSheet(APP_TITLE_CONTAINER_STYLE)

        title_layout = QHBoxLayout(self.title_frame)
        title_layout.setContentsMargins(5,5,5,5)
        title_layout.setSpacing(0)

        self.title_label = QLabel("Win 11 → Python → EXE Builder")
        self.title_label.setObjectName("appTitleLabel")
        self.title_label.setFont(QFont("Rubik UI", 18, QFont.Bold))
        self.title_label.setFixedHeight(34)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(APP_TITLE_LABEL_STYLE)

        self.build_options_btn = QPushButton("☰")
        self.build_options_btn.setObjectName("buildOptionsButton")
        self.build_options_btn.setAccessibleName("Options menu")
        self.build_options_btn.setAccessibleDescription(
            "Open build options and application preferences."
        )
        self.build_options_btn.setFixedSize(34, 34)
        self.build_options_btn.setFont(QFont("Segoe UI Symbol", 16, QFont.Bold))
        self.build_options_btn.setStyleSheet(sidebar_menu_button_style())

        title_frame_width = (
            QFontMetrics(self.title_label.font()).horizontalAdvance(
                self.title_label.text()
            ) + 25
        )
        self.title_frame.setFixedWidth(title_frame_width)

        title_layout.addStretch()
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        # -------------------------------
        # BUILD OPTIONS DIALOG
        # -------------------------------

        self.tooltips_checkbox = QCheckBox("Tooltips")
        self.minimize_after_build = QCheckBox("Minimize After Build")
        self.suppress_exit_dialogue = QCheckBox("Surpress Exit Dialogue")
        self.open_output_dir_after_build = QCheckBox("Open Output Directory")
        self.run_built_app_after_build = QCheckBox("Run Built App")
        self.close_after_build = QCheckBox("Close After Build")
        self.open_app_data_btn = QPushButton("Open App Data")

        toggle_grid = QGridLayout()
        toggle_grid.setContentsMargins(0, 0, 0, 0)
        toggle_grid.setHorizontalSpacing(20)
        toggle_grid.setVerticalSpacing(8)
        toggle_grid.setColumnStretch(0, 1)
        toggle_grid.setColumnStretch(1, 1)

        for row, left, right in (
            (0, self.tooltips_checkbox, self.open_output_dir_after_build),
            (1, self.minimize_after_build, self.run_built_app_after_build),
            (2, self.suppress_exit_dialogue, self.close_after_build),
        ):
            toggle_grid.addWidget(left, row, 0, alignment=Qt.AlignLeft | Qt.AlignTop)
            toggle_grid.addWidget(right, row, 1, alignment=Qt.AlignLeft | Qt.AlignTop)
        toggle_grid.addWidget(self.open_app_data_btn, 3, 0, alignment=Qt.AlignLeft | Qt.AlignTop)

        self.build_options_dialog = QDialog(self)
        self.build_options_dialog.setWindowTitle("Global Build Options")
        self.build_options_dialog.setModal(True)
        self.build_options_dialog.setFixedSize(500, 220)
        self.build_options_dialog.setStyleSheet(BUILD_OPTIONS_DIALOG_STYLE)
        apply_build_options_title_bar_style(self.build_options_dialog)

        build_options_layout = QVBoxLayout(self.build_options_dialog)
        build_options_layout.setContentsMargins(20, 20, 20, 20)
        build_options_layout.setSpacing(8)
        build_options_layout.addLayout(toggle_grid)

        build_options_buttons = QDialogButtonBox(QDialogButtonBox.Close)
        build_options_buttons.rejected.connect(self.build_options_dialog.reject)
        build_options_buttons.setCenterButtons(True)
        self.build_options_close_btn = build_options_buttons.button(
            QDialogButtonBox.Close
        )
        self.build_options_close_btn.setFixedSize(120, 32)
        self.build_options_close_btn.setFont(QFont("Rubik UI", 13, QFont.Bold))
        build_options_layout.addWidget(build_options_buttons)

        # -------------------------------
        # MAIN LAYOUT
        # -------------------------------

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.setAlignment(Qt.AlignTop)

        title_row = QWidget()
        title_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        title_row.setFixedSize(APP_FIXED_WIDTH, 44)
        title_row_layout = QHBoxLayout(title_row)
        title_row_layout.setContentsMargins(0, 0, 0, 0)
        title_row_layout.setSpacing(0)
        self.python_title_navigation_header = QWidget()
        self.python_title_navigation_header.setFixedWidth(NAVIGATION_SIDEBAR_WIDTH)
        title_navigation_layout = QHBoxLayout(self.python_title_navigation_header)
        title_navigation_layout.setContentsMargins(5, 0, 0, 0)
        title_navigation_layout.setSpacing(0)
        self.title_options_slot = QWidget()
        self.title_options_slot.setFixedSize(34, 34)
        self.title_options_layout = QHBoxLayout(self.title_options_slot)
        self.title_options_layout.setContentsMargins(0, 0, 0, 0)
        title_navigation_layout.addWidget(
            self.title_options_slot, alignment=Qt.AlignLeft | Qt.AlignVCenter
        )
        self.python_title_content_header = QWidget()
        self.python_title_content_header.setFixedWidth(CONTENT_PANE_WIDTH)
        self.title_frame.setParent(self.python_title_content_header)
        title_row_layout.addWidget(self.python_title_navigation_header)
        title_row_layout.addWidget(self.python_title_content_header)

        self.content_row = QWidget()
        self.content_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        content_row_layout = QHBoxLayout(self.content_row)
        content_row_layout.setContentsMargins(0, 0, 0, 0)
        content_row_layout.setSpacing(0)

        build_title_row = QWidget()
        build_title_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        build_title_row_layout = QHBoxLayout(build_title_row)
        build_title_row_layout.setContentsMargins(0, 0, 0, 0)
        build_title_row_layout.setSpacing(0)

        build_frame_row = QWidget()
        build_frame_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        build_frame_row_layout = QHBoxLayout(build_frame_row)
        build_frame_row_layout.setContentsMargins(0, 0, 0, 0)
        build_frame_row_layout.setSpacing(0)

        self.left_content, self.left_layout = self._create_content_column()
        self.right_content, self.right_layout = self._create_content_column()
        self.main_layout = self.right_layout
        self.center_divider = QFrame()
        self.center_divider.setObjectName("centerDivider")
        self.center_divider.setFrameShape(QFrame.NoFrame)
        self.center_divider.setFixedWidth(2)
        self.center_divider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.center_divider.setStyleSheet(CENTER_DIVIDER_STYLE)

        content_row_layout.addWidget(self.left_content, alignment=Qt.AlignTop)
        content_row_layout.addWidget(self.center_divider, alignment=Qt.AlignBottom)
        content_row_layout.addWidget(self.right_content, alignment=Qt.AlignTop)

        root_layout.addWidget(title_row)
        root_layout.addWidget(self.content_row)
        root_layout.addWidget(build_title_row)
        root_layout.addWidget(build_frame_row)

        # =============================================================
        # Script / Buttons Section
        # =============================================================

        # =============================================================
        # Environment Sync Section
        # =============================================================

        self.env_sync_title_frame = QFrame()
        self.env_sync_title_frame.setFrameShape(QFrame.StyledPanel)
        self.env_sync_title_frame.setFrameShadow(QFrame.Raised)

        env_sync_title_layout = QHBoxLayout(self.env_sync_title_frame)
        env_sync_title_layout.setContentsMargins(3,3,3,3)
        env_sync_title_layout.setSpacing(3)

        self.env_sync_title = QLabel("Environment Sync")
        self.env_sync_title.setFixedHeight(30)
        self.env_sync_title.setFont(QFont("Rubik UI", 14, QFont.Bold))

        env_sync_title_layout.addStretch()
        env_sync_title_layout.addWidget(self.env_sync_title)
        env_sync_title_layout.addStretch()

        self.env_sync_frame = QFrame()
        self.env_sync_frame.setFrameShape(QFrame.StyledPanel)
        self.env_sync_frame.setFrameShadow(QFrame.Raised)

        env_sync_layout = QVBoxLayout(self.env_sync_frame)
        env_sync_layout.setContentsMargins(6,6,6,6)
        env_sync_layout.setSpacing(4)
        
        self.env_sync_log_input = QLineEdit()
        self.env_sync_log_input.setReadOnly(True)
        self.env_sync_log_input.setFocusPolicy(Qt.NoFocus)
        self.env_sync_log_input.setFixedWidth(ENV_SYNC_CONTENT_WIDTH)
        self.env_sync_log_input.setPlaceholderText("Environment sync ready.")
        self.env_sync_log_input.setText("Environment sync ready.")
        self.env_sync_log_input.setFont(QFont("Rubik UI", 11, QFont.Bold))
        self.env_sync_log_input.setStyleSheet(ENV_SYNC_STATUS_LINE_STYLE)

        self.env_sync_action_row = QWidget()
        env_sync_action_layout = QHBoxLayout(self.env_sync_action_row)
        env_sync_action_layout.setContentsMargins(0,0,0,0)
        env_sync_action_layout.setSpacing(4)

        self.env_sync_scan_btn = QPushButton("Scan Profiles")
        self.env_sync_match_btn = QPushButton("Sync Dependencies")
        self.env_sync_help_btn = QPushButton("?")
        self.env_sync_scan_btn.setFixedSize(145,35)
        self.env_sync_match_btn.setFixedSize(175,35)
        self.env_sync_help_btn.setFixedSize(35,35)
        self.env_sync_help_btn.setFont(QFont("Rubik UI", 14, QFont.Bold))
        self.env_sync_match_btn.setEnabled(False)
        self.env_sync_scan_btn.setStyleSheet(ENV_SYNC_BUTTON_STYLE)
        self.env_sync_match_btn.setStyleSheet(ENV_SYNC_BUTTON_STYLE)
        self.env_sync_help_btn.setStyleSheet(ENV_SYNC_BUTTON_STYLE)

        env_sync_action_layout.addWidget(self.env_sync_scan_btn)
        env_sync_action_layout.addWidget(self.env_sync_match_btn)
        env_sync_action_layout.addWidget(self.env_sync_help_btn)
        env_sync_action_layout.addStretch()

        self.env_sync_warning_label = QLabel(
            "Warning: sync may fail if packages are incompatible."
        )
        self.env_sync_warning_label.setFixedWidth(485)
        self.env_sync_warning_label.setFont(QFont("Rubik UI", 10, QFont.Bold))
        self.env_sync_warning_label.setStyleSheet(
            f"QLabel {{ color: {qcolor_name(Colors.WARNING)}; }}"
        )

        self.env_sync_status_header = QWidget()
        env_sync_status_header_layout = QHBoxLayout(self.env_sync_status_header)
        env_sync_status_header_layout.setContentsMargins(
            ENV_SYNC_TABLE_PADDING,
            ENV_SYNC_TABLE_PADDING,
            ENV_SYNC_TABLE_PADDING,
            ENV_SYNC_TABLE_PADDING,
        )
        env_sync_status_header_layout.setSpacing(4)

        self.env_sync_status_labels = []
        self.env_sync_row_labels = []

        for text, width in [
            ("Python Version", 125),
            ("Packages", 80),
            ("State", 275),
        ]:
            label = QLabel(text)
            label.setFixedWidth(width)
            label.setFont(QFont("Rubik UI", 10, QFont.Bold))
            self.env_sync_status_labels.append(label)
            env_sync_status_header_layout.addWidget(label)

        env_sync_status_header_layout.addStretch()

        self.env_sync_rows_container = QWidget()
        self.env_sync_rows_layout = QVBoxLayout(self.env_sync_rows_container)
        self.env_sync_rows_layout.setContentsMargins(
            ENV_SYNC_TABLE_PADDING,
            ENV_SYNC_TABLE_PADDING,
            ENV_SYNC_TABLE_PADDING,
            ENV_SYNC_TABLE_PADDING,
        )
        self.env_sync_rows_layout.setSpacing(2)

        env_sync_visible_rows = 5
        env_sync_row_height = 22
        env_sync_row_spacing = self.env_sync_rows_layout.spacing()
        env_sync_scroll_height = (
            env_sync_visible_rows * env_sync_row_height
            + (env_sync_visible_rows - 1) * env_sync_row_spacing
            + (2 * ENV_SYNC_TABLE_PADDING)
        )
        self._env_sync_rows_scroll_base_height = env_sync_scroll_height

        self.env_sync_rows_scroll_area = QScrollArea()
        self.env_sync_rows_scroll_area.setWidgetResizable(True)
        self.env_sync_rows_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.env_sync_rows_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.env_sync_rows_scroll_area.setFixedHeight(env_sync_scroll_height)
        self.env_sync_rows_scroll_area.setFrameShape(QFrame.NoFrame)
        self.env_sync_rows_scroll_area.setStyleSheet(ENV_SYNC_SCROLL_AREA_STYLE)
        self.env_sync_rows_scroll_area.setWidget(self.env_sync_rows_container)

        env_sync_layout.addWidget(self.env_sync_action_row)
        env_sync_layout.addWidget(self.env_sync_warning_label)
        env_sync_layout.addWidget(self.env_sync_status_header)
        env_sync_layout.addWidget(self.env_sync_rows_scroll_area)
        env_sync_layout.addWidget(self.env_sync_log_input)
        self.add_env_sync_status_row("", "", "Press Scan Profiles")

        self.left_layout.addWidget(self.env_sync_title_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)
        self.left_layout.addWidget(self.env_sync_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)

        row2 = QWidget(self)
        row2_layout = QVBoxLayout(row2)
        row2_layout.setContentsMargins(0,0,0,0)
        row2_layout.setSpacing(0)

        self.interpreter_frame = QFrame()
        self.interpreter_frame.setFrameShape(QFrame.StyledPanel)
        self.interpreter_frame.setFrameShadow(QFrame.Raised)

        combined_layout = QVBoxLayout(self.interpreter_frame)
        combined_layout.setContentsMargins(3,3,3,3)
        combined_layout.setSpacing(3)

        # =================================================
        # Apps TITLE FRAME
        # =================================================

        self.apps_title_frame = QFrame()
        self.apps_title_frame.setFrameShape(QFrame.StyledPanel)
        self.apps_title_frame.setFrameShadow(QFrame.Raised)

        apps_title_layout = QHBoxLayout(self.apps_title_frame)
        apps_title_layout.setContentsMargins(3,3,3,3)
        apps_title_layout.setSpacing(3)

        self.apps_title = QLabel("Interpreter Select")
        self.apps_title.setFixedHeight(30)
        self.apps_title.setFont(QFont("Rubik UI", 14, QFont.Bold))

        apps_title_layout.addStretch()
        apps_title_layout.addWidget(self.apps_title)
        apps_title_layout.addStretch()

        # =================================================
        # Apps ROW (buttons)
        # =================================================

        apps_row = QWidget()
        apps_row.setFixedHeight(37)
        apps_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        apps_layout = QHBoxLayout(apps_row)
        apps_layout.setContentsMargins(*SELECTOR_ROW_MARGINS)
        apps_layout.setSpacing(SELECTOR_ROW_SPACING)

        self.open_python_site_btn = QPushButton("Python.org")
        apps_layout.addWidget(self.open_python_site_btn)
        apps_layout.addStretch()

        # =================================================
        # Interpreter (VERTICAL stack)
        # =================================================

        interpreter_container = QWidget()
        interpreter_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        interpreter_layout = QVBoxLayout(interpreter_container)
        interpreter_layout.setContentsMargins(0, 0, 0, 0)
        interpreter_layout.setSpacing(SELECTOR_SECTION_ROW_SPACING)

        interpreter_btn_row = QWidget()
        interpreter_btn_row.setFixedHeight(37)
        interpreter_btn_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        interpreter_btn_layout = QHBoxLayout(interpreter_btn_row)
        interpreter_btn_layout.setContentsMargins(*SELECTOR_ROW_MARGINS)
        interpreter_btn_layout.setSpacing(SELECTOR_ROW_SPACING)
        self.interpreter_btn = QPushButton("Py Interpreter")
    
        self.select_interpreter = QComboBox()
        self.select_interpreter.setFixedSize(*PATH_DROPDOWN_SIZE)
        self.select_interpreter.setFont(QFont("Rubik UI", 12))
        interpreter_popup_view = QListView()
        interpreter_popup_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        interpreter_popup_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        interpreter_popup_view.setStyleSheet(combo_box_popup_style())
        self.select_interpreter.setView(interpreter_popup_view)

        # 🔑 Header
        self.select_interpreter.addItem("Select Recent Interpreter")
    
        model = self.select_interpreter.model()
        item = model.item(0)
        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)

        # 🔑 Placeholder behavior
        self.select_interpreter.setEditable(True)
        self.select_interpreter.lineEdit().setReadOnly(True)
        self.select_interpreter.setEnabled(True)

        self.python_delete_interpreter = QPushButton(DELETE_BUTTON_TEXT)
        self.python_delete_interpreter.setIcon(QIcon(str(DELETE_BUTTON_ICON)))
        self.python_delete_interpreter.setIconSize(QSize(*DELETE_BUTTON_ICON_SIZE))
        self.python_delete_all_interpreter = QPushButton(DELETE_ALL_BUTTON_TEXT)
        self.python_delete_all_interpreter.setIcon(QIcon(str(DELETE_ALL_BUTTON_ICON)))
        self.python_delete_all_interpreter.setIconSize(QSize(*DELETE_ALL_BUTTON_ICON_SIZE))

        interpreter_btn_layout.addWidget(self.interpreter_btn)
        interpreter_btn_layout.addWidget(self.select_interpreter)
        interpreter_btn_layout.addWidget(self.python_delete_interpreter)
        interpreter_btn_layout.addWidget(self.python_delete_all_interpreter)
        interpreter_btn_layout.addStretch()

        interpreter_layout.addWidget(interpreter_btn_row)

        # --- Path row (input + refresh inline) ---
        interpreter_entry_row = QWidget()
        interpreter_entry_row.setFixedHeight(52)
        interpreter_entry_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        interpreter_entry_layout = QHBoxLayout(interpreter_entry_row)
        interpreter_entry_layout.setContentsMargins(*SELECTOR_ROW_MARGINS)
        interpreter_entry_layout.setSpacing(PATH_ENTRY_ROW_SPACING)

        self.python_entry_input = PathDisplayLineEdit()
        self.python_entry_input.setPlaceholderText("No python entry is selected.")

        self.interpreter_refresh_btn = QPushButton(REFRESH_BUTTON_TEXT)
        self.interpreter_refresh_btn.setFixedSize(*UTILITY_ICON_BUTTON_SIZE)

        interpreter_entry_layout.addWidget(self.python_entry_input)
        interpreter_entry_layout.addWidget(self.interpreter_refresh_btn)
        interpreter_layout.addWidget(interpreter_entry_row)

        # --- Final attach ---
        self.left_layout.addWidget(self.apps_title_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)
        combined_layout.addWidget(apps_row)
        combined_layout.addWidget(interpreter_container)
        combined_layout.addStretch()

        row2_layout.addWidget(self.interpreter_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)
        self.left_layout.addWidget(row2, alignment=Qt.AlignHCenter | Qt.AlignTop)
 
        # =============================================================
        # Icon Picker
        # =============================================================

        self.icons_title_frame = QFrame()
        self.icons_title_frame.setFrameShape(QFrame.StyledPanel)
        self.icons_title_frame.setFrameShadow(QFrame.Raised)
  
        icons_title_layout = QHBoxLayout(self.icons_title_frame)
        icons_title_layout.setContentsMargins(3,3,3,3)
        icons_title_layout.setSpacing(3)

        self.icons_title = QLabel("Icons Select")
        self.icons_title.setFixedHeight(30)
        self.icons_title.setFont(QFont("Rubik UI", 14, QFont.Bold))

        icons_title_layout.addStretch()
        icons_title_layout.addWidget(self.icons_title)
        icons_title_layout.addStretch()

        self.icon_frame = QFrame()
        self.icon_frame.setFrameShape(QFrame.StyledPanel)
        self.icon_frame.setFrameShadow(QFrame.Raised)

        icon_frame_layout = QVBoxLayout(self.icon_frame)
        icon_frame_layout.setContentsMargins(*SELECTOR_ROW_MARGINS)
        icon_frame_layout.setSpacing(SELECTOR_SECTION_ROW_SPACING)

        icon_block = QWidget()
        icon_block_layout = QVBoxLayout(icon_block)
        icon_block_layout.setContentsMargins(*SELECTOR_ROW_MARGINS)
        icon_block_layout.setSpacing(SELECTOR_SECTION_ROW_SPACING)

        # -------- Row 1: Select Icon + Recent Dropdown + Delete --------

        icon_row1 = QWidget()
        icon_row1_layout = QHBoxLayout(icon_row1)
        icon_row1_layout.setContentsMargins(*SELECTOR_ROW_MARGINS)
        icon_row1_layout.setSpacing(SELECTOR_ROW_SPACING)

        self.icon_btn = QPushButton("Select ICO optional")

        self.select_recent_icons = QComboBox()
        self.select_recent_icons.setFixedSize(*PATH_DROPDOWN_SIZE)
        self.select_recent_icons.setFont(QFont("Rubik UI", 12))
        self.select_recent_icons.addItem("Select Recent Icon")

        model = self.select_recent_icons.model()
        item = model.item(0)
        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)

        # placeholder behavior
        self.select_recent_icons.setEditable(True)
        self.select_recent_icons.lineEdit().setReadOnly(True)
        self.select_recent_icons.setEnabled(True)

        self.delete_recent_icons = QPushButton(DELETE_BUTTON_TEXT)
        self.delete_recent_icons.setIcon(QIcon(str(DELETE_BUTTON_ICON)))
        self.delete_recent_icons.setIconSize(QSize(*DELETE_BUTTON_ICON_SIZE))
        self.delete_all_icons = QPushButton(DELETE_ALL_BUTTON_TEXT)
        self.delete_all_icons.setIcon(QIcon(str(DELETE_ALL_BUTTON_ICON)))
        self.delete_all_icons.setIconSize(QSize(*DELETE_ALL_BUTTON_ICON_SIZE))

        # -------- Row 2: ICO Converter (below) --------

        icon_row2 = QWidget()
        icon_row2_layout = QHBoxLayout(icon_row2)
        icon_row2_layout.setContentsMargins(*SELECTOR_ROW_MARGINS)
        icon_row2_layout.setSpacing(SELECTOR_ROW_SPACING)

        self.ico_convert_btn = QPushButton("Open ICO Convert")
        icon_row1_layout.addWidget(self.ico_convert_btn)
        icon_row1_layout.addStretch()
        icon_block_layout.addWidget(icon_row1)

        icon_row2_layout.addWidget(self.icon_btn)
        icon_row2_layout.addWidget(self.select_recent_icons)
        icon_row2_layout.addWidget(self.delete_recent_icons)
        icon_row2_layout.addWidget(self.delete_all_icons)
        icon_row2_layout.addStretch()
        icon_block_layout.addWidget(icon_row2)

        # -------- Row 3: Entry + Clear --------

        icon_entry_row = QWidget()
        icon_entry_layout = QHBoxLayout(icon_entry_row)
        icon_entry_layout.setContentsMargins(*SELECTOR_ROW_MARGINS)
        icon_entry_layout.setSpacing(PATH_ENTRY_ROW_SPACING)

        self.icon_path_input = PathDisplayLineEdit()
        self.icon_path_input.setPlaceholderText("icon_path_input")
        self.icon_clear_btn = QPushButton("")

        icon_entry_layout.addWidget(self.icon_path_input)
        icon_entry_layout.addWidget(self.icon_clear_btn)
        icon_block_layout.addWidget(icon_entry_row)
        
        icon_frame_layout.addWidget(icon_block)
        self.main_layout.addWidget(self.icons_title_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)
        self.main_layout.addWidget(self.icon_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)

        # =================================================
        # PYTHON FILE TITLE FRAME
        # =================================================

        self.python_title_frame = QFrame()
        self.python_title_frame.setFrameShape(QFrame.StyledPanel)
        self.python_title_frame.setFrameShadow(QFrame.Raised)

        python_title_layout = QHBoxLayout(self.python_title_frame)
        python_title_layout.setContentsMargins(3,3,3,3)
        python_title_layout.setSpacing(3)

        self.python_title = QLabel("File Select")
        self.python_title.setFixedHeight(30)
        self.python_title.setFont(QFont("Rubik UI", 14, QFont.Bold))

        python_title_layout.addStretch()
        python_title_layout.addWidget(self.python_title)
        python_title_layout.addStretch()

        python_frame = QFrame()
        python_frame.setFrameShape(QFrame.StyledPanel)
        python_frame.setFrameShadow(QFrame.Raised)


        python_layout = QVBoxLayout(python_frame)
        python_layout.setContentsMargins(3,3,3,3)
        python_layout.setSpacing(3)

        # =================================================
        # Row 1: Select folder button + recent dropdown
        # =================================================

        self.folder_btn = QPushButton("Python File")
      
        self.recent_folder_dropdown = QComboBox()
        self.recent_folder_dropdown.setFixedSize(*PATH_DROPDOWN_SIZE)
        self.recent_folder_dropdown.setFont(QFont("Rubik UI", 12))
        self.recent_folder_dropdown.addItem("Select Recent File")
        
        model = self.recent_folder_dropdown.model()
        item = model.item(0)
        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
        
        self.recent_folder_dropdown.setEditable(True)
        self.recent_folder_dropdown.lineEdit().setReadOnly(True)
        self.recent_folder_dropdown.setEnabled(True)
        
        self.delete_recent_folder = QPushButton(DELETE_BUTTON_TEXT)
        self.delete_recent_folder.setIcon(QIcon(str(DELETE_BUTTON_ICON)))
        self.delete_recent_folder.setIconSize(QSize(*DELETE_BUTTON_ICON_SIZE))
        self.delete_all_folders = QPushButton(DELETE_ALL_BUTTON_TEXT)
        self.delete_all_folders.setIcon(QIcon(str(DELETE_ALL_BUTTON_ICON)))
        self.delete_all_folders.setIconSize(QSize(*DELETE_ALL_BUTTON_ICON_SIZE))
   
        folder_row = QHBoxLayout()
        folder_row.setContentsMargins(*SELECTOR_ROW_MARGINS)
        folder_row.setSpacing(SELECTOR_ROW_SPACING)

        python_layout.addLayout(folder_row)

        # =================================================
        # Row 3: Path + clear (side-by-side)
        # =================================================

        script_row = QWidget()
        script_layout = QHBoxLayout(script_row)
        script_layout.setContentsMargins(3,3,3,3)
        script_layout.setSpacing(3)

        self.script_path_input = PathDisplayLineEdit()

        self.script_path_input.setPlaceholderText("No python file has been selected.")
        script_layout.addWidget(self.script_path_input)

        self.script_clear_btn = QPushButton("")
        script_layout.addWidget(self.script_clear_btn)

        script_layout.setContentsMargins(*SELECTOR_ROW_MARGINS)
        script_layout.setSpacing(PATH_ENTRY_ROW_SPACING)
        python_layout.addWidget(script_row)
        self.main_layout.addWidget(self.python_title_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)
        self.main_layout.addWidget(python_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)

        # =============================================================
        # Output Folder
        # =============================================================

        output_block = QWidget()
        output_block_layout = QVBoxLayout(output_block)
        output_block_layout.setContentsMargins(3,3,3,3)
        output_block_layout.setSpacing(3)

        # =================================================
        # OUTPUT TITLE FRAME
        # =================================================

        self.output_title_frame = QFrame()
        self.output_title_frame.setFrameShape(QFrame.StyledPanel)
        self.output_title_frame.setFrameShadow(QFrame.Raised)

        output_title_layout = QHBoxLayout(self.output_title_frame)
        output_title_layout.setContentsMargins(3,3,3,3)
        output_title_layout.setSpacing(3)

        self.output_title = QLabel("Output Select")
        self.output_title.setFixedHeight(30)
        self.output_title.setFont(QFont("Rubik UI", 14, QFont.Bold))

        output_title_layout.addStretch()
        output_title_layout.addWidget(self.output_title)
        output_title_layout.addStretch()

        self.output_frame = QFrame()
        self.output_frame.setFrameShape(QFrame.StyledPanel)
        self.output_frame.setFrameShadow(QFrame.Raised)

        output_layout = QVBoxLayout(self.output_frame)
        output_layout.setContentsMargins(3,3,3,3)
        output_layout.setSpacing(3)

        # =================================================
        # Row 1: Select Output Folder button
        # =================================================

        self.output_btn = QPushButton("Output Folder")

        self.date_time_dropdown = QComboBox()
        self.date_time_dropdown.setFixedSize(245, 35)
        self.date_time_dropdown.setFont(QFont("Rubik UI", 12))

        self.appened_py_version = QPushButton("Append Py Version")
        self.appened_py_version.setFixedSize(125,35)
        self.appened_py_version.setCheckable(True)

        self.appened_py_version.setStyleSheet(APPEND_PY_VERSION_INITIAL_STYLE)
                
        self._populate_datetime_dropdown(self.date_time_dropdown)

        row1 = QHBoxLayout()
        row1.setContentsMargins(*SELECTOR_ROW_MARGINS)
        row1.setSpacing(SELECTOR_ROW_SPACING)

        row1.addWidget(self.appened_py_version)
        row1.addStretch()

        row2 = QHBoxLayout()
        row2.setContentsMargins(*SELECTOR_ROW_MARGINS)
        row2.setSpacing(SELECTOR_ROW_SPACING)
        row2.addWidget(self.output_btn)
        row2.addWidget(self.date_time_dropdown)
        row2.addStretch()
    
        output_layout.addLayout(row1)
        output_layout.addLayout(row2)

        # =================================================
        # Row 2: Output path + reset
        # =================================================

        output_entry_row = QWidget()
        output_entry_layout = QHBoxLayout(output_entry_row)
        output_entry_layout.setContentsMargins(*SELECTOR_ROW_MARGINS)
        output_entry_layout.setSpacing(PATH_ENTRY_ROW_SPACING)

        self.output_path_input = PathDisplayLineEdit()
        self.output_path_input.setPlaceholderText("No output path selected.")
        output_entry_layout.addWidget(self.output_path_input)

        self.output_refresh_btn = QPushButton("")
        output_entry_layout.addWidget(self.output_refresh_btn)

        output_layout.addWidget(output_entry_row)
        # =================================================
        # Row 4: EXE name + reset
        # =================================================

        exe_row = QWidget()
        exe_layout = QHBoxLayout(exe_row)
        exe_layout.setContentsMargins(*SELECTOR_ROW_MARGINS)
        exe_layout.setSpacing(PATH_ENTRY_ROW_SPACING)

        self.exe_name_input = QLineEdit()
        self.exe_name_input.setPlaceholderText("Exe has not been named.")
        exe_layout.addWidget(self.exe_name_input)

        self.refresh_btn = QPushButton("")
        exe_layout.addWidget(self.refresh_btn)

        output_layout.addWidget(exe_row)
        self.main_layout.addWidget(self.output_title_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)
        self.main_layout.addWidget(self.output_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)
        
        # =============================================================
        # Build FRAME
        # =============================================================
        
        build_title_frame = QFrame()
        build_title_frame.setFrameShape(QFrame.StyledPanel)
        build_title_frame.setFrameShadow(QFrame.Raised)

        build_title_layout = QHBoxLayout(build_title_frame)
        build_title_layout.setContentsMargins(3,3,3,3)
        build_title_layout.setSpacing(3)

        self.build_title = QLabel("Build Section")
        self.build_title.setFixedHeight(30)
        self.build_title.setFont(QFont("Rubik UI", 14, QFont.Bold))

        build_title_layout.addStretch()
        build_title_layout.addWidget(self.build_title)
        build_title_layout.addStretch()

        build_frame = QFrame()
        build_frame.setFrameShape(QFrame.StyledPanel)
        build_frame.setFrameShadow(QFrame.Raised)
        build_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        build_frame.setObjectName("configurationFrame")
        build_frame.setStyleSheet(MAIN_FRAME_STYLE)

        build_action_edge_padding = 12
        build_layout = QVBoxLayout(build_frame)
        build_layout.setContentsMargins(
            build_action_edge_padding, build_action_edge_padding,
            build_action_edge_padding, build_action_edge_padding,
        )
        build_layout.setSpacing(7)

        self.status_label = QTextEdit("Ready")
        self.status_label.setReadOnly(True)
        self.status_label.setFixedSize(420, 75)
        self.status_label.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.status_label.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.status_label.setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)

        # 🔑 center text
        cursor = self.status_label.textCursor()
        cursor.select(QTextCursor.Document)

        fmt = QTextBlockFormat()
        fmt.setAlignment(Qt.AlignCenter)

        cursor.mergeBlockFormat(fmt)
        self.status_label.setTextCursor(cursor)

        

        self.build_btn = QPushButton("Build EXE")
        self.build_btn.setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.build_btn.setFixedSize(180, 35)
        self.build_btn.clicked.connect(self.build_controller.build_exe)

        self.python_open_output_btn = QPushButton("Open Output Folder")
        self.python_open_output_btn.setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.python_open_output_btn.setFixedSize(180, 35)
        self.python_open_output_btn.clicked.connect(
            self.build_controller.open_python_output_folder
        )

        build_layout.addWidget(self.status_label, alignment=Qt.AlignHCenter)
        build_actions = QHBoxLayout()
        build_actions.addStretch()
        build_actions.addWidget(self.build_btn)
        build_actions.addWidget(self.python_open_output_btn)
        build_actions.addStretch()
        build_layout.addLayout(build_actions)

        output_frame_width = max(
            PAIRED_FRAME_WIDTH,
            self.output_btn.sizeHint().width() + self.date_time_dropdown.width() + 40,
        )
        self.output_frame.setFixedWidth(output_frame_width)
        self.interpreter_frame.setFixedSize(
            output_frame_width, self.interpreter_frame.sizeHint().height()
        )
        build_frame.setFixedWidth(BUILD_ACTION_FRAME_WIDTH)
        build_frame.setFixedHeight(build_frame.sizeHint().height())
        self.env_sync_frame.setFixedWidth(output_frame_width)

        for frame in [
            self.env_sync_frame,
            self.interpreter_frame,
            interpreter_container,
            self.icon_frame,
            python_frame,
            self.output_frame,
        ]:
            frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        for dropdowns in [
            self.date_time_dropdown,
            self.recent_folder_dropdown,
            self.select_recent_icons,
            self.select_interpreter,
        ]:
            dropdowns.setStyleSheet(COMBO_BOX_STYLE)
            if dropdowns.isEditable() and dropdowns.lineEdit():
                dropdowns.lineEdit().setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                dropdowns.lineEdit().setStyleSheet(COMBO_BOX_LINE_EDIT_STYLE)

        frames = [
            self.env_sync_frame,
            self.interpreter_frame,
            self.icon_frame,
            python_frame,
            self.output_frame,
            build_frame,
        ]

        build_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        for frame in frames:
            if frame:
                frame.setObjectName("configurationFrame")
                frame.setStyleSheet(MAIN_FRAME_STYLE)

        frames = [
            self.env_sync_title_frame,
            self.apps_title_frame,
            self.icons_title_frame,
            self.python_title_frame,
            self.output_title_frame,
            build_title_frame,
        ]

        for frame in frames:
            if frame:
                frame.setStyleSheet(TITLE_FRAME_STYLE)

            frame.setFixedSize(100, 35)
            frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            
                
        for label in [
            self.env_sync_title,
            self.apps_title,
            self.icons_title,
            self.python_title,
            self.output_title,
            self.build_title,
        ]:
            label.setAlignment(Qt.AlignVCenter)
                

        # -------------------------------
        # TITLE FRAMES — shrink to content
        # -------------------------------

        title_pairs = [
            (self.env_sync_title_frame, self.env_sync_title),
            (self.apps_title_frame, self.apps_title),
            (self.icons_title_frame, self.icons_title),
            (self.python_title_frame, self.python_title),
            (self.output_title_frame, self.output_title),
            (build_title_frame, self.build_title),
        ]

        for frame, label in title_pairs:
            if frame and label:
                fm = QFontMetrics(label.font())
                text_width = fm.horizontalAdvance(label.text())

                padding = 25 # space for margins + breathing room

                frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                frame.setMaximumHeight(40)
                frame.setFixedWidth(text_width + padding)

        # -------------------------------
        # INPUT DEFAULTS (placeholders + font)
        # -------------------------------

        inputs = [
            (self.exe_name_input, "Exe has not been named."),
            (self.env_sync_log_input, "Environment sync ready."),
            (self.python_entry_input, "No Python interpreter selected."),
            (self.icon_path_input, "No icon selected."),
            (self.output_path_input, "No output folder selected."),
            (self.script_path_input,"No python file has been selected.")
        ]

        font = QFont("Rubik UI", 11)
        font.setBold(True)

        for widget, text in inputs:
            if widget:
                widget.setPlaceholderText(text)
                widget.setFont(font)

        section_output_line_height = self.python_entry_input.two_line_height()
        for widget in [
            self.python_entry_input,
            self.icon_path_input,
            self.script_path_input,
            self.output_path_input,
        ]:
            widget.setFixedHeight(section_output_line_height)
        self.exe_name_input.setFixedHeight(30)

        for cb in [
            self.tooltips_checkbox,
            self.minimize_after_build,
            self.suppress_exit_dialogue,
            self.close_after_build,
        ]:
            cb.setFixedSize(225, 28)
            cb.setChecked(True)
            cb.setFont(QFont("Rubik UI", 13, QFont.Bold))

        self.suppress_exit_dialogue.setChecked(False)

        self.open_output_dir_after_build.setFixedSize(240, 28)
        self.open_output_dir_after_build.setChecked(True)
        self.open_output_dir_after_build.setFont(QFont("Rubik UI", 13, QFont.Bold))

        self.open_output_dir_after_build.setChecked(False)
        self.run_built_app_after_build.setFixedSize(240, 28)
        self.run_built_app_after_build.setFont(QFont("Rubik UI", 13, QFont.Bold))
        self.run_built_app_after_build.setChecked(False)
        self.open_app_data_btn.setFixedSize(225, 28)
        self.open_app_data_btn.setFont(QFont("Rubik UI", 13, QFont.Bold))

        for widget in [
            self.folder_btn,
            self.recent_folder_dropdown,
            self.delete_recent_folder,
            self.delete_all_folders,
        ]:  
            folder_row.addWidget(widget)
            
        folder_row.addStretch()

        for delete_btns in [
            self.delete_recent_icons,
            self.delete_recent_folder,
            self.delete_all_icons,
            self.delete_all_folders,
            self.python_delete_all_interpreter,
            self.python_delete_interpreter,
            
        ]:

            delete_btns.setFixedSize(*UTILITY_ICON_BUTTON_SIZE)
            delete_btns.setEnabled(True)
        
        for refresh_btns in [
            self.refresh_btn,
            self.output_refresh_btn,
            self.icon_clear_btn,
            self.script_clear_btn,
            self.interpreter_refresh_btn,
        ]:
            refresh_btns.setText(REFRESH_BUTTON_TEXT)
            refresh_btns.setIcon(QIcon(str(REFRESH_BUTTON_ICON)))
            refresh_btns.setIconSize(QSize(*REFRESH_BUTTON_ICON_SIZE))
            refresh_btns.setFixedSize(*UTILITY_ICON_BUTTON_SIZE)

        for output_paths in [
            self.env_sync_log_input,
            self.python_entry_input,
            self.script_path_input,
            self.icon_path_input,
            self.output_path_input,
            self.exe_name_input,
        ]:
            output_paths.setReadOnly(True)

        self.exe_name_input.setReadOnly(False)

        buttons = [
            self.env_sync_scan_btn,
            self.env_sync_match_btn,
            self.open_python_site_btn,
            self.appened_py_version,
            self.icon_btn,
            self.ico_convert_btn,
            self.interpreter_btn,
            self.folder_btn,
            self.output_btn,
        ]

        for btn in buttons:
            if btn not in (self.env_sync_scan_btn, self.env_sync_match_btn):
                btn.setFixedSize(160, 35)
            btn.setFont(QFont("Rubik UI", 11, QFont.Bold))
        
        self.recent_folder_dropdown.setFixedSize(*PATH_DROPDOWN_SIZE)

        buttons = [
            self.appened_py_version,
            self.output_btn,
            self.folder_btn,
            self.icon_btn,
            self.ico_convert_btn,
            self.interpreter_btn,
            self.open_python_site_btn,
            self.open_app_data_btn,
        ]

        for btn in buttons:
            btn.setStyleSheet(button_base())

        output_layout.activate()
        self.output_frame.setFixedHeight(self.output_frame.sizeHint().height())
                    
        for widget in [
            self.recent_folder_dropdown,
            self.select_recent_icons,
        ]:
            widget.setAcceptDrops(True)
            widget.installEventFilter(self)

        # Keep the established Python UI together, then add the compact .NET
        # page without forcing C# controls into the PyInstaller workflow.
        self._install_build_mode_pages(root_layout)
        
        build_title_row_layout.addWidget(build_title_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)
        build_frame_row_layout.addWidget(build_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)
        self._install_python_sidebar(python_frame, build_title_frame, build_frame)

        attach_tooltips(self)
        attach_path_hovers(self)
        self._loading_state = False
        self.state_ctrl.load_state()
        self._connect_python_progression()
        self._update_dotnet_selection_summaries()
        self.dotnet_publish_controller.populate_recents("project")
        self.dotnet_publish_controller.populate_recents("icon")
        self.recent_controller.populate_recent_dropdown()
        self.validator.validation_status_message()
        self.json_import_controller.attach()
        self.env_sync_scan_btn.clicked.connect(self.ui_handlers.on_env_sync_scan)
        self.env_sync_match_btn.clicked.connect(self.ui_handlers.on_env_sync_match)
        self.env_sync_help_btn.clicked.connect(self._show_environment_sync_help)
        self.interpreter_btn.clicked.connect(self.file_pickers.select_python_interpreter)
        self.python_delete_interpreter.clicked.connect(self.recent_controller.interpreter_delete)
        self.select_interpreter.currentIndexChanged.connect(self.recent_controller.on_recent_interpreter_selected)
        self.python_delete_all_interpreter.clicked.connect(
            self.recent_controller.all_interpreter_delete
        )

        self.recent_controller.populate_recent_icons_dropdown()
        self.recent_folder_dropdown.currentIndexChanged.connect(self.recent_controller.on_recent_file_selected)
        self.delete_recent_folder.clicked.connect(self.recent_controller.confirm_delete_recent)
        self.delete_all_folders.clicked.connect(self.recent_controller.confirm_delete_all_folder)
        self.ico_convert_btn.clicked.connect(self.ui_handlers.open_icon_sites)

        self.open_python_site_btn.clicked.connect(self.ui_handlers.open_python_site)
        self.select_recent_icons.currentIndexChanged.connect(self.recent_controller.on_recent_icon_selected)
        self.delete_recent_icons.clicked.connect(self.recent_controller.confirm_delete_recent_icon)
        self.delete_all_icons.clicked.connect(self.recent_controller.confirm_delete_all_icons)

        self.date_time_dropdown.currentIndexChanged.connect(self.ui_handlers.on_datetime_format_changed)
        self.appened_py_version.toggled.connect(self.ui_handlers.on_append_py_version_toggle)
        self.recent_controller.populate_recent_interpreters_dropdown()
        self.interpreter_refresh_btn.clicked.connect(self.ui_handlers.clear_interpreter_path)
        self.icon_btn.clicked.connect(self.file_pickers.select_icon)
        self.icon_clear_btn.clicked.connect(self.ui_handlers.clear_icon)
        self.folder_btn.clicked.connect(self.file_pickers.select_script_folder)
        self.script_clear_btn.clicked.connect(self.ui_handlers.clear_script_path)
        self.output_btn.clicked.connect(self.file_pickers.select_output_folder)
        self.output_refresh_btn.clicked.connect(self.ui_handlers.reset_output_to_desktop)
        self.open_app_data_btn.clicked.connect(self.ui_handlers.open_app_data)
        self.build_options_btn.clicked.connect(self._show_build_options)
        self.refresh_btn.clicked.connect(self.ui_handlers.reset_exe_name_from_script)
        self.tooltips_checkbox.stateChanged.connect(self.ui_handlers.on_tooltips_toggle)
        self.exe_name_input.textChanged.connect(self.ui_handlers._on_exe_name_user_edit)
        self.exe_name_input.textChanged.connect(self.ui_handlers.on_exe_name_change)
        self.script_path_input.textChanged.connect(self.ui_handlers.on_script_path_change)
        self.minimize_after_build.stateChanged.connect(self.ui_handlers.on_minimize_toggle)
        self.open_output_dir_after_build.stateChanged.connect(self.ui_handlers.on_open_output_dir_toggle)
        self.run_built_app_after_build.stateChanged.connect(self.ui_handlers.on_run_built_app_toggle)
        self.suppress_exit_dialogue.stateChanged.connect(self.ui_handlers.on_suppress_exit_dialogue_toggle)
        self.close_after_build.stateChanged.connect(self.ui_handlers.on_close_toggle)

        self.validator.update_ui_state()
        self.validation_controller.update_build_button()
        self.dotnet_publish_controller.refresh_ui()
        self.output_folder_monitor = OutputFolderValidityMonitor(self)
        self._start_output_folder_monitor()
        self._sync_paired_section_geometry()
        self._sync_center_divider_height()
        self._sync_dotnet_center_divider_height()

    def _show_build_options(self):
        """Open the compact dialog that contains the build option controls."""
        if not self.building:
            # A mode switch can recreate the native handle; reapply DWM colours.
            apply_build_options_title_bar_style(self.build_options_dialog)
            self.build_options_dialog.exec()

    def _install_python_sidebar(self, python_frame, build_title_frame, build_frame):
        """Place the existing controls on focused pages without recreating them."""
        self.python_section_stack = QStackedWidget()
        self.python_section_nav = QListWidget()
        self.python_section_nav.setObjectName("sectionNavigation")
        self.python_section_nav.setFixedWidth(185)
        self.python_section_nav.setSpacing(2)
        self.python_section_nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.python_section_nav.setStyleSheet(SECTION_NAV_STYLE)
        sections = (
            ("Environment Sync", self.env_sync_title_frame, self.env_sync_frame),
            ("Interpreter", self.apps_title_frame, self.interpreter_frame),
            ("Icons", self.icons_title_frame, self.icon_frame),
            ("File", self.python_title_frame, python_frame),
            ("Output", self.output_title_frame, self.output_frame),
            ("Build", build_title_frame, build_frame),
        )
        self._create_build_summary()
        self.python_selection_summaries = {
            "Icons": self._create_selection_summary(("interpreter",)),
            "File": self._create_selection_summary(("interpreter", "icon")),
            "Output": self._create_selection_summary(("interpreter", "icon", "file")),
        }

        def progression_button(text, callback):
            button = QPushButton(text)
            button.setFixedSize(*PROGRESSION_BUTTON_SIZE)
            button.setFont(QFont("Rubik UI", 12, QFont.Bold))
            button.setStyleSheet(button_base())
            button.clicked.connect(callback)
            return button

        for label, title, controls in sections:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(28, 28, 28, 20)
            layout.setSpacing(16 if label == "Build" else 12)
            if label in self.python_selection_summaries:
                summary_title, summary_frame, _labels, _values = self.python_selection_summaries[label]
                layout.addWidget(summary_title, alignment=Qt.AlignHCenter)
                layout.addWidget(summary_frame, alignment=Qt.AlignHCenter)
            if label == "Build":
                layout.addWidget(self.build_summary_title_frame, alignment=Qt.AlignHCenter)
                layout.addWidget(self.build_summary_frame, alignment=Qt.AlignHCenter)
            layout.addWidget(title, alignment=Qt.AlignHCenter)
            layout.addWidget(controls, alignment=Qt.AlignHCenter)
            if label == "Build":
                saved_setups_section = QWidget()
                saved_setups_section.setFixedWidth(PAIRED_FRAME_WIDTH)
                saved_setups_layout = QVBoxLayout(saved_setups_section)
                saved_setups_layout.setContentsMargins(0, 0, 0, 0)
                saved_setups_layout.setSpacing(16)
                self.saved_setups_label = QLabel("Saved setups")
                self.saved_setups_label.setFont(QFont("Rubik UI", 12, QFont.Bold))
                self.saved_setups_label.setAlignment(Qt.AlignCenter)
                self.saved_setups_label.setStyleSheet(
                    f"QLabel {{ color: {qcolor_name(Colors.TEXT_LIGHT)}; }}"
                )
                saved_setups_layout.addWidget(self.saved_setups_label)
                saved_setups_controls = QHBoxLayout()
                saved_setups_controls.setContentsMargins(0, 0, 0, 0)
                saved_setups_controls.setSpacing(8)
                saved_setups_controls.addWidget(self.save_build_setup_btn)
                saved_setups_controls.addWidget(self.saved_build_setup_dropdown)
                saved_setups_controls.addWidget(self.delete_build_setup_btn)
                saved_setups_layout.addLayout(saved_setups_controls)
                layout.addWidget(saved_setups_section, alignment=Qt.AlignHCenter)
                self.python_saved_setups_backup_section = (
                    self._create_saved_setups_backup_controls("python")
                )
                layout.addWidget(
                    self.python_saved_setups_backup_section,
                    alignment=Qt.AlignHCenter,
                )
            if label == "Environment Sync":
                skip = progression_button(
                    "Continue without syncing", self._continue_to_interpreter
                )
                layout.addWidget(skip, alignment=Qt.AlignHCenter)
            elif label == "Interpreter":
                self.interpreter_continue_btn = progression_button(
                    "Continue to icons", self._continue_to_icons
                )
                layout.addWidget(self.interpreter_continue_btn, alignment=Qt.AlignHCenter)
            elif label == "Icons":
                self.icon_continue_btn = progression_button(
                    "Use no icon and continue", self._continue_from_icons
                )
                layout.addWidget(self.icon_continue_btn, alignment=Qt.AlignHCenter)
            elif label == "File":
                self.file_continue_btn = progression_button(
                    "Continue to output", self._continue_to_output
                )
                layout.addWidget(self.file_continue_btn, alignment=Qt.AlignHCenter)
            elif label == "Output":
                self.output_continue_btn = progression_button(
                    "Continue to build", self._continue_to_build
                )
                layout.addWidget(self.output_continue_btn, alignment=Qt.AlignHCenter)
            layout.addStretch()
            self.python_section_stack.addWidget(page)
            self.python_section_nav.addItem(label)

        # The old grid is now empty. Replace it with a single navigation shell.
        python_layout = self.python_mode_page.layout()
        for widget in (self.content_row,):
            python_layout.removeWidget(widget)
            widget.hide()
        for row_index in (1, 2):
            old_row = python_layout.itemAt(row_index)
            if old_row and old_row.widget():
                old_row.widget().hide()
        self.python_navigation_sidebar = QWidget()
        self.python_navigation_sidebar.setFixedWidth(NAVIGATION_SIDEBAR_WIDTH)
        self.python_navigation_sidebar.setStyleSheet("background: #19232d;")
        sidebar_layout = QVBoxLayout(self.python_navigation_sidebar)
        sidebar_layout.setContentsMargins(10, 8, 10, 8)
        sidebar_layout.setSpacing(4)
        self.python_mode_selector = QWidget()
        python_mode_selector_layout = QHBoxLayout(self.python_mode_selector)
        python_mode_selector_layout.setContentsMargins(0, 0, 0, 0)
        python_mode_selector_layout.setSpacing(2)
        self.python_mode_btn.setText("Python")
        self.dotnet_mode_btn.setText("C# .NET")
        for button in (self.python_mode_btn, self.dotnet_mode_btn):
            button.setFixedHeight(30)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            python_mode_selector_layout.addWidget(button)
        sidebar_layout.addWidget(self.python_mode_selector)
        sidebar_layout.addWidget(self.python_section_nav, 1)

        shell = QWidget()
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        shell_layout.addWidget(self.python_navigation_sidebar)
        shell_layout.addWidget(self.python_section_stack, 1)
        python_layout.insertWidget(1, shell, 1)
        self.python_section_nav.currentRowChanged.connect(self.python_section_stack.setCurrentIndex)
        self.python_section_nav.setCurrentRow(0)
        self._place_build_options_button("python")
        self._update_python_navigation()

    def _create_build_summary(self):
        """Create the live build-input summary shown above the build controls."""
        self.build_summary_title_frame = QFrame()
        self.build_summary_title_frame.setFrameShape(QFrame.StyledPanel)
        self.build_summary_title_frame.setFrameShadow(QFrame.Raised)
        self.build_summary_title_frame.setStyleSheet(TITLE_FRAME_STYLE)
        summary_title_layout = QHBoxLayout(self.build_summary_title_frame)
        summary_title_layout.setContentsMargins(3, 3, 3, 3)
        self.build_summary_title = QLabel("Build Summary")
        self.build_summary_title.setFixedHeight(30)
        self.build_summary_title.setFont(QFont("Rubik UI", 14, QFont.Bold))
        self.build_summary_title.setAlignment(Qt.AlignVCenter)
        summary_title_layout.addStretch()
        summary_title_layout.addWidget(self.build_summary_title)
        summary_title_layout.addStretch()
        self.build_summary_title_frame.setFixedSize(
            QFontMetrics(self.build_summary_title.font()).horizontalAdvance(
                self.build_summary_title.text()
            ) + 25,
            35,
        )

        self.build_summary_frame = QFrame()
        self.build_summary_frame.setObjectName("configurationFrame")
        self.build_summary_frame.setStyleSheet(MAIN_FRAME_STYLE)
        self.build_summary_frame.setFixedWidth(PAIRED_FRAME_WIDTH)
        summary_layout = QVBoxLayout(self.build_summary_frame)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setSpacing(5)

        self.saved_build_setup_dropdown = QComboBox()
        self.saved_build_setup_dropdown.addItem("Saved build setups")
        self.saved_build_setup_dropdown.setAccessibleName("Saved build setups")
        self.saved_build_setup_dropdown.setToolTip(
            "Choose a saved setup to fill the build fields, then click Build EXE."
        )
        self.saved_build_setup_dropdown.setFixedWidth(300)
        self.saved_build_setup_dropdown.setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.saved_build_setup_dropdown.setStyleSheet(SAVED_SETUP_COMBO_BOX_STYLE)
        self.saved_build_setup_dropdown.view().setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.saved_build_setup_dropdown.currentIndexChanged.connect(
            self._load_selected_build_setup
        )
        self.save_build_setup_btn = QPushButton("Save setup")
        self.save_build_setup_btn.setAccessibleName("Save current build setup")
        self.save_build_setup_btn.setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.save_build_setup_btn.setFixedSize(135, 28)
        self.save_build_setup_btn.setStyleSheet(
            button_base()
            + "QPushButton { padding: 2px 12px; }"
            + f"QPushButton:disabled {{ background-color: {qcolor_name(Colors.DISABLED_BG)}; "
              f"color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)}; }}"
        )
        self.save_build_setup_btn.clicked.connect(self._save_current_build_setup)
        self.delete_build_setup_btn = QToolButton()
        self.delete_build_setup_btn.setText("Delete")
        self.delete_build_setup_btn.setAccessibleName("Delete saved build setup")
        self.delete_build_setup_btn.setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.delete_build_setup_btn.setFixedSize(85, 28)
        self.delete_build_setup_btn.setStyleSheet(SAVED_SETUP_DELETE_MENU_STYLE)
        self.delete_build_setup_menu = QMenu(self.delete_build_setup_btn)
        self.delete_build_setup_menu.setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.delete_selected_build_setup_action = self.delete_build_setup_menu.addAction(
            "Delete selected"
        )
        self.delete_all_build_setups_action = self.delete_build_setup_menu.addAction(
            "Delete all"
        )
        self.delete_selected_build_setup_action.triggered.connect(
            self._delete_selected_build_setup
        )
        self.delete_all_build_setups_action.triggered.connect(
            self._delete_all_saved_build_setups
        )
        self.delete_build_setup_btn.setMenu(self.delete_build_setup_menu)
        self.delete_build_setup_btn.setPopupMode(QToolButton.MenuButtonPopup)
        self.delete_build_setup_btn.clicked.connect(self._delete_selected_build_setup)

        self.build_summary_labels = {}
        self.build_summary_values = {}
        for key, label_text in (
            ("interpreter", "Interpreter"),
            ("icon", "Icon"),
            ("file", "File"),
            ("output", "Output"),
            ("name", "EXE name"),
        ):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            label = QLabel(label_text)
            label.setFont(QFont("Rubik UI", 10, QFont.Bold))
            label.setFixedWidth(85)
            value = QLabel()
            value.setFont(QFont("Rubik UI", 10, QFont.Bold))
            value.setFixedHeight(QFontMetrics(value.font()).lineSpacing() * 2 + 2)
            value.setWordWrap(True)
            value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value.setTextInteractionFlags(Qt.NoTextInteraction)
            value.setFocusPolicy(Qt.NoFocus)
            value.setToolTip("")
            text_color = Colors.TEXT_LIGHT if key == "icon" else Colors.SUCCESS
            label.setStyleSheet(f"QLabel {{ color: {qcolor_name(text_color)}; }}")
            value.setStyleSheet(
                f"QLabel {{ color: {qcolor_name(text_color)}; font-weight: bold; "
                f"background-color: {qcolor_name(Colors.DISABLED_BG)}; "
                f"border: 1px solid {qcolor_name(Colors.BORDER_DARK)}; padding: 0 4px; }}"
            )
            row.addWidget(label)
            row.addWidget(value, 1)
            summary_layout.addLayout(row)
            self.build_summary_labels[key] = label
            self.build_summary_values[key] = value

    @staticmethod
    def _summary_display_text(text):
        """Add invisible wrap points at path separators without changing the data."""
        return text.replace("\\", "\\\u200b").replace("/", "/\u200b")

    def _update_build_summary(self):
        if not hasattr(self, "build_summary_values"):
            return
        self._invalidate_saved_setup_backup_status("python")
        values = {
            "interpreter": self.python_entry_input.text() or "Not selected",
            "icon": self.icon_path_input.text() or "(No icon needed to build)",
            "file": self.script_path_input.text() or "Not selected",
            "output": self.output_path_input.text() or "Not selected",
            "name": self.exe_name_input.text().strip() or "Not named",
        }
        for key, text in values.items():
            widget = self.build_summary_values[key]
            widget.setText(self._summary_display_text(text))
            widget.setToolTip(text)
            if key == "icon":
                text_color = Colors.SUCCESS if self.icon_path_input.text() else Colors.TEXT_LIGHT
                self.build_summary_labels[key].setStyleSheet(
                    f"QLabel {{ color: {qcolor_name(text_color)}; }}"
                )
                widget.setStyleSheet(
                    f"QLabel {{ color: {qcolor_name(text_color)}; font-weight: bold; "
                    f"background-color: {qcolor_name(Colors.DISABLED_BG)}; "
                    f"border: 1px solid {qcolor_name(Colors.BORDER_DARK)}; padding: 0 4px; }}"
                )
        self._update_saved_build_setup_controls()

    def _current_build_setup(self):
        return {
            "interpreter": self.python_entry_input.text().strip(),
            "icon": self.icon_path_input.text().strip(),
            "script": self.script_path_input.text().strip(),
            "output": self.output_path_input.text().strip(),
            "name": self.exe_name_input.text().strip(),
            "datetime_format": self.date_time_dropdown.currentData(),
            "append_py_version": self.appened_py_version.isChecked(),
        }

    @staticmethod
    def _build_setup_is_available(setup):
        return (
            isinstance(setup, dict)
            and all(isinstance(setup.get(key), str) for key in
                    ("interpreter", "icon", "script", "output", "name"))
            and bool(setup["name"].strip())
            and os.path.isfile(setup["interpreter"])
            and os.path.isfile(setup["script"])
            and os.path.isdir(setup["output"])
            and (not setup["icon"] or os.path.isfile(setup["icon"]))
        )

    def _populate_saved_build_setups(self):
        dropdown = self.saved_build_setup_dropdown
        previous = dropdown.blockSignals(True)
        try:
            dropdown.clear()
            dropdown.addItem("Saved build setups")
            placeholder = dropdown.model().item(0)
            if placeholder is not None:
                placeholder.setEnabled(False)
            for index, setup in enumerate(self.saved_build_setups):
                if not isinstance(setup, dict):
                    continue
                name = str(setup.get("name", "Unnamed"))
                output = os.path.normpath(str(setup.get("output", "")))
                folder = os.path.basename(output)
                parent = os.path.basename(os.path.dirname(output))
                label = " / ".join(part for part in (parent, folder, name) if part)
                dropdown.addItem(label, index)
                dropdown.setItemData(dropdown.count() - 1, "\n".join(
                    str(setup.get(key, "")) for key in
                    ("interpreter", "script", "output", "icon")
                ), Qt.ToolTipRole)
            dropdown.setCurrentIndex(0)
        finally:
            dropdown.blockSignals(previous)
        self._update_saved_build_setup_controls()

    def _update_saved_build_setup_controls(self):
        if not hasattr(self, "save_build_setup_btn"):
            return
        busy = self.building or self.environment_sync_controller.is_running
        current_setup = self._current_build_setup()
        self._sync_saved_build_setup_selection(current_setup)
        self.save_build_setup_btn.setEnabled(
            not busy
            and self._build_setup_is_available(current_setup)
            and current_setup not in self.saved_build_setups
        )
        self.saved_build_setup_dropdown.setEnabled(
            not busy and self.saved_build_setup_dropdown.count() > 1
        )
        has_saved_setups = self.saved_build_setup_dropdown.count() > 1
        self.delete_build_setup_btn.setEnabled(not busy and has_saved_setups)
        self.delete_selected_build_setup_action.setEnabled(
            not busy and self.saved_build_setup_dropdown.currentIndex() > 0
        )
        self.delete_all_build_setups_action.setEnabled(not busy and has_saved_setups)
        for name in ("export_python_build_setups_btn", "import_python_build_setups_btn"):
            button = getattr(self, name, None)
            if button is not None:
                button.setEnabled(not busy)

    def _sync_saved_build_setup_selection(self, current_setup):
        """Reflect the configuration currently displayed in the build summary."""
        dropdown = self.saved_build_setup_dropdown
        matching_index = 0
        for dropdown_index in range(1, dropdown.count()):
            setup_index = dropdown.itemData(dropdown_index)
            if (isinstance(setup_index, int)
                    and 0 <= setup_index < len(self.saved_build_setups)
                    and self.saved_build_setups[setup_index] == current_setup):
                matching_index = dropdown_index
                break
        if dropdown.currentIndex() != matching_index:
            previous = dropdown.blockSignals(True)
            dropdown.setCurrentIndex(matching_index)
            dropdown.blockSignals(previous)

    def _create_saved_setups_backup_controls(self, mode):
        """Create portable saved-setup import and export controls for a mode."""
        section = QWidget()
        section.setFixedWidth(PAIRED_FRAME_WIDTH)
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        label = QLabel("Setups backup")
        label.setFont(QFont("Rubik UI", 12, QFont.Bold))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"QLabel {{ color: {qcolor_name(Colors.TEXT_LIGHT)}; }}")
        layout.addWidget(label)
        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        controls.addStretch()
        export_btn = QPushButton("Export setups")
        import_btn = QPushButton("Import setups")
        for button in (export_btn, import_btn):
            button.setFixedSize(160, 28)
            button.setFont(QFont("Rubik UI", 12, QFont.Bold))
            button.setStyleSheet(button_base() + "QPushButton { padding: 2px 12px; }")
            controls.addWidget(button)
        controls.addStretch()
        export_btn.clicked.connect(lambda: self._export_saved_build_setups(mode))
        import_btn.clicked.connect(lambda: self._import_saved_build_setups(mode))
        layout.addLayout(controls)
        setattr(self, f"export_{mode}_build_setups_btn", export_btn)
        setattr(self, f"import_{mode}_build_setups_btn", import_btn)
        return section

    @staticmethod
    def _portable_saved_setup_is_valid(mode, setup):
        if not isinstance(setup, dict):
            return False
        if mode == "python":
            return (
                all(isinstance(setup.get(key), str) for key in
                    ("interpreter", "icon", "script", "output", "name"))
                and isinstance(setup.get("append_py_version"), bool)
                and (setup.get("datetime_format") is None
                     or isinstance(setup.get("datetime_format"), str))
            )
        option_keys = ("self_contained", "single_file", "trim")
        return (
            all(isinstance(setup.get(key), str) for key in
                ("project", "output", "icon", "name", "runtime"))
            and all(isinstance(setup.get(key), bool) for key in option_keys)
            and sum(setup[key] for key in option_keys) == 1
            and (setup.get("datetime_format") is None
                 or isinstance(setup.get("datetime_format"), str))
        )

    def _saved_setup_collection(self, mode):
        if mode == "python":
            return self.saved_build_setups
        return self.saved_dotnet_build_setups

    def _replace_saved_setup_collection(self, mode, setups):
        if mode == "python":
            self.saved_build_setups = setups
            self._populate_saved_build_setups()
            self.state_ctrl.save_python_state()
        else:
            self.saved_dotnet_build_setups = setups
            self._populate_saved_dotnet_build_setups()
            self.state_ctrl.save_csharp_state()

    def _invalidate_saved_setup_backup_status(self, mode):
        self._saved_setup_backup_status_tokens[mode] += 1

    def _set_saved_setup_backup_status(self, mode, message, color):
        self._invalidate_saved_setup_backup_status(mode)
        if mode == "python":
            self.status_label.setText(message)
            self.status_label.setAlignment(Qt.AlignCenter)
            self.status_label.setStyleSheet(status_text_style(color))
        else:
            self.dotnet_publish_controller._set_status(message)
            self.dotnet_status_label.setStyleSheet(status_text_style(color))

    def _restore_saved_setup_backup_status(self, mode, message, token):
        """Restore normal status only if this import result is still current."""
        if (self._saved_setup_backup_status_tokens[mode] != token or self.building):
            return
        label = self.status_label if mode == "python" else self.dotnet_status_label
        current_text = label.toPlainText() if hasattr(label, "toPlainText") else label.text()
        if current_text != message:
            return
        if mode == "python":
            self.validator.update_ui_state()
        else:
            self.dotnet_publish_controller.refresh_ui()

    def _schedule_saved_setup_backup_status_reset(self, mode, message, delay_ms=3000):
        token = self._saved_setup_backup_status_tokens[mode]
        QTimer.singleShot(
            delay_ms,
            lambda: self._restore_saved_setup_backup_status(mode, message, token),
        )

    def _export_saved_build_setups(self, mode):
        title = "Export Python Saved Setups" if mode == "python" else "Export C# Saved Setups"
        default_name = f"{mode}_exe_builder_saved_setups.json"
        path, _ = QFileDialog.getSaveFileName(
            self, title, os.path.join(os.path.expanduser("~"), default_name),
            "JSON Files (*.json)",
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        setups = [
            setup for setup in self._saved_setup_collection(mode)
            if self._portable_saved_setup_is_valid(mode, setup)
        ]
        payload = {
            "format": "win11-exe-builder-saved-setups",
            "version": 1,
            "builder": mode,
            "saved_setups": setups,
        }
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=4)
        except OSError as exc:
            self._set_saved_setup_backup_status(
                mode, f"Could not export saved setups: {exc}", Colors.ERROR
            )
            return
        self._set_saved_setup_backup_status(
            mode, f"Exported {len(setups)} saved setup{'s' if len(setups) != 1 else ''}.",
            Colors.SUCCESS,
        )

    def _import_saved_build_setups(self, mode):
        title = "Import Python Saved Setups" if mode == "python" else "Import C# Saved Setups"
        path, _ = QFileDialog.getOpenFileName(self, title, "", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self._set_saved_setup_backup_status(
                mode, f"Could not import saved setups: {exc}", Colors.ERROR
            )
            return
        if not isinstance(payload, dict) or payload.get("format") != "win11-exe-builder-saved-setups":
            self._set_saved_setup_backup_status(
                mode, "That file is not a saved-setups backup.", Colors.ERROR
            )
            return
        if payload.get("version") != 1 or payload.get("builder") != mode:
            message = "That backup is for a different builder."
            self._set_saved_setup_backup_status(mode, message, Colors.ERROR)
            self._schedule_saved_setup_backup_status_reset(mode, message, 5000)
            return
        imported = payload.get("saved_setups")
        if not isinstance(imported, list):
            self._set_saved_setup_backup_status(
                mode, "That backup has no valid saved setups.", Colors.ERROR
            )
            return
        imported = [
            setup for setup in imported
            if self._portable_saved_setup_is_valid(mode, setup)
        ]
        existing = [
            setup for setup in self._saved_setup_collection(mode)
            if self._portable_saved_setup_is_valid(mode, setup)
        ]
        merged = []
        for setup in [*imported, *existing]:
            if setup not in merged:
                merged.append(setup)
        added = sum(1 for setup in imported if setup not in existing)
        self._replace_saved_setup_collection(mode, merged[:50])
        if not added:
            message = "Imported 0 saved setups — no new valid setups were found."
            self._set_saved_setup_backup_status(mode, message, Colors.ERROR)
            self._schedule_saved_setup_backup_status_reset(mode, message, 5000)
            return
        message = f"Imported {added} saved setup{'s' if added != 1 else ''}."
        self._set_saved_setup_backup_status(mode, message, Colors.SUCCESS)
        self._schedule_saved_setup_backup_status_reset(mode, message)

    def _create_dotnet_saved_build_setup_controls(self):
        """Create the C# counterpart of the Python saved-setups controls."""
        self.dotnet_saved_setups_section = QWidget()
        self.dotnet_saved_setups_section.setFixedWidth(PAIRED_FRAME_WIDTH)
        layout = QVBoxLayout(self.dotnet_saved_setups_section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.dotnet_saved_setups_label = QLabel("Saved setups")
        self.dotnet_saved_setups_label.setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.dotnet_saved_setups_label.setAlignment(Qt.AlignCenter)
        self.dotnet_saved_setups_label.setStyleSheet(
            f"QLabel {{ color: {qcolor_name(Colors.TEXT_LIGHT)}; }}"
        )
        layout.addWidget(self.dotnet_saved_setups_label)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        self.dotnet_save_build_setup_btn = QPushButton("Save setup")
        self.dotnet_save_build_setup_btn.setAccessibleName("Save current C# build setup")
        self.dotnet_save_build_setup_btn.setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.dotnet_save_build_setup_btn.setFixedSize(135, 28)
        self.dotnet_save_build_setup_btn.setStyleSheet(
            button_base()
            + "QPushButton { padding: 2px 12px; }"
            + f"QPushButton:disabled {{ background-color: {qcolor_name(Colors.DISABLED_BG)}; "
              f"color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)}; }}"
        )
        self.dotnet_save_build_setup_btn.clicked.connect(self._save_current_dotnet_build_setup)

        self.saved_dotnet_build_setup_dropdown = QComboBox()
        self.saved_dotnet_build_setup_dropdown.addItem("Saved build setups")
        self.saved_dotnet_build_setup_dropdown.setAccessibleName("Saved C# build setups")
        self.saved_dotnet_build_setup_dropdown.setToolTip(
            "Choose a saved setup to fill the publish fields, then click Publish."
        )
        self.saved_dotnet_build_setup_dropdown.setFixedWidth(300)
        self.saved_dotnet_build_setup_dropdown.setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.saved_dotnet_build_setup_dropdown.setStyleSheet(SAVED_SETUP_COMBO_BOX_STYLE)
        self.saved_dotnet_build_setup_dropdown.view().setFont(
            QFont("Rubik UI", 12, QFont.Bold)
        )
        self.saved_dotnet_build_setup_dropdown.currentIndexChanged.connect(
            self._load_selected_dotnet_build_setup
        )

        self.dotnet_delete_build_setup_btn = QToolButton()
        self.dotnet_delete_build_setup_btn.setText("Delete")
        self.dotnet_delete_build_setup_btn.setAccessibleName("Delete saved C# build setup")
        self.dotnet_delete_build_setup_btn.setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.dotnet_delete_build_setup_btn.setFixedSize(85, 28)
        self.dotnet_delete_build_setup_btn.setStyleSheet(SAVED_SETUP_DELETE_MENU_STYLE)
        self.dotnet_delete_build_setup_menu = QMenu(self.dotnet_delete_build_setup_btn)
        self.dotnet_delete_build_setup_menu.setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.dotnet_delete_selected_build_setup_action = (
            self.dotnet_delete_build_setup_menu.addAction("Delete selected")
        )
        self.dotnet_delete_all_build_setups_action = (
            self.dotnet_delete_build_setup_menu.addAction("Delete all")
        )
        self.dotnet_delete_selected_build_setup_action.triggered.connect(
            self._delete_selected_dotnet_build_setup
        )
        self.dotnet_delete_all_build_setups_action.triggered.connect(
            self._delete_all_saved_dotnet_build_setups
        )
        self.dotnet_delete_build_setup_btn.setMenu(self.dotnet_delete_build_setup_menu)
        self.dotnet_delete_build_setup_btn.setPopupMode(QToolButton.MenuButtonPopup)
        self.dotnet_delete_build_setup_btn.clicked.connect(
            self._delete_selected_dotnet_build_setup
        )

        controls.addWidget(self.dotnet_save_build_setup_btn)
        controls.addWidget(self.saved_dotnet_build_setup_dropdown)
        controls.addWidget(self.dotnet_delete_build_setup_btn)
        layout.addLayout(controls)
        self._update_saved_dotnet_build_setup_controls()

    def _create_dotnet_build_summary(self):
        """Create the C# build recap with the Python builder's presentation."""
        self.dotnet_build_summary_title_frame = QFrame()
        self.dotnet_build_summary_title_frame.setFrameShape(QFrame.StyledPanel)
        self.dotnet_build_summary_title_frame.setFrameShadow(QFrame.Raised)
        self.dotnet_build_summary_title_frame.setStyleSheet(TITLE_FRAME_STYLE)
        title_layout = QHBoxLayout(self.dotnet_build_summary_title_frame)
        title_layout.setContentsMargins(3, 3, 3, 3)
        self.dotnet_build_summary_title = QLabel("Build Summary")
        self.dotnet_build_summary_title.setFixedHeight(30)
        self.dotnet_build_summary_title.setFont(QFont("Rubik UI", 14, QFont.Bold))
        self.dotnet_build_summary_title.setAlignment(Qt.AlignVCenter)
        title_layout.addStretch()
        title_layout.addWidget(self.dotnet_build_summary_title)
        title_layout.addStretch()
        self.dotnet_build_summary_title_frame.setFixedSize(
            QFontMetrics(self.dotnet_build_summary_title.font()).horizontalAdvance(
                self.dotnet_build_summary_title.text()
            ) + 25,
            35,
        )

        self.dotnet_build_summary_frame = QFrame()
        self.dotnet_build_summary_frame.setObjectName("configurationFrame")
        self.dotnet_build_summary_frame.setStyleSheet(MAIN_FRAME_STYLE)
        self.dotnet_build_summary_frame.setFixedWidth(PAIRED_FRAME_WIDTH)
        summary_layout = QVBoxLayout(self.dotnet_build_summary_frame)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setSpacing(5)
        self.dotnet_build_summary_labels = {}
        self.dotnet_build_summary_values = {}
        for key, label_text in (
            ("project", "Project"),
            ("icon", "Icon"),
            ("output", "Output"),
            ("name", "EXE name"),
            ("runtime", "Runtime"),
        ):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            label = QLabel(label_text)
            label.setFont(QFont("Rubik UI", 10, QFont.Bold))
            label.setFixedWidth(85)
            value = QLabel()
            value.setFont(QFont("Rubik UI", 10, QFont.Bold))
            value.setFixedHeight(QFontMetrics(value.font()).lineSpacing() * 2 + 2)
            value.setWordWrap(True)
            value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value.setTextInteractionFlags(Qt.NoTextInteraction)
            value.setFocusPolicy(Qt.NoFocus)
            row.addWidget(label)
            row.addWidget(value, 1)
            summary_layout.addLayout(row)
            self.dotnet_build_summary_labels[key] = label
            self.dotnet_build_summary_values[key] = value
        self._update_dotnet_build_summary()

    def _update_dotnet_build_summary(self):
        if not hasattr(self, "dotnet_build_summary_values"):
            return
        values = {
            "project": self.dotnet_project_input.text() or "Not selected",
            "icon": self.dotnet_icon_input.text() or "(No icon needed to publish)",
            "output": self.dotnet_output_input.text() or "Not selected",
            "name": self.dotnet_name_input.text().strip() or "Not named",
            "runtime": self.dotnet_runtime_combo.currentText() or "Not selected",
        }
        for key, text in values.items():
            is_optional_icon = key == "icon" and not self.dotnet_icon_input.text()
            color = Colors.TEXT_LIGHT if is_optional_icon else Colors.SUCCESS
            self.dotnet_build_summary_labels[key].setStyleSheet(
                f"QLabel {{ color: {qcolor_name(color)}; }}"
            )
            widget = self.dotnet_build_summary_values[key]
            widget.setStyleSheet(
                f"QLabel {{ color: {qcolor_name(color)}; font-weight: bold; "
                f"background-color: {qcolor_name(Colors.DISABLED_BG)}; "
                f"border: 1px solid {qcolor_name(Colors.BORDER_DARK)}; padding: 0 4px; }}"
            )
            widget.setText(self._summary_display_text(text))
            widget.setToolTip(text)

    def _current_dotnet_build_setup(self):
        values = self.dotnet_publish_controller.values()
        return {
            **values,
            "datetime_format": self.dotnet_publish_controller.selected_datetime_format(),
        }

    def _dotnet_build_setup_is_available(self, setup):
        required_strings = ("project", "output", "icon", "name", "runtime")
        option_keys = ("self_contained", "single_file", "trim")
        if not isinstance(setup, dict) or not all(
            isinstance(setup.get(key), str) for key in required_strings
        ):
            return False
        if setup.get("datetime_format") is not None and not isinstance(
            setup.get("datetime_format"), str
        ):
            return False
        if not all(isinstance(setup.get(key), bool) for key in option_keys):
            return False
        if sum(setup[key] for key in option_keys) != 1:
            return False

        original_setup = self._current_dotnet_build_setup()
        fields = (
            self.dotnet_project_input,
            self.dotnet_output_input,
            self.dotnet_icon_input,
            self.dotnet_name_input,
            self.dotnet_runtime_combo,
            self.dotnet_date_time_dropdown,
            self.dotnet_self_contained,
            self.dotnet_single_file,
            self.dotnet_trim,
        )
        previous = [(field, field.blockSignals(True)) for field in fields]
        try:
            self.dotnet_project_input.set_display_path(setup["project"])
            self.dotnet_output_input.set_display_path(setup["output"])
            self.dotnet_icon_input.set_display_path(setup["icon"])
            self.dotnet_name_input.setText(setup["name"])
            runtime_index = self.dotnet_runtime_combo.findData(setup["runtime"])
            datetime_index = (
                self.dotnet_date_time_dropdown.findText(NO_DATETIME_LABEL)
                if setup["datetime_format"] is None
                else self.dotnet_date_time_dropdown.findData(setup["datetime_format"])
            )
            if runtime_index < 0 or datetime_index < 0:
                return False
            self.dotnet_runtime_combo.setCurrentIndex(runtime_index)
            self.dotnet_date_time_dropdown.setCurrentIndex(datetime_index)
            for key, checkbox in zip(option_keys, fields[-3:]):
                checkbox.setChecked(setup[key])
            return not self.dotnet_publish_controller.validation_error()
        finally:
            self._restore_dotnet_build_setup_fields(original_setup)
            for field, blocked in previous:
                field.blockSignals(blocked)

    def _restore_dotnet_build_setup_fields(self, setup):
        """Restore setup values after temporary validation or saved-setup loading."""
        self.dotnet_project_input.set_display_path(setup["project"])
        self.dotnet_output_input.set_display_path(setup["output"])
        self.dotnet_icon_input.set_display_path(setup["icon"])
        self.dotnet_name_input.setText(setup["name"])
        self.dotnet_runtime_combo.setCurrentIndex(
            self.dotnet_runtime_combo.findData(setup["runtime"])
        )
        datetime_index = (
            self.dotnet_date_time_dropdown.findText(NO_DATETIME_LABEL)
            if setup["datetime_format"] is None
            else self.dotnet_date_time_dropdown.findData(setup["datetime_format"])
        )
        self.dotnet_date_time_dropdown.setCurrentIndex(datetime_index)
        for key, checkbox in (
            ("self_contained", self.dotnet_self_contained),
            ("single_file", self.dotnet_single_file),
            ("trim", self.dotnet_trim),
        ):
            checkbox.setChecked(setup[key])

    def _populate_saved_dotnet_build_setups(self):
        dropdown = self.saved_dotnet_build_setup_dropdown
        previous = dropdown.blockSignals(True)
        try:
            dropdown.clear()
            dropdown.addItem("Saved build setups")
            placeholder = dropdown.model().item(0)
            if placeholder is not None:
                placeholder.setEnabled(False)
            for index, setup in enumerate(self.saved_dotnet_build_setups):
                if not isinstance(setup, dict):
                    continue
                output = os.path.normpath(str(setup.get("output", "")))
                label = " / ".join(part for part in (
                    os.path.basename(os.path.dirname(output)),
                    os.path.basename(output),
                    str(setup.get("name", "Unnamed")),
                ) if part)
                dropdown.addItem(label, index)
                dropdown.setItemData(dropdown.count() - 1, "\n".join(
                    str(setup.get(key, "")) for key in ("project", "output", "icon")
                ), Qt.ToolTipRole)
            dropdown.setCurrentIndex(0)
        finally:
            dropdown.blockSignals(previous)
        self._update_saved_dotnet_build_setup_controls()

    def _update_saved_dotnet_build_setup_controls(self):
        if not hasattr(self, "dotnet_save_build_setup_btn"):
            return
        current_setup = self._current_dotnet_build_setup()
        self._sync_saved_dotnet_build_setup_selection(current_setup)
        self.dotnet_save_build_setup_btn.setEnabled(
            not self.building
            and self._dotnet_build_setup_is_available(current_setup)
            and current_setup not in self.saved_dotnet_build_setups
        )
        self.saved_dotnet_build_setup_dropdown.setEnabled(
            not self.building and self.saved_dotnet_build_setup_dropdown.count() > 1
        )
        has_saved_setups = self.saved_dotnet_build_setup_dropdown.count() > 1
        self.dotnet_delete_build_setup_btn.setEnabled(
            not self.building and has_saved_setups
        )
        self.dotnet_delete_selected_build_setup_action.setEnabled(
            not self.building
            and self.saved_dotnet_build_setup_dropdown.currentIndex() > 0
        )
        self.dotnet_delete_all_build_setups_action.setEnabled(
            not self.building and has_saved_setups
        )
        for name in ("export_dotnet_build_setups_btn", "import_dotnet_build_setups_btn"):
            button = getattr(self, name, None)
            if button is not None:
                button.setEnabled(not self.building)

    def _sync_saved_dotnet_build_setup_selection(self, current_setup):
        """Reflect the configuration currently displayed in the C# build summary."""
        dropdown = self.saved_dotnet_build_setup_dropdown
        matching_index = 0
        for dropdown_index in range(1, dropdown.count()):
            setup_index = dropdown.itemData(dropdown_index)
            if (isinstance(setup_index, int)
                    and 0 <= setup_index < len(self.saved_dotnet_build_setups)
                    and self.saved_dotnet_build_setups[setup_index] == current_setup):
                matching_index = dropdown_index
                break
        if dropdown.currentIndex() != matching_index:
            previous = dropdown.blockSignals(True)
            dropdown.setCurrentIndex(matching_index)
            dropdown.blockSignals(previous)

    def _save_current_dotnet_build_setup(self):
        setup = self._current_dotnet_build_setup()
        if (self.building or not self._dotnet_build_setup_is_available(setup)
                or setup in self.saved_dotnet_build_setups):
            return
        self.saved_dotnet_build_setups = [
            setup, *(item for item in self.saved_dotnet_build_setups if item != setup)
        ][:50]
        self._populate_saved_dotnet_build_setups()
        self.state_ctrl.save_csharp_state()

    def _load_selected_dotnet_build_setup(self, index):
        if index <= 0 or self.building:
            self._update_saved_dotnet_build_setup_controls()
            return
        setup_index = self.saved_dotnet_build_setup_dropdown.itemData(index)
        if not isinstance(setup_index, int) or setup_index >= len(self.saved_dotnet_build_setups):
            return
        setup = self.saved_dotnet_build_setups[setup_index]
        if not self._dotnet_build_setup_is_available(setup):
            self.dotnet_publish_controller._set_status(
                "Saved setup has a missing file or output folder."
            )
            self._update_saved_dotnet_build_setup_controls()
            return

        fields = (
            self.dotnet_project_input,
            self.dotnet_output_input,
            self.dotnet_icon_input,
            self.dotnet_name_input,
            self.dotnet_runtime_combo,
            self.dotnet_date_time_dropdown,
            self.dotnet_self_contained,
            self.dotnet_single_file,
            self.dotnet_trim,
        )
        previous_loading = self._loading_state
        self._loading_state = True
        previous = [(field, field.blockSignals(True)) for field in fields]
        try:
            self._restore_dotnet_build_setup_fields(setup)
            selected = next(
                checkbox for key, checkbox in (
                    ("self_contained", self.dotnet_self_contained),
                    ("single_file", self.dotnet_single_file),
                    ("trim", self.dotnet_trim),
                ) if setup[key]
            )
            self._sync_dotnet_publish_options(selected)
        finally:
            for field, blocked in previous:
                field.blockSignals(blocked)
            self._loading_state = previous_loading
        self.restore_dotnet_guided_workflow(range(3))
        self._on_dotnet_settings_changed()
        self.state_ctrl.save_csharp_state()

    def _delete_selected_dotnet_build_setup(self):
        index = self.saved_dotnet_build_setup_dropdown.currentIndex()
        if index <= 0 or self.building:
            return
        setup_index = self.saved_dotnet_build_setup_dropdown.itemData(index)
        if not isinstance(setup_index, int) or setup_index >= len(self.saved_dotnet_build_setups):
            return
        if not self._confirm_delete_saved_dotnet_build_setup(
            self.saved_dotnet_build_setup_dropdown.itemText(index)
        ):
            return
        del self.saved_dotnet_build_setups[setup_index]
        self._populate_saved_dotnet_build_setups()
        self.state_ctrl.save_csharp_state()

    def _delete_all_saved_dotnet_build_setups(self):
        if self.building or not self.saved_dotnet_build_setups:
            return
        if not self._confirm_delete_all_saved_dotnet_build_setups():
            return
        self.saved_dotnet_build_setups = []
        self._populate_saved_dotnet_build_setups()
        self.state_ctrl.save_csharp_state()

    def _confirm_delete_saved_dotnet_build_setup(self, setup_name):
        return self._confirm_delete_saved_build_setup(setup_name)

    def _confirm_delete_all_saved_dotnet_build_setups(self):
        return self._confirm_delete_all_saved_build_setups()

    def _save_current_build_setup(self):
        setup = self._current_build_setup()
        if (self.building or self.environment_sync_controller.is_running
                or not self._build_setup_is_available(setup)
                or setup in self.saved_build_setups):
            return
        self.saved_build_setups = [
            setup, *(item for item in self.saved_build_setups if item != setup)
        ][:50]
        self._populate_saved_build_setups()
        self.state_ctrl.save_python_state()

    def _load_selected_build_setup(self, index):
        if index <= 0 or self.building or self.environment_sync_controller.is_running:
            self._update_saved_build_setup_controls()
            return
        setup_index = self.saved_build_setup_dropdown.itemData(index)
        if not isinstance(setup_index, int) or setup_index >= len(self.saved_build_setups):
            return
        setup = self.saved_build_setups[setup_index]
        if not self._build_setup_is_available(setup):
            self.status_label.setText("Saved setup has a missing file or output folder.")
            self._update_saved_build_setup_controls()
            return

        fields = (
            (self.python_entry_input, setup["interpreter"]),
            (self.icon_path_input, setup["icon"]),
            (self.script_path_input, setup["script"]),
            (self.output_path_input, setup["output"]),
            (self.exe_name_input, setup["name"]),
        )
        widgets = [field for field, _value in fields]
        widgets.extend((self.date_time_dropdown, self.appened_py_version))
        previous_loading = self._loading_state
        self._loading_state = True
        previous_states = [(widget, widget.blockSignals(True)) for widget in widgets]
        try:
            for field, value in fields:
                if field is self.exe_name_input:
                    field.setText(value)
                else:
                    field.set_display_path(value)
            self.python_interpreter_path = self.python_path = setup["interpreter"]
            self.icon_path = setup["icon"]
            self.script_path = self.entry_script = setup["script"]
            self.project_root = os.path.dirname(setup["script"])
            self.output_path = setup["output"]
            self.exe_name = setup["name"]
            self.interpreter_user_cleared = self.icon_user_cleared = False
            self.script_user_cleared = self.exe_name_user_modified = False
            self.datetime_format = setup.get("datetime_format")
            self.append_py_version = bool(setup.get("append_py_version", False))
            self.appened_py_version.setChecked(self.append_py_version)
            datetime_index = (
                self.date_time_dropdown.findText(NO_DATETIME_LABEL)
                if self.datetime_format is None
                else self.date_time_dropdown.findData(self.datetime_format)
            )
            if datetime_index < 0:
                datetime_index = self.date_time_dropdown.findText(NO_DATETIME_LABEL)
            self.date_time_dropdown.setCurrentIndex(datetime_index)
            self.datetime_format = self.date_time_dropdown.currentData()
            self.mass_datetime_build_selected = self.datetime_format in {
                MASS_DATETIME_BUILD_SENTINEL,
                ISO_MASS_DATETIME_BUILD_SENTINEL,
                UK_MASS_DATETIME_BUILD_SENTINEL,
                USA_MASS_DATETIME_BUILD_SENTINEL,
            }
            self.append_datetime = bool(
                self.datetime_format and not self.mass_datetime_build_selected
            )
        finally:
            for widget, previous_state in previous_states:
                widget.blockSignals(previous_state)
            self._loading_state = previous_loading
        self.restore_python_guided_workflow(range(5))
        self._update_icon_continue_button()
        self.validator.validation_status_message()
        self.validator.update_ui_state()
        self.state_ctrl.save_python_state()
        self._update_saved_build_setup_controls()

    def _delete_selected_build_setup(self):
        index = self.saved_build_setup_dropdown.currentIndex()
        if index <= 0 or self.building or self.environment_sync_controller.is_running:
            return
        setup_index = self.saved_build_setup_dropdown.itemData(index)
        if not isinstance(setup_index, int) or setup_index >= len(self.saved_build_setups):
            return
        if not self._confirm_delete_saved_build_setup(
            self.saved_build_setup_dropdown.itemText(index)
        ):
            return
        del self.saved_build_setups[setup_index]
        self._populate_saved_build_setups()
        self.state_ctrl.save_python_state()

    def _delete_all_saved_build_setups(self):
        if self.building or self.environment_sync_controller.is_running or not self.saved_build_setups:
            return
        if not self._confirm_delete_all_saved_build_setups():
            return
        self.saved_build_setups = []
        self._populate_saved_build_setups()
        self.state_ctrl.save_python_state()

    def _confirm_delete_saved_build_setup(self, setup_name):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Delete Saved Setup")
        dialog.setText(f"Delete this saved setup?\n\n{setup_name}")
        dialog.setIcon(QMessageBox.NoIcon)
        yes_button = dialog.addButton("Yes", QMessageBox.AcceptRole)
        cancel_button = dialog.addButton("Cancel", QMessageBox.RejectRole)
        dialog.setDefaultButton(cancel_button)
        dialog.setEscapeButton(cancel_button)
        dialog.setStyleSheet(CONFIRMATION_MESSAGE_BOX_STYLE)
        dialog.setWindowFlags(
            (dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            | Qt.MSWindowsFixedSizeDialogHint
        )
        button_box = dialog.findChild(QDialogButtonBox)
        if button_box is not None:
            button_box.setCenterButtons(True)
        apply_native_title_bar_style(
            dialog,
            caption=Colors.PANEL_BG,
            border=Colors.PANEL_BG,
        )
        dialog.exec()
        return dialog.clickedButton() == yes_button

    def _confirm_delete_all_saved_build_setups(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Delete All Saved Setups")
        dialog.setText("Delete all saved setups?")
        dialog.setIcon(QMessageBox.NoIcon)
        yes_button = dialog.addButton("Yes", QMessageBox.AcceptRole)
        cancel_button = dialog.addButton("Cancel", QMessageBox.RejectRole)
        dialog.setDefaultButton(cancel_button)
        dialog.setEscapeButton(cancel_button)
        dialog.setStyleSheet(CONFIRMATION_MESSAGE_BOX_STYLE)
        dialog.setWindowFlags(
            (dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            | Qt.MSWindowsFixedSizeDialogHint
        )
        button_box = dialog.findChild(QDialogButtonBox)
        if button_box is not None:
            button_box.setCenterButtons(True)
        apply_native_title_bar_style(
            dialog,
            caption=Colors.PANEL_BG,
            border=Colors.PANEL_BG,
        )
        dialog.exec()
        return dialog.clickedButton() == yes_button

    def _create_selection_summary(self, keys):
        """Create a compact, read-only recap for selections on earlier pages."""
        title_frame = QFrame()
        title_frame.setFrameShape(QFrame.StyledPanel)
        title_frame.setFrameShadow(QFrame.Raised)
        title_frame.setStyleSheet(TITLE_FRAME_STYLE)
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(3, 3, 3, 3)
        title = QLabel("Selection Summary")
        title.setFixedHeight(30)
        title.setFont(QFont("Rubik UI", 14, QFont.Bold))
        title_layout.addStretch()
        title_layout.addWidget(title)
        title_layout.addStretch()
        title_frame.setFixedSize(
            QFontMetrics(title.font()).horizontalAdvance(title.text()) + 25, 35
        )

        frame = QFrame()
        frame.setObjectName("configurationFrame")
        frame.setStyleSheet(MAIN_FRAME_STYLE)
        frame.setFixedWidth(PAIRED_FRAME_WIDTH)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)
        labels = {}
        values = {}
        captions = {"interpreter": "Interpreter", "icon": "Icon", "file": "File"}
        for key in keys:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            label = QLabel(captions[key])
            label.setFont(QFont("Rubik UI", 10, QFont.Bold))
            label.setFixedWidth(85)
            value = QLabel()
            value.setFont(QFont("Rubik UI", 10, QFont.Bold))
            value.setFixedHeight(QFontMetrics(value.font()).lineSpacing() * 2 + 2)
            value.setWordWrap(True)
            value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value.setTextInteractionFlags(Qt.NoTextInteraction)
            value.setFocusPolicy(Qt.NoFocus)
            row.addWidget(label)
            row.addWidget(value, 1)
            layout.addLayout(row)
            labels[key] = label
            values[key] = value
        return title_frame, frame, labels, values

    def _update_selection_summaries(self, summaries, selections):
        for _title, _frame, labels, values in summaries.values():
            for key, value in values.items():
                path = selections[key].strip()
                display = path or ("No icon" if key == "icon" else "Not selected")
                color = Colors.SUCCESS if path else Colors.TEXT_LIGHT
                label = labels[key]
                label.setStyleSheet(f"QLabel {{ color: {qcolor_name(color)}; }}")
                value.setStyleSheet(
                    f"QLabel {{ color: {qcolor_name(color)}; font-weight: bold; "
                    f"background-color: {qcolor_name(Colors.DISABLED_BG)}; "
                    f"border: 1px solid {qcolor_name(Colors.BORDER_DARK)}; padding: 0 4px; }}"
                )
                value.setText(self._summary_display_text(display))
                value.setToolTip(display)

    def _update_python_selection_summaries(self):
        self._update_selection_summaries(self.python_selection_summaries, {
            "interpreter": self.python_entry_input.text(),
            "icon": self.icon_path_input.text(),
            "file": self.script_path_input.text(),
        })

    def _update_dotnet_selection_summaries(self):
        self._update_selection_summaries(self.dotnet_selection_summaries, {
            "icon": self.dotnet_icon_input.text(),
            "file": self.dotnet_project_input.text(),
        })

    def _connect_python_progression(self):
        for field in (
            self.python_entry_input,
            self.script_path_input,
            self.output_path_input,
            self.exe_name_input,
        ):
            field.textChanged.connect(self._update_python_navigation)
        self.icon_path_input.textChanged.connect(self._update_icon_continue_button)
        self._update_icon_continue_button()
        self._update_python_navigation()

    def _update_icon_continue_button(self, *_args):
        """Describe the current icon choice before the user advances."""
        if hasattr(self, "icon_continue_btn"):
            self.icon_continue_btn.setText(
                "Continue to file" if self.icon_path_input.text() else "Use no icon and continue"
            )
        self._update_python_navigation()

    def _update_python_progression_controls(self, *_args):
        """Only offer a continuation after the selection needed for it exists."""
        if not hasattr(self, "interpreter_continue_btn"):
            return
        self.interpreter_continue_btn.setVisible(
            bool(self.python_entry_input.text())
        )
        # Choosing no icon is itself a valid choice, so this control remains
        # available whenever the Icons tab can be reached.
        self.icon_continue_btn.setVisible(True)
        self.file_continue_btn.setVisible(
            bool(self.script_path_input.text())
        )
        self.output_continue_btn.setVisible(
            bool(self.output_path_input.text() and self.exe_name_input.text().strip())
        )

    def _continue_from_icons(self):
        """Keep a selected icon, or clear it, then always show File next."""
        if not self.icon_path_input.text():
            self.ui_handlers.clear_icon()
        self._complete_python_step(2)
        if self.guided_flow_enabled and self.build_mode == "python":
            self.python_section_nav.setCurrentRow(3)

    def _continue_to_output(self):
        if not self.script_path_input.text() or getattr(self, "_loading_state", False):
            return
        self._complete_python_step(3)
        if self.guided_flow_enabled and self.build_mode == "python":
            self.python_section_nav.setCurrentRow(4)

    def _continue_to_build(self):
        if (not self.output_path_input.text() or not self.exe_name_input.text().strip()
                or getattr(self, "_loading_state", False)):
            return
        self._complete_python_step(4)
        if self.guided_flow_enabled and self.build_mode == "python":
            self.python_section_nav.setCurrentRow(5)

    def _continue_to_interpreter(self):
        """Mark sync as skipped and always show the interpreter step next."""
        self._complete_python_step(0)
        if self.guided_flow_enabled and self.build_mode == "python":
            self.python_section_nav.setCurrentRow(1)

    def _continue_to_icons(self):
        """Complete the interpreter step and always show the icon step next."""
        if not self.python_entry_input.text() or getattr(self, "_loading_state", False):
            return
        self._complete_python_step(1)
        if self.guided_flow_enabled and self.build_mode == "python":
            self.python_section_nav.setCurrentRow(2)

    def _complete_python_step(self, index):
        self._completed_python_steps.add(index)
        next_index = index + 1
        self._update_python_navigation()
        if not self._loading_state:
            self.state_ctrl.save_python_state()
        if self.guided_flow_enabled and self.build_mode == "python":
            if self.python_section_nav.currentRow() == index:
                self.python_section_nav.setCurrentRow(min(next_index, 5))

    def restore_python_guided_workflow(self, saved_steps=()):
        """Restore a valid saved Python workflow without trapping it at Sync."""
        if not hasattr(self, "python_section_nav"):
            return

        python_path = getattr(self, "python_interpreter_path", "").strip()
        script_path = getattr(self, "script_path", "").strip()
        output_path = getattr(self, "output_path", "").strip()
        icon_path = getattr(self, "icon_path", "").strip()
        exe_name = self.exe_name_input.text().strip()
        is_file = lambda path: bool(path and os.path.isfile(os.path.normpath(path)))
        is_directory = lambda path: bool(path and os.path.isdir(os.path.normpath(path)))

        # Saved selections mean Environment Sync has already been intentionally
        # bypassed or completed. Revalidate every required path before opening Build.
        has_saved_selection = bool(python_path or script_path or output_path or exe_name)
        completed = {int(step) for step in saved_steps if isinstance(step, int) and 0 <= step <= 4}
        if has_saved_selection:
            completed.add(0)
        if is_file(python_path):
            completed.add(1)
        else:
            completed.discard(1)
        if not icon_path or is_file(icon_path):
            completed.add(2)
        else:
            completed.discard(2)
        if is_file(script_path):
            completed.add(3)
        else:
            completed.discard(3)
        if is_directory(output_path) and exe_name:
            completed.add(4)
        else:
            completed.discard(4)

        self._completed_python_steps = completed
        self._update_python_navigation()
        if self.guided_flow_enabled:
            if all(step in completed for step in range(5)):
                self.python_section_nav.setCurrentRow(5)
            elif 0 not in completed:
                self.python_section_nav.setCurrentRow(0)
            elif 1 not in completed:
                self.python_section_nav.setCurrentRow(1)
            elif 2 not in completed:
                self.python_section_nav.setCurrentRow(2)
            elif 3 not in completed:
                self.python_section_nav.setCurrentRow(3)
            else:
                self.python_section_nav.setCurrentRow(4)

    def _update_python_navigation(self):
        if not hasattr(self, "python_section_nav"):
            return
        if not self.guided_flow_enabled:
            reachable = 5
        elif 0 not in self._completed_python_steps:
            reachable = 0
        elif not self.python_entry_input.text():
            reachable = 1
        elif not (self.icon_path_input.text() or 2 in self._completed_python_steps):
            reachable = 2
        elif not self.script_path_input.text():
            reachable = 3
        elif not (self.output_path_input.text() and self.exe_name_input.text().strip()):
            reachable = 4
        else:
            reachable = 5
        for index in range(self.python_section_nav.count()):
            item = self.python_section_nav.item(index)
            item.setFlags(
                item.flags() | Qt.ItemIsEnabled if index <= reachable
                else item.flags() & ~Qt.ItemIsEnabled
            )
        if self.guided_flow_enabled and self.python_section_nav.currentRow() > reachable:
            self.python_section_nav.setCurrentRow(reachable)
        self._update_python_progression_controls()
        self._update_build_summary()
        self._update_python_selection_summaries()

    def _dotnet_project_is_valid(self):
        """Return whether the selected C# project can advance the workflow."""
        project = self.dotnet_project_input.text().strip()
        return bool(
            project
            and project.lower().endswith(".csproj")
            and os.path.isfile(project)
            and is_sdk_style_project(project)
        )

    def _dotnet_output_is_ready(self):
        """Return whether the output step has all entries required to continue."""
        output = self.dotnet_output_input.text().strip()
        return bool(
            output
            and os.path.isdir(output)
            and not validate_executable_name(self.dotnet_name_input.text())
        )

    def _update_dotnet_progression_controls(self):
        if not hasattr(self, "dotnet_icon_continue_btn"):
            return
        self.dotnet_icon_continue_btn.setText(
            "Continue to file"
            if self.dotnet_icon_input.text().strip()
            else "Use no icon and continue"
        )
        self.dotnet_icon_continue_btn.setVisible(True)
        self.dotnet_file_continue_btn.setVisible(self._dotnet_project_is_valid())
        self.dotnet_output_continue_btn.setVisible(self._dotnet_output_is_ready())

    def _update_dotnet_navigation(self):
        """Enable C# sidebar pages only after their prior step is complete."""
        if not hasattr(self, "dotnet_section_nav"):
            return
        if 0 not in self._completed_dotnet_steps:
            reachable = 0
        elif not self._dotnet_project_is_valid() or 1 not in self._completed_dotnet_steps:
            reachable = 1
        elif not self._dotnet_output_is_ready() or 2 not in self._completed_dotnet_steps:
            reachable = 2
        else:
            reachable = 3
        for index in range(self.dotnet_section_nav.count()):
            item = self.dotnet_section_nav.item(index)
            item.setFlags(
                item.flags() | Qt.ItemIsEnabled if index <= reachable
                else item.flags() & ~Qt.ItemIsEnabled
            )
        if self.dotnet_section_nav.currentRow() > reachable:
            self.dotnet_section_nav.setCurrentRow(reachable)
        self._update_dotnet_progression_controls()

    def _complete_dotnet_step(self, index):
        self._completed_dotnet_steps.add(index)
        self._update_dotnet_navigation()
        if not getattr(self, "_loading_state", False):
            self.state_ctrl.save_csharp_state()

    def _continue_from_dotnet_icons(self):
        self._complete_dotnet_step(0)
        if self.build_mode == "dotnet":
            self.dotnet_section_nav.setCurrentRow(1)

    def _continue_to_dotnet_output(self):
        if not self._dotnet_project_is_valid() or getattr(self, "_loading_state", False):
            return
        self._complete_dotnet_step(1)
        if self.build_mode == "dotnet":
            self.dotnet_section_nav.setCurrentRow(2)

    def _continue_to_dotnet_build(self):
        if not self._dotnet_output_is_ready() or getattr(self, "_loading_state", False):
            return
        self._complete_dotnet_step(2)
        if self.build_mode == "dotnet":
            self.dotnet_section_nav.setCurrentRow(3)

    def restore_dotnet_guided_workflow(self, saved_steps=()):
        """Restore the furthest valid C# step from saved selections."""
        if not hasattr(self, "dotnet_section_nav"):
            return
        completed = {
            int(step) for step in saved_steps
            if isinstance(step, int) and 0 <= step <= 2
        }
        if self._dotnet_project_is_valid():
            completed.update((0, 1))
        else:
            completed.discard(1)
            completed.discard(2)
        if self._dotnet_project_is_valid() and self._dotnet_output_is_ready():
            completed.add(2)
        else:
            completed.discard(2)
        self._completed_dotnet_steps = completed
        self._update_dotnet_navigation()
        if all(step in completed for step in range(3)):
            self.dotnet_section_nav.setCurrentRow(3)

    def _update_section_navigation_enabled(self):
        """Keep sidebar tabs locked while either build mode is running."""
        for name in ("python_section_nav", "dotnet_section_nav"):
            navigation = getattr(self, name, None)
            if navigation is not None:
                navigation.setEnabled(not self.building)
        self._update_saved_build_setup_controls()

    def _install_build_mode_pages(self, root_layout):
        """Move the legacy screen into a Python page and create the .NET page."""
        self.python_mode_page = QWidget()
        python_layout = QVBoxLayout(self.python_mode_page)
        python_layout.setContentsMargins(0, 0, 0, 0)
        python_layout.setSpacing(0)
        while root_layout.count():
            item = root_layout.takeAt(0)
            if item.widget() is not None:
                python_layout.addWidget(item.widget())

        self.dotnet_mode_page = QWidget()
        dotnet_layout = QVBoxLayout(self.dotnet_mode_page)
        # The two build-mode pages share a single vertical rhythm.  The
        # Python page has no outer inset or inter-row gap, so keep the C#
        # title, divider, build heading, and build panel on those same lines.
        dotnet_layout.setContentsMargins(0, 0, 0, 0)
        dotnet_layout.setSpacing(0)
        self.dotnet_mode_title = QLabel("Win 11 →  C# .NET → EXE Publish")
        self.dotnet_mode_title.setFont(QFont("Rubik UI", 18, QFont.Bold))
        self.dotnet_mode_title.setFixedHeight(34)
        self.dotnet_mode_title.setAlignment(Qt.AlignCenter)
        self.dotnet_mode_title.setStyleSheet(
            f"QLabel {{ color: {qcolor_name(Colors.TEXT_LIGHT)}; }}"
        )
        self.dotnet_title_container = QWidget()
        self.dotnet_title_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.dotnet_title_container.setFixedHeight(44)
        self.dotnet_title_container.setFixedWidth(
            QFontMetrics(self.dotnet_mode_title.font()).horizontalAdvance(
                self.dotnet_mode_title.text()
            ) + 25
        )
        dotnet_title_layout = QHBoxLayout(self.dotnet_title_container)
        dotnet_title_layout.setContentsMargins(5, 5, 5, 5)
        dotnet_title_layout.addStretch()
        dotnet_title_layout.addWidget(self.dotnet_mode_title)
        dotnet_title_layout.addStretch()
        dotnet_header = QWidget()
        dotnet_header.setFixedSize(APP_FIXED_WIDTH, 44)
        dotnet_header_layout = QHBoxLayout(dotnet_header)
        dotnet_header_layout.setContentsMargins(0, 0, 0, 0)
        dotnet_header_layout.setSpacing(0)
        self.dotnet_title_navigation_header = QWidget()
        self.dotnet_title_navigation_header.setFixedWidth(NAVIGATION_SIDEBAR_WIDTH)
        dotnet_title_navigation_layout = QHBoxLayout(
            self.dotnet_title_navigation_header
        )
        dotnet_title_navigation_layout.setContentsMargins(5, 0, 0, 0)
        dotnet_title_navigation_layout.setSpacing(0)
        self.dotnet_title_options_slot = QWidget()
        self.dotnet_title_options_slot.setFixedSize(34, 34)
        self.dotnet_title_options_layout = QHBoxLayout(self.dotnet_title_options_slot)
        self.dotnet_title_options_layout.setContentsMargins(0, 0, 0, 0)
        dotnet_title_navigation_layout.addWidget(
            self.dotnet_title_options_slot, alignment=Qt.AlignLeft | Qt.AlignVCenter
        )
        self.dotnet_title_content_header = QWidget()
        self.dotnet_title_content_header.setFixedWidth(CONTENT_PANE_WIDTH)
        self.dotnet_title_container.setParent(self.dotnet_title_content_header)
        dotnet_header_layout.addWidget(self.dotnet_title_navigation_header)
        dotnet_header_layout.addWidget(self.dotnet_title_content_header)
        self.dotnet_section_title_frames = []
        self.dotnet_configuration_frames = []
        self.dotnet_sections = []
        dotnet_layout.addWidget(dotnet_header)

        # Keep the C# workflow on the same fixed two-column grid as the
        # Python workflow.  This makes both pages share the exact divider,
        # column width, and section rhythm rather than merely looking similar.
        self.dotnet_content_row = QWidget()
        self.dotnet_content_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        dotnet_content_row_layout = QHBoxLayout(self.dotnet_content_row)
        dotnet_content_row_layout.setContentsMargins(0, 0, 0, 0)
        dotnet_content_row_layout.setSpacing(0)
        self.dotnet_left_content, left_column = self._create_content_column()
        self.dotnet_right_content, right_column = self._create_content_column()
        self.dotnet_center_divider = QFrame()
        self.dotnet_center_divider.setObjectName("centerDivider")
        self.dotnet_center_divider.setFrameShape(QFrame.NoFrame)
        self.dotnet_center_divider.setFixedWidth(2)
        self.dotnet_center_divider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.dotnet_center_divider.setStyleSheet(CENTER_DIVIDER_STYLE)
        dotnet_content_row_layout.addWidget(self.dotnet_left_content, alignment=Qt.AlignTop)
        dotnet_content_row_layout.addWidget(self.dotnet_center_divider, alignment=Qt.AlignBottom)
        dotnet_content_row_layout.addWidget(self.dotnet_right_content, alignment=Qt.AlignTop)
        dotnet_layout.addWidget(self.dotnet_content_row)

        # Match the Python workflow: the build controls live in their own
        # centered section below the two-column selection grid.
        self.dotnet_build_title_row = QWidget()
        self.dotnet_build_title_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        dotnet_build_title_row_layout = QHBoxLayout(self.dotnet_build_title_row)
        dotnet_build_title_row_layout.setContentsMargins(0, 0, 0, 0)
        dotnet_build_title_row_layout.setSpacing(0)

        self.dotnet_build_frame_row = QWidget()
        self.dotnet_build_frame_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        dotnet_build_frame_row_layout = QHBoxLayout(self.dotnet_build_frame_row)
        dotnet_build_frame_row_layout.setContentsMargins(0, 0, 0, 0)
        dotnet_build_frame_row_layout.setSpacing(0)

        self.dotnet_build_options_row = QWidget()
        self.dotnet_build_options_row.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.Fixed
        )
        dotnet_build_options_row_layout = QHBoxLayout(self.dotnet_build_options_row)
        dotnet_build_options_row_layout.setContentsMargins(0, 0, 0, 0)
        dotnet_build_options_row_layout.setSpacing(0)

        self.dotnet_build_title_frame = QFrame()
        self.dotnet_build_title_frame.setFrameShape(QFrame.StyledPanel)
        self.dotnet_build_title_frame.setFrameShadow(QFrame.Raised)
        self.dotnet_build_title_frame.setStyleSheet(TITLE_FRAME_STYLE)
        self.dotnet_section_title_frames.append(self.dotnet_build_title_frame)
        dotnet_build_title_layout = QHBoxLayout(self.dotnet_build_title_frame)
        dotnet_build_title_layout.setContentsMargins(3, 3, 3, 3)
        dotnet_build_title_layout.setSpacing(3)
        self.dotnet_build_title = QLabel("Build Section")
        self.dotnet_build_title.setFixedHeight(30)
        self.dotnet_build_title.setFont(QFont("Rubik UI", 14, QFont.Bold))
        self.dotnet_build_title.setAlignment(Qt.AlignVCenter)
        dotnet_build_title_layout.addStretch()
        dotnet_build_title_layout.addWidget(self.dotnet_build_title)
        dotnet_build_title_layout.addStretch()
        self.dotnet_build_title_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.dotnet_build_title_frame.setMaximumHeight(40)
        self.dotnet_build_title_frame.setFixedWidth(
            QFontMetrics(self.dotnet_build_title.font()).horizontalAdvance(
                self.dotnet_build_title.text()
            ) + 25
        )
        dotnet_build_title_row_layout.addWidget(
            self.dotnet_build_title_frame, alignment=Qt.AlignHCenter | Qt.AlignTop
        )
        dotnet_layout.addWidget(self.dotnet_build_title_row)

        def section(title, column):
            heading = QFrame()
            heading.setStyleSheet(TITLE_FRAME_STYLE)
            self.dotnet_section_title_frames.append(heading)
            heading_layout = QHBoxLayout(heading)
            heading_layout.setContentsMargins(3, 3, 3, 3)
            label = QLabel(title)
            label.setFixedHeight(30)
            label.setFont(QFont("Rubik UI", 14, QFont.Bold))
            heading_layout.addStretch()
            heading_layout.addWidget(label)
            heading_layout.addStretch()
            frame = QFrame()
            frame.setObjectName("configurationFrame")
            frame.setStyleSheet(MAIN_FRAME_STYLE)
            self.dotnet_configuration_frames.append(frame)
            frame.setFixedWidth(PAIRED_FRAME_WIDTH)
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(3, 3, 3, 3)
            layout.setSpacing(3)
            column.addWidget(heading, alignment=Qt.AlignHCenter)
            column.addWidget(frame, alignment=Qt.AlignHCenter)
            self.dotnet_sections.append((title, heading, frame))
            return layout

        def utility_button(icon_path, icon_size, caption):
            button = QPushButton(caption)
            button.setIcon(QIcon(str(icon_path)))
            button.setIconSize(QSize(*icon_size))
            button.setFixedSize(*UTILITY_ICON_BUTTON_SIZE)
            button.setStyleSheet(utility_icon_button_style())
            return button

        def path_section(kind, title, column, select_text, placeholder):
            layout = section(title, column)
            if kind == "icon":
                converter_row = QHBoxLayout()
                self.dotnet_ico_convert_btn = QPushButton("Open ICO Convert")
                self.dotnet_ico_convert_btn.setFixedSize(160, 35)
                self.dotnet_ico_convert_btn.setFont(QFont("Rubik UI", 11, QFont.Bold))
                self.dotnet_ico_convert_btn.setStyleSheet(button_base())
                self.dotnet_ico_convert_btn.clicked.connect(self.ui_handlers.open_icon_sites)
                converter_row.addWidget(self.dotnet_ico_convert_btn)
                converter_row.addStretch()
                layout.addLayout(converter_row)
            row = QHBoxLayout()
            row.setContentsMargins(*SELECTOR_ROW_MARGINS)
            row.setSpacing(SELECTOR_ROW_SPACING)
            select = QPushButton(select_text)
            select.setFixedSize(160, 35)
            select.setFont(QFont("Rubik UI", 11, QFont.Bold))
            select.setStyleSheet(button_base())
            recent = QComboBox()
            recent.setFixedSize(*PATH_DROPDOWN_SIZE)
            recent.setFont(QFont("Rubik UI", 12))
            recent.setEditable(True)
            recent.lineEdit().setReadOnly(True)
            recent.setStyleSheet(COMBO_BOX_STYLE)
            delete = utility_button(DELETE_BUTTON_ICON, DELETE_BUTTON_ICON_SIZE, DELETE_BUTTON_TEXT)
            delete_all = utility_button(DELETE_ALL_BUTTON_ICON, DELETE_ALL_BUTTON_ICON_SIZE, DELETE_ALL_BUTTON_TEXT)
            for widget in (select, recent, delete, delete_all):
                row.addWidget(widget)
            row.addStretch()
            layout.addLayout(row)
            entry = QHBoxLayout()
            entry.setContentsMargins(*SELECTOR_ROW_MARGINS)
            entry.setSpacing(PATH_ENTRY_ROW_SPACING)
            field = PathDisplayLineEdit()
            field.setPlaceholderText(placeholder)
            field.setFixedHeight(field.two_line_height())
            reset = utility_button(REFRESH_BUTTON_ICON, REFRESH_BUTTON_ICON_SIZE, REFRESH_BUTTON_TEXT)
            entry.addWidget(field)
            entry.addWidget(reset)
            layout.addLayout(entry)
            prefix = "dotnet_project" if kind == "project" else "dotnet_icon"
            setattr(self, prefix + "_input", field)
            setattr(self, prefix + "_select_btn", select)
            setattr(self, prefix + "_delete_btn", delete)
            setattr(self, prefix + "_delete_all_btn", delete_all)
            setattr(self, prefix + "_reset_btn", reset)
            setattr(self, "dotnet_recent_projects" if kind == "project" else "dotnet_recent_icons", recent)
            select.clicked.connect(self._select_dotnet_project if kind == "project" else self._select_dotnet_icon)
            recent.currentIndexChanged.connect(lambda _index, k=kind: self.dotnet_publish_controller.on_recent_selected(k))
            delete.clicked.connect(lambda _checked=False, k=kind: self.dotnet_publish_controller.delete_recent(k))
            delete_all.clicked.connect(lambda _checked=False, k=kind: self.dotnet_publish_controller.delete_recent(k, True))
            reset.clicked.connect(self.dotnet_publish_controller.clear_project if kind == "project" else self.dotnet_publish_controller.clear_icon)

        path_section("icon", "Icons Select", right_column, "Select ICO optional", "No icon selected.")
        path_section("project", "File Select", right_column, "C# Project File", "No C# project selected.")

        output_layout = section("Output Select", right_column)
        output_select_row = QHBoxLayout()
        output_select_row.setContentsMargins(*SELECTOR_ROW_MARGINS)
        output_select_row.setSpacing(SELECTOR_ROW_SPACING)
        self.dotnet_output_select_btn = QPushButton("Output Folder")
        self.dotnet_output_select_btn.setFixedSize(160, 35)
        self.dotnet_output_select_btn.setFont(QFont("Rubik UI", 11, QFont.Bold))
        self.dotnet_output_select_btn.setStyleSheet(button_base())
        self.dotnet_output_select_btn.clicked.connect(self._select_dotnet_output)
        output_select_row.addWidget(self.dotnet_output_select_btn)
        self.dotnet_date_time_dropdown = QComboBox()
        self.dotnet_date_time_dropdown.setFont(QFont("Rubik UI", 12))
        self.dotnet_date_time_dropdown.setFixedHeight(35)
        self._populate_datetime_dropdown(self.dotnet_date_time_dropdown)
        self.dotnet_date_time_dropdown.setCurrentIndex(
            self.dotnet_date_time_dropdown.findText(NO_DATETIME_LABEL)
        )
        output_select_row.addWidget(self.dotnet_date_time_dropdown)
        output_select_row.addStretch()
        output_layout.addLayout(output_select_row)
        output_entry = QHBoxLayout()
        output_entry.setContentsMargins(*SELECTOR_ROW_MARGINS)
        output_entry.setSpacing(PATH_ENTRY_ROW_SPACING)
        self.dotnet_output_input = PathDisplayLineEdit()
        self.dotnet_output_input.setPlaceholderText("No output folder selected.")
        self.dotnet_output_input.setFixedHeight(
            self.dotnet_output_input.two_line_height()
        )
        self.dotnet_output_reset_btn = utility_button(REFRESH_BUTTON_ICON, REFRESH_BUTTON_ICON_SIZE, REFRESH_BUTTON_TEXT)
        self.dotnet_output_reset_btn.clicked.connect(self.dotnet_publish_controller.reset_output_to_desktop)
        output_entry.addWidget(self.dotnet_output_input)
        output_entry.addWidget(self.dotnet_output_reset_btn)
        output_layout.addLayout(output_entry)
        name_entry = QHBoxLayout()
        name_entry.setContentsMargins(*SELECTOR_ROW_MARGINS)
        name_entry.setSpacing(PATH_ENTRY_ROW_SPACING)
        self.dotnet_name_input = QLineEdit()
        self.dotnet_name_input.setPlaceholderText("Exe has not been named.")
        self.dotnet_name_input.setFixedHeight(30)
        self.dotnet_name_input.setFont(QFont("Rubik UI", 11, QFont.Bold))
        self.dotnet_name_reset_btn = utility_button(REFRESH_BUTTON_ICON, REFRESH_BUTTON_ICON_SIZE, REFRESH_BUTTON_TEXT)
        self.dotnet_name_reset_btn.clicked.connect(self.dotnet_publish_controller.reset_name_from_project)
        name_entry.addWidget(self.dotnet_name_input)
        name_entry.addWidget(self.dotnet_name_reset_btn)
        output_layout.addLayout(name_entry)

        panel = QFrame()
        panel.setObjectName("configurationFrame")
        panel.setStyleSheet(MAIN_FRAME_STYLE)
        self.dotnet_configuration_frames.append(panel)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(7)

        build_options = QWidget()
        build_options.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        build_options_layout = QVBoxLayout(build_options)
        build_options_layout.setContentsMargins(0, 4, 0, 4)
        build_options_layout.setSpacing(3)

        runtime_row = QHBoxLayout()
        self.dotnet_runtime_label = QLabel("Target runtime")
        self.dotnet_runtime_label.setFont(QFont("Rubik UI", 11, QFont.Bold))
        self.dotnet_runtime_label.setMinimumWidth(
            self.dotnet_runtime_label.sizeHint().width()
        )
        runtime_row.addStretch()
        runtime_row.addWidget(self.dotnet_runtime_label)
        self.dotnet_runtime_combo = QComboBox()
        self.dotnet_runtime_combo.addItem("Windows x64", "win-x64")
        self.dotnet_runtime_combo.addItem("Windows ARM64", "win-arm64")
        self.dotnet_runtime_combo.setStyleSheet(COMBO_BOX_STYLE)
        self.dotnet_runtime_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.dotnet_runtime_combo.setMinimumWidth(190)
        runtime_row.addWidget(self.dotnet_runtime_combo)
        runtime_row.addStretch()

        publish_options_row = QHBoxLayout()
        self.dotnet_self_contained = QCheckBox("Self-contained")
        self.dotnet_single_file = QCheckBox("Single file")
        self.dotnet_trim = QCheckBox("Trim")
        for checkbox in (
            self.dotnet_self_contained,
            self.dotnet_single_file,
            self.dotnet_trim,
        ):
            checkbox.setFont(QFont("Rubik UI", 11, QFont.Bold))
            checkbox.setMinimumWidth(checkbox.sizeHint().width())
        self.dotnet_self_contained.setChecked(True)
        publish_options_row.addStretch()
        publish_options_row.addWidget(self.dotnet_self_contained)
        publish_options_row.addWidget(self.dotnet_single_file)
        publish_options_row.addWidget(self.dotnet_trim)
        publish_options_row.addStretch()
        build_options_layout.addLayout(runtime_row)
        build_options_layout.addLayout(publish_options_row)
        dotnet_build_options_row_layout.addWidget(
            build_options, alignment=Qt.AlignHCenter | Qt.AlignTop
        )

        # The bordered build frame contains only build status and actions;
        # publish settings live directly below the Build Section heading.
        panel.setFixedWidth(BUILD_ACTION_FRAME_WIDTH)

        self.dotnet_status_label = QTextEdit("Select a C# project to begin.")
        self.dotnet_status_label.setReadOnly(True)
        self.dotnet_status_label.setFixedSize(420, 75)
        self.dotnet_status_label.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dotnet_status_label.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dotnet_status_label.setFont(QFont("Rubik UI", 12, QFont.Bold))
        self.dotnet_status_label.setAlignment(Qt.AlignCenter)

        dotnet_status_cursor = self.dotnet_status_label.textCursor()
        dotnet_status_cursor.select(QTextCursor.Document)
        dotnet_status_format = QTextBlockFormat()
        dotnet_status_format.setAlignment(Qt.AlignCenter)
        dotnet_status_cursor.mergeBlockFormat(dotnet_status_format)
        dotnet_status_cursor.clearSelection()
        self.dotnet_status_label.setTextCursor(dotnet_status_cursor)

        panel_layout.addWidget(self.dotnet_status_label, alignment=Qt.AlignHCenter)
        actions = QHBoxLayout()
        actions.addStretch()
        self.dotnet_publish_btn = QPushButton("Publish")
        self.dotnet_open_output_btn = QPushButton("Open Output Folder")
        for button in (self.dotnet_publish_btn, self.dotnet_open_output_btn):
            button.setFixedSize(180, 35)
            button.setFont(QFont("Rubik UI", 12, QFont.Bold))
            button.setStyleSheet(button_base())
            actions.addWidget(button)
        actions.addStretch()
        panel_layout.addLayout(actions)
        panel.setFixedHeight(panel.sizeHint().height())
        dotnet_build_frame_row_layout.addWidget(
            panel, alignment=Qt.AlignHCenter | Qt.AlignTop
        )
        self.dotnet_build_controls = QWidget()
        dotnet_build_controls_layout = QVBoxLayout(self.dotnet_build_controls)
        dotnet_build_controls_layout.setContentsMargins(0, 0, 0, 0)
        dotnet_build_controls_layout.setSpacing(16)
        dotnet_build_controls_layout.addWidget(self.dotnet_build_options_row)
        dotnet_build_controls_layout.addWidget(self.dotnet_build_frame_row)
        left_column.addStretch()
        right_column.addStretch()
        self._sync_dotnet_center_divider_height()

        self.build_mode_stack = QStackedWidget()
        self.build_mode_stack.addWidget(self.python_mode_page)
        self.build_mode_stack.addWidget(self.dotnet_mode_page)
        self.python_mode_btn = QPushButton("Python EXE")
        self.dotnet_mode_btn = QPushButton("C# .NET Publish")
        for button in (self.python_mode_btn, self.dotnet_mode_btn):
            button.setCheckable(True)
            button.setFixedHeight(32)
            button.setFont(build_mode_button_font())
            button.setStyleSheet(button_base())
        self.python_mode_btn.setChecked(True)
        self.python_mode_btn.clicked.connect(lambda: self.set_build_mode("python"))
        self.dotnet_mode_btn.clicked.connect(lambda: self.set_build_mode("dotnet"))
        self._apply_build_mode_button_state("python")
        self.dotnet_publish_btn.clicked.connect(self.dotnet_publish_controller.publish)
        self.dotnet_open_output_btn.clicked.connect(self.dotnet_publish_controller.open_output_folder)
        for widget in (
            self.dotnet_project_input, self.dotnet_output_input, self.dotnet_icon_input,
            self.dotnet_name_input,
        ):
            widget.textChanged.connect(self._on_dotnet_settings_changed)
        self.dotnet_runtime_combo.currentIndexChanged.connect(self._on_dotnet_settings_changed)
        self.dotnet_date_time_dropdown.currentIndexChanged.connect(self._on_dotnet_settings_changed)
        for widget in (self.dotnet_self_contained, self.dotnet_single_file, self.dotnet_trim):
            widget.toggled.connect(
                lambda checked, selected=widget: self._on_dotnet_publish_option_toggled(selected, checked)
            )
        self._sync_dotnet_publish_options()
        self._create_dotnet_build_summary()
        self._create_dotnet_saved_build_setup_controls()
        self.dotnet_saved_setups_backup_section = (
            self._create_saved_setups_backup_controls("dotnet")
        )
        self._install_dotnet_sidebar(dotnet_layout, panel)
        root_layout.addWidget(self.build_mode_stack)

    def _install_dotnet_sidebar(self, dotnet_layout, build_panel):
        self.dotnet_section_nav = QListWidget()
        self.dotnet_section_nav.setObjectName("sectionNavigation")
        self.dotnet_section_nav.setFixedWidth(185)
        self.dotnet_section_nav.setSpacing(2)
        self.dotnet_section_nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dotnet_section_nav.setStyleSheet(SECTION_NAV_STYLE)
        self.dotnet_section_stack = QStackedWidget()
        self.dotnet_navigation_sidebar = QWidget()
        self.dotnet_navigation_sidebar.setFixedWidth(NAVIGATION_SIDEBAR_WIDTH)
        self.dotnet_navigation_sidebar.setStyleSheet("background: #19232d;")
        dotnet_sidebar_layout = QVBoxLayout(self.dotnet_navigation_sidebar)
        dotnet_sidebar_layout.setContentsMargins(10, 8, 10, 8)
        dotnet_sidebar_layout.setSpacing(4)
        self.dotnet_python_mode_btn = QPushButton("Python EXE")
        self.dotnet_mode_sidebar_btn = QPushButton("C# .NET Publish")
        for button in (self.dotnet_python_mode_btn, self.dotnet_mode_sidebar_btn):
            button.setCheckable(True)
            button.setFixedHeight(30)
            button.setFont(build_mode_button_font())
        self.dotnet_python_mode_btn.setText("Python")
        self.dotnet_mode_sidebar_btn.setText("C# .NET")
        self.dotnet_python_mode_btn.clicked.connect(lambda: self.set_build_mode("python"))
        self.dotnet_mode_sidebar_btn.clicked.connect(lambda: self.set_build_mode("dotnet"))
        self.dotnet_mode_selector = QWidget()
        dotnet_mode_selector_layout = QHBoxLayout(self.dotnet_mode_selector)
        dotnet_mode_selector_layout.setContentsMargins(0, 0, 0, 0)
        dotnet_mode_selector_layout.setSpacing(2)
        for button in (self.dotnet_python_mode_btn, self.dotnet_mode_sidebar_btn):
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            dotnet_mode_selector_layout.addWidget(button)
        dotnet_sidebar_layout.addWidget(self.dotnet_mode_selector)
        sections = list(self.dotnet_sections)
        sections.append(
            ("Build", self.dotnet_build_title_frame, self.dotnet_build_controls)
        )
        self.dotnet_selection_summaries = {
            "File Select": self._create_selection_summary(("icon",)),
            "Output Select": self._create_selection_summary(("icon", "file")),
        }

        def progression_button(text, callback):
            button = QPushButton(text)
            button.setFixedSize(*PROGRESSION_BUTTON_SIZE)
            button.setFont(QFont("Rubik UI", 12, QFont.Bold))
            button.setStyleSheet(button_base())
            button.clicked.connect(callback)
            return button

        for label, heading, controls in sections:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(28, 28, 28, 20)
            layout.setSpacing(16 if label == "Build" else 12)
            if label in self.dotnet_selection_summaries:
                summary_title, summary_frame, _labels, _values = self.dotnet_selection_summaries[label]
                layout.addWidget(summary_title, alignment=Qt.AlignHCenter)
                layout.addWidget(summary_frame, alignment=Qt.AlignHCenter)
            if label == "Build":
                layout.addWidget(
                    self.dotnet_build_summary_title_frame, alignment=Qt.AlignHCenter
                )
                layout.addWidget(
                    self.dotnet_build_summary_frame, alignment=Qt.AlignHCenter
                )
            layout.addWidget(heading, alignment=Qt.AlignHCenter)
            layout.addWidget(controls, alignment=Qt.AlignHCenter)
            if label == "Build":
                layout.addWidget(
                    self.dotnet_saved_setups_section, alignment=Qt.AlignHCenter
                )
                layout.addWidget(
                    self.dotnet_saved_setups_backup_section,
                    alignment=Qt.AlignHCenter,
                )
            if label == "Icons Select":
                self.dotnet_icon_continue_btn = progression_button(
                    "Use no icon and continue", self._continue_from_dotnet_icons
                )
                layout.addWidget(self.dotnet_icon_continue_btn, alignment=Qt.AlignHCenter)
            elif label == "File Select":
                self.dotnet_file_continue_btn = progression_button(
                    "Continue to output", self._continue_to_dotnet_output
                )
                layout.addWidget(self.dotnet_file_continue_btn, alignment=Qt.AlignHCenter)
            elif label == "Output Select":
                self.dotnet_output_continue_btn = progression_button(
                    "Continue to build", self._continue_to_dotnet_build
                )
                layout.addWidget(self.dotnet_output_continue_btn, alignment=Qt.AlignHCenter)
            layout.addStretch()
            self.dotnet_section_stack.addWidget(page)
            self.dotnet_section_nav.addItem(label.replace(" Select", ""))
        for row in (self.dotnet_content_row, self.dotnet_build_title_row):
            dotnet_layout.removeWidget(row)
            row.hide()
        shell = QWidget()
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        dotnet_sidebar_layout.addWidget(self.dotnet_section_nav, 1)
        shell_layout.addWidget(self.dotnet_navigation_sidebar)
        shell_layout.addWidget(self.dotnet_section_stack, 1)
        dotnet_layout.addWidget(shell, 1)
        self.dotnet_section_nav.currentRowChanged.connect(self.dotnet_section_stack.setCurrentIndex)
        self.dotnet_section_nav.setCurrentRow(0)
        self._apply_build_mode_button_state(self.build_mode)
        self._update_dotnet_navigation()

    @staticmethod
    def _populate_datetime_dropdown(dropdown):
        dropdown.clear()

        def add(label, data=None, enabled=True):
            dropdown.addItem(label, data)
            if not enabled:
                item = dropdown.model().item(dropdown.count() - 1)
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)

        add("Append Date/Time", enabled=False)
        add("──────────", enabled=False)
        add(NO_DATETIME_LABEL)
        add("──────────", enabled=False)
        add(MASS_DATETIME_BUILD_LABEL, MASS_DATETIME_BUILD_SENTINEL)
        for region_label, build_all_label, build_all_data, format_options in REGIONAL_DATETIME_DROPDOWN_GROUPS:
            add("──────────", enabled=False)
            add(region_label, enabled=False)
            for label, data in format_options:
                add(label, data)
            add(build_all_label, build_all_data)

        metrics = QFontMetrics(dropdown.font())
        longest_label = max(
            MASS_DATETIME_BUILD_LABEL,
            ISO_MASS_DATETIME_BUILD_LABEL,
            UK_MASS_DATETIME_BUILD_LABEL,
            USA_MASS_DATETIME_BUILD_LABEL,
            key=len,
        )
        dropdown.setFixedSize(max(300, metrics.horizontalAdvance(longest_label) + 64), 35)
        dropdown.setEditable(True)
        line_edit = dropdown.lineEdit()
        line_edit.setReadOnly(True)
        dropdown.setStyleSheet(COMBO_BOX_STYLE)
        line_edit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        line_edit.setStyleSheet(COMBO_BOX_LINE_EDIT_STYLE)
        dropdown.setCurrentIndex(0)

    def _apply_build_mode_button_state(self, mode):
        """Refresh build-mode selectors for the displayed mode and build state."""
        building = getattr(self, "building", False)
        apply_build_mode_button_state(
            self.python_mode_btn,
            self.dotnet_mode_btn,
            mode,
            building,
        )
        if hasattr(self, "dotnet_python_mode_btn"):
            apply_build_mode_button_state(
                self.dotnet_python_mode_btn,
                self.dotnet_mode_sidebar_btn,
                mode,
                building,
            )
    def _place_build_options_button(self, mode):
        """Keep the shared options menu in the active workflow's top header."""
        header_layout = (
            self.title_options_layout
            if mode == "python" else self.dotnet_title_options_layout
        )
        for layout in (
            self.title_options_layout,
            self.dotnet_title_options_layout,
        ):
            layout.removeWidget(self.build_options_btn)
        header_layout.addWidget(self.build_options_btn)
        self.build_options_btn.show()

    def _center_mode_headers(self):
        """Center each visible mode title over its content pane, not its sidebar."""
        for container, title in (
            (self.python_title_content_header, self.title_frame),
            (self.dotnet_title_content_header, self.dotnet_title_container),
        ):
            title.move((container.width() - title.width()) // 2, 0)

    def set_build_mode(self, mode, save=True):
        if mode not in {"python", "dotnet"} or getattr(self, "building", False):
            return
        self.build_mode = mode
        self.build_mode_stack.setCurrentIndex(0 if mode == "python" else 1)
        self._place_build_options_button(mode)
        self._apply_build_mode_button_state(mode)
        self.setFixedSize(
            *(PYTHON_APP_FIXED_SIZE if mode == "python" else DOTNET_APP_FIXED_SIZE)
        )
        self._center_mode_headers()
        QTimer.singleShot(0, self._center_mode_headers)
        if mode == "python":
            self.validation_controller.update_build_button()
            self.validation_controller.update_ui_state()
        else:
            self._sync_dotnet_center_divider_height()
            QTimer.singleShot(0, self._sync_dotnet_center_divider_height)
            self.dotnet_publish_controller.refresh_ui()
        if save and not getattr(self, "_loading_state", False):
            self.state_ctrl.save_preferences()

    def _on_dotnet_settings_changed(self, *_args):
        self._invalidate_saved_setup_backup_status("dotnet")
        self._update_dotnet_selection_summaries()
        self._update_dotnet_build_summary()
        self._update_dotnet_navigation()
        self.dotnet_publish_controller.refresh_ui()
        self._update_saved_dotnet_build_setup_controls()
        if not getattr(self, "_loading_state", False):
            self.state_ctrl.save_csharp_state()

    def _on_dotnet_publish_option_toggled(self, selected, checked):
        """Apply a publish-option choice, allowing an intentionally empty state."""
        self._sync_dotnet_publish_options(selected if checked else None)
        self._on_dotnet_settings_changed()

    def _sync_dotnet_publish_options(self, selected=None):
        """Keep publish options mutually exclusive without disabling alternatives."""
        options = (
            self.dotnet_self_contained,
            self.dotnet_single_file,
            self.dotnet_trim,
        )
        if selected not in options:
            selected = next((option for option in options if option.isChecked()), None)

        for option in options:
            signals_were_blocked = option.blockSignals(True)
            option.setChecked(option is selected)
            option.blockSignals(signals_were_blocked)

        building = getattr(self, "building", False)
        for option in options:
            option.setEnabled(not building)
            if building:
                style = build_disabled_checkbox()
            elif selected is None:
                style = required_selection_checkbox()
            else:
                style = ""
            option.setStyleSheet(style)

    def _start_output_folder_monitor(self):
        self.output_folder_monitor_timer = QTimer(self)
        self.output_folder_monitor_timer.setInterval(OUTPUT_FOLDER_MONITOR_INTERVAL_MS)
        self.output_folder_monitor_timer.timeout.connect(self._refresh_output_folder_validity)
        self.output_folder_monitor_timer.start()

    def _refresh_output_folder_validity(self):
        """Refresh output controls only when either output folder changes state."""
        self.output_folder_monitor.refresh_if_changed()

    def _stop_output_folder_monitor(self):
        timer = getattr(self, "output_folder_monitor_timer", None)
        if timer is not None:
            timer.stop()

    def _select_dotnet_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select C# Project", "", "C# Project Files (*.csproj)")
        if path:
            self.dotnet_publish_controller.select_path("project", path)

    def _select_dotnet_output(self):
        desktop = os.path.normpath(os.path.join(os.path.expanduser("~"), "Desktop"))
        saved = getattr(self, "csharp_state_data", {}).get("last_non_desktop_output_folder", "")
        current = self.dotnet_output_input.text()
        start = next((p for p in (saved, current) if p and os.path.isdir(p) and os.path.normcase(os.path.normpath(p)) != os.path.normcase(desktop)), desktop)
        path = QFileDialog.getExistingDirectory(self, "Select Publish Output Folder", start)
        if path:
            path = os.path.normpath(path)
            self.dotnet_output_input.set_display_path(path)
            if os.path.normcase(path) != os.path.normcase(desktop):
                self.csharp_state_data.setdefault("last_non_desktop_output_folder", path)
                self.state_ctrl.save_csharp_state()
            from exe_builder.ui.ui_highlights import flash_add_highlight
            flash_add_highlight(self.dotnet_output_select_btn, self.dotnet_output_input)

    def _select_dotnet_icon(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Application Icon", "", "ICON Files (*.ico)")
        if path:
            self.dotnet_publish_controller.select_path("icon", path)

    def add_env_sync_status_row(self, version, package_count, status):
        if not hasattr(self, "env_sync_rows_layout"):
            return

        row = QWidget()
        row.setFixedHeight(22)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0,0,0,0)
        row_layout.setSpacing(4)

        column_data = [
            (version, 125),
            (package_count, 80),
            (status, max(275, QFontMetrics(QFont("Rubik UI", 10, QFont.Bold)).horizontalAdvance(str(status)) + 12)),
        ]
        row_width = sum(width for _, width in column_data) + row_layout.spacing() * (len(column_data) - 1)

        for text, width in column_data:
            label = QLabel(text)
            label.setFixedWidth(width)
            label.setFont(QFont("Rubik UI", 10, QFont.Bold))
            if not hasattr(self, "env_sync_row_labels"):
                self.env_sync_row_labels = []
            self.env_sync_row_labels.append(label)
            row_layout.addWidget(label)

        row_layout.addStretch()
        row.setMinimumWidth(row_width)
        self.env_sync_rows_container.setMinimumWidth(
            max(
                self.env_sync_rows_container.minimumWidth(),
                row_width + (2 * ENV_SYNC_TABLE_PADDING),
            )
        )
        self.env_sync_rows_layout.addWidget(row)
        self._sync_center_divider_height()

    def _sync_paired_section_geometry(self):
        if hasattr(self, "python_section_stack"):
            return
        if not all(
            hasattr(self, attr)
            for attr in (
                "env_sync_title",
                "icons_title",
                "apps_title",
                "output_title",
                "env_sync_title_frame",
                "icons_title_frame",
                "apps_title_frame",
                "output_title_frame",
                "env_sync_frame",
                "icon_frame",
                "interpreter_frame",
                "output_frame",
                "content_row",
                "env_sync_rows_scroll_area",
            )
        ):
            return

        self.content_row.setMinimumHeight(0)
        self.content_row.setMaximumHeight(16777215)
        self.left_content.setMinimumHeight(0)
        self.left_content.setMaximumHeight(16777215)
        self.right_content.setMinimumHeight(0)
        self.right_content.setMaximumHeight(16777215)
        self.env_sync_frame.setMinimumHeight(0)
        self.env_sync_frame.setMaximumHeight(16777215)

        for source, target in (
            (self.icons_title, self.env_sync_title),
            (self.output_title, self.apps_title),
        ):
            title_height = max(
                source.height(),
                source.sizeHint().height(),
                target.height(),
                target.sizeHint().height(),
            )
            source.setFixedHeight(title_height)
            target.setFixedHeight(title_height)

        for source, target in (
            (self.icons_title_frame, self.env_sync_title_frame),
            (self.output_title_frame, self.apps_title_frame),
        ):
            frame_height = max(
                source.height(),
                source.sizeHint().height(),
                target.height(),
                target.sizeHint().height(),
            )
            source.setFixedHeight(frame_height)
            target.setFixedHeight(frame_height)

        base_height = getattr(
            self,
            "_env_sync_rows_scroll_base_height",
            self.env_sync_rows_scroll_area.height(),
        )
        self.env_sync_rows_scroll_area.setFixedHeight(base_height)

        for widget in (self, self.content_row, self.left_content, self.right_content):
            layout = widget.layout()
            if layout is not None:
                layout.activate()

        interpreter_top = self.apps_title_frame.mapTo(self.content_row, QPoint(0, 0)).y()
        output_top = self.output_title_frame.mapTo(self.content_row, QPoint(0, 0)).y()
        alignment_delta = output_top - interpreter_top
        next_height = self.env_sync_rows_scroll_area.height() + alignment_delta
        if alignment_delta > 0 and next_height >= base_height:
            self.env_sync_rows_scroll_area.setFixedHeight(next_height)

        self.env_sync_frame.setFixedHeight(self.env_sync_frame.sizeHint().height())
        self.icon_frame.setFixedHeight(self.icon_frame.sizeHint().height())
        for widget in (self, self.content_row, self.left_content, self.right_content):
            layout = widget.layout()
            if layout is not None:
                layout.activate()

    def _sync_center_divider_height(self):
        """Synchronize both mode dividers from the Python layout geometry."""
        if hasattr(self, "python_section_stack"):
            return
        python_attrs = (
            "left_content",
            "right_content",
            "content_row",
            "center_divider",
        )
        if not all(hasattr(self, attr) for attr in python_attrs):
            return

        content_height = max(
            self.left_content.sizeHint().height(),
            self.right_content.sizeHint().height(),
        )
        dotnet_attrs = (
            "dotnet_left_content",
            "dotnet_right_content",
            "dotnet_content_row",
            "dotnet_center_divider",
        )
        has_dotnet_divider = all(hasattr(self, attr) for attr in dotnet_attrs)
        if has_dotnet_divider:
            content_height = max(
                content_height,
                self.dotnet_left_content.sizeHint().height(),
                self.dotnet_right_content.sizeHint().height(),
            )
        if content_height <= 0:
            return

        divider_height = max(1, content_height - self._center_divider_top_offset())
        self.content_row.setFixedHeight(content_height)
        self.center_divider.setFixedHeight(divider_height)
        if has_dotnet_divider:
            self.dotnet_content_row.setFixedHeight(content_height)
            self.dotnet_center_divider.setFixedHeight(divider_height)

    def _sync_dotnet_center_divider_height(self):
        """Compatibility entry point for C# layout refreshes."""
        self._sync_center_divider_height()

    def _center_divider_top_offset(self):
        if not hasattr(self, "icons_title"):
            return 0

        text_bounds = QFontMetrics(self.icons_title.font()).boundingRect(
            self.icons_title.text()
        )
        label_height = self.icons_title.height() or self.icons_title.sizeHint().height()
        text_top_offset = max(0, (label_height - text_bounds.height()) // 2)
        title_position = self.icons_title.mapTo(self.content_row, QPoint(0, 0))
        return max(0, title_position.y() + text_top_offset)

    def _create_content_column(self):
        content = QWidget()
        content.setFixedWidth(CONTENT_COLUMN_WIDTH)
        content.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignTop)

        return content, layout

    def close_app(self):
        self._is_closing = True
        self.close()

    def _show_environment_sync_help(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Environment Sync Help")
        dialog.setText(
            "Environment Sync aligns detected Python profiles by installing missing "
            "or mismatched packages.\n\n"
            "It does not guarantee package compatibility or a successful EXE build. "
            "Some packages may not work with every Python version or build."
        )
        dialog.setIcon(QMessageBox.NoIcon)
        close_button = dialog.addButton("Close", QMessageBox.AcceptRole)
        dialog.setDefaultButton(close_button)
        dialog.setEscapeButton(close_button)
        dialog.setStyleSheet(CONFIRMATION_MESSAGE_BOX_STYLE)
        dialog.setWindowFlags(
            (dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            | Qt.MSWindowsFixedSizeDialogHint
        )

        button_box = dialog.findChild(QDialogButtonBox)
        if button_box is not None:
            button_box.setCenterButtons(True)

        apply_native_title_bar_style(
            dialog,
            caption=Colors.PANEL_BG,
            border=Colors.PANEL_BG,
        )
        dialog.exec()

    def _confirm_manual_close(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle(" ")
        dialog.setText("Are you sure you want to close?")
        dialog.setIcon(QMessageBox.NoIcon)
        close_button = dialog.addButton("Close", QMessageBox.AcceptRole)
        cancel_button = dialog.addButton("Cancel", QMessageBox.RejectRole)
        dialog.setDefaultButton(cancel_button)
        dialog.setEscapeButton(cancel_button)
        dialog.setStyleSheet(CONFIRMATION_MESSAGE_BOX_STYLE)
        dialog.setWindowFlags(
            (dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            | Qt.MSWindowsFixedSizeDialogHint
        )

        button_box = dialog.findChild(QDialogButtonBox)
        if button_box is not None:
            button_box.setCenterButtons(True)

        apply_native_title_bar_style(
            dialog,
            caption=Colors.PANEL_BG,
            border=Colors.PANEL_BG,
        )
        dialog.exec()
        return dialog.clickedButton() == close_button

    def showEvent(self, event):
        super().showEvent(event)
        self._finalize_paired_section_geometry()
        QTimer.singleShot(0, self._finalize_paired_section_geometry)

    def _finalize_paired_section_geometry(self):
        self._sync_paired_section_geometry()
        self._sync_center_divider_height()

    def set_status(self, text):
        self.status_label.setPlainText(text)

        cursor = self.status_label.textCursor()
        cursor.select(QTextCursor.Document)

        fmt = QTextBlockFormat()
        fmt.setAlignment(Qt.AlignCenter)

        cursor.mergeBlockFormat(fmt)

        # 🔑 CLEAR SELECTION (this fixes the green highlight)
        cursor.clearSelection()
        self.status_label.setTextCursor(cursor)

    def set_env_sync_status(self, text):
        if not hasattr(self, "env_sync_log_input"):
            return

        single_line = " ".join(str(text).splitlines()).strip()
        self.env_sync_log_input.setText(single_line)
        self.env_sync_log_input.deselect()
        self.env_sync_log_input.setCursorPosition(0)

    def closeEvent(self, event):
        should_confirm_close = (
            not self._is_closing
            and not getattr(self, "suppress_exit_dialogue_enabled", False)
        )
        if should_confirm_close and not self._confirm_manual_close():
            event.ignore()
            return

        self._is_closing = True
        self._stop_output_folder_monitor()
        self.ui_handlers.shutdown()
        self.build_controller.shutdown()
        self.environment_sync_controller.shutdown()
        self.state_ctrl.save_all_state()
        event.accept()

# -------------------------------------------------------------
# Launch
# -------------------------------------------------------------

def main():
    # ✅ FORCE valid default font (kills -1 propagation)
    font = QFont("Rubik UI")
    font.setPointSize(10)
    QApplication.setFont(font)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()

    # Main background (empty space / non-widget areas)
    palette.setColor(QPalette.Window, Colors.WINDOW)

    app.setPalette(palette)

    window = EXEBuilderApp()
    window.show()
    apply_native_title_bar_style(window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
