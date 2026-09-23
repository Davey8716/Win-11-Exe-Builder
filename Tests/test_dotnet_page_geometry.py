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
