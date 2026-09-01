import os
import sys


TRAY_ICON_BUNDLE_NAME = "_exe_builder_tray_icon.ico"
TRAY_ICON_ENV_VAR = "EXE_BUILDER_TRAY_ICON_PATH"


def _resolve_tray_icon_path():
    base_dir = os.path.dirname(getattr(sys, "executable", ""))
    meipass_dir = getattr(sys, "_MEIPASS", "")

    candidates = []
    for root in (
        meipass_dir,
        base_dir,
        os.path.join(base_dir, "_internal"),
    ):
        candidates.extend(_expanded_bundle_icon_candidates(root))

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate

    return ""


def _expanded_bundle_icon_candidates(base_dir):
    if not base_dir:
        return []

    bundle_path = os.path.join(base_dir, TRAY_ICON_BUNDLE_NAME)
    candidates = [bundle_path]
    if os.path.isdir(bundle_path):
        candidates.extend(
            sorted(
                os.path.join(bundle_path, name)
                for name in os.listdir(bundle_path)
                if name.lower().endswith(".ico")
            )
        )
    return candidates


def _install_pystray_icon_fallback():
    icon_path = _resolve_tray_icon_path()
    if not icon_path:
        return

    os.environ[TRAY_ICON_ENV_VAR] = icon_path

    try:
        import pystray
        from PIL import Image
    except Exception:
        return

    original_init = pystray.Icon.__init__
    if getattr(original_init, "_exe_builder_tray_patch", False):
        return

    def patched_init(self, name, icon=None, *args, **kwargs):
        if icon is None:
            try:
                icon = Image.open(icon_path)
            except Exception:
                pass

        return original_init(self, name, icon, *args, **kwargs)

    patched_init._exe_builder_tray_patch = True
    pystray.Icon.__init__ = patched_init


_install_pystray_icon_fallback()
