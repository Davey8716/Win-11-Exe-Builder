from types import SimpleNamespace

from exe_builder.controllers.output_folder_monitor import (
    OUTPUT_FOLDER_MONITOR_INTERVAL_MS,
    OutputFolderValidityMonitor,
)


class DummyInput:
    def __init__(self, value):
        self.value = str(value)

    def text(self):
        return self.value


class RecordingValidator:
    def __init__(self):
        self.refreshes = 0

    def update_ui_state(self):
        self.refreshes += 1


class RecordingDotnetController:
    def __init__(self):
        self.refreshes = 0

    def refresh_ui(self):
        self.refreshes += 1


def make_app(python_output, dotnet_output):
    app = SimpleNamespace(
        building=False,
        output_path_input=DummyInput(python_output),
        dotnet_output_input=DummyInput(dotnet_output),
        validator=RecordingValidator(),
        dotnet_publish_controller=RecordingDotnetController(),
    )
    return app


def test_output_folder_monitor_refreshes_both_modes_after_delete_and_recreate(tmp_path):
    python_output = tmp_path / "python-output"
    dotnet_output = tmp_path / "dotnet-output"
    python_output.mkdir()
    dotnet_output.mkdir()
    app = make_app(python_output, dotnet_output)
    monitor = OutputFolderValidityMonitor(app)

    monitor.refresh_if_changed()
    assert app.validator.refreshes == 0
    assert app.dotnet_publish_controller.refreshes == 0

    python_output.rmdir()
    dotnet_output.rmdir()
    monitor.refresh_if_changed()
    assert app.validator.refreshes == 1
    assert app.dotnet_publish_controller.refreshes == 1
    assert monitor.snapshot["python"][1] is False
    assert monitor.snapshot["dotnet"][1] is False

    python_output.mkdir()
    dotnet_output.mkdir()
    monitor.refresh_if_changed()
    assert app.validator.refreshes == 2
    assert app.dotnet_publish_controller.refreshes == 2
    assert monitor.snapshot["python"][1] is True
    assert monitor.snapshot["dotnet"][1] is True


def test_output_folder_monitor_defers_changes_while_building(tmp_path):
    python_output = tmp_path / "python-output"
    dotnet_output = tmp_path / "dotnet-output"
    python_output.mkdir()
    dotnet_output.mkdir()
    app = make_app(python_output, dotnet_output)
    monitor = OutputFolderValidityMonitor(app)

    python_output.rmdir()
    app.building = True
    monitor.refresh_if_changed()
    assert app.validator.refreshes == 0

    app.building = False
    monitor.refresh_if_changed()
    assert app.validator.refreshes == 1


def test_output_folder_monitor_uses_a_two_second_interval():
    assert OUTPUT_FOLDER_MONITOR_INTERVAL_MS == 2_000
