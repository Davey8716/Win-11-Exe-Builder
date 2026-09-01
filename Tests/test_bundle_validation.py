from pathlib import Path
from types import SimpleNamespace

import pytest

from exe_builder.build import bundle_validation
from exe_builder.build.bundle_validation import validate_bundle_inputs


def make_app(tmp_path: Path, **overrides):
    script = tmp_path / "app.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    python = tmp_path / "python.exe"
    python.write_text("", encoding="utf-8")

    output = tmp_path / "dist"
    output.mkdir()

    app = SimpleNamespace(
        entry_script=str(script),
        python_interpreter_path=str(python),
        output_path=str(output),
        exe_name="MyApp",
        icon_path="",
    )

    for name, value in overrides.items():
        setattr(app, name, value)

    return app


@pytest.fixture
def python_version_ok(monkeypatch):
    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(bundle_validation.subprocess, "run", fake_run)


def test_validate_bundle_inputs_accepts_valid_required_values(tmp_path, python_version_ok):
    app = make_app(tmp_path)

    assert validate_bundle_inputs(app) == (True, None)


def test_validate_bundle_inputs_rejects_missing_entry_script(tmp_path):
    app = make_app(tmp_path, entry_script="")

    assert validate_bundle_inputs(app) == (False, "No entry script selected.")


def test_validate_bundle_inputs_rejects_non_python_entry_script(tmp_path):
    script = tmp_path / "notes.txt"
    script.write_text("not python\n", encoding="utf-8")
    app = make_app(tmp_path, entry_script=str(script))

    assert validate_bundle_inputs(app) == (False, "Entry script must be a .py file.")


def test_validate_bundle_inputs_rejects_invalid_exe_name(tmp_path, python_version_ok):
    app = make_app(tmp_path, exe_name="bad:name")

    valid, message = validate_bundle_inputs(app)

    assert valid is False
    assert "invalid characters" in message


def test_validate_bundle_inputs_rejects_non_ico_icon(tmp_path, python_version_ok):
    icon = tmp_path / "icon.png"
    icon.write_text("", encoding="utf-8")
    app = make_app(tmp_path, icon_path=str(icon))

    assert validate_bundle_inputs(app) == (False, "Icon must be a .ico file.")
