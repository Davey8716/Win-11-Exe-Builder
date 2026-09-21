import os
import json

from ..build.datetime_build_options import (
    ISO_MASS_DATETIME_BUILD_SENTINEL,
    MASS_DATETIME_BUILD_SENTINEL,
    NO_DATETIME_LABEL as DATETIME_NO_DATETIME_LABEL,
    UK_MASS_DATETIME_BUILD_SENTINEL,
    USA_MASS_DATETIME_BUILD_SENTINEL,
)

class StateController:
    NO_DATETIME_LABEL = DATETIME_NO_DATETIME_LABEL

    def __init__(self, app):
        self.app = app
        self.last_build_counter = 0

    # def _state_file_path(self) -> str:
    #     if getattr(sys, "frozen", False):
    #         base_dir = os.path.dirname(sys.executable)
    #     else:
    #         base_dir = os.path.abspath(".")
    #     return os.path.join(base_dir, "exe_builder_state.json")

    def _state_file_path(self) -> str:

        # -------------------------------
        # ALWAYS use user-writable location
        # -------------------------------
        app_name = "EXEBuilder"

        base_dir = os.path.join(
            os.getenv("LOCALAPPDATA") or os.path.expanduser("~"),
            app_name
        )

        os.makedirs(base_dir, exist_ok=True)

        return os.path.join(base_dir, "exe_builder_state.json")

        
    # ============================================================
    # LOAD
    # ============================================================
    def _find_enabled_dropdown_text(self, dropdown, text):
        for index in range(dropdown.count()):
            if dropdown.itemText(index) != text:
                continue

            model = getattr(dropdown, "model", lambda: None)()
            if model is None:
                return index

            item = model.item(index)
            if item is None or item.isEnabled():
                return index

        return -1

    def load_state(self):
        state_path = self._state_file_path()

        if not os.path.isfile(state_path):
            self.app.state_data = {"recent_scripts": []}
            return

        blocked_widgets = []

        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            def _norm(p):
                return os.path.normpath(p) if p else ""

            def _desktop_path():
                return os.path.normpath(os.path.join(os.path.expanduser("~"), "Desktop"))

            def _is_desktop_path(p):
                return bool(p) and os.path.normcase(_norm(p)) == os.path.normcase(_desktop_path())

            # keep full raw state in memory
            self.app.state_data = data

            # -------------------------
            # Block UI signals during hydrate
            # -------------------------
            for name in (
                "tooltips_checkbox",
                "suppress_exit_dialogue",
                "script_path_input",
                "icon_path_input",
                "output_path_input",
                "exe_name_input",
                "python_entry_input",
                "dotnet_project_input",
                "dotnet_output_input",
                "dotnet_icon_input",
                "dotnet_name_input",
                "dotnet_runtime_combo",
                "dotnet_self_contained",
                "dotnet_single_file",
                "dotnet_trim",
            ):
                widget = getattr(self.app, name, None)
                if widget is not None:
                    widget.blockSignals(True)
                    blocked_widgets.append(widget)

            # -------------------------
            # Load JSON app state
            # -------------------------
            self.app.tooltips_enabled = data.get("tooltips_enabled", True)
            self.app.close_after_build_enabled = data.get("close_after_build_enabled", True)
            self.app.minimize_after_build_enabled = data.get("minimize_after_build_enabled", True)
            self.app.open_output_dir_after_build_enabled = data.get("open_output_dir_after_build_enabled", False)
            self.app.suppress_exit_dialogue_enabled = data.get("suppress_exit_dialogue_enabled", False)

            self.app.script_path = _norm(data.get("last_script_path", ""))
            self.app.icon_path = _norm(data.get("last_icon_path", ""))
            self.app.output_path = _norm(data.get("last_output_folder", ""))
            self.app.last_non_desktop_output_dir = _norm(
                data.get("last_non_desktop_output_folder", "")
            )
            if not self.app.last_non_desktop_output_dir and not _is_desktop_path(self.app.output_path):
                self.app.last_non_desktop_output_dir = self.app.output_path

            if self.app.last_non_desktop_output_dir:
                self.app.last_output_dir = self.app.last_non_desktop_output_dir
            elif self.app.output_path and not _is_desktop_path(self.app.output_path):
                self.app.last_output_dir = self.app.output_path
            self.app.python_interpreter_path = _norm(data.get("python_interpreter_path", ""))
            self.app.python_path = self.app.python_interpreter_path
            self.app.exe_name = data.get("last_exe_name", "")
            self.app.append_datetime = data.get("append_datetime", False)
            self.app.datetime_format = data.get("datetime_format", None)

            self.app.last_build_seconds = data.get("last_build_seconds", 45)

            self.app.icon_user_cleared = data.get("icon_user_cleared", False)
            self.app.script_user_cleared = data.get("script_user_cleared", False)
            self.app.interpreter_user_cleared = data.get("interpreter_user_cleared", False)
            self.app.append_py_version = data.get("append_py_version", False)
            dotnet = data.get("dotnet_publish", {})
            self.app.build_mode = data.get("build_mode", "python")

            if self.app.python_interpreter_path:
                self.app.last_python_dir = os.path.dirname(self.app.python_interpreter_path)

            # -------------------------
            # Runtime rehydrate
            # -------------------------
            if self.app.script_path:
                self.app.entry_script = self.app.script_path
                self.app.project_root = os.path.dirname(self.app.script_path)
            else:
                self.app.entry_script = None
                self.app.project_root = None

            # -------------------------
            # Sync state -> UI rehdration
            # -------------------------
            # 🔑 restore + enforce mutual exclusion (hasattr style)

            close_val = getattr(self.app, "close_after_build_enabled", True)
            min_val = getattr(self.app, "minimize_after_build_enabled", True)

            # enforce rule (close wins if both True)
            if close_val and min_val:
                min_val = False
                self.app.minimize_after_build_enabled = False

            if hasattr(self.app, "close_after_build"):
                self.app.close_after_build.setChecked(close_val)

            if hasattr(self.app, "minimize_after_build"):
                self.app.minimize_after_build.setChecked(min_val)

            if hasattr(self.app, "open_output_dir_after_build"):
                self.app.open_output_dir_after_build.setChecked(
                    getattr(self.app, "open_output_dir_after_build_enabled", False)
                )

            if hasattr(self.app, "tooltips_checkbox"):
                self.app.tooltips_checkbox.setChecked(self.app.tooltips_enabled)

            if hasattr(self.app, "suppress_exit_dialogue"):
                self.app.suppress_exit_dialogue.setChecked(
                    getattr(self.app, "suppress_exit_dialogue_enabled", False)
                )

            if hasattr(self.app, "script_path_input"):
                self.app.script_path_input.set_display_path(self.app.script_path)

            if hasattr(self.app, "icon_path_input"):
                self.app.icon_path_input.set_display_path(self.app.icon_path)

            if hasattr(self.app, "output_path_input"):
                self.app.output_path_input.set_display_path(self.app.output_path)

            if hasattr(self.app, "exe_name_input"):
                self.app.exe_name_input.setText(self.app.exe_name)

            if hasattr(self.app, "python_entry_input"):
                self.app.python_entry_input.set_display_path(self.app.python_interpreter_path)

            if hasattr(self.app, "dotnet_project_input"):
                self.app.dotnet_project_input.set_display_path(_norm(dotnet.get("project_path", "")))
                self.app.dotnet_output_input.set_display_path(_norm(dotnet.get("output_folder", "")))
                self.app.dotnet_icon_input.set_display_path(_norm(dotnet.get("icon_path", "")))
                self.app.dotnet_name_input.setText(dotnet.get("executable_name", ""))
                runtime = dotnet.get("runtime", "win-x64")
                index = self.app.dotnet_runtime_combo.findData(runtime)
                self.app.dotnet_runtime_combo.setCurrentIndex(index if index >= 0 else 0)
                self.app.dotnet_self_contained.setChecked(dotnet.get("self_contained", True))
                self.app.dotnet_single_file.setChecked(dotnet.get("single_file", False))
                self.app.dotnet_trim.setChecked(dotnet.get("trim", False))

            # --- restore datetime dropdown ---
            if hasattr(self.app, "date_time_dropdown"):
                if self.app.datetime_format in {
                    MASS_DATETIME_BUILD_SENTINEL,
                    ISO_MASS_DATETIME_BUILD_SENTINEL,
                    UK_MASS_DATETIME_BUILD_SENTINEL,
                    USA_MASS_DATETIME_BUILD_SENTINEL,
                }:
                    index = self.app.date_time_dropdown.findData(self.app.datetime_format)
                    if index != -1:
                        self.app.date_time_dropdown.setCurrentIndex(index)
                elif self.app.append_datetime and self.app.datetime_format:
                    index = self.app.date_time_dropdown.findData(self.app.datetime_format)
                    if index != -1:
                        self.app.date_time_dropdown.setCurrentIndex(index)
                elif not self.app.append_datetime:
                    index = self._find_enabled_dropdown_text(
                        self.app.date_time_dropdown,
                        self.NO_DATETIME_LABEL,
                    )
                    if index != -1:
                        self.app.date_time_dropdown.setCurrentIndex(index)

            # --- restore toggle state ---
            if hasattr(self.app, "appened_py_version"):  # (your naming)
                self.app.appened_py_version.setChecked(
                    getattr(self.app, "append_py_version", False)
                )

            if getattr(self.app, "interpreter_user_cleared", False):
                self.app.python_interpreter_path = ""
                self.app.python_path = ""

                if hasattr(self.app, "python_entry_input"):
                    self.app.python_entry_input.clear()

                if hasattr(self.app, "select_interpreter"):
                    self.app.select_interpreter.setCurrentIndex(0)

            env_sync_controller = getattr(self.app, "environment_sync_controller", None)
            if env_sync_controller is not None:
                env_sync_profiles = data.get("env_sync_profiles", [])
                if env_sync_profiles:
                    env_sync_controller.load_serialized_profiles(
                        env_sync_profiles,
                        update_ui=True,
                    )
                
            self.app.validator.update_ui_state()
            if hasattr(self.app, "set_build_mode"):
                self.app.set_build_mode(
                    self.app.build_mode if self.app.build_mode in {"python", "dotnet"} else "python",
                    save=False,
                )

        except Exception as e:
            self.app.state_data = {"recent_scripts": []}
            print("State load error:", e)

        finally:
            for widget in blocked_widgets:
                widget.blockSignals(False)
    
    def save_state(self):
        def _norm(p):
            return os.path.normpath(p) if p else ""

        def _desktop_path():
            return os.path.normpath(os.path.join(os.path.expanduser("~"), "Desktop"))

        def _is_desktop_path(p):
            return bool(p) and os.path.normcase(_norm(p)) == os.path.normcase(_desktop_path())

        state_path = self._state_file_path()

        # preserve existing recent scripts from memory/file
        existing_data = {}

        try:
            if os.path.isfile(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
        except Exception:
            existing_data = {}

        recent_scripts = getattr(self.app, "state_data", {}).get(
            "recent_scripts",
            existing_data.get("recent_scripts", [])
        )
        
        recent_icons = getattr(self.app, "state_data", {}).get(
            "recent_icons",
            existing_data.get("recent_icons", [])
        )

        recent_interpreters =  getattr(self.app, "state_data", {}).get(
            "recent_interpreters",
            existing_data.get("recent_interpreters", [])
        )

        env_sync_controller = getattr(self.app, "environment_sync_controller", None)
        if env_sync_controller is not None:
            env_sync_profiles = env_sync_controller.serialize_profiles()
        else:
            env_sync_profiles = getattr(self.app, "state_data", {}).get(
                "env_sync_profiles",
                existing_data.get("env_sync_profiles", [])
            )

        data = {
            # --- Paths / core selections ---
            "last_script_path": _norm(self.app.script_path),
            "last_icon_path": _norm(self.app.icon_path),
            "last_output_folder": _norm(self.app.output_path),
            "last_non_desktop_output_folder": _norm(
                getattr(self.app, "last_non_desktop_output_dir", "")
            ) or (
                _norm(self.app.output_path)
                if not _is_desktop_path(getattr(self.app, "output_path", ""))
                else ""
            ),
            "python_interpreter_path": _norm(
                getattr(self.app, "python_interpreter_path", "")
            ),
            "last_exe_name": self.app.exe_name,

            # --- Recents ---
            "recent_scripts": recent_scripts,
            "recent_icons": recent_icons,
            "recent_interpreters": recent_interpreters,
            "env_sync_profiles": env_sync_profiles,

            # --- Build info ---
            "last_build_seconds": self.app.last_build_seconds,

            # --- Toggles / settings ---
            "tooltips_enabled": getattr(self.app, "tooltips_enabled", True),
            "close_after_build_enabled": getattr(self.app, "close_after_build_enabled", True),
            "minimize_after_build_enabled": getattr(self.app, "minimize_after_build_enabled", True),
            "open_output_dir_after_build_enabled": getattr(self.app, "open_output_dir_after_build_enabled", False),
            "suppress_exit_dialogue_enabled": getattr(self.app, "suppress_exit_dialogue_enabled", False),

            # --- User flags ---
            "icon_user_cleared": getattr(self.app, "icon_user_cleared", False),
            "script_user_cleared": getattr(self.app, "script_user_cleared", False),
            "interpreter_user_cleared": getattr(self.app, "interpreter_user_cleared", False),

            # --- Datetime ---
            "append_datetime": getattr(self.app, "append_datetime", False),
            "datetime_format": getattr(self.app, "datetime_format", None),
            "append_py_version": getattr(self.app, "append_py_version", False),
            "build_mode": getattr(self.app, "build_mode", "python"),
            "dotnet_publish": {
                "recent_projects": getattr(self.app, "state_data", {}).get("dotnet_publish", {}).get("recent_projects", existing_data.get("dotnet_publish", {}).get("recent_projects", [])),
                "recent_icons": getattr(self.app, "state_data", {}).get("dotnet_publish", {}).get("recent_icons", existing_data.get("dotnet_publish", {}).get("recent_icons", [])),
                "last_non_desktop_output_folder": getattr(self.app, "state_data", {}).get("dotnet_publish", {}).get("last_non_desktop_output_folder", existing_data.get("dotnet_publish", {}).get("last_non_desktop_output_folder", "")),
                "project_path": _norm(getattr(self.app, "dotnet_project_input", None).text() if hasattr(self.app, "dotnet_project_input") else ""),
                "output_folder": _norm(getattr(self.app, "dotnet_output_input", None).text() if hasattr(self.app, "dotnet_output_input") else ""),
                "icon_path": _norm(getattr(self.app, "dotnet_icon_input", None).text() if hasattr(self.app, "dotnet_icon_input") else ""),
                "executable_name": getattr(self.app, "dotnet_name_input", None).text() if hasattr(self.app, "dotnet_name_input") else "",
                "runtime": getattr(self.app, "dotnet_runtime_combo", None).currentData() if hasattr(self.app, "dotnet_runtime_combo") else "win-x64",
                "self_contained": getattr(self.app, "dotnet_self_contained", None).isChecked() if hasattr(self.app, "dotnet_self_contained") else True,
                "single_file": getattr(self.app, "dotnet_single_file", None).isChecked() if hasattr(self.app, "dotnet_single_file") else False,
                "trim": getattr(self.app, "dotnet_trim", None).isChecked() if hasattr(self.app, "dotnet_trim") else False,
            },
        }

        self.app.state_data = data


        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("State save error:", e)
