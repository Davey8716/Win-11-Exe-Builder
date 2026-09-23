"""Check the rendered vertical positions when switching build modes."""

import ctypes
import sys

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="The app uses Windows APIs")
def test_build_mode_pages_share_vertical_landmarks(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QApplication

    from exe_builder.controllers.activation_controller import ActivationController

    monkeypatch.setattr(ActivationController, "listen_for_activation", lambda self: None)
    monkeypatch.setattr(ctypes, "GetLastError", lambda: 0)
    from exe_builder.main import EXEBuilderApp

    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    window = EXEBuilderApp()

    def top(widget):
        return widget.mapTo(window, QPoint(0, 0)).y()

    def bottom(widget):
        return top(widget) + widget.height()

    try:
        window.show()
        window.set_build_mode("python", save=False)
        app.processEvents()
        python_positions = (
            top(window.title_frame),
            top(window.icons_title_frame),
            top(window.icon_frame),
            top(window.center_divider),
            bottom(window.center_divider),
            top(window.build_title.parentWidget()),
            top(window.build_btn.parentWidget()),
        )

        window.set_build_mode("dotnet", save=False)
        app.processEvents()
        dotnet_positions = (
            top(window.dotnet_title_container),
            top(window.dotnet_section_title_frames[1]),
            top(window.dotnet_configuration_frames[0]),
            top(window.dotnet_center_divider),
            bottom(window.dotnet_center_divider),
            top(window.dotnet_build_title_frame),
            top(window.dotnet_publish_btn.parentWidget()),
        )

        assert all(
            abs(python_y - dotnet_y) <= 2
            for python_y, dotnet_y in zip(python_positions, dotnet_positions)
        ), (
            f"Python: {python_positions}; C#: {dotnet_positions}; "
            f"Python row heights: {[window.python_mode_page.layout().itemAt(i).widget().height() for i in range(4)]}; "
            f"C# row heights: {[window.dotnet_mode_page.layout().itemAt(i).widget().height() for i in range(4)]}"
        )

        window.set_build_mode("python", save=False)
        app.processEvents()
        assert top(window.title_frame) == python_positions[0]
        assert top(window.build_btn.parentWidget()) == python_positions[-1]
    finally:
        window._is_closing = True
        window.close()
