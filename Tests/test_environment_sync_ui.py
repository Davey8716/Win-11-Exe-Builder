from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_SOURCE = (PROJECT_ROOT / "exe_builder" / "main.py").read_text(encoding="utf-8")
TOOLTIPS_SOURCE = (PROJECT_ROOT / "exe_builder" / "ui" / "tooltips.py").read_text(
    encoding="utf-8"
)
STYLES_SOURCE = (PROJECT_ROOT / "exe_builder" / "ui" / "styles.py").read_text(
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


def test_environment_sync_table_uses_uniform_six_pixel_padding():
    assert "ENV_SYNC_TABLE_PADDING = 6" in MAIN_SOURCE
    assert MAIN_SOURCE.count("ENV_SYNC_TABLE_PADDING,") >= 8
    assert "+ (2 * ENV_SYNC_TABLE_PADDING)" in MAIN_SOURCE


def test_environment_sync_content_uses_shared_section_typography_and_geometry():
    assert "ENV_SYNC_CONTENT_FONT_SIZE = 11" in MAIN_SOURCE
    assert "ENV_SYNC_TABLE_ROW_VERTICAL_PADDING = 6" in MAIN_SOURCE
    assert '"Rubik UI", ENV_SYNC_CONTENT_FONT_SIZE, QFont.Bold' in MAIN_SOURCE
    assert "self.env_sync_warning_label.setFont(self.env_sync_content_font)" in MAIN_SOURCE
    assert "label.setFont(self.env_sync_content_font)" in MAIN_SOURCE
    assert "env_sync_font_metrics.height() + ENV_SYNC_TABLE_ROW_VERTICAL_PADDING" in MAIN_SOURCE
    assert "row.setFixedHeight(self._env_sync_row_height)" in MAIN_SOURCE


def test_environment_sync_subframes_use_shared_control_typography():
    assert 'font-family: "Rubik UI";' in STYLES_SOURCE
    assert "font-size: 11pt;" in STYLES_SOURCE
    assert "ENV_SYNC_STATUS_LINE_STYLE" in STYLES_SOURCE
    assert "ENV_SYNC_SCROLL_AREA_STYLE" in STYLES_SOURCE


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
