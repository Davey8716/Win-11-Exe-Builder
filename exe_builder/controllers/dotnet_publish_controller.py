"""The isolated ``dotnet publish`` workflow used by the C# build mode."""

import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET

from PySide6.QtCore import QObject, QThread, Signal

from ..build.build_cancellation import BuildCancellation
from ..ui.styles import (
    Colors,
    build_disabled_line_edit_style,
    line_edit_style,
    status_text_style,
)


CREATE_NO_WINDOW = 0x08000000
_INVALID_WINDOWS_NAME = re.compile(r'[<>:"/\\|?*]|[. ]$')
_RESERVED_WINDOWS_NAMES = {
    "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def is_sdk_style_project(project_path):
    """Return whether *project_path* is an SDK-style C# project file."""
    try:
        root = ET.parse(project_path).getroot()
    except (OSError, ET.ParseError):
        return False
    return bool(root.attrib.get("Sdk") or root.attrib.get("sdk"))


def validate_executable_name(name):
    name = (name or "").strip()
    if not name:
        return "Please enter an executable name."
    stem = os.path.splitext(name)[0]
    if _INVALID_WINDOWS_NAME.search(name) or stem.upper() in _RESERVED_WINDOWS_NAMES:
        return "Executable name contains unsupported Windows filename characters."
    return ""


def build_dotnet_publish_command(project, output_dir, name, runtime, self_contained,
                                single_file, trim, icon=""):
    """Build a non-mutating dotnet publish command for the selected options."""
    target = os.path.join(output_dir, name)
    cmd = [
        "dotnet", "publish", project, "-c", "Release", "-r", runtime,
        "--self-contained", "true" if self_contained else "false",
        "-p:AssemblyName=" + name,
        "-p:PublishSingleFile=" + ("true" if single_file else "false"),
        "-p:PublishTrimmed=" + ("true" if trim else "false"),
        "-o", target,
    ]
    if icon:
        cmd.append("-p:ApplicationIcon=" + icon)
    return cmd


class DotnetPublishWorker(QObject):
    finished = Signal(int, str)

    def __init__(self, app, command, log_path):
        super().__init__()
        self.app = app
        self.command = command
        self.log_path = log_path

    def run(self):
        ret, error = -1, ""
        try:
            with open(self.log_path, "a", encoding="utf-8") as log:
                log.write("--- dotnet publish command ---\n")
                log.write("CMD: " + " ".join(self.command) + "\n\n")
                log.flush()
                proc = subprocess.Popen(
                    self.command, stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, creationflags=CREATE_NO_WINDOW,
                )
                self.app.build_process = proc
                ret = proc.wait()
                log.write(f"\n--- Publish result: {ret} ---\n")
        except Exception as exc:  # surfaced on the UI thread
            error = str(exc)
        self.finished.emit(ret, error)


class DotnetPublishController(QObject):
    publish_finished = Signal(int, str)

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.thread = None
        self.worker = None
        self._cancelled = False
        self.publish_finished.connect(self._on_publish_finished)

    def values(self):
        app = self.app
        def norm(value):
            value = (value or "").strip()
            return os.path.normpath(value) if value else ""
        return {
            "project": norm(app.dotnet_project_input.text()),
            "output": norm(app.dotnet_output_input.text()),
            "name": app.dotnet_name_input.text().strip(),
            "icon": norm(app.dotnet_icon_input.text()),
            "runtime": app.dotnet_runtime_combo.currentData(),
            "self_contained": app.dotnet_self_contained.isChecked(),
            "single_file": app.dotnet_single_file.isChecked(),
            "trim": app.dotnet_trim.isChecked(),
        }

    def output_path(self):
        values = self.values()
        return os.path.join(values["output"], values["name"]) if values["output"] and values["name"] else ""

    def validation_error(self, check_sdk=False):
        values = self.values()
        if not values["project"] or not os.path.isfile(values["project"]):
            return "Select an existing .csproj file."
        if not values["project"].lower().endswith(".csproj") or not is_sdk_style_project(values["project"]):
            return "C# mode supports SDK-style .csproj projects only."
        if not values["output"] or not os.path.isdir(values["output"]):
            return "Select an existing output folder."
        name_error = validate_executable_name(values["name"])
        if name_error:
            return name_error
        if values["icon"] and (not os.path.isfile(values["icon"]) or not values["icon"].lower().endswith(".ico")):
            return "Application icon must be an existing .ico file."
        if values["runtime"] not in {"win-x64", "win-arm64"}:
            return "Select a Windows target runtime."
        if check_sdk:
            try:
                result = subprocess.run(["dotnet", "--version"], capture_output=True, text=True,
                                        timeout=15, creationflags=CREATE_NO_WINDOW)
            except (OSError, subprocess.TimeoutExpired):
                return "The .NET SDK (dotnet) was not found."
            if result.returncode != 0:
                return "The .NET SDK (dotnet) was not found."
        return ""

    def refresh_ui(self):
        if not hasattr(self.app, "dotnet_publish_btn"):
            return
        building = getattr(self.app, "building", False)
        values = self.values()
        project_ok = bool(
            values["project"]
            and values["project"].lower().endswith(".csproj")
            and os.path.isfile(values["project"])
            and is_sdk_style_project(values["project"])
        )
        output_ok = bool(values["output"] and os.path.isdir(values["output"]))
        icon_ok = bool(
            values["icon"]
            and values["icon"].lower().endswith(".ico")
            and os.path.isfile(values["icon"])
        )
        if building:
            styles = [build_disabled_line_edit_style()] * 4
        else:
            styles = [
                line_edit_style(Colors.SUCCESS if project_ok else Colors.ERROR),
                line_edit_style(Colors.SUCCESS if output_ok else Colors.ERROR),
                line_edit_style(
                    Colors.MUTED_BORDER if not values["icon"]
                    else Colors.SUCCESS if icon_ok else Colors.ERROR
                ),
                line_edit_style(
                    Colors.SUCCESS if not validate_executable_name(values["name"])
                    else Colors.ERROR
                ),
            ]
        for field, style in zip(
            (
                self.app.dotnet_project_input,
                self.app.dotnet_output_input,
                self.app.dotnet_icon_input,
                self.app.dotnet_name_input,
            ),
            styles,
        ):
            field.setStyleSheet(style)

        error = self.validation_error()
        self.app.dotnet_publish_btn.setEnabled(building or not error)
        self.app.dotnet_publish_btn.setText("Cancel Publish" if building else "Publish")
        self.app.dotnet_open_output_btn.setEnabled(bool(self.output_path() and os.path.isdir(self.output_path()) and not building))
        self.app.dotnet_status_label.setStyleSheet(
            status_text_style(Colors.SUCCESS if building or not error else Colors.ERROR)
        )
        if not building:
            self.app.dotnet_status_label.setText("Ready to publish" if not error else error)

    def publish(self):
        if getattr(self.app, "build_process", None):
            self.cancel()
            return
        error = self.validation_error(check_sdk=True)
        if error:
            self.app.dotnet_status_label.setText(error)
            self.refresh_ui()
            return
        values = self.values()
        target = self.output_path()
        try:
            os.makedirs(target, exist_ok=True)
            test_path = os.path.join(target, ".exe_builder_write_test.tmp")
            with open(test_path, "w", encoding="utf-8") as handle:
                handle.write("ok")
            os.remove(test_path)
        except OSError:
            self.app.dotnet_status_label.setText("Cannot write to the selected publish output folder.")
            return

        self.app.building = True
        self._cancelled = False
        self.app.output_path = values["output"]
        self.app.current_build_paths = [target]
        self.app.build_start_time = time.time()
        self.app.build_cancellation = BuildCancellation(self.app, self.app)
        self.app.dotnet_status_label.setText("Publishing .NET project...")
        log_name = f"DOTNET_PUBLISH_DEBUG_{values['name']}.log"
        log_path = os.path.join(values["output"], log_name)
        self.app.debug_log_path = log_path
        command = build_dotnet_publish_command(
            values["project"], values["output"], values["name"], values["runtime"],
            values["self_contained"], values["single_file"], values["trim"], values["icon"],
        )
        self.thread = QThread()
        self.worker = DotnetPublishWorker(self.app, command, log_path)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.publish_finished.emit)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        self.refresh_ui()

    def cancel(self):
        self._cancelled = True
        if hasattr(self.app, "build_cancellation"):
            self.app.build_cancellation.cancel_build()
        self.refresh_ui()
        self.app.dotnet_status_label.setText("Publish cancelled.")

    def _on_publish_finished(self, result, error):
        if getattr(self.app, "_is_closing", False):
            return
        self.app.building = False
        self.app.build_process = None
        self.refresh_ui()
        if self._cancelled:
            self.app.dotnet_status_label.setText("Publish cancelled.")
        elif result == 0:
            self.app.last_build_seconds = int(time.time() - self.app.build_start_time)
            self.app.dotnet_status_label.setStyleSheet(status_text_style(Colors.SUCCESS, border_width=1))
            self.app.dotnet_status_label.setText("Publish complete.")
            self.app.state_ctrl.save_state()
            self.app.build_controller._present_successful_build_outputs()
            self.app.build_controller._run_success_post_build_action()
        else:
            self.app.dotnet_status_label.setStyleSheet(status_text_style(Colors.ERROR, border_width=1))
            self.app.dotnet_status_label.setText(error or "Publish failed. See debug log.")

    def open_output_folder(self):
        target = self.output_path()
        if target and os.path.isdir(target):
            os.startfile(target)
