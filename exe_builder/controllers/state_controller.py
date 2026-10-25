import json
import os

from ..build.datetime_build_options import (
    ISO_MASS_DATETIME_BUILD_SENTINEL,
    MASS_DATETIME_BUILD_SENTINEL,
    NO_DATETIME_LABEL as DATETIME_NO_DATETIME_LABEL,
    UK_MASS_DATETIME_BUILD_SENTINEL,
    USA_MASS_DATETIME_BUILD_SENTINEL,
)


class StateController:
    """Persists Python and C# workflows independently."""

    NO_DATETIME_LABEL = DATETIME_NO_DATETIME_LABEL
    PYTHON_FILENAME = "python_exe_builder_state.json"
    CSHARP_FILENAME = "csharp_exe_builder_state.json"
    PREFERENCES_FILENAME = "exe_builder_preferences.json"
    LEGACY_FILENAME = "exe_builder_state.json"

    def __init__(self, app):
        self.app = app
        self.last_build_counter = 0

    def _state_dir(self):
        path = os.path.join(os.getenv("LOCALAPPDATA") or os.path.expanduser("~"), "EXEBuilder")
        os.makedirs(path, exist_ok=True)
        return path

    def python_state_file_path(self):
        return os.path.join(self._state_dir(), self.PYTHON_FILENAME)

    def csharp_state_file_path(self):
        return os.path.join(self._state_dir(), self.CSHARP_FILENAME)

    def preferences_file_path(self):
        return os.path.join(self._state_dir(), self.PREFERENCES_FILENAME)

    def legacy_state_file_path(self):
        return os.path.join(self._state_dir(), self.LEGACY_FILENAME)

    def _state_file_path(self):
        """Compatibility path for Python recents and JSON drag-and-drop import."""
        return self.python_state_file_path()

    @staticmethod
    def _read(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                value = json.load(handle)
            return value if isinstance(value, dict) else {}
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _write(path, value):
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(value, handle, indent=4)
        except OSError as exc:
            print("State save error:", exc)

    def _migrate_legacy_state(self):
        legacy_path = self.legacy_state_file_path()
        new_paths = (self.python_state_file_path(), self.csharp_state_file_path(), self.preferences_file_path())
        if not os.path.isfile(legacy_path) or any(os.path.isfile(path) for path in new_paths):
            return
        legacy = self._read(legacy_path)
        if not legacy:
            return
        pref_keys = {"tooltips_enabled", "close_after_build_enabled", "minimize_after_build_enabled", "open_output_dir_after_build_enabled", "suppress_exit_dialogue_enabled", "build_mode", "guided_flow_enabled"}
        python_data = {key: value for key, value in legacy.items() if key not in pref_keys | {"dotnet_publish"}}
        self._write(self.python_state_file_path(), python_data)
        self._write(self.csharp_state_file_path(), dict(legacy.get("dotnet_publish", {})))
        self._write(self.preferences_file_path(), {key: legacy[key] for key in pref_keys if key in legacy})
        try:
            os.remove(legacy_path)
        except OSError as exc:
            print("Legacy state removal error:", exc)

    def _find_enabled_dropdown_text(self, dropdown, text):
        for index in range(dropdown.count()):
            if dropdown.itemText(index) == text:
                model = getattr(dropdown, "model", lambda: None)()
                item = model.item(index) if model is not None else None
                if item is None or item.isEnabled():
                    return index
        return -1

    def load_state(self):
        self._migrate_legacy_state()
        app = self.app
        python_data = self._read(self.python_state_file_path())
        csharp_data = self._read(self.csharp_state_file_path())
        preferences = self._read(self.preferences_file_path())
        app.state_data = python_data
        app.csharp_state_data = csharp_data
        saved_setups = python_data.get("saved_build_setups", [])
        app.saved_build_setups = saved_setups if isinstance(saved_setups, list) else []
        blocked = []
        names = ("tooltips_checkbox", "suppress_exit_dialogue", "script_path_input", "icon_path_input", "output_path_input", "exe_name_input", "python_entry_input", "appened_py_version", "dotnet_project_input", "dotnet_output_input", "dotnet_icon_input", "dotnet_name_input", "dotnet_runtime_combo", "dotnet_date_time_dropdown", "dotnet_self_contained", "dotnet_single_file", "dotnet_trim")
        for name in names:
            widget = getattr(app, name, None)
            if widget is not None:
                widget.blockSignals(True)
                blocked.append(widget)
        try:
            norm = lambda path: os.path.normpath(path) if path else ""
            for key, default in (("tooltips_enabled", True), ("close_after_build_enabled", True), ("minimize_after_build_enabled", True), ("open_output_dir_after_build_enabled", False), ("suppress_exit_dialogue_enabled", False)):
                setattr(app, key, preferences.get(key, default))
            app.build_mode = preferences.get("build_mode", "python")
            app.guided_flow_enabled = True
            if hasattr(app, "_update_python_navigation"):
                app._update_python_navigation()
            app.script_path = norm(python_data.get("last_script_path", "")); app.icon_path = norm(python_data.get("last_icon_path", "")); app.output_path = norm(python_data.get("last_output_folder", ""))
            app.last_non_desktop_output_dir = norm(python_data.get("last_non_desktop_output_folder", ""))
            if app.last_non_desktop_output_dir:
                app.last_output_dir = app.last_non_desktop_output_dir
            app.python_interpreter_path = norm(python_data.get("python_interpreter_path", "")); app.python_path = app.python_interpreter_path
            app.exe_name = python_data.get("last_exe_name", ""); app.append_datetime = python_data.get("append_datetime", False); app.datetime_format = python_data.get("datetime_format")
            # The selected values must also remain available to the recent-item
            # lists. Those lists are populated immediately after state loading
            # and otherwise clear a valid selection that predates its recents.
            recents_changed = False
            for key, path in (
                ("recent_scripts", app.script_path),
                ("recent_icons", app.icon_path),
                ("recent_interpreters", app.python_interpreter_path),
            ):
                items = list(python_data.get(key, []))
                if path and all(os.path.normcase(norm(item)) != os.path.normcase(path) for item in items):
                    python_data[key] = [path, *items]
                    recents_changed = True
            if recents_changed:
                self._write(self.python_state_file_path(), python_data)
            app.last_build_seconds = python_data.get("last_build_seconds", csharp_data.get("last_build_seconds", 45))
            for name in ("icon_user_cleared", "script_user_cleared", "interpreter_user_cleared", "append_py_version"):
                setattr(app, name, python_data.get(name, False))
            if hasattr(app, "appened_py_version"):
                app.appened_py_version.setChecked(app.append_py_version)
            app.entry_script = app.script_path or None; app.project_root = os.path.dirname(app.script_path) if app.script_path else None
            for field, value, method in (("script_path_input", app.script_path, "set_display_path"), ("icon_path_input", app.icon_path, "set_display_path"), ("output_path_input", app.output_path, "set_display_path"), ("exe_name_input", app.exe_name, "setText"), ("python_entry_input", app.python_interpreter_path, "set_display_path")):
                if hasattr(app, field): getattr(getattr(app, field), method)(value)
            if hasattr(app, "dotnet_project_input"):
                app.dotnet_project_input.set_display_path(norm(csharp_data.get("project_path", ""))); app.dotnet_output_input.set_display_path(norm(csharp_data.get("output_folder", ""))); app.dotnet_icon_input.set_display_path(norm(csharp_data.get("icon_path", ""))); app.dotnet_name_input.setText(csharp_data.get("executable_name", ""))
                index = app.dotnet_runtime_combo.findData(csharp_data.get("runtime", "win-x64")); app.dotnet_runtime_combo.setCurrentIndex(index if index >= 0 else 0)
                dropdown = getattr(app, "dotnet_date_time_dropdown", None)
                if dropdown is not None:
                    selected = csharp_data.get("datetime_format")
                    index = dropdown.findData(selected) if selected is not None else -1
                    if index < 0 or selected is None:
                        index = self._find_enabled_dropdown_text(dropdown, self.NO_DATETIME_LABEL)
                    if index >= 0:
                        dropdown.setCurrentIndex(index)
                option_keys = ("self_contained", "single_file", "trim")
                first_use = not any(key in csharp_data for key in option_keys)
                app.dotnet_self_contained.setChecked(csharp_data.get("self_contained", first_use)); app.dotnet_single_file.setChecked(csharp_data.get("single_file", False)); app.dotnet_trim.setChecked(csharp_data.get("trim", False))
                sync_publish_options = getattr(app, "_sync_dotnet_publish_options", None)
                if sync_publish_options is not None:
                    sync_publish_options()
            for field, value in (("tooltips_checkbox", app.tooltips_enabled), ("close_after_build", app.close_after_build_enabled), ("minimize_after_build", app.minimize_after_build_enabled and not app.close_after_build_enabled), ("open_output_dir_after_build", app.open_output_dir_after_build_enabled), ("suppress_exit_dialogue", app.suppress_exit_dialogue_enabled)):
                if hasattr(app, field): getattr(app, field).setChecked(value)
            if hasattr(app, "date_time_dropdown"):
                if app.datetime_format:
                    index = app.date_time_dropdown.findData(app.datetime_format)
                    if index >= 0:
                        app.date_time_dropdown.setCurrentIndex(index)
                elif not app.append_datetime:
                    index = self._find_enabled_dropdown_text(app.date_time_dropdown, self.NO_DATETIME_LABEL)
                    if index >= 0: app.date_time_dropdown.setCurrentIndex(index)
            env = getattr(app, "environment_sync_controller", None)
            if env is not None and python_data.get("env_sync_profiles"): env.load_serialized_profiles(python_data["env_sync_profiles"], update_ui=True)
            app.validator.update_ui_state()
            restore_workflow = getattr(app, "restore_python_guided_workflow", None)
            if restore_workflow is not None:
                restore_workflow(python_data.get("guided_python_steps", []))
            if hasattr(app, "_populate_saved_build_setups"):
                app._populate_saved_build_setups()
            if hasattr(app, "set_build_mode"): app.set_build_mode(app.build_mode if app.build_mode in {"python", "dotnet"} else "python", save=False)
        finally:
            for widget in blocked: widget.blockSignals(False)

    def save_preferences(self):
        app = self.app
        self._write(self.preferences_file_path(), {key: getattr(app, key, default) for key, default in (("tooltips_enabled", True), ("close_after_build_enabled", True), ("minimize_after_build_enabled", True), ("open_output_dir_after_build_enabled", False), ("suppress_exit_dialogue_enabled", False), ("build_mode", "python"))})

    def save_python_state(self):
        app = self.app; norm = lambda path: os.path.normpath(path) if path else ""; existing = self._read(self.python_state_file_path())
        env = getattr(app, "environment_sync_controller", None)
        output = norm(app.output_path)
        desktop = norm(os.path.join(os.path.expanduser("~"), "Desktop"))
        remembered = norm(getattr(app, "last_non_desktop_output_dir", "")) or (output if output and os.path.normcase(output) != os.path.normcase(desktop) else "")
        data = {"last_script_path": norm(app.script_path), "last_icon_path": norm(app.icon_path), "last_output_folder": output, "last_non_desktop_output_folder": remembered, "python_interpreter_path": norm(getattr(app, "python_interpreter_path", "")), "last_exe_name": app.exe_name, "recent_scripts": app.state_data.get("recent_scripts", existing.get("recent_scripts", [])), "recent_icons": app.state_data.get("recent_icons", existing.get("recent_icons", [])), "recent_interpreters": app.state_data.get("recent_interpreters", existing.get("recent_interpreters", [])), "saved_build_setups": getattr(app, "saved_build_setups", existing.get("saved_build_setups", [])), "env_sync_profiles": env.serialize_profiles() if env else app.state_data.get("env_sync_profiles", []), "last_build_seconds": app.last_build_seconds, "icon_user_cleared": getattr(app, "icon_user_cleared", False), "script_user_cleared": getattr(app, "script_user_cleared", False), "interpreter_user_cleared": getattr(app, "interpreter_user_cleared", False), "append_datetime": getattr(app, "append_datetime", False), "datetime_format": getattr(app, "datetime_format", None), "append_py_version": getattr(app, "append_py_version", False), "guided_python_steps": sorted(getattr(app, "_completed_python_steps", set()))}
        app.state_data = data; self._write(self.python_state_file_path(), data)

    def save_csharp_state(self):
        app = self.app; norm = lambda path: os.path.normpath(path) if path else ""; existing = getattr(app, "csharp_state_data", self._read(self.csharp_state_file_path()))
        selected = next((name for name in ("self_contained", "single_file", "trim") if getattr(app, f"dotnet_{name}").isChecked()), None)
        dropdown = getattr(app, "dotnet_date_time_dropdown", None)
        data = {"recent_projects": existing.get("recent_projects", []), "recent_icons": existing.get("recent_icons", []), "last_non_desktop_output_folder": existing.get("last_non_desktop_output_folder", ""), "project_path": norm(app.dotnet_project_input.text()), "output_folder": norm(app.dotnet_output_input.text()), "icon_path": norm(app.dotnet_icon_input.text()), "executable_name": app.dotnet_name_input.text(), "runtime": app.dotnet_runtime_combo.currentData(), "datetime_format": dropdown.currentData() if dropdown is not None else existing.get("datetime_format"), "self_contained": selected == "self_contained", "single_file": selected == "single_file", "trim": selected == "trim", "last_build_seconds": getattr(app, "last_build_seconds", 45)}
        app.csharp_state_data = data; self._write(self.csharp_state_file_path(), data)

    def save_state(self):
        self.save_python_state(); self.save_preferences()

    def save_all_state(self):
        self.save_python_state(); self.save_csharp_state(); self.save_preferences()
