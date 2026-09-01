import time
import os, json
from PySide6.QtWidgets import QMessageBox, QDialogButtonBox
from PySide6.QtCore import Qt
from ..ui.styles import (
    Colors,
    RECENT_DELETE_MESSAGE_BOX_STYLE,
    apply_native_title_bar_style,
)
from ..ui.ui_highlights import flash_add_highlight, flash_delete_highlight

MAX_RECENTS = 50
DELETE_CONFIRMATION_PATH_WRAP_WIDTH = 58

def _title_case_recent_part(value, preserve_extension=False):
    if not value:
        return value

    if preserve_extension:
        stem, extension = os.path.splitext(value)
        if stem:
            return f"{stem.title()}{extension}"

    return value.title()


def _recent_display_label(index, parent, name):
    display_name = _title_case_recent_part(name, preserve_extension=True)

    if parent:
        display_parent = _title_case_recent_part(parent)
        return f"{index}. {display_parent}\\{display_name}"

    return f"{index}. {display_name}"


def _split_path_for_delete_confirmation(path):
    path = os.path.normpath(path)
    drive, remainder = os.path.splitdrive(path)
    root = ""

    while remainder.startswith(("\\", "/")):
        root += remainder[0]
        remainder = remainder[1:]

    parts = [part for part in remainder.replace("/", "\\").split("\\") if part]
    prefix = f"{drive}{root}"

    if prefix and parts:
        parts[0] = f"{prefix}{parts[0]}"
    elif prefix:
        parts = [prefix]

    return parts


def _wrap_delete_confirmation_path(path, max_line_length=DELETE_CONFIRMATION_PATH_WRAP_WIDTH):
    if not path:
        return ""

    parts = _split_path_for_delete_confirmation(path)
    if not parts:
        return os.path.normpath(path)

    lines = []
    current = parts[0]

    for part in parts[1:]:
        candidate = f"{current}\\{part}"
        if len(candidate) <= max_line_length:
            current = candidate
            continue

        lines.append(current)
        current = part

    lines.append(current)

    wrapped_lines = []
    for line in lines:
        if len(line) <= max_line_length:
            wrapped_lines.append(line)
            continue

        while len(line) > max_line_length:
            wrapped_lines.append(line[:max_line_length])
            line = line[max_line_length:]
        if line:
            wrapped_lines.append(line)

    return "\n".join(wrapped_lines)


class RecentController:
    def __init__(self, app):
        self.app = app

    def _show_recent_delete_confirmation(
        self,
        title,
        message,
        style_native_title_bar=True,
    ):
        dialog = QMessageBox(self.app)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        dialog.setIcon(QMessageBox.NoIcon)
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dialog.setDefaultButton(QMessageBox.No)
        dialog.setStyleSheet(RECENT_DELETE_MESSAGE_BOX_STYLE)
        dialog.setWindowFlags(
            (dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            | Qt.MSWindowsFixedSizeDialogHint
        )

        if style_native_title_bar:
            apply_native_title_bar_style(
                dialog,
                caption=Colors.PANEL_BG,
                border=Colors.PANEL_BG,
            )

        button_box = dialog.findChild(QDialogButtonBox)
        if button_box is not None:
            button_box.setCenterButtons(True)

        return dialog.exec() == QMessageBox.Yes

    def _confirm_delete_recent_item(self, title, path):
        formatted_path = _wrap_delete_confirmation_path(path)
        return self._show_recent_delete_confirmation(
            title,
            f"Are you sure you want to remove:\n\n{formatted_path}",
        )

    def on_recent_interpreter_selected(self, index):
        app = self.app
        if index <= 0:
            return

        path = app.select_interpreter.currentData()

        if not path:
            return

        path = os.path.abspath(os.path.normpath(path))
        app.interpreter_user_cleared = False

        print("Selected:", path)

        # 🔑 APPLY DIRECTLY (same pattern as script/icon)
        app.python_interpreter_path = path
        app.python_path = path

        self.add_recent_interpreter(path)  # ← ADD THIS


        self.app.validator.update_ui_state()
        self.app.validator.validation_status_message()

        self.app.python_entry_input.set_display_path(self.app.python_interpreter_path)
        self.app.select_interpreter.setCurrentIndex(0)
        flash_add_highlight(
            getattr(app, "interpreter_btn", None),
            getattr(app, "python_entry_input", None),
        )
        app.state_ctrl.save_state()
        
    def add_recent_interpreter(self, path):
        app = self.app
        ap = os.path.abspath(os.path.normpath(path)) if path else ""
        if not ap:
            return

        state_path = app.state_ctrl._state_file_path()

        try:
            if os.path.isfile(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}

        lst = data.get("recent_interpreters", [])

        if ap in lst:
            lst.remove(ap)

        lst.insert(0, ap)
        lst = lst[:MAX_RECENTS]

        data["recent_interpreters"] = lst

        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Recent interpreters save error:", e)

        app.state_data = data
        self.populate_recent_interpreters_dropdown()
        self.app.validator.update_ui_state()
        self.app.validator.validation_status_message()

    def populate_recent_interpreters_dropdown(self):
        app = self.app

        def _abs(p):
            return os.path.abspath(os.path.normpath(p)) if p else ""

        app.select_interpreter.blockSignals(True)
        app.select_interpreter.clear()
        
        app.select_interpreter.addItem("Select Recent Interpreter")
        model = app.select_interpreter.model()
        item = model.item(0)
        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
    
        state_path = app.state_ctrl._state_file_path()

        try:
            if os.path.isfile(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}

        # paths = sorted(
        #     data.get("recent_interpreters", []),
        #     key=lambda p: (
        #         os.path.basename(os.path.dirname(p)).lower(),
        #         os.path.basename(p).lower()
        #     )
        # )

        raw_paths = data.get("recent_interpreters", [])

        # 🔑 CLEAN STALE ENTRIES
        valid_paths = [
            os.path.abspath(os.path.normpath(p))
            for p in raw_paths
            if p and os.path.isfile(os.path.abspath(os.path.normpath(p)))
        ]

        # 🔑 WRITE BACK CLEANED LIST
        if len(valid_paths) != len(raw_paths):
            data["recent_interpreters"] = valid_paths
            try:
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            except:
                pass

        # 🔑 USE CLEAN LIST
        paths = sorted(
            valid_paths,
            key=lambda p: (
                os.path.basename(os.path.dirname(p)).lower(),
                os.path.basename(p).lower()
            )
        )

        current = os.path.abspath(os.path.normpath(getattr(app, "python_interpreter_path", "") or ""))

        if current and current not in valid_paths:
            if hasattr(app, "ui_handlers"):
                app.ui_handlers.clear_interpreter_path()

        seen = set()

        index = 1

        for p in paths:
            ap = _abs(p)

            if not ap:
                continue
            if not os.path.isfile(ap):
                continue
            if ap in seen:
                continue

            seen.add(ap)

            name = os.path.basename(ap)
            parent = os.path.basename(os.path.dirname(ap))

            display = _recent_display_label(index, parent, name)

            app.select_interpreter.addItem(display, ap)
            index += 1
        

        app.select_interpreter.blockSignals(False)
        self.app.validator.update_ui_state()
        self.app.validator.validation_status_message()

    def interpreter_delete(self):
        app = self.app
        full_path = getattr(app, "python_interpreter_path", "") or ""

        if not full_path:
            return

        if not self._confirm_delete_recent_item("Delete Interpreter", full_path):
            return

        flash_delete_highlight(
            getattr(app, "python_delete_interpreter", None),
            getattr(app, "python_entry_input", None),
        )

        # 🔑 clear current if matching
        if os.path.abspath(os.path.normpath(full_path)) == os.path.abspath(os.path.normpath(getattr(app, "python_interpreter_path", ""))):
            if hasattr(app, "python_entry_input"):
                app.python_entry_input.clear()
            app.python_interpreter_path = ""
            app.python_path = ""

        state_path = app.state_ctrl._state_file_path()

        try:
            if os.path.isfile(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}

        lst = data.get("recent_interpreters", [])

        norm = os.path.abspath(os.path.normpath(full_path))
        lst = [p for p in lst if os.path.abspath(os.path.normpath(p)) != norm]

        data["recent_interpreters"] = lst
        app.state_data = data

        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        app.validator.validation_status_message()
        self.populate_recent_interpreters_dropdown()
        self.app.validator.update_ui_state()
        self.app.validator.validation_status_message()
        

    def all_interpreter_delete(self):
        app = self.app

        if not self._show_recent_delete_confirmation(
            "Delete All Interpreters",
            "Are you sure you want to delete ALL interpreters?",
        ):
            return

        flash_delete_highlight(
            getattr(app, "python_delete_all_interpreter", None),
            getattr(app, "python_entry_input", None),
        )

        state_path = app.state_ctrl._state_file_path()

        try:
            if os.path.isfile(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}

        data["recent_interpreters"] = []
        app.state_data = data

        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Delete all interpreters error:", e)

        # 🔑 clear current UI/state
        if hasattr(app, "python_entry_input"):
            app.python_entry_input.clear()

        app.python_interpreter_path = ""
        app.python_path = ""

        self.populate_recent_interpreters_dropdown()
        app.validator.validation_status_message()
        self.app.validator.update_ui_state()
        self.app.validator.validation_status_message()
       

    # Files ####################################################################################################################################################################################################################################################################################################################
    def add_recent_script(self, path):
        app = self.app
        ap = os.path.abspath(os.path.normpath(path)) if path else ""
        if not ap:
            return

        state_path = app.state_ctrl._state_file_path()

        try:
            if os.path.isfile(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}

        lst = data.get("recent_scripts", [])

        if ap in lst:
            lst.remove(ap)

        lst.insert(0, ap)
        lst = lst[:MAX_RECENTS]

        data["recent_scripts"] = lst

        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Recent scripts save error:", e)

        app.state_data = data
        self.populate_recent_dropdown() 
        self.app.validator.update_ui_state()
        self.app.validator.validation_status_message()
        
    def populate_recent_dropdown(self):
        app = self.app

        def _abs(p):
            return os.path.abspath(os.path.normpath(p)) if p else ""

        app.recent_folder_dropdown.blockSignals(True)
        app.recent_folder_dropdown.clear()
        
        app.recent_folder_dropdown.addItem("Select Recent File")
        model = app.recent_folder_dropdown.model()
        item = model.item(0)
        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
       
        state_path = app.state_ctrl._state_file_path()

        try:
            if os.path.isfile(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}

        # paths = sorted(
        #     data.get("recent_scripts", []),
        #     key=lambda p: (
        #         os.path.basename(os.path.dirname(p)).lower(),  # project folder
        #         os.path.basename(p).lower()                    # file name
        #     )
        # )

        raw_paths = data.get("recent_scripts", [])

        # 🔑 CLEAN STALE ENTRIES
        valid_paths = [
            os.path.abspath(os.path.normpath(p))
            for p in raw_paths
            if p and os.path.isfile(os.path.abspath(os.path.normpath(p)))
        ]

        # 🔑 WRITE BACK CLEANED LIST
        if len(valid_paths) != len(raw_paths):
            data["recent_scripts"] = valid_paths
            try:
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            except:
                pass

        # 🔑 USE CLEAN LIST
        paths = sorted(
            valid_paths,
            key=lambda p: (
                os.path.basename(os.path.dirname(p)).lower(),
                os.path.basename(p).lower()
            )
        )

        current = os.path.abspath(os.path.normpath(getattr(app, "entry_script", "") or ""))

        if current and current not in valid_paths:
            if hasattr(app, "ui_handlers"):
                app.ui_handlers.clear_script_path()

        seen = set()

        index = 1

        for p in paths:
            ap = _abs(p)

            if not ap:
                continue
            if not os.path.isfile(ap):
                continue
            if ap in seen:
                continue

            seen.add(ap)

            name = os.path.basename(ap)
            parent = os.path.basename(os.path.dirname(ap))

            display = _recent_display_label(index, parent, name)

            app.recent_folder_dropdown.addItem(display, ap)
            index += 1

        app.recent_folder_dropdown.blockSignals(False)
        self.app.validator.update_ui_state()
        self.app.validator.validation_status_message()
                
    def on_recent_file_selected(self, index):
        app = self.app
        if index <=0:
            return

        path = app.recent_folder_dropdown.currentData()

        if not path:
            return
        
        app.script_user_cleared = False

        path = os.path.abspath(os.path.normpath(path))

        print("Selected:", path)

        if hasattr(app, "file_pickers"):
            app.file_pickers._apply_selected_entry(path)
                    # ← add
        self.populate_recent_dropdown()    # ← add

        self.app.validator.update_ui_state()
        self.app.validator.validation_status_message()

        self.app.script_path_input.set_display_path(self.app.script_path)

    def confirm_delete_recent(self):
        app = self.app
        full_path = getattr(app, "entry_script", "") or getattr(app, "script_path", "")

        if not full_path:
            return

        if not self._confirm_delete_recent_item("Delete Recent File", full_path):
            return

        flash_delete_highlight(
            getattr(app, "delete_recent_folder", None),
            getattr(app, "script_path_input", None),
        )

        if os.path.abspath(os.path.normpath(full_path)) == os.path.abspath(os.path.normpath(getattr(app, "entry_script", ""))):
            app.script_path_input.clear()
            app.entry_script = None
            app.project_root = None
            app.script_path = ""

        state_path = app.state_ctrl._state_file_path()

        try:
            if os.path.isfile(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}

        lst = data.get("recent_scripts", [])

        norm = os.path.abspath(os.path.normpath(full_path))
        lst = [p for p in lst if os.path.abspath(os.path.normpath(p)) != norm]

        data["recent_scripts"] = lst
        app.state_data = data

        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        self.populate_recent_dropdown()
        app.validator.validation_status_message()
        self.app.validator.update_ui_state()
        
    def confirm_delete_all_folder(self):
        app = self.app

        if not self._show_recent_delete_confirmation(
            "Delete All Recent Files",
            "Are you sure you want to delete ALL recent files?",
        ):
            return

        flash_delete_highlight(
            getattr(app, "delete_all_folders", None),
            getattr(app, "script_path_input", None),
        )

        state_path = app.state_ctrl._state_file_path()

        try:
            if os.path.isfile(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}

        # 🔑 clear list
        data["recent_scripts"] = []

        app.state_data = data

        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Delete all recent scripts error:", e)

        # 🔑 clear UI + runtime state
        if hasattr(app, "script_path_input"):
            app.script_path_input.clear()
        app.entry_script = None
        app.project_root = None
        app.script_path = ""

        # 🔑 refresh dropdown
        self.populate_recent_dropdown()
        app.validator.validation_status_message()
        self.app.validator.update_ui_state()

    #========================================
    #================================ Icons
    #========================================
    def on_recent_icon_selected(self, index):
        app = self.app

        path = app.select_recent_icons.currentData()

        # 🔑 NO ICON → single source of truth
        if not path:
            if hasattr(app, "ui_handlers"):
                app.ui_handlers.clear_icon()
            return

        path = os.path.abspath(os.path.normpath(path))

        app.icon_user_cleared = False

        print("Selected:", path)

        if hasattr(app, "file_pickers"):
            app.file_pickers._apply_selected_icon(path)

        # 🔑 FULL SYNC
        app.state_ctrl.save_state()
        self.app.validator.validation_status_message()
        self.app.validator.update_ui_state()

        if hasattr(app, "icon_path_input"):
            app.icon_path_input.set_display_path(app.icon_path)
                                

    def add_recent_icon(self, path):
        app = self.app
        ap = os.path.abspath(os.path.normpath(path)) if path else ""
        if not ap:
            return

        state_path = app.state_ctrl._state_file_path()

        try:
            if os.path.isfile(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}

        lst = data.get("recent_icons", [])

        if ap in lst:
            lst.remove(ap)

        lst.insert(0, ap)
        lst = lst[:MAX_RECENTS]

        data["recent_icons"] = lst

        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Recent icons save error:", e)

        self.populate_recent_icons_dropdown()
        app.state_data = data
        self.app.validator.update_ui_state()
        
    def populate_recent_icons_dropdown(self):
        app = self.app

        def _abs(p):
            return os.path.abspath(os.path.normpath(p)) if p else ""

        app.select_recent_icons.blockSignals(True)
        app.select_recent_icons.clear()
    
        app.select_recent_icons.addItem("Select Recent Icon")
        app.select_recent_icons.addItem("No Icon", "")
        model = app.select_recent_icons.model()
        item = model.item(0)
        item.setFlags(item.flags() & ~Qt.ItemIsEnabled)

        state_path = app.state_ctrl._state_file_path()

        try:
            if os.path.isfile(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}

        # paths = sorted(
        #     data.get("recent_icons", []),
        #     key=lambda p: os.path.basename(p).lower()
        # )

        raw_paths = data.get("recent_icons", [])

        # 🔑 CLEAN STALE ENTRIES
        valid_paths = [
            os.path.abspath(os.path.normpath(p))
            for p in raw_paths
            if p and os.path.isfile(os.path.abspath(os.path.normpath(p)))
        ]

        # 🔑 WRITE BACK CLEANED LIST
        if len(valid_paths) != len(raw_paths):
            data["recent_icons"] = valid_paths
            try:
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            except:
                pass

        # 🔑 USE CLEAN LIST
        paths = sorted(
            valid_paths,
            key=lambda p: os.path.basename(p).lower()
        )

        current = os.path.abspath(os.path.normpath(getattr(app, "icon_path", "") or ""))

        if current and current not in valid_paths:
            if hasattr(app, "ui_handlers"):
                app.ui_handlers.clear_icon()

        seen = set()

        index = 1
            
        for p in paths:
            ap = _abs(p)

            if not ap:
                continue
            if not os.path.isfile(ap):
                continue
            if ap in seen:
                continue

            seen.add(ap)

            name = os.path.basename(ap)
            parent = os.path.basename(os.path.dirname(ap))

            display = _recent_display_label(index, parent, name)

            app.select_recent_icons.addItem(display, ap)
            index += 1


        app.select_recent_icons.blockSignals(False)
        self.app.validator.update_ui_state()
        
    def confirm_delete_recent_icon(self):
        app = self.app
        full_path = getattr(app, "icon_path", "") or ""

        if not full_path:
            return

        if not self._confirm_delete_recent_item("Delete Recent Icon", full_path):
            return

        flash_delete_highlight(
            getattr(app, "delete_recent_icons", None),
            getattr(app, "icon_path_input", None),
        )

        if os.path.abspath(os.path.normpath(full_path)) == os.path.abspath(os.path.normpath(getattr(app, "icon_path", ""))):
            app.icon_path_input.clear()
            app.icon_path = ""

        state_path = app.state_ctrl._state_file_path()

        try:
            if os.path.isfile(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}

        lst = data.get("recent_icons", [])

        norm = os.path.abspath(os.path.normpath(full_path))
        lst = [p for p in lst if os.path.abspath(os.path.normpath(p)) != norm]

        data["recent_icons"] = lst
        app.state_data = data

        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        self.populate_recent_icons_dropdown()
        app.validator.validation_status_message()
        self.app.validator.update_ui_state()
        
        
    def confirm_delete_all_icons(self):
        app = self.app

        if not self._show_recent_delete_confirmation(
            "Delete All Recent Icons",
            "Are you sure you want to delete ALL recent icons?",
        ):
            return

        flash_delete_highlight(
            getattr(app, "delete_all_icons", None),
            getattr(app, "icon_path_input", None),
        )

        state_path = app.state_ctrl._state_file_path()

        try:
            if os.path.isfile(state_path):
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
        except:
            data = {}

        data["recent_icons"] = []

        app.state_data = data

        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Delete all recent icons error:", e)

        if hasattr(app, "icon_path_input"):
            app.icon_path_input.clear()
        app.icon_path = ""

        self.populate_recent_icons_dropdown()
        app.validator.validation_status_message()
        self.app.validator.update_ui_state()
