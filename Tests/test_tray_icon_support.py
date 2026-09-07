import os
import sys
import subprocess
from pathlib import Path

from exe_builder.build import pyinstaller_tray_icon_hook as tray_icon_hook
from exe_builder.build import tray_icon_support
from exe_builder.build.tray_icon_support import (
    TRAY_ICON_BUNDLE_NAME,
    get_tray_icon_hook_path,
    get_tray_icon_pyinstaller_args,
)


def test_get_tray_icon_pyinstaller_args_returns_empty_without_icon():
    assert get_tray_icon_pyinstaller_args("") == []


def test_get_tray_icon_pyinstaller_args_includes_runtime_hook_and_icon(tmp_path):
    icon = tmp_path / "sample.ico"
    icon.write_text("", encoding="utf-8")

    args = get_tray_icon_pyinstaller_args(str(icon))

    assert args == [
        "--runtime-hook",
        get_tray_icon_hook_path(),
        "--add-data",
        f"{os.path.normpath(str(icon))}{os.pathsep}{TRAY_ICON_BUNDLE_NAME}",
    ]


def test_tray_icon_hook_file_exists():
    assert Path(get_tray_icon_hook_path()).is_file()


def test_frozen_builder_materializes_standalone_hook(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "missing_bundle"), raising=False)
    monkeypatch.setattr(tray_icon_support, "__file__", str(tmp_path / "missing_bundle" / "tray_icon_support.py"))
    monkeypatch.setattr(tray_icon_support, "_hook_directory", None)
    try:
        hook = Path(get_tray_icon_hook_path())
        assert hook.is_file()
        # Isolated Python cannot import the builder package from this folder.
        # The generated hook must work using only its own standalone source.
        result = subprocess.run(
            [sys.executable, "-I", str(hook)], cwd=tmp_path,
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0, result.stderr
        assert get_tray_icon_hook_path() == str(hook)
    finally:
        if tray_icon_support._hook_directory is not None:
            tray_icon_support._hook_directory.cleanup()


def test_tray_icon_hook_resolves_direct_meipass_icon(monkeypatch, tmp_path):
    direct_icon = tmp_path / "bundle" / TRAY_ICON_BUNDLE_NAME
    direct_icon.parent.mkdir()
    direct_icon.write_text("icon", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(direct_icon.parent), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "dist" / "App.exe"))

    assert tray_icon_hook._resolve_tray_icon_path() == str(direct_icon)


def test_tray_icon_hook_resolves_nested_meipass_icon(monkeypatch, tmp_path):
    nested_icon = tmp_path / "bundle" / TRAY_ICON_BUNDLE_NAME / "selected.ico"
    nested_icon.parent.mkdir(parents=True)
    nested_icon.write_text("icon", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "dist" / "App.exe"))

    assert tray_icon_hook._resolve_tray_icon_path() == str(nested_icon)


def test_tray_icon_hook_direct_icon_beats_nested_icon(monkeypatch, tmp_path):
    direct_icon = tmp_path / "bundle" / TRAY_ICON_BUNDLE_NAME
    nested_icon = tmp_path / "dist" / "_internal" / TRAY_ICON_BUNDLE_NAME / "selected.ico"
    direct_icon.parent.mkdir()
    nested_icon.parent.mkdir(parents=True)
    direct_icon.write_text("direct", encoding="utf-8")
    nested_icon.write_text("nested", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "dist" / "App.exe"))

    assert tray_icon_hook._resolve_tray_icon_path() == str(direct_icon)


def test_tray_icon_hook_resolves_nested_internal_icon(monkeypatch, tmp_path):
    fake_exe = tmp_path / "dist" / "App.exe"
    nested_icon = fake_exe.parent / "_internal" / TRAY_ICON_BUNDLE_NAME / "selected.ico"
    nested_icon.parent.mkdir(parents=True)
    nested_icon.write_text("icon", encoding="utf-8")
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))

    assert tray_icon_hook._resolve_tray_icon_path() == str(nested_icon)
