"""Check the sidebar workflow when switching build modes."""

import ctypes
import sys

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="The app uses Windows APIs")
def test_build_modes_use_sidebars_and_guided_python_steps(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QPushButton

    from exe_builder.controllers.activation_controller import ActivationController

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
        assert window.python_section_nav.count() == 6
        assert window.python_section_stack.currentIndex() == 0
        for index, label in ((1, "Continue to icons"), (3, "Continue to output")):
            assert label in [
                button.text()
                for button in window.python_section_stack.widget(index).findChildren(QPushButton)
            ]
        assert window.python_section_nav.geometry().right() < window.python_section_stack.geometry().left()
        assert not bool(window.python_section_nav.item(1).flags() & Qt.ItemIsEnabled)

        continue_sync = next(
            button for button in window.python_section_stack.widget(0).findChildren(QPushButton)
            if button.text() == "Continue without syncing"
        )
        continue_sync.click()
        assert window.python_section_stack.currentIndex() == 1
        window.python_entry_input.setText("C:/Python/python.exe")
        assert window.python_section_stack.currentIndex() == 1
        window.icon_path_input.setText("C:/icons/app.ico")
        window.script_path_input.setText("C:/project/main.py")
        window.python_section_nav.setCurrentRow(1)
        next_button = next(
            button for button in window.python_section_stack.widget(1).findChildren(QPushButton)
            if button.text() == "Continue to icons"
        )
        next_button.click()
        assert window.python_section_stack.currentIndex() == 2
        window.ui_handlers.clear_icon()
        assert window.icon_continue_btn.text() == "Use no icon and continue"
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

        window.guided_flow_checkbox.setChecked(False)
        assert all(bool(window.python_section_nav.item(i).flags() & Qt.ItemIsEnabled)
                   for i in range(6))

        window.set_build_mode("dotnet", save=False)
        app.processEvents()
        assert window.dotnet_section_nav.count() == 4
        assert window.dotnet_section_nav.geometry().right() < window.dotnet_section_stack.geometry().left()
        window.set_build_mode("python", save=False)
        app.processEvents()
        assert window.python_section_stack.currentIndex() == 4
    finally:
        window._is_closing = True
        window.close()
