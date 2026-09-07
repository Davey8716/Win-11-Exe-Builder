"""Launch installed Python without inheriting the frozen builder's DLL paths."""

import ctypes
import os
import sys
import threading
from contextlib import contextmanager

_launch_lock = threading.RLock()


@contextmanager
def external_python_environment():
    env = os.environ.copy()
    bundle = getattr(sys, "_MEIPASS", None)
    if not getattr(sys, "frozen", False) or not bundle or sys.platform != "win32":
        yield env
        return

    bundle = os.path.normcase(os.path.abspath(bundle))

    def bundled_path(value):
        value = os.path.normcase(os.path.abspath(value.strip('"')))
        return value == bundle or value.startswith(bundle + os.sep)

    env["PATH"] = os.pathsep.join(
        part for part in env.get("PATH", "").split(os.pathsep)
        if not part or not bundled_path(part)
    )
    # SetDllDirectory affects child processes as well as the current process.
    # Restore the exact previous value immediately after creating the child.
    with _launch_lock:
        kernel32 = ctypes.windll.kernel32
        size = kernel32.GetDllDirectoryW(0, None)
        previous = ctypes.create_unicode_buffer(size + 1)
        kernel32.GetDllDirectoryW(len(previous), previous)
        if not kernel32.SetDllDirectoryW(None):
            raise ctypes.WinError()
        try:
            yield env
        finally:
            if not kernel32.SetDllDirectoryW(previous.value or None):
                raise ctypes.WinError()
