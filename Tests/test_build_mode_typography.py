from PySide6.QtWidgets import QApplication, QPushButton

from exe_builder.ui.styles import build_mode_button_font, title_frame_minimum_width


def test_build_mode_buttons_match_dropdown_typography():
    QApplication.instance() or QApplication([])

    for button in (QPushButton("Python EXE"), QPushButton("C# .NET Publish")):
        button.setFont(build_mode_button_font())
        font = button.font()
        assert font.family() == "Rubik UI"
        assert font.pointSize() == 11
        assert font.bold()


def test_title_frame_width_reserves_text_margins_and_balanced_controls():
    assert title_frame_minimum_width(320, 34, 10) == 414
