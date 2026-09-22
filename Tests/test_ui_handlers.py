from types import SimpleNamespace
import os
import sys

from exe_builder.controllers import ui_handlers
from exe_builder.build.datetime_build_options import (
    ISO_MASS_DATETIME_BUILD_SENTINEL,
    MASS_DATETIME_BUILD_SENTINEL,
    NO_DATETIME_LABEL,
    UK_MASS_DATETIME_BUILD_SENTINEL,
    USA_MASS_DATETIME_BUILD_SENTINEL,
)
from exe_builder.controllers.ui_handlers import UIHandlers


class DummyDropdown:
    def __init__(self, data=MASS_DATETIME_BUILD_SENTINEL):
        self.data = data

    def currentData(self):
        return self.data


class DummyIndexedDropdown:
    def __init__(self, options, current_index):
        self.options = options
        self.current_index = current_index
        self.blocked = False

    def currentData(self):
        return self.options[self.current_index]["data"]

    def currentIndex(self):
        return self.current_index

    def count(self):
        return len(self.options)

    def itemText(self, index):
        return self.options[index]["text"]

    def blockSignals(self, value):
        self.blocked = value

    def setCurrentIndex(self, index):
        self.current_index = index


class DummyIconDropdown:
    def __init__(self):
        self.current_index = 0
        self.blocked = False

    def blockSignals(self, value):
        self.blocked = value

    def setCurrentIndex(self, index):
        self.current_index = index


class DummyStateController:
    def __init__(self, state_file=None):
        self.saved = False
        self.state_file = state_file

    def save_state(self):
        self.saved = True

    def _state_file_path(self):
        return str(self.state_file)


class DummyValidator:
    def __init__(self):
        self.status_updated = False
        self.ui_updated = False

    def validation_status_message(self):
        self.status_updated = True

    def update_ui_state(self):
        self.ui_updated = True


class DummyPathInput:
    def __init__(self):
        self.value = ""
        self.deselected = False
        self.cursor_position = None

    def set_display_path(self, value):
        self.value = value

    def clear(self):
        self.value = ""

    def deselect(self):
        self.deselected = True

    def setCursorPosition(self, position):
        self.cursor_position = position


def test_mass_datetime_selection_saves_sentinel_and_keeps_restore_state():
    state_ctrl = DummyStateController()
    validator = DummyValidator()
    app = SimpleNamespace(
        date_time_dropdown=DummyDropdown(),
        append_datetime=True,
        datetime_format="%Y-%m-%d",
        state_ctrl=state_ctrl,
        validator=validator,
    )

    UIHandlers(app).on_datetime_format_changed(0)

    assert app.mass_datetime_build_selected is True
    assert app.append_datetime is False
    assert app.datetime_format == MASS_DATETIME_BUILD_SENTINEL
    assert app._mass_datetime_restore_state == {
        "append_datetime": True,
        "datetime_format": "%Y-%m-%d",
    }
    assert state_ctrl.saved is True
    assert validator.status_updated is True
    assert validator.ui_updated is True


def test_iso_mass_datetime_selection_saves_sentinel_and_keeps_restore_state():
    state_ctrl = DummyStateController()
    validator = DummyValidator()
    app = SimpleNamespace(
        date_time_dropdown=DummyDropdown(ISO_MASS_DATETIME_BUILD_SENTINEL),
        append_datetime=True,
        datetime_format="%Y-%m-%d_%H-%M",
        state_ctrl=state_ctrl,
        validator=validator,
    )

    UIHandlers(app).on_datetime_format_changed(0)

    assert app.mass_datetime_build_selected is True
    assert app.append_datetime is False
    assert app.datetime_format == ISO_MASS_DATETIME_BUILD_SENTINEL
    assert app._mass_datetime_restore_state == {
        "append_datetime": True,
        "datetime_format": "%Y-%m-%d_%H-%M",
    }
    assert state_ctrl.saved is True
    assert validator.status_updated is True
    assert validator.ui_updated is True


def test_uk_mass_datetime_selection_saves_sentinel_and_keeps_restore_state():
    state_ctrl = DummyStateController()
    validator = DummyValidator()
    app = SimpleNamespace(
        date_time_dropdown=DummyDropdown(UK_MASS_DATETIME_BUILD_SENTINEL),
        append_datetime=True,
        datetime_format="%d-%m-%Y_%H-%M",
        state_ctrl=state_ctrl,
        validator=validator,
    )

    UIHandlers(app).on_datetime_format_changed(0)

    assert app.mass_datetime_build_selected is True
    assert app.append_datetime is False
    assert app.datetime_format == UK_MASS_DATETIME_BUILD_SENTINEL
    assert app._mass_datetime_restore_state == {
        "append_datetime": True,
        "datetime_format": "%d-%m-%Y_%H-%M",
    }
    assert state_ctrl.saved is True
    assert validator.status_updated is True
    assert validator.ui_updated is True


def test_usa_mass_datetime_selection_saves_sentinel_and_keeps_restore_state():
    state_ctrl = DummyStateController()
    validator = DummyValidator()
    app = SimpleNamespace(
        date_time_dropdown=DummyDropdown(USA_MASS_DATETIME_BUILD_SENTINEL),
        append_datetime=True,
        datetime_format="%m-%d-%Y_%H-%M",
        state_ctrl=state_ctrl,
        validator=validator,
    )

    UIHandlers(app).on_datetime_format_changed(0)

    assert app.mass_datetime_build_selected is True
    assert app.append_datetime is False
    assert app.datetime_format == USA_MASS_DATETIME_BUILD_SENTINEL
    assert app._mass_datetime_restore_state == {
        "append_datetime": True,
        "datetime_format": "%m-%d-%Y_%H-%M",
    }
    assert state_ctrl.saved is True
    assert validator.status_updated is True
    assert validator.ui_updated is True


def test_none_datetime_selection_uses_no_datetime_label_index():
    state_ctrl = DummyStateController()
    validator = DummyValidator()
    dropdown = DummyIndexedDropdown(
        [
            {"text": "Append Date/Time", "data": None},
            {"text": "──────────", "data": None},
            {"text": "ISO", "data": None},
            {"text": NO_DATETIME_LABEL, "data": None},
        ],
        current_index=2,
    )
    app = SimpleNamespace(
        date_time_dropdown=dropdown,
        append_datetime=True,
        datetime_format="%Y-%m-%d",
        state_ctrl=state_ctrl,
        validator=validator,
    )

    UIHandlers(app).on_datetime_format_changed(0)

    assert app.mass_datetime_build_selected is False
    assert app.append_datetime is False
    assert app.datetime_format == ""
    assert dropdown.currentIndex() == 3
    assert state_ctrl.saved is True
    assert validator.status_updated is True
    assert validator.ui_updated is True


def test_clear_icon_selects_no_icon_and_clears_runtime_state(monkeypatch):
    state_ctrl = DummyStateController()
    validator = DummyValidator()
    icon_dropdown = DummyIconDropdown()
    icon_input = DummyPathInput()
    script_input = DummyPathInput()
    script_input.set_display_path("main.py")
    icon_input.set_display_path("old.ico")
    app = SimpleNamespace(
        icon_clear_btn=object(),
        icon_path_input=icon_input,
        script_path_input=script_input,
        select_recent_icons=icon_dropdown,
        icon_path="old.ico",
        icon_user_cleared=False,
        state_ctrl=state_ctrl,
        validator=validator,
    )

    highlighted = []
    monkeypatch.setattr(
        ui_handlers,
        "flash_delete_highlight",
        lambda *args, **kwargs: highlighted.append(args),
    )

    UIHandlers(app).clear_icon()

    assert app.icon_path == ""
    assert app.icon_user_cleared is True
    assert icon_input.value == ""
    assert highlighted == [(app.icon_clear_btn,)]
    assert script_input.deselected is True
    assert script_input.cursor_position == 0
    assert icon_dropdown.current_index == 1
    assert icon_dropdown.blocked is False
    assert state_ctrl.saved is True
    assert validator.status_updated is True
    assert validator.ui_updated is True


def test_open_app_data_selects_existing_state_file(tmp_path):
    state_file = tmp_path / "EXEBuilder" / "exe_builder_state.json"
    state_file.parent.mkdir()
    state_file.write_text("{}", encoding="utf-8")
    app = SimpleNamespace(state_ctrl=DummyStateController(state_file))
    handler = UIHandlers(app)
    opened = []
    focused = []

    handler._select_file_in_explorer = lambda path: opened.append(("select", path))
    handler._open_folder = lambda path: opened.append(("folder", path))
    handler._force_app_data_folder_on_top = lambda path: focused.append(path)

    handler.open_app_data()

    assert opened == [("select", str(state_file))]
    assert focused == [str(state_file.parent)]


def test_open_app_data_opens_state_folder_when_file_missing(tmp_path):
    state_file = tmp_path / "EXEBuilder" / "exe_builder_state.json"
    app = SimpleNamespace(state_ctrl=DummyStateController(state_file))
    handler = UIHandlers(app)
    opened = []
    focused = []

    handler._select_file_in_explorer = lambda path: opened.append(("select", path))
    handler._open_folder = lambda path: opened.append(("folder", path))
    handler._force_app_data_folder_on_top = lambda path: focused.append(path)

    handler.open_app_data()

    assert opened == [("folder", str(state_file.parent))]
    assert focused == [str(state_file.parent)]
    assert state_file.parent.is_dir()


class DummySignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback


class DummyTimer:
    instances = []

    def __init__(self):
        self.timeout = DummySignal()
        self.interval = None
        self.started = False
        self.stopped = False
        self.__class__.instances.append(self)

    def setInterval(self, interval):
        self.interval = interval

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def _app_with_window_events(events):
    return SimpleNamespace(
        _is_closing=False,
        showMinimized=lambda: events.append("minimize"),
        showNormal=lambda: events.append("restore"),
        raise_=lambda: events.append("raise"),
        activateWindow=lambda: events.append("activate"),
    )


def test_app_data_monitor_minimizes_then_restores_when_folder_view_is_gone(monkeypatch, tmp_path):
    events = []
    DummyTimer.instances = []
    handler = UIHandlers(_app_with_window_events(events))
    folder_states = iter((True, False))

    monkeypatch.setattr(ui_handlers, "QTimer", DummyTimer)
    monkeypatch.setattr(
        handler,
        "_is_explorer_folder_open",
        lambda _path: next(folder_states),
    )

    assert handler._start_app_data_monitor(str(tmp_path)) is True
    timer = DummyTimer.instances[0]

    assert events == ["minimize"]
    assert timer.interval == 150
    assert timer.started is True

    timer.timeout.callback()

    assert events == ["minimize", "restore", "raise", "activate"]
    assert timer.stopped is True
    assert handler._app_data_monitor is None


def test_app_data_monitor_replaces_existing_timer(monkeypatch, tmp_path):
    events = []
    DummyTimer.instances = []
    handler = UIHandlers(_app_with_window_events(events))

    monkeypatch.setattr(ui_handlers, "QTimer", DummyTimer)
    monkeypatch.setattr(handler, "_is_explorer_folder_open", lambda _path: True)

    assert handler._start_app_data_monitor(str(tmp_path)) is True
    first_timer = DummyTimer.instances[0]
    assert handler._start_app_data_monitor(str(tmp_path)) is True

    assert first_timer.stopped is True
    assert len(DummyTimer.instances) == 2
    assert events == ["minimize", "minimize"]


def test_app_data_monitor_does_not_minimize_when_folder_cannot_be_detected(monkeypatch, tmp_path):
    events = []
    DummyTimer.instances = []
    handler = UIHandlers(_app_with_window_events(events))

    monkeypatch.setattr(ui_handlers, "QTimer", DummyTimer)
    monkeypatch.setattr(handler, "_is_explorer_folder_open", lambda _path: None)

    assert handler._start_app_data_monitor(str(tmp_path)) is False
    assert events == []
    assert DummyTimer.instances == []


def test_app_data_monitor_shutdown_does_not_restore(monkeypatch, tmp_path):
    events = []
    DummyTimer.instances = []
    app = _app_with_window_events(events)
    handler = UIHandlers(app)

    monkeypatch.setattr(ui_handlers, "QTimer", DummyTimer)
    monkeypatch.setattr(handler, "_is_explorer_folder_open", lambda _path: True)

    assert handler._start_app_data_monitor(str(tmp_path)) is True
    timer = DummyTimer.instances[0]
    app._is_closing = True
    timer.timeout.callback()

    assert timer.stopped is True
    assert events == ["minimize"]


def test_reset_output_to_desktop_keeps_remembered_non_desktop_output(monkeypatch, tmp_path):
    remembered_output = os.path.normpath(str(tmp_path / "dist"))
    state_ctrl = DummyStateController()
    validation_controller = DummyValidator()
    app = SimpleNamespace(
        output_refresh_btn=None,
        output_path_input=DummyPathInput(),
        output_path=remembered_output,
        last_output_dir=remembered_output,
        last_non_desktop_output_dir=remembered_output,
        state_ctrl=state_ctrl,
        validation_controller=validation_controller,
    )

    monkeypatch.setattr(ui_handlers, "flash_delete_highlight", lambda *args, **kwargs: None)

    handler = UIHandlers(app)
    desktop = os.path.normpath(handler.get_desktop_path())
    handler.reset_output_to_desktop()

    assert app.output_path == desktop
    assert app.output_path_input.value == desktop
    assert app.last_output_dir == remembered_output
    assert app.last_non_desktop_output_dir == remembered_output
    assert state_ctrl.saved is True
    assert validation_controller.ui_updated is True


def test_force_app_data_folder_on_top_activates_matching_window(monkeypatch, tmp_path):
    events = []

    class FakeWindow:
        title = "EXEBuilder"
        _hWnd = 123
        isMinimized = True

        def restore(self):
            events.append("restore")
            self.isMinimized = False

        def activate(self):
            events.append("activate")

    fake_window = FakeWindow()
    fake_pygetwindow = SimpleNamespace(
        getWindowsWithTitle=lambda title: [fake_window]
    )
    fake_win32con = SimpleNamespace(
        SW_RESTORE=9,
        SWP_NOMOVE=1,
        SWP_NOSIZE=2,
        SWP_SHOWWINDOW=4,
        HWND_TOPMOST=-1,
        HWND_NOTOPMOST=-2,
    )
    fake_win32gui = SimpleNamespace(
        ShowWindow=lambda hwnd, command: events.append(("show", hwnd, command)),
        SetForegroundWindow=lambda hwnd: events.append(("foreground", hwnd)),
        SetWindowPos=lambda hwnd, after, x, y, cx, cy, flags: events.append(
            ("position", hwnd, after, flags)
        ),
    )

    monkeypatch.setitem(sys.modules, "pygetwindow", fake_pygetwindow)
    monkeypatch.setitem(sys.modules, "win32con", fake_win32con)
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)

    handler = UIHandlers(SimpleNamespace())

    assert handler._force_app_data_folder_on_top(str(tmp_path / "EXEBuilder")) is True
    assert "restore" in events
    assert "activate" in events
    assert ("position", 123, fake_win32con.HWND_TOPMOST, 7) in events
    assert ("position", 123, fake_win32con.HWND_NOTOPMOST, 7) in events
