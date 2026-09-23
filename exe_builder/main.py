import sys
import os
import ctypes
import threading
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ctypes import wintypes
from exe_builder.controllers.build_controller import BuildController
from exe_builder.controllers.dotnet_publish_controller import DotnetPublishController
from exe_builder.build.datetime_build_options import (
    ISO_MASS_DATETIME_BUILD_LABEL,
    MASS_DATETIME_BUILD_LABEL,
    MASS_DATETIME_BUILD_SENTINEL,
    NO_DATETIME_LABEL,
    REGIONAL_DATETIME_DROPDOWN_GROUPS,
    UK_MASS_DATETIME_BUILD_LABEL,
    USA_MASS_DATETIME_BUILD_LABEL,
)
from exe_builder.controllers.environment_sync_controller import EnvironmentSyncController
from exe_builder.ui.path_hover import attach_path_hovers
from exe_builder.ui.tooltips import attach_tooltips
from PySide6.QtCore import QPoint, QSize, Qt, QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton,QFrame,QApplication,QHBoxLayout,QVBoxLayout,QCheckBox,QLineEdit,QHBoxLayout, QComboBox,QTextEdit,QListView,QScrollArea,QMessageBox,QDialog,QDialogButtonBox,QStackedWidget,QFileDialog
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
    title_frame_minimum_width,
    Colors,
    utility_icon_button_style,
)

APP_FIXED_SIZE = (1200, 915)
CONTENT_COLUMN_WIDTH = 599
PATH_DROPDOWN_SIZE = (320, 35)
PAIRED_FRAME_WIDTH = 575

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
        
        self.setFixedSize(*APP_FIXED_SIZE)
        self.setWindowTitle(" ")
        self.setContentsMargins(0,0,0,0)
        
        self.close_after_build_enabled = getattr(self, "close_after_build_enabled", True)
        self.minimize_after_build_enabled = getattr(self, "minimize_after_build_enabled", True)
        self.open_output_dir_after_build_enabled = getattr(self, "open_output_dir_after_build_enabled", False)
        self.suppress_exit_dialogue_enabled = getattr(self, "suppress_exit_dialogue_enabled", False)
        self.tooltips_enabled = getattr(self, "tooltips_enabled", True)
        self.script_path = getattr(self, "script_path", "")
        self.icon_path = getattr(self, "icon_path", "")
        self.output_path = getattr(self, "output_path", "")
        self.python_path = getattr(self, "python_path", "")
        self.exe_name = getattr(self, "exe_name", "")
        self.build_mode = "python"
                    
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

        title_spacer = QWidget()
        title_spacer.setFixedSize(34, 34)

        self.build_options_btn = QPushButton("⚙")
        self.build_options_btn.setObjectName("buildOptionsButton")
        self.build_options_btn.setAccessibleName("Build options")
        self.build_options_btn.setAccessibleDescription(
            "Open build options and application preferences."
        )
        self.build_options_btn.setFixedSize(34, 34)
        self.build_options_btn.setFont(QFont("Segoe UI Symbol", 18, QFont.Bold))
        self.build_options_btn.setStyleSheet(utility_icon_button_style())

        title_frame_width = title_frame_minimum_width(
            QFontMetrics(self.title_label.font()).horizontalAdvance(
                self.title_label.text()
            ),
            self.build_options_btn.width(),
            10,
        )
        self.title_frame.setFixedWidth(title_frame_width)

        title_layout.addWidget(title_spacer)
        title_layout.addStretch()
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.build_options_btn)

        # -------------------------------
        # BUILD OPTIONS DIALOG
        # -------------------------------

        self.tooltips_checkbox = QCheckBox("Tooltips")
        self.minimize_after_build = QCheckBox("Minimize After Build")
        self.suppress_exit_dialogue = QCheckBox("Surpress Exit Dialogue")
        self.open_output_dir_after_build = QCheckBox("Open Output Directory")
        self.close_after_build = QCheckBox("Close After Build")
        self.open_app_data_btn = QPushButton("Open App Data")

        toggle_columns = QHBoxLayout()
        toggle_columns.setContentsMargins(0, 0, 0, 0)
        toggle_columns.setSpacing(0)

        left_toggle_column = QVBoxLayout()
        left_toggle_column.setContentsMargins(0, 0, 0, 0)
        left_toggle_column.setSpacing(0)

        right_toggle_column = QVBoxLayout()
        right_toggle_column.setContentsMargins(0, 0, 0, 0)
        right_toggle_column.setSpacing(0)

        left_toggle_column.addWidget(self.tooltips_checkbox, alignment=Qt.AlignLeft | Qt.AlignTop)
        left_toggle_column.addWidget(self.minimize_after_build, alignment=Qt.AlignLeft | Qt.AlignTop)
        left_toggle_column.addWidget(self.suppress_exit_dialogue, alignment=Qt.AlignLeft | Qt.AlignTop)
        left_toggle_column.addStretch()

        right_toggle_column.addWidget(self.open_output_dir_after_build, alignment=Qt.AlignLeft | Qt.AlignTop)
        right_toggle_column.addWidget(self.close_after_build, alignment=Qt.AlignLeft | Qt.AlignTop)
        right_toggle_column.addWidget(self.open_app_data_btn, alignment=Qt.AlignLeft | Qt.AlignTop)
        right_toggle_column.addStretch()

        toggle_columns.addLayout(left_toggle_column, 1)
        toggle_columns.addLayout(right_toggle_column, 1)

        self.build_options_dialog = QDialog(self)
        self.build_options_dialog.setWindowTitle("Global Build Options")
        self.build_options_dialog.setModal(True)
        self.build_options_dialog.setFixedSize(500, 150)
        self.build_options_dialog.setStyleSheet(BUILD_OPTIONS_DIALOG_STYLE)
        apply_build_options_title_bar_style(self.build_options_dialog)

        build_options_layout = QVBoxLayout(self.build_options_dialog)
        build_options_layout.setContentsMargins(12, 12, 12, 10)
        build_options_layout.setSpacing(6)
        build_options_layout.addLayout(toggle_columns)

        build_options_buttons = QDialogButtonBox(QDialogButtonBox.Close)
        build_options_buttons.rejected.connect(self.build_options_dialog.reject)
        build_options_buttons.setCenterButtons(True)
        self.build_options_close_btn = build_options_buttons.button(
            QDialogButtonBox.Close
        )
        self.build_options_close_btn.setFixedSize(120, 32)
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
        title_row.setFixedHeight(44)
        title_row_layout = QHBoxLayout(title_row)
        title_row_layout.setContentsMargins(0, 0, 0, 0)
        title_row_layout.setSpacing(20)
        title_row_layout.addWidget(self.title_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)

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
        self.env_sync_log_input.setFixedWidth(485)
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
        self.env_sync_scan_btn.setFixedSize(145,35)
        self.env_sync_match_btn.setFixedSize(175,35)
        self.env_sync_match_btn.setEnabled(False)
        self.env_sync_scan_btn.setStyleSheet(ENV_SYNC_BUTTON_STYLE)
        self.env_sync_match_btn.setStyleSheet(ENV_SYNC_BUTTON_STYLE)

        env_sync_action_layout.addWidget(self.env_sync_scan_btn)
        env_sync_action_layout.addWidget(self.env_sync_match_btn)
        env_sync_action_layout.addStretch()

        self.env_sync_warning_label = QLabel(
            "Warning: builds can fail when the selected Python environment is "
            "missing dependencies. Scan profiles and sync missing or mismatched "
            "packages when needed. Some environments still may not sync if required "
            "packages are not compatible with that Python version or build."
        )
        self.env_sync_warning_label.setFixedWidth(485)
        self.env_sync_warning_label.setWordWrap(True)
        self.env_sync_warning_label.setFont(QFont("Rubik UI", 10, QFont.Bold))
        self.env_sync_warning_label.setStyleSheet(
            f"QLabel {{ color: {qcolor_name(Colors.WARNING)}; }}"
        )

        self.env_sync_status_header = QWidget()
        env_sync_status_header_layout = QHBoxLayout(self.env_sync_status_header)
        env_sync_status_header_layout.setContentsMargins(0,0,0,0)
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
        self.env_sync_rows_layout.setContentsMargins(0,0,0,0)
        self.env_sync_rows_layout.setSpacing(2)

        env_sync_visible_rows = 5
        env_sync_row_height = 22
        env_sync_row_spacing = self.env_sync_rows_layout.spacing()
        env_sync_scroll_height = (
            env_sync_visible_rows * env_sync_row_height
            + (env_sync_visible_rows - 1) * env_sync_row_spacing
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
        apps_layout.setContentsMargins(1,1,1,1)
        apps_layout.setSpacing(4)

        self.open_python_site_btn = QPushButton("Python.org")
        apps_layout.addWidget(self.open_python_site_btn)
        apps_layout.addStretch()

        # =================================================
        # Interpreter (VERTICAL stack)
        # =================================================

        interpreter_container = QWidget()
        interpreter_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        interpreter_layout = QVBoxLayout(interpreter_container)
        interpreter_layout.setContentsMargins(0,0,0,0)
        interpreter_layout.setSpacing(3)

        interpreter_btn_row = QWidget()
        interpreter_btn_row.setFixedHeight(37)
        interpreter_btn_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        interpreter_btn_layout = QHBoxLayout(interpreter_btn_row)
        interpreter_btn_layout.setContentsMargins(1,1,1,1)
        interpreter_btn_layout.setSpacing(4)
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
        interpreter_entry_row.setFixedHeight(37)
        interpreter_entry_row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        interpreter_entry_layout = QHBoxLayout(interpreter_entry_row)
        interpreter_entry_layout.setContentsMargins(1,1,1,1)
        interpreter_entry_layout.setSpacing(3)

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
        icon_frame_layout.setContentsMargins(1,1,1,1)
        icon_frame_layout.setSpacing(1)

        icon_block = QWidget()
        icon_block_layout = QVBoxLayout(icon_block)
        icon_block_layout.setContentsMargins(1,1,1,1)
        icon_block_layout.setSpacing(1)

        # -------- Row 1: Select Icon + Recent Dropdown + Delete --------

        icon_row1 = QWidget()
        icon_row1_layout = QHBoxLayout(icon_row1)
        icon_row1_layout.setContentsMargins(1,1,1,1)
        icon_row1_layout.setSpacing(1)

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
        icon_row2_layout.setContentsMargins(1,1,1,1)
        icon_row2_layout.setSpacing(5)

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
        icon_entry_layout.setContentsMargins(1,1,1,1)
        icon_entry_layout.setSpacing(5)

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
        folder_row.setContentsMargins(0, 0, 0, 0)
        folder_row.setSpacing(5)

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

        script_layout.setContentsMargins(1,1,1,1)
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
        self.date_time_dropdown.addItem("Date Time Append")

        self.appened_py_version = QPushButton("Append Py Version")
        self.appened_py_version.setFixedSize(125,35)
        self.appened_py_version.setCheckable(True)

        self.appened_py_version.setStyleSheet(APPEND_PY_VERSION_INITIAL_STYLE)
                
        self.date_time_dropdown.clear()

        def _add(label, data=None, enabled=True):
            self.date_time_dropdown.addItem(label, data)
            item = self.date_time_dropdown.model().item(self.date_time_dropdown.count() - 1)
            if not enabled:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)

        # Header
        _add("Append Date/Time", None, enabled=False)

        _add("──────────", enabled=False)
        # Top option
        _add(NO_DATETIME_LABEL, None)

        _add("──────────", enabled=False)
        _add(MASS_DATETIME_BUILD_LABEL, MASS_DATETIME_BUILD_SENTINEL)

        for (
            region_label,
            build_all_label,
            build_all_data,
            format_options,
        ) in REGIONAL_DATETIME_DROPDOWN_GROUPS:
            _add("──────────", enabled=False)
            _add(region_label, enabled=False)
            for label, data in format_options:
                _add(label, data)
            _add(build_all_label, build_all_data)

        date_dropdown_metrics = QFontMetrics(self.date_time_dropdown.font())
        longest_date_label = max(
            MASS_DATETIME_BUILD_LABEL,
            ISO_MASS_DATETIME_BUILD_LABEL,
            UK_MASS_DATETIME_BUILD_LABEL,
            USA_MASS_DATETIME_BUILD_LABEL,
            key=len,
        )
        date_dropdown_width = max(300, date_dropdown_metrics.horizontalAdvance(longest_date_label) + 64)
        self.date_time_dropdown.setFixedSize(date_dropdown_width, 35)

        model = self.date_time_dropdown.model()
        item = model.item(0)
        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
        
        self.date_time_dropdown.setEditable(True)
        self.date_time_dropdown.lineEdit().setReadOnly(True)
        self.date_time_dropdown.setCurrentIndex(0)
        self.date_time_dropdown.setEnabled(True)
            
        row1 = QHBoxLayout()
        row1.setContentsMargins(1,1,1,1)
        row1.setSpacing(4)

        row1.addWidget(self.appened_py_version)
        row1.addStretch()

        row2 = QHBoxLayout()
        row2.setContentsMargins(1,1,1,1)
        row2.setSpacing(4)
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
        output_entry_layout.setContentsMargins(1,1,1,1)
        output_entry_layout.setSpacing(3)

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
        exe_layout.setContentsMargins(1,1,1,1)
        exe_layout.setSpacing(3)

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

        build_layout = QVBoxLayout(build_frame)
        build_layout.setContentsMargins(5,5,5,5)
        build_layout.setSpacing(4)

        self.status_label = QTextEdit("Ready")
        self.status_label.setReadOnly(True)
        self.status_label.setFixedSize(200,100)
        self.status_label.setFont(QFont("Rubik UI", 12, QFont.Bold))

        # 🔑 center text
        cursor = self.status_label.textCursor()
        cursor.select(QTextCursor.Document)

        fmt = QTextBlockFormat()
        fmt.setAlignment(Qt.AlignCenter)

        cursor.mergeBlockFormat(fmt)
        self.status_label.setTextCursor(cursor)

        

        self.build_btn = QPushButton("Build EXE")
        self.build_btn.setFont(QFont("Rubik UI", 13, QFont.Bold))
        self.build_btn.setFixedSize(150, 35)
        self.build_btn.clicked.connect(self.build_controller.build_exe)

        build_layout.addWidget(self.status_label)
        build_layout.addWidget(self.build_btn, alignment=Qt.AlignCenter)

        output_frame_width = max(
            PAIRED_FRAME_WIDTH,
            self.output_btn.sizeHint().width() + self.date_time_dropdown.width() + 40,
        )
        self.output_frame.setFixedSize(output_frame_width, 170)
        self.interpreter_frame.setFixedSize(output_frame_width, self.output_frame.height())
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

        section_output_line_height = 30
        for widget in [
            self.python_entry_input,
            self.icon_path_input,
            self.script_path_input,
            self.output_path_input,
            self.exe_name_input,
        ]:
            widget.setFixedHeight(section_output_line_height)

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

        attach_tooltips(self)
        attach_path_hovers(self)
        self._loading_state = False
        self.state_ctrl.load_state()
        self.dotnet_publish_controller.populate_recents("project")
        self.dotnet_publish_controller.populate_recents("icon")
        self.recent_controller.populate_recent_dropdown()
        self.validator.validation_status_message()
        self.json_import_controller.attach()
        self.env_sync_scan_btn.clicked.connect(self.ui_handlers.on_env_sync_scan)
        self.env_sync_match_btn.clicked.connect(self.ui_handlers.on_env_sync_match)
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
        self.suppress_exit_dialogue.stateChanged.connect(self.ui_handlers.on_suppress_exit_dialogue_toggle)
        self.close_after_build.stateChanged.connect(self.ui_handlers.on_close_toggle)

        self.validator.update_ui_state()
        self.validation_controller.update_build_button()
        self.dotnet_publish_controller.refresh_ui()
        self.output_folder_monitor = OutputFolderValidityMonitor(self)
        self._start_output_folder_monitor()
        self._sync_paired_section_geometry()
        self._sync_center_divider_height()

    def _show_build_options(self):
        """Open the compact dialog that contains the build option controls."""
        if not self.building:
            # A mode switch can recreate the native handle; reapply DWM colours.
            apply_build_options_title_bar_style(self.build_options_dialog)
            self.build_options_dialog.exec()

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
        dotnet_layout.setContentsMargins(20, 12, 20, 12)
        dotnet_layout.setSpacing(8)
        self.dotnet_mode_title = QLabel("C# .NET → EXE Publish")
        self.dotnet_mode_title.setFont(QFont("Rubik UI", 18, QFont.Bold))
        self.dotnet_mode_title.setAlignment(Qt.AlignCenter)
        self.dotnet_mode_title.setStyleSheet(
            f"QLabel {{ color: {qcolor_name(Colors.TEXT_LIGHT)}; }}"
        )
        self.dotnet_section_title_frames = []
        self.dotnet_configuration_frames = []
        dotnet_layout.addWidget(self.dotnet_mode_title)

        columns = QHBoxLayout()
        columns.setSpacing(4)
        dotnet_layout.addLayout(columns)
        left_column = QVBoxLayout()
        right_column = QVBoxLayout()
        left_column.setSpacing(4)
        right_column.setSpacing(4)
        columns.addLayout(left_column)
        columns.addLayout(right_column)

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
            row = QHBoxLayout()
            row.setSpacing(5)
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
            field = PathDisplayLineEdit()
            field.setPlaceholderText(placeholder)
            field.setFixedHeight(30)
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

        path_section("project", "File Select", left_column, "C# Project File", "No C# project selected.")
        path_section("icon", "Icons Select", right_column, "Select ICO optional", "No icon selected.")

        output_layout = section("Output Select", right_column)
        output_select_row = QHBoxLayout()
        self.dotnet_output_select_btn = QPushButton("Output Folder")
        self.dotnet_output_select_btn.setFixedSize(160, 35)
        self.dotnet_output_select_btn.setFont(QFont("Rubik UI", 11, QFont.Bold))
        self.dotnet_output_select_btn.setStyleSheet(button_base())
        self.dotnet_output_select_btn.clicked.connect(self._select_dotnet_output)
        output_select_row.addWidget(self.dotnet_output_select_btn)
        output_select_row.addStretch()
        output_layout.addLayout(output_select_row)
        output_entry = QHBoxLayout()
        self.dotnet_output_input = PathDisplayLineEdit()
        self.dotnet_output_input.setPlaceholderText("No output folder selected.")
        self.dotnet_output_input.setFixedHeight(30)
        self.dotnet_output_reset_btn = utility_button(REFRESH_BUTTON_ICON, REFRESH_BUTTON_ICON_SIZE, REFRESH_BUTTON_TEXT)
        self.dotnet_output_reset_btn.clicked.connect(self.dotnet_publish_controller.reset_output_to_desktop)
        output_entry.addWidget(self.dotnet_output_input)
        output_entry.addWidget(self.dotnet_output_reset_btn)
        output_layout.addLayout(output_entry)
        name_entry = QHBoxLayout()
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

        option_row = QHBoxLayout()
        self.dotnet_runtime_label = QLabel("Target runtime")
        self.dotnet_runtime_label.setFont(QFont("Rubik UI", 11, QFont.Bold))
        option_row.addWidget(self.dotnet_runtime_label)
        self.dotnet_runtime_combo = QComboBox()
        self.dotnet_runtime_combo.addItem("Windows x64", "win-x64")
        self.dotnet_runtime_combo.addItem("Windows ARM64", "win-arm64")
        self.dotnet_runtime_combo.setStyleSheet(COMBO_BOX_STYLE)
        option_row.addWidget(self.dotnet_runtime_combo)
        self.dotnet_self_contained = QCheckBox("Self-contained")
        self.dotnet_single_file = QCheckBox("Single file")
        self.dotnet_trim = QCheckBox("Trim")
        for checkbox in (
            self.dotnet_self_contained,
            self.dotnet_single_file,
            self.dotnet_trim,
        ):
            checkbox.setFont(QFont("Rubik UI", 11, QFont.Bold))
        self.dotnet_self_contained.setChecked(True)
        option_row.addWidget(self.dotnet_self_contained)
        option_row.addWidget(self.dotnet_single_file)
        option_row.addWidget(self.dotnet_trim)
        option_row.addStretch()
        panel_layout.addLayout(option_row)

        self.dotnet_status_label = QTextEdit("Select a C# project to begin.")
        self.dotnet_status_label.setReadOnly(True)
        self.dotnet_status_label.setFixedSize(520, 65)
        self.dotnet_status_label.setFont(QFont("Rubik UI", 11, QFont.Bold))
        self.dotnet_status_frame = QFrame()
        self.dotnet_status_frame.setObjectName("configurationFrame")
        self.dotnet_status_frame.setStyleSheet(MAIN_FRAME_STYLE)
        self.dotnet_configuration_frames.append(self.dotnet_status_frame)
        self.dotnet_status_frame.setFixedSize(530, 75)
        status_layout = QVBoxLayout(self.dotnet_status_frame)
        status_layout.setContentsMargins(3, 3, 3, 3)
        status_layout.setSpacing(0)
        status_layout.addWidget(self.dotnet_status_label)
        panel_layout.addWidget(self.dotnet_status_frame, alignment=Qt.AlignHCenter)
        actions = QHBoxLayout()
        self.dotnet_publish_btn = QPushButton("Publish")
        self.dotnet_open_output_btn = QPushButton("Open Output Folder")
        for button in (self.dotnet_publish_btn, self.dotnet_open_output_btn):
            button.setFixedSize(180, 35)
            button.setFont(QFont("Rubik UI", 11, QFont.Bold))
            button.setStyleSheet(button_base())
            actions.addWidget(button)
        actions.addStretch()
        panel_layout.addLayout(actions)
        left_column.addWidget(panel, alignment=Qt.AlignHCenter | Qt.AlignTop)
        left_column.addStretch()
        right_column.addStretch()
        dotnet_layout.addStretch()

        self.build_mode_stack = QStackedWidget()
        self.build_mode_stack.addWidget(self.python_mode_page)
        self.build_mode_stack.addWidget(self.dotnet_mode_page)
        mode_row = QWidget()
        mode_layout = QHBoxLayout(mode_row)
        mode_layout.setContentsMargins(0, 4, 0, 4)
        mode_layout.addStretch()
        self.build_mode_label = QLabel("Build mode:")
        self.build_mode_label.setStyleSheet(
            f"QLabel {{ color: {qcolor_name(Colors.TEXT_LIGHT)}; }}"
        )
        self.build_mode_label.setFont(build_mode_button_font())
        mode_layout.addWidget(self.build_mode_label)
        self.python_mode_btn = QPushButton("Python EXE")
        self.dotnet_mode_btn = QPushButton("C# .NET Publish")
        for button in (self.python_mode_btn, self.dotnet_mode_btn):
            button.setCheckable(True)
            button.setFixedSize(150, 32)
            button.setFont(build_mode_button_font())
            button.setStyleSheet(button_base())
            mode_layout.addWidget(button)
        mode_layout.addStretch()
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
        for widget in (self.dotnet_self_contained, self.dotnet_single_file, self.dotnet_trim):
            widget.toggled.connect(
                lambda checked, selected=widget: self._on_dotnet_publish_option_toggled(selected, checked)
            )
        self._sync_dotnet_publish_options()
        root_layout.addWidget(mode_row)
        root_layout.addWidget(self.build_mode_stack)

    def _apply_build_mode_button_state(self, mode):
        """Refresh build-mode selectors for the displayed mode and build state."""
        apply_build_mode_button_state(
            self.python_mode_btn,
            self.dotnet_mode_btn,
            mode,
            getattr(self, "building", False),
        )

    def set_build_mode(self, mode, save=True):
        if mode not in {"python", "dotnet"} or getattr(self, "building", False):
            return
        self.build_mode = mode
        self.build_mode_stack.setCurrentIndex(0 if mode == "python" else 1)
        self._apply_build_mode_button_state(mode)
        self.setFixedSize(*(APP_FIXED_SIZE if mode == "python" else (1200, 650)))
        if mode == "python":
            self.validation_controller.update_build_button()
            self.validation_controller.update_ui_state()
        else:
            self.dotnet_publish_controller.refresh_ui()
        if save and not getattr(self, "_loading_state", False):
            self.state_ctrl.save_preferences()

    def _on_dotnet_settings_changed(self, *_args):
        self.dotnet_publish_controller.refresh_ui()
        if not getattr(self, "_loading_state", False):
            self.state_ctrl.save_csharp_state()

    def _on_dotnet_publish_option_toggled(self, selected, checked):
        """Apply the selected .NET publish option, or its required empty state."""
        self._sync_dotnet_publish_options(selected if checked else None)
        self._on_dotnet_settings_changed()

    def _sync_dotnet_publish_options(self, selected=None):
        """Synchronize one selected publish option or the required empty state."""
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
            enabled = not building and (selected is None or option is selected)
            option.setEnabled(enabled)
            if building or not enabled:
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
            max(self.env_sync_rows_container.minimumWidth(), row_width)
        )
        self.env_sync_rows_layout.addWidget(row)
        self._sync_center_divider_height()

    def _sync_paired_section_geometry(self):
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

        self.interpreter_frame.setFixedHeight(self.output_frame.height())

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
        self.interpreter_frame.setFixedHeight(self.output_frame.height())

        for widget in (self, self.content_row, self.left_content, self.right_content):
            layout = widget.layout()
            if layout is not None:
                layout.activate()

    def _sync_center_divider_height(self):
        if not all(
            hasattr(self, attr)
            for attr in ("left_content", "right_content", "content_row", "center_divider")
        ):
            return

        content_height = max(
            self.left_content.sizeHint().height(),
            self.right_content.sizeHint().height(),
        )
        if content_height <= 0:
            return

        divider_top_offset = self._center_divider_top_offset()
        self.content_row.setFixedHeight(content_height)
        self.center_divider.setFixedHeight(max(1, content_height - divider_top_offset))

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
