import os

from exe_builder.ui.path_hover_text import build_path_hover_text


def test_path_hover_text_includes_help_when_tooltips_are_enabled():
    raw_path = os.path.join("C:\\", "project", "..", "project", "main.py")
    help_text = "File path to python script folder and file."

    text = build_path_hover_text(raw_path, help_text, include_help=True)

    assert text == f"{os.path.normpath(raw_path)}\n\n{help_text}"


def test_path_hover_text_omits_help_when_tooltips_are_disabled():
    raw_path = os.path.join("C:\\", "project", "..", "project", "main.py")

    text = build_path_hover_text(
        raw_path,
        "File path to python script folder and file.",
        include_help=False,
    )

    assert text == os.path.normpath(raw_path)


def test_path_hover_text_returns_none_for_empty_input():
    text = build_path_hover_text("   ", "File path to python script folder and file.", True)

    assert text is None


def test_summary_hover_text_preserves_the_displayed_value_and_removes_wrap_points():
    text = build_path_hover_text(
        "C:/project/\u200bmain.py",
        "File path to python script folder and file.",
        include_help=True,
        normalize_path=False,
    )

    assert text == (
        "C:/project/main.py\n\nFile path to python script folder and file."
    )
