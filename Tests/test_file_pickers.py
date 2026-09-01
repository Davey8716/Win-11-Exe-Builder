import os
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from exe_builder.controllers import file_pickers
from exe_builder.controllers.file_pickers import FilePickerController, ScriptPickerPopup
from exe_builder.ui.styles import Colors


def _qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_script_picker_popup_styles_native_title_bar(monkeypatch, tmp_path):
    _qapp()
    style_calls = []

    def record_native_title_style(dialog, caption=None, text=None, border=None):
        style_calls.append(
            {
                "dialog": dialog,
                "caption": caption,
                "text": text,
                "border": border,
            }
        )

    monkeypatch.setattr(
        file_pickers,
        "apply_native_title_bar_style",
        record_native_title_style,
    )

    parent = QWidget()
    parent.setGeometry(10, 20, 100, 80)
    selected_paths = []

    popup = ScriptPickerPopup(
        parent=parent,
        folder_path=str(tmp_path),
        py_files=["app.py", "main.py"],
        callback=selected_paths.append,
    )

    try:
        flags = popup.windowFlags()

        assert popup.windowTitle() == "Select Entry Script"
        assert popup.width() == 300
        assert popup.height() == 200
        assert popup.dropdown.count() == 2
        assert bool(flags & Qt.WindowMinimizeButtonHint)
        assert bool(flags & Qt.WindowCloseButtonHint)
        assert not bool(flags & Qt.WindowContextHelpButtonHint)
        assert style_calls == [
            {
                "dialog": popup,
                "caption": Colors.PANEL_BG,
                "text": None,
                "border": Colors.PANEL_BG,
            }
        ]
    finally:
        popup.close()
        parent.close()


def test_script_picker_popup_confirm_returns_selected_script(monkeypatch, tmp_path):
    _qapp()
    monkeypatch.setattr(file_pickers, "apply_native_title_bar_style", lambda *args, **kwargs: None)

    parent = QWidget()
    selected_paths = []
    popup = ScriptPickerPopup(
        parent=parent,
        folder_path=str(tmp_path),
        py_files=["app.py", "main.py"],
        callback=selected_paths.append,
    )

    try:
        popup.dropdown.setCurrentText("main.py")
        popup.confirm()

        assert selected_paths == [os.path.normpath(str(tmp_path / "main.py"))]
    finally:
        popup.close()
        parent.close()


class DummyPathInput:
    def __init__(self):
        self.value = ""

    def set_display_path(self, value):
        self.value = value


class DummyStateController:
    def __init__(self):
        self.saved = False

    def save_state(self):
        self.saved = True


class DummyValidator:
    def __init__(self):
        self.status_updated = False
        self.ui_updated = False

    def validation_status_message(self):
        self.status_updated = True

    def update_ui_state(self):
        self.ui_updated = True


class DummyRecentController:
    def __init__(self):
        self.icons = []
        self.populated_icons = False

    def add_recent_icon(self, path):
        self.icons.append(path)

    def populate_recent_icons_dropdown(self):
        self.populated_icons = True


def make_output_picker_app(**overrides):
    app = SimpleNamespace(
        output_path="",
        last_output_dir="",
        last_non_desktop_output_dir="",
        output_path_input=DummyPathInput(),
        output_btn=None,
        exe_name="",
        entry_script="",
        script_path="",
        state_ctrl=DummyStateController(),
        validator=DummyValidator(),
    )

    for name, value in overrides.items():
        setattr(app, name, value)

    return app


def make_icon_picker_app(**overrides):
    app = SimpleNamespace(
        icon_path="",
        icon_user_cleared=True,
        icon_path_input=DummyPathInput(),
        icon_btn=None,
        recent_controller=DummyRecentController(),
        state_ctrl=DummyStateController(),
        validator=DummyValidator(),
    )

    for name, value in overrides.items():
        setattr(app, name, value)

    return app


def test_apply_selected_icon_clears_user_cleared_flag(monkeypatch, tmp_path):
    icon = tmp_path / "app.ico"
    icon.write_text("", encoding="utf-8")
    app = make_icon_picker_app()
    controller = FilePickerController(app)

    monkeypatch.setattr(file_pickers, "flash_add_highlight", lambda *args, **kwargs: None)

    controller._apply_selected_icon(str(icon))

    expected = os.path.normpath(str(icon))
    assert app.icon_path == expected
    assert app.icon_user_cleared is False
    assert app.icon_path_input.value == expected
    assert app.recent_controller.icons == [expected]
    assert app.recent_controller.populated_icons is True
    assert app.state_ctrl.saved is True
    assert app.validator.status_updated is True
    assert app.validator.ui_updated is True


def test_select_icon_clears_user_cleared_flag(monkeypatch, tmp_path):
    icon = tmp_path / "selected.ico"
    icon.write_text("", encoding="utf-8")
    app = make_icon_picker_app()
    controller = FilePickerController(app)

    monkeypatch.setattr(file_pickers, "flash_add_highlight", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        file_pickers.QFileDialog,
        "getOpenFileName",
        lambda parent, title, start_dir, file_filter: (str(icon), ""),
    )

    controller.select_icon()

    expected = os.path.normpath(str(icon))
    assert app.icon_path == expected
    assert app.icon_user_cleared is False
    assert app.icon_path_input.value == expected


def test_output_picker_uses_remembered_non_desktop_start_dir(monkeypatch, tmp_path):
    remembered_dir = tmp_path / "dist"
    remembered_dir.mkdir()
    app = make_output_picker_app(last_non_desktop_output_dir=str(remembered_dir))
    controller = FilePickerController(app)
    start_dirs = []

    def record_get_existing_directory(parent, title, start_dir):
        start_dirs.append(start_dir)
        return ""

    monkeypatch.setattr(file_pickers.QFileDialog, "getExistingDirectory", record_get_existing_directory)

    controller.select_output_folder()

    assert start_dirs == [os.path.normpath(str(remembered_dir))]


def test_selecting_desktop_output_does_not_overwrite_remembered_non_desktop(monkeypatch, tmp_path):
    remembered_dir = tmp_path / "dist"
    remembered_dir.mkdir()
    app = make_output_picker_app(
        last_output_dir=str(remembered_dir),
        last_non_desktop_output_dir=str(remembered_dir),
    )
    controller = FilePickerController(app)
    desktop = controller._desktop_path()

    monkeypatch.setattr(file_pickers, "flash_add_highlight", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        file_pickers.QFileDialog,
        "getExistingDirectory",
        lambda parent, title, start_dir: desktop,
    )

    controller.select_output_folder()

    assert app.output_path == desktop
    assert app.output_path_input.value == desktop
    assert app.last_output_dir == os.path.normpath(str(remembered_dir))
    assert app.last_non_desktop_output_dir == os.path.normpath(str(remembered_dir))
    assert app.state_ctrl.saved is True
    assert app.validator.status_updated is True
    assert app.validator.ui_updated is True


def test_selecting_non_desktop_output_updates_remembered_location(monkeypatch, tmp_path):
    output_dir = tmp_path / "release"
    output_dir.mkdir()
    app = make_output_picker_app()
    controller = FilePickerController(app)

    monkeypatch.setattr(file_pickers, "flash_add_highlight", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        file_pickers.QFileDialog,
        "getExistingDirectory",
        lambda parent, title, start_dir: str(output_dir),
    )

    controller.select_output_folder()

    expected = os.path.normpath(str(output_dir))
    assert app.output_path == expected
    assert app.last_output_dir == expected
    assert app.last_non_desktop_output_dir == expected
