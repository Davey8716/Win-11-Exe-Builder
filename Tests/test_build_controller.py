import os
import warnings
from datetime import datetime as real_datetime
from pathlib import Path
from types import SimpleNamespace

import build_controller
import build_icon_contract
from build_controller import BuildController, BuildWorker
from datetime_build_options import (
    ISO_MASS_DATETIME_BUILD_SENTINEL,
    MASS_DATETIME_BUILD_SENTINEL,
    NO_DATETIME_LABEL,
    UK_MASS_DATETIME_BUILD_SENTINEL,
    USA_MASS_DATETIME_BUILD_SENTINEL,
)


class DummyInput:
    def __init__(self, value):
        self._value = value

    def text(self):
        return self._value

    def setText(self, value):
        self._value = value


def make_app(**overrides):
    app = SimpleNamespace(
        exe_name_input=DummyInput("Builder"),
        append_py_version=False,
        python_interpreter_path="",
        entry_script="",
        project_root="",
    )

    for name, value in overrides.items():
        setattr(app, name, value)

    return app


def test_initialize_debug_log_uses_selected_output_folder(tmp_path):
    script = tmp_path / "project" / "main.py"
    script.parent.mkdir()
    script.write_text("print('hello')\n", encoding="utf-8")

    app = make_app(
        entry_script=str(script),
        project_root=str(script.parent),
    )
    controller = BuildController(app)

    controller._initialize_debug_log(str(script), str(tmp_path))

    log_path = Path(app.debug_log_path)

    assert log_path.parent == tmp_path
    assert log_path.name.startswith("EXE_BUILDER_DEBUG_Builder_project_")
    assert log_path.suffix == ".log"
    assert log_path.exists()

    contents = log_path.read_text(encoding="utf-8")
    assert "=== BUILD STARTED ===" in contents
    assert "--- Build Inputs ---" in contents
    assert f"  OUTPUT_DIR={repr(str(tmp_path))}" in contents
    assert f"  ENTRY_SCRIPT={repr(str(script))}" in contents


def test_build_debug_log_name_appends_python_version_when_enabled(tmp_path):
    app = make_app(
        append_py_version=True,
        python_interpreter_path=str(tmp_path / "Python314" / "python.exe"),
    )
    controller = BuildController(app)

    log_name = controller._build_debug_log_name(str(tmp_path / "project" / "main.py"))

    assert "py3.14" in log_name


def test_build_debug_log_name_appends_datetime_region_and_timestamp(tmp_path, monkeypatch):
    monkeypatch.setattr(build_controller, "datetime", FixedDateTime)

    app = make_app(
        append_datetime=True,
        datetime_format="%Y-%m-%d",
    )
    controller = BuildController(app)

    log_name = controller._build_debug_log_name(str(tmp_path / "project" / "main.py"))

    assert log_name.startswith("EXE_BUILDER_DEBUG_Builder_project_ISO_2026-05-19_")
    assert log_name.endswith(".log")


def test_mass_datetime_debug_log_reuses_single_txt_file(tmp_path, monkeypatch):
    monkeypatch.setattr(build_controller, "datetime", FixedDateTime)

    script = tmp_path / "project" / "main.py"
    script.parent.mkdir()
    script.write_text("print('hello')\n", encoding="utf-8")

    app = make_app(
        entry_script=str(script),
        project_root=str(script.parent),
        python_interpreter_path=str(tmp_path / "Python314" / "python.exe"),
    )
    controller = BuildController(app)
    controller._mass_datetime_active = True
    controller._mass_datetime_total = 7
    controller._mass_datetime_index = 1
    controller._mass_datetime_current_label = NO_DATETIME_LABEL

    controller._initialize_debug_log(str(script), str(tmp_path))

    first_log_path = Path(app.debug_log_path)
    assert first_log_path.parent == tmp_path
    assert first_log_path.name.startswith("EXE_BUILDER_BUILD_ALL_DEBUG_Builder_project_")
    assert first_log_path.suffix == ".txt"
    assert first_log_path.exists()

    controller._mass_datetime_index = 2
    controller._mass_datetime_current_label = "ISO | YYYY-MM-DD"
    controller._initialize_debug_log(str(script), str(tmp_path))

    assert Path(app.debug_log_path) == first_log_path

    contents = first_log_path.read_text(encoding="utf-8")
    assert contents.count("=== BUILD ALL DATE/TIME OUTPUTS STARTED ===") == 1
    assert f"=== OUTPUT 1/7: {NO_DATETIME_LABEL} ===" in contents
    assert "=== OUTPUT 2/7: ISO | YYYY-MM-DD ===" in contents
    assert contents.count("--- Build Inputs ---") == 2
    assert contents.count(f"  ENTRY_SCRIPT={repr(str(script))}") == 2
    assert f"  OUTPUT_DIR={repr(str(tmp_path))}" in contents


def test_iso_mass_datetime_debug_log_reuses_separate_txt_file(tmp_path, monkeypatch):
    monkeypatch.setattr(build_controller, "datetime", FixedDateTime)

    script = tmp_path / "project" / "main.py"
    script.parent.mkdir()
    script.write_text("print('hello')\n", encoding="utf-8")

    app = make_app(
        entry_script=str(script),
        project_root=str(script.parent),
        python_interpreter_path=str(tmp_path / "Python314" / "python.exe"),
        append_datetime=True,
        datetime_format="%Y-%m-%d",
    )
    controller = BuildController(app)
    controller._start_mass_datetime_build = lambda *_args, **_kwargs: None
    controller._mass_datetime_active = True
    controller._mass_datetime_total = 2
    controller._mass_datetime_index = 1
    controller._mass_datetime_current_label = "ISO | YYYY-MM-DD"
    controller._mass_datetime_debug_log_prefix = "EXE_BUILDER_BUILD_ALL_ISO_DEBUG"
    controller._mass_datetime_log_title = "ISO DATE/TIME"

    controller._initialize_debug_log(str(script), str(tmp_path))

    first_log_path = Path(app.debug_log_path)
    assert first_log_path.parent == tmp_path
    assert first_log_path.name.startswith("EXE_BUILDER_BUILD_ALL_ISO_DEBUG_Builder_project_ISO_2026-05-19_")
    assert first_log_path.suffix == ".txt"
    assert first_log_path.exists()

    controller._mass_datetime_index = 2
    controller._mass_datetime_current_label = "ISO | YYYY-MM-DD_HH-MM"
    controller._initialize_debug_log(str(script), str(tmp_path))

    assert Path(app.debug_log_path) == first_log_path

    contents = first_log_path.read_text(encoding="utf-8")
    assert contents.count("=== BUILD ALL ISO DATE/TIME OUTPUTS STARTED ===") == 1
    assert "=== OUTPUT 1/2: ISO | YYYY-MM-DD ===" in contents
    assert "=== OUTPUT 2/2: ISO | YYYY-MM-DD_HH-MM ===" in contents
    assert contents.count("--- Build Inputs ---") == 2
    assert contents.count(f"  ENTRY_SCRIPT={repr(str(script))}") == 2
    assert f"  OUTPUT_DIR={repr(str(tmp_path))}" in contents


def test_uk_mass_datetime_debug_log_reuses_separate_txt_file(tmp_path, monkeypatch):
    monkeypatch.setattr(build_controller, "datetime", FixedDateTime)

    script = tmp_path / "project" / "main.py"
    script.parent.mkdir()
    script.write_text("print('hello')\n", encoding="utf-8")

    app = make_app(
        entry_script=str(script),
        project_root=str(script.parent),
        python_interpreter_path=str(tmp_path / "Python314" / "python.exe"),
        append_datetime=True,
        datetime_format="%d-%m-%Y",
    )
    controller = BuildController(app)
    controller._mass_datetime_active = True
    controller._mass_datetime_total = 2
    controller._mass_datetime_index = 1
    controller._mass_datetime_current_label = "UK | DD-MM-YYYY"
    controller._mass_datetime_debug_log_prefix = "EXE_BUILDER_BUILD_ALL_UK_DEBUG"
    controller._mass_datetime_log_title = "UK DATE/TIME"

    controller._initialize_debug_log(str(script), str(tmp_path))

    first_log_path = Path(app.debug_log_path)
    assert first_log_path.parent == tmp_path
    assert first_log_path.name.startswith("EXE_BUILDER_BUILD_ALL_UK_DEBUG_Builder_project_UK_19-05-2026_")
    assert first_log_path.suffix == ".txt"
    assert first_log_path.exists()

    controller._mass_datetime_index = 2
    controller._mass_datetime_current_label = "UK | DD-MM-YYYY_HH-MM"
    controller._initialize_debug_log(str(script), str(tmp_path))

    assert Path(app.debug_log_path) == first_log_path

    contents = first_log_path.read_text(encoding="utf-8")
    assert contents.count("=== BUILD ALL UK DATE/TIME OUTPUTS STARTED ===") == 1
    assert "=== OUTPUT 1/2: UK | DD-MM-YYYY ===" in contents
    assert "=== OUTPUT 2/2: UK | DD-MM-YYYY_HH-MM ===" in contents
    assert contents.count("--- Build Inputs ---") == 2
    assert contents.count(f"  ENTRY_SCRIPT={repr(str(script))}") == 2
    assert f"  OUTPUT_DIR={repr(str(tmp_path))}" in contents


def test_usa_mass_datetime_debug_log_reuses_separate_txt_file(tmp_path, monkeypatch):
    monkeypatch.setattr(build_controller, "datetime", FixedDateTime)

    script = tmp_path / "project" / "main.py"
    script.parent.mkdir()
    script.write_text("print('hello')\n", encoding="utf-8")

    app = make_app(
        entry_script=str(script),
        project_root=str(script.parent),
        python_interpreter_path=str(tmp_path / "Python314" / "python.exe"),
        append_datetime=True,
        datetime_format="%m-%d-%Y",
    )
    controller = BuildController(app)
    controller._mass_datetime_active = True
    controller._mass_datetime_total = 2
    controller._mass_datetime_index = 1
    controller._mass_datetime_current_label = "USA | MM-DD-YYYY"
    controller._mass_datetime_debug_log_prefix = "EXE_BUILDER_BUILD_ALL_USA_DEBUG"
    controller._mass_datetime_log_title = "USA DATE/TIME"

    controller._initialize_debug_log(str(script), str(tmp_path))

    first_log_path = Path(app.debug_log_path)
    assert first_log_path.parent == tmp_path
    assert first_log_path.name.startswith("EXE_BUILDER_BUILD_ALL_USA_DEBUG_Builder_project_USA_05-19-2026_")
    assert first_log_path.suffix == ".txt"
    assert first_log_path.exists()

    controller._mass_datetime_index = 2
    controller._mass_datetime_current_label = "USA | MM-DD-YYYY_HH-MM"
    controller._initialize_debug_log(str(script), str(tmp_path))

    assert Path(app.debug_log_path) == first_log_path

    contents = first_log_path.read_text(encoding="utf-8")
    assert contents.count("=== BUILD ALL USA DATE/TIME OUTPUTS STARTED ===") == 1
    assert "=== OUTPUT 1/2: USA | MM-DD-YYYY ===" in contents
    assert "=== OUTPUT 2/2: USA | MM-DD-YYYY_HH-MM ===" in contents
    assert contents.count("--- Build Inputs ---") == 2
    assert contents.count(f"  ENTRY_SCRIPT={repr(str(script))}") == 2
    assert f"  OUTPUT_DIR={repr(str(tmp_path))}" in contents


def test_build_worker_writes_sectioned_command_and_result_log(tmp_path, monkeypatch):
    log_path = tmp_path / "build.log"
    log_path.write_text("=== BUILD STARTED ===\n\n", encoding="utf-8")
    app = make_app(debug_log_path=str(log_path), build_process=None)

    class FakeProcess:
        returncode = 0

        def communicate(self):
            return "stdout text", "warning text"

    monkeypatch.setattr(
        build_controller.subprocess,
        "Popen",
        lambda *_args, **_kwargs: FakeProcess(),
    )

    worker = BuildWorker(app, ["python", "-m", "PyInstaller", "app.py"])
    worker.run()

    contents = log_path.read_text(encoding="utf-8")
    assert "--- PyInstaller Command ---" in contents
    assert "  ENTERED run_build" in contents
    assert "  CMD: python -m PyInstaller app.py" in contents
    assert "--- Build Result ---" in contents
    assert "  RETURN CODE: 0" in contents
    assert "  STDERR:" in contents
    assert "    warning text" in contents


class DummySignal:
    def connect(self, *_args, **_kwargs):
        pass

    def disconnect(self, *_args, **_kwargs):
        pass


class DummyButton:
    def __init__(self):
        self.clicked = DummySignal()
        self.text = ""

    def setText(self, value):
        self.text = value


class WarningSignal(DummySignal):
    def disconnect(self, *_args, **_kwargs):
        warnings.warn(
            'Failed to disconnect (None) from signal "clicked()".',
            RuntimeWarning,
            stacklevel=2,
        )


class WarningButton(DummyButton):
    def __init__(self):
        super().__init__()
        self.clicked = WarningSignal()


class DummyLabel:
    def __init__(self):
        self.text = ""
        self.stylesheet = ""

    def setFixedWidth(self, _value):
        pass

    def setText(self, value):
        self.text = value

    def setStyleSheet(self, value):
        self.stylesheet = value


class DummyToggle:
    def __init__(self):
        self.checked = None

    def setChecked(self, value):
        self.checked = value


class DummyDropdown:
    def __init__(self, options, current_index=0):
        self.options = list(options)
        self.current_index = current_index
        self.signals_blocked = False

    def currentData(self):
        return self.options[self.current_index]["data"]

    def count(self):
        return len(self.options)

    def itemText(self, index):
        return self.options[index]["text"]

    def findData(self, value):
        for index, option in enumerate(self.options):
            if option["data"] == value:
                return index
        return -1

    def setCurrentIndex(self, index):
        self.current_index = index

    def blockSignals(self, value):
        self.signals_blocked = value

    def currentText(self):
        return self.options[self.current_index]["text"]


class DummyValidationController:
    def update_ui_state(self):
        pass

    def set_build_error(self, _message):
        pass

    def update_build_button(self):
        pass


class DummyThread:
    def __init__(self):
        self.started = DummySignal()
        self.finished = DummySignal()

    def start(self):
        pass

    def quit(self):
        pass

    def deleteLater(self):
        pass


class ShutdownThread(DummyThread):
    def __init__(self, running=True):
        super().__init__()
        self.running = running
        self.quit_called = False
        self.wait_timeout = None

    def isRunning(self):
        return self.running

    def quit(self):
        self.quit_called = True

    def wait(self, timeout):
        self.wait_timeout = timeout
        self.running = False
        return True


class FakeWorker:
    def __init__(self, app, cmd):
        app.captured_cmd = cmd
        self.finished = DummySignal()

    def moveToThread(self, _thread):
        pass

    def run(self):
        pass

    def deleteLater(self):
        pass


class CapturingWorker:
    def __init__(self, app, cmd):
        app.captured_cmds.append(cmd)
        self.finished = DummySignal()

    def moveToThread(self, _thread):
        pass

    def run(self):
        pass

    def deleteLater(self):
        pass


class FixedDateTime:
    @classmethod
    def now(cls):
        return real_datetime(2026, 5, 19, 12, 34, 56)


def make_buildable_app(tmp_path, date_time_dropdown=None, **overrides):
    project_root = tmp_path / "project"
    project_root.mkdir()
    script = project_root / "launcher.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    output_dir = tmp_path / "dist"
    output_dir.mkdir()

    python_dir = tmp_path / "Python314"
    python_dir.mkdir()
    python_exe = python_dir / "python.exe"
    python_exe.write_text("", encoding="utf-8")

    app = make_app(
        script_path_input=DummyInput(str(script)),
        output_path_input=DummyInput(str(output_dir)),
        build_process=None,
        icon_path="",
        output_path="",
        build_btn=DummyButton(),
        status_label=DummyLabel(),
        validation_controller=DummyValidationController(),
        last_build_counter=0,
        append_datetime=False,
        datetime_format="",
        append_py_version=False,
        repaint=lambda: None,
        set_status=lambda message: setattr(app, "last_status", message),
        python_interpreter_path=str(python_exe),
        entry_script=str(script),
        project_root=str(project_root),
        captured_cmds=[],
        date_time_dropdown=date_time_dropdown,
        state_ctrl=SimpleNamespace(save_state=lambda: setattr(app, "saved_state", True)),
        open_output_dir_after_build_enabled=False,
        minimize_after_build_enabled=False,
        close_after_build_enabled=False,
        showMinimized=lambda: setattr(app, "minimized", True),
        close_app=lambda: setattr(app, "closed", True),
    )

    for name, value in overrides.items():
        setattr(app, name, value)

    return app


def mass_datetime_dropdown():
    return DummyDropdown(
        [
            {"text": NO_DATETIME_LABEL, "data": None},
            {"text": "Build All Date/Time Outputs", "data": MASS_DATETIME_BUILD_SENTINEL},
            {"text": "ISO | YYYY-MM-DD", "data": "%Y-%m-%d"},
            {"text": "ISO | YYYY-MM-DD_HH-MM", "data": "%Y-%m-%d_%H-%M"},
            {"text": "UK | DD-MM-YYYY", "data": "%d-%m-%Y"},
            {"text": "UK | DD-MM-YYYY_HH-MM", "data": "%d-%m-%Y_%H-%M"},
            {"text": "USA | MM-DD-YYYY", "data": "%m-%d-%Y"},
            {"text": "USA | MM-DD-YYYY_HH-MM", "data": "%m-%d-%Y_%H-%M"},
        ],
        current_index=1,
    )


def iso_mass_datetime_dropdown():
    return DummyDropdown(
        [
            {"text": NO_DATETIME_LABEL, "data": None},
            {
                "text": "Build All ISO Date/Time Outputs",
                "data": ISO_MASS_DATETIME_BUILD_SENTINEL,
            },
            {"text": "ISO | YYYY-MM-DD", "data": "%Y-%m-%d"},
            {"text": "ISO | YYYY-MM-DD_HH-MM", "data": "%Y-%m-%d_%H-%M"},
            {"text": "UK | DD-MM-YYYY", "data": "%d-%m-%Y"},
            {"text": "UK | DD-MM-YYYY_HH-MM", "data": "%d-%m-%Y_%H-%M"},
            {"text": "USA | MM-DD-YYYY", "data": "%m-%d-%Y"},
            {"text": "USA | MM-DD-YYYY_HH-MM", "data": "%m-%d-%Y_%H-%M"},
        ],
        current_index=1,
    )


def uk_mass_datetime_dropdown():
    return DummyDropdown(
        [
            {"text": NO_DATETIME_LABEL, "data": None},
            {
                "text": "Build All UK Date/Time Outputs",
                "data": UK_MASS_DATETIME_BUILD_SENTINEL,
            },
            {"text": "ISO | YYYY-MM-DD", "data": "%Y-%m-%d"},
            {"text": "ISO | YYYY-MM-DD_HH-MM", "data": "%Y-%m-%d_%H-%M"},
            {"text": "UK | DD-MM-YYYY", "data": "%d-%m-%Y"},
            {"text": "UK | DD-MM-YYYY_HH-MM", "data": "%d-%m-%Y_%H-%M"},
            {"text": "USA | MM-DD-YYYY", "data": "%m-%d-%Y"},
            {"text": "USA | MM-DD-YYYY_HH-MM", "data": "%m-%d-%Y_%H-%M"},
        ],
        current_index=1,
    )


def usa_mass_datetime_dropdown():
    return DummyDropdown(
        [
            {"text": NO_DATETIME_LABEL, "data": None},
            {
                "text": "Build All USA Date/Time Outputs",
                "data": USA_MASS_DATETIME_BUILD_SENTINEL,
            },
            {"text": "ISO | YYYY-MM-DD", "data": "%Y-%m-%d"},
            {"text": "ISO | YYYY-MM-DD_HH-MM", "data": "%Y-%m-%d_%H-%M"},
            {"text": "UK | DD-MM-YYYY", "data": "%d-%m-%Y"},
            {"text": "UK | DD-MM-YYYY_HH-MM", "data": "%d-%m-%Y_%H-%M"},
            {"text": "USA | MM-DD-YYYY", "data": "%m-%d-%Y"},
            {"text": "USA | MM-DD-YYYY_HH-MM", "data": "%m-%d-%Y_%H-%M"},
        ],
        current_index=1,
    )


def build_names(app):
    names = []
    for cmd in app.captured_cmds:
        for part in cmd:
            if part.startswith("--name="):
                names.append(part.removeprefix("--name="))
                break
    return names


def build_icon_arg(cmd):
    if "--icon" in cmd:
        return cmd[cmd.index("--icon") + 1]

    for part in cmd:
        if part.startswith("--icon="):
            return part.removeprefix("--icon=")

    return None


def latest_build_target(app):
    return Path(app.output_path_input.text()) / build_names(app)[-1]


def finish_current_build_successfully(controller, app):
    target_dir = latest_build_target(app)
    target_dir.mkdir(parents=True, exist_ok=True)
    controller._on_build_complete_ui(0, "", "")
    return target_dir


def create_legacy_folder_icon_metadata(target_dir, icon_bytes=b"folder-icon"):
    cache_dir = target_dir.parent / build_icon_contract.FOLDER_ICON_CACHE_DIR_NAME
    cache_dir.mkdir(exist_ok=True)
    cache_icon = cache_dir / f"{build_icon_contract.FOLDER_ICON_PREFIX}legacy.ico"
    cache_icon.write_bytes(icon_bytes)
    (target_dir / "desktop.ini").write_text(
        "\n".join(
            [
                "[.ShellClassInfo]",
                f"; {build_icon_contract.DESKTOP_INI_MARKER}",
                f"IconResource=..\\{cache_dir.name}\\{cache_icon.name},0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return cache_icon


def assert_folder_has_no_generated_icon_metadata(target_dir):
    assert not (target_dir / "desktop.ini").exists()
    assert not list(target_dir.glob(".exe_builder_folder_icon_*.ico"))
    assert not (target_dir.parent / ".exe_builder_folder_icons").exists()


def test_build_icon_contract_emits_explicit_none_without_tray_args():
    contract = build_icon_contract.resolve_build_icon_contract("")

    assert contract.icon_path == ""
    assert contract.pyinstaller_args == ["--icon=NONE"]


def test_build_icon_contract_reuses_same_icon_for_exe_and_tray(tmp_path):
    icon = tmp_path / "app.ico"
    icon.write_bytes(b"icon")

    contract = build_icon_contract.resolve_build_icon_contract(str(icon))
    normalized_icon = os.path.normpath(str(icon))

    assert contract.icon_path == normalized_icon
    assert build_icon_arg(contract.pyinstaller_args) == normalized_icon
    assert f"{normalized_icon}{os.pathsep}_exe_builder_tray_icon.ico" in contract.pyinstaller_args


def test_clear_legacy_folder_icon_metadata_removes_generated_files(tmp_path):
    output_folder = tmp_path / "Builder"
    output_folder.mkdir()
    create_legacy_folder_icon_metadata(output_folder)

    assert build_icon_contract.clear_output_folder_icon_metadata(output_folder) is True
    assert_folder_has_no_generated_icon_metadata(output_folder)


def test_shutdown_stops_running_build_thread_and_clears_state():
    app = make_app(
        _eta_running=True,
        building=True,
        build_process=None,
    )
    controller = BuildController(app)
    thread = ShutdownThread()
    controller.build_thread = thread
    controller.worker = object()

    controller.shutdown(timeout_ms=1234)

    assert app._eta_running is False
    assert app.building is False
    assert app.build_process is None
    assert thread.quit_called is True
    assert thread.wait_timeout == 1234
    assert controller.build_thread is None
    assert controller.worker is None


def test_shutdown_cancels_active_build_process(monkeypatch):
    import build_cancellation

    cancelled = []
    app = make_app(
        _eta_running=True,
        building=True,
        build_process=object(),
        _is_closing=True,
    )
    controller = BuildController(app)

    def fake_cancel(self):
        cancelled.append(self.app.build_process)
        self.app.build_process = None
        self.app.building = False

    monkeypatch.setattr(build_cancellation.BuildCancellation, "cancel_build", fake_cancel)

    controller.shutdown()

    assert cancelled
    assert app._eta_running is False
    assert app.building is False
    assert app.build_process is None


def patch_build_runtime(monkeypatch):
    monkeypatch.setattr(build_controller, "validate_bundle_inputs", lambda app: (True, ""))
    monkeypatch.setattr(build_controller, "QThread", DummyThread)
    monkeypatch.setattr(build_controller, "BuildWorker", CapturingWorker)
    monkeypatch.setattr(BuildController, "start_eta", lambda self: None)
    monkeypatch.setattr(BuildController, "stop_eta", lambda self: None)
    monkeypatch.setattr(build_controller, "datetime", FixedDateTime)
    monkeypatch.setattr(
        build_controller.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    monkeypatch.setattr(build_controller.QTimer, "singleShot", lambda _ms, callback: callback())


def test_mass_datetime_build_runs_all_outputs_in_sequence(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(tmp_path, date_time_dropdown=mass_datetime_dropdown())
    controller = BuildController(app)

    controller.build_exe(None)
    for _ in range(6):
        controller._on_build_complete_ui(0, "", "")

    assert build_names(app) == [
        "Builder",
        "Builder_ISO_2026-05-19",
        "Builder_ISO_2026-05-19_12-34",
        "Builder_UK_19-05-2026",
        "Builder_UK_19-05-2026_12-34",
        "Builder_USA_05-19-2026",
        "Builder_USA_05-19-2026_12-34",
    ]
    assert controller._mass_datetime_active is True

    controller._on_build_complete_ui(0, "", "")

    assert controller._mass_datetime_active is False
    assert app.append_datetime is False
    assert app.datetime_format == MASS_DATETIME_BUILD_SENTINEL
    assert app.date_time_dropdown.currentText() == "Build All Date/Time Outputs"
    assert app.saved_state is True


def test_rebuilding_same_output_uses_new_icon_and_clears_exact_artifacts(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)

    icon_a = tmp_path / "a.ico"
    icon_b = tmp_path / "b.ico"
    icon_a.write_bytes(b"icon-a")
    icon_b.write_bytes(b"icon-b")

    app = make_buildable_app(tmp_path, icon_path=str(icon_a))
    controller = BuildController(app)

    controller.build_exe(None)

    output_dir = Path(app.output_path_input.text())
    stale_paths = [
        output_dir / "Builder",
        output_dir / "build" / "Builder",
        output_dir / "spec" / "Builder",
    ]
    for stale_path in stale_paths:
        stale_path.mkdir(parents=True, exist_ok=True)
        (stale_path / "stale.txt").write_text("old", encoding="utf-8")

    app.icon_path = str(icon_b)
    controller.build_exe(None)

    first_cmd, second_cmd = app.captured_cmds
    icon_a_path = os.path.normpath(str(icon_a))
    icon_b_path = os.path.normpath(str(icon_b))

    assert build_icon_arg(first_cmd) == icon_a_path
    assert build_icon_arg(second_cmd) == icon_b_path
    assert icon_a_path not in second_cmd
    assert f"{icon_a_path}{os.pathsep}_exe_builder_tray_icon.ico" not in " ".join(second_cmd)
    assert f"{icon_b_path}{os.pathsep}_exe_builder_tray_icon.ico" in second_cmd
    assert all(not (stale_path / "stale.txt").exists() for stale_path in stale_paths)

    target_dir = output_dir / "Builder"
    target_dir.mkdir()
    controller._on_build_complete_ui(0, "", "")

    assert_folder_has_no_generated_icon_metadata(target_dir)


def test_rebuilding_same_output_with_no_icon_passes_explicit_none(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)

    icon = tmp_path / "app.ico"
    icon.write_bytes(b"icon")

    app = make_buildable_app(tmp_path, icon_path=str(icon))
    controller = BuildController(app)

    controller.build_exe(None)
    target_dir = Path(app.output_path_input.text()) / "Builder"
    target_dir.mkdir()
    controller._on_build_complete_ui(0, "", "")
    assert_folder_has_no_generated_icon_metadata(target_dir)

    app.icon_path = ""
    create_legacy_folder_icon_metadata(target_dir)
    controller.build_exe(None)
    target_dir.mkdir()
    controller._on_build_complete_ui(0, "", "")

    first_cmd, second_cmd = app.captured_cmds

    assert build_icon_arg(first_cmd) == os.path.normpath(str(icon))
    assert build_icon_arg(second_cmd) == "NONE"
    assert "--icon" not in second_cmd
    assert "_exe_builder_tray_icon.ico" not in " ".join(second_cmd)
    assert_folder_has_no_generated_icon_metadata(target_dir)


def test_mass_datetime_build_uses_explicit_no_icon_for_every_output(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)

    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=mass_datetime_dropdown(),
        icon_path="",
    )
    controller = BuildController(app)

    controller.build_exe(None)
    for _ in range(6):
        controller._on_build_complete_ui(0, "", "")

    assert len(app.captured_cmds) == 7
    assert all(build_icon_arg(cmd) == "NONE" for cmd in app.captured_cmds)
    assert all("--icon" not in cmd for cmd in app.captured_cmds)
    assert all("_exe_builder_tray_icon.ico" not in " ".join(cmd) for cmd in app.captured_cmds)


def test_mass_datetime_build_applies_selected_icon_to_every_output(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    icon = tmp_path / "app.ico"
    icon.write_bytes(b"batch-icon")
    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=mass_datetime_dropdown(),
        icon_path=str(icon),
    )
    controller = BuildController(app)

    controller.build_exe(None)
    built_dirs = []
    for _ in range(7):
        built_dirs.append(finish_current_build_successfully(controller, app))

    normalized_icon = os.path.normpath(str(icon))
    assert len(app.captured_cmds) == 7
    assert all(build_icon_arg(cmd) == normalized_icon for cmd in app.captured_cmds)
    assert all(f"{normalized_icon}{os.pathsep}_exe_builder_tray_icon.ico" in cmd for cmd in app.captured_cmds)
    for target_dir in built_dirs:
        assert_folder_has_no_generated_icon_metadata(target_dir)


def test_regional_mass_datetime_builds_apply_selected_icon_to_every_output(tmp_path, monkeypatch):
    for dropdown_factory in (
        iso_mass_datetime_dropdown,
        uk_mass_datetime_dropdown,
        usa_mass_datetime_dropdown,
    ):
        patch_build_runtime(monkeypatch)
        icon = tmp_path / f"{dropdown_factory.__name__}.ico"
        icon.write_bytes(dropdown_factory.__name__.encode("utf-8"))
        case_dir = tmp_path / dropdown_factory.__name__
        case_dir.mkdir()
        app = make_buildable_app(
            case_dir,
            date_time_dropdown=dropdown_factory(),
            icon_path=str(icon),
        )
        controller = BuildController(app)

        controller.build_exe(None)
        built_dirs = []
        for _ in range(2):
            built_dirs.append(finish_current_build_successfully(controller, app))

        normalized_icon = os.path.normpath(str(icon))
        assert len(app.captured_cmds) == 2
        assert all(build_icon_arg(cmd) == normalized_icon for cmd in app.captured_cmds)
        assert all(f"{normalized_icon}{os.pathsep}_exe_builder_tray_icon.ico" in cmd for cmd in app.captured_cmds)
        for target_dir in built_dirs:
            assert_folder_has_no_generated_icon_metadata(target_dir)


def test_mass_datetime_build_waits_for_success_before_next_output(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(tmp_path, date_time_dropdown=mass_datetime_dropdown())
    controller = BuildController(app)

    controller.build_exe(None)

    assert build_names(app) == ["Builder"]

    controller._on_build_complete_ui(0, "", "")

    assert build_names(app) == ["Builder", "Builder_ISO_2026-05-19"]


def test_mass_datetime_desktop_build_centers_all_outputs_after_final_success(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    centered = []

    def record_single_shot(ms, callback):
        if ms == 0:
            callback()

    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=mass_datetime_dropdown(),
        open_output_dir_after_build_enabled=True,
    )
    desktop_path = os.path.normpath(app.output_path_input.text())
    controller = BuildController(app)
    monkeypatch.setattr(controller, "_get_desktop_path", lambda: desktop_path)
    monkeypatch.setattr(controller, "_center_desktop_build_outputs", lambda: centered.append(list(app.current_build_paths)))
    monkeypatch.setattr(build_controller.QTimer, "singleShot", record_single_shot)

    controller.build_exe(None)
    built_dirs = []
    for _ in range(7):
        built_dirs.append(finish_current_build_successfully(controller, app))

    assert centered == [app.current_build_paths]
    assert all(str(path) in app.current_build_paths for path in built_dirs)
    for target_dir in built_dirs:
        name = Path(target_dir).name
        assert os.path.join(desktop_path, "build", name) in app.current_build_paths
        assert os.path.join(desktop_path, "spec", name) in app.current_build_paths
    assert app.debug_log_path in app.current_build_paths


def test_regional_mass_datetime_desktop_builds_center_all_outputs_after_final_success(tmp_path, monkeypatch):
    for dropdown_factory in (
        iso_mass_datetime_dropdown,
        uk_mass_datetime_dropdown,
        usa_mass_datetime_dropdown,
    ):
        patch_build_runtime(monkeypatch)
        centered = []

        def record_single_shot(ms, callback):
            if ms == 0:
                callback()

        case_dir = tmp_path / f"{dropdown_factory.__name__}_desktop"
        case_dir.mkdir()
        app = make_buildable_app(case_dir, date_time_dropdown=dropdown_factory())
        desktop_path = os.path.normpath(app.output_path_input.text())
        controller = BuildController(app)
        monkeypatch.setattr(controller, "_get_desktop_path", lambda: desktop_path)
        monkeypatch.setattr(controller, "_center_desktop_build_outputs", lambda: centered.append(list(app.current_build_paths)))
        monkeypatch.setattr(build_controller.QTimer, "singleShot", record_single_shot)

        controller.build_exe(None)
        built_dirs = []
        for _ in range(2):
            built_dirs.append(finish_current_build_successfully(controller, app))

        assert centered == [app.current_build_paths]
        assert all(str(path) in app.current_build_paths for path in built_dirs)


def test_mass_datetime_non_desktop_build_opens_output_after_final_success(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    opened_paths = []

    monkeypatch.setattr(build_controller.os, "startfile", lambda path: opened_paths.append(path), raising=False)
    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=iso_mass_datetime_dropdown(),
        open_output_dir_after_build_enabled=True,
    )
    controller = BuildController(app)
    monkeypatch.setattr(controller, "_focus_existing_output_explorer_window", lambda _path: False)

    controller.build_exe(None)
    for _ in range(2):
        finish_current_build_successfully(controller, app)

    assert opened_paths == [os.path.normpath(app.output_path_input.text())]


def test_failed_mass_datetime_build_does_not_present_partial_outputs(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    centered = []
    delayed_callbacks = []

    def record_single_shot(ms, callback):
        if ms == 0:
            callback()
        elif ms == 1000:
            delayed_callbacks.append(callback)

    app = make_buildable_app(tmp_path, date_time_dropdown=mass_datetime_dropdown())
    desktop_path = os.path.normpath(app.output_path_input.text())
    controller = BuildController(app)
    monkeypatch.setattr(controller, "_get_desktop_path", lambda: desktop_path)
    monkeypatch.setattr(controller, "_center_desktop_build_outputs", lambda: centered.append(True))
    monkeypatch.setattr(build_controller.QTimer, "singleShot", record_single_shot)

    controller.build_exe(None)
    latest_build_target(app).mkdir(parents=True, exist_ok=True)
    controller._on_build_complete_ui(1, "", "failed")

    assert delayed_callbacks == []
    assert centered == []
    assert controller._mass_datetime_output_group == []


def test_mass_datetime_desktop_centering_happens_before_close_after_build(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    events = []

    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=mass_datetime_dropdown(),
        close_after_build_enabled=True,
        close_app=lambda: events.append("close"),
        state_ctrl=SimpleNamespace(save_state=lambda: events.append("save")),
    )
    desktop_path = os.path.normpath(app.output_path_input.text())
    controller = BuildController(app)
    monkeypatch.setattr(controller, "_get_desktop_path", lambda: desktop_path)
    monkeypatch.setattr(controller, "_center_desktop_build_outputs", lambda: events.append("center"))

    controller.build_exe(None)
    for _ in range(7):
        finish_current_build_successfully(controller, app)

    assert events[-3:] == ["center", "save", "close"]


def test_regional_mass_datetime_desktop_centering_happens_before_minimize_after_build(tmp_path, monkeypatch):
    for dropdown_factory in (
        iso_mass_datetime_dropdown,
        uk_mass_datetime_dropdown,
        usa_mass_datetime_dropdown,
    ):
        patch_build_runtime(monkeypatch)
        events = []

        case_dir = tmp_path / f"{dropdown_factory.__name__}_minimize"
        case_dir.mkdir()
        app = make_buildable_app(
            case_dir,
            date_time_dropdown=dropdown_factory(),
            minimize_after_build_enabled=True,
            showMinimized=lambda: events.append("minimize"),
            state_ctrl=SimpleNamespace(save_state=lambda: events.append("save")),
        )
        desktop_path = os.path.normpath(app.output_path_input.text())
        controller = BuildController(app)
        monkeypatch.setattr(controller, "_get_desktop_path", lambda: desktop_path)
        monkeypatch.setattr(controller, "_center_desktop_build_outputs", lambda: events.append("center"))

        controller.build_exe(None)
        for _ in range(2):
            finish_current_build_successfully(controller, app)

        assert events[-3:] == ["center", "save", "minimize"]


def test_saved_mass_datetime_sentinel_restores_to_build_all_after_build(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=mass_datetime_dropdown(),
        append_datetime=False,
        datetime_format=MASS_DATETIME_BUILD_SENTINEL,
    )
    controller = BuildController(app)

    controller.build_exe(None)
    for _ in range(7):
        controller._on_build_complete_ui(0, "", "")

    assert controller._mass_datetime_active is False
    assert app.append_datetime is False
    assert app.datetime_format == MASS_DATETIME_BUILD_SENTINEL
    assert app.date_time_dropdown.currentText() == "Build All Date/Time Outputs"
    assert app.saved_state is True


def test_iso_mass_datetime_build_runs_iso_outputs_only(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(tmp_path, date_time_dropdown=iso_mass_datetime_dropdown())
    controller = BuildController(app)

    controller.build_exe(None)

    assert build_names(app) == ["Builder_ISO_2026-05-19"]
    assert controller._mass_datetime_active is True

    controller._on_build_complete_ui(0, "", "")

    assert build_names(app) == [
        "Builder_ISO_2026-05-19",
        "Builder_ISO_2026-05-19_12-34",
    ]
    assert controller._mass_datetime_active is True

    controller._on_build_complete_ui(0, "", "")

    assert controller._mass_datetime_active is False
    assert app.append_datetime is False
    assert app.datetime_format == ISO_MASS_DATETIME_BUILD_SENTINEL
    assert app.date_time_dropdown.currentText() == "Build All ISO Date/Time Outputs"
    assert app.saved_state is True


def test_iso_mass_datetime_build_waits_for_success_before_next_output(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(tmp_path, date_time_dropdown=iso_mass_datetime_dropdown())
    controller = BuildController(app)

    controller.build_exe(None)

    assert build_names(app) == ["Builder_ISO_2026-05-19"]

    controller._on_build_complete_ui(0, "", "")

    assert build_names(app) == ["Builder_ISO_2026-05-19", "Builder_ISO_2026-05-19_12-34"]


def test_uk_mass_datetime_build_runs_uk_outputs_only(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(tmp_path, date_time_dropdown=uk_mass_datetime_dropdown())
    controller = BuildController(app)

    controller.build_exe(None)

    assert build_names(app) == ["Builder_UK_19-05-2026"]
    assert controller._mass_datetime_active is True

    controller._on_build_complete_ui(0, "", "")

    assert build_names(app) == [
        "Builder_UK_19-05-2026",
        "Builder_UK_19-05-2026_12-34",
    ]
    assert controller._mass_datetime_active is True

    controller._on_build_complete_ui(0, "", "")

    assert controller._mass_datetime_active is False
    assert app.append_datetime is False
    assert app.datetime_format == UK_MASS_DATETIME_BUILD_SENTINEL
    assert app.date_time_dropdown.currentText() == "Build All UK Date/Time Outputs"


def test_uk_mass_datetime_build_waits_for_success_before_next_output(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(tmp_path, date_time_dropdown=uk_mass_datetime_dropdown())
    controller = BuildController(app)

    controller.build_exe(None)

    assert build_names(app) == ["Builder_UK_19-05-2026"]

    controller._on_build_complete_ui(0, "", "")

    assert build_names(app) == ["Builder_UK_19-05-2026", "Builder_UK_19-05-2026_12-34"]


def test_usa_mass_datetime_build_runs_usa_outputs_only(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(tmp_path, date_time_dropdown=usa_mass_datetime_dropdown())
    controller = BuildController(app)

    controller.build_exe(None)

    assert build_names(app) == ["Builder_USA_05-19-2026"]
    assert controller._mass_datetime_active is True

    controller._on_build_complete_ui(0, "", "")

    assert build_names(app) == [
        "Builder_USA_05-19-2026",
        "Builder_USA_05-19-2026_12-34",
    ]
    assert controller._mass_datetime_active is True

    controller._on_build_complete_ui(0, "", "")

    assert controller._mass_datetime_active is False
    assert app.append_datetime is False
    assert app.datetime_format == USA_MASS_DATETIME_BUILD_SENTINEL
    assert app.date_time_dropdown.currentText() == "Build All USA Date/Time Outputs"


def test_usa_mass_datetime_build_waits_for_success_before_next_output(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(tmp_path, date_time_dropdown=usa_mass_datetime_dropdown())
    controller = BuildController(app)

    controller.build_exe(None)

    assert build_names(app) == ["Builder_USA_05-19-2026"]

    controller._on_build_complete_ui(0, "", "")

    assert build_names(app) == ["Builder_USA_05-19-2026", "Builder_USA_05-19-2026_12-34"]


def test_mass_datetime_build_stops_on_failure_and_restores_state(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    dropdown = mass_datetime_dropdown()
    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=dropdown,
        append_datetime=True,
        datetime_format="%Y-%m-%d",
        _mass_datetime_restore_state={
            "append_datetime": True,
            "datetime_format": "%Y-%m-%d",
        },
    )
    controller = BuildController(app)

    controller.build_exe(None)
    controller._on_build_complete_ui(1, "", "failed")

    assert build_names(app) == ["Builder"]
    assert controller._mass_datetime_active is False
    assert app.append_datetime is False
    assert app.datetime_format == MASS_DATETIME_BUILD_SENTINEL
    assert app.date_time_dropdown.currentText() == "Build All Date/Time Outputs"
    assert app.saved_state is True
    assert app.status_label.stylesheet == build_controller.status_text_style(
        build_controller.Colors.ERROR,
        border_width=1,
    )


def test_iso_mass_datetime_build_stops_on_failure_and_restores_state(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    dropdown = iso_mass_datetime_dropdown()
    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=dropdown,
        append_datetime=True,
        datetime_format="%Y-%m-%d",
        _mass_datetime_restore_state={
            "append_datetime": True,
            "datetime_format": "%Y-%m-%d",
        },
    )
    controller = BuildController(app)

    controller.build_exe(None)
    controller._on_build_complete_ui(1, "", "failed")

    assert build_names(app) == ["Builder_ISO_2026-05-19"]
    assert controller._mass_datetime_active is False
    assert app.append_datetime is False
    assert app.datetime_format == ISO_MASS_DATETIME_BUILD_SENTINEL
    assert app.date_time_dropdown.currentText() == "Build All ISO Date/Time Outputs"
    assert app.saved_state is True
    assert app.status_label.stylesheet == build_controller.status_text_style(
        build_controller.Colors.ERROR,
        border_width=1,
    )


def test_uk_mass_datetime_build_stops_on_failure_and_restores_state(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    dropdown = uk_mass_datetime_dropdown()
    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=dropdown,
        append_datetime=True,
        datetime_format="%d-%m-%Y",
        _mass_datetime_restore_state={
            "append_datetime": True,
            "datetime_format": "%d-%m-%Y",
        },
    )
    controller = BuildController(app)

    controller.build_exe(None)
    controller._on_build_complete_ui(1, "", "failed")

    assert build_names(app) == ["Builder_UK_19-05-2026"]
    assert controller._mass_datetime_active is False
    assert app.append_datetime is False
    assert app.datetime_format == UK_MASS_DATETIME_BUILD_SENTINEL
    assert app.date_time_dropdown.currentText() == "Build All UK Date/Time Outputs"
    assert app.saved_state is True
    assert app.status_label.stylesheet == build_controller.status_text_style(
        build_controller.Colors.ERROR,
        border_width=1,
    )


def test_usa_mass_datetime_build_stops_on_failure_and_restores_state(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    dropdown = usa_mass_datetime_dropdown()
    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=dropdown,
        append_datetime=True,
        datetime_format="%m-%d-%Y",
        _mass_datetime_restore_state={
            "append_datetime": True,
            "datetime_format": "%m-%d-%Y",
        },
    )
    controller = BuildController(app)

    controller.build_exe(None)
    controller._on_build_complete_ui(1, "", "failed")

    assert build_names(app) == ["Builder_USA_05-19-2026"]
    assert controller._mass_datetime_active is False
    assert app.append_datetime is False
    assert app.datetime_format == USA_MASS_DATETIME_BUILD_SENTINEL
    assert app.date_time_dropdown.currentText() == "Build All USA Date/Time Outputs"
    assert app.saved_state is True
    assert app.status_label.stylesheet == build_controller.status_text_style(
        build_controller.Colors.ERROR,
        border_width=1,
    )


def test_mass_datetime_build_cancel_restores_state(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    import build_cancellation

    dropdown = mass_datetime_dropdown()
    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=dropdown,
        append_datetime=True,
        datetime_format="%d-%m-%Y",
        _mass_datetime_restore_state={
            "append_datetime": True,
            "datetime_format": "%d-%m-%Y",
        },
    )
    controller = BuildController(app)

    controller.build_exe(None)
    app.build_process = object()

    def fake_cancel(self):
        self.app.build_process = None
        self.app.building = False
        self.app.cancelled = True

    monkeypatch.setattr(build_cancellation.BuildCancellation, "cancel_build", fake_cancel)

    controller.build_exe(None)

    assert app.cancelled is True
    assert controller._mass_datetime_active is False
    assert app.append_datetime is False
    assert app.datetime_format == MASS_DATETIME_BUILD_SENTINEL
    assert app.date_time_dropdown.currentText() == "Build All Date/Time Outputs"
    assert app.saved_state is True


def test_iso_mass_datetime_build_cancel_restores_state(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    import build_cancellation

    dropdown = iso_mass_datetime_dropdown()
    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=dropdown,
        append_datetime=True,
        datetime_format="%Y-%m-%d_%H-%M",
        _mass_datetime_restore_state={
            "append_datetime": True,
            "datetime_format": "%Y-%m-%d_%H-%M",
        },
    )
    controller = BuildController(app)

    controller.build_exe(None)
    app.build_process = object()

    def fake_cancel(self):
        self.app.build_process = None
        self.app.building = False
        self.app.cancelled = True

    monkeypatch.setattr(build_cancellation.BuildCancellation, "cancel_build", fake_cancel)

    controller.build_exe(None)

    assert app.cancelled is True
    assert controller._mass_datetime_active is False
    assert app.append_datetime is False
    assert app.datetime_format == ISO_MASS_DATETIME_BUILD_SENTINEL
    assert app.date_time_dropdown.currentText() == "Build All ISO Date/Time Outputs"
    assert app.saved_state is True


def test_uk_mass_datetime_build_cancel_restores_state(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    import build_cancellation

    dropdown = uk_mass_datetime_dropdown()
    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=dropdown,
        append_datetime=True,
        datetime_format="%d-%m-%Y_%H-%M",
        _mass_datetime_restore_state={
            "append_datetime": True,
            "datetime_format": "%d-%m-%Y_%H-%M",
        },
    )
    controller = BuildController(app)

    controller.build_exe(None)
    app.build_process = object()

    def fake_cancel(self):
        self.app.build_process = None
        self.app.building = False
        self.app.cancelled = True

    monkeypatch.setattr(build_cancellation.BuildCancellation, "cancel_build", fake_cancel)

    controller.build_exe(None)

    assert app.cancelled is True
    assert controller._mass_datetime_active is False
    assert app.append_datetime is False
    assert app.datetime_format == UK_MASS_DATETIME_BUILD_SENTINEL
    assert app.date_time_dropdown.currentText() == "Build All UK Date/Time Outputs"
    assert app.saved_state is True


def test_usa_mass_datetime_build_cancel_restores_state(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    import build_cancellation

    dropdown = usa_mass_datetime_dropdown()
    app = make_buildable_app(
        tmp_path,
        date_time_dropdown=dropdown,
        append_datetime=True,
        datetime_format="%m-%d-%Y_%H-%M",
        _mass_datetime_restore_state={
            "append_datetime": True,
            "datetime_format": "%m-%d-%Y_%H-%M",
        },
    )
    controller = BuildController(app)

    controller.build_exe(None)
    app.build_process = object()

    def fake_cancel(self):
        self.app.build_process = None
        self.app.building = False
        self.app.cancelled = True

    monkeypatch.setattr(build_cancellation.BuildCancellation, "cancel_build", fake_cancel)

    controller.build_exe(None)

    assert app.cancelled is True
    assert controller._mass_datetime_active is False
    assert app.append_datetime is False
    assert app.datetime_format == USA_MASS_DATETIME_BUILD_SENTINEL
    assert app.date_time_dropdown.currentText() == "Build All USA Date/Time Outputs"
    assert app.saved_state is True


def test_build_exe_suppresses_empty_clicked_disconnect_warning(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(tmp_path, build_btn=WarningButton())
    controller = BuildController(app)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        controller.build_exe(None)

    assert not [
        warning
        for warning in caught
        if issubclass(warning.category, RuntimeWarning)
        and "Failed to disconnect" in str(warning.message)
    ]


def test_project_exclusions_are_added_without_forcing_tk_collection(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(tmp_path)
    manifest = Path(app.project_root) / ".python-exe-builder.json"
    manifest.write_text(
        '{"schema_version": 1, "pyinstaller": '
        '{"exclude_modules": ["tkinter", "_tkinter", "tk"]}}',
        encoding="utf-8",
    )

    BuildController(app).build_exe(None)

    command = app.captured_cmds[0]
    assert "--collect-all=tkinter" not in command
    assert "--collect-all=tk" not in command
    assert "--collect-all=qt_material" in command
    assert "--exclude-module=tkinter" in command
    assert "--exclude-module=_tkinter" in command
    assert "--exclude-module=tk" in command


def test_default_build_does_not_force_tk_into_non_tk_projects(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(tmp_path)

    BuildController(app).build_exe(None)

    command = app.captured_cmds[0]
    assert "--collect-all=tkinter" not in command
    assert "--collect-all=tk" not in command
    assert "--collect-all=qt_material" in command
    assert not [arg for arg in command if arg.startswith("--exclude-module=")]


def test_workpath_layout_keeps_repeated_youtube_name_below_resource_limit():
    output_dir = (
        r"C:\Users\davey\Desktop\Local EXES\Youtube Endless Scroll Blocker"
    )
    name = "Youtube Endless Scroll Blocker_Youtube Endless Scroll Blocker"

    expected_exe = build_controller._expected_pyinstaller_exe_path(
        os.path.join(output_dir, "build"),
        name,
    )

    assert expected_exe == os.path.join(
        output_dir,
        "build",
        name,
        f"{name}.exe",
    )
    assert len(expected_exe) == 198
    assert len(expected_exe) < build_controller.WINDOWS_RESOURCE_PATH_LIMIT


def test_build_exe_rejects_path_too_long_for_windows_resources(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(
        tmp_path,
        exe_name_input=DummyInput("x" * 200),
    )

    BuildController(app).build_exe(None)

    assert app.captured_cmds == []
    assert "Generated build path is too long" in app.last_status
    assert "Choose a shorter EXE name or output folder" in app.last_status


def test_build_exe_cleans_only_project_specific_stale_workpath(tmp_path, monkeypatch):
    patch_build_runtime(monkeypatch)
    app = make_buildable_app(tmp_path)
    build_root = Path(app.output_path_input.text()) / "build"
    stale_project = build_root / "Builder"
    sibling_project = build_root / "keep-existing-build"
    stale_project.mkdir(parents=True)
    sibling_project.mkdir()

    BuildController(app).build_exe(None)

    assert not stale_project.exists()
    assert sibling_project.is_dir()


def test_get_project_asset_data_args_preserves_relative_destinations(tmp_path):
    project_root = tmp_path / "project with spaces"
    nested_dir = project_root / "Icons" / "Screen Mover"
    nested_dir.mkdir(parents=True)

    root_png = project_root / "root icon.PNG"
    nested_png = nested_dir / "move left.png"
    root_ahk = project_root / "launcher.AHK"
    nested_ahk = nested_dir / "window helper.ahk"
    ignored_svg = nested_dir / "move left.svg"

    root_png.write_text("root", encoding="utf-8")
    nested_png.write_text("nested", encoding="utf-8")
    root_ahk.write_text("#Requires AutoHotkey v2.0", encoding="utf-8")
    nested_ahk.write_text("ExitApp", encoding="utf-8")
    ignored_svg.write_text("ignored", encoding="utf-8")

    controller = BuildController(make_app())

    args = controller._get_project_asset_data_args(str(project_root))

    assert args == [
        f"--add-data={os.path.normpath(str(root_ahk))}{os.pathsep}.",
        f"--add-data={os.path.normpath(str(root_png))}{os.pathsep}.",
        (
            f"--add-data={os.path.normpath(str(nested_png))}{os.pathsep}"
            f"{os.path.normpath(os.path.join('Icons', 'Screen Mover'))}"
        ),
        (
            f"--add-data={os.path.normpath(str(nested_ahk))}{os.pathsep}"
            f"{os.path.normpath(os.path.join('Icons', 'Screen Mover'))}"
        ),
    ]
    assert str(ignored_svg) not in " ".join(args)


def test_get_project_asset_data_args_includes_parent_project_sibling_assets(tmp_path):
    repo_root = tmp_path / "Browser-App-Mover"
    package_root = repo_root / "browser_app_mover"
    dock_icon_dir = repo_root / "Icon Pngs" / "Green"
    app_icon_dir = repo_root / "Icons"
    package_root.mkdir(parents=True)
    dock_icon_dir.mkdir(parents=True)
    app_icon_dir.mkdir()
    (repo_root / "pyproject.toml").write_text("[project]\nname='browser-app-mover'\n", encoding="utf-8")

    dock_icon = dock_icon_dir / "Left.png"
    app_icon = app_icon_dir / "Browser App Mover Icon.png"
    dock_icon.write_text("dock", encoding="utf-8")
    app_icon.write_text("app", encoding="utf-8")

    controller = BuildController(make_app())

    args = controller._get_project_asset_data_args(str(package_root))

    assert (
        f"--add-data={os.path.normpath(str(dock_icon))}{os.pathsep}"
        f"{os.path.normpath(os.path.join('Icon Pngs', 'Green'))}"
    ) in args
    assert f"--add-data={os.path.normpath(str(app_icon))}{os.pathsep}Icons" in args


def test_get_project_asset_data_args_bundles_hover_controls_ahk_resource(tmp_path):
    repo_root = tmp_path / "Hover Window Controls"
    package_root = repo_root / "hover_window_controls"
    resources_dir = repo_root / "resources"
    package_root.mkdir(parents=True)
    resources_dir.mkdir()
    (repo_root / "requirements.txt").write_text("pyinstaller\n", encoding="utf-8")

    ahk_script = resources_dir / "taskbar_restore.ahk"
    ahk_script.write_text("#Requires AutoHotkey v2.0\nExitApp\n", encoding="utf-8")

    controller = BuildController(make_app())

    args = controller._get_project_asset_data_args(str(package_root))

    assert (
        f"--add-data={os.path.normpath(str(ahk_script))}{os.pathsep}resources"
    ) in args


def test_get_project_asset_data_args_skips_generated_and_environment_directories(tmp_path):
    project_root = tmp_path / "project"
    included_dir = project_root / "resources"
    included_dir.mkdir(parents=True)
    included = included_dir / "included.ahk"
    included.write_text("ExitApp\n", encoding="utf-8")

    excluded_files = []
    excluded_dirnames = (
        ".git",
        "__pycache__",
        "build",
        "dist",
        "env",
        "spec",
        "venv",
        ".venv",
    )
    for dirname in excluded_dirnames:
        excluded_dir = project_root / dirname
        excluded_dir.mkdir()
        excluded = excluded_dir / "excluded.ahk"
        excluded.write_text("ExitApp\n", encoding="utf-8")
        excluded_files.append(excluded)

    controller = BuildController(make_app())

    args = controller._get_project_asset_data_args(str(project_root))
    command_text = " ".join(args)

    assert f"--add-data={included}{os.pathsep}resources" in args
    for excluded in excluded_files:
        assert str(excluded) not in command_text


def test_build_exe_adds_project_root_to_paths_and_data(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    script = project_root / "main.py"
    script.write_text("print('hello')\n", encoding="utf-8")
    png_dir = project_root / "Icons"
    png_dir.mkdir()
    png_file = png_dir / "move.png"
    png_file.write_text("png", encoding="utf-8")
    resources_dir = project_root / "resources"
    resources_dir.mkdir()
    ahk_file = resources_dir / "taskbar_restore.ahk"
    ahk_file.write_text("ExitApp\n", encoding="utf-8")
    manifest_file = project_root / ".python-exe-builder.json"
    manifest_file.write_text(
        '{"schema_version": 1, "pyinstaller": '
        '{"collect_all": ["uiautomation"]}}',
        encoding="utf-8",
    )

    output_dir = tmp_path / "dist"
    output_dir.mkdir()

    python_dir = tmp_path / "Python314"
    python_dir.mkdir()
    python_exe = python_dir / "python.exe"
    python_exe.write_text("", encoding="utf-8")

    monkeypatch.setattr(build_controller, "validate_bundle_inputs", lambda app: (True, ""))
    monkeypatch.setattr(build_controller, "QThread", DummyThread)
    monkeypatch.setattr(build_controller, "BuildWorker", FakeWorker)
    monkeypatch.setattr(BuildController, "start_eta", lambda self: None)

    monkeypatch.setattr(
        build_controller.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    app = make_app(
        script_path_input=DummyInput(str(script)),
        output_path_input=DummyInput(str(output_dir)),
        build_process=None,
        icon_path="",
        output_path="",
        build_btn=DummyButton(),
        status_label=DummyLabel(),
        validation_controller=DummyValidationController(),
        last_build_counter=0,
        append_datetime=False,
        repaint=lambda: None,
        set_status=lambda _message: None,
        python_interpreter_path=str(python_exe),
        entry_script=str(script),
        project_root=str(project_root),
    )
    controller = BuildController(app)

    controller.build_exe(app)

    assert f"--paths={project_root}" in app.captured_cmd
    assert f"--add-data={project_root}{os.pathsep}." in app.captured_cmd
    assert f"--add-data={png_file}{os.pathsep}Icons" in app.captured_cmd
    assert f"--add-data={ahk_file}{os.pathsep}resources" in app.captured_cmd
    assert "--collect-all=uiautomation" in app.captured_cmd
    assert app.captured_cmd.index(f"--paths={project_root}") < app.captured_cmd.index(str(script))
    assert app.captured_cmd.index(f"--add-data={png_file}{os.pathsep}Icons") < app.captured_cmd.index(str(script))
    assert app.captured_cmd.index(
        f"--add-data={ahk_file}{os.pathsep}resources"
    ) < app.captured_cmd.index(str(script))
    assert app.captured_cmd.index(
        "--collect-all=uiautomation"
    ) < app.captured_cmd.index(str(script))
    assert f"--workpath={output_dir / 'build'}" in app.captured_cmd
    assert f"--specpath={output_dir / 'spec' / 'Builder_project'}" in app.captured_cmd
    assert app.current_build_paths == [
        os.path.join(str(output_dir), "Builder_project"),
        os.path.join(str(output_dir), "build", "Builder_project"),
        os.path.join(str(output_dir), "spec", "Builder_project"),
    ]


def test_build_exe_adds_parent_project_sibling_png_assets(tmp_path, monkeypatch):
    repo_root = tmp_path / "Browser-App-Mover"
    project_root = repo_root / "browser_app_mover"
    icon_dir = repo_root / "Icon Pngs" / "Green"
    project_root.mkdir(parents=True)
    icon_dir.mkdir(parents=True)
    (repo_root / "pyproject.toml").write_text("[project]\nname='browser-app-mover'\n", encoding="utf-8")

    script = project_root / "main.py"
    script.write_text("print('hello')\n", encoding="utf-8")
    icon = icon_dir / "Left.png"
    icon.write_text("png", encoding="utf-8")

    output_dir = tmp_path / "dist"
    output_dir.mkdir()

    python_dir = tmp_path / "Python314"
    python_dir.mkdir()
    python_exe = python_dir / "python.exe"
    python_exe.write_text("", encoding="utf-8")

    monkeypatch.setattr(build_controller, "validate_bundle_inputs", lambda app: (True, ""))
    monkeypatch.setattr(build_controller, "QThread", DummyThread)
    monkeypatch.setattr(build_controller, "BuildWorker", FakeWorker)
    monkeypatch.setattr(BuildController, "start_eta", lambda self: None)
    monkeypatch.setattr(
        build_controller.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    app = make_app(
        script_path_input=DummyInput(str(script)),
        output_path_input=DummyInput(str(output_dir)),
        build_process=None,
        icon_path="",
        output_path="",
        build_btn=DummyButton(),
        status_label=DummyLabel(),
        validation_controller=DummyValidationController(),
        last_build_counter=0,
        append_datetime=False,
        repaint=lambda: None,
        set_status=lambda _message: None,
        python_interpreter_path=str(python_exe),
        entry_script=str(script),
        project_root=str(project_root),
    )
    controller = BuildController(app)

    controller.build_exe(app)

    expected_arg = (
        f"--add-data={icon}{os.pathsep}"
        f"{os.path.normpath(os.path.join('Icon Pngs', 'Green'))}"
    )
    assert expected_arg in app.captured_cmd
    assert app.captured_cmd.index(expected_arg) < app.captured_cmd.index(str(script))


def test_build_exe_adds_parent_search_path_for_sibling_packages(tmp_path, monkeypatch):
    workspace_root = tmp_path / "workspace"
    project_root = workspace_root / "Code Workspace Builder"
    shared_root = workspace_root / "Shared"
    project_root.mkdir(parents=True)
    shared_root.mkdir()

    script = project_root / "main.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    output_dir = tmp_path / "dist"
    output_dir.mkdir()

    python_dir = tmp_path / "Python314"
    python_dir.mkdir()
    python_exe = python_dir / "python.exe"
    python_exe.write_text("", encoding="utf-8")

    monkeypatch.setattr(build_controller, "validate_bundle_inputs", lambda app: (True, ""))
    monkeypatch.setattr(build_controller, "QThread", DummyThread)
    monkeypatch.setattr(build_controller, "BuildWorker", FakeWorker)
    monkeypatch.setattr(BuildController, "start_eta", lambda self: None)
    monkeypatch.setattr(
        build_controller.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    app = make_app(
        script_path_input=DummyInput(str(script)),
        output_path_input=DummyInput(str(output_dir)),
        build_process=None,
        icon_path="",
        output_path="",
        build_btn=DummyButton(),
        status_label=DummyLabel(),
        validation_controller=DummyValidationController(),
        last_build_counter=0,
        append_datetime=False,
        repaint=lambda: None,
        set_status=lambda _message: None,
        python_interpreter_path=str(python_exe),
        entry_script=str(script),
        project_root=str(project_root),
    )
    controller = BuildController(app)

    controller.build_exe(app)

    assert f"--paths={project_root}" in app.captured_cmd
    assert f"--paths={workspace_root}" in app.captured_cmd
    assert f"--add-data={project_root}{os.pathsep}." in app.captured_cmd


def test_build_complete_focuses_existing_output_directory_window(tmp_path, monkeypatch):
    output_dir = tmp_path / "dist"
    output_dir.mkdir()
    opened_paths = []
    focused_paths = []

    monkeypatch.setattr(build_controller.os, "startfile", lambda path: opened_paths.append(path), raising=False)

    app = make_app(
        build_start_time=0,
        last_build_seconds=45,
        status_label=DummyLabel(),
        output_path=str(output_dir),
        open_output_dir_after_build_enabled=True,
        minimize_after_build_enabled=False,
        close_after_build_enabled=False,
        state_ctrl=SimpleNamespace(save_state=lambda: None),
        validation_controller=DummyValidationController(),
        set_status=lambda _message: None,
        build_process=None,
    )
    controller = BuildController(app)
    monkeypatch.setattr(
        controller,
        "_focus_existing_output_explorer_window",
        lambda path: focused_paths.append(path) or True,
    )
    monkeypatch.setattr(build_controller.time, "time", lambda: 5)
    monkeypatch.setattr(controller, "stop_eta", lambda: None)
    monkeypatch.setattr(build_controller.QTimer, "singleShot", lambda *_args, **_kwargs: None)

    controller._on_build_complete_ui(0, "", "")

    assert focused_paths == [os.path.normpath(str(output_dir))]
    assert opened_paths == []


def test_build_complete_opens_output_directory_for_non_desktop_path(tmp_path, monkeypatch):
    output_dir = tmp_path / "dist"
    output_dir.mkdir()
    opened_paths = []

    monkeypatch.setattr(build_controller.os, "startfile", lambda path: opened_paths.append(path), raising=False)

    app = make_app(
        build_start_time=0,
        last_build_seconds=45,
        status_label=DummyLabel(),
        output_path=str(output_dir),
        open_output_dir_after_build_enabled=True,
        minimize_after_build_enabled=False,
        close_after_build_enabled=False,
        state_ctrl=SimpleNamespace(save_state=lambda: None),
        validation_controller=DummyValidationController(),
        set_status=lambda _message: None,
        build_process=None,
    )
    controller = BuildController(app)
    monkeypatch.setattr(controller, "_focus_existing_output_explorer_window", lambda _path: False)
    monkeypatch.setattr(build_controller.time, "time", lambda: 5)
    monkeypatch.setattr(controller, "stop_eta", lambda: None)
    monkeypatch.setattr(build_controller.QTimer, "singleShot", lambda *_args, **_kwargs: None)

    controller._on_build_complete_ui(0, "", "")

    assert opened_paths == [os.path.normpath(str(output_dir))]


def test_build_complete_opens_output_directory_when_focus_helper_fails(tmp_path, monkeypatch):
    output_dir = tmp_path / "dist"
    output_dir.mkdir()
    opened_paths = []

    def raise_focus_error(_path):
        raise RuntimeError("focus failed")

    monkeypatch.setattr(build_controller.os, "startfile", lambda path: opened_paths.append(path), raising=False)

    app = make_app(
        build_start_time=0,
        last_build_seconds=45,
        status_label=DummyLabel(),
        output_path=str(output_dir),
        open_output_dir_after_build_enabled=True,
        minimize_after_build_enabled=False,
        close_after_build_enabled=False,
        state_ctrl=SimpleNamespace(save_state=lambda: None),
        validation_controller=DummyValidationController(),
        set_status=lambda _message: None,
        build_process=None,
    )
    controller = BuildController(app)
    monkeypatch.setattr(controller, "_focus_existing_output_explorer_window", raise_focus_error)
    monkeypatch.setattr(build_controller.time, "time", lambda: 5)
    monkeypatch.setattr(controller, "stop_eta", lambda: None)
    monkeypatch.setattr(build_controller.QTimer, "singleShot", lambda *_args, **_kwargs: None)

    controller._on_build_complete_ui(0, "", "")

    assert opened_paths == [os.path.normpath(str(output_dir))]


def test_build_complete_centers_desktop_outputs_without_opening_explorer(tmp_path, monkeypatch):
    desktop_path = os.path.normpath(str(tmp_path / "Desktop"))
    os.makedirs(desktop_path)
    opened_paths = []
    focused_paths = []
    centered = []

    monkeypatch.setattr(build_controller.os, "startfile", lambda path: opened_paths.append(path), raising=False)

    app = make_app(
        build_start_time=0,
        last_build_seconds=45,
        status_label=DummyLabel(),
        output_path=desktop_path,
        open_output_dir_after_build_enabled=True,
        minimize_after_build_enabled=False,
        close_after_build_enabled=False,
        state_ctrl=SimpleNamespace(save_state=lambda: None),
        validation_controller=DummyValidationController(),
        set_status=lambda _message: None,
        build_process=None,
    )
    controller = BuildController(app)
    monkeypatch.setattr(controller, "_get_desktop_path", lambda: desktop_path)
    monkeypatch.setattr(controller, "_center_desktop_build_outputs", lambda: centered.append(True))
    monkeypatch.setattr(
        controller,
        "_focus_existing_output_explorer_window",
        lambda path: focused_paths.append(path) or True,
    )
    monkeypatch.setattr(build_controller.time, "time", lambda: 5)
    monkeypatch.setattr(controller, "stop_eta", lambda: None)
    monkeypatch.setattr(build_controller.QTimer, "singleShot", lambda *_args, **_kwargs: None)

    controller._on_build_complete_ui(0, "", "")

    assert opened_paths == []
    assert focused_paths == []
    assert centered == [True]


def test_desktop_centering_groups_existing_build_outputs_and_debug_log(tmp_path, monkeypatch):
    desktop_path = tmp_path / "Desktop"
    desktop_path.mkdir()
    final_output = desktop_path / "Builder"
    build_output = desktop_path / "build"
    spec_output = desktop_path / "spec"
    missing_output = desktop_path / "missing"
    debug_log = desktop_path / "EXE_BUILDER_DEBUG_Builder.log"
    for path in [final_output, build_output, spec_output]:
        path.mkdir()
    debug_log.write_text("BUILD STARTED\n", encoding="utf-8")
    moved_paths = []

    app = make_app(
        current_build_paths=[
            str(final_output),
            str(build_output),
            str(spec_output),
            str(missing_output),
        ],
        debug_log_path=str(debug_log),
    )
    controller = BuildController(app)
    monkeypatch.setattr(controller, "_move_desktop_icons_to_center", lambda paths: moved_paths.extend(paths) or True)

    assert controller._center_desktop_build_outputs() is True
    assert moved_paths == [
        os.path.normpath(str(final_output)),
        os.path.normpath(str(build_output)),
        os.path.normpath(str(spec_output)),
        os.path.normpath(str(debug_log)),
    ]


def test_build_complete_restores_ui_before_desktop_centering_and_minimize(tmp_path, monkeypatch):
    desktop_path = os.path.normpath(str(tmp_path / "Desktop"))
    os.makedirs(desktop_path)
    events = []

    app = make_app(
        build_start_time=0,
        last_build_seconds=45,
        status_label=DummyLabel(),
        output_path=desktop_path,
        open_output_dir_after_build_enabled=False,
        minimize_after_build_enabled=True,
        close_after_build_enabled=False,
        state_ctrl=SimpleNamespace(save_state=lambda: events.append(("save", app.building))),
        set_status=lambda _message: events.append(("status", app.building)),
        build_process=object(),
        building=True,
        showMinimized=lambda: events.append(("minimize", app.building)),
    )
    app.validation_controller = SimpleNamespace(
        update_build_button=lambda: events.append(("button", app.building)),
        update_ui_state=lambda: events.append(("ui", app.building)),
    )
    controller = BuildController(app)
    monkeypatch.setattr(controller, "_get_desktop_path", lambda: desktop_path)
    monkeypatch.setattr(controller, "_center_desktop_build_outputs", lambda: events.append(("center", app.building)))
    monkeypatch.setattr(build_controller.time, "time", lambda: 5)
    monkeypatch.setattr(controller, "stop_eta", lambda: events.append(("eta", app.building)))
    monkeypatch.setattr(build_controller.QTimer, "singleShot", lambda *_args, **_kwargs: None)

    controller._on_build_complete_ui(0, "", "")

    assert events == [
        ("eta", True),
        ("status", False),
        ("button", False),
        ("ui", False),
        ("center", False),
        ("save", False),
        ("minimize", False),
    ]


def test_build_complete_closes_after_desktop_centering(tmp_path, monkeypatch):
    desktop_path = os.path.normpath(str(tmp_path / "Desktop"))
    os.makedirs(desktop_path)
    events = []

    app = make_app(
        build_start_time=0,
        last_build_seconds=45,
        status_label=DummyLabel(),
        output_path=desktop_path,
        open_output_dir_after_build_enabled=False,
        minimize_after_build_enabled=False,
        close_after_build_enabled=True,
        close_app=lambda: events.append("close"),
        state_ctrl=SimpleNamespace(save_state=lambda: events.append("save")),
        validation_controller=DummyValidationController(),
        set_status=lambda _message: None,
        build_process=None,
    )
    controller = BuildController(app)
    monkeypatch.setattr(controller, "_get_desktop_path", lambda: desktop_path)
    monkeypatch.setattr(controller, "_center_desktop_build_outputs", lambda: events.append("center"))
    monkeypatch.setattr(build_controller.time, "time", lambda: 5)
    monkeypatch.setattr(controller, "stop_eta", lambda: None)
    monkeypatch.setattr(build_controller.QTimer, "singleShot", lambda *_args, **_kwargs: None)

    controller._on_build_complete_ui(0, "", "")

    assert events == ["center", "save", "close"]


def test_desktop_centering_failure_does_not_block_save_or_close(tmp_path, monkeypatch):
    desktop_path = os.path.normpath(str(tmp_path / "Desktop"))
    os.makedirs(desktop_path)
    events = []

    def raise_center_error():
        events.append("center")
        raise RuntimeError("desktop unavailable")

    app = make_app(
        build_start_time=0,
        last_build_seconds=45,
        status_label=DummyLabel(),
        output_path=desktop_path,
        open_output_dir_after_build_enabled=False,
        minimize_after_build_enabled=False,
        close_after_build_enabled=True,
        close_app=lambda: events.append("close"),
        state_ctrl=SimpleNamespace(save_state=lambda: events.append("save")),
        validation_controller=DummyValidationController(),
        set_status=lambda _message: None,
        build_process=None,
    )
    controller = BuildController(app)
    monkeypatch.setattr(controller, "_get_desktop_path", lambda: desktop_path)
    monkeypatch.setattr(controller, "_center_desktop_build_outputs", raise_center_error)
    monkeypatch.setattr(build_controller.time, "time", lambda: 5)
    monkeypatch.setattr(controller, "stop_eta", lambda: None)
    monkeypatch.setattr(build_controller.QTimer, "singleShot", lambda *_args, **_kwargs: None)

    controller._on_build_complete_ui(0, "", "")

    assert events == ["center", "save", "close"]


def test_build_complete_opens_output_directory_before_closing(tmp_path, monkeypatch):
    output_dir = tmp_path / "dist"
    output_dir.mkdir()
    events = []

    monkeypatch.setattr(
        build_controller.os,
        "startfile",
        lambda path: events.append(("open", path)),
        raising=False,
    )

    app = make_app(
        build_start_time=0,
        last_build_seconds=45,
        status_label=DummyLabel(),
        output_path=str(output_dir),
        open_output_dir_after_build_enabled=True,
        minimize_after_build_enabled=False,
        close_after_build_enabled=True,
        close_app=lambda: events.append(("close", None)),
        state_ctrl=SimpleNamespace(save_state=lambda: None),
        validation_controller=DummyValidationController(),
        set_status=lambda _message: None,
        build_process=None,
    )
    controller = BuildController(app)
    monkeypatch.setattr(controller, "_focus_existing_output_explorer_window", lambda _path: False)
    monkeypatch.setattr(build_controller.time, "time", lambda: 5)
    monkeypatch.setattr(controller, "stop_eta", lambda: None)
    monkeypatch.setattr(build_controller.QTimer, "singleShot", lambda *_args, **_kwargs: None)

    controller._on_build_complete_ui(0, "", "")

    assert events == [
        ("open", os.path.normpath(str(output_dir))),
        ("close", None),
    ]
