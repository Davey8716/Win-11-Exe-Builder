from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_SOURCE = (PROJECT_ROOT / "exe_builder" / "main.py").read_text(encoding="utf-8")
TOOLTIPS_SOURCE = (PROJECT_ROOT / "exe_builder" / "ui" / "tooltips.py").read_text(
    encoding="utf-8"
)


def test_environment_sync_uses_compact_visible_warning_and_help_button():
    assert 'self.env_sync_help_btn = QPushButton("?")' in MAIN_SOURCE
    assert "self.env_sync_help_btn.setFixedSize(35,35)" in MAIN_SOURCE
    assert (
        '"Warning: sync may fail if packages are incompatible."' in MAIN_SOURCE
    )
    assert "self.env_sync_warning_label.setWordWrap(True)" not in MAIN_SOURCE

    scan_position = MAIN_SOURCE.index(
        "env_sync_action_layout.addWidget(self.env_sync_scan_btn)"
    )
    sync_position = MAIN_SOURCE.index(
        "env_sync_action_layout.addWidget(self.env_sync_match_btn)"
    )
    help_position = MAIN_SOURCE.index(
        "env_sync_action_layout.addWidget(self.env_sync_help_btn)"
    )
    assert scan_position < sync_position < help_position


def test_environment_sync_help_button_has_the_full_compatibility_tooltip():
    assert "QtTooltip(\n        app.env_sync_help_btn,\n        env_sync_summary," in TOOLTIPS_SOURCE
    assert "it does not guarantee\\n\"\n        \"package compatibility" in TOOLTIPS_SOURCE


def test_environment_sync_help_button_opens_styled_information_dialog():
    assert "def _show_environment_sync_help(self):" in MAIN_SOURCE
    assert 'dialog.setWindowTitle("Environment Sync Help")' in MAIN_SOURCE
    assert "does not guarantee package compatibility" in MAIN_SOURCE
    assert "successful EXE build" in MAIN_SOURCE
    assert 'dialog.addButton("Close", QMessageBox.AcceptRole)' in MAIN_SOURCE
    assert "dialog.setDefaultButton(close_button)" in MAIN_SOURCE
    assert "dialog.setEscapeButton(close_button)" in MAIN_SOURCE
    assert "dialog.setStyleSheet(CONFIRMATION_MESSAGE_BOX_STYLE)" in MAIN_SOURCE
    assert "~Qt.WindowContextHelpButtonHint" in MAIN_SOURCE
    assert "apply_native_title_bar_style(" in MAIN_SOURCE
    assert "dialog.exec()" in MAIN_SOURCE
    assert "self.env_sync_help_btn.clicked.connect(self._show_environment_sync_help)" in MAIN_SOURCE
