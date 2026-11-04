"""Derive and validate executable names from selected output folders."""
import ntpath
import re


def output_folder_name(path):
    path = (path or "").strip()
    if not path:
        return ""
    return ntpath.basename(ntpath.normpath(path))


def executable_name_error(name):
    if not name:
        return "Select an output folder with a usable name."
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if (name in {".", ".."} or name.endswith((" ", "."))
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
            or name.split(".")[0].upper() in reserved):
        return "Output folder name contains invalid characters or is a reserved Windows filename."
    return ""
