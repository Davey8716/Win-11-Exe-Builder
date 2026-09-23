"""Regression coverage for the Python build action frame spacing."""

from pathlib import Path


MAIN_SOURCE = (
    Path(__file__).resolve().parents[1] / "exe_builder" / "main.py"
).read_text(encoding="utf-8")


def test_python_build_frame_edges_match_the_action_button_gap():
    assert "build_action_gap = 4" in MAIN_SOURCE
    assert "build_action_edge_padding = 12" in MAIN_SOURCE
    assert "build_layout.setContentsMargins(" in MAIN_SOURCE
    assert "build_action_edge_padding, 5," in MAIN_SOURCE
    assert "build_action_edge_padding, build_action_edge_padding," in MAIN_SOURCE
    assert "build_layout.setSpacing(build_action_gap)" in MAIN_SOURCE
    assert "build_actions.setSpacing(build_action_gap)" in MAIN_SOURCE
    assert "build_actions.minimumSize().width()" in MAIN_SOURCE
    assert "+ (2 * build_action_edge_padding)" in MAIN_SOURCE
    assert "build_frame.setFixedSize(build_frame_width, 170)" in MAIN_SOURCE
