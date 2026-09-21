from PySide6.QtWidgets import QApplication, QPushButton

from exe_builder.ui.styles import build_mode_button_font


def test_build_mode_buttons_match_dropdown_typography():
    QApplication.instance() or QApplication([])

    for button in (QPushButton("Python EXE"), QPushButton("C# .NET Publish")):
        button.setFont(build_mode_button_font())
        font = button.font()
        assert font.family() == "Rubik UI"
        assert font.pointSize() == 11
        assert font.bold()
