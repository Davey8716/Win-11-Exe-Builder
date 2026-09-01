import os


def build_path_hover_text(raw_text, help_text="", include_help=False):
    raw_text = raw_text.strip()
    if not raw_text:
        return None

    full_path = os.path.normpath(raw_text)
    if include_help and help_text:
        return f"{full_path}\n\n{help_text.strip()}"

    return full_path
