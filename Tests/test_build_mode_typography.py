from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from exe_builder.ui.styles import (
    BUILD_OPTIONS_DIALOG_STYLE,
    Colors,
    apply_build_mode_button_state,
    build_disabled_button,
    build_mode_button_font,
    button_base,
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


def test_build_mode_label_uses_bold_mode_typography():
    QApplication.instance() or QApplication([])

    label = QLabel("Build mode:")
    label.setFont(build_mode_button_font())

    assert label.font().family() == "Rubik UI"
    assert label.font().pointSize() == 11
    assert label.font().bold()


def test_active_build_mode_button_is_greyed_and_inactive_button_is_enabled():
    QApplication.instance() or QApplication([])
    python_button = QPushButton("Python EXE")
    dotnet_button = QPushButton("C# .NET Publish")
    python_button.setCheckable(True)
    dotnet_button.setCheckable(True)

    apply_build_mode_button_state(python_button, dotnet_button, "python")
    assert python_button.isChecked()
    assert not python_button.isEnabled()
    assert python_button.styleSheet() == build_disabled_button()
    assert not dotnet_button.isChecked()
    assert dotnet_button.isEnabled()
    assert dotnet_button.styleSheet() == button_base()

    apply_build_mode_button_state(python_button, dotnet_button, "dotnet")
    assert not python_button.isChecked()
    assert python_button.isEnabled()
    assert python_button.styleSheet() == button_base()
    assert dotnet_button.isChecked()
    assert not dotnet_button.isEnabled()
    assert dotnet_button.styleSheet() == build_disabled_button()


def test_title_frame_width_reserves_text_margins_and_balanced_controls():
    assert title_frame_minimum_width(320, 34, 10) == 414


def test_build_options_dialog_has_white_enabled_text_and_blue_close_button():
    assert "QDialog QCheckBox {" in BUILD_OPTIONS_DIALOG_STYLE
    assert f"color: {qcolor_name(Colors.TEXT_LIGHT)};" in BUILD_OPTIONS_DIALOG_STYLE
    assert "QDialog QCheckBox:disabled" in BUILD_OPTIONS_DIALOG_STYLE
    assert f"color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};" in BUILD_OPTIONS_DIALOG_STYLE
    assert "QDialogButtonBox QPushButton" in BUILD_OPTIONS_DIALOG_STYLE
    assert f"background-color: {qcolor_name(Colors.TITLE_BG)};" in BUILD_OPTIONS_DIALOG_STYLE
