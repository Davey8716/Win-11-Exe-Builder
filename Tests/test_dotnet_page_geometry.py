"""Regression coverage for the C# page's shared Python-style grid."""

from pathlib import Path


MAIN_SOURCE = (
    Path(__file__).resolve().parents[1] / "exe_builder" / "main.py"
).read_text(encoding="utf-8")


def test_dotnet_page_uses_the_python_two_column_grid():
    assert "self.dotnet_left_content, left_column = self._create_content_column()" in MAIN_SOURCE
    assert "self.dotnet_right_content, right_column = self._create_content_column()" in MAIN_SOURCE
    assert "dotnet_content_row_layout.setContentsMargins(0, 0, 0, 0)" in MAIN_SOURCE
    assert "dotnet_content_row_layout.setSpacing(0)" in MAIN_SOURCE
    assert "self.dotnet_center_divider.setFixedWidth(2)" in MAIN_SOURCE
    assert "self.dotnet_center_divider.setStyleSheet(CENTER_DIVIDER_STYLE)" in MAIN_SOURCE


def test_dotnet_divider_is_synchronized_from_its_section_heading():
    assert "def _sync_dotnet_center_divider_height(self):" in MAIN_SOURCE
    assert "anchor.mapTo(self.dotnet_content_row, QPoint(0, 0))" in MAIN_SOURCE
    assert "self.dotnet_content_row.setFixedHeight(content_height)" in MAIN_SOURCE
    assert "self.dotnet_center_divider.setFixedHeight(" in MAIN_SOURCE


def test_dotnet_build_section_is_centered_below_the_selection_grid():
    assert "self.dotnet_build_title = QLabel(\"Build Section\")" in MAIN_SOURCE
    assert "self.dotnet_build_title_row = QWidget()" in MAIN_SOURCE
    assert "self.dotnet_build_frame_row = QWidget()" in MAIN_SOURCE
    assert "dotnet_layout.addWidget(self.dotnet_build_title_row)" in MAIN_SOURCE
    assert "dotnet_layout.addWidget(self.dotnet_build_frame_row)" in MAIN_SOURCE
    assert "dotnet_build_frame_row_layout.addWidget(" in MAIN_SOURCE
    assert "left_column.addWidget(panel" not in MAIN_SOURCE


def test_dotnet_publish_panel_width_fits_the_runtime_and_option_controls():
    assert "self.dotnet_runtime_label.setMinimumWidth(" in MAIN_SOURCE
    assert "self.dotnet_runtime_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)" in MAIN_SOURCE
    assert "self.dotnet_runtime_combo.setMinimumWidth(190)" in MAIN_SOURCE
    assert "checkbox.setMinimumWidth(checkbox.sizeHint().width())" in MAIN_SOURCE
    assert "option_row.minimumSize().width()" in MAIN_SOURCE
    assert "panel.setFixedWidth(dotnet_publish_panel_width)" in MAIN_SOURCE
    assert "panel.setFixedWidth(PAIRED_FRAME_WIDTH)" not in MAIN_SOURCE


def test_dotnet_selection_sections_are_ordered_in_the_right_column():
    icon_section = 'path_section("icon", "Icons Select", right_column'
    file_section = 'path_section("project", "File Select", right_column'

    assert icon_section in MAIN_SOURCE
    assert file_section in MAIN_SOURCE
    assert MAIN_SOURCE.index(icon_section) < MAIN_SOURCE.index(file_section)


def test_dotnet_icon_section_includes_the_ico_converter():
    assert 'self.dotnet_ico_convert_btn = QPushButton("Open ICO Convert")' in MAIN_SOURCE
    assert "self.dotnet_ico_convert_btn.clicked.connect(self.ui_handlers.open_icon_sites)" in MAIN_SOURCE
