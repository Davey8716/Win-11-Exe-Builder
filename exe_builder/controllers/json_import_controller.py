import json, os
from PySide6.QtCore import QObject, QEvent


class JsonImportController(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app

    # -------------------------------
    # Attach to BOTH combo boxes
    # -------------------------------
    def attach(self):
        self.app.recent_folder_dropdown.setAcceptDrops(True)
        self.app.select_recent_icons.setAcceptDrops(True)

        self.app.recent_folder_dropdown.installEventFilter(self)
        self.app.select_recent_icons.installEventFilter(self)

        self.app.select_interpreter.setAcceptDrops(True)
        self.app.select_interpreter.installEventFilter(self)

    # -------------------------------
    # Event filter (shared for both)
    # -------------------------------
    def eventFilter(self, obj, event):
        if event.type() == QEvent.DragEnter:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
                return True

        if event.type() == QEvent.Drop:
            urls = event.mimeData().urls()
            if not urls:
                return True

            path = urls[0].toLocalFile()

            if path.lower().endswith(".json"):
                self.load_json(path)

            return True

        return super().eventFilter(obj, event)

    # -------------------------------
    # Core loader (single source)
    # -------------------------------
    def load_json(self, path):
        app = self.app

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print("JSON load failed:", e)
            return

        # optional safety
        data["recent_scripts"] = [
            p for p in data.get("recent_scripts", [])
            if os.path.isfile(p)
        ]

        data["recent_icons"] = [
            p for p in data.get("recent_icons", [])
            if os.path.exists(p)
        ]

        data["python_interpreter_path"] = (
            data.get("python_interpreter_path", "")
            if os.path.isfile(data.get("python_interpreter_path", ""))
            else ""
        )

        # 🔑 overwrite state
        app.state_data = data

        state_path = app.state_ctrl._state_file_path()
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("State overwrite failed:", e)

        # 🔑 sync BOTH dropdowns
        app.recent_controller.populate_recent_dropdown()
        app.recent_controller.populate_recent_icons_dropdown()
        app.recent_controller.populate_recent_interpreters_dropdown()


        # 🔑 restore selections
        if data.get("last_script_path"):
            app.file_pickers._apply_selected_entry(data["last_script_path"])

        if data.get("last_icon_path"):
            app.file_pickers._apply_selected_icon(data["last_icon_path"])

        if data.get("python_interpreter_path"):
            path = data["python_interpreter_path"]

            app.python_interpreter_path = path
            app.python_path = path

            app.python_entry_input.set_display_path(path)

        if data.get("datetime_format"):
            app.datetime_format = data["datetime_format"]
            for i in range(app.date_time_dropdown.count()):
                if app.date_time_dropdown.itemData(i) == data["datetime_format"]:
                    app.date_time_dropdown.setCurrentIndex(i)
                    break

        # -------------------------------
        # Restore script correctly
        # -------------------------------
        script_path = data.get("last_script_path", "")

        if script_path and os.path.isfile(script_path):
            script_path = os.path.normpath(script_path)

            app.entry_script = script_path
            app.script_path = script_path
            app.project_root = os.path.dirname(script_path)
            app.script_path_input.set_display_path(script_path)
            app.project_root = os.path.dirname(path)
        app.state_ctrl.save_state()
        app.validator.validation_status_message()
        self.app.validator.update_ui_state()
        
