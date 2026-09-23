import os
from types import SimpleNamespace

from exe_builder.controllers import validation_controller
from exe_builder.ui.styles import (
    Colors,
    COMBO_BOX_LINE_EDIT_STYLE,
    COMBO_BOX_STYLE,
    ENV_SYNC_BUTTON_STYLE,
    ENV_SYNC_STATUS_LINE_STYLE,
    REFRESH_BUTTON_TEXT,
    SCRIPT_PICKER_DROPDOWN_STYLE,
    build_disabled_button,
    build_disabled_checkbox,
    build_disabled_checkbox_without_checkmark,
    build_disabled_line_edit_style,
    env_sync_disabled_status_line_style,
    line_edit_style,
    qcolor_name,
)
from exe_builder.controllers.validation_controller import ValidationController


def test_combo_box_disabled_style_greys_drop_down_and_arrow():
    disabled_bg = qcolor_name(Colors.COMBO_DISABLED_BG)
    disabled_text = qcolor_name(Colors.COMBO_DISABLED_TEXT)

    assert "QComboBox {" in COMBO_BOX_STYLE
    assert "border-radius: 4px;" in COMBO_BOX_STYLE
    assert "QComboBox::drop-down:disabled" in COMBO_BOX_STYLE
    assert "QComboBox::down-arrow:disabled" in COMBO_BOX_STYLE
    assert "QComboBox:disabled" in COMBO_BOX_STYLE
    assert f"background-color: {disabled_bg};" in COMBO_BOX_STYLE
    assert f"color: {disabled_text};" in COMBO_BOX_STYLE
    assert "border-radius: 4px;" in COMBO_BOX_LINE_EDIT_STYLE


def test_script_picker_dropdown_matches_main_combo_colors():
    title_bg = qcolor_name(Colors.TITLE_BG)
    text_light = qcolor_name(Colors.TEXT_LIGHT)
    white = qcolor_name(Colors.WHITE)

    assert "QComboBox {" in SCRIPT_PICKER_DROPDOWN_STYLE
    assert f"background-color: {title_bg};" in SCRIPT_PICKER_DROPDOWN_STYLE
    assert f"color: {text_light};" in SCRIPT_PICKER_DROPDOWN_STYLE
    assert "QComboBox::drop-down" in SCRIPT_PICKER_DROPDOWN_STYLE
    assert "QComboBox::down-arrow" in SCRIPT_PICKER_DROPDOWN_STYLE
    assert f"background-color: {white};" in SCRIPT_PICKER_DROPDOWN_STYLE


def test_path_line_edit_styles_have_rounded_borders():
    assert "border-radius: 4px;" in line_edit_style(Colors.SUCCESS)
    assert "border-radius: 4px;" in build_disabled_line_edit_style()


def test_environment_sync_status_line_uses_panel_background_when_read_only():
    panel_bg = qcolor_name(Colors.PANEL_BG)

    assert ENV_SYNC_STATUS_LINE_STYLE.count(f"background-color: {panel_bg};") == 2


class DummyCheckbox:
    def __init__(self, checked=False):
        self._checked = checked
        self.enabled = None
        self.text = ""
        self.stylesheet = ""

    def isChecked(self):
        return self._checked

    def setChecked(self, value):
        self._checked = value

    def setEnabled(self, value):
        self.enabled = value

    def setStyleSheet(self, value):
        self.stylesheet = value

    def setText(self, value):
        self.text = value


class DummyButton:
    def __init__(self):
        self.enabled = None
        self.text = ""
        self.stylesheet = ""

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


class DummyInput:
    def __init__(self, value=""):
        self._value = value
        self.read_only = False
        self.stylesheet = ""

    def text(self):
        return self._value

    def setText(self, value):
        self._value = value

    def setReadOnly(self, value):
        self.read_only = value

    def setStyleSheet(self, value):
        self.stylesheet = value


class DummyDropdown:
    def __init__(self):
        self.enabled = None

    def setEnabled(self, value):
        self.enabled = value


class DummyLabel:
    def __init__(self):
        self.text = ""
        self.stylesheet = ""
        self.alignment = None
        self.size = None

    def setFixedSize(self, width, height):
        self.size = (width, height)

    def setText(self, value):
        self.text = value

    def setAlignment(self, value):
        self.alignment = value

    def setStyleSheet(self, value):
        self.stylesheet = value


class DummyFrame:
    def __init__(self):
        self.stylesheet = ""

    def setStyleSheet(self, value):
        self.stylesheet = value


def make_app(tmp_path, exe_name="", script_name="main.py", entry_script=None):
    script = tmp_path / script_name
    script.write_text("print('hello')\n", encoding="utf-8")

    python = tmp_path / "python.exe"
    python.write_text("", encoding="utf-8")

    output_dir = tmp_path / "dist"
    output_dir.mkdir()

    script_path = str(script) if entry_script is None else entry_script

    return SimpleNamespace(
        building=False,
        build_error=None,
        _was_build_ready=False,
        _status_lock=False,
        state_data={
            "recent_scripts": [],
            "recent_icons": [],
            "recent_interpreters": [],
        },
        entry_script=script_path,
        script_path=script_path,
        python_interpreter_path=str(python),
        icon_path="",
        build_options_btn=DummyButton(),
        dotnet_build_options_btn=DummyButton(),
        tooltips_checkbox=DummyCheckbox(),
        open_app_data_btn=DummyButton(),
        open_output_dir_after_build=DummyCheckbox(),
        minimize_after_build=DummyCheckbox(),
        close_after_build=DummyCheckbox(),
        env_sync_scan_btn=DummyButton(),
        env_sync_match_btn=DummyButton(),
        env_sync_log_input=DummyInput("Environment sync ready."),
        env_sync_status_labels=[DummyLabel(), DummyLabel(), DummyLabel()],
        env_sync_row_labels=[DummyLabel(), DummyLabel(), DummyLabel()],
        environment_sync_controller=SimpleNamespace(
            is_running=False,
            last_plan=SimpleNamespace(total_actions=1),
        ),
        open_python_site_btn=DummyButton(),
        interpreter_btn=DummyButton(),
        interpreter_refresh_btn=DummyButton(),
        icon_btn=DummyButton(),
        icon_clear_btn=DummyButton(),
        ico_convert_btn=DummyButton(),
        folder_btn=DummyButton(),
        script_clear_btn=DummyButton(),
        appened_py_version=DummyButton(),
        output_btn=DummyButton(),
        python_open_output_btn=DummyButton(),
        output_refresh_btn=DummyButton(),
        refresh_btn=DummyButton(),
        delete_recent_icons=DummyButton(),
        delete_recent_folder=DummyButton(),
        delete_all_icons=DummyButton(),
        delete_all_folders=DummyButton(),
        python_delete_all_interpreter=DummyButton(),
        python_delete_interpreter=DummyButton(),
        select_interpreter=DummyDropdown(),
        select_recent_icons=DummyDropdown(),
        recent_folder_dropdown=DummyDropdown(),
        date_time_dropdown=DummyDropdown(),
        python_entry_input=DummyInput(str(python)),
        script_path_input=DummyInput(script_path),
        output_path_input=DummyInput(str(output_dir)),
        icon_path_input=DummyInput(""),
        exe_name_input=DummyInput(exe_name),
        status_label=DummyLabel(),
        title_frame=DummyFrame(),
        env_sync_title_frame=DummyFrame(),
        apps_title_frame=DummyFrame(),
        icons_title_frame=DummyFrame(),
        python_title_frame=DummyFrame(),
        output_title_frame=DummyFrame(),
        build_controller=SimpleNamespace(has_python_output=lambda: False),
    )


def test_python_open_output_button_matches_dotnet_availability_styling(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path)
    app.build_controller = SimpleNamespace(has_python_output=lambda: True)

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.python_open_output_btn.enabled is True
    assert qcolor_name(Colors.TITLE_BG) in app.python_open_output_btn.stylesheet

    app.building = True
    controller.update_ui_state()

    assert app.python_open_output_btn.enabled is False
    assert qcolor_name(Colors.BUILD_DISABLED_BG) in app.python_open_output_btn.stylesheet


def test_exe_refresh_enabled_when_name_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="")

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.refresh_btn.enabled is True
    assert app.refresh_btn.text == REFRESH_BUTTON_TEXT


def test_exe_refresh_disabled_when_name_matches_script_default(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="main")

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.refresh_btn.enabled is False
    assert app.refresh_btn.text == ""
    assert app.refresh_btn.stylesheet == build_disabled_button()


def test_python_utility_icons_restore_after_build_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="custom-name")
    app.icon_path = str(tmp_path / "app.ico")
    app.state_data.update(
        recent_scripts=[app.script_path],
        recent_icons=[app.icon_path],
        recent_interpreters=[app.python_interpreter_path],
    )
    controller = ValidationController(app)
    buttons = (
        app.delete_recent_icons,
        app.delete_recent_folder,
        app.delete_all_icons,
        app.delete_all_folders,
        app.python_delete_interpreter,
        app.python_delete_all_interpreter,
        app.interpreter_refresh_btn,
        app.icon_clear_btn,
        app.script_clear_btn,
        app.output_refresh_btn,
        app.refresh_btn,
    )

    controller.update_ui_state()
    assert all(not button.icon.isNull() for button in buttons)
    assert {button.size for button in buttons} == {(35, 35)}

    app.building = True
    controller.update_ui_state()
    assert all(button.icon.isNull() for button in buttons)

    app.building = False
    controller.update_ui_state()
    assert all(not button.icon.isNull() for button in buttons)


def test_python_empty_selection_clear_and_delete_controls_are_greyed(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="custom-name")
    app.entry_script = None
    app.script_path = ""
    app.script_path_input.setText("")
    app.python_interpreter_path = ""
    app.python_entry_input.setText("")
    app.icon_path = ""
    app.icon_path_input.setText("")

    ValidationController(app).update_ui_state()

    for button in (
        app.delete_recent_icons,
        app.delete_recent_folder,
        app.python_delete_interpreter,
        app.icon_clear_btn,
        app.script_clear_btn,
        app.interpreter_refresh_btn,
    ):
        assert button.enabled is False
        assert button.text == ""
        assert qcolor_name(Colors.BUILD_DISABLED_BG) in button.stylesheet
        assert button.icon.isNull()


def test_python_populated_selection_clear_and_delete_controls_restore(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="custom-name")
    icon = tmp_path / "tool.ico"
    icon.write_text("ico", encoding="utf-8")
    app.icon_path = str(icon)
    app.icon_path_input.setText(str(icon))

    ValidationController(app).update_ui_state()

    for button in (
        app.delete_recent_icons,
        app.delete_recent_folder,
        app.python_delete_interpreter,
        app.icon_clear_btn,
        app.script_clear_btn,
        app.interpreter_refresh_btn,
    ):
        assert button.enabled is True
        assert qcolor_name(Colors.TITLE_BG) in button.stylesheet
        assert not button.icon.isNull()


def test_environment_sync_uses_disabled_build_styling(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="main")
    app.building = True

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.env_sync_scan_btn.enabled is False
    assert app.env_sync_match_btn.enabled is False
    assert app.env_sync_scan_btn.stylesheet == build_disabled_button()
    assert app.env_sync_match_btn.stylesheet == build_disabled_button()
    assert app.env_sync_log_input.stylesheet == env_sync_disabled_status_line_style()

    disabled_text = qcolor_name(Colors.BUILD_DISABLED_TEXT)
    for label in [
        *app.env_sync_status_labels,
        *app.env_sync_row_labels,
    ]:
        assert disabled_text in label.stylesheet


def test_python_ui_refresh_updates_build_mode_selectors(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="main")
    app.build_mode = "python"
    refreshes = []
    app._apply_build_mode_button_state = refreshes.append

    controller = ValidationController(app)
    app.building = True
    controller.update_ui_state()
    app.building = False
    controller.update_ui_state()

    assert refreshes == ["python", "python"]


def test_environment_sync_restores_normal_styling_when_not_building(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="main")

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.env_sync_scan_btn.enabled is True
    assert app.env_sync_match_btn.enabled is True
    assert app.env_sync_scan_btn.stylesheet == ENV_SYNC_BUTTON_STYLE
    assert app.env_sync_match_btn.stylesheet == ENV_SYNC_BUTTON_STYLE
    assert app.env_sync_log_input.stylesheet == ENV_SYNC_STATUS_LINE_STYLE

    normal_text = qcolor_name(Colors.TEXT_LIGHT)
    for label in [
        *app.env_sync_status_labels,
        *app.env_sync_row_labels,
    ]:
        assert normal_text in label.stylesheet


def test_open_app_data_enabled_when_not_building(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="main")

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.open_app_data_btn.enabled is True


def test_open_app_data_disabled_while_building(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="main")
    app.building = True

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.open_app_data_btn.enabled is False
    assert app.open_app_data_btn.stylesheet == build_disabled_button()


def test_build_options_button_is_disabled_while_building(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="main")
    app.building = True

    ValidationController(app).update_ui_state()

    assert app.build_options_btn.enabled is False
    assert app.build_options_btn.stylesheet == build_disabled_button()
    assert app.dotnet_build_options_btn.enabled is False
    assert app.dotnet_build_options_btn.stylesheet == build_disabled_button()


def test_dotnet_build_options_button_restores_after_publish_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="main")
    controller = ValidationController(app)

    app.building = True
    controller.update_ui_state()
    app.building = False
    controller.update_ui_state()

    assert app.dotnet_build_options_btn.enabled is True
    assert app.dotnet_build_options_btn.stylesheet != build_disabled_button()


def test_open_output_directory_disabled_for_desktop_output(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="main")
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    app.output_path_input.setText(desktop)
    app.open_output_dir_after_build.setChecked(True)

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.open_output_dir_after_build.enabled is False
    assert app.open_output_dir_after_build.isChecked() is True
    assert (
        app.open_output_dir_after_build.stylesheet
        == build_disabled_checkbox_without_checkmark()
    )
    assert "image: none;" in app.open_output_dir_after_build.stylesheet


def test_open_output_directory_tick_stays_hidden_for_desktop_while_building(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="main")
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    app.output_path_input.setText(desktop)
    app.open_output_dir_after_build.setChecked(True)
    app.building = True

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.open_output_dir_after_build.enabled is False
    assert app.open_output_dir_after_build.isChecked() is True
    assert (
        app.open_output_dir_after_build.stylesheet
        == build_disabled_checkbox_without_checkmark()
    )
    assert "image: none;" in app.open_output_dir_after_build.stylesheet


def test_open_output_directory_enabled_for_non_desktop_output(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="main")

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.open_output_dir_after_build.enabled is True
    assert app.open_output_dir_after_build.stylesheet == ""


def test_output_refresh_disabled_for_desktop_output_uses_build_style(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="main")
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    app.output_path_input.setText(desktop)

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.output_refresh_btn.enabled is False
    assert app.output_refresh_btn.text == ""
    assert app.output_refresh_btn.stylesheet == build_disabled_button()


def test_output_refresh_disables_for_case_insensitive_desktop_path(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    monkeypatch.setattr(
        validation_controller.os.path,
        "expanduser",
        lambda _path: str(tmp_path),
    )
    app = make_app(tmp_path, exe_name="main")
    desktop = tmp_path / "Desktop"
    app.output_path_input.setText(str(desktop).upper())

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.output_refresh_btn.enabled is False
    assert app.output_refresh_btn.stylesheet == build_disabled_button()
    assert app.output_refresh_btn.icon.isNull()


def test_output_refresh_enabled_for_non_desktop_output(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="main")

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.output_refresh_btn.enabled is True
    assert app.output_refresh_btn.text == REFRESH_BUTTON_TEXT


def test_exe_refresh_enabled_when_name_differs_from_script_default(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    app = make_app(tmp_path, exe_name="CustomApp", script_name="launcher.py")

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.refresh_btn.enabled is True
    assert app.refresh_btn.text == REFRESH_BUTTON_TEXT


def test_exe_refresh_disabled_without_valid_script(monkeypatch, tmp_path):
    monkeypatch.setattr(validation_controller, "QCheckBox", DummyCheckbox)
    missing_script = os.path.join(str(tmp_path), "missing.py")
    app = make_app(tmp_path, exe_name="", entry_script=missing_script)
    app.script_path_input.setText(missing_script)

    controller = ValidationController(app)
    controller.update_ui_state()

    assert app.refresh_btn.enabled is False
    assert app.refresh_btn.text == ""
    assert app.refresh_btn.stylesheet == build_disabled_button()
