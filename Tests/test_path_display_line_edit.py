from PySide6.QtWidgets import QApplication

from exe_builder.ui.path_display_line_edit import PathDisplayLineEdit


def test_dotnet_path_fields_use_the_python_path_font():
    QApplication.instance() or QApplication([])

    fields = {
        "project": PathDisplayLineEdit(),
        "icon": PathDisplayLineEdit(),
        "output": PathDisplayLineEdit(),
    }

    for field in fields.values():
        font = field.font()
        assert font.family() == "Rubik UI"
        assert font.pointSize() == 11
        assert font.bold()
        assert field.height() >= field.fontMetrics().lineSpacing() * 2
