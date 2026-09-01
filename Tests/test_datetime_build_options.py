from exe_builder.build.datetime_build_options import (
    ISO_MASS_DATETIME_BUILD_LABEL,
    REGIONAL_DATETIME_DROPDOWN_GROUPS,
    UK_MASS_DATETIME_BUILD_LABEL,
    USA_MASS_DATETIME_BUILD_LABEL,
)


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
