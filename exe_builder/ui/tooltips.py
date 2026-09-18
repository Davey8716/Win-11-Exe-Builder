from PySide6.QtCore import QObject, QEvent, QTimer, QPoint
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import Qt, QCursor
from .styles import TOOLTIP_STYLE

# -------------------------------------------------------------
#  Simple tooltip class for Qt widgets (qt_material compatible)
# -------------------------------------------------------------
class QtTooltip(QObject):
    def __init__(
        self,
        widget,
        text,
        delay=500,
        direct_widget_only=False,
        ignored_hover_children=None,
        blocked_hover_widgets=None,
    ):
        super().__init__(widget)

        self.widget = widget
        self.text = text
        self.delay = delay
        self.direct_widget_only = direct_widget_only
        self.ignored_hover_children = set(ignored_hover_children or [])
        self.blocked_hover_widgets = set(blocked_hover_widgets or [])

        self.tip_window = None
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.show)
        self.monitor_timer = QTimer()
        self.monitor_timer.setInterval(75)
        self.monitor_timer.timeout.connect(self._monitor_direct_hover)

        # Install event filter instead of Tk bindings
        if self.blocked_hover_widgets:
            widget.setMouseTracking(True)
        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.widget:
            if event.type() in (QEvent.Enter, QEvent.MouseMove):
                self._handle_hover_update()
            elif event.type() == QEvent.Leave:
                self.hide()
            elif event.type() == QEvent.MouseButtonPress:
                self.hide()
        return super().eventFilter(obj, event)

    def schedule(self):
        if self._is_blocked_hover():
            self.hide()
            return

        if self.direct_widget_only and not self._is_direct_hover():
            self.hide()
            return

        self.timer.stop()
        self.timer.start(self.delay)

    def show(self):
        if self._is_blocked_hover():
            self._hide_tip_window()
            return

        if self.direct_widget_only and not self._is_direct_hover():
            self.hide()
            return

        # Global toggle (match your existing pattern)
        root = self.widget.window()
        if hasattr(root, "tooltips_enabled"):
            if not root.tooltips_enabled:
                return

        if self.tip_window:
            return

        self.tip_window = QLabel(self.text, None)
        self.tip_window.setWindowFlags(
            Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )

        # Styling (qt_material-friendly)
        self.tip_window.setStyleSheet(TOOLTIP_STYLE)

        self.tip_window.adjustSize()

        # Position relative to widget (same offsets as before)
        pos = self.widget.mapToGlobal(QPoint(40, 25))
        self.tip_window.move(pos)

        self.tip_window.show()
        if self.direct_widget_only or self.blocked_hover_widgets:
            self.monitor_timer.start()

    def hide(self):
        self.timer.stop()
        self.monitor_timer.stop()
        self._hide_tip_window()

    def _hide_tip_window(self):
        if self.tip_window:
            self.tip_window.close()
            self.tip_window = None

    def _is_direct_hover(self):
        local_pos = self.widget.mapFromGlobal(QCursor.pos())
        if not self.widget.rect().contains(local_pos):
            return False

        child = self.widget.childAt(local_pos)
        if child is None:
            return True

        if child not in self.ignored_hover_children:
            return False

        child_pos = child.mapFromGlobal(QCursor.pos())
        return child.childAt(child_pos) is None

    def _monitor_direct_hover(self):
        if self._is_blocked_hover():
            self.timer.stop()
            self._hide_tip_window()
            return

        if self.direct_widget_only and not self._is_direct_hover():
            self.hide()
            return

        if self.blocked_hover_widgets and not self.tip_window and not self.timer.isActive():
            self.schedule()

    def _is_blocked_hover(self):
        if not self.blocked_hover_widgets:
            return False

        cursor_pos = QCursor.pos()
        for widget in self.blocked_hover_widgets:
            local_pos = widget.mapFromGlobal(cursor_pos)
            if widget.rect().contains(local_pos):
                return True

        return False

    def _handle_hover_update(self):
        if not self.blocked_hover_widgets:
            self.schedule()
            return

        if not self.monitor_timer.isActive():
            self.monitor_timer.start()

        if self._is_blocked_hover():
            self.timer.stop()
            self._hide_tip_window()
            return

        if not self.tip_window and not self.timer.isActive():
            self.schedule()


# -------------------------------------------------------------
#  Tooltip wiring (UI → text mapping) [Qt version]
# -------------------------------------------------------------

def attach_tooltips(app):
    """
    Attach all tooltips to the EXEBuilderApp instance.
    Assumes widgets already exist on `app`.
    """

    # -----------------------------
    # Title / global controls
    # -----------------------------

    QtTooltip(
        app.tooltips_checkbox,
        "Toggle all tooltips on or off.\n"
        "Turn this off once you’re familiar with the interface."
    )
    
    QtTooltip(
        app.minimize_after_build,
        "If toggled the app will minimize after a build.\n"
        "Mutually excluse to the close after build toggle."
    )

    QtTooltip(
        app.open_output_dir_after_build,
        "Opens Output Directory after build if it output directory is not Desktop."

    )    

    QtTooltip(
        app.suppress_exit_dialogue,
        "Skip the exit confirmation popup when closing the app.\n"
        "When enabled, the native X close exits immediately."
    )

    QtTooltip(
        app.close_after_build,
        "If toggled the app will close after a build.\n"
        "Mutually excluse to the minimize after build toggle."
    )

    QtTooltip(
        app.open_app_data_btn,
        "Open the folder containing the app state file and saved settings."
    )

    # -----------------------------
    # Script picker
    # -----------------------------

    QtTooltip(
        app.open_python_site_btn,
        "Direct link to python.org."
    )

    QtTooltip(
        app.folder_btn,
        "Select a folder containing one or more Python files.\n"
        "If the folder contains only one .py file, it will be used automatically.\n"
        "If multiple .py files are found, a popup will appear.\n"
        "Allowing you to choose the main entry script."
    )
    
    QtTooltip(
        app.recent_folder_dropdown,
        "Select a recent python main file from this drop down list."
    )
    
    QtTooltip(
        app.delete_recent_folder,
        "Deletes current file in the path line output."
    )
    
    QtTooltip(
        app.delete_all_folders,
        "Deletes all saved files from the drop down."
    )

    # -----------------------------
    # Python interpreter
    # -----------------------------

    env_sync_summary = (
        "Environment Sync aligns detected Python profiles, but it does not guarantee\n"
        "package compatibility. If the build interpreter is missing required\n"
        "dependencies, the EXE build may fail. Some environments still may not\n"
        "sync if required packages are not compatible with that Python version."
    )

    QtTooltip(
        app.env_sync_title_frame,
        env_sync_summary,
    )

    QtTooltip(
        app.env_sync_frame,
        env_sync_summary,
        blocked_hover_widgets=[
            app.env_sync_scan_btn,
            app.env_sync_match_btn,
            app.env_sync_warning_label,
            app.env_sync_log_input,
        ],
    )

    QtTooltip(
        app.env_sync_warning_label,
        env_sync_summary,
    )

    QtTooltip(
        app.env_sync_log_input,
        "Shows Environment Sync scan progress, package install progress,\n"
        "and final sync results. This does not affect the EXE build status."
    )

    QtTooltip(
        app.env_sync_scan_btn,
        "Scans Python installs under AppData\\Local\\Programs\\Python.\n"
        "Compares installed package names and versions across all detected profiles."
    )

    QtTooltip(
        app.env_sync_match_btn,
        "Installs missing or mismatched packages so detected Python profiles converge\n"
        "toward the same union dependency state. This does not guarantee package\n"
        "compatibility; some packages may not install on every Python version."
    )

    QtTooltip(
        app.select_recent_icons,
        "Select a recent Icon from this drop down list."
    )

    QtTooltip(
        app.select_interpreter,
        "Select a recent python interpreter from this drop down list."
    )

    QtTooltip(
        app.python_delete_interpreter,
        "Deletes current interpreter in the path line output."
    )

    QtTooltip(
        app.python_delete_all_interpreter,
        "Deletes all interpreters from the drop down."
    )

    QtTooltip(
        app.interpreter_refresh_btn,
        "Clear selected interpreter."
    )

    QtTooltip(
        app.interpreter_btn,
        "Select the Python interpreter used to build EXEs.\n"
        "This determines which Python installation PyInstaller runs under."
    )

    # -----------------------------
    # Icon picker
    # -----------------------------

    QtTooltip(
        app.icon_btn,
        "Choose a .ico file to use as your EXE’s icon.\n"
        "Optional — PyInstaller uses a default icon otherwise."
    )

    QtTooltip(
        app.ico_convert_btn,
        "Opens 3 websites that convert PNG/JPG images into .ico files.\n"
        "For use as custom EXE icons."
    )

    QtTooltip(
        app.delete_recent_icons,
            "Deletes current icon in the path line output."
    )
    
    QtTooltip(
        app.delete_all_icons,
        "Deletes all Icons from the drop down."
    )
    
    QtTooltip(
        app.script_clear_btn,
        "Clear selected script/folder."
    ) 

    QtTooltip(
        app.icon_clear_btn,
        "Clear icon (build without an icon)."
    )

    QtTooltip(
        app.dotnet_icon_reset_btn,
        "Clear the optional .NET application icon. The next publish uses no custom icon."
    )

    # -----------------------------
    # Output / EXE name
    # -----------------------------

    QtTooltip(
        app.appened_py_version,
        "Append the python version to the file name."
    )

    QtTooltip(
        app.output_btn,
        "The file path to the folder the EXE is to be built in."
    )

    QtTooltip(
        app.date_time_dropdown,
        "Select a date/time format to append to the file name." 
        "\nFormats without minutes will overwrite builds from the same day." 
        "\nFormats including minutes usually produce a unique file per build." 
        "\nAs most builds take longer than a minute.\nIf a name is reused, wait briefly before rebuilding."
    )

    QtTooltip(
        app.output_refresh_btn,
        "Reset output folder to Desktop."
    )

    QtTooltip(
        app.exe_name_input,
        "Name of the generated EXE folder and file.\n"
        "Do not include .exe."
    )

    QtTooltip(
        app.refresh_btn,
        "Reset EXE name to match the entry script name.\n"
        "A python folder must be selected to for this to be ungryed and resettable.\n"
    )

    QtTooltip(
        app.build_btn,
        "Builds your Python project into a standalone Windows EXE using PyInstaller."
    )

