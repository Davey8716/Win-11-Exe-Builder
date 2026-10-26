"""Saved Python build setups can be restored without starting a build."""

import ctypes
import json
import sys

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="The app uses Windows APIs")
@pytest.mark.parametrize("with_icon", [False, True])
def test_save_restore_restart_and_delete_build_setup(monkeypatch, tmp_path, with_icon):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from exe_builder.controllers.activation_controller import ActivationController

    monkeypatch.setattr(ActivationController, "listen_for_activation", lambda self: None)
    monkeypatch.setattr(ctypes, "GetLastError", lambda: 0)
    from exe_builder.main import EXEBuilderApp

    interpreter = tmp_path / "python.exe"
    script = tmp_path / "main.py"
    icon = tmp_path / "icon.ico"
    output = tmp_path / "Local Exes" / "Audio Book"
    for path in (interpreter, script, icon):
        path.write_text("test", encoding="utf-8")
    output.mkdir(parents=True)

    app = QApplication.instance() or QApplication([])
    window = EXEBuilderApp()
    try:
        window.show()
        app.processEvents()
        assert not hasattr(window, "build_summary_clear_btn")
        build_page = window.python_section_stack.widget(5)
        saved_setups_section = window.save_build_setup_btn.parentWidget()
        assert saved_setups_section.parentWidget() is build_page
        assert window.saved_build_setup_dropdown.parentWidget() is saved_setups_section
        assert window.saved_build_setup_dropdown.width() == 300
        assert not window.saved_build_setup_dropdown.model().item(0).isEnabled()
        assert window.delete_build_setup_btn.parentWidget() is saved_setups_section
        assert window.saved_setups_label.parentWidget() is saved_setups_section
        assert window.saved_setups_label.font().bold()
        assert window.saved_setups_label.alignment() == Qt.AlignCenter
        controls = saved_setups_section.layout().itemAt(1).layout()
        assert controls.itemAt(0).widget() is window.save_build_setup_btn
        assert controls.itemAt(1).widget() is window.saved_build_setup_dropdown
        assert controls.itemAt(2).widget() is window.delete_build_setup_btn
        build_layout = build_page.layout()
        assert build_layout.indexOf(window.build_summary_frame) < build_layout.indexOf(saved_setups_section)
        assert build_layout.indexOf(saved_setups_section) < build_layout.indexOf(window.build_title.parentWidget())
        assert saved_setups_section.width() == window.build_summary_frame.width()
        assert window.python_saved_setups_backup_section.parentWidget() is build_page
        assert build_layout.indexOf(saved_setups_section) < build_layout.indexOf(
            window.python_saved_setups_backup_section
        )
        assert build_layout.indexOf(window.python_saved_setups_backup_section) < build_layout.indexOf(
            window.build_title.parentWidget()
        )
        assert window.save_build_setup_btn.font().bold()
        assert window.save_build_setup_btn.width() == 135
        assert window.save_build_setup_btn.height() == 28
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
        window.exe_name = "main"
        window.python_entry_input.set_display_path(str(interpreter))
        window.script_path_input.set_display_path(str(script))
        window.icon_path_input.set_display_path(window.icon_path)
        window.output_path_input.set_display_path(str(output))
        window.exe_name_input.setText("main")
        window.appened_py_version.setChecked(True)
        window._update_python_navigation()
        assert window.save_build_setup_btn.isEnabled()

        window.save_build_setup_btn.click()
        assert not window.save_build_setup_btn.isEnabled()
        assert window.saved_build_setup_dropdown.currentIndex() == 1
        assert window.delete_build_setup_btn.isEnabled()
        window.save_build_setup_btn.click()
        assert len(window.saved_build_setups) == 1
        assert window.saved_build_setup_dropdown.count() == 2
        assert window.saved_build_setup_dropdown.itemText(1) == "Local Exes / Audio Book / main"
        saved_file = tmp_path / "EXEBuilder" / "python_exe_builder_state.json"
        assert len(json.loads(saved_file.read_text())["saved_build_setups"]) == 1

        window.exe_name_input.setText("Changed")
        assert window.saved_build_setup_dropdown.count() == 2
        assert window.saved_build_setup_dropdown.currentIndex() == 0
        assert window.save_build_setup_btn.isEnabled()
        window.saved_build_setup_dropdown.setCurrentIndex(1)
        assert window.python_entry_input.text() == str(interpreter)
        assert window.script_path_input.text() == str(script)
        assert window.icon_path_input.text() == (str(icon) if with_icon else "")
        assert window.output_path_input.text() == str(output)
        assert window.exe_name_input.text() == "main"
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
        reopened.exe_name_input.setText("Changed again")
        reopened.saved_build_setup_dropdown.setCurrentIndex(1)
        assert reopened.script_path_input.text() == str(script)
        assert reopened.exe_name_input.text() == "main"
        assert reopened.delete_build_setup_btn.isEnabled()
        confirmations = []
        reopened._confirm_delete_saved_build_setup = lambda name: confirmations.append(name) or False
        reopened._delete_selected_build_setup()
        assert confirmations == ["Local Exes / Audio Book / main"]
        assert reopened.saved_build_setup_dropdown.count() == 2
        reopened._confirm_delete_saved_build_setup = lambda _name: True
        reopened._delete_selected_build_setup()
        assert reopened.saved_build_setup_dropdown.count() == 1
        assert not reopened.delete_build_setup_btn.isEnabled()
        assert reopened.save_build_setup_btn.isEnabled()
        assert json.loads(saved_file.read_text())["saved_build_setups"] == []
        assert all(path.exists() for path in (interpreter, script, icon, output))
    finally:
        reopened._is_closing = True
        reopened.close()


@pytest.mark.skipif(sys.platform != "win32", reason="The app uses Windows APIs")
def test_save_restore_restart_and_delete_dotnet_build_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from exe_builder.controllers.activation_controller import ActivationController

    monkeypatch.setattr(ActivationController, "listen_for_activation", lambda self: None)
    monkeypatch.setattr(ctypes, "GetLastError", lambda: 0)
    from exe_builder.main import EXEBuilderApp

    project = tmp_path / "Reader.csproj"
    icon = tmp_path / "reader.ico"
    output = tmp_path / "Local Exes" / "Reader"
    project.write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup /></Project>',
        encoding="utf-8",
    )
    icon.write_text("test", encoding="utf-8")
    output.mkdir(parents=True)

    app = QApplication.instance() or QApplication([])
    window = EXEBuilderApp()
    try:
        window.show()
        app.processEvents()
        build_page = window.dotnet_section_stack.widget(3)
        saved_setups_section = window.dotnet_save_build_setup_btn.parentWidget()
        assert window.dotnet_build_summary_title_frame.parentWidget() is build_page
        assert window.dotnet_build_summary_frame.parentWidget() is build_page
        assert saved_setups_section is window.dotnet_saved_setups_section
        assert saved_setups_section.parentWidget() is build_page
        assert window.saved_dotnet_build_setup_dropdown.parentWidget() is saved_setups_section
        assert window.saved_dotnet_build_setup_dropdown.width() == 300
        assert not window.saved_dotnet_build_setup_dropdown.model().item(0).isEnabled()
        assert window.dotnet_delete_build_setup_btn.parentWidget() is saved_setups_section
        assert window.dotnet_saved_setups_label.font().bold()
        assert window.dotnet_saved_setups_label.alignment() == Qt.AlignCenter
        controls = saved_setups_section.layout().itemAt(1).layout()
        assert controls.itemAt(0).widget() is window.dotnet_save_build_setup_btn
        assert controls.itemAt(1).widget() is window.saved_dotnet_build_setup_dropdown
        assert controls.itemAt(2).widget() is window.dotnet_delete_build_setup_btn
        build_layout = build_page.layout()
        assert build_layout.indexOf(window.dotnet_build_summary_frame) < build_layout.indexOf(
            saved_setups_section
        )
        assert build_layout.indexOf(saved_setups_section) < build_layout.indexOf(
            window.dotnet_build_title_frame
        )
        assert window.dotnet_build_summary_frame.width() == window.build_summary_frame.width()
        assert saved_setups_section.width() == window.dotnet_build_summary_frame.width()
        assert window.dotnet_saved_setups_backup_section.parentWidget() is build_page
        assert build_layout.indexOf(saved_setups_section) < build_layout.indexOf(
            window.dotnet_saved_setups_backup_section
        )
        assert build_layout.indexOf(window.dotnet_saved_setups_backup_section) < build_layout.indexOf(
            window.dotnet_build_title_frame
        )
        assert not window.dotnet_save_build_setup_btn.isEnabled()
        assert not window.dotnet_delete_build_setup_btn.isEnabled()

        window.dotnet_project_input.set_display_path(str(project))
        window.dotnet_output_input.set_display_path(str(output))
        window.dotnet_icon_input.set_display_path(str(icon))
        window.dotnet_name_input.setText("Reader")
        window.dotnet_runtime_combo.setCurrentIndex(
            window.dotnet_runtime_combo.findData("win-arm64")
        )
        window.dotnet_date_time_dropdown.setCurrentIndex(
            window.dotnet_date_time_dropdown.findData("%d-%m-%Y")
        )
        window.dotnet_single_file.setChecked(True)
        window.restore_dotnet_guided_workflow(range(3))
        window._on_dotnet_settings_changed()
        assert window.dotnet_save_build_setup_btn.isEnabled()

        window.dotnet_save_build_setup_btn.click()
        assert len(window.saved_dotnet_build_setups) == 1
        assert window.saved_dotnet_build_setup_dropdown.count() == 2
        assert window.saved_dotnet_build_setup_dropdown.itemText(1) == "Local Exes / Reader / Reader"
        assert window.saved_dotnet_build_setup_dropdown.currentIndex() == 1
        assert window.dotnet_delete_build_setup_btn.isEnabled()
        assert not window.dotnet_save_build_setup_btn.isEnabled()
        window.dotnet_save_build_setup_btn.click()
        assert len(window.saved_dotnet_build_setups) == 1
        saved_file = tmp_path / "EXEBuilder" / "csharp_exe_builder_state.json"
        assert len(json.loads(saved_file.read_text())["saved_build_setups"]) == 1

        window.dotnet_name_input.setText("Changed")
        assert window.saved_dotnet_build_setup_dropdown.currentIndex() == 0
        assert window.dotnet_save_build_setup_btn.isEnabled()
        window.saved_dotnet_build_setup_dropdown.setCurrentIndex(1)
        assert window.dotnet_project_input.text() == str(project)
        assert window.dotnet_output_input.text() == str(output)
        assert window.dotnet_icon_input.text() == str(icon)
        assert window.dotnet_name_input.text() == "Reader"
        assert window.dotnet_runtime_combo.currentData() == "win-arm64"
        assert window.dotnet_date_time_dropdown.currentData() == "%d-%m-%Y"
        assert window.dotnet_single_file.isChecked()
        assert not window.dotnet_self_contained.isChecked()
        assert window.dotnet_build_summary_values["project"].toolTip() == str(project)
        assert window.dotnet_build_summary_values["icon"].toolTip() == str(icon)
        assert window.dotnet_build_summary_values["output"].toolTip() == str(output)
        assert window.dotnet_build_summary_values["name"].toolTip() == "Reader"
        assert window.dotnet_build_summary_values["runtime"].toolTip() == "Windows ARM64"
        assert window.dotnet_section_nav.currentRow() == 3
        assert not window.building
        assert window.dotnet_publish_btn.text() == "Publish"
        assert not window.dotnet_save_build_setup_btn.isEnabled()
        assert window.dotnet_delete_build_setup_btn.isEnabled()
    finally:
        window._is_closing = True
        window.close()

    reopened = EXEBuilderApp()
    try:
        assert reopened.saved_dotnet_build_setup_dropdown.count() == 2
        reopened.dotnet_name_input.setText("Changed again")
        reopened.saved_dotnet_build_setup_dropdown.setCurrentIndex(1)
        assert reopened.dotnet_project_input.text() == str(project)
        assert reopened.dotnet_name_input.text() == "Reader"
        confirmations = []
        reopened._confirm_delete_saved_dotnet_build_setup = (
            lambda name: confirmations.append(name) or False
        )
        reopened._delete_selected_dotnet_build_setup()
        assert confirmations == ["Local Exes / Reader / Reader"]
        assert reopened.saved_dotnet_build_setup_dropdown.count() == 2
        reopened._confirm_delete_saved_dotnet_build_setup = lambda _name: True
        reopened._delete_selected_dotnet_build_setup()
        assert reopened.saved_dotnet_build_setup_dropdown.count() == 1
        assert not reopened.dotnet_delete_build_setup_btn.isEnabled()
        assert reopened.dotnet_save_build_setup_btn.isEnabled()
        assert json.loads(saved_file.read_text())["saved_build_setups"] == []
    finally:
        reopened._is_closing = True
        reopened.close()


@pytest.mark.skipif(sys.platform != "win32", reason="The app uses Windows APIs")
def test_export_import_saved_setups_are_portable_and_mode_specific(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QFileDialog
    from exe_builder.controllers.activation_controller import ActivationController
    from exe_builder.ui.styles import Colors, qcolor_name

    monkeypatch.setattr(ActivationController, "listen_for_activation", lambda self: None)
    monkeypatch.setattr(ctypes, "GetLastError", lambda: 0)
    from exe_builder.main import EXEBuilderApp

    python_setup = {
        "interpreter": "C:/Python/python.exe",
        "icon": "C:/Icons/tool.ico",
        "script": "C:/Project/tool.py",
        "output": "C:/Builds/Tool",
        "name": "Tool",
        "datetime_format": None,
        "append_py_version": False,
    }
    dotnet_setup = {
        "project": "C:/Project/Tool.csproj",
        "icon": "C:/Icons/tool.ico",
        "output": "C:/Builds/Tool",
        "name": "Tool",
        "runtime": "win-x64",
        "datetime_format": None,
        "self_contained": True,
        "single_file": False,
        "trim": False,
    }
    python_backup = tmp_path / "python-setups.json"
    dotnet_backup = tmp_path / "dotnet-setups.json"
    app = QApplication.instance() or QApplication([])
    window = EXEBuilderApp()
    try:
        scheduled_resets = []
        monkeypatch.setattr(
            QTimer, "singleShot",
            lambda milliseconds, callback: scheduled_resets.append((milliseconds, callback)),
        )
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName", lambda *_args: (str(python_backup), "")
        )
        window.saved_build_setups = [python_setup]
        window._export_saved_build_setups("python")
        payload = json.loads(python_backup.read_text(encoding="utf-8"))
        assert payload == {
            "format": "win11-exe-builder-saved-setups",
            "version": 1,
            "builder": "python",
            "saved_setups": [python_setup],
        }

        window.saved_build_setups = []
        monkeypatch.setattr(
            QFileDialog, "getOpenFileName", lambda *_args: (str(python_backup), "")
        )
        window._import_saved_build_setups("python")
        assert window.saved_build_setups == [python_setup]
        assert qcolor_name(Colors.SUCCESS) in window.status_label.styleSheet()
        assert scheduled_resets[-1][0] == 3000
        python_refreshes = []
        window.validator.update_ui_state = lambda: python_refreshes.append(True)
        scheduled_resets[-1][1]()
        assert python_refreshes == [True]

        monkeypatch.setattr(
            QFileDialog, "getSaveFileName", lambda *_args: (str(dotnet_backup), "")
        )
        window.saved_dotnet_build_setups = [dotnet_setup]
        window._export_saved_build_setups("dotnet")
        payload = json.loads(dotnet_backup.read_text(encoding="utf-8"))
        assert payload["builder"] == "dotnet"
        assert payload["saved_setups"] == [dotnet_setup]

        window.saved_dotnet_build_setups = []
        monkeypatch.setattr(
            QFileDialog, "getOpenFileName", lambda *_args: (str(dotnet_backup), "")
        )
        window._import_saved_build_setups("dotnet")
        assert window.saved_dotnet_build_setups == [dotnet_setup]
        assert qcolor_name(Colors.SUCCESS) in window.dotnet_status_label.styleSheet()
        assert scheduled_resets[-1][0] == 3000
        dotnet_refreshes = []
        window.dotnet_publish_controller.refresh_ui = lambda: dotnet_refreshes.append(True)
        scheduled_resets[-1][1]()
        assert dotnet_refreshes == [True]

        window._import_saved_build_setups("dotnet")
        assert "Imported 0 saved setups" in window.dotnet_status_label.toPlainText()
        assert qcolor_name(Colors.ERROR) in window.dotnet_status_label.styleSheet()

        monkeypatch.setattr(
            QFileDialog, "getOpenFileName", lambda *_args: (str(python_backup), "")
        )
        window._import_saved_build_setups("dotnet")
        assert window.saved_dotnet_build_setups == [dotnet_setup]
        assert "different builder" in window.dotnet_status_label.toPlainText()
        assert qcolor_name(Colors.ERROR) in window.dotnet_status_label.styleSheet()
    finally:
        window._is_closing = True
        window.close()
