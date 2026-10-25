import os
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QCheckBox
from ..ui.styles import (
    APPEND_PY_VERSION_STYLE,
    BUILD_DISABLED_TITLE_FRAME_STYLE,
    Colors,
    DELETE_ALL_BUTTON_ICON,
    DELETE_ALL_BUTTON_ICON_SIZE,
    DELETE_ALL_BUTTON_TEXT,
    DELETE_BUTTON_ICON,
    DELETE_BUTTON_ICON_SIZE,
    DELETE_BUTTON_TEXT,
    ENV_SYNC_BUTTON_STYLE,
    ENV_SYNC_SCROLL_AREA_DISABLED_STYLE,
    ENV_SYNC_SCROLL_AREA_STYLE,
    ENV_SYNC_STATUS_LINE_STYLE,
    REFRESH_BUTTON_ICON,
    REFRESH_BUTTON_ICON_SIZE,
    REFRESH_BUTTON_TEXT,
    build_disabled_button,
    build_disabled_checkbox,
    build_disabled_checkbox_without_checkmark,
    build_disabled_line_edit_style,
    button_base,
    button_with_border,
    env_sync_disabled_status_line_style,
    filled_button,
    line_edit_style,
    qcolor_name,
    status_text_style,
    TITLE_FRAME_STYLE,
    UTILITY_ICON_BUTTON_SIZE,
    utility_icon_button_disabled_style,
    utility_icon_button_style,
)

class ValidationController:
    def __init__(self, app):
        """
        app = EXEBuilderApp instance
        """
        self.app = app
            
    def set_build_error(self, message: str):
        self.app.build_error = message
        self.validation_status_message()
        self.app.validator.update_ui_state()

    # ==================================================
    # Can we build again?
    # =================================================
    
    def inputs_are_valid(self):
        script = self.app.script_path_input.text().strip()
        outdir = self.app.output_path_input.text().strip()
        exe_name = self.app.exe_name_input.text().strip()
        python = getattr(self.app, "python_interpreter_path", "").strip()
        
        # 🔑 NORMALIZE
        script = os.path.normpath(script) if script else ""
        outdir = os.path.normpath(outdir) if outdir else ""
        python = os.path.normpath(python) if python else ""

        if not python or not os.path.isfile(python):
            return False

        if not script or not os.path.isfile(script):
            return False

        if not outdir or not os.path.isdir(outdir):
            return False

        if not exe_name:
            return False

        return True
    
    def validation_status_message(self):

        script = os.path.normpath(self.app.script_path_input.text().strip() or "")
        outdir = os.path.normpath(self.app.output_path_input.text().strip() or "")
        exe_name = self.app.exe_name_input.text().strip()
        python = os.path.normpath(getattr(self.app, "python_interpreter_path", "") or "")
        icon_path = os.path.normpath(getattr(self.app, "icon_path", "").strip() or "")

        # -------------------------------
        # STATE
        # -------------------------------
        state = {}

        script_ok = bool(script and os.path.isfile(script))
        outdir_ok = bool(outdir and os.path.isdir(outdir))
        exe_ok = bool(exe_name)
        python_ok = bool(python and os.path.isfile(python))
        icon_ok = bool(icon_path and os.path.isfile(icon_path))

        state.update({
            "script_ok": script_ok,
            "outdir_ok": outdir_ok,
            "exe_ok": exe_ok,
            "python_ok": python_ok,
            "icon_ok": icon_ok,
            "output_ok": outdir_ok,
        })

        # -------------------------------
        # BUILD READINESS
        # -------------------------------
        is_ready = script_ok and outdir_ok and exe_ok and python_ok

        if getattr(self.app, "build_error", None):
            is_ready = False

        state["is_ready"] = is_ready

        self.app.status_label.setFixedSize(250, 80)

        # Track previous state
        self.app._was_build_ready = is_ready
                # Track previous state
        self.app._was_build_ready = is_ready
                
        # --------------------------------
        # STATUS TEXT
        # --------------------------------

        # Python version (Py 3.14)
        python_path = python
        python_version = "Unknown"
        if python_path:
            parent = os.path.basename(os.path.dirname(python_path))
            if parent.lower().startswith("python"):
                raw = parent.lower().replace("python", "")
                if raw.isdigit():
                    python_version = f"{raw[0]}.{raw[1:]}" if len(raw) > 1 else raw
                    
        # Icon (name or Default)
        icon_display = os.path.basename(icon_path) if icon_path else "Default - (No User Icon)"

        # Script (parent\file)
        script_display = "No script"
        if script:
            name = os.path.basename(script)
            parent = os.path.basename(os.path.dirname(script))
            script_display = f"{parent}\\{name}" if parent else name

        # EXE name
        exe_name_display = exe_name if exe_name else "No EXE name"

        # Output path
        outdir_display = outdir if outdir else "No output"
        error_msg = getattr(self.app, "build_error", None)
        
        if error_msg:
            state["status_text"] = error_msg
            is_ready = False  # 🔑 force red + stop READY logic
        state["status_text"] = (
            f"READY — Py {python_version} | {icon_display} |\n"
            f"{script_display} |\n"
            f"{outdir_display} |{exe_name_display}"
            
            if is_ready else
            (
                error_msg if error_msg else
                "NOT READY\n"
                "TO BUILD"
            )
        )
        
        return state

    def update_ui_state(self):
        app = self.app
        building = getattr(app, "building", False)

        if hasattr(app, "_update_section_navigation_enabled"):
            app._update_section_navigation_enabled()

        if hasattr(app, "_apply_build_mode_button_state"):
            app._apply_build_mode_button_state(getattr(app, "build_mode", "python"))

        # -------------------------------
        # INPUT STATES
        # -------------------------------
        script = getattr(app, "entry_script", "")
        script_ok = bool(script and os.path.isfile(script))

        outdir = app.output_path_input.text().strip()
        outdir = os.path.normpath(outdir) if outdir else ""

        desktop = os.path.normpath(os.path.join(os.path.expanduser("~"), "Desktop"))
        is_desktop = bool(
            outdir
            and os.path.normcase(outdir) == os.path.normcase(desktop)
        )

        python_path = getattr(app, "python_interpreter_path", "").strip()
        python_ok = bool(python_path and os.path.isfile(python_path))

        icon_path = getattr(app, "icon_path", "").strip()
        exe_name = app.exe_name_input.text().strip()

        python_path = getattr(app, "python_interpreter_path", "").strip()

        is_ready = (
            script_ok and
            outdir and os.path.isdir(outdir) and
            python_ok and
            exe_name
        )

        # -------------------------------
        # BUTTON HELPER
        # -------------------------------
        def is_utility_icon_button(btn):
            return btn in (
                getattr(app, "delete_recent_icons", None),
                getattr(app, "delete_recent_folder", None),
                getattr(app, "delete_all_icons", None),
                getattr(app, "delete_all_folders", None),
                getattr(app, "python_delete_all_interpreter", None),
                getattr(app, "python_delete_interpreter", None),
                getattr(app, "refresh_btn", None),
                getattr(app, "output_refresh_btn", None),
                getattr(app, "icon_clear_btn", None),
                getattr(app, "script_clear_btn", None),
                getattr(app, "interpreter_refresh_btn", None),
            )

        def is_delete_button(btn):
            return btn in (
                getattr(app, "delete_recent_icons", None),
                getattr(app, "delete_recent_folder", None),
                getattr(app, "python_delete_interpreter", None),
            )

        def is_delete_all_button(btn):
            return btn in (
                getattr(app, "delete_all_icons", None),
                getattr(app, "delete_all_folders", None),
                getattr(app, "python_delete_all_interpreter", None),
            )

        def is_refresh_button(btn):
            return btn in (
                getattr(app, "refresh_btn", None),
                getattr(app, "output_refresh_btn", None),
                getattr(app, "icon_clear_btn", None),
                getattr(app, "script_clear_btn", None),
                getattr(app, "interpreter_refresh_btn", None),
            )

        def uses_empty_selection_disabled_style(btn):
            """Return whether an empty path should visibly disable this action."""
            return btn in (
                getattr(app, "delete_recent_icons", None),
                getattr(app, "delete_recent_folder", None),
                getattr(app, "python_delete_interpreter", None),
                getattr(app, "icon_clear_btn", None),
                getattr(app, "script_clear_btn", None),
                getattr(app, "interpreter_refresh_btn", None),
            )

        def set_button_icon(btn, visible, icon_path, icon_size, text):
            if hasattr(btn, "setFixedSize"):
                btn.setFixedSize(*UTILITY_ICON_BUTTON_SIZE)
            if visible:
                if hasattr(btn, "setIcon"):
                    btn.setIcon(QIcon(str(icon_path)))
                if hasattr(btn, "setIconSize"):
                    btn.setIconSize(QSize(*icon_size))
                btn.setText(text)
            else:
                if hasattr(btn, "setIcon"):
                    btn.setIcon(QIcon())
                btn.setText("")

        def set_delete_button_icon(btn, visible):
            set_button_icon(
                btn,
                visible,
                DELETE_BUTTON_ICON,
                DELETE_BUTTON_ICON_SIZE,
                DELETE_BUTTON_TEXT,
            )

        def set_delete_all_button_icon(btn, visible):
            set_button_icon(
                btn,
                visible,
                DELETE_ALL_BUTTON_ICON,
                DELETE_ALL_BUTTON_ICON_SIZE,
                DELETE_ALL_BUTTON_TEXT,
            )

        def set_refresh_button_icon(btn, visible):
            set_button_icon(
                btn,
                visible,
                REFRESH_BUTTON_ICON,
                REFRESH_BUTTON_ICON_SIZE,
                REFRESH_BUTTON_TEXT,
            )

        def set_btn(btn, enabled, color=None):
            btn.setEnabled(enabled)

            if not enabled:
                if isinstance(btn, QCheckBox):
                    btn.setStyleSheet(build_disabled_checkbox())
                elif btn in (
                    getattr(app, "refresh_btn", None),
                    getattr(app, "output_refresh_btn", None),
                ):
                    btn.setStyleSheet(build_disabled_button())
                elif uses_empty_selection_disabled_style(btn):
                    btn.setStyleSheet(build_disabled_button())
                elif is_utility_icon_button(btn):
                    btn.setStyleSheet(utility_icon_button_disabled_style(building))
                elif building:
                    btn.setStyleSheet(build_disabled_button())
                else:
                    btn.setStyleSheet(button_base(border_width=4))
            elif color:
                btn.setStyleSheet(button_with_border(color))
            else:
                if isinstance(btn, QCheckBox):
                    btn.setStyleSheet("")
                    return
                if is_utility_icon_button(btn):
                    btn.setStyleSheet(utility_icon_button_style())
                else:
                    btn.setStyleSheet(button_base(border_width=4))

        # -------------------------------
        # VALUE STATE (TEXT-BASED)
        # -------------------------------
        icon_has_value = bool(getattr(app, "icon_path", "").strip())
        script_has_value = bool(getattr(app, "script_path", "").strip())
        interpreter_has_value = bool(getattr(app, "python_interpreter_path", "").strip())

        # -------------------------------
        # RECENTS STATE (JSON-backed)
        # -------------------------------
        recent_scripts = app.state_data.get("recent_scripts", [])
        recent_icons = app.state_data.get("recent_icons", [])
        recent_interpreters = app.state_data.get("recent_interpreters", [])

        has_recent_scripts = bool(recent_scripts)
        has_recent_icons = bool(recent_icons)
        has_recent_interpreters = bool(recent_interpreters)

        # -------------------------------
        # DELETE + DELETE ALL BUTTONS
        # -------------------------------

        # ICON
        icon_enabled = not building and icon_has_value
        set_btn(app.delete_recent_icons, icon_enabled)
        set_delete_button_icon(app.delete_recent_icons, icon_enabled)

        # SCRIPT
        script_enabled = not building and script_has_value
        set_btn(app.delete_recent_folder, script_enabled)
        set_delete_button_icon(app.delete_recent_folder, script_enabled)

        # INTERPRETER
        interpreter_enabled = not building and interpreter_has_value

        set_btn(app.python_delete_interpreter, interpreter_enabled)
        set_delete_button_icon(app.python_delete_interpreter, interpreter_enabled)

        delete_all_icons_enabled = not building and has_recent_icons
        delete_all_folders_enabled = not building and has_recent_scripts
        delete_all_interpreters_enabled = not building and has_recent_interpreters

        set_btn(app.delete_all_icons, delete_all_icons_enabled)
        set_delete_all_button_icon(app.delete_all_icons, delete_all_icons_enabled)

        set_btn(app.delete_all_folders, delete_all_folders_enabled)
        set_delete_all_button_icon(app.delete_all_folders, delete_all_folders_enabled)

        set_btn(app.python_delete_all_interpreter, delete_all_interpreters_enabled)
        set_delete_all_button_icon(
            app.python_delete_all_interpreter,
            delete_all_interpreters_enabled,
        )
                        
        # Tooltips
        for name in ("build_options_btn", "dotnet_build_options_btn"):
            if hasattr(app, name):
                set_btn(getattr(app, name), not building)
        set_btn(app.tooltips_checkbox, not building)
        if hasattr(app, "suppress_exit_dialogue"):
            set_btn(app.suppress_exit_dialogue, not building)
        if hasattr(app, "open_app_data_btn"):
            set_btn(app.open_app_data_btn, not building)
        set_btn(app.open_output_dir_after_build, not building and not is_desktop)
        if is_desktop:
            app.open_output_dir_after_build.setStyleSheet(
                build_disabled_checkbox_without_checkmark()
            )
        # 🔑 mutual exclusion + build lock
        min_checked = app.minimize_after_build.isChecked()
        close_checked = app.close_after_build.isChecked()

        set_btn(
            app.minimize_after_build,
            not building and not close_checked
        )

        set_btn(
            app.close_after_build,
            not building and not min_checked
        )

        # Apps
        env_sync_controller = getattr(app, "environment_sync_controller", None)
        env_sync_running = bool(getattr(env_sync_controller, "is_running", False))

        if hasattr(app, "env_sync_scan_btn"):
            app.env_sync_scan_btn.setEnabled(not building and not env_sync_running)

        if hasattr(app, "env_sync_match_btn"):
            sync_plan = getattr(
                env_sync_controller,
                "last_plan",
                None,
            )
            app.env_sync_match_btn.setEnabled(
                not building
                and not env_sync_running
                and bool(sync_plan and sync_plan.total_actions > 0),
            )

        if hasattr(app, "env_sync_help_btn"):
            app.env_sync_help_btn.setEnabled(not building)

        set_btn(app.open_python_site_btn, not building)
        set_btn(app.interpreter_btn, not building)
        set_btn(app.interpreter_refresh_btn, not building and python_ok)
        app.select_interpreter.setEnabled(not building)

        # -------------------------------
        # ICON SECTION
        # -------------------------------
        set_btn(app.icon_btn, not building)
        set_btn(app.icon_clear_btn, not building and icon_has_value)
        set_btn(app.ico_convert_btn, not building)
        app.select_recent_icons.setEnabled(not building)

        # -------------------------------
        # FILE SECTION
        # -------------------------------
        set_btn(app.folder_btn, not building)
        set_btn(app.script_clear_btn, not building and script_has_value)
        app.recent_folder_dropdown.setEnabled(not building)

        # -------------------------------
        # OUTPUT SECTION
        # -------------------------------
        set_btn(app.appened_py_version, not building)
        set_btn(app.output_btn, not building)
        app.date_time_dropdown.setEnabled(not building)

        python_open_output_btn = getattr(app, "python_open_output_btn", None)
        if python_open_output_btn is not None:
            output_available = (
                not building
                and getattr(app, "build_controller", None) is not None
                and app.build_controller.has_python_output()
            )
            python_open_output_btn.setEnabled(output_available)
            python_open_output_btn.setStyleSheet(
                button_base() if output_available else build_disabled_button()
            )

        set_btn(app.output_refresh_btn, not building and not is_desktop)

        # -------------------------------
        # EXE NAME REFRESH (revert to script name)
        # -------------------------------
        derived_name = ""

        if script_ok:
            derived_name = os.path.splitext(os.path.basename(script))[0].strip().lower()

        current_name = app.exe_name_input.text().strip().lower()

        can_revert_name = bool(
            derived_name and
            current_name != derived_name
        )

        set_btn(app.refresh_btn, not building and can_revert_name)
        app.exe_name_input.setReadOnly(building)

        # -------------------------------
        # BUTTON COLOR: Python Interpreter
        # -------------------------------

        if building:
            app.interpreter_btn.setStyleSheet(build_disabled_button())
        else:
            if python_ok:
                app.interpreter_btn.setStyleSheet(filled_button(Colors.SUCCESS))
            else:
                app.interpreter_btn.setStyleSheet(filled_button(Colors.ERROR))

        # -------------------------------
        # BUTTON COLOR: Script Folder
        # -------------------------------

        folder_ok = bool(script_ok)

        if building:
            app.folder_btn.setStyleSheet(build_disabled_button())
        else:
            if folder_ok:
                app.folder_btn.setStyleSheet(filled_button(Colors.SUCCESS))
            else:
                app.folder_btn.setStyleSheet(filled_button(Colors.ERROR))

        # -------------------------------
        # BUTTON COLOR: Output Folder
        # -------------------------------

        output_ok = bool(outdir and os.path.isdir(outdir))

        if building:
            app.output_btn.setStyleSheet(build_disabled_button())
        else:
            if output_ok:
                app.output_btn.setStyleSheet(filled_button(Colors.SUCCESS))
            else:
                app.output_btn.setStyleSheet(filled_button(Colors.ERROR))

        # -------------------------------
        # STATUS ONLY (lock applies here ONLY)
        # -------------------------------
        if getattr(app, "_status_lock", False):
            return

        if building:
            status_text = "Building..."

        elif is_ready:
            status_text = (
                "A build already exists here. Build again to overwrite it, "
                "or choose another output folder."
                if output_available else "Ready to build."
            )
        else:
            status_text = "Missing required inputs."

        app.status_label.setText(status_text)
        app.status_label.setAlignment(Qt.AlignCenter)

        if building:
            color = Colors.BLACK
        elif status_text.startswith("Building..."):
            color = Colors.BLACK if "complete" in status_text.lower() else Colors.ERROR
        elif is_ready:
            color = Colors.SUCCESS
        else:
            color = Colors.ERROR

        app.status_label.setStyleSheet(status_text_style(color))

        if building:
            app.status_label.setStyleSheet(status_text_style(Colors.SUCCESS))

        section_title_frames = [
            getattr(app, "title_frame", None),
            getattr(app, "env_sync_title_frame", None),
            getattr(app, "apps_title_frame", None),
            getattr(app, "icons_title_frame", None),
            getattr(app, "python_title_frame", None),
            getattr(app, "output_title_frame", None),
        ]

        for frame in section_title_frames:
            if frame:
                frame.setStyleSheet(
                    BUILD_DISABLED_TITLE_FRAME_STYLE if building else TITLE_FRAME_STYLE
                )

        # -------------------------------
        # ENVIRONMENT SYNC GREY STATE
        # -------------------------------
        for btn in [
            getattr(app, "env_sync_scan_btn", None),
            getattr(app, "env_sync_match_btn", None),
            getattr(app, "env_sync_help_btn", None),
        ]:
            if btn:
                btn.setStyleSheet(
                    build_disabled_button() if building else ENV_SYNC_BUTTON_STYLE
                )

        if hasattr(app, "env_sync_log_input"):
            app.env_sync_log_input.setStyleSheet(
                env_sync_disabled_status_line_style()
                if building
                else ENV_SYNC_STATUS_LINE_STYLE
            )

        if hasattr(app, "env_sync_rows_scroll_area"):
            app.env_sync_rows_scroll_area.setStyleSheet(
                ENV_SYNC_SCROLL_AREA_DISABLED_STYLE
                if building
                else ENV_SYNC_SCROLL_AREA_STYLE
            )
            for scrollbar in (
                app.env_sync_rows_scroll_area.verticalScrollBar(),
                app.env_sync_rows_scroll_area.horizontalScrollBar(),
            ):
                scrollbar.setEnabled(not building)

        env_sync_label_color = (
            Colors.BUILD_DISABLED_TEXT if building else Colors.TEXT_LIGHT
        )
        env_sync_label_style = (
            f"QLabel {{ color: {qcolor_name(env_sync_label_color)}; }}"
        )

        env_sync_labels = []
        for attr in [
            "env_sync_status_labels",
            "env_sync_row_labels",
        ]:
            widgets = getattr(app, attr, None)
            if widgets is None:
                continue
            if isinstance(widgets, list):
                env_sync_labels.extend(widgets)
            else:
                env_sync_labels.append(widgets)

        for label in env_sync_labels:
            if label:
                label.setStyleSheet(env_sync_label_style)

        env_sync_warning_label = getattr(app, "env_sync_warning_label", None)
        if env_sync_warning_label:
            env_sync_warning_color = (
                Colors.BUILD_DISABLED_TEXT if building else Colors.WARNING
            )
            env_sync_warning_label.setStyleSheet(
                f"QLabel {{ color: {qcolor_name(env_sync_warning_color)}; }}"
            )

        # -------------------------------
        # ICON BUTTON TEXT (match grey state)
        # -------------------------------
        icon_buttons = [
            app.delete_recent_icons,
            app.delete_recent_folder,
            app.delete_all_icons,
            app.delete_all_folders,
            app.python_delete_all_interpreter,
            app.python_delete_interpreter,
            app.refresh_btn,
            app.output_refresh_btn,
            app.icon_clear_btn,
            app.script_clear_btn,
            app.interpreter_refresh_btn,
        ]

        for btn in icon_buttons:
            if building:
                if is_delete_button(btn):
                    set_delete_button_icon(btn, False)
                elif is_delete_all_button(btn):
                    set_delete_all_button_icon(btn, False)
                elif is_refresh_button(btn):
                    set_refresh_button_icon(btn, False)
                else:
                    btn.setText("")
            else:
                # DELETE BUTTONS → respect actual state
                if btn == app.delete_recent_icons:
                    set_delete_button_icon(btn, icon_has_value)
                elif btn == app.delete_recent_folder:
                    set_delete_button_icon(btn, script_has_value)
                elif btn == app.python_delete_interpreter:
                    set_delete_button_icon(btn, interpreter_has_value)

                elif btn == app.delete_all_icons:
                    set_delete_all_button_icon(btn, has_recent_icons)
                elif btn == app.delete_all_folders:
                    set_delete_all_button_icon(btn, has_recent_scripts)
                elif btn == app.python_delete_all_interpreter:
                    set_delete_all_button_icon(btn, has_recent_interpreters)

                # REFRESH / CLEAR (state-driven)
                elif btn == app.interpreter_refresh_btn:
                    set_refresh_button_icon(btn, interpreter_has_value)
                elif btn == app.script_clear_btn:
                    set_refresh_button_icon(btn, script_has_value)
                elif btn == app.icon_clear_btn:
                    set_refresh_button_icon(btn, icon_has_value)
                elif btn == app.output_refresh_btn:
                    set_refresh_button_icon(btn, not is_desktop)
                elif btn == app.refresh_btn:
                    set_refresh_button_icon(btn, can_revert_name)
                            
        # -------------------------------
        # LOCK + GREY INPUTS DURING BUILD
        # -------------------------------

        script = app.script_path_input.text().strip()
        outdir = app.output_path_input.text().strip()
        python_path = getattr(app, "python_interpreter_path", "").strip()
        exe_name = app.exe_name_input.text().strip()
        icon_path = getattr(app, "icon_path", "").strip()

        script_ok = bool(script and os.path.isfile(os.path.normpath(script)))
        outdir_ok = bool(outdir and os.path.isdir(os.path.normpath(outdir)))
        python_ok = bool(python_path and os.path.isfile(os.path.normpath(python_path)))
        exe_ok = bool(exe_name)
        icon_ok = bool(icon_path and os.path.isfile(os.path.normpath(icon_path)))

        # -------------------------------
        # LOCK + GREY (respect validation)
        # -------------------------------
        state = self.validation_status_message()

        path_mapping = [
            (app.python_entry_input, state["python_ok"]),
            (app.script_path_input, state["script_ok"]),
            (app.output_path_input, state["outdir_ok"]),
            (app.icon_path_input, state["icon_ok"]),
        ]

        validation_mapping = path_mapping + [
            (app.exe_name_input, state["exe_ok"]),
        ]

        # -------------------------------
        # BUILD MODE → force grey
        # -------------------------------
        if building:
            for widget, _ in path_mapping:
                widget.setStyleSheet(build_disabled_line_edit_style())

            app.exe_name_input.setStyleSheet(build_disabled_line_edit_style())
        else:
            for widget, ok in validation_mapping:

                widget.setStyleSheet("")  # reset first

                # 🔑 ICON (optional → grey if empty)
                if widget is app.icon_path_input and not widget.text().strip():
                    widget.setStyleSheet(line_edit_style(Colors.MUTED_BORDER))

                elif widget is app.output_path_input and not widget.text().strip():
                    # output = required → force RED if empty
                    widget.setStyleSheet(line_edit_style(Colors.ERROR))

                elif ok:
                    widget.setStyleSheet(line_edit_style(Colors.SUCCESS))
                else:
                    widget.setStyleSheet(line_edit_style(Colors.ERROR))

            # 🔑 THEN reapply validation styling
            self.validation_status_message()
        self.update_build_button()

    def update_build_button(self):
        app = self.app

        if not hasattr(app, "build_btn"):
            return

        state = self.validation_status_message()
        building = getattr(app, "building", False)
        is_ready = state["is_ready"]

        def set_btn(btn, enabled, color=None):
            # 🔑 skip styling for toggle button
            if btn is self.app.appened_py_version:
                return
            btn.setEnabled(enabled)
            if color:
                btn.setStyleSheet(filled_button(color, radius=5))
        try:
            app.build_btn.clicked.disconnect()
        except:
            pass

        if building:
            set_btn(app.build_btn, True, Colors.CANCEL)
            app.build_btn.setText("Cancel EXE")
            app.build_btn.clicked.connect(app.build_cancellation.cancel_build)

        else:
            if is_ready:
                set_btn(app.build_btn, True, Colors.SUCCESS)
            else:
                set_btn(app.build_btn, False, Colors.ERROR)

            app.build_btn.setText("Build EXE")
            app.build_btn.clicked.connect(app.build_controller.build_exe)


        # 🔑 restore toggle styling (it gets wiped during validation cycles)
        app.appened_py_version.setStyleSheet(APPEND_PY_VERSION_STYLE)

