from types import SimpleNamespace
import pytest
from PySide6.QtWidgets import QApplication, QComboBox, QPushButton
from exe_builder.ui.path_display_line_edit import PathDisplayLineEdit

from exe_builder.controllers.dotnet_publish_controller import (
    DotnetPublishController,
    DotnetPublishWorker,
    TRAY_ICON_MARKER_NAME,
    TRAY_ICON_NAME,
    build_dotnet_clean_command,
    build_dotnet_publish_command,
    is_sdk_style_project,
    sync_published_tray_icon,
    validate_executable_name,
)
from exe_builder.ui.styles import Colors, qcolor_name


class DummyInput:
    def __init__(self, value=""):
        self.value = value

    def text(self):
        return self.value

    def setStyleSheet(self, value):
        self.stylesheet = value

    def setEnabled(self, value):
        self.enabled = value

    def clear(self):
        self.value = ""


class DummyCheck:
    def __init__(self, checked=False):
        self.checked = checked

    def isChecked(self):
        return self.checked

    def setEnabled(self, value):
        self.enabled = value

    def setStyleSheet(self, value):
        self.stylesheet = value


class DummyRuntime:
    def __init__(self, value="win-x64"):
        self.value = value

    def currentData(self):
        return self.value

    def setEnabled(self, value):
        self.enabled = value


class DummyButton:
    def setEnabled(self, value):
        self.enabled = value

    def setText(self, value):
        self.text = value

    def setStyleSheet(self, value):
        self.stylesheet = value

    def setIcon(self, value):
        self.icon = value

    def setIconSize(self, value):
        self.icon_size = value

    def setFixedSize(self, width, height):
        self.size = (width, height)


class DummyStatus:
    def setText(self, value):
        self.text = value

    def setStyleSheet(self, value):
        self.stylesheet = value


class DummyFrame:
    def setStyleSheet(self, value):
        self.stylesheet = value


def make_controller(tmp_path, project_text='<Project Sdk="Microsoft.NET.Sdk"></Project>'):
    project = tmp_path / "Tool.csproj"
    project.write_text(project_text, encoding="utf-8")
    app = SimpleNamespace(
        dotnet_project_input=DummyInput(str(project)),
        dotnet_output_input=DummyInput(str(tmp_path)),
        dotnet_name_input=DummyInput("Tool"),
        dotnet_icon_input=DummyInput(""),
        dotnet_runtime_combo=DummyRuntime(),
        dotnet_self_contained=DummyCheck(True),
        dotnet_single_file=DummyCheck(False),
        dotnet_trim=DummyCheck(False),
        building=False,
        dotnet_publish_btn=DummyButton(),
        dotnet_open_output_btn=DummyButton(),
        dotnet_project_select_btn=DummyButton(),
        dotnet_icon_select_btn=DummyButton(),
        dotnet_icon_reset_btn=DummyButton(),
        dotnet_status_label=DummyStatus(),
    )
    controller = DotnetPublishController(app)
    return controller, project


def test_sdk_style_project_detection(tmp_path):
    sdk = tmp_path / "Sdk.csproj"
    legacy = tmp_path / "Legacy.csproj"
    sdk.write_text('<Project Sdk="Microsoft.NET.Sdk"></Project>', encoding="utf-8")
    legacy.write_text('<Project ToolsVersion="15.0"></Project>', encoding="utf-8")

    assert is_sdk_style_project(sdk)
    assert not is_sdk_style_project(legacy)


def test_dotnet_ui_refresh_updates_build_mode_selectors(tmp_path):
    controller, _ = make_controller(tmp_path)
    controller.app.build_mode = "dotnet"
    refreshes = []
    controller.app._apply_build_mode_button_state = refreshes.append

    controller.app.building = True
    controller.refresh_ui()
    controller.app.building = False
    controller.refresh_ui()

    assert refreshes == ["dotnet", "dotnet"]


def test_publish_command_contains_selected_options(tmp_path):
    command = build_dotnet_publish_command(
        str(tmp_path / "Tool.csproj"), str(tmp_path / "dist"), "MyTool",
        "win-arm64", True, True, True, str(tmp_path / "app.ico"),
    )

    assert command[:8] == [
        "dotnet", "publish", str(tmp_path / "Tool.csproj"), "-c", "Release",
        "-r", "win-arm64", "--self-contained",
    ]
    assert "true" in command
    assert "-p:AssemblyName=MyTool" in command
    assert "-p:PublishSingleFile=true" in command
    assert "-p:PublishTrimmed=true" in command
    assert f"-p:ApplicationIcon={tmp_path / 'app.ico'}" in command
    assert command[command.index("-o") + 1].endswith("dist\\MyTool") or command[command.index("-o") + 1].endswith("dist/MyTool")


def test_clean_command_uses_same_project_configuration(tmp_path):
    project = str(tmp_path / "Tool.csproj")
    assert build_dotnet_clean_command(project, "MyTool", "win-arm64") == [
        "dotnet", "clean", project, "-c", "Release", "-r", "win-arm64",
        "-p:AssemblyName=MyTool",
    ]


@pytest.mark.parametrize("clean_result,expected", [
    (0, [["dotnet", "clean"], ["dotnet", "publish"]]),
    (1, [["dotnet", "clean"]]),
])
def test_publish_worker_cleans_before_publish_and_stops_if_clean_fails(
    tmp_path, monkeypatch, clean_result, expected,
):
    commands = []
    results = iter([clean_result, 0])

    class FakeProcess:
        def wait(self):
            return next(results)

    def fake_popen(command, **_kwargs):
        commands.append(command)
        return FakeProcess()

    monkeypatch.setattr("exe_builder.controllers.dotnet_publish_controller.subprocess.Popen", fake_popen)
    app = SimpleNamespace(build_process=None)
    worker = DotnetPublishWorker(app, ["dotnet", "clean"], ["dotnet", "publish"], str(tmp_path / "publish.log"))
    finished = []
    worker.finished.connect(lambda code, error: finished.append((code, error)))

    worker.run()

    assert commands == expected
    assert finished == [(clean_result, "")]
    assert app.build_process is None


def test_publish_command_explicitly_disables_unselected_project_options(tmp_path):
    command = build_dotnet_publish_command(
        str(tmp_path / "Tool.csproj"), str(tmp_path / "dist"), "MyTool",
        "win-x64", False, False, False,
    )

    assert command[command.index("--self-contained") + 1] == "false"
    assert "-p:PublishSingleFile=false" in command
    assert "-p:PublishTrimmed=false" in command
    assert "-p:ApplicationIcon=" in command


def test_clear_icon_removes_the_publish_icon_and_disables_reset(tmp_path):
    controller, _ = make_controller(tmp_path)
    icon = tmp_path / "tool.ico"
    icon.write_text("ico", encoding="utf-8")
    controller.app.dotnet_icon_input.value = str(icon)

    controller.refresh_ui()
    assert controller.app.dotnet_icon_select_btn.enabled is True
    assert controller.app.dotnet_icon_reset_btn.enabled is True

    controller.clear_icon()

    assert controller.app.dotnet_icon_input.value == ""
    assert controller.app.dotnet_icon_reset_btn.enabled is False
    assert qcolor_name(Colors.MUTED_BORDER) in controller.app.dotnet_icon_input.stylesheet
    command = build_dotnet_publish_command(
        str(tmp_path / "Tool.csproj"), str(tmp_path / "dist"), "MyTool",
        "win-x64", True, False, False, controller.values()["icon"],
    )
    assert "-p:ApplicationIcon=" in command


def test_no_icon_overrides_project_application_icon(tmp_path):
    controller, project = make_controller(
        tmp_path,
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
        '<ApplicationIcon>old.ico</ApplicationIcon></PropertyGroup></Project>',
    )
    before = project.read_bytes()

    assert controller.validation_error() == ""
    command = build_dotnet_publish_command(
        str(project), str(tmp_path), "Tool", "win-x64", True, False, False,
        controller.values()["icon"],
    )

    assert "-p:ApplicationIcon=" in command
    assert project.read_bytes() == before


def test_no_icon_rejects_project_win32_resource(tmp_path):
    controller, _ = make_controller(
        tmp_path,
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
        '<Win32Resource>custom.res</Win32Resource></PropertyGroup></Project>',
    )
    assert "Win32Resource" in controller.validation_error()


def test_tray_sidecar_replaced_and_removed_across_publishes(tmp_path):
    target = tmp_path / "Tool"
    target.mkdir()
    (target / "Tool.exe").write_bytes(b"single-file executable")
    first = tmp_path / "first.ico"
    second = tmp_path / "second.ico"
    first.write_bytes(b"first icon")
    second.write_bytes(b"second icon")

    sync_published_tray_icon(str(target), str(first))
    assert (target / TRAY_ICON_NAME).read_bytes() == b"first icon"
    sync_published_tray_icon(str(target), str(second))
    assert (target / TRAY_ICON_NAME).read_bytes() == b"second icon"
    assert (target / "Tool.exe").read_bytes() == b"single-file executable"
    sync_published_tray_icon(str(target), "")
    assert not (target / TRAY_ICON_NAME).exists()
    assert not (target / TRAY_ICON_MARKER_NAME).exists()


def test_no_icon_keeps_unmanaged_sidecar(tmp_path):
    target = tmp_path / "Tool"
    target.mkdir()
    sidecar = target / TRAY_ICON_NAME
    sidecar.write_bytes(b"user icon")

    sync_published_tray_icon(str(target), "")

    assert sidecar.read_bytes() == b"user icon"


def test_dotnet_recents_select_and_delete_independently(tmp_path, monkeypatch):
    QApplication.instance() or QApplication([])
    controller, project = make_controller(tmp_path)
    app = controller.app
    app.csharp_state_data = {}
    app.state_ctrl = SimpleNamespace(save_state=lambda: None)
    app.recent_controller = SimpleNamespace(
        _confirm_delete_recent_item=lambda *_: True,
        _show_recent_delete_confirmation=lambda *_: True,
    )
    for kind in ("project", "icon"):
        setattr(app, f"dotnet_{kind}_input", PathDisplayLineEdit())
        setattr(app, f"dotnet_{kind}_select_btn", QPushButton())
        setattr(app, f"dotnet_{kind}_delete_btn", QPushButton())
        setattr(app, f"dotnet_{kind}_delete_all_btn", QPushButton())
    app.dotnet_recent_projects = QComboBox()
    app.dotnet_recent_icons = QComboBox()
    monkeypatch.setattr("exe_builder.controllers.dotnet_publish_controller.flash_add_highlight", lambda *_: None)
    monkeypatch.setattr("exe_builder.controllers.dotnet_publish_controller.flash_delete_highlight", lambda *_: None)

    controller.select_path("project", str(project))
    assert app.dotnet_name_input.value == "Tool"
    assert app.dotnet_recent_projects.count() == 2
    icon = tmp_path / "tool.ico"
    icon.write_bytes(b"icon")
    controller.select_path("icon", str(icon))
    assert app.dotnet_recent_icons.count() == 3  # heading, No Icon, selected icon

    controller.delete_recent("project")
    assert not app.dotnet_project_input.text()
    assert not app.csharp_state_data["recent_projects"]
    assert app.dotnet_icon_input.text() == str(icon)
    controller.delete_recent("icon", all_items=True)
    assert not app.dotnet_icon_input.text()
    assert not app.csharp_state_data["recent_icons"]


def test_icon_controls_are_disabled_while_publishing(tmp_path):
    controller, _ = make_controller(tmp_path)
    controller.app.dotnet_icon_input.value = str(tmp_path / "tool.ico")
    controller.app.building = True

    controller.refresh_ui()

    assert controller.app.dotnet_icon_select_btn.enabled is False
    assert controller.app.dotnet_icon_reset_btn.enabled is False


def test_validation_rejects_legacy_project_and_invalid_fields(tmp_path):
    controller, project = make_controller(tmp_path, '<Project ToolsVersion="15.0"></Project>')
    assert "SDK-style" in controller.validation_error()

    project.write_text('<Project Sdk="Microsoft.NET.Sdk"></Project>', encoding="utf-8")
    controller.app.dotnet_name_input.value = "bad/name"
    assert "filename" in controller.validation_error()

    controller.app.dotnet_name_input.value = "Tool"
    controller.app.dotnet_runtime_combo.value = "linux-x64"
    assert "runtime" in controller.validation_error()


def test_validation_accepts_complete_sdk_project(tmp_path):
    controller, _ = make_controller(tmp_path)
    assert controller.validation_error() == ""
    assert controller.output_path().endswith("Tool")


def test_publish_button_uses_readiness_colours(tmp_path):
    controller, _ = make_controller(tmp_path)

    controller.refresh_ui()

    assert controller.app.dotnet_publish_btn.enabled is True
    assert qcolor_name(Colors.SUCCESS) in controller.app.dotnet_publish_btn.stylesheet

    controller.app.dotnet_project_input.value = str(tmp_path / "missing.csproj")
    controller.refresh_ui()

    assert controller.app.dotnet_publish_btn.enabled is False
    assert qcolor_name(Colors.ERROR) in controller.app.dotnet_publish_btn.stylesheet


def test_project_file_button_uses_project_validity_colours(tmp_path):
    controller, project = make_controller(tmp_path)

    controller.refresh_ui()
    button = controller.app.dotnet_project_select_btn
    assert button.enabled is True
    assert qcolor_name(Colors.SUCCESS) in button.stylesheet

    project.write_text('<Project ToolsVersion="15.0"></Project>', encoding="utf-8")
    controller.refresh_ui()
    assert qcolor_name(Colors.ERROR) in button.stylesheet

    controller.app.building = True
    controller.refresh_ui()
    assert button.enabled is False
    assert qcolor_name(Colors.BUILD_DISABLED_BG) in button.stylesheet


def test_open_output_button_requires_current_published_executable(tmp_path):
    controller, _ = make_controller(tmp_path)
    target = tmp_path / "Tool"
    target.mkdir()

    controller.refresh_ui()

    assert controller.app.dotnet_open_output_btn.enabled is False
    assert qcolor_name(Colors.BUILD_DISABLED_BG) in controller.app.dotnet_open_output_btn.stylesheet

    (target / "Tool.exe").write_bytes(b"published")
    controller.refresh_ui()

    assert controller.app.dotnet_open_output_btn.enabled is True
    assert qcolor_name(Colors.TITLE_BG) in controller.app.dotnet_open_output_btn.stylesheet

    controller.app.building = True
    controller.refresh_ui()

    assert controller.app.dotnet_open_output_btn.enabled is False
    assert qcolor_name(Colors.BUILD_DISABLED_BG) in controller.app.dotnet_open_output_btn.stylesheet


def test_open_output_button_tracks_current_executable_name(tmp_path):
    controller, _ = make_controller(tmp_path)
    target = tmp_path / "Tool"
    target.mkdir()
    (target / "Tool.exe").write_bytes(b"published")

    controller.refresh_ui()
    assert controller.app.dotnet_open_output_btn.enabled is True

    controller.app.dotnet_name_input.value = "RenamedTool"
    controller.refresh_ui()

    assert controller.app.dotnet_open_output_btn.enabled is False


def test_open_output_folder_does_not_open_incomplete_target(tmp_path, monkeypatch):
    controller, _ = make_controller(tmp_path)
    target = tmp_path / "Tool"
    target.mkdir()
    opened = []
    monkeypatch.setattr(
        "exe_builder.controllers.dotnet_publish_controller.os.startfile",
        opened.append,
        raising=False,
    )

    controller.open_output_folder()

    assert opened == []


def test_windows_executable_name_rules():
    assert validate_executable_name("")
    assert validate_executable_name("CON")
    assert validate_executable_name("Tool.")
    assert validate_executable_name("GoodTool") == ""


def test_publish_completion_leaves_executable_untouched(tmp_path):
    controller, _ = make_controller(tmp_path)
    icon = tmp_path / "tool.ico"
    icon.write_bytes(b"selected-icon")
    target = tmp_path / "Tool"
    target.mkdir()
    executable = target / "Tool.exe"
    executable.write_bytes(b"apphost-with-single-file-bundle")
    controller.app.dotnet_icon_input.value = str(icon)
    controller.app.debug_log_path = str(tmp_path / "publish.log")
    controller.app.build_start_time = 0
    controller.app.output_path = str(tmp_path)
    controller.app.building = True
    controller.app.build_process = object()
    controller.app.last_build_seconds = 0
    controller.app.state_ctrl = SimpleNamespace(save_state=lambda: None)
    presented_outputs = []
    controller._publish_output_dir = str(tmp_path)
    controller.app.build_controller = SimpleNamespace(
        _present_successful_build_outputs=presented_outputs.append,
        _run_success_post_build_action=lambda: None,
    )
    controller._on_publish_finished(0, "")

    assert executable.read_bytes() == b"apphost-with-single-file-bundle"
    assert (target / TRAY_ICON_NAME).read_bytes() == b"selected-icon"
    assert controller.app.dotnet_status_label.text == "Publish complete."
    assert presented_outputs == [str(tmp_path)]


def test_publish_completion_preserves_python_output_path(tmp_path):
    controller, _ = make_controller(tmp_path)
    python_output = tmp_path / "python-dist"
    python_output.mkdir()
    desktop_output = tmp_path / "Desktop"
    desktop_output.mkdir()
    target = desktop_output / "Tool"
    target.mkdir()

    controller.app.output_path = str(python_output)
    controller.app.dotnet_output_input.value = str(desktop_output)
    controller.app.debug_log_path = str(desktop_output / "publish.log")
    controller.app.build_start_time = 0
    controller.app.building = True
    controller.app.build_process = object()
    controller.app.last_build_seconds = 0
    controller.app.state_ctrl = SimpleNamespace(
        save_csharp_state=lambda: None,
        save_state=lambda: None,
    )
    presented_outputs = []
    controller._publish_output_dir = str(desktop_output)
    controller.app.build_controller = SimpleNamespace(
        _present_successful_build_outputs=presented_outputs.append,
        _run_success_post_build_action=lambda: None,
    )

    controller._on_publish_finished(0, "")

    assert controller.app.output_path == str(python_output)
    assert presented_outputs == [str(desktop_output)]


@pytest.mark.parametrize("result,cancelled", [(1, False), (0, True)])
def test_failed_or_cancelled_publish_keeps_existing_tray_sidecar(tmp_path, result, cancelled):
    controller, project = make_controller(tmp_path)
    project_before = project.read_bytes()
    target = tmp_path / "Tool"
    target.mkdir()
    original = tmp_path / "original.ico"
    replacement = tmp_path / "replacement.ico"
    original.write_bytes(b"original")
    replacement.write_bytes(b"replacement")
    sync_published_tray_icon(str(target), str(original))
    controller._publish_target = str(target)
    controller._publish_icon_path = str(replacement)
    controller._cancelled = cancelled
    controller.app.building = True
    controller.app.build_process = object()

    controller._on_publish_finished(result, "publish failed")

    assert (target / TRAY_ICON_NAME).read_bytes() == b"original"
    assert project.read_bytes() == project_before


def test_cancel_keeps_existing_publish_folder(tmp_path):
    controller, _ = make_controller(tmp_path)
    target = tmp_path / "Tool"
    target.mkdir()
    existing = target / "user-data.txt"
    existing.write_text("keep", encoding="utf-8")
    controller.app.building = True
    controller.app.build_process = None

    controller.cancel()

    assert existing.read_text(encoding="utf-8") == "keep"
    assert controller._cancelled is True


def test_publish_failure_remains_visible_after_controls_refresh(tmp_path):
    controller, _ = make_controller(tmp_path)
    controller.app.building = True
    controller.app.build_process = object()

    controller._on_publish_finished(1, "SDK publish failed")

    assert controller.app.dotnet_status_label.text == "SDK publish failed"
    assert qcolor_name(Colors.ERROR) in controller.app.dotnet_status_label.stylesheet


def test_refresh_styles_dotnet_paths_like_python_validation(tmp_path):
    controller, project = make_controller(tmp_path)
    icon = tmp_path / "tool.ico"
    icon.write_text("ico", encoding="utf-8")
    controller.app.dotnet_icon_input.value = str(icon)

    controller.refresh_ui()

    for field in (
        controller.app.dotnet_project_input,
        controller.app.dotnet_output_input,
        controller.app.dotnet_icon_input,
        controller.app.dotnet_name_input,
    ):
        assert qcolor_name(Colors.PANEL_BG) in field.stylesheet
        assert qcolor_name(Colors.SUCCESS) in field.stylesheet
    assert qcolor_name(Colors.SUCCESS) in controller.app.dotnet_status_label.stylesheet
    assert controller.app.dotnet_status_label.text == "Ready to publish"

    controller.app.dotnet_project_input.value = str(project.with_name("missing.csproj"))
    controller.app.dotnet_icon_input.value = ""
    controller.refresh_ui()

    assert qcolor_name(Colors.ERROR) in controller.app.dotnet_project_input.stylesheet
    assert qcolor_name(Colors.MUTED_BORDER) in controller.app.dotnet_icon_input.stylesheet

    controller.app.dotnet_name_input.value = "invalid/name"
    controller.refresh_ui()
    assert qcolor_name(Colors.ERROR) in controller.app.dotnet_name_input.stylesheet
    assert qcolor_name(Colors.ERROR) in controller.app.dotnet_status_label.stylesheet

    controller.app.building = True
    controller.refresh_ui()
    assert qcolor_name(Colors.BUILD_DISABLED_TEXT) in controller.app.dotnet_project_input.stylesheet
    assert qcolor_name(Colors.BUILD_DISABLED_TEXT) in controller.app.dotnet_name_input.stylesheet


def test_refresh_styles_dotnet_utility_buttons_like_python_buttons(tmp_path):
    controller, _ = make_controller(tmp_path)
    controller.app.dotnet_name_input.value = "CustomTool"
    for name in (
        "dotnet_project_delete_btn", "dotnet_project_delete_all_btn",
        "dotnet_project_reset_btn", "dotnet_icon_delete_btn",
        "dotnet_icon_delete_all_btn", "dotnet_output_reset_btn",
        "dotnet_name_reset_btn",
    ):
        setattr(controller.app, name, DummyButton())

    controller.refresh_ui()

    assert qcolor_name(Colors.TITLE_BG) in controller.app.dotnet_project_delete_btn.stylesheet
    assert qcolor_name(Colors.TITLE_BG) in controller.app.dotnet_name_reset_btn.stylesheet

    controller.app.building = True
    controller.refresh_ui()

    assert qcolor_name(Colors.BUILD_DISABLED_BG) in controller.app.dotnet_project_delete_btn.stylesheet


def test_dotnet_empty_selection_clear_and_delete_controls_are_greyed(tmp_path):
    controller, _ = make_controller(tmp_path)
    for name in (
        "dotnet_project_delete_btn", "dotnet_project_reset_btn",
        "dotnet_icon_delete_btn", "dotnet_icon_reset_btn",
    ):
        setattr(controller.app, name, DummyButton())
    controller.app.dotnet_project_input.value = ""

    controller.refresh_ui()

    for name in (
        "dotnet_project_delete_btn", "dotnet_project_reset_btn",
        "dotnet_icon_delete_btn", "dotnet_icon_reset_btn",
    ):
        button = getattr(controller.app, name)
        assert button.enabled is False
        assert button.text == ""
        assert qcolor_name(Colors.BUILD_DISABLED_BG) in button.stylesheet
        assert button.icon.isNull()


def test_dotnet_populated_selection_clear_and_delete_controls_restore(tmp_path):
    controller, project = make_controller(tmp_path)
    icon = tmp_path / "tool.ico"
    icon.write_text("ico", encoding="utf-8")
    for name in (
        "dotnet_project_delete_btn", "dotnet_project_reset_btn",
        "dotnet_icon_delete_btn", "dotnet_icon_reset_btn",
    ):
        setattr(controller.app, name, DummyButton())
    controller.app.dotnet_project_input.value = str(project)
    controller.app.dotnet_icon_input.value = str(icon)

    controller.refresh_ui()

    for name in (
        "dotnet_project_delete_btn", "dotnet_project_reset_btn",
        "dotnet_icon_delete_btn", "dotnet_icon_reset_btn",
    ):
        button = getattr(controller.app, name)
        assert button.enabled is True
        assert qcolor_name(Colors.TITLE_BG) in button.stylesheet
        assert not button.icon.isNull()


def test_dotnet_output_reset_icon_restores_after_build_lock(tmp_path):
    controller, _ = make_controller(tmp_path)
    output_reset = DummyButton()
    controller.app.dotnet_output_reset_btn = output_reset

    controller.refresh_ui()
    assert not output_reset.icon.isNull()
    assert output_reset.size == (35, 35)

    controller.app.building = True
    controller.refresh_ui()
    assert output_reset.icon.isNull()

    controller.app.building = False
    controller.refresh_ui()
    assert not output_reset.icon.isNull()


def test_dotnet_utility_icons_clear_and_restore_during_build(tmp_path, monkeypatch):
    class IconSpy:
        def __init__(self, path=None):
            self.path = str(path or "")

        def isNull(self):
            return not self.path

    monkeypatch.setattr(
        "exe_builder.controllers.dotnet_publish_controller.QIcon", IconSpy,
    )
    controller, _ = make_controller(tmp_path)
    controller.app.dotnet_name_input.value = "CustomTool"
    icon = tmp_path / "tool.ico"
    icon.write_text("ico", encoding="utf-8")
    controller.app.dotnet_icon_input.value = str(icon)
    button_icons = {
        "dotnet_project_delete_btn": "utility_delete.svg",
        "dotnet_project_delete_all_btn": "utility_delete_all.svg",
        "dotnet_project_reset_btn": "utility_refresh.svg",
        "dotnet_icon_delete_btn": "utility_delete.svg",
        "dotnet_icon_delete_all_btn": "utility_delete_all.svg",
        "dotnet_icon_reset_btn": "utility_refresh.svg",
        "dotnet_name_reset_btn": "utility_refresh.svg",
    }
    for name in button_icons:
        setattr(controller.app, name, DummyButton())

    controller.refresh_ui()
    for name, expected_icon in button_icons.items():
        button = getattr(controller.app, name)
        assert not button.icon.isNull()
        assert button.icon.path.endswith(expected_icon)
        assert button.size == (35, 35)

    controller.app.building = True
    controller.refresh_ui()
    assert all(getattr(controller.app, name).icon.isNull() for name in button_icons)

    controller.app.building = False
    controller.refresh_ui()
    for name, expected_icon in button_icons.items():
        button = getattr(controller.app, name)
        assert not button.icon.isNull()
        assert button.icon.path.endswith(expected_icon)


def test_dotnet_name_reset_disables_when_name_matches_project(tmp_path):
    controller, _ = make_controller(tmp_path)
    controller.app.dotnet_name_reset_btn = DummyButton()

    controller.refresh_ui()

    button = controller.app.dotnet_name_reset_btn
    assert button.enabled is False
    assert qcolor_name(Colors.BUILD_DISABLED_BG) in button.stylesheet
    assert button.icon.isNull()

    controller.app.dotnet_name_input.value = "CustomTool"
    controller.refresh_ui()

    assert button.enabled is True
    assert qcolor_name(Colors.TITLE_BG) in button.stylesheet
    assert not button.icon.isNull()

    controller.app.dotnet_project_input.value = ""
    controller.refresh_ui()

    assert button.enabled is False
    assert qcolor_name(Colors.BUILD_DISABLED_BG) in button.stylesheet
    assert button.icon.isNull()


def test_publish_lock_keeps_csharp_configuration_frames_blue(tmp_path):
    controller, _ = make_controller(tmp_path)
    app = controller.app
    for name in (
        "dotnet_project_select_btn", "dotnet_output_select_btn",
        "dotnet_project_delete_btn", "dotnet_project_delete_all_btn",
        "dotnet_project_reset_btn", "dotnet_icon_delete_btn",
        "dotnet_icon_delete_all_btn", "dotnet_output_reset_btn",
        "dotnet_name_reset_btn", "dotnet_recent_projects", "dotnet_recent_icons",
    ):
        setattr(app, name, DummyButton())
    app.dotnet_section_title_frames = [DummyFrame(), DummyFrame(), DummyFrame()]
    app.dotnet_configuration_frames = [DummyFrame(), DummyFrame(), DummyFrame()]
    app.dotnet_mode_title = DummyFrame()

    app.building = True
    controller.refresh_ui()

    for control in (
        app.dotnet_project_input, app.dotnet_output_input, app.dotnet_icon_input,
        app.dotnet_name_input, app.dotnet_runtime_combo, app.dotnet_self_contained,
        app.dotnet_single_file, app.dotnet_trim, app.dotnet_project_select_btn,
        app.dotnet_icon_select_btn, app.dotnet_output_select_btn,
        app.dotnet_recent_projects, app.dotnet_recent_icons,
        app.dotnet_open_output_btn,
    ):
        assert control.enabled is False
    for field in (
        app.dotnet_project_input, app.dotnet_output_input, app.dotnet_icon_input,
        app.dotnet_name_input,
    ):
        assert qcolor_name(Colors.BUILD_DISABLED_TEXT) in field.stylesheet
    for checkbox in (
        app.dotnet_self_contained, app.dotnet_single_file, app.dotnet_trim,
    ):
        assert qcolor_name(Colors.BUILD_DISABLED_TEXT) in checkbox.stylesheet
    for button in (
        app.dotnet_project_select_btn, app.dotnet_icon_select_btn,
        app.dotnet_output_select_btn, app.dotnet_open_output_btn,
    ):
        assert qcolor_name(Colors.BUILD_DISABLED_BG) in button.stylesheet
    assert app.dotnet_publish_btn.enabled is True
    assert app.dotnet_publish_btn.text == "Cancel Publish"
    assert qcolor_name(Colors.CANCEL) in app.dotnet_publish_btn.stylesheet
    for frame in app.dotnet_section_title_frames:
        assert qcolor_name(Colors.BUILD_DISABLED_TEXT) in frame.stylesheet
    for frame in app.dotnet_configuration_frames:
        assert qcolor_name(Colors.PANEL_BG) in frame.stylesheet
    assert qcolor_name(Colors.BUILD_DISABLED_TEXT) in app.dotnet_mode_title.stylesheet

    app.building = False
    controller.refresh_ui()

    for control in (
        app.dotnet_project_input, app.dotnet_output_input, app.dotnet_icon_input,
        app.dotnet_name_input, app.dotnet_runtime_combo, app.dotnet_self_contained,
        app.dotnet_single_file, app.dotnet_trim, app.dotnet_project_select_btn,
        app.dotnet_icon_select_btn, app.dotnet_output_select_btn,
        app.dotnet_recent_projects, app.dotnet_recent_icons,
    ):
        assert control.enabled is True
    assert app.dotnet_publish_btn.text == "Publish"
    assert qcolor_name(Colors.SUCCESS) in app.dotnet_publish_btn.stylesheet
    for frame in app.dotnet_section_title_frames:
        assert qcolor_name(Colors.TEXT_LIGHT) in frame.stylesheet
    for frame in app.dotnet_configuration_frames:
        assert qcolor_name(Colors.PANEL_BG) in frame.stylesheet


def test_output_refresh_matches_python_desktop_state(tmp_path, monkeypatch):
    controller, _ = make_controller(tmp_path)
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    controller.app.dotnet_output_reset_btn = DummyButton()
    monkeypatch.setattr(
        "exe_builder.controllers.dotnet_publish_controller.os.path.expanduser",
        lambda _path: str(tmp_path),
    )

    controller.app.dotnet_output_input.value = str(desktop).upper()
    controller.refresh_ui()

    assert controller.app.dotnet_output_reset_btn.enabled is False
    assert qcolor_name(Colors.BUILD_DISABLED_BG) in controller.app.dotnet_output_reset_btn.stylesheet
    assert controller.app.dotnet_output_reset_btn.icon.isNull()

    controller.app.dotnet_output_input.value = str(tmp_path)
    controller.refresh_ui()

    assert controller.app.dotnet_output_reset_btn.enabled is True
    assert qcolor_name(Colors.TITLE_BG) in controller.app.dotnet_output_reset_btn.stylesheet
    assert not controller.app.dotnet_output_reset_btn.icon.isNull()

    controller.app.building = True
    controller.refresh_ui()

    assert controller.app.dotnet_output_reset_btn.enabled is False
    assert qcolor_name(Colors.BUILD_DISABLED_BG) in controller.app.dotnet_output_reset_btn.stylesheet
