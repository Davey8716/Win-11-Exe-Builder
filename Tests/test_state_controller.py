import json
import os
from types import SimpleNamespace

from exe_builder.build.datetime_build_options import (
    ISO_MASS_DATETIME_BUILD_SENTINEL,
    MASS_DATETIME_BUILD_SENTINEL,
    UK_MASS_DATETIME_BUILD_SENTINEL,
    USA_MASS_DATETIME_BUILD_SENTINEL,
)
from exe_builder.controllers.state_controller import StateController


def make_app(**overrides):
    app = SimpleNamespace(
        script_path="",
        icon_path="",
        output_path="",
        python_interpreter_path="",
        exe_name="",
        last_build_seconds=45,
        state_data={},
    )

    for name, value in overrides.items():
        setattr(app, name, value)

    return app


class DummyCheckbox:
    def __init__(self):
        self.checked = None

    def blockSignals(self, _value):
        pass

    def setChecked(self, value):
        self.checked = value


class DummyInput:
    def __init__(self, value=""):
        self.value = value

    def blockSignals(self, _value):
        pass

    def setText(self, value):
        self.value = value

    def set_display_path(self, value):
        self.value = value

    def text(self):
        return self.value


class DummyValidator:
    def update_ui_state(self):
        pass


class DummyEnvironmentSyncController:
    def __init__(self, profiles=None):
        self.profiles = profiles if profiles is not None else []
        self.loaded_profiles = None
        self.update_ui = None

    def serialize_profiles(self):
        return self.profiles

    def load_serialized_profiles(self, profiles, update_ui=True):
        self.loaded_profiles = profiles
        self.update_ui = update_ui


class DummyDropdownItem:
    def __init__(self, enabled=True):
        self.enabled = enabled

    def isEnabled(self):
        return self.enabled


class DummyDropdownModel:
    def __init__(self, items):
        self.items = items

    def item(self, index):
        return self.items[index]


class DummyDropdown:
    def __init__(self, options):
        self.options = list(options)
        self.current_index = None

    def count(self):
        return len(self.options)

    def blockSignals(self, _value):
        pass

    def itemText(self, index):
        return self.options[index]["text"]

    def findData(self, value):
        for index, option in enumerate(self.options):
            if option["data"] == value:
                return index
        return -1

    def setCurrentIndex(self, index):
        self.current_index = index

    def currentText(self):
        if self.current_index is None:
            return ""
        return self.itemText(self.current_index)

    def currentData(self):
        if self.current_index is None:
            return None
        return self.options[self.current_index]["data"]

    def model(self):
        return DummyDropdownModel(
            [DummyDropdownItem(enabled=option.get("enabled", True)) for option in self.options]
        )


def test_state_file_path_uses_localappdata(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    controller = StateController(make_app())

    state_path = controller._state_file_path()

    assert state_path == os.path.join(str(tmp_path), "EXEBuilder", "python_exe_builder_state.json")
    assert os.path.isdir(os.path.dirname(state_path))


def test_save_state_writes_current_values_and_preserves_recents(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    app = make_app(
        script_path=str(tmp_path / "project" / ".." / "project" / "main.py"),
        icon_path=str(tmp_path / "icon.ico"),
        output_path=str(tmp_path / "dist"),
        python_interpreter_path=str(tmp_path / "Python314" / "python.exe"),
        exe_name="Builder",
        state_data={
            "recent_scripts": ["one.py"],
            "recent_icons": ["icon.ico"],
            "recent_interpreters": ["python.exe"],
        },
    )

    controller = StateController(app)
    controller.save_state()

    with open(controller._state_file_path(), "r", encoding="utf-8") as state_file:
        data = json.load(state_file)

    assert data["last_script_path"] == os.path.normpath(app.script_path)
    assert data["last_non_desktop_output_folder"] == os.path.normpath(app.output_path)
    assert data["python_interpreter_path"] == os.path.normpath(app.python_interpreter_path)
    assert data["last_exe_name"] == "Builder"
    assert data["recent_scripts"] == ["one.py"]
    assert data["recent_icons"] == ["icon.ico"]
    assert data["recent_interpreters"] == ["python.exe"]


def test_save_state_persists_independent_dotnet_publish_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    runtime = DummyDropdown([
        {"text": "Windows x64", "data": "win-x64"},
        {"text": "Windows ARM64", "data": "win-arm64"},
    ])
    runtime.setCurrentIndex(1)
    date_selection = DummyDropdown([
        {"text": "No Date Time Appended", "data": None},
        {"text": "UK | DD-MM-YYYY", "data": "%d-%m-%Y"},
    ])
    date_selection.setCurrentIndex(1)
    self_contained = DummyCheckbox()
    self_contained.checked = True
    single_file = DummyCheckbox()
    single_file.checked = True
    trim = DummyCheckbox()
    trim.checked = False
    for checkbox in (self_contained, single_file, trim):
        checkbox.isChecked = lambda checkbox=checkbox: checkbox.checked
    app = make_app(
        build_mode="dotnet",
        dotnet_project_input=DummyInput(str(tmp_path / "Tool.csproj")),
        dotnet_output_input=DummyInput(str(tmp_path / "publish")),
        dotnet_icon_input=DummyInput(str(tmp_path / "tool.ico")),
        dotnet_name_input=DummyInput("Tool"),
        dotnet_runtime_combo=runtime,
        dotnet_date_time_dropdown=date_selection,
        dotnet_self_contained=self_contained,
        dotnet_single_file=single_file,
        dotnet_trim=trim,
    )
    controller = StateController(app)
    controller.save_csharp_state()

    with open(controller.csharp_state_file_path(), "r", encoding="utf-8") as state_file:
        data = json.load(state_file)
    assert data == {
        "project_path": os.path.normpath(str(tmp_path / "Tool.csproj")),
        "output_folder": os.path.normpath(str(tmp_path / "publish")),
        "icon_path": os.path.normpath(str(tmp_path / "tool.ico")),
        "executable_name": "Tool",
        "runtime": "win-arm64",
        "datetime_format": "%d-%m-%Y",
        "self_contained": True,
        "single_file": False,
        "trim": False,
        "recent_projects": [],
        "recent_icons": [],
        "last_non_desktop_output_folder": "",
        "last_build_seconds": 45,
            "guided_dotnet_steps": [],
    }
    assert not controller.python_state_file_path() == controller.csharp_state_file_path()


def test_save_csharp_state_preserves_an_intentionally_cleared_publish_option(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    runtime = DummyDropdown([{"text": "Windows x64", "data": "win-x64"}])
    runtime.setCurrentIndex(0)
    options = [DummyCheckbox() for _ in range(3)]
    for option in options:
        option.checked = False
        option.isChecked = lambda option=option: option.checked
    app = make_app(
        dotnet_project_input=DummyInput("Tool.csproj"),
        dotnet_output_input=DummyInput("publish"),
        dotnet_icon_input=DummyInput(),
        dotnet_name_input=DummyInput("Tool"),
        dotnet_runtime_combo=runtime,
        dotnet_self_contained=options[0],
        dotnet_single_file=options[1],
        dotnet_trim=options[2],
    )

    controller = StateController(app)
    controller.save_csharp_state()

    assert app.csharp_state_data["self_contained"] is False
    assert app.csharp_state_data["single_file"] is False
    assert app.csharp_state_data["trim"] is False


def test_legacy_state_is_partitioned_and_removed(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    controller = StateController(make_app(validator=DummyValidator()))
    legacy_path = controller.legacy_state_file_path()
    with open(legacy_path, "w", encoding="utf-8") as state_file:
        json.dump({
            "last_script_path": "main.py",
            "dotnet_publish": {"project_path": "Tool.csproj"},
            "tooltips_enabled": False,
            "build_mode": "dotnet",
        }, state_file)

    controller._migrate_legacy_state()

    assert not os.path.exists(legacy_path)
    assert controller._read(controller.python_state_file_path())["last_script_path"] == "main.py"
    assert controller._read(controller.csharp_state_file_path())["project_path"] == "Tool.csproj"
    assert controller._read(controller.preferences_file_path())["build_mode"] == "dotnet"


def test_save_state_writes_environment_sync_profiles(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    env_sync_profiles = [
        {
            "version": "3.13",
            "executable": "C:/Python313/python.exe",
            "packages": {"numpy": {"name": "numpy", "version": "2.3.0"}},
            "error": "",
        }
    ]
    app = make_app(
        environment_sync_controller=DummyEnvironmentSyncController(env_sync_profiles)
    )

    controller = StateController(app)
    controller.save_state()

    with open(controller.python_state_file_path(), "r", encoding="utf-8") as state_file:
        data = json.load(state_file)

    assert data["env_sync_profiles"] == env_sync_profiles


def test_save_state_writes_guided_python_steps(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    app = make_app(_completed_python_steps={0, 1, 2, 3, 4})

    controller = StateController(app)
    controller.save_state()

    data = controller._read(controller.python_state_file_path())
    assert data["guided_python_steps"] == [0, 1, 2, 3, 4]


def test_save_state_preserves_remembered_non_desktop_output_when_output_is_desktop(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    remembered_output = tmp_path / "dist"
    desktop = os.path.normpath(os.path.join(os.path.expanduser("~"), "Desktop"))
    app = make_app(
        output_path=desktop,
        last_non_desktop_output_dir=str(remembered_output),
    )

    controller = StateController(app)
    controller.save_state()

    with open(controller._state_file_path(), "r", encoding="utf-8") as state_file:
        data = json.load(state_file)

    assert data["last_output_folder"] == desktop
    assert data["last_non_desktop_output_folder"] == os.path.normpath(str(remembered_output))


def test_load_state_restores_last_non_desktop_output_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    remembered_output = tmp_path / "dist"
    remembered_output.mkdir()
    desktop = os.path.normpath(os.path.join(os.path.expanduser("~"), "Desktop"))
    app = make_app(
        tooltips_checkbox=DummyCheckbox(),
        close_after_build=DummyCheckbox(),
        minimize_after_build=DummyCheckbox(),
        open_output_dir_after_build=DummyCheckbox(),
        script_path_input=DummyInput(),
        icon_path_input=DummyInput(),
        output_path_input=DummyInput(),
        exe_name_input=DummyInput(),
        python_entry_input=DummyInput(),
        validator=DummyValidator(),
    )
    controller = StateController(app)

    state_path = controller.python_state_file_path()
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as state_file:
        json.dump(
            {
                "last_output_folder": desktop,
                "last_non_desktop_output_folder": str(remembered_output),
            },
            state_file,
        )

    controller.load_state()

    expected = os.path.normpath(str(remembered_output))
    assert app.output_path == desktop
    assert app.output_path_input.value == desktop
    assert app.last_non_desktop_output_dir == expected
    assert app.last_output_dir == expected


def test_save_state_persists_open_output_directory_toggle(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    app = make_app(open_output_dir_after_build_enabled=True)

    controller = StateController(app)
    controller.save_state()

    with open(controller.preferences_file_path(), "r", encoding="utf-8") as state_file:
        data = json.load(state_file)

    assert data["open_output_dir_after_build_enabled"] is True


def test_save_state_persists_mass_datetime_sentinels(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    sentinels = [
        MASS_DATETIME_BUILD_SENTINEL,
        ISO_MASS_DATETIME_BUILD_SENTINEL,
        UK_MASS_DATETIME_BUILD_SENTINEL,
        USA_MASS_DATETIME_BUILD_SENTINEL,
    ]

    for sentinel in sentinels:
        app = make_app(
            append_datetime=False,
            datetime_format=sentinel,
        )

        controller = StateController(app)
        controller.save_state()

        with open(controller._state_file_path(), "r", encoding="utf-8") as state_file:
            data = json.load(state_file)

        assert data["append_datetime"] is False
        assert data["datetime_format"] == sentinel


def test_load_state_restores_open_output_directory_toggle(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    app = make_app(
        tooltips_checkbox=DummyCheckbox(),
        close_after_build=DummyCheckbox(),
        minimize_after_build=DummyCheckbox(),
        open_output_dir_after_build=DummyCheckbox(),
        script_path_input=DummyInput(),
        icon_path_input=DummyInput(),
        output_path_input=DummyInput(),
        exe_name_input=DummyInput(),
        python_entry_input=DummyInput(),
        validator=DummyValidator(),
    )
    controller = StateController(app)

    state_path = controller.preferences_file_path()
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as state_file:
        json.dump({"open_output_dir_after_build_enabled": True}, state_file)

    controller.load_state()

    assert app.open_output_dir_after_build_enabled is True
    assert app.open_output_dir_after_build.checked is True


def test_load_state_restores_environment_sync_profiles(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    env_sync_profiles = [
        {
            "version": "3.13",
            "executable": "C:/Python313/python.exe",
            "packages": {"numpy": {"name": "numpy", "version": "2.3.0"}},
            "error": "",
        }
    ]
    env_sync_controller = DummyEnvironmentSyncController()
    app = make_app(
        tooltips_checkbox=DummyCheckbox(),
        close_after_build=DummyCheckbox(),
        minimize_after_build=DummyCheckbox(),
        open_output_dir_after_build=DummyCheckbox(),
        script_path_input=DummyInput(),
        icon_path_input=DummyInput(),
        output_path_input=DummyInput(),
        exe_name_input=DummyInput(),
        python_entry_input=DummyInput(),
        validator=DummyValidator(),
        environment_sync_controller=env_sync_controller,
    )
    controller = StateController(app)

    state_path = controller._state_file_path()
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as state_file:
        json.dump({"env_sync_profiles": env_sync_profiles}, state_file)

    controller.load_state()

    assert env_sync_controller.loaded_profiles == env_sync_profiles
    assert env_sync_controller.update_ui is True


def test_load_state_restores_no_datetime_appended_selection(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    app = make_app(
        tooltips_checkbox=DummyCheckbox(),
        close_after_build=DummyCheckbox(),
        minimize_after_build=DummyCheckbox(),
        open_output_dir_after_build=DummyCheckbox(),
        script_path_input=DummyInput(),
        icon_path_input=DummyInput(),
        output_path_input=DummyInput(),
        exe_name_input=DummyInput(),
        python_entry_input=DummyInput(),
        validator=DummyValidator(),
        date_time_dropdown=DummyDropdown(
            [
                {"text": "Append Date/Time", "data": None, "enabled": False},
                {"text": "──────────", "data": None, "enabled": False},
                {"text": "No Date Time Appended", "data": None, "enabled": True},
                {"text": "ISO | YYYY-MM-DD", "data": "%Y-%m-%d", "enabled": True},
            ]
        ),
    )
    controller = StateController(app)

    state_path = controller._state_file_path()
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as state_file:
        json.dump({"append_datetime": False, "datetime_format": ""}, state_file)

    controller.load_state()

    assert app.append_datetime is False
    assert app.date_time_dropdown.currentText() == "No Date Time Appended"


def test_load_state_restores_saved_datetime_format_selection(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    app = make_app(
        tooltips_checkbox=DummyCheckbox(),
        close_after_build=DummyCheckbox(),
        minimize_after_build=DummyCheckbox(),
        open_output_dir_after_build=DummyCheckbox(),
        script_path_input=DummyInput(),
        icon_path_input=DummyInput(),
        output_path_input=DummyInput(),
        exe_name_input=DummyInput(),
        python_entry_input=DummyInput(),
        validator=DummyValidator(),
        date_time_dropdown=DummyDropdown(
            [
                {"text": "Append Date/Time", "data": None, "enabled": False},
                {"text": "──────────", "data": None, "enabled": False},
                {"text": "No Date Time Appended", "data": None, "enabled": True},
                {"text": "ISO | YYYY-MM-DD", "data": "%Y-%m-%d", "enabled": True},
            ]
        ),
    )
    controller = StateController(app)

    state_path = controller._state_file_path()
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as state_file:
        json.dump({"append_datetime": True, "datetime_format": "%Y-%m-%d"}, state_file)

    controller.load_state()

    assert app.append_datetime is True
    assert app.date_time_dropdown.currentText() == "ISO | YYYY-MM-DD"


def test_load_state_restores_saved_mass_datetime_sentinel_selection(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    options = [
        {"text": "No Date Time Appended", "data": None, "enabled": True},
        {
            "text": "Build All Date/Time Outputs",
            "data": MASS_DATETIME_BUILD_SENTINEL,
            "enabled": True,
        },
        {
            "text": "Build All ISO Date/Time Outputs",
            "data": ISO_MASS_DATETIME_BUILD_SENTINEL,
            "enabled": True,
        },
        {
            "text": "Build All UK Date/Time Outputs",
            "data": UK_MASS_DATETIME_BUILD_SENTINEL,
            "enabled": True,
        },
        {
            "text": "Build All USA Date/Time Outputs",
            "data": USA_MASS_DATETIME_BUILD_SENTINEL,
            "enabled": True,
        },
    ]
    expected_labels = {
        MASS_DATETIME_BUILD_SENTINEL: "Build All Date/Time Outputs",
        ISO_MASS_DATETIME_BUILD_SENTINEL: "Build All ISO Date/Time Outputs",
        UK_MASS_DATETIME_BUILD_SENTINEL: "Build All UK Date/Time Outputs",
        USA_MASS_DATETIME_BUILD_SENTINEL: "Build All USA Date/Time Outputs",
    }

    for sentinel, label in expected_labels.items():
        app = make_app(
            tooltips_checkbox=DummyCheckbox(),
            close_after_build=DummyCheckbox(),
            minimize_after_build=DummyCheckbox(),
            open_output_dir_after_build=DummyCheckbox(),
            script_path_input=DummyInput(),
            icon_path_input=DummyInput(),
            output_path_input=DummyInput(),
            exe_name_input=DummyInput(),
            python_entry_input=DummyInput(),
            validator=DummyValidator(),
            date_time_dropdown=DummyDropdown(options),
        )
        controller = StateController(app)

        state_path = controller._state_file_path()
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, "w", encoding="utf-8") as state_file:
            json.dump(
                {"append_datetime": False, "datetime_format": sentinel},
                state_file,
            )

        controller.load_state()

        assert app.append_datetime is False
        assert app.datetime_format == sentinel
        assert app.date_time_dropdown.currentText() == label


def test_csharp_datetime_selection_restores_independently_and_defaults_to_no_date(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    options = [
        {"text": "Append Date/Time", "data": None, "enabled": False},
        {"text": "No Date Time Appended", "data": None},
        {"text": "Build All USA Date/Time Outputs", "data": USA_MASS_DATETIME_BUILD_SENTINEL},
    ]
    app = make_app(
        validator=DummyValidator(),
        dotnet_project_input=DummyInput(),
        dotnet_output_input=DummyInput(),
        dotnet_icon_input=DummyInput(),
        dotnet_name_input=DummyInput(),
        dotnet_runtime_combo=DummyDropdown([{"text": "Windows x64", "data": "win-x64"}]),
        dotnet_date_time_dropdown=DummyDropdown(options),
        dotnet_self_contained=DummyCheckbox(),
        dotnet_single_file=DummyCheckbox(),
        dotnet_trim=DummyCheckbox(),
    )
    controller = StateController(app)
    with open(controller.python_state_file_path(), "w", encoding="utf-8") as handle:
        json.dump({"datetime_format": "%Y-%m-%d"}, handle)
    with open(controller.csharp_state_file_path(), "w", encoding="utf-8") as handle:
        json.dump({"datetime_format": USA_MASS_DATETIME_BUILD_SENTINEL}, handle)

    controller.load_state()
    assert app.datetime_format == "%Y-%m-%d"
    assert app.dotnet_date_time_dropdown.currentData() == USA_MASS_DATETIME_BUILD_SENTINEL

    with open(controller.csharp_state_file_path(), "w", encoding="utf-8") as handle:
        json.dump({}, handle)
    controller.load_state()
    assert app.dotnet_date_time_dropdown.currentText() == "No Date Time Appended"
