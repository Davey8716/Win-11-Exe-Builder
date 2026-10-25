"""The Build Summary Clear action resets both workflows without touching files."""

import ctypes
import json
import sys

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="The app uses Windows APIs")
def test_clear_build_workflows_resets_saved_selections_and_keeps_recents(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from PySide6.QtWidgets import QApplication
    from exe_builder.controllers.activation_controller import ActivationController

    monkeypatch.setattr(ActivationController, "listen_for_activation", lambda self: None)
    monkeypatch.setattr(ctypes, "GetLastError", lambda: 0)
    from exe_builder.main import EXEBuilderApp

    interpreter = tmp_path / "python.exe"
    icon = tmp_path / "app.ico"
    script = tmp_path / "main.py"
    project = tmp_path / "app.csproj"
    output = tmp_path / "output"
    for path in (interpreter, icon, script):
        path.write_text("test", encoding="utf-8")
    project.write_text('<Project Sdk="Microsoft.NET.Sdk" />', encoding="utf-8")
    output.mkdir()

    app = QApplication.instance() or QApplication([])
    window = EXEBuilderApp()
    try:
        window.show()
        app.processEvents()
        assert window.build_summary_clear_btn.parentWidget() is window.build_summary_title_frame

        window.python_interpreter_path = window.python_path = str(interpreter)
        window.icon_path = str(icon)
        window.script_path = str(script)
        window.entry_script = str(script)
        window.output_path = str(output)
        window.exe_name = "PythonApp"
        window.python_entry_input.set_display_path(str(interpreter))
        window.icon_path_input.set_display_path(str(icon))
        window.script_path_input.set_display_path(str(script))
        window.output_path_input.set_display_path(str(output))
        window.exe_name_input.setText("PythonApp")
        window.appened_py_version.setChecked(True)
        window.date_time_dropdown.setCurrentIndex(5)
        window._completed_python_steps.update(range(5))
        window.state_data.update({
            "recent_interpreters": [str(interpreter)],
            "recent_icons": [str(icon)],
            "recent_scripts": [str(script)],
        })

        window.dotnet_project_input.set_display_path(str(project))
        window.dotnet_icon_input.set_display_path(str(icon))
        window.dotnet_output_input.set_display_path(str(output))
        window.dotnet_name_input.setText("DotnetApp")
        window.dotnet_runtime_combo.setCurrentIndex(1)
        window.dotnet_single_file.setChecked(True)
        window.dotnet_date_time_dropdown.setCurrentIndex(5)
        window.csharp_state_data.update({
            "recent_projects": [str(project)], "recent_icons": [str(icon)]
        })
        window.environment_sync_controller.load_serialized_profiles([{
            "version": "3.14", "executable": str(interpreter), "packages": {}
        }])
        window.state_ctrl.save_all_state()
        window.python_section_nav.setCurrentRow(5)
        app.processEvents()

        window.building = True
        window._update_section_navigation_enabled()
        assert not window.build_summary_clear_btn.isEnabled()
        window.building = False
        window.environment_sync_controller.is_running = True
        window._update_clear_button_enabled()
        assert not window.build_summary_clear_btn.isEnabled()
        window.environment_sync_controller.is_running = False
        window._update_clear_button_enabled()
        assert window.build_summary_clear_btn.isEnabled()
        window.build_summary_clear_btn.click()
        app.processEvents()

        assert window.build_mode == "python"
        assert window.python_section_nav.currentRow() == 0
        assert window.dotnet_section_nav.currentRow() == 0
        assert window._completed_python_steps == set()
        assert window.environment_sync_controller.last_plan is None
        assert window.env_sync_rows_layout.count() == 0
        assert window.env_sync_log_input.text() == "Environment sync ready."
        assert not window.env_sync_match_btn.isEnabled()
        for field in (
            window.python_entry_input, window.icon_path_input,
            window.script_path_input, window.output_path_input,
            window.exe_name_input, window.dotnet_project_input,
            window.dotnet_icon_input, window.dotnet_output_input,
            window.dotnet_name_input,
        ):
            assert field.text() == ""
        assert window.build_summary_values["file"].text() == "Not selected"
        assert not window.appened_py_version.isChecked()
        assert window.dotnet_runtime_combo.currentData() == "win-x64"
        assert window.dotnet_self_contained.isChecked()
        assert not window.dotnet_single_file.isChecked()
        assert window.date_time_dropdown.currentData() is None
        assert window.dotnet_date_time_dropdown.currentData() is None

        state_dir = tmp_path / "EXEBuilder"
        python_state = json.loads((state_dir / "python_exe_builder_state.json").read_text())
        csharp_state = json.loads((state_dir / "csharp_exe_builder_state.json").read_text())
        assert python_state["last_script_path"] == ""
        assert python_state["env_sync_profiles"] == []
        assert python_state["guided_python_steps"] == []
        assert python_state["recent_scripts"] == [str(script)]
        assert csharp_state["project_path"] == ""
        assert csharp_state["recent_projects"] == [str(project)]
        assert all(path.exists() for path in (interpreter, icon, script, project, output))
    finally:
        window._is_closing = True
        window.close()

    reopened = EXEBuilderApp()
    try:
        assert reopened.python_section_nav.currentRow() == 0
        assert reopened.build_mode == "python"
        assert reopened.script_path_input.text() == ""
        assert reopened.dotnet_project_input.text() == ""
        assert reopened.environment_sync_controller.last_plan is None
    finally:
        reopened._is_closing = True
        reopened.close()
