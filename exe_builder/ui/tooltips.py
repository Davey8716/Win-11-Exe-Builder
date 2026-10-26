from PySide6.QtCore import QObject, QEvent, QTimer, QPoint
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import Qt, QCursor
from .path_hover import PathHover
from .styles import TOOLTIP_STYLE


PYTHON_SUMMARY_HELP_TEXT = {
    "interpreter": (
        "Displays the full path to the Python interpreter.\n"
        "That will be used for building EXEs.\n"
        "This is read only.\n"
        "Once a path has been set the navigation is locked to where pyton interpreters are.\n"
    ),
    "icon": "File path to Icon if used.",
    "file": "File path to python script folder and file.",
    "output": "File path to the EXE output folder.",
    "name": "Name of the generated EXE folder and file.\nDo not include .exe.",
    "python_version": "Append the python version to the file name.",
    "datetime": (
        "Select a date/time format to append to the file name.\n"
        "Formats without minutes will overwrite builds from the same day.\n"
        "Formats including minutes usually produce a unique file per build.\n"
        "As most builds take longer than a minute.\nIf a name is reused, wait briefly before rebuilding."
    ),
}

DOTNET_SUMMARY_HELP_TEXT = {
    "project": "File path to the selected SDK-style C# project file.",
    "icon": "File path to the optional application icon used for this publish.",
    "output": "File path to the folder that will receive the C# publish output.",
    "name": "Set the published executable name. Do not include .exe.",
    "runtime": "Choose the Windows architecture for the published application.",
    "datetime": PYTHON_SUMMARY_HELP_TEXT["datetime"],
}

DOTNET_SELECTION_SUMMARY_HELP_TEXT = {
    "icon": DOTNET_SUMMARY_HELP_TEXT["icon"],
    "file": DOTNET_SUMMARY_HELP_TEXT["project"],
}

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
        position_at_cursor=False,
    ):
        super().__init__(widget)

        self.widget = widget
        self.text = text
        self.delay = delay
        self.direct_widget_only = direct_widget_only
        self.ignored_hover_children = set(ignored_hover_children or [])
        self.blocked_hover_widgets = set(blocked_hover_widgets or [])
        self.position_at_cursor = position_at_cursor

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

        text = self.text() if callable(self.text) else self.text
        if not text:
            return

        if self.tip_window:
            return

        self.tip_window = QLabel(text, None)
        self.tip_window.setWindowFlags(
            Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )

        # Styling (qt_material-friendly)
        self.tip_window.setStyleSheet(TOOLTIP_STYLE)

        self.tip_window.adjustSize()

        # Position relative to widget (same offsets as before)
        pos = (
            QCursor.pos() + QPoint(16, 18)
            if self.position_at_cursor else self.widget.mapToGlobal(QPoint(40, 25))
        )
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
        if self.tip_window:
            text = self.text() if callable(self.text) else self.text
            if text != self.tip_window.text():
                self._hide_tip_window()

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

def attach_section_nav_tooltips(nav, descriptions):
    """Show the description for the sidebar row under the pointer."""
    viewport = nav.viewport()
    viewport.setMouseTracking(True)

    def hovered_description():
        item = nav.itemAt(viewport.mapFromGlobal(QCursor.pos()))
        return descriptions.get(item.text(), "") if item else ""

    QtTooltip(viewport, hovered_description, position_at_cursor=True)


def attach_tooltips(app):
    """
    Attach all tooltips to the EXEBuilderApp instance.
    Assumes widgets already exist on `app`.
    """

    # -----------------------------
    # Title / global controls
    # -----------------------------

    QtTooltip(
        app.build_options_btn,
        "Open build options and application preferences."
    )

    attach_section_nav_tooltips(app.python_section_nav, {
        "Environment Sync": "Compare and sync packages across detected Python installations.",
        "Interpreter": "Choose the Python installation used to build the EXE.",
        "Icons": "Choose an optional icon for the EXE.",
        "File": "Select the Python script to run when the EXE starts.",
        "Output": "Choose the output folder and name the EXE.",
        "Build": "Review the settings, save a setup, and build the EXE.",
    })
    attach_section_nav_tooltips(app.dotnet_section_nav, {
        "Icons": "Choose an optional icon for the published app.",
        "File": "Select the C# project file to publish.",
        "Output": "Choose the publish folder and name the executable.",
        "Build": "Choose publish options and build the C# app.",
    })

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
        app.run_built_app_after_build,
        "Launch the executable that was just built after a successful build."
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
            app.env_sync_help_btn,
            app.env_sync_warning_label,
            app.env_sync_log_input,
        ],
    )

    QtTooltip(
        app.env_sync_help_btn,
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

    QtTooltip(app.appened_py_version, PYTHON_SUMMARY_HELP_TEXT["python_version"])

    QtTooltip(
        app.output_btn,
        "The file path to the folder the EXE is to be built in."
    )

    QtTooltip(app.date_time_dropdown, PYTHON_SUMMARY_HELP_TEXT["datetime"])

    QtTooltip(
        app.output_refresh_btn,
        "Reset output folder to Desktop."
    )

    QtTooltip(app.exe_name_input, PYTHON_SUMMARY_HELP_TEXT["name"])

    QtTooltip(
        app.refresh_btn,
        "Reset EXE name to match the entry script name.\n"
        "A python folder must be selected to for this to be ungryed and resettable.\n"
    )

    QtTooltip(
        app.build_btn,
        "Builds your Python project into a standalone Windows EXE using PyInstaller."
    )

    QtTooltip(
        app.python_open_output_btn,
        "Open the latest complete Python build folder for the current EXE name. "
        "Available only when that folder contains its generated EXE."
    )

    attach_saved_setup_tooltips(app, "python")
    attach_dotnet_tooltips(app)
    attach_summary_hovers(app)


def attach_summary_hovers(app):
    """Attach value-plus-guidance hovers to every read-only summary value."""
    tooltips_enabled = lambda: getattr(app, "tooltips_enabled", True)
    summaries = (
        (app.build_summary_values, PYTHON_SUMMARY_HELP_TEXT),
        (app.dotnet_build_summary_values, DOTNET_SUMMARY_HELP_TEXT),
    )
    summaries += tuple(
        (values, PYTHON_SUMMARY_HELP_TEXT)
        for _title, _frame, _labels, values in app.python_selection_summaries.values()
    )
    summaries += tuple(
        (values, DOTNET_SELECTION_SUMMARY_HELP_TEXT)
        for _title, _frame, _labels, values in app.dotnet_selection_summaries.values()
    )
    app._summary_hovers = [
        PathHover(
            widget,
            help_text=help_text[key],
            help_enabled_getter=tooltips_enabled,
            normalize_path=False,
        )
        for values, help_text in summaries
        for key, widget in values.items()
    ]


def attach_saved_setup_tooltips(app, mode):
    """Register help for saved-setup controls in a build mode."""

    if mode == "python":
        tooltip_text = {
            "saved_build_setup_dropdown": (
                "Choose a saved setup to fill the build fields, then click Build EXE."
            ),
            "save_build_setup_btn": (
                "Save the current Python build settings as a setup you can restore later."
            ),
            "export_python_build_setups_btn": (
                "Export saved Python build setups to a JSON backup file."
            ),
            "import_python_build_setups_btn": (
                "Import saved Python build setups from a JSON backup file. "
                "Imported setups are added to your current list."
            ),
            "delete_build_setup_btn": (
                "Delete the selected saved Python build setup. Use the arrow to delete "
                "all saved Python build setups."
            ),
        }
    else:
        tooltip_text = {
            "saved_dotnet_build_setup_dropdown": (
                "Choose a saved setup to fill the publish fields, then click Publish."
            ),
            "dotnet_save_build_setup_btn": (
                "Save the current C# publish settings as a setup you can restore later."
            ),
            "export_dotnet_build_setups_btn": (
                "Export saved C# publish setups to a JSON backup file."
            ),
            "import_dotnet_build_setups_btn": (
                "Import saved C# publish setups from a JSON backup file. "
                "Imported setups are added to your current list."
            ),
            "dotnet_delete_build_setup_btn": (
                "Delete the selected saved C# publish setup. Use the arrow to delete all "
                "saved C# publish setups."
            ),
        }

    for name, text in tooltip_text.items():
        QtTooltip(getattr(app, name), text)


def attach_dotnet_tooltips(app):
    """Register help for controls shown by the C# .NET Publish mode."""

    tooltip_text = {
        "dotnet_project_select_btn": "Select the SDK-style C# project file (.csproj) to publish.",
        "dotnet_recent_projects": "Choose a recently used C# project file.",
        "dotnet_project_delete_btn": "Remove the selected project from the recent-project list.",
        "dotnet_project_delete_all_btn": "Remove all saved C# projects from the recent-project list.",
        "dotnet_project_reset_btn": "Clear the selected C# project.",
        "dotnet_icon_select_btn": "Choose an optional .ico file for the published application.",
        "dotnet_ico_convert_btn": "Open online tools for converting an image to an .ico file.",
        "dotnet_recent_icons": "Choose a recently used application icon, or select No Icon.",
        "dotnet_icon_delete_btn": "Remove the selected icon from the recent-icon list.",
        "dotnet_icon_delete_all_btn": "Remove all saved icons from the recent-icon list.",
        "dotnet_icon_reset_btn": "Clear the optional application icon for the next publish.",
        "dotnet_output_select_btn": "Choose the folder where the Release publish output will be created.",
        "dotnet_output_reset_btn": "Reset the publish output folder to Desktop.",
        "dotnet_name_input": DOTNET_SUMMARY_HELP_TEXT["name"],
        "dotnet_name_reset_btn": "Reset the executable name to match the selected C# project.",
        "dotnet_runtime_combo": DOTNET_SUMMARY_HELP_TEXT["runtime"],
        "dotnet_self_contained": (
            "Include the .NET runtime in the publish output. This runs without a separate "
            ".NET install but increases output size."
        ),
        "dotnet_single_file": (
            "Bundle the application into a single executable where supported. Startup and "
            "runtime extraction behavior can vary by application."
        ),
        "dotnet_trim": (
            "Remove unused framework code to reduce size. Test carefully if the application "
            "uses reflection or dynamic loading."
        ),
        "dotnet_status_label": "Shows C# publish readiness, progress, success, and failure messages.",
        "dotnet_publish_btn": "Clean and publish the selected C# project in Release configuration.",
        "dotnet_open_output_btn": (
            "Open the current C# publish output folder in File Explorer. Available only when "
            "the current published EXE exists."
        ),
        "dotnet_mode_btn": "Switch to the C# .NET Publish workflow.",
    }

    for name, text in tooltip_text.items():
        QtTooltip(getattr(app, name), text)

    attach_saved_setup_tooltips(app, "dotnet")

    tooltips_enabled = lambda: getattr(app, "tooltips_enabled", True)
    app._dotnet_path_hovers = [
        PathHover(
            app.dotnet_project_input,
            help_text=DOTNET_SUMMARY_HELP_TEXT["project"],
            help_enabled_getter=tooltips_enabled,
        ),
        PathHover(
            app.dotnet_icon_input,
            help_text=DOTNET_SUMMARY_HELP_TEXT["icon"],
            help_enabled_getter=tooltips_enabled,
        ),
        PathHover(
            app.dotnet_output_input,
            help_text=DOTNET_SUMMARY_HELP_TEXT["output"],
            help_enabled_getter=tooltips_enabled,
        ),
    ]

