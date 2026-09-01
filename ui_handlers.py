
import os,subprocess,time,webbrowser
from PySide6.QtCore import QTimer
from datetime_build_options import (
    ISO_MASS_DATETIME_BUILD_SENTINEL,
    MASS_DATETIME_BUILD_SENTINEL,
    NO_DATETIME_LABEL,
    UK_MASS_DATETIME_BUILD_SENTINEL,
    USA_MASS_DATETIME_BUILD_SENTINEL,
)
from ui_highlights import flash_delete_highlight

MASS_DATETIME_BUILD_SENTINELS = {
    MASS_DATETIME_BUILD_SENTINEL,
    ISO_MASS_DATETIME_BUILD_SENTINEL,
    UK_MASS_DATETIME_BUILD_SENTINEL,
    USA_MASS_DATETIME_BUILD_SENTINEL,
}


def _find_no_datetime_index(dropdown):
    if not hasattr(dropdown, "count") or not hasattr(dropdown, "itemText"):
        return -1
    for index in range(dropdown.count()):
        if dropdown.itemText(index) == NO_DATETIME_LABEL:
            return index
    return -1


class UIHandlers:
    def __init__(self, app):
        self.app = app
        self._app_data_monitor = None
        self._app_data_monitor_path = ""


    def get_desktop_path(self):
        return os.path.join(os.path.expanduser("~"), "Desktop")

    def clear_interpreter_path(self):
        app = self.app
        flash_delete_highlight(
            getattr(app, "interpreter_refresh_btn", None),
            getattr(app, "python_entry_input", None),
        )

        # -------------------------------
        # CLEAR STATE (source of truth FIRST)
        # -------------------------------
        app.python_interpreter_path = ""
        app.python_path = ""
        app.interpreter_user_cleared = True

        # -------------------------------
        # CLEAR UI
        # -------------------------------
        if hasattr(app, "python_entry_input"):
            app.python_entry_input.clear()

        # reset dropdown safely
        if hasattr(app, "select_interpreter"):
            app.select_interpreter.blockSignals(True)
            app.select_interpreter.setCurrentIndex(0)
            app.select_interpreter.blockSignals(False)

        # -------------------------------
        # SAVE STATE
        # -------------------------------
        app.state_ctrl.save_state()

        # -------------------------------
        # FORCE UI UPDATE (ORDER MATTERS)
        # -------------------------------
        app.validator.validation_status_message()
        app.validator.update_ui_state()

    def clear_script_path(self):
        app = self.app
        flash_delete_highlight(
            getattr(app, "script_clear_btn", None),
            getattr(app, "script_path_input", None),
        )

        # -------------------------------
        # CLEAR STATE FIRST
        # -------------------------------
        app.entry_script = None
        app.project_root = None
        app.script_path = ""
        app.script_user_cleared = True

        # -------------------------------
        # CLEAR UI
        # -------------------------------
        if hasattr(app, "script_path_input"):
            app.script_path_input.clear()

        # -------------------------------
        # SAVE STATE
        # -------------------------------
        app.state_ctrl.save_state()

        # -------------------------------
        # FORCE UI UPDATE
        # -------------------------------
        app.validator.validation_status_message()
        app.validator.update_ui_state()

    def clear_icon(self):
        app = self.app
        flash_delete_highlight(
            getattr(app, "icon_clear_btn", None),
            getattr(app, "icon_path_input", None),
        )

        # -------------------------------
        # CLEAR STATE FIRST
        # -------------------------------
        app.icon_path = ""
        app.icon_user_cleared = True

        # 🔑 prevent signal loop
        if hasattr(app, "select_recent_icons"):
            app.select_recent_icons.blockSignals(True)
            app.select_recent_icons.setCurrentIndex(1)  # "No Icon"
            app.select_recent_icons.blockSignals(False)

        # -------------------------------
        # CLEAR UI
        # -------------------------------
        if hasattr(app, "icon_path_input"):
            app.icon_path_input.clear()

        # -------------------------------
        # SAVE STATE
        # -------------------------------
        app.state_ctrl.save_state()

        # -------------------------------
        # FORCE UI UPDATE
        # -------------------------------
        app.validator.validation_status_message()
        app.validator.update_ui_state()
        
    def reset_output_to_desktop(self):
        app = self.app
        flash_delete_highlight(
            getattr(app, "output_refresh_btn", None),
            getattr(app, "output_path_input", None),
        )
        app.build_error = None
        desktop = self.get_desktop_path()
        app.output_path_input.set_display_path(desktop)
        app.output_path = desktop
        app.state_ctrl.save_state()
        app.validation_controller.update_ui_state()

    def _open_folder(self, folder_path):
        os.startfile(folder_path)

    def _select_file_in_explorer(self, file_path):
        subprocess.Popen(["explorer.exe", f"/select,{file_path}"])

    def _normalize_explorer_path(self, path):
        if not path:
            return ""
        return os.path.normcase(os.path.abspath(os.path.normpath(path)))

    def _path_from_explorer_url(self, url):
        if not url or not url.startswith("file:"):
            return ""

        try:
            from urllib.parse import unquote, urlparse

            parsed = urlparse(url)
            path = unquote(parsed.path or "")
            if parsed.netloc:
                return os.path.normpath(f"//{parsed.netloc}{path}")
            return os.path.normpath(path.lstrip("/"))
        except Exception:
            return ""

    def _get_explorer_window_path(self, window):
        try:
            folder_path = window.Document.Folder.Self.Path
        except Exception:
            folder_path = ""

        if folder_path:
            return folder_path

        try:
            return self._path_from_explorer_url(window.LocationURL)
        except Exception:
            return ""

    def _is_explorer_folder_open(self, folder_path):
        target_path = self._normalize_explorer_path(folder_path)
        if not target_path:
            return False

        try:
            import win32com.client

            windows = win32com.client.Dispatch("Shell.Application").Windows()
            count = windows.Count
        except Exception:
            return None

        for index in range(count):
            try:
                window = windows.Item(index)
                window_path = self._normalize_explorer_path(
                    self._get_explorer_window_path(window)
                )
            except Exception:
                continue

            if window_path == target_path:
                return True

        return False

    def _stop_app_data_monitor(self):
        timer = self._app_data_monitor
        self._app_data_monitor = None
        self._app_data_monitor_path = ""
        if timer is not None:
            timer.stop()

    def _restore_after_app_data(self):
        self._stop_app_data_monitor()
        app = self.app
        if getattr(app, "_is_closing", False):
            return

        app.showNormal()
        app.raise_()
        app.activateWindow()

    def _poll_app_data_folder(self):
        if getattr(self.app, "_is_closing", False):
            self._stop_app_data_monitor()
            return

        if self._is_explorer_folder_open(self._app_data_monitor_path) is True:
            return

        self._restore_after_app_data()

    def _start_app_data_monitor(self, state_dir):
        self._stop_app_data_monitor()
        if self._is_explorer_folder_open(state_dir) is not True:
            return False

        timer = QTimer()
        timer.setInterval(150)
        timer.timeout.connect(self._poll_app_data_folder)
        self._app_data_monitor_path = state_dir
        self._app_data_monitor = timer
        self.app.showMinimized()
        timer.start()
        return True

    def shutdown(self):
        self._stop_app_data_monitor()

    def _pulse_window_topmost(self, hwnd):
        try:
            import win32con
            import win32gui
        except Exception:
            return False

        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        except Exception:
            pass

        flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW

        try:
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                0,
                0,
                0,
                0,
                flags,
            )
            win32gui.SetForegroundWindow(hwnd)
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_NOTOPMOST,
                0,
                0,
                0,
                0,
                flags,
            )
            return True
        except Exception:
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass
            return False

    def _force_app_data_folder_on_top(self, state_dir):
        folder_title = os.path.basename(os.path.normpath(state_dir))
        if not folder_title:
            return False

        deadline = time.time() + 1.5
        while time.time() < deadline:
            try:
                import pygetwindow

                windows = pygetwindow.getWindowsWithTitle(folder_title)
            except Exception:
                windows = []

            for window in windows:
                title = getattr(window, "title", "")
                if folder_title.lower() not in title.lower():
                    continue

                try:
                    if getattr(window, "isMinimized", False):
                        window.restore()
                except Exception:
                    pass

                try:
                    window.activate()
                except Exception:
                    pass

                hwnd = getattr(window, "_hWnd", None) or getattr(window, "hWnd", None)
                if hwnd:
                    self._pulse_window_topmost(hwnd)

                return True

            time.sleep(0.1)

        return False

    def open_app_data(self):
        app = self.app
        self._stop_app_data_monitor()
        state_file = app.state_ctrl._state_file_path()
        state_dir = os.path.dirname(state_file)
        os.makedirs(state_dir, exist_ok=True)

        try:
            if os.path.isfile(state_file):
                self._select_file_in_explorer(state_file)
            else:
                self._open_folder(state_dir)
            if self._force_app_data_folder_on_top(state_dir):
                self._start_app_data_monitor(state_dir)
        except Exception:
            try:
                self._open_folder(state_dir)
                if self._force_app_data_folder_on_top(state_dir):
                    self._start_app_data_monitor(state_dir)
            except Exception:
                pass
    
    def reset_exe_name_from_script(self):
        app = self.app
        script = app.entry_script
        if not script or not os.path.isfile(script):
            return

        flash_delete_highlight(
            getattr(app, "refresh_btn", None),
            getattr(app, "exe_name_input", None),
        )
        derived = os.path.splitext(os.path.basename(script))[0]
        app.exe_name_user_modified = False
        app.exe_name_input.setText(derived)
        app.state_ctrl.save_state()
        
    def on_tooltips_toggle(self, state):
        app = self.app
        app.tooltips_enabled = bool(state)
        app.state_ctrl.save_state()

    def on_minimize_toggle(self, state):
        app = self.app
        app.minimize_after_build_enabled = bool(state)

        # 🔑 enforce mutual exclusion immediately
        if state:
            app.close_after_build.setChecked(False)
            app.close_after_build_enabled = False

        app.state_ctrl.save_state()
        app.validator.update_ui_state()   # 🔑 THIS WAS MISSING

    def on_open_output_dir_toggle(self, state):
        app = self.app
        app.open_output_dir_after_build_enabled = bool(state)
        app.state_ctrl.save_state()
        app.validator.update_ui_state()

    def on_suppress_exit_dialogue_toggle(self, state):
        app = self.app
        app.suppress_exit_dialogue_enabled = bool(state)
        app.state_ctrl.save_state()
        app.validator.update_ui_state()

    def on_close_toggle(self, state):
        app = self.app
        app.close_after_build_enabled = bool(state)

        # 🔑 enforce mutual exclusion immediately
        if state:
            app.minimize_after_build.setChecked(False)
            app.minimize_after_build_enabled = False

        app.state_ctrl.save_state()
        app.validator.update_ui_state()   
        
    def on_script_path_change(self, text):
        app = self.app
        if getattr(app, "_loading_state", False):
            return

        value = text.strip()

        if not value:
            app.entry_script = None
            app.project_root = None

            # ✅ clear dependent fields
            if hasattr(app, "output_path_input"):
                app.output_path_input.clear()
            app.output_path = ""
            if hasattr(app, "exe_name_input"):
                app.exe_name_input.clear()
            app.exe_name = ""
            app.state_ctrl.save_state()

    # =============================================================
    # EXE name cleared by USER
    # =============================================================

    def on_exe_name_change(self, text):
        app = self.app
        if app._loading_state:
            return

        value = text.strip()
        if not value:
            app.state_ctrl.save_state()

            
        if hasattr(app, "validator"):
            app.validator.validation_status_message()
            app.validator.update_ui_state()

        app.exe_name = value  # 🔑 ensure source of truth is updated
        app.state_ctrl.save_state()

    def on_datetime_format_changed(self, index):
        app = self.app

        data = app.date_time_dropdown.currentData()

        if data in MASS_DATETIME_BUILD_SENTINELS:
            app.mass_datetime_build_selected = True
            if not hasattr(app, "_mass_datetime_restore_state"):
                app._mass_datetime_restore_state = {
                    "append_datetime": getattr(app, "append_datetime", False),
                    "datetime_format": getattr(app, "datetime_format", None),
                }
            app.append_datetime = False
            app.datetime_format = data
            if hasattr(app, "state_ctrl"):
                app.state_ctrl.save_state()
            if hasattr(app, "validator"):
                app.validator.validation_status_message()
                self.app.validator.update_ui_state()
            return

        app.mass_datetime_build_selected = False
        if hasattr(app, "_mass_datetime_restore_state"):
            delattr(app, "_mass_datetime_restore_state")

        if data is None:
            # 🔴 OFF (None selected)
            app.append_datetime = False
            app.datetime_format = ""

            none_index = _find_no_datetime_index(app.date_time_dropdown)
            if none_index != -1 and app.date_time_dropdown.currentIndex() != none_index:
                app.date_time_dropdown.blockSignals(True)
                app.date_time_dropdown.setCurrentIndex(none_index)
                app.date_time_dropdown.blockSignals(False)

        else:
            # 🟢 ON
            app.append_datetime = True
            app.datetime_format = data

        if hasattr(app, "state_ctrl"):
            app.state_ctrl.save_state()

        if hasattr(app, "validator"):
            app.validator.validation_status_message()
            self.app.validator.update_ui_state()

    def on_append_py_version_toggle(self, checked):
        app = self.app

        app.append_py_version = checked

        if hasattr(app, "state_ctrl"):
            app.state_ctrl.save_state()

        if hasattr(app, "validator"):
            app.validator.validation_status_message()
            self.app.validator.update_ui_state()

    def on_env_sync_scan(self):
        app = self.app
        app.set_env_sync_status("Scanning Python profiles...")
        if not app.environment_sync_controller.start_scan_async():
            app.set_env_sync_status("Environment sync is already running.")

    def on_env_sync_match(self):
        app = self.app
        app.set_env_sync_status("Syncing dependencies...")
        if not app.environment_sync_controller.start_sync_async():
            app.set_env_sync_status("Environment sync is already running.")
    
    def _on_exe_name_user_edit(self, text):
        app = self.app
        if app._loading_state:
            return
        app.exe_name_user_modified = True
        if hasattr(app, "validator"):
            app.validator.validation_status_message()
            app.validator.update_ui_state()


    def open_python_site(self):
        app = self.app
        webbrowser.open("https://www.python.org")

    def open_icon_sites(self):
        app = self.app
        urls = [
            "https://convertico.com/",
            "https://cloudconvert.com/png-to-ico",
            "https://www.icoconverter.com/"
        ]
        for url in urls:
            webbrowser.open(url)
