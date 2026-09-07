import os
import tempfile
import threading
from pathlib import Path

from .tray_icon_hook_source import TRAY_ICON_HOOK_SOURCE


TRAY_ICON_BUNDLE_NAME = "_exe_builder_tray_icon.ico"
_hook_directory = None
_hook_lock = threading.Lock()


def get_tray_icon_hook_path():
    # Frozen modules do not imply matching .py files on disk. PyInstaller needs
    # a real standalone source file, kept alive until all child builds finish.
    global _hook_directory
    with _hook_lock:
        if _hook_directory is None:
            _hook_directory = tempfile.TemporaryDirectory(prefix="exe-builder-hooks-")
        hook_path = Path(_hook_directory.name) / "pyinstaller_tray_icon_hook.py"
        hook_path.parent.mkdir(parents=True, exist_ok=True)
        if not hook_path.is_file():
            hook_path.write_text(TRAY_ICON_HOOK_SOURCE, encoding="utf-8")
        return str(hook_path)


def get_tray_icon_pyinstaller_args(icon_path):
    icon = (icon_path or "").strip()
    if not icon:
        return []

    normalized_icon = os.path.normpath(icon)
    return [
        "--runtime-hook",
        get_tray_icon_hook_path(),
        "--add-data",
        f"{normalized_icon}{os.pathsep}{TRAY_ICON_BUNDLE_NAME}",
    ]
