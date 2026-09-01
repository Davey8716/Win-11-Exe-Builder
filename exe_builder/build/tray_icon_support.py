import os
from pathlib import Path


TRAY_ICON_BUNDLE_NAME = "_exe_builder_tray_icon.ico"


def get_tray_icon_hook_path():
    return str(Path(__file__).with_name("pyinstaller_tray_icon_hook.py"))


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
