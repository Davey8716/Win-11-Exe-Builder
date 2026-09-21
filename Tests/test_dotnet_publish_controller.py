from types import SimpleNamespace
from PySide6.QtWidgets import QApplication, QComboBox, QPushButton
from exe_builder.ui.path_display_line_edit import PathDisplayLineEdit

from exe_builder.controllers.dotnet_publish_controller import (
    DotnetPublishController,
    build_dotnet_publish_command,
    is_sdk_style_project,
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

    def clear(self):
        self.value = ""


class DummyCheck:
    def __init__(self, checked=False):
        self.checked = checked

    def isChecked(self):
        return self.checked


class DummyRuntime:
    def __init__(self, value="win-x64"):
        self.value = value

    def currentData(self):
        return self.value


class DummyButton:
    def setEnabled(self, value):
        self.enabled = value

    def setText(self, value):
        self.text = value

    def setStyleSheet(self, value):
        self.stylesheet = value


class DummyStatus:
    def setText(self, value):
        self.text = value

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


def test_publish_command_explicitly_disables_unselected_project_options(tmp_path):
    command = build_dotnet_publish_command(
        str(tmp_path / "Tool.csproj"), str(tmp_path / "dist"), "MyTool",
        "win-x64", False, False, False,
    )

    assert command[command.index("--self-contained") + 1] == "false"
    assert "-p:PublishSingleFile=false" in command
    assert "-p:PublishTrimmed=false" in command
    assert not any(part.startswith("-p:ApplicationIcon=") for part in command)


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
    assert not any(part.startswith("-p:ApplicationIcon=") for part in command)


def test_dotnet_recents_select_and_delete_independently(tmp_path, monkeypatch):
    QApplication.instance() or QApplication([])
    controller, project = make_controller(tmp_path)
    app = controller.app
    app.state_data = {"dotnet_publish": {}}
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
    assert not app.state_data["dotnet_publish"]["recent_projects"]
    assert app.dotnet_icon_input.text() == str(icon)
    controller.delete_recent("icon", all_items=True)
    assert not app.dotnet_icon_input.text()
    assert not app.state_data["dotnet_publish"]["recent_icons"]


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
    controller.app.build_controller = SimpleNamespace(
        _present_successful_build_outputs=lambda: None,
        _run_success_post_build_action=lambda: None,
    )
    controller._on_publish_finished(0, "")

    assert executable.read_bytes() == b"apphost-with-single-file-bundle"
    assert controller.app.dotnet_status_label.text == "Publish complete."


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
