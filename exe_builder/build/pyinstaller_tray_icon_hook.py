"""Compatibility module for the tray icon runtime hook.

The standalone script passed to PyInstaller is materialized by tray_icon_support.
"""

from .tray_icon_hook_source import TRAY_ICON_HOOK_SOURCE

exec(compile(TRAY_ICON_HOOK_SOURCE, __file__, "exec"))
