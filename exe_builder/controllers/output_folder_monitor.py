import os


OUTPUT_FOLDER_MONITOR_INTERVAL_MS = 2_000


class OutputFolderValidityMonitor:
    """Refresh output controls when their selected folders change on disk."""

    def __init__(self, app):
        self.app = app
        self.snapshot = self.current_state()

    @staticmethod
    def _path_state(field):
        path = field.text().strip()
        normalized = os.path.normcase(os.path.normpath(path)) if path else ""
        return normalized, bool(normalized and os.path.isdir(normalized))

    def current_state(self):
        build_controller = getattr(self.app, "build_controller", None)
        python_output_available = bool(
            build_controller
            and getattr(build_controller, "has_python_output", lambda: False)()
        )
        dotnet_controller = getattr(self.app, "dotnet_publish_controller", None)
        published_output_available = bool(
            dotnet_controller
            and getattr(dotnet_controller, "has_publish_output", lambda: False)()
        )
        return {
            "python": (*self._path_state(self.app.output_path_input), python_output_available),
            "dotnet": (*self._path_state(self.app.dotnet_output_input), published_output_available),
        }

    def refresh_if_changed(self):
        if getattr(self.app, "building", False):
            return

        current = self.current_state()
        previous = self.snapshot
        self.snapshot = current

        if current["python"] != previous["python"]:
            self.app.validator.update_ui_state()
        if current["dotnet"] != previous["dotnet"]:
            self.app.dotnet_publish_controller.refresh_ui()
