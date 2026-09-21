from PySide6.QtWidgets import QApplication, QPushButton

from exe_builder.ui.styles import (
    BUILD_OPTIONS_DIALOG_STYLE,
    Colors,
    build_mode_button_font,
    qcolor_name,
    title_frame_minimum_width,
)


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


def test_build_options_dialog_has_white_enabled_text_and_blue_close_button():
    assert "QDialog QCheckBox {" in BUILD_OPTIONS_DIALOG_STYLE
    assert f"color: {qcolor_name(Colors.TEXT_LIGHT)};" in BUILD_OPTIONS_DIALOG_STYLE
    assert "QDialog QCheckBox:disabled" in BUILD_OPTIONS_DIALOG_STYLE
    assert f"color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};" in BUILD_OPTIONS_DIALOG_STYLE
    assert "QDialogButtonBox QPushButton" in BUILD_OPTIONS_DIALOG_STYLE
    assert f"background-color: {qcolor_name(Colors.TITLE_BG)};" in BUILD_OPTIONS_DIALOG_STYLE
