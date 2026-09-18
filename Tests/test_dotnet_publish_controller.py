from types import SimpleNamespace

from exe_builder.controllers.dotnet_publish_controller import (
    DotnetPublishController,
    build_dotnet_publish_command,
    is_sdk_style_project,
    validate_executable_name,
)


class DummyInput:
    def __init__(self, value=""):
        self.value = value

    def text(self):
        return self.value


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
