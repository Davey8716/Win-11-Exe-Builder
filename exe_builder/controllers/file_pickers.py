import os
import subprocess
from PySide6.QtWidgets import QFileDialog, QDialog, QVBoxLayout, QPushButton, QLabel, QComboBox, QVBoxLayout, QPushButton,QFrame
from PySide6.QtCore import Qt
from ..ui.styles import (
    Colors,
    SCRIPT_PICKER_CONFIRM_STYLE,
    SCRIPT_PICKER_DROPDOWN_STYLE,
    SCRIPT_PICKER_FRAME_STYLE,
    SCRIPT_PICKER_LABEL_STYLE,
    apply_native_title_bar_style,
)
from ..ui.ui_highlights import flash_add_highlight

# -------------------------------------------------------------
# File Pickers (Qt version)
# -------------------------------------------------------------

class FilePickerController:
    def __init__(self, app):
        """
        app = EXEBuilderApp instance
        """
        self.app = app

    def _derive_exe_name_from_script(self, script_path):
        return os.path.splitext(os.path.basename(script_path))[0]

    # ============================================================
    # Locate python installs
    # ============================================================

    def _get_where_python_dirs(self):
        """Return a list of python.exe paths from `where python` (silent)."""
        try:
            result = subprocess.run(
                ["where", "python"],
                capture_output=True,
                text=True,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )

            paths = [
                line.strip()
                for line in result.stdout.splitlines()
                if line.lower().endswith("python.exe")
            ]

            return paths
        except Exception:
            return []

    # ============================================================
    # Select python interpreter
    # ============================================================
    def select_python_interpreter(self):
        start_dir = self._resolve_python_start_dir() or os.path.expanduser("~")

        path, _ = QFileDialog.getOpenFileName(
            self.app,
            "Select Python Interpreter",
            start_dir,
            "Python Interpreter (python.exe)"
        )

        if not path:
            return

        # 🔑 NORMALIZE
        path = os.path.normpath(path)

        # ✅ SINGLE SOURCE OF TRUTH (current)
        self.app.python_interpreter_path = path
        self.app.python_path = path

        # ✅ UI update
        if hasattr(self.app, "python_entry_input"):
            self.app.python_entry_input.set_display_path(path)

        flash_add_highlight(
            getattr(self.app, "interpreter_btn", None),
            getattr(self.app, "python_entry_input", None),
        )

        # 🔑 ADD → recents system
        if hasattr(self.app, "recent_controller"):
            self.app.recent_controller.add_recent_interpreter(path)
            self.app.recent_controller.populate_recent_interpreters_dropdown()

        # remember last dir
        self.app.last_python_dir = os.path.dirname(path)

        # persist
        if hasattr(self.app, "state_ctrl"):
            self.app.state_ctrl.save_state()

        # refresh validation
        if hasattr(self.app, "validator"):
            self.app.validator.validation_status_message()
            self.app.validator.update_ui_state()

        self.app.state_ctrl.save_state()
            
    def _resolve_python_start_dir(self):
        """Best directory to open the interpreter picker in."""

        # 1️⃣ Last-used interpreter directory (preferred)
        last_dir = getattr(self.app, "last_python_dir", "")
        last_dir = os.path.normpath(last_dir) if last_dir else ""

        if last_dir and os.path.isdir(last_dir):
            return last_dir

        # 2️⃣ Use `where python` as a hint
        candidates = self._get_where_python_dirs()
        for path in candidates:
            if "WindowsApps" not in path:
                path = os.path.normpath(path)
                return os.path.dirname(path)

        return None

    # ============================================================
    # Select single script
    # ============================================================

    def select_script(self):
        path, _ = QFileDialog.getOpenFileName(
            self.app,
            "Select Python Script",
            "",
            "Python Files (*.py)"
        )

        if not path:
            return

        path = os.path.normpath(path)

        # 🔑 SINGLE SOURCE OF TRUTH
        self._apply_selected_entry(path)

    # ============================================================
    # Select script folder
    # ============================================================

    def select_script_folder(self):

        start_dir = None

        # 1️⃣ Existing project root
        if getattr(self.app, "project_root", None):
            root = os.path.normpath(self.app.project_root)
            if os.path.isdir(root):
                start_dir = root

        # 2️⃣ Last selected script path
        elif getattr(self.app, "script_path", ""):
            script = os.path.normpath(self.app.script_path)
            if os.path.isfile(script):
                start_dir = os.path.dirname(script)

        # 3️⃣ Fallback: Desktop
        if not start_dir:
            start_dir = os.path.join(os.path.expanduser("~"), "Desktop")

        folder = QFileDialog.getExistingDirectory(
            self.app,
            "Select Python Folder",
            start_dir
        )

        if not folder:
            return

        folder = os.path.normpath(folder)

        py_files = [
            f for f in os.listdir(folder)
            if f.endswith(".py") and os.path.isfile(os.path.join(folder, f))
        ]

        if not py_files:
            return

        # Single-file shortcut
        if len(py_files) == 1:
            full_path = os.path.join(folder, py_files[0])
            full_path = os.path.normpath(full_path)
            self._apply_selected_entry(full_path)
            return

        # Multi-file → popup
        popup = ScriptPickerPopup(
            parent=self.app,
            folder_path=folder,
            py_files=py_files,
            callback=self._apply_selected_entry
        )
        popup.exec()

    # ============================================================
    # Apply selected entry
    # ============================================================
    def _apply_selected_entry(self, full_path):
        """Callback from ScriptPickerPopup"""

        # 🔑 NORMALIZE
        full_path = os.path.normpath(full_path)

        # ------------------------------------
        # Capture previous state BEFORE change
        # ------------------------------------

        previous_script = getattr(self.app, "entry_script", "")
        previous_exe_name = getattr(self.app, "exe_name", "").strip()

        # ------------------------------------
        # Apply new script selection
        # ------------------------------------

        self.app.entry_script = full_path
        
        if hasattr(self.app, "script_path_input"):
            display = os.path.normpath(full_path)
            self.app.script_path_input.set_display_path(display)

        flash_add_highlight(
            getattr(self.app, "folder_btn", None),
            getattr(self.app, "script_path_input", None),
        )

        self.app.project_root = os.path.dirname(full_path)
        self.app.script_path = full_path

        # ------------------------------------
        # Auto-update EXE name ONLY if safe
        # ------------------------------------

        old_derived = ""
        if previous_script:
            previous_script = os.path.normpath(previous_script)
            old_derived = os.path.splitext(os.path.basename(previous_script))[0]

        new_derived = os.path.splitext(os.path.basename(full_path))[0]

        if not previous_exe_name or previous_exe_name in {
            old_derived,
            new_derived
        }:
            self.app.exe_name = new_derived

            if hasattr(self.app, "exe_name_input"):
                self.app.exe_name_input.setText(new_derived)

      
        # ------------------------------------
        # Persist + revalidate
        # ------------------------------------

        self.app.recent_controller.add_recent_script(full_path)
        self.app.recent_controller.populate_recent_dropdown()

        self.app.state_ctrl.save_state()
        self.app.validator.validation_status_message()
        self.app.validator.update_ui_state()
        
    def _apply_selected_icon(self, full_path):
    # 🔑 NORMALIZE
        full_path = os.path.normpath(full_path)

        # ------------------------------------
        # Apply new icon selection
        # ------------------------------------

        self.app.icon_path = full_path
        self.app.icon_user_cleared = False

        if hasattr(self.app, "icon_path_input"):
            display = os.path.normpath(full_path)
            self.app.icon_path_input.set_display_path(display)

        flash_add_highlight(
            getattr(self.app, "icon_btn", None),
            getattr(self.app, "icon_path_input", None),
        )

        # ------------------------------------
        # Persist + revalidate (MATCH SCRIPT)
        # ------------------------------------

        self.app.recent_controller.add_recent_icon(full_path)
        self.app.recent_controller.populate_recent_icons_dropdown()

        self.app.state_ctrl.save_state()
        self.app.validator.validation_status_message()
        self.app.validator.update_ui_state()

    # ============================================================
    # Select icon
    # ============================================================

    def select_icon(self):
        path, _ = QFileDialog.getOpenFileName(
            self.app,
            "Select Icon",
            "",
            "ICON Files (*.ico)"
        )

        if path:
            # 🔑 NORMALIZE
            path = os.path.normpath(path)

            self.app.icon_path = path
            self.app.icon_user_cleared = False

            # ✅ update UI
            if hasattr(self.app, "icon_path_input"):
                self.app.icon_path_input.set_display_path(path)

            flash_add_highlight(
                getattr(self.app, "icon_btn", None),
                getattr(self.app, "icon_path_input", None),
            )
                
            self.app.recent_controller.add_recent_icon(path)
            self.app.recent_controller.populate_recent_icons_dropdown()


            self.app.state_ctrl.save_state()
            self.app.validator.validation_status_message()
            self.app.validator.update_ui_state()

    # ============================================================
    # Select output folder
    # ============================================================
    def _desktop_path(self):
        return os.path.normpath(os.path.join(os.path.expanduser("~"), "Desktop"))

    def _is_desktop_path(self, path):
        if not path:
            return False
        return os.path.normcase(os.path.normpath(path)) == os.path.normcase(self._desktop_path())

    def _valid_non_desktop_output_dir(self, path):
        return bool(path and os.path.isdir(path) and not self._is_desktop_path(path))

    def _resolve_output_start_dir(self):
        for attr in ("last_output_dir", "last_non_desktop_output_dir", "output_path"):
            raw_path = getattr(self.app, attr, "") or ""
            path = os.path.normpath(raw_path) if raw_path else ""
            if self._valid_non_desktop_output_dir(path):
                return path

        return self._desktop_path()

    def select_output_folder(self):
        start_dir = self._resolve_output_start_dir()
        folder = QFileDialog.getExistingDirectory(
            self.app,
            "Select Output Folder",
            start_dir
        )

        if not folder:
            return

        # 🔑 NORMALIZE
        folder = os.path.normpath(folder)

        # optional alias
        self.app.output_path = folder

        # remember last non-Desktop location for the next picker open
        if not self._is_desktop_path(folder):
            self.app.last_output_dir = folder
            self.app.last_non_desktop_output_dir = folder

        if hasattr(self.app, "output_path_input"):
            self.app.output_path_input.set_display_path(folder)

        flash_add_highlight(
            getattr(self.app, "output_btn", None),
            getattr(self.app, "output_path_input", None),
        )

        # Auto-derive exe name ONLY if empty
        if not getattr(self.app, "exe_name", "").strip():
            script = getattr(self.app, "entry_script", "") or getattr(self.app, "script_path", "")
            if script:
                script = os.path.normpath(script)
                base = os.path.splitext(os.path.basename(script))[0]
                self.app.exe_name = base

                if hasattr(self.app, "exe_name_input"):
                    self.app.exe_name_input.setText(base)

        self.app.state_ctrl.save_state()
        self.app.validator.validation_status_message()
        self.app.validator.update_ui_state()
    
class ScriptPickerPopup(QDialog):
    def __init__(self, parent, folder_path, py_files, callback):
        super().__init__(parent)

        self.setWindowTitle("Select Entry Script")
        self.setFixedSize(300, 200)
        self.setWindowFlags(
            (self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            | Qt.MSWindowsFixedSizeDialogHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        apply_native_title_bar_style(
            self,
            caption=Colors.PANEL_BG,
            border=Colors.PANEL_BG,
        )

        # 🔑 NORMALIZE
        self.folder_path = os.path.normpath(folder_path)

        self.callback = callback

        # -------------------------------------------------------------
        # Position: snap to right side of parent
        # -------------------------------------------------------------

        parent_geom = parent.geometry()
        x = parent_geom.x() + parent_geom.width()
        y = parent_geom.y()

        self.move(x, y)

    # -------------------------------------------------------------
        # Layout
        # -------------------------------------------------------------

        layout = QVBoxLayout(self)

        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.NoFrame)
        self.frame.setFrameShadow(QFrame.Raised)
        self.frame.setLineWidth(1)

        self.frame.setStyleSheet(SCRIPT_PICKER_FRAME_STYLE)

        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.setSpacing(6)

        label = QLabel("Select the script\nthat starts your program:")
        label.setWordWrap(True)
        label.setStyleSheet(SCRIPT_PICKER_LABEL_STYLE)
        frame_layout.addWidget(label, alignment=Qt.AlignHCenter)

        self.dropdown = QComboBox()
        self.dropdown.addItems(py_files)
        self.dropdown.setStyleSheet(SCRIPT_PICKER_DROPDOWN_STYLE)
        frame_layout.addWidget(self.dropdown, alignment=Qt.AlignHCenter)

        confirm_btn = QPushButton("Confirm")
        confirm_btn.setFixedWidth(120)
        confirm_btn.clicked.connect(self.confirm)
        confirm_btn.setStyleSheet(SCRIPT_PICKER_CONFIRM_STYLE)
        frame_layout.addWidget(confirm_btn, alignment=Qt.AlignHCenter)

        layout.addWidget(self.frame, alignment=Qt.AlignHCenter)

    def confirm(self):
        selected_file = self.dropdown.currentText()

        full_path = os.path.join(self.folder_path, selected_file)

        # 🔑 NORMALIZE
        full_path = os.path.normpath(full_path)

        # Return selection
        self.callback(full_path)

        self.accept()
