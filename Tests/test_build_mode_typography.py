import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from exe_builder.ui.styles import (
    BUILD_OPTIONS_DIALOG_STYLE,
    Colors,
    apply_build_mode_button_state,
    build_mode_button_font,
    qcolor_name,
    segmented_build_mode_button_style,
    title_frame_minimum_width,
)
import exe_builder.ui.styles as styles


def test_build_mode_buttons_match_dropdown_typography():
    QApplication.instance() or QApplication([])

    for button in (QPushButton("Python"), QPushButton("C# .NET")):
        button.setFont(build_mode_button_font())
        font = button.font()
        assert font.family() == "Rubik UI"
        assert font.pointSize() == 10
        assert font.weight() == styles.QFont.DemiBold


def test_active_build_mode_button_is_blue_and_both_modes_are_available():
    QApplication.instance() or QApplication([])
    python_button = QPushButton("Python")
    dotnet_button = QPushButton("C# .NET")
    python_button.setCheckable(True)
    dotnet_button.setCheckable(True)

    apply_build_mode_button_state(python_button, dotnet_button, "python")
    assert python_button.isChecked()
    assert python_button.isEnabled()
    assert python_button.styleSheet() == segmented_build_mode_button_style(True)
    assert not dotnet_button.isChecked()
    assert dotnet_button.isEnabled()
    assert dotnet_button.styleSheet() == segmented_build_mode_button_style(False)

    apply_build_mode_button_state(python_button, dotnet_button, "dotnet")
    assert not python_button.isChecked()
    assert python_button.isEnabled()
    assert python_button.styleSheet() == segmented_build_mode_button_style(False)
    assert dotnet_button.isChecked()
    assert dotnet_button.isEnabled()
    assert dotnet_button.styleSheet() == segmented_build_mode_button_style(True)


@pytest.mark.parametrize("mode", ("python", "dotnet"))
def test_both_build_mode_buttons_are_greyed_while_building(mode):
    QApplication.instance() or QApplication([])
    python_button = QPushButton("Python")
    dotnet_button = QPushButton("C# .NET")
    python_button.setCheckable(True)
    dotnet_button.setCheckable(True)

    apply_build_mode_button_state(python_button, dotnet_button, mode, building=True)

    assert python_button.isChecked() is (mode == "python")
    assert dotnet_button.isChecked() is (mode == "dotnet")
    for button in (python_button, dotnet_button):
        assert not button.isEnabled()
        assert button.styleSheet() == segmented_build_mode_button_style(
            button.isChecked(), disabled=True
        )


def test_title_frame_width_reserves_text_margins_and_balanced_controls():
    assert title_frame_minimum_width(320, 34, 10) == 414


def test_build_options_dialog_has_white_enabled_text_and_blue_close_button():
    assert "QDialog QCheckBox {" in BUILD_OPTIONS_DIALOG_STYLE
    assert f"color: {qcolor_name(Colors.TEXT_LIGHT)};" in BUILD_OPTIONS_DIALOG_STYLE
    assert "QDialog QCheckBox:disabled" in BUILD_OPTIONS_DIALOG_STYLE
    assert f"color: {qcolor_name(Colors.BUILD_DISABLED_TEXT)};" in BUILD_OPTIONS_DIALOG_STYLE
    assert "QDialogButtonBox QPushButton" in BUILD_OPTIONS_DIALOG_STYLE
    assert f"background-color: {qcolor_name(Colors.TITLE_BG)};" in BUILD_OPTIONS_DIALOG_STYLE


def test_build_options_native_title_style_uses_panel_blue(monkeypatch):
    calls = []
    dialog = object()
    monkeypatch.setattr(
        styles,
        "apply_native_title_bar_style",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    styles.apply_build_options_title_bar_style(dialog)

    assert calls == [((dialog,), {"caption": Colors.PANEL_BG, "border": Colors.PANEL_BG})]
