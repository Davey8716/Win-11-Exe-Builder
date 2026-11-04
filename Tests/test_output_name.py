import pytest

from exe_builder.build.output_name import executable_name_error, output_folder_name


@pytest.mark.parametrize(("path", "expected"), [
    (r"C:\\Users\\davey\\Local EXES\\Win-11-Resurface", "Win-11-Resurface"),
    ("C:/Local EXES/Win-11-Resurface/", "Win-11-Resurface"),
    ("C:/", ""),
    ("", ""),
])
def test_output_folder_name(path, expected):
    assert output_folder_name(path) == expected


@pytest.mark.parametrize("name", ["", "CON", "NUL.txt", "bad?name", "trailing."])
def test_invalid_output_folder_names(name):
    assert executable_name_error(name)


def test_valid_output_folder_name():
    assert not executable_name_error("Win-11-Resurface")
