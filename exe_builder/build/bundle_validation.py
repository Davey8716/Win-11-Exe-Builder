
import os
import subprocess

INVALID_EXE_CHARS = set('<>:"/\\|?*')
CREATE_NO_WINDOW = 0x08000000

def validate_bundle_inputs(app):
    """
    Validate that the current app state is safe for running PyInstaller.

    Returns:
        (True, None) if validation passes
        (False, "error message") if validation fails
    """

    # ---------------------------------------------------------
    # 1. Entry script
    # ---------------------------------------------------------
    entry = getattr(app, "entry_script", "") or ""
    entry = os.path.normpath(entry) if entry else ""

    if not entry:
        return False, "No entry script selected."

    if not os.path.isfile(entry):
        return False, "Entry script does not exist."

    if not entry.lower().endswith(".py"):
        return False, "Entry script must be a .py file."

    # ---------------------------------------------------------
    # 2. Python interpreter
    # ---------------------------------------------------------
    python = getattr(app, "python_interpreter_path", "").strip()

    if not python:
        return False, "Python interpreter not set."

    if not os.path.isfile(python):
        return False, "Python interpreter path is invalid."

    try:
        result = subprocess.run(
            [python, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            creationflags=CREATE_NO_WINDOW
        )
    except Exception:
        return False, "Python interpreter could not be executed."

    if result.returncode != 0:
        return False, "Python interpreter failed to run."

    # ---------------------------------------------------------
    # 3. Output directory
    # ---------------------------------------------------------
    output_dir = getattr(app, "output_path", "") or ""
    output_dir = os.path.normpath(output_dir) if output_dir else ""

    if not output_dir:
        return False, "Output folder not set."

    if not os.path.isdir(output_dir):
        return False, "Output folder does not exist."

    # ---------------------------------------------------------
    # 4. EXE name
    # ---------------------------------------------------------
    exe_name = getattr(app, "exe_name", "").strip()

    if not exe_name:
        return False, "EXE name is empty."

    if exe_name.endswith(" "):
        return False, "EXE name cannot end with a space."

    if any(ch in INVALID_EXE_CHARS for ch in exe_name):
        return False, (
            "EXE name contains invalid characters:\n"
            "< > : \" / \\ | ? *"
        )

    # ---------------------------------------------------------
    # 5. Icon (optional)
    # ---------------------------------------------------------
    icon = getattr(app, "icon_path", "") or ""
    icon = os.path.normpath(icon) if icon else ""

    if icon:
        if not os.path.isfile(icon):
            return False, "Icon file does not exist."

        if not icon.lower().endswith(".ico"):
            return False, "Icon must be a .ico file."

    # ---------------------------------------------------------
    # All checks passed
    # ---------------------------------------------------------
    return True, None
