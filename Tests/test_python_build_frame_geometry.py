"""Regression coverage for the Python build action frame spacing."""

from pathlib import Path


MAIN_SOURCE = (
    Path(__file__).resolve().parents[1] / "exe_builder" / "main.py"
).read_text(encoding="utf-8")


def test_python_build_frame_matches_the_dotnet_action_panel_geometry():
    assert "BUILD_ACTION_FRAME_WIDTH = 450" in MAIN_SOURCE
    assert "build_action_edge_padding = 12" in MAIN_SOURCE
    assert "build_layout.setContentsMargins(" in MAIN_SOURCE
    assert "build_action_edge_padding, build_action_edge_padding," in MAIN_SOURCE
    assert "build_layout.setSpacing(7)" in MAIN_SOURCE
    assert "self.status_label.setFixedSize(420, 75)" in MAIN_SOURCE
    assert "build_actions.addStretch()" in MAIN_SOURCE
    assert "build_layout.addStretch()" not in MAIN_SOURCE
    assert "build_frame.setFixedWidth(BUILD_ACTION_FRAME_WIDTH)" in MAIN_SOURCE
    assert "build_frame.setFixedHeight(build_frame.sizeHint().height())" in MAIN_SOURCE
