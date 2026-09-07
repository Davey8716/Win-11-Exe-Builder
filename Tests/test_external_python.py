import os
from types import SimpleNamespace

import pytest

from exe_builder.build import external_python


def test_source_launch_preserves_environment(monkeypatch):
    monkeypatch.setattr(external_python.sys, "frozen", False, raising=False)
    with external_python.external_python_environment() as env:
        assert env == dict(os.environ)
        env["BUILDER_TEST_ONLY"] = "1"
    assert "BUILDER_TEST_ONLY" not in os.environ


@pytest.mark.parametrize("launch_fails", [False, True])
def test_frozen_launch_cleans_paths_and_restores_dll_directory(tmp_path, monkeypatch, launch_fails):
    bundle = str(tmp_path / "_internal")
    installed = str(tmp_path / "Python314")
    original_path = os.pathsep.join([bundle, bundle + os.sep + "PySide6", installed, bundle + "-other"])
    monkeypatch.setenv("PATH", original_path)
    monkeypatch.setattr(external_python.sys, "frozen", True, raising=False)
    monkeypatch.setattr(external_python.sys, "_MEIPASS", bundle, raising=False)
    monkeypatch.setattr(external_python.sys, "platform", "win32")
    calls = []

    def get_directory(size, buffer):
        if buffer is not None:
            buffer.value = bundle
        return len(bundle) + (1 if size == 0 else 0)

    def set_directory(value):
        calls.append(value)
        return 1

    kernel = SimpleNamespace(GetDllDirectoryW=get_directory, SetDllDirectoryW=set_directory)
    monkeypatch.setattr(external_python.ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False)
    try:
        with external_python.external_python_environment() as env:
            assert calls == [None]
            assert env["PATH"] == os.pathsep.join([installed, bundle + "-other"])
            if launch_fails:
                raise OSError("launch failed")
    except OSError:
        assert launch_fails
    assert calls == [None, bundle]
    assert os.environ["PATH"] == original_path
