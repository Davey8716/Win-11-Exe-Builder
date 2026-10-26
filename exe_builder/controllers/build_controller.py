import datetime,os,sys,subprocess,time,warnings
from PySide6.QtGui import QFont
from ..build.bundle_validation import validate_bundle_inputs
from ..build.external_python import external_python_environment
from ..build.datetime_build_options import (
    DATETIME_FORMAT_REGIONS,
    ISO_MASS_DATETIME_BUILD_SENTINEL,
    ISO_MASS_DATETIME_BUILD_SEQUENCE,
    MASS_DATETIME_BUILD_SENTINEL,
    MASS_DATETIME_BUILD_SEQUENCE,
    NO_DATETIME_LABEL,
    UK_MASS_DATETIME_BUILD_SENTINEL,
    UK_MASS_DATETIME_BUILD_SEQUENCE,
    USA_MASS_DATETIME_BUILD_SENTINEL,
    USA_MASS_DATETIME_BUILD_SEQUENCE,
)
from datetime import datetime
from PySide6.QtCore import QObject, Signal,QTimer
from PySide6.QtCore import QThread
from pathlib import Path
import shutil
from ..build.build_icon_contract import (
    clear_output_folder_icon_metadata,
    resolve_build_icon_contract,
)
from ..build.project_build_manifest import (
    ProjectBuildManifestError,
    load_project_build_manifest,
)
from ..build.self_update import (
    SelfUpdateError,
    cleanup_staging,
    create_self_update_plan,
    is_frozen_self_target,
    launch_self_update,
    validate_self_update_plan,
)
from ..ui.styles import Colors, status_text_style

CREATE_NO_WINDOW = 0x08000000
WINDOWS_RESOURCE_PATH_LIMIT = 260

MASS_DATETIME_BUILD_SENTINELS = {
    MASS_DATETIME_BUILD_SENTINEL,
    ISO_MASS_DATETIME_BUILD_SENTINEL,
    UK_MASS_DATETIME_BUILD_SENTINEL,
    USA_MASS_DATETIME_BUILD_SENTINEL,
}

def _write_debug_log_banner(file, title):
    file.write(f"=== {title} ===\n\n")


def _write_debug_log_section(file, title, lines):
    file.write(f"--- {title} ---\n")
    for line in lines:
        file.write(f"  {line}\n")
    file.write("\n")


def _write_debug_log_stderr(file, stderr):
    file.write("  STDERR:\n")
    for line in (stderr or "<empty>").splitlines():
        file.write(f"    {line}\n")
    file.write("\n")


def _expected_pyinstaller_exe_path(build_root, final_exe_name):
    return os.path.abspath(
        os.path.join(build_root, final_exe_name, f"{final_exe_name}.exe")
    )


class BuildController(QObject):
    build_complete_signal = Signal(int, str, str)

    def __init__(self, app):
        super().__init__()
        self.app = app
        self._mass_datetime_active = False
        self._mass_datetime_queue = []
        self._mass_datetime_total = 0
        self._mass_datetime_index = 0
        self._mass_datetime_current_label = ""
        self._mass_datetime_restore_state = None
        self._mass_datetime_debug_log_path = ""
        self._mass_datetime_debug_log_prefix = "EXE_BUILDER_BUILD_ALL_DEBUG"
        self._mass_datetime_log_title = "DATE/TIME"
        self._mass_datetime_output_group = []
        self._pending_self_update = None
        self._active_self_update_plan = None
        self._self_update_launched = False
        self._python_output_identity = None
        self._python_output_target = ""
        self.build_thread = None
        self.worker = None

        self.build_complete_signal.connect(self._on_build_complete_ui)

    # ============================================================
    # MASS DATE/TIME BUILD QUEUE
    # ============================================================

    def _datetime_dropdown_data(self):
        dropdown = getattr(self.app, "date_time_dropdown", None)
        if dropdown is None or not hasattr(dropdown, "currentData"):
            return None
        return dropdown.currentData()

    def _find_no_datetime_index(self):
        dropdown = getattr(self.app, "date_time_dropdown", None)
        if dropdown is None or not hasattr(dropdown, "count"):
            return -1

        for index in range(dropdown.count()):
            if dropdown.itemText(index) == NO_DATETIME_LABEL:
                return index

        return -1

    def _set_datetime_dropdown_index(self, index):
        dropdown = getattr(self.app, "date_time_dropdown", None)
        if dropdown is None or index == -1:
            return

        if hasattr(dropdown, "blockSignals"):
            dropdown.blockSignals(True)
        dropdown.setCurrentIndex(index)
        if hasattr(dropdown, "blockSignals"):
            dropdown.blockSignals(False)

    def _set_datetime_dropdown_for_state(self, append_datetime, datetime_format):
        dropdown = getattr(self.app, "date_time_dropdown", None)
        if dropdown is None:
            return

        index = -1
        if (
            datetime_format in MASS_DATETIME_BUILD_SENTINELS
            and hasattr(dropdown, "findData")
        ):
            index = dropdown.findData(datetime_format)
        elif append_datetime and datetime_format and hasattr(dropdown, "findData"):
            index = dropdown.findData(datetime_format)
        elif not append_datetime:
            index = self._find_no_datetime_index()

        self._set_datetime_dropdown_index(index)

    def _apply_datetime_build_option(self, label, datetime_format):
        app = self.app
        app.append_datetime = bool(datetime_format)
        app.datetime_format = datetime_format or ""
        self._set_datetime_dropdown_for_state(app.append_datetime, app.datetime_format)

        self._mass_datetime_current_label = label
        self._mass_datetime_index += 1
        app.set_status(
            f"Mass build {self._mass_datetime_index}/{self._mass_datetime_total}: {label}"
        )

    def _mass_datetime_build_config(self, sentinel):
        if sentinel == ISO_MASS_DATETIME_BUILD_SENTINEL:
            return (
                ISO_MASS_DATETIME_BUILD_SEQUENCE,
                "EXE_BUILDER_BUILD_ALL_ISO_DEBUG",
                "ISO DATE/TIME",
            )
        if sentinel == UK_MASS_DATETIME_BUILD_SENTINEL:
            return (
                UK_MASS_DATETIME_BUILD_SEQUENCE,
                "EXE_BUILDER_BUILD_ALL_UK_DEBUG",
                "UK DATE/TIME",
            )
        if sentinel == USA_MASS_DATETIME_BUILD_SENTINEL:
            return (
                USA_MASS_DATETIME_BUILD_SEQUENCE,
                "EXE_BUILDER_BUILD_ALL_USA_DEBUG",
                "USA DATE/TIME",
            )

        return (
            MASS_DATETIME_BUILD_SEQUENCE,
            "EXE_BUILDER_BUILD_ALL_DEBUG",
            "DATE/TIME",
        )

    def _start_mass_datetime_build(self, sentinel=MASS_DATETIME_BUILD_SENTINEL):
        app = self.app
        restore_state = {
            "append_datetime": False,
            "datetime_format": sentinel,
        }
        sequence, debug_log_prefix, log_title = self._mass_datetime_build_config(sentinel)

        self._mass_datetime_restore_state = restore_state
        self._mass_datetime_queue = list(sequence)
        self._mass_datetime_total = len(self._mass_datetime_queue)
        self._mass_datetime_index = 0
        self._mass_datetime_current_label = ""
        self._mass_datetime_debug_log_path = ""
        self._mass_datetime_debug_log_prefix = debug_log_prefix
        self._mass_datetime_log_title = log_title
        self._reset_mass_datetime_output_group()
        self._mass_datetime_active = True
        app.mass_datetime_build_selected = True

        self._run_next_mass_datetime_build()

    def _run_next_mass_datetime_build(self):
        if not self._mass_datetime_queue:
            return

        label, datetime_format = self._mass_datetime_queue.pop(0)
        self._apply_datetime_build_option(label, datetime_format)
        self.build_exe(None)

    def _restore_mass_datetime_state(self):
        app = self.app
        restore_state = self._mass_datetime_restore_state or {
            "append_datetime": False,
            "datetime_format": "",
        }

        append_datetime = restore_state.get("append_datetime", False)
        datetime_format = restore_state.get("datetime_format", None)

        app.append_datetime = append_datetime
        app.datetime_format = datetime_format or ""
        app.mass_datetime_build_selected = False

        if hasattr(app, "_mass_datetime_restore_state"):
            delattr(app, "_mass_datetime_restore_state")

        self._set_datetime_dropdown_for_state(append_datetime, app.datetime_format)
        if hasattr(app, "state_ctrl"):
            app.state_ctrl.save_state()

    def _reset_mass_datetime_output_group(self):
        self._mass_datetime_output_group = []

    def _remember_mass_datetime_output_group(self):
        paths = list(getattr(self.app, "current_build_paths", []) or [])
        debug_log_path = getattr(self.app, "debug_log_path", "")
        if debug_log_path:
            paths.append(debug_log_path)

        seen = {
            self._normalize_explorer_path_for_compare(path)
            for path in self._mass_datetime_output_group
        }
        for path in paths:
            normalized = os.path.normpath(path) if path else ""
            if not normalized:
                continue
            key = self._normalize_explorer_path_for_compare(normalized)
            if key in seen:
                continue
            self._mass_datetime_output_group.append(normalized)
            seen.add(key)

    def _apply_mass_datetime_output_group(self):
        if self._mass_datetime_output_group:
            self.app.current_build_paths = list(self._mass_datetime_output_group)

    def _finish_mass_datetime_build(self, clear_output_group=True):
        self._mass_datetime_queue = []
        self._mass_datetime_total = 0
        self._mass_datetime_index = 0
        self._mass_datetime_current_label = ""
        self._mass_datetime_active = False
        self._mass_datetime_debug_log_path = ""
        self._mass_datetime_debug_log_prefix = "EXE_BUILDER_BUILD_ALL_DEBUG"
        self._mass_datetime_log_title = "DATE/TIME"
        if clear_output_group:
            self._reset_mass_datetime_output_group()
        self._restore_mass_datetime_state()

    def _cancel_mass_datetime_build(self):
        if self._mass_datetime_active:
            self._finish_mass_datetime_build()
        self._discard_pending_self_update()

    def _discard_pending_self_update(self):
        plan = self._pending_self_update
        self._pending_self_update = None
        self._active_self_update_plan = None
        if plan is not None and not self._self_update_launched:
            cleanup_staging(plan)

    def _schedule_pending_self_update(self):
        plan = self._pending_self_update
        if plan is None:
            return False

        app = self.app
        try:
            validate_self_update_plan(plan)
            launch_self_update(plan)
        except (OSError, SelfUpdateError) as exc:
            cleanup_staging(plan)
            self._pending_self_update = None
            app.status_label.setStyleSheet(
                status_text_style(Colors.ERROR, border_width=1)
            )
            app.set_status(f"Build completed, but restart setup failed: {exc}")
            app.validation_controller.update_build_button()
            app.validation_controller.update_ui_state()
            return False

        self._self_update_launched = True
        app._status_lock = True
        app.set_status("Build complete. Restarting...")
        app.status_label.setStyleSheet(
            status_text_style(Colors.SUCCESS, border_width=1)
        )
        QTimer.singleShot(0, app.close_app)
        return True

    def _abort_current_build(self, message):
        app = self.app
        self._discard_pending_self_update()
        app.build_cancellation.abort_build(message)
        self.stop_eta()
        app.building = False
        app.build_process = None

        if self._mass_datetime_active:
            self._finish_mass_datetime_build()

        app.validation_controller.update_ui_state()
        app.validation_controller.update_build_button()

    def _disconnect_build_button_clicked(self):
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r'.*Failed to disconnect.*from signal "clicked\(\)".*',
                category=RuntimeWarning,
            )
            try:
                self.app.build_btn.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass

    def shutdown(self, timeout_ms=5000):
        app = self.app
        self.stop_eta()

        if getattr(app, "build_process", None):
            try:
                from ..build import build_cancellation

                if not hasattr(app, "build_cancellation"):
                    app.build_cancellation = build_cancellation.BuildCancellation(
                        app=app,
                        ui=app,
                    )
                app.build_cancellation.cancel_build()
            except Exception:
                pass

        if self._mass_datetime_active:
            self._finish_mass_datetime_build()

        if not self._self_update_launched:
            self._discard_pending_self_update()

        thread = getattr(self, "build_thread", None)
        if thread is not None:
            try:
                is_running = thread.isRunning() if hasattr(thread, "isRunning") else True
                if is_running:
                    thread.quit()
                    if hasattr(thread, "wait"):
                        thread.wait(timeout_ms)
            except RuntimeError:
                pass

        app.building = False
        app.build_process = None
        self.build_thread = None
        self.worker = None

    # ============================================================
    # ETA LOOP
    # ============================================================
    def start_eta(self):
        self.app._eta_running = True
        self._tick_eta()

    def stop_eta(self):
        self.app._eta_running = False

    def _tick_eta(self):
        app = self.app

        if not getattr(app, "_eta_running", False):
            return

        if not getattr(app, "building", False):
            return

        elapsed = int(time.time() - app.build_start_time)
        est_total = app.last_build_seconds
        remaining = max(est_total - elapsed, 0)

        app.status_label.setFont(QFont("Rubik UI", 13, QFont.Bold))
         # 🔑 USE CENTRAL METHOD (keeps alignment + padding)
        self.app.set_status(
            f"Building... {elapsed}s elapsed\napprox {remaining}s remaining"
        )

        QTimer.singleShot(300, self._tick_eta)

    def _get_python_version_suffix(self):
        python_path = getattr(self.app, "python_interpreter_path", "")
        version = "py"

        if python_path:
            try:
                parent = os.path.basename(os.path.dirname(python_path)).lower()
                if parent.startswith("python"):
                    raw = parent.replace("python", "")
                    if raw.isdigit():
                        version = f"py{raw[0]}.{raw[1:]}" if len(raw) > 1 else f"py{raw}"
            except Exception:
                pass

        return version

    def _get_datetime_region_identifier(self):
        if not getattr(self.app, "append_datetime", False):
            return ""

        return DATETIME_FORMAT_REGIONS.get(getattr(self.app, "datetime_format", ""), "")

    def _get_datetime_timestamp_suffix(self):
        if not getattr(self.app, "append_datetime", False):
            return ""

        fmt = getattr(self.app, "datetime_format", "")
        return datetime.now().strftime(fmt) if fmt else ""

    def _build_name_parts(self, script):
        script = os.path.normpath(script) if script else ""
        script_name = os.path.splitext(os.path.basename(script))[0].lower() if script else ""
        parent_name = os.path.basename(os.path.dirname(script)) if script else ""

        parts = []

        if script:
            parts.append(self.app.exe_name_input.text().strip() or "exe")

            if script_name in {"main", "app", "run"} and parent_name:
                parts.append(parent_name)

        return parts

    def _python_output_identity_for_current_settings(self):
        """Return the current output selection and its stable generated-name base."""
        output_input = getattr(self.app, "output_path_input", None)
        script_input = getattr(self.app, "script_path_input", None)
        outdir = output_input.text().strip() if output_input is not None else ""
        script = script_input.text().strip() if script_input is not None else ""
        exe_name = self.app.exe_name_input.text().strip()

        if not outdir or not script or not exe_name:
            return None

        name_base = "_".join(self._build_name_parts(script))
        if not name_base:
            return None

        return (
            os.path.normpath(outdir),
            os.path.normcase(os.path.normpath(script)),
            name_base.casefold(),
        )

    @staticmethod
    def _is_complete_python_output(target):
        target = os.path.normpath(target) if target else ""
        name = os.path.basename(target)
        return bool(target and name and os.path.isfile(os.path.join(target, f"{name}.exe")))

    def _find_latest_python_output(self, identity):
        """Find the newest complete app folder for a newly selected identity."""
        if identity is None:
            return ""

        outdir, _script, name_base = identity
        if not os.path.isdir(outdir):
            return ""

        prefix = name_base + "_"
        candidates = []
        try:
            with os.scandir(outdir) as entries:
                for entry in entries:
                    if not entry.is_dir():
                        continue
                    candidate_name = entry.name
                    normalized_name = candidate_name.casefold()
                    if normalized_name != name_base and not normalized_name.startswith(prefix):
                        continue
                    if self._is_complete_python_output(entry.path):
                        executable = os.path.join(entry.path, f"{candidate_name}.exe")
                        candidates.append((os.path.getmtime(executable), entry.path))
        except OSError:
            return ""

        return max(candidates, default=(0, ""))[1]

    def _set_current_python_output(self, target):
        """Record the exact Python app folder created by the current build."""
        identity = self._python_output_identity_for_current_settings()
        if identity is None:
            return
        self._python_output_identity = identity
        self._python_output_target = os.path.normpath(target) if target else ""

    def latest_python_output_path(self):
        """Return the cached current app folder only while its EXE still exists."""
        identity = self._python_output_identity_for_current_settings()
        if identity != self._python_output_identity:
            self._python_output_identity = identity
            self._python_output_target = self._find_latest_python_output(identity)
        elif not self._python_output_target:
            self._python_output_target = self._find_latest_python_output(identity)

        target = self._python_output_target
        return target if self._is_complete_python_output(target) else ""

    def has_python_output(self):
        """Return whether the current Python build naming base has a complete output."""
        return bool(self.latest_python_output_path())

    def open_python_output_folder(self):
        """Open the latest complete Python app folder, if one is available."""
        target = self.latest_python_output_path()
        if target:
            try:
                os.startfile(target)
            except OSError:
                pass

    def _build_debug_log_name(self, script):
        parts = ["EXE_BUILDER_DEBUG"]
        parts.extend(self._build_name_parts(script))

        datetime_region = self._get_datetime_region_identifier()
        if datetime_region:
            parts.append(datetime_region)

        datetime_timestamp = self._get_datetime_timestamp_suffix()
        if datetime_timestamp:
            parts.append(datetime_timestamp)

        if getattr(self.app, "append_py_version", False):
            parts.append(self._get_python_version_suffix())

        parts.append(datetime.now().strftime("%d-%m-%Y_%H-%M-%S"))

        return "_".join(parts) + ".log"

    def _build_mass_datetime_debug_log_name(self, script):
        parts = [self._mass_datetime_debug_log_prefix]
        parts.extend(self._build_name_parts(script))

        datetime_region = self._get_datetime_region_identifier()
        if datetime_region:
            parts.append(datetime_region)

        datetime_timestamp = self._get_datetime_timestamp_suffix()
        if datetime_timestamp:
            parts.append(datetime_timestamp)

        if getattr(self.app, "append_py_version", False):
            parts.append(self._get_python_version_suffix())

        parts.append(datetime.now().strftime("%d-%m-%Y_%H-%M-%S"))

        return "_".join(parts) + ".txt"

    def _get_pyinstaller_search_paths(self, project_root):
        if not project_root:
            return []

        normalized_root = os.path.normpath(project_root)
        search_paths = [normalized_root]

        parent_root = os.path.dirname(normalized_root)
        if parent_root and parent_root != normalized_root:
            # Sibling packages are often stored one level above the entry script folder.
            search_paths.append(parent_root)

        return search_paths

    def _get_project_asset_data_args(self, project_root):
        if not project_root or not os.path.isdir(project_root):
            return []

        normalized_root = os.path.normpath(project_root)
        scan_roots = [normalized_root]
        project_container = self._find_nearest_project_container(normalized_root)
        if (
            project_container
            and os.path.normcase(project_container) != os.path.normcase(normalized_root)
        ):
            scan_roots.append(project_container)

        data_args = []
        seen = set()
        skipped_dirnames = {
            ".git",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            "__pycache__",
            "build",
            "dist",
            "env",
            "spec",
            "venv",
            ".venv",
        }

        for data_root in scan_roots:
            for folder, dirnames, filenames in os.walk(data_root):
                dirnames[:] = sorted(
                    dirname
                    for dirname in dirnames
                    if dirname.lower() not in skipped_dirnames
                )
                for filename in sorted(filenames):
                    if Path(filename).suffix.lower() not in {".ahk", ".png", ".svg"}:
                        continue

                    source_path = os.path.normpath(os.path.join(folder, filename))
                    destination = os.path.relpath(folder, data_root)
                    if destination == ".":
                        destination = "."
                    else:
                        destination = os.path.normpath(destination)

                    key = (os.path.normcase(source_path), os.path.normcase(destination))
                    if key in seen:
                        continue

                    seen.add(key)
                    data_args.append(f"--add-data={source_path}{os.pathsep}{destination}")

        return data_args

    def _find_nearest_project_container(self, project_root):
        fallback_markers = ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")
        ancestors = []
        current = Path(project_root).resolve()

        for _ in range(3):
            ancestors.append(current)
            parent = current.parent
            if parent == current:
                break
            current = parent

        # A nested source folder can carry its own requirements.txt while shared
        # runtime assets live at the enclosing repository root. Prefer that root
        # so asset destinations remain relative to the repository layout.
        for ancestor in ancestors:
            if (ancestor / ".git").exists():
                return os.path.normpath(str(ancestor))

        for ancestor in ancestors:
            if any((ancestor / marker).exists() for marker in fallback_markers):
                return os.path.normpath(str(ancestor))

        return ""

    def _get_desktop_path(self):
        return os.path.normpath(os.path.join(os.path.expanduser("~"), "Desktop"))

    def _is_desktop_output_path(self, output_dir):
        return (
            self._normalize_explorer_path_for_compare(output_dir)
            == self._normalize_explorer_path_for_compare(self._get_desktop_path())
        )

    def _normalize_explorer_path_for_compare(self, path):
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

    def _focus_window_by_handle(self, hwnd):
        if not hwnd:
            return False

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
                return True
            except Exception:
                return False

    def _focus_existing_output_explorer_window(self, output_dir):
        if sys.platform != "win32":
            return False

        target_path = self._normalize_explorer_path_for_compare(output_dir)
        if not target_path:
            return False

        try:
            import win32com.client

            windows = win32com.client.Dispatch("Shell.Application").Windows()
        except Exception:
            return False

        try:
            count = windows.Count
        except Exception:
            return False

        for index in range(count):
            try:
                window = windows.Item(index)
            except Exception:
                continue

            window_path = self._normalize_explorer_path_for_compare(
                self._get_explorer_window_path(window)
            )
            if window_path != target_path:
                continue

            try:
                hwnd = int(window.HWND)
            except Exception:
                hwnd = None

            return self._focus_window_by_handle(hwnd)

        return False

    def _desktop_build_group_paths(self):
        app = self.app
        paths = list(getattr(app, "current_build_paths", []) or [])
        debug_log_path = getattr(app, "debug_log_path", "")
        if debug_log_path:
            paths.append(debug_log_path)

        existing_paths = []
        seen = set()
        for path in paths:
            normalized = os.path.normpath(path) if path else ""
            if not normalized or not os.path.exists(normalized):
                continue

            key = self._normalize_explorer_path_for_compare(normalized)
            if key in seen:
                continue

            existing_paths.append(normalized)
            seen.add(key)

        return existing_paths

    def _find_desktop_list_view(self):
        if sys.platform != "win32":
            return None

        try:
            import win32gui
        except Exception:
            return None

        def list_view_from_def_view(def_view):
            if not def_view:
                return None
            try:
                return win32gui.FindWindowEx(def_view, 0, "SysListView32", None)
            except Exception:
                return None

        try:
            progman = win32gui.FindWindow("Progman", None)
            list_view = list_view_from_def_view(
                win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None)
            )
            if list_view:
                return list_view
        except Exception:
            pass

        found = []

        def enum_windows(hwnd, _lparam):
            if found:
                return False
            try:
                def_view = win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None)
            except Exception:
                def_view = None

            list_view = list_view_from_def_view(def_view)
            if list_view:
                found.append(list_view)
                return False
            return True

        try:
            win32gui.EnumWindows(enum_windows, None)
        except Exception:
            return None

        return found[0] if found else None

    def _desktop_icon_count(self, list_view):
        try:
            import win32gui

            return int(win32gui.SendMessage(list_view, 0x1004, 0, 0))
        except Exception:
            return 0

    def _desktop_icon_text(self, list_view, index):
        try:
            import ctypes
        except Exception:
            return ""

        try:
            import win32process

            _thread_id, process_id = win32process.GetWindowThreadProcessId(list_view)
        except Exception:
            return ""

        if not process_id:
            return ""

        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        kernel32.OpenProcess.argtypes = [
            ctypes.c_uint,
            ctypes.c_bool,
            ctypes.c_uint,
        ]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.VirtualAllocEx.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_uint,
            ctypes.c_uint,
        ]
        kernel32.VirtualAllocEx.restype = ctypes.c_void_p
        kernel32.WriteProcessMemory.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        kernel32.WriteProcessMemory.restype = ctypes.c_bool
        kernel32.ReadProcessMemory.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        kernel32.ReadProcessMemory.restype = ctypes.c_bool
        kernel32.VirtualFreeEx.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_uint,
        ]
        kernel32.VirtualFreeEx.restype = ctypes.c_bool
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_bool
        user32.SendMessageW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_size_t,
            ctypes.c_void_p,
        ]
        user32.SendMessageW.restype = ctypes.c_ssize_t

        PROCESS_VM_OPERATION = 0x0008
        PROCESS_VM_READ = 0x0010
        PROCESS_VM_WRITE = 0x0020
        PROCESS_QUERY_INFORMATION = 0x0400
        MEM_COMMIT = 0x1000
        MEM_RELEASE = 0x8000
        MEM_RESERVE = 0x2000
        PAGE_READWRITE = 0x04
        LVIF_TEXT = 0x0001
        LVM_GETITEMTEXTW = 0x1073
        text_chars = 260
        text_bytes = text_chars * ctypes.sizeof(ctypes.c_wchar)

        class LVITEMW(ctypes.Structure):
            _fields_ = [
                ("mask", ctypes.c_uint),
                ("iItem", ctypes.c_int),
                ("iSubItem", ctypes.c_int),
                ("state", ctypes.c_uint),
                ("stateMask", ctypes.c_uint),
                ("pszText", ctypes.c_void_p),
                ("cchTextMax", ctypes.c_int),
                ("iImage", ctypes.c_int),
                ("lParam", ctypes.c_ssize_t),
                ("iIndent", ctypes.c_int),
                ("iGroupId", ctypes.c_int),
                ("cColumns", ctypes.c_uint),
                ("puColumns", ctypes.c_void_p),
                ("piColFmt", ctypes.c_void_p),
                ("iGroup", ctypes.c_int),
            ]

        process = None
        remote_text = None
        remote_item = None
        try:
            access = (
                PROCESS_VM_OPERATION
                | PROCESS_VM_READ
                | PROCESS_VM_WRITE
                | PROCESS_QUERY_INFORMATION
            )
            process = kernel32.OpenProcess(access, False, process_id)
            if not process:
                return ""

            remote_text = kernel32.VirtualAllocEx(
                process,
                None,
                text_bytes,
                MEM_COMMIT | MEM_RESERVE,
                PAGE_READWRITE,
            )
            remote_item = kernel32.VirtualAllocEx(
                process,
                None,
                ctypes.sizeof(LVITEMW),
                MEM_COMMIT | MEM_RESERVE,
                PAGE_READWRITE,
            )
            if not remote_text or not remote_item:
                return ""

            item = LVITEMW()
            item.mask = LVIF_TEXT
            item.iItem = index
            item.iSubItem = 0
            item.pszText = remote_text
            item.cchTextMax = text_chars

            written = ctypes.c_size_t()
            if not kernel32.WriteProcessMemory(
                process,
                remote_item,
                ctypes.byref(item),
                ctypes.sizeof(item),
                ctypes.byref(written),
            ):
                return ""

            user32.SendMessageW(list_view, LVM_GETITEMTEXTW, index, remote_item)

            buffer = ctypes.create_string_buffer(text_bytes)
            read = ctypes.c_size_t()
            if not kernel32.ReadProcessMemory(
                process,
                remote_text,
                buffer,
                text_bytes,
                ctypes.byref(read),
            ):
                return ""

            return buffer.raw.decode("utf-16-le", errors="ignore").split("\x00", 1)[0]
        except Exception:
            return ""
        finally:
            try:
                if remote_text:
                    kernel32.VirtualFreeEx(process, remote_text, 0, MEM_RELEASE)
                if remote_item:
                    kernel32.VirtualFreeEx(process, remote_item, 0, MEM_RELEASE)
                if process:
                    kernel32.CloseHandle(process)
            except Exception:
                pass

    def _desktop_icon_indices_by_name(self, list_view):
        indices = {}
        for index in range(self._desktop_icon_count(list_view)):
            name = self._desktop_icon_text(list_view, index)
            if not name:
                continue
            indices.setdefault(name.casefold(), index)
        return indices

    def _primary_available_desktop_rect(self):
        try:
            from PySide6.QtGui import QGuiApplication

            screen = QGuiApplication.primaryScreen()
            if screen:
                geometry = screen.availableGeometry()
                return geometry.x(), geometry.y(), geometry.width(), geometry.height()
        except Exception:
            pass

        if sys.platform == "win32":
            try:
                import ctypes

                user32 = ctypes.windll.user32
                return 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            except Exception:
                pass

        return 0, 0, 1280, 720

    def _centered_desktop_icon_positions(self, count):
        if count <= 0:
            return []

        x, y, width, height = self._primary_available_desktop_rect()
        columns = 1 if count == 1 else 2 if count <= 4 else 3
        rows = (count + columns - 1) // columns
        spacing_x = 112
        spacing_y = 96
        group_width = (columns - 1) * spacing_x
        group_height = (rows - 1) * spacing_y
        start_x = int(x + max(0, width - group_width) / 2)
        start_y = int(y + max(0, height - group_height) / 2)

        return [
            (
                start_x + (index % columns) * spacing_x,
                start_y + (index // columns) * spacing_y,
            )
            for index in range(count)
        ]

    def _set_desktop_icon_position(self, list_view, index, x, y):
        try:
            import win32gui

            lparam = ((int(y) & 0xFFFF) << 16) | (int(x) & 0xFFFF)
            win32gui.SendMessage(list_view, 0x100F, index, lparam)
            return True
        except Exception:
            return False

    def _move_desktop_icons_to_center(self, paths):
        list_view = self._find_desktop_list_view()
        if not list_view:
            return False

        indices_by_name = self._desktop_icon_indices_by_name(list_view)
        icon_indices = []
        for path in paths:
            name = os.path.basename(os.path.normpath(path))
            candidate_names = [name]
            stem, extension = os.path.splitext(name)
            if extension:
                candidate_names.append(stem)

            icon_index = None
            for candidate_name in candidate_names:
                icon_index = indices_by_name.get(candidate_name.casefold())
                if icon_index is not None:
                    break

            if icon_index is not None:
                icon_indices.append(icon_index)

        if not icon_indices:
            return False

        moved = False
        for icon_index, (x, y) in zip(
            icon_indices,
            self._centered_desktop_icon_positions(len(icon_indices)),
        ):
            moved = self._set_desktop_icon_position(list_view, icon_index, x, y) or moved

        return moved

    def _center_desktop_build_outputs(self):
        paths = self._desktop_build_group_paths()
        if not paths:
            return False

        try:
            return self._move_desktop_icons_to_center(paths)
        except Exception:
            return False

    def _present_successful_build_outputs(self, output_dir=None):
        output_dir = os.path.normpath(
            output_dir if output_dir is not None else getattr(self.app, "output_path", "") or ""
        )
        if not output_dir or not os.path.isdir(output_dir):
            return

        if self._is_desktop_output_path(output_dir):
            try:
                self._center_desktop_build_outputs()
            except Exception:
                pass
            return

        self._maybe_open_output_directory_on_success(output_dir)

    def _present_successful_mass_datetime_outputs(self):
        output_dir = os.path.normpath(getattr(self.app, "output_path", "") or "")
        if not output_dir or not os.path.isdir(output_dir):
            return

        if self._is_desktop_output_path(output_dir):
            try:
                self._center_desktop_build_outputs()
            except Exception:
                pass
            return

        self._maybe_open_output_directory_on_success()

    def _run_success_post_build_action(self):
        app = self.app
        self._run_built_application_on_success()
        if getattr(app, "minimize_after_build_enabled", False):
            app.showMinimized()
        if getattr(app, "close_after_build_enabled", False):
            app.close_app()

    def _run_built_application_on_success(self):
        """Launch the executable produced by this build, when requested."""
        app = self.app
        if not getattr(app, "run_built_app_after_build_enabled", False):
            return

        executable = ""
        if getattr(app, "build_mode", "python") == "python":
            output = self.latest_python_output_path()
            if output:
                executable = os.path.join(output, f"{os.path.basename(output)}.exe")
        else:
            name_input = getattr(app, "dotnet_name_input", None)
            name = name_input.text().strip() if name_input is not None else ""
            for output in reversed(getattr(app, "current_build_paths", []) or []):
                candidate = os.path.join(output, f"{name}.exe") if name else ""
                if candidate and os.path.isfile(candidate):
                    executable = candidate
                    break

        if not executable or not os.path.isfile(executable):
            return
        try:
            os.startfile(executable)
        except OSError:
            pass

    def _maybe_open_output_directory_on_success(self, output_dir=None):
        app = self.app

        if not getattr(app, "open_output_dir_after_build_enabled", False):
            return

        output_dir = os.path.normpath(
            output_dir if output_dir is not None else getattr(app, "output_path", "") or ""
        )
        if not output_dir or not os.path.isdir(output_dir):
            return

        if self._is_desktop_output_path(output_dir):
            return

        try:
            focused_existing_window = self._focus_existing_output_explorer_window(output_dir)
        except Exception:
            focused_existing_window = False

        if focused_existing_window:
            return

        try:
            os.startfile(output_dir)
        except Exception:
            pass

    def _initialize_debug_log(self, script, outdir):
        app = self.app
        if self._mass_datetime_active:
            self._initialize_mass_datetime_debug_log(script, outdir)
            return

        app.debug_log_path = os.path.join(outdir, self._build_debug_log_name(script)) if outdir else ""

        if not app.debug_log_path or not os.path.isdir(outdir):
            return

        try:
            with open(app.debug_log_path, "w", encoding="utf-8") as f:
                _write_debug_log_banner(f, "BUILD STARTED")
                _write_debug_log_section(
                    f,
                    "Build Inputs",
                    [
                        f"ENTRY_SCRIPT={repr(app.entry_script)}",
                        f"PROJECT_ROOT={repr(app.project_root)}",
                        f"OUTPUT_DIR={repr(outdir)}",
                        f"PYTHON_INTERPRETER_PATH={repr(app.python_interpreter_path)}",
                        f"IS_FROZEN={getattr(sys, 'frozen', False)}",
                    ],
                )
        except OSError:
            pass

    def _initialize_mass_datetime_debug_log(self, script, outdir):
        app = self.app
        is_first_mass_log_write = not self._mass_datetime_debug_log_path

        if is_first_mass_log_write and outdir:
            self._mass_datetime_debug_log_path = os.path.join(
                outdir,
                self._build_mass_datetime_debug_log_name(script),
            )

        app.debug_log_path = self._mass_datetime_debug_log_path

        if not app.debug_log_path or not os.path.isdir(outdir):
            return

        try:
            mode = "w" if is_first_mass_log_write else "a"

            with open(app.debug_log_path, mode, encoding="utf-8") as f:
                if is_first_mass_log_write:
                    _write_debug_log_banner(
                        f,
                        f"BUILD ALL {self._mass_datetime_log_title} OUTPUTS STARTED",
                    )

                _write_debug_log_banner(
                    f,
                    (
                        f"OUTPUT {self._mass_datetime_index}/"
                        f"{self._mass_datetime_total}: "
                        f"{self._mass_datetime_current_label}"
                    ),
                )
                _write_debug_log_section(
                    f,
                    "Build Inputs",
                    [
                        f"ENTRY_SCRIPT={repr(app.entry_script)}",
                        f"PROJECT_ROOT={repr(app.project_root)}",
                        f"OUTPUT_DIR={repr(outdir)}",
                        f"PYTHON_INTERPRETER_PATH={repr(app.python_interpreter_path)}",
                        f"IS_FROZEN={getattr(sys, 'frozen', False)}",
                    ],
                )
        except OSError:
            pass

    # -------------------------------------------------------------
    # Build EXE
    # -------------------------------------------------------------

    def build_exe(self, app=None):
        app = self.app

        datetime_dropdown_data = self._datetime_dropdown_data()

        if not self._mass_datetime_active and not app.build_process:
            self._discard_pending_self_update()
            self._self_update_launched = False

        if (
            not self._mass_datetime_active
            and datetime_dropdown_data
            in {
                MASS_DATETIME_BUILD_SENTINEL,
                ISO_MASS_DATETIME_BUILD_SENTINEL,
                UK_MASS_DATETIME_BUILD_SENTINEL,
                USA_MASS_DATETIME_BUILD_SENTINEL,
            }
        ):
            self._start_mass_datetime_build(datetime_dropdown_data)
            return

        app.building = True
        app._eta_running = True

        # ==================================================
        # CANCEL MODE
        # ==================================================

        from ..build import build_cancellation
        app.build_cancellation = build_cancellation.BuildCancellation(
            app=app, ui=app
        )


        if app.build_process:
            app.build_cancellation.cancel_build()
            self._cancel_mass_datetime_build()
            return

      
        # ==================================================
        # READ UI VALUES
        # ==================================================
        
        script = app.script_path_input.text().strip()
        outdir = app.output_path_input.text().strip()
        icon = getattr(app, "icon_path", "").strip()
        
        script = os.path.normpath(script) if script else ""
        outdir = os.path.normpath(outdir) if outdir else ""
        icon = os.path.normpath(icon) if icon else ""
        app.icon_path = icon

        entry_point = app.entry_script
        project_root = app.project_root

        if not entry_point and script and os.path.isfile(script):
            entry_point = script
            project_root = os.path.dirname(script)

        app.entry_script = entry_point
        app.project_root = project_root
        app.output_path = outdir
        self._initialize_debug_log(script, outdir)

        # ==================================================
        # Bundle validation
        # ==================================================

        ok, error = validate_bundle_inputs(app)

        if not ok:
            self._abort_current_build(error)
            return

        try:
            project_manifest = load_project_build_manifest(project_root)
        except ProjectBuildManifestError as exc:
            self._abort_current_build(f"Invalid project build manifest: {exc}")
            return

        # ==================================================
        # ENTER BUILD MODE
        # ==================================================

        app.build_btn.setText("Cancel EXE")
        self._disconnect_build_button_clicked()
        app.build_btn.clicked.connect(self.build_exe)
        app.status_label.setFixedWidth(250)
        app.validation_controller.update_ui_state()
        
        app.build_start_time = time.time()
        self.start_eta()
        
        # ==================================================
        # Final validation
        # ==================================================

        if not entry_point or not os.path.isfile(entry_point):
            self._abort_current_build("Invalid or missing entry script.")
            return

        if not project_root or not os.path.isdir(project_root):
            self._abort_current_build("Invalid project folder.")
            return

        exe_name = app.exe_name_input.text().strip()
        if not exe_name:
            self._abort_current_build("Please enter an EXE name.")
            return

        # ==================================================
        # Resolve PyInstaller (ALWAYS via Python interpreter)
        # ==================================================

        python = app.python_interpreter_path
        if not python or not os.path.isfile(python):
            self._abort_current_build(
                "Python interpreter not found.\n"
                "Please select a Python interpreter before building."
            )
            return  

        try:
            with external_python_environment() as env:
                result = subprocess.run(
                    [python, "-m", "PyInstaller", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30,
                    env=env,
                    creationflags=CREATE_NO_WINDOW
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self._abort_current_build(f"Could not start PyInstaller: {exc}")
            return

        if result.returncode != 0:
            self._abort_current_build(
                "PyInstaller is not available in the selected Python interpreter.\n\n"
                "Install it with:\n\npip install pyinstaller"
            )
            return

        cmd_prefix = [python, "-m", "PyInstaller"]

        app.status_label.setText("Using PyInstaller (python -m)")
        app.repaint()
        
        # --------------------------------------------------
        # OUTPUT FOLDER SAFETY CHECK (exists + writable)
        # --------------------------------------------------

        if not outdir or not os.path.isdir(outdir):
            self._abort_current_build("Output folder does not exist.")
            return

        # 🔑 Test write access (handles protected folders)
        try:
            test_file = os.path.join(outdir, "__write_test.tmp")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
        except Exception:
            app.validation_controller.set_build_error(
                f"ERROR — Cannot write to this folder\n{outdir}\n"
                "This location is read-only. Choose another."
            )

            self.stop_eta()
            app.building = False
            app.build_process = None
            if self._mass_datetime_active:
                self._finish_mass_datetime_build()

            app.validation_controller.update_ui_state()
            return
        
        # ==================================================
        # Build paths
        # ==================================================

        app.last_build_counter += 1
        timestamp = self._get_datetime_timestamp_suffix()
        

        script_path = Path(script)
        script_name = script_path.stem.lower()

        parts = [exe_name]

        # 🔑 prevent overwrite for common entry files
        if script_name in {"main", "app", "run"}:
            parent_name = script_path.parent.name
            if parent_name:
                parts.append(parent_name)

        # date/time
        datetime_region = self._get_datetime_region_identifier()
        if datetime_region:
            parts.append(datetime_region)
        if timestamp:
            parts.append(timestamp)

        # python version
        if getattr(app, "append_py_version", False):
            parts.append(self._get_python_version_suffix())

        final_exe_name = "_".join(parts)

        build_root = os.path.join(outdir, "build")
        build_path = os.path.join(build_root, final_exe_name)
        spec_path = os.path.join(outdir, "spec", final_exe_name)
        target_dir = os.path.join(outdir, final_exe_name)
        self_update_plan = None
        dist_path = outdir

        if is_frozen_self_target(target_dir):
            self_update_plan = create_self_update_plan(
                target_dir,
                final_exe_name + ".exe",
                app.debug_log_path,
            )
            self._pending_self_update = self_update_plan
            dist_path = self_update_plan.staging_root

        self._active_self_update_plan = self_update_plan

        expected_exe_path = _expected_pyinstaller_exe_path(
            build_root,
            final_exe_name,
        )
        if len(expected_exe_path) >= WINDOWS_RESOURCE_PATH_LIMIT:
            self._abort_current_build(
                "Generated build path is too long for Windows resource tools "
                f"({len(expected_exe_path)} characters; maximum is "
                f"{WINDOWS_RESOURCE_PATH_LIMIT - 1}).\n"
                "Choose a shorter EXE name or output folder.\n"
                f"{expected_exe_path}"
            )
            return

        output_cleanup_path = (
            self_update_plan.staging_root if self_update_plan else target_dir
        )
        try:
            for stale_path in (output_cleanup_path, build_path, spec_path):
                if os.path.isdir(stale_path):
                    if (
                        not self_update_plan
                        and os.path.normcase(os.path.abspath(stale_path))
                        == os.path.normcase(os.path.abspath(target_dir))
                    ):
                        try:
                            clear_output_folder_icon_metadata(stale_path)
                        except Exception:
                            pass
                    shutil.rmtree(stale_path)
                elif os.path.exists(stale_path):
                    os.remove(stale_path)

                if os.path.exists(stale_path):
                    raise OSError("The path still exists after cleanup.")
        except OSError as exc:
            self._abort_current_build(
                "Could not replace the existing build output.\n"
                "Close any running copy of the generated EXE, or any other "
                "program using its files, then try again.\n"
                f"Locked path: {stale_path}\n"
                f"Windows reported: {exc}"
            )
            return

        os.makedirs(build_root, exist_ok=True)
        os.makedirs(spec_path, exist_ok=True)

        excluded_modules = set(project_manifest.exclude_modules)

        # Tkinter is part of the standard library and PyInstaller discovers it
        # when the entry point actually imports it. Forcing it into every build
        # also forces pyi_rth__tkinter into non-Tk applications. With Python
        # 3.14's Tcl 9 zipfs layout, PyInstaller can then install the runtime
        # hook without collecting _tcl_data/_tk_data, making an otherwise valid
        # PySide application fail before its own code starts.
        default_collect_all = ("qt_material",)

        cmd = [
            *cmd_prefix,
            "--onedir",
            "--clean",
            "--noconfirm",
            *(
                f"--collect-all={name}"
                for name in default_collect_all
                if name not in excluded_modules
            ),
            "--windowed",
            "--noconsole",
            "--hidden-import=pynput",
            "--hidden-import=win32gui",
            "--hidden-import=win32con",
            "--hidden-import=win32api",
            "--hidden-import=win32process",
            "--hidden-import=pygetwindow",
            "--hidden-import=pystray",
            f"--distpath={dist_path}",
            f"--workpath={build_root}",
            f"--specpath={spec_path}",
            f"--name={final_exe_name}",
        ]

        for search_path in self._get_pyinstaller_search_paths(project_root):
            cmd.append(f"--paths={search_path}")

        if project_root:
            cmd.append(f"--add-data={project_root}{os.pathsep}.")

        cmd.extend(self._get_project_asset_data_args(project_root))

        cmd.extend(project_manifest.pyinstaller_args())

        icon_contract = resolve_build_icon_contract(icon)

        data_file = os.path.join(project_root, "screen_mover_state.json")
        if os.path.isfile(data_file):
            cmd.append(f"--add-data={data_file}{os.pathsep}.")

        try:
            cmd.extend(icon_contract.pyinstaller_args)
        except OSError as exc:
            self._abort_current_build(f"Could not prepare build icon hook: {exc}")
            return

        cmd.append(entry_point)

        app.current_build_paths = [
            output_cleanup_path,
            build_path,
            spec_path,
        ]

        # ==================================================
        # Run PyInstaller (threaded)
        # ==================================================

        app.status_label.setText("Building...")
        # ⛔ move this OUT of thread (safe here)


        self.build_thread = QThread()
        self.worker = BuildWorker(app, cmd)

        self.worker.moveToThread(self.build_thread)

        self.build_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_build_complete)

        # cleanup
        self.worker.finished.connect(self.build_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.build_thread.finished.connect(self.build_thread.deleteLater)

        self.build_thread.start()

    def on_build_complete(self, ret, out, err):
        # 🔑 ONLY emit — NO UI CODE HERE
        self.build_complete_signal.emit(ret, out, err)

    def _on_build_complete_ui(self, ret, out, err):
        app = self.app
        if getattr(app, "_is_closing", False):
            self.stop_eta()
            app.building = False
            app.build_process = None
            return

        active_self_update = self._active_self_update_plan
        self._active_self_update_plan = None
        if ret == 0 and active_self_update is not None:
            try:
                validate_self_update_plan(active_self_update)
            except SelfUpdateError as exc:
                ret = -1
                err = str(exc)
            else:
                app.current_build_paths = [
                    active_self_update.target_dir
                    if os.path.normcase(os.path.abspath(path))
                    == os.path.normcase(
                        os.path.abspath(active_self_update.staging_root)
                    )
                    else path
                    for path in app.current_build_paths
                ]

        mass_active = self._mass_datetime_active
        mass_completed_successfully = False

        if ret == 0:
            completed_output = next(
                (
                    path for path in getattr(app, "current_build_paths", [])
                    if self._is_complete_python_output(path)
                ),
                "",
            )
            if completed_output:
                self._set_current_python_output(completed_output)
            app.last_build_seconds = int(time.time() - app.build_start_time)
            if mass_active:
                self._remember_mass_datetime_output_group()

            if mass_active and self._mass_datetime_queue:
                self.stop_eta()
                app.building = False
                app.build_process = None
                QTimer.singleShot(0, self._run_next_mass_datetime_build)
                return

            if mass_active:
                self._finish_mass_datetime_build(clear_output_group=False)
                self._apply_mass_datetime_output_group()
                self._reset_mass_datetime_output_group()
                mass_completed_successfully = True
                msg = "Mass date/time build complete."
            else:
                msg = "Build complete."

            app.status_label.setStyleSheet(status_text_style(Colors.SUCCESS, border_width=1))

        else:
            self._discard_pending_self_update()
            if mass_active:
                failed_label = self._mass_datetime_current_label
                self._finish_mass_datetime_build()
                msg = f"Mass build failed on {failed_label}. See debug log."
            else:
                msg = "Build failed. See debug log."
            app.status_label.setStyleSheet(status_text_style(Colors.ERROR, border_width=1))

        self.stop_eta()
        app.building = False
        app.build_process = None

        app._status_lock = True
        app.set_status(msg)
        app.validation_controller.update_build_button()
        app.validation_controller.update_ui_state()

        if ret == 0:
            if self._pending_self_update is not None:
                app.state_ctrl.save_state()
                self._schedule_pending_self_update()
                return
            if mass_completed_successfully:
                self._present_successful_mass_datetime_outputs()
            else:
                self._present_successful_build_outputs()
            app.state_ctrl.save_state()
            self._run_success_post_build_action()
        
            
        QTimer.singleShot(5000, self._unlock_status)

    def _unlock_status(self):
        app = self.app
        app._status_lock = False
        app.validation_controller.update_ui_state()

    # ============================================================
    # ETA time estimator
    # ============================================================
    def update_eta_loop(self):
        if not getattr(self.app, "_eta_running", False):
            return

        if not getattr(self.app, "building", False):
            return

        elapsed = int(time.time() - self.app.build_start_time)
        est_total = self.app.last_build_seconds
        remaining = max(est_total - elapsed, 0)

        self.app.status_label.setFont(QFont("Rubik UI", 13, QFont.Bold))

        # 🔑 USE CENTRAL METHOD (keeps alignment + padding)
        self.app.set_status(
            f"Building... {elapsed}s elapsed\napprox {remaining}s remaining"
        )

        self.app.status_label.setFixedSize(420, 95)

        QTimer.singleShot(1, self.update_eta_loop)


class BuildWorker(QObject):
    finished = Signal(int, str, str)  # ret, stdout, stderr

    def __init__(self, app, cmd):
        super().__init__()
        self.app = app
        self.cmd = cmd

    def run(self):
        try:
            with open(self.app.debug_log_path, "a", encoding="utf-8") as f:
                _write_debug_log_section(
                    f,
                    "PyInstaller Command",
                    [
                        "ENTERED run_build",
                        "CMD: " + " ".join(self.cmd),
                    ],
                )

            # Write directly to disk: output is visible while PyInstaller runs,
            # and large builds cannot fill a pipe or accumulate unbounded RAM.
            with open(self.app.debug_log_path, "a", encoding="utf-8") as log:
                log.write("--- Live PyInstaller Output (stdout + stderr) ---\n")
                log.flush()
                with external_python_environment() as env:
                    env["PYTHONUNBUFFERED"] = "1"
                    env["PYTHONIOENCODING"] = "utf-8"
                    proc = subprocess.Popen(
                        self.cmd,
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        env=env,
                        creationflags=CREATE_NO_WINDOW
                    )
                self.app.build_process = proc
                ret = proc.wait()
            out, err = "", ""

            with open(self.app.debug_log_path, "a", encoding="utf-8") as f:
                f.write("--- Build Result ---\n")
                f.write(f"  RETURN CODE: {ret}\n")
                _write_debug_log_stderr(f, err)

        except Exception as e:
            ret = -1
            out = ""
            err = str(e)
            try:
                with open(self.app.debug_log_path, "a", encoding="utf-8") as log:
                    log.write(f"\nBUILD ERROR: {err}\n")
            except OSError:
                pass

        self.finished.emit(ret, out, err)
