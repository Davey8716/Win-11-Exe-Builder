"""Regression checks for the shared utility-button SVG contract."""

from xml.etree import ElementTree

from exe_builder.ui.styles import (
    DELETE_ALL_BUTTON_ICON,
    DELETE_ALL_BUTTON_ICON_SIZE,
    DELETE_BUTTON_ICON,
    DELETE_BUTTON_ICON_SIZE,
    REFRESH_BUTTON_ICON,
    REFRESH_BUTTON_ICON_SIZE,
    UTILITY_ICON_BUTTON_SIZE,
    UTILITY_ICON_RENDER_SIZE,
)


def test_utility_icon_assets_use_a_normalized_svg_canvas():
    for icon_path in (
        DELETE_BUTTON_ICON,
        DELETE_ALL_BUTTON_ICON,
        REFRESH_BUTTON_ICON,
    ):
        root = ElementTree.parse(icon_path).getroot()
        assert root.tag.endswith("svg")
        assert root.attrib["viewBox"] == "0 0 24 24"


def test_utility_icon_buttons_share_one_render_and_button_size():
    assert UTILITY_ICON_BUTTON_SIZE == (35, 35)
    assert UTILITY_ICON_RENDER_SIZE == (18, 18)
    assert {
        DELETE_BUTTON_ICON_SIZE,
        DELETE_ALL_BUTTON_ICON_SIZE,
        REFRESH_BUTTON_ICON_SIZE,
    } == {UTILITY_ICON_RENDER_SIZE}
