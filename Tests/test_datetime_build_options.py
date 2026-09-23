from exe_builder.build.datetime_build_options import (
    ISO_MASS_DATETIME_BUILD_LABEL,
    REGIONAL_DATETIME_DROPDOWN_GROUPS,
    UK_MASS_DATETIME_BUILD_LABEL,
    USA_MASS_DATETIME_BUILD_LABEL,
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox
from exe_builder.main import EXEBuilderApp
from exe_builder.ui.styles import COMBO_BOX_LINE_EDIT_STYLE, COMBO_BOX_STYLE


def test_regional_dropdown_groups_place_build_all_after_singular_formats():
    visible_items = []
    for region_label, build_all_label, _build_all_data, format_options in REGIONAL_DATETIME_DROPDOWN_GROUPS:
        visible_items.append(region_label)
        visible_items.extend(label for label, _data in format_options)
        visible_items.append(build_all_label)

    assert visible_items == [
        "ISO",
        "ISO | YYYY-MM-DD",
        "ISO | YYYY-MM-DD_HH-MM",
        ISO_MASS_DATETIME_BUILD_LABEL,
        "UK",
        "UK | DD-MM-YYYY",
        "UK | DD-MM-YYYY_HH-MM",
        UK_MASS_DATETIME_BUILD_LABEL,
        "USA",
        "USA | MM-DD-YYYY",
        "USA | MM-DD-YYYY_HH-MM",
        USA_MASS_DATETIME_BUILD_LABEL,
    ]


def test_python_and_dotnet_date_selectors_share_the_same_populated_options():
    QApplication.instance() or QApplication([])
    python_dropdown = QComboBox()
    dotnet_dropdown = QComboBox()
    EXEBuilderApp._populate_datetime_dropdown(python_dropdown)
    EXEBuilderApp._populate_datetime_dropdown(dotnet_dropdown)

    def options(dropdown):
        return [
            (dropdown.itemText(index), dropdown.itemData(index), dropdown.model().item(index).isEnabled())
            for index in range(dropdown.count())
        ]

    assert options(dotnet_dropdown) == options(python_dropdown)
    assert [label for label, _, enabled in options(dotnet_dropdown) if enabled] == [
        "No Date Time Appended",
        "Build All Date/Time Outputs",
        "ISO | YYYY-MM-DD",
        "ISO | YYYY-MM-DD_HH-MM",
        "Build All ISO Date/Time Outputs",
        "UK | DD-MM-YYYY",
        "UK | DD-MM-YYYY_HH-MM",
        "Build All UK Date/Time Outputs",
        "USA | MM-DD-YYYY",
        "USA | MM-DD-YYYY_HH-MM",
        "Build All USA Date/Time Outputs",
    ]


def test_datetime_selectors_share_the_python_combo_box_theme():
    QApplication.instance() or QApplication([])
    python_dropdown = QComboBox()
    dotnet_dropdown = QComboBox()
    EXEBuilderApp._populate_datetime_dropdown(python_dropdown)
    EXEBuilderApp._populate_datetime_dropdown(dotnet_dropdown)

    for dropdown in (python_dropdown, dotnet_dropdown):
        assert dropdown.styleSheet() == COMBO_BOX_STYLE
        assert dropdown.lineEdit().styleSheet() == COMBO_BOX_LINE_EDIT_STYLE
        assert dropdown.lineEdit().alignment() == (Qt.AlignLeft | Qt.AlignVCenter)
