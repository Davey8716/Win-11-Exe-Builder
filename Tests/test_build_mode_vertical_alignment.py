"""Check the sidebar workflow when switching build modes."""

import ctypes
import json
import os
import sys

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="The app uses Windows APIs")
def test_build_modes_use_sidebars_and_guided_python_steps(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QPushButton

    from exe_builder.controllers.activation_controller import ActivationController
    from exe_builder.build.build_cancellation import BuildCancellation
    from exe_builder.ui.styles import Colors, qcolor_name

    monkeypatch.setattr(ActivationController, "listen_for_activation", lambda self: None)
    monkeypatch.setattr(ctypes, "GetLastError", lambda: 0)
    from exe_builder.main import EXEBuilderApp

    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    window = EXEBuilderApp()

    try:
        window.show()
        window.set_build_mode("python", save=False)
        app.processEvents()
        python_title_center = window.title_label.mapTo(
            window, QPoint(window.title_label.width() // 2, 0)
        ).x()
        assert abs(python_title_center - window.width() / 2) <= 1
        assert window.build_options_btn.text() == "☰"
        assert window.build_options_btn.mapTo(window, QPoint(0, 0)).y() + window.build_options_btn.height() <= window.python_navigation_sidebar.mapTo(window, QPoint(0, 0)).y()
        assert window.python_section_nav.count() == 6
        assert window.python_section_stack.currentIndex() == 0
        assert window.python_mode_btn.parentWidget() is window.python_navigation_sidebar
        assert window.dotnet_mode_btn.parentWidget() is window.python_navigation_sidebar
        build_page = window.python_section_stack.widget(5)
        assert window.build_summary_title_frame.parentWidget() is build_page
        assert window.build_summary_title.parentWidget() is window.build_summary_title_frame
        for index, keys in ((2, {"interpreter"}), (3, {"interpreter", "icon"}),
                            (4, {"interpreter", "icon", "file"})):
            title, frame, labels, values = window.python_selection_summaries[
                ("Icons", "File", "Output")[index - 2]
            ]
            assert title.parentWidget() is window.python_section_stack.widget(index)
            assert frame.parentWidget() is window.python_section_stack.widget(index)
            assert set(labels) == set(values) == keys
        assert window.python_selection_summaries["Icons"][3]["interpreter"].text() == "Not selected"
        assert window.python_selection_summaries["File"][3]["icon"].text() == "No icon"
        assert window.build_summary_values["interpreter"].font().bold()
        assert qcolor_name(Colors.SUCCESS) in window.build_summary_values["interpreter"].styleSheet()
        assert window.build_summary_values["interpreter"].textInteractionFlags() == Qt.NoTextInteraction
        assert window.build_summary_values["interpreter"].focusPolicy() == Qt.NoFocus
        assert qcolor_name(Colors.TEXT_LIGHT) in window.build_summary_values["icon"].styleSheet()
        assert window.build_summary_values["icon"].text() == "(No icon needed to build)"
        for index, label in ((1, "Continue to icons"), (3, "Continue to output")):
            assert label in [
                button.text()
                for button in window.python_section_stack.widget(index).findChildren(QPushButton)
            ]
        assert window.python_section_nav.geometry().right() < window.python_section_stack.geometry().left()
        assert not bool(window.python_section_nav.item(1).flags() & Qt.ItemIsEnabled)
        assert window.interpreter_continue_btn.isHidden()
        assert window.file_continue_btn.isHidden()
        assert window.output_continue_btn.isHidden()
        for button in (
            window.interpreter_continue_btn,
            window.icon_continue_btn,
            window.file_continue_btn,
            window.output_continue_btn,
        ):
            assert button.width() == 280
            assert button.height() == 42
            assert button.font().bold()

        continue_sync = next(
            button for button in window.python_section_stack.widget(0).findChildren(QPushButton)
            if button.text() == "Continue without syncing"
        )
        continue_sync.click()
        assert window.python_section_stack.currentIndex() == 1
        window.python_entry_input.setText("C:/Python/python.exe")
        assert window.python_section_stack.currentIndex() == 1
        assert not window.interpreter_continue_btn.isHidden()
        assert bool(window.python_section_nav.item(2).flags() & Qt.ItemIsEnabled)
        assert window.build_summary_values["interpreter"].text() == "C:/Python/python.exe"
        assert window.python_selection_summaries["Icons"][3]["interpreter"].text() == "C:/Python/python.exe"
        assert window.python_selection_summaries["Output"][3]["interpreter"].text() == "C:/Python/python.exe"
        window.icon_path_input.setText("C:/icons/app.ico")
        assert bool(window.python_section_nav.item(3).flags() & Qt.ItemIsEnabled)
        assert window.build_summary_values["icon"].text() == "C:/icons/app.ico"
        assert qcolor_name(Colors.SUCCESS) in window.build_summary_labels["icon"].styleSheet()
        assert qcolor_name(Colors.SUCCESS) in window.build_summary_values["icon"].styleSheet()
        assert window.python_selection_summaries["File"][3]["icon"].text() == "C:/icons/app.ico"
        assert window.python_selection_summaries["Output"][3]["icon"].toolTip() == "C:/icons/app.ico"
        window.script_path_input.setText("C:/project/main.py")
        assert bool(window.python_section_nav.item(4).flags() & Qt.ItemIsEnabled)
        assert window.build_summary_values["file"].text() == "C:/project/main.py"
        assert window.python_selection_summaries["Output"][3]["file"].text() == "C:/project/main.py"
        window.python_section_nav.setCurrentRow(1)
        next_button = next(
            button for button in window.python_section_stack.widget(1).findChildren(QPushButton)
            if button.text() == "Continue to icons"
        )
        next_button.click()
        assert window.python_section_stack.currentIndex() == 2
        window.ui_handlers.clear_icon()
        assert window.icon_continue_btn.text() == "Use no icon and continue"
        assert window.python_selection_summaries["File"][3]["icon"].text() == "No icon"
        assert window.python_selection_summaries["Output"][3]["icon"].text() == "No icon"
        window.icon_path_input.setText("C:/icons/app.ico")
        assert window.icon_continue_btn.text() == "Continue to file"
        assert window.icon_path_input.text() == "C:/icons/app.ico"
        assert window.python_section_stack.currentIndex() == 2
        window.icon_continue_btn.click()
        assert window.python_section_stack.currentIndex() == 3
        continue_file = next(
            button for button in window.python_section_stack.widget(3).findChildren(QPushButton)
            if button.text() == "Continue to output"
        )
        continue_file.click()
        assert window.python_section_stack.currentIndex() == 4
        assert window.output_continue_btn.isHidden()

        window.guided_flow_checkbox.setChecked(False)
        assert all(bool(window.python_section_nav.item(i).flags() & Qt.ItemIsEnabled)
                   for i in range(6))

        window.set_build_mode("dotnet", save=False)
        app.processEvents()
        dotnet_title_center = window.dotnet_mode_title.mapTo(
            window, QPoint(window.dotnet_mode_title.width() // 2, 0)
        ).x()
        assert abs(dotnet_title_center - window.width() / 2) <= 1
        assert window.dotnet_build_options_btn.text() == "☰"
        assert window.dotnet_build_options_btn.mapTo(window, QPoint(0, 0)).y() + window.dotnet_build_options_btn.height() <= window.dotnet_navigation_sidebar.mapTo(window, QPoint(0, 0)).y()
        assert window.dotnet_section_nav.count() == 4
        assert window.dotnet_python_mode_btn.parentWidget() is window.dotnet_navigation_sidebar
        assert window.dotnet_mode_sidebar_btn.parentWidget() is window.dotnet_navigation_sidebar
        assert window.dotnet_section_nav.geometry().right() < window.dotnet_section_stack.geometry().left()
        assert window.dotnet_selection_summaries["File Select"][3]["icon"].text() == "No icon"
        assert window.dotnet_selection_summaries["Output Select"][3]["file"].text() == "Not selected"
        assert window.dotnet_selection_summaries["File Select"][0].parentWidget() is window.dotnet_section_stack.widget(1)
        assert window.dotnet_selection_summaries["Output Select"][0].parentWidget() is window.dotnet_section_stack.widget(2)
        assert window.dotnet_build_title_frame.parentWidget() is window.dotnet_section_stack.widget(3)
        window.dotnet_icon_input.setText("C:/icons/dotnet.ico")
        assert window.dotnet_selection_summaries["File Select"][3]["icon"].text() == "C:/icons/dotnet.ico"
        assert window.dotnet_selection_summaries["Output Select"][3]["icon"].text() == "C:/icons/dotnet.ico"
        window.dotnet_project_input.setText("C:/project/app.csproj")
        assert window.dotnet_selection_summaries["Output Select"][3]["file"].text() == "C:/project/app.csproj"
        window.dotnet_icon_input.clear()
        assert window.dotnet_selection_summaries["File Select"][3]["icon"].text() == "No icon"
        assert window.dotnet_selection_summaries["Output Select"][3]["icon"].text() == "No icon"
        window.set_build_mode("python", save=False)
        app.processEvents()
        assert window.python_section_stack.currentIndex() == 4

        window.build_cancellation = BuildCancellation(window, window)
        window.building = True
        window.validation_controller.update_ui_state()
        assert not window.python_section_nav.isEnabled()
        assert not window.dotnet_section_nav.isEnabled()
        assert "item:selected:disabled" in window.python_section_nav.styleSheet()
        for label in (window.build_mode_label, window.dotnet_build_mode_label):
            assert not label.isEnabled()
            assert qcolor_name(Colors.BUILD_DISABLED_TEXT) in label.styleSheet()
        for button in (window.python_mode_btn, window.dotnet_mode_btn,
                       window.dotnet_python_mode_btn, window.dotnet_mode_sidebar_btn):
            assert not button.isEnabled()
        QTest.mouseClick(
            window.python_section_nav.viewport(), Qt.LeftButton,
            pos=window.python_section_nav.visualItemRect(window.python_section_nav.item(0)).center(),
        )
        assert window.python_section_nav.currentRow() == 4
        window.building = False
        window.validation_controller.update_ui_state()
        assert window.python_section_nav.isEnabled()
        assert window.dotnet_section_nav.isEnabled()
        for label in (window.build_mode_label, window.dotnet_build_mode_label):
            assert label.isEnabled()
            assert qcolor_name(Colors.TEXT_LIGHT) in label.styleSheet()
        assert window.dotnet_mode_btn.isEnabled()
        assert all(bool(window.python_section_nav.item(i).flags() & Qt.ItemIsEnabled)
                   for i in range(6))

        window.set_build_mode("dotnet", save=False)
        window.dotnet_section_nav.setCurrentRow(2)
        window.building = True
        window.dotnet_publish_controller.refresh_ui()
        assert not window.python_section_nav.isEnabled()
        assert not window.dotnet_section_nav.isEnabled()
        for label in (window.build_mode_label, window.dotnet_build_mode_label):
            assert not label.isEnabled()
            assert qcolor_name(Colors.BUILD_DISABLED_TEXT) in label.styleSheet()
        for button in (window.python_mode_btn, window.dotnet_mode_btn,
                       window.dotnet_python_mode_btn, window.dotnet_mode_sidebar_btn):
            assert not button.isEnabled()
        QTest.mouseClick(
            window.dotnet_section_nav.viewport(), Qt.LeftButton,
            pos=window.dotnet_section_nav.visualItemRect(window.dotnet_section_nav.item(0)).center(),
        )
        assert window.dotnet_section_nav.currentRow() == 2
        window.building = False
        window.dotnet_publish_controller.refresh_ui()
        assert window.python_section_nav.isEnabled()
        assert window.dotnet_section_nav.isEnabled()
        for label in (window.build_mode_label, window.dotnet_build_mode_label):
            assert label.isEnabled()
            assert qcolor_name(Colors.TEXT_LIGHT) in label.styleSheet()
        assert window.dotnet_python_mode_btn.isEnabled()
    finally:
        window._is_closing = True
        window.close()


@pytest.mark.skipif(sys.platform != "win32", reason="The app uses Windows APIs")
def test_ready_saved_python_workflow_opens_build_tab(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from exe_builder.controllers.activation_controller import ActivationController

    interpreter = tmp_path / "python.exe"
    script = tmp_path / "main.py"
    icon = tmp_path / "app.ico"
    project = tmp_path / "app.csproj"
    output = tmp_path / "output"
    interpreter.write_text("", encoding="utf-8")
    script.write_text("print('ready')", encoding="utf-8")
    icon.write_bytes(b"icon")
    project.write_text('<Project Sdk="Microsoft.NET.Sdk" />', encoding="utf-8")
    output.mkdir()
    state_dir = tmp_path / "EXEBuilder"
    state_dir.mkdir()
    (state_dir / "python_exe_builder_state.json").write_text(
        json.dumps(
            {
                "python_interpreter_path": str(interpreter),
                "last_script_path": str(script),
                "last_icon_path": str(icon),
                "last_output_folder": str(output),
                "last_exe_name": "ReadyApp",
                "guided_python_steps": [0, 1, 2, 3, 4],
            }
        ),
        encoding="utf-8",
    )
    (state_dir / "exe_builder_preferences.json").write_text(
        json.dumps({"build_mode": "python", "guided_flow_enabled": True}),
        encoding="utf-8",
    )
    (state_dir / "csharp_exe_builder_state.json").write_text(
        json.dumps({
            "project_path": str(project),
            "icon_path": str(icon),
            "recent_projects": [str(project)],
            "recent_icons": [str(icon)],
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr(ActivationController, "listen_for_activation", lambda self: None)
    monkeypatch.setattr(ctypes, "GetLastError", lambda: 0)
    from exe_builder.main import EXEBuilderApp

    app = QApplication.instance() or QApplication([])
    window = EXEBuilderApp()
    try:
        window.show()
        app.processEvents()
        assert window.python_section_stack.currentIndex() == 5
        assert window.python_selection_summaries["Icons"][3]["interpreter"].toolTip() == str(interpreter)
        assert window.python_selection_summaries["File"][3]["icon"].toolTip() == str(icon)
        assert window.python_selection_summaries["Output"][3]["file"].toolTip() == str(script)
        assert window.dotnet_selection_summaries["File Select"][3]["icon"].toolTip() == str(icon)
        assert window.dotnet_selection_summaries["Output Select"][3]["file"].toolTip() == str(project)
        assert all(
            bool(window.python_section_nav.item(index).flags() & Qt.ItemIsEnabled)
            for index in range(6)
        )
    finally:
        window._is_closing = True
        window.close()
