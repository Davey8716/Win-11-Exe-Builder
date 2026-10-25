"""Saved Python build setups can be restored without starting a build."""

import ctypes
import json
import sys

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="The app uses Windows APIs")
@pytest.mark.parametrize("with_icon", [False, True])
def test_save_restore_clear_restart_and_delete_build_setup(monkeypatch, tmp_path, with_icon):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from PySide6.QtWidgets import QApplication
    from exe_builder.controllers.activation_controller import ActivationController

    monkeypatch.setattr(ActivationController, "listen_for_activation", lambda self: None)
    monkeypatch.setattr(ctypes, "GetLastError", lambda: 0)
    from exe_builder.main import EXEBuilderApp

    interpreter = tmp_path / "python.exe"
    script = tmp_path / "main.py"
    icon = tmp_path / "icon.ico"
    output = tmp_path / "output"
    for path in (interpreter, script, icon):
        path.write_text("test", encoding="utf-8")
    output.mkdir()

    app = QApplication.instance() or QApplication([])
    window = EXEBuilderApp()
    try:
        window.show()
        app.processEvents()
        assert window.saved_build_setup_dropdown.parentWidget() is window.python_navigation_sidebar
        build_page = window.python_section_stack.widget(5)
        save_row = window.save_build_setup_btn.parentWidget()
        assert save_row.parentWidget() is build_page
        build_layout = build_page.layout()
        assert build_layout.indexOf(window.build_summary_frame) < build_layout.indexOf(save_row)
        assert build_layout.indexOf(save_row) < build_layout.indexOf(window.build_title.parentWidget())
        assert save_row.width() == window.build_summary_frame.width()
        assert window.build_summary_clear_btn.font().bold()
        assert window.save_build_setup_btn.font().bold()
        assert window.save_build_setup_btn.width() == 135
        assert window.save_build_setup_btn.height() == 38
        assert window.delete_build_setup_btn.font().bold()
        assert window.delete_build_setup_btn.width() == 75
        assert window.delete_build_setup_btn.height() == 28
        assert not window.save_build_setup_btn.isEnabled()
        assert not window.delete_build_setup_btn.isEnabled()
        window.python_interpreter_path = window.python_path = str(interpreter)
        window.script_path = window.entry_script = str(script)
        window.project_root = str(tmp_path)
        window.icon_path = str(icon) if with_icon else ""
        window.output_path = str(output)
        window.exe_name = "Example"
        window.python_entry_input.set_display_path(str(interpreter))
        window.script_path_input.set_display_path(str(script))
        window.icon_path_input.set_display_path(window.icon_path)
        window.output_path_input.set_display_path(str(output))
        window.exe_name_input.setText("Example")
        window.appened_py_version.setChecked(True)
        window._update_python_navigation()
        assert window.save_build_setup_btn.isEnabled()

        window.save_build_setup_btn.click()
        assert not window.save_build_setup_btn.isEnabled()
        assert not window.delete_build_setup_btn.isEnabled()
        window.save_build_setup_btn.click()
        assert len(window.saved_build_setups) == 1
        assert window.saved_build_setup_dropdown.count() == 2
        saved_file = tmp_path / "EXEBuilder" / "python_exe_builder_state.json"
        assert len(json.loads(saved_file.read_text())["saved_build_setups"]) == 1

        window._clear_build_workflows()
        assert window.saved_build_setup_dropdown.count() == 2
        assert window.script_path_input.text() == ""
        assert window.python_section_nav.currentRow() == 0
        window.saved_build_setup_dropdown.setCurrentIndex(1)
        assert window.python_entry_input.text() == str(interpreter)
        assert window.script_path_input.text() == str(script)
        assert window.icon_path_input.text() == (str(icon) if with_icon else "")
        assert window.output_path_input.text() == str(output)
        assert window.exe_name_input.text() == "Example"
        assert window.appened_py_version.isChecked()
        assert window.python_section_nav.currentRow() == 5
        assert not window.building
        assert window.build_btn.text() == "Build EXE"
        assert not window.save_build_setup_btn.isEnabled()
        assert window.delete_build_setup_btn.isEnabled()
    finally:
        window._is_closing = True
        window.close()

    reopened = EXEBuilderApp()
    try:
        assert reopened.saved_build_setup_dropdown.count() == 2
        reopened._clear_build_workflows()
        reopened.saved_build_setup_dropdown.setCurrentIndex(1)
        assert reopened.script_path_input.text() == str(script)
        assert reopened.delete_build_setup_btn.isEnabled()
        reopened.delete_build_setup_btn.click()
        assert reopened.saved_build_setup_dropdown.count() == 1
        assert not reopened.delete_build_setup_btn.isEnabled()
        assert reopened.save_build_setup_btn.isEnabled()
        assert json.loads(saved_file.read_text())["saved_build_setups"] == []
        assert all(path.exists() for path in (interpreter, script, icon, output))
    finally:
        reopened._is_closing = True
        reopened.close()
