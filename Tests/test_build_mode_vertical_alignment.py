"""Check the sidebar workflow when switching build modes."""

import ctypes
import json
import os
import sys

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="The app uses Windows APIs")
def test_build_modes_use_sidebars_and_guided_python_steps(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QPushButton

    from exe_builder.controllers.activation_controller import ActivationController
    from exe_builder.build.build_cancellation import BuildCancellation
    from exe_builder.ui.styles import Colors, qcolor_name

    monkeypatch.setattr(ActivationController, "listen_for_activation", lambda self: None)
    monkeypatch.setattr(ctypes, "GetLastError", lambda: 0)
    from exe_builder.main import EXEBuilderApp

    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    window = EXEBuilderApp()

    try:
        build_options_dialog = window.build_options_dialog
        build_options_grid = build_options_dialog.layout().itemAt(0).layout()
        assert build_options_dialog.size().width() == 500
        assert build_options_dialog.size().height() == 220
        assert build_options_grid.horizontalSpacing() == 20
        assert build_options_grid.verticalSpacing() == 8
        assert build_options_grid.itemAtPosition(3, 0).widget() is window.open_app_data_btn
        assert build_options_grid.itemAtPosition(3, 1) is None
        close_font = window.build_options_close_btn.font()
        assert close_font.family() == "Rubik UI"
        assert close_font.pointSize() == 13
        assert close_font.bold()
        assert window.status_label.size().width() == 420
        assert window.status_label.size().height() == 75
        assert window.status_label.parentWidget().height() == 145
        assert window.status_label.parentWidget().width() == 450
        assert window.dotnet_status_label.size().height() == 75
        assert window.status_label.parentWidget().size() == (
            window.dotnet_status_label.parentWidget().size()
        )
        ready_message = (
            "Ready to build.\nThe output folder will open after building."
            "\nThis app will then close."
        )
        window.status_label.setPlainText(ready_message)
        app.processEvents()
        assert window.status_label.toPlainText() == ready_message
        assert window.status_label.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
        assert window.status_label.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
        assert window.dotnet_status_label.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
        assert window.dotnet_status_label.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff

        def horizontal_gap(left, right):
            left_edge = left.mapTo(window, QPoint(left.width(), 0)).x()
            right_edge = right.mapTo(window, QPoint(0, 0)).x()
            return right_edge - left_edge

        def assert_selector_row(*widgets):
            assert all(widget.height() == 35 for widget in widgets)
            assert [
                horizontal_gap(left, right) for left, right in zip(widgets, widgets[1:])
            ] == [4] * (len(widgets) - 1)

        def assert_path_row(field, reset):
            assert horizontal_gap(field, reset) == 3
            field_center = field.mapTo(window, QPoint(0, field.height() // 2)).y()
            reset_center = reset.mapTo(window, QPoint(0, reset.height() // 2)).y()
            assert abs(field_center - reset_center) <= 1

        window.show()
        window.set_build_mode("python", save=False)
        app.processEvents()
        assert window.size().width() == 860
        assert window.size().height() == 840
        python_title_center = window.title_label.mapTo(
            window, QPoint(window.title_label.width() // 2, 0)
        ).x()
        python_content_center = window.python_section_stack.mapTo(
            window, QPoint(window.python_section_stack.width() // 2, 0)
        ).x()
        assert abs(python_title_center - python_content_center) <= 1
        assert window.build_options_btn.text() == "☰"
        assert window.build_options_btn.parentWidget() is window.title_options_slot
        assert window.python_mode_selector.layout().count() == 2
        assert window.python_section_nav.item(0).text() == "Environment Sync"
        assert window.python_section_nav.count() == 6
        assert window.python_section_stack.currentIndex() == 0
        window.python_section_nav.setCurrentRow(5)
        app.processEvents()
        python_actions_center = (
            window.build_btn.mapTo(window, QPoint(window.build_btn.width(), 0)).x()
            + window.python_open_output_btn.mapTo(window, QPoint(0, 0)).x()
        ) // 2
        python_panel_center = window.status_label.parentWidget().mapTo(
            window, QPoint(window.status_label.parentWidget().width() // 2, 0)
        ).x()
        assert abs(python_actions_center - python_panel_center) <= 1
        assert window.python_mode_btn.parentWidget() is window.python_mode_selector
        assert window.dotnet_mode_btn.parentWidget() is window.python_mode_selector
        for field in (
            window.python_entry_input,
            window.icon_path_input,
            window.script_path_input,
            window.output_path_input,
        ):
            assert field.height() >= field.fontMetrics().lineSpacing() * 2
        assert window.interpreter_frame.height() < window.output_frame.height()
        assert window.output_frame.height() < 200
        for index, widgets in (
            (1, (window.interpreter_btn, window.select_interpreter,
                 window.python_delete_interpreter, window.python_delete_all_interpreter)),
            (2, (window.icon_btn, window.select_recent_icons,
                 window.delete_recent_icons, window.delete_all_icons)),
            (3, (window.folder_btn, window.recent_folder_dropdown,
                 window.delete_recent_folder, window.delete_all_folders)),
            (4, (window.output_btn, window.date_time_dropdown)),
        ):
            window.python_section_stack.setCurrentIndex(index)
            app.processEvents()
            assert_selector_row(*widgets)
        for index, field, reset in (
            (1, window.python_entry_input, window.interpreter_refresh_btn),
            (2, window.icon_path_input, window.icon_clear_btn),
            (3, window.script_path_input, window.script_clear_btn),
            (4, window.output_path_input, window.output_refresh_btn),
        ):
            window.python_section_stack.setCurrentIndex(index)
            app.processEvents()
            assert_path_row(field, reset)
        window.python_section_stack.setCurrentIndex(4)
        app.processEvents()
        output_bottom = window.output_frame.mapTo(
            window, QPoint(0, window.output_frame.height())
        ).y()
        for widget in (
            window.appened_py_version,
            window.output_btn,
            window.date_time_dropdown,
            window.output_path_input,
            window.output_refresh_btn,
            window.exe_name_input,
            window.refresh_btn,
        ):
            assert widget.mapTo(window, QPoint(0, widget.height())).y() <= output_bottom
        window.python_section_stack.setCurrentIndex(0)
        build_page = window.python_section_stack.widget(5)
        assert window.build_summary_title_frame.parentWidget() is build_page
        assert window.build_summary_title.parentWidget() is window.build_summary_title_frame
        assert window.build_summary_frame.width() == 585
        assert all(
            label.width() >= 96 for label in window.build_summary_labels.values()
        )
        interpreter_summary_label = window.build_summary_labels["interpreter"]
        assert (
            interpreter_summary_label.fontMetrics().horizontalAdvance(
                interpreter_summary_label.text()
            )
            <= interpreter_summary_label.width()
        )
        assert window.build_summary_title.font().pointSize() == 15
        assert qcolor_name(Colors.TEXT_LIGHT) in window.build_summary_title_frame.styleSheet()
        assert all(
            label.font().pointSize() == 11
            for label in window.build_summary_labels.values()
        )
        assert all(
            value.font().pointSize() == 11
            for value in window.build_summary_values.values()
        )
        for index, keys in ((2, {"interpreter"}), (3, {"interpreter", "icon"}),
                            (4, {"interpreter", "icon", "file"})):
            title, frame, labels, values = window.python_selection_summaries[
                ("Icons", "File", "Output")[index - 2]
            ]
            assert title.parentWidget() is window.python_section_stack.widget(index)
            assert frame.parentWidget() is window.python_section_stack.widget(index)
            assert set(labels) == set(values) == keys
            assert frame.width() == 585
            assert all(label.width() >= 96 for label in labels.values())
            if "interpreter" in labels:
                interpreter_label = labels["interpreter"]
                assert (
                    interpreter_label.fontMetrics().horizontalAdvance(
                        interpreter_label.text()
                    )
                    <= interpreter_label.width()
                )
            assert title.layout().itemAt(1).widget().font().pointSize() == 15
            assert all(label.font().pointSize() == 11 for label in labels.values())
            for value in values.values():
                assert value.font().pointSize() == 11
                assert value.wordWrap()
                assert value.height() >= value.fontMetrics().lineSpacing() * 2
                assert qcolor_name(Colors.TEXT_LIGHT) in value.styleSheet()
            assert qcolor_name(Colors.TEXT_LIGHT) in title.styleSheet()
            assert all(qcolor_name(Colors.TEXT_LIGHT) in label.styleSheet() for label in labels.values())
        assert window.python_selection_summaries["Icons"][3]["interpreter"].text() == "Not selected"
        assert window.python_selection_summaries["File"][3]["icon"].text() == "No icon"
        assert window.build_summary_values["interpreter"].font().bold()
        assert qcolor_name(Colors.TEXT_LIGHT) in window.build_summary_values["interpreter"].styleSheet()
        assert all(
            qcolor_name(Colors.TEXT_LIGHT) in label.styleSheet()
            for label in window.build_summary_labels.values()
        )
        assert all(
            qcolor_name(Colors.TEXT_LIGHT) in value.styleSheet()
            for value in window.build_summary_values.values()
        )
        assert window.build_summary_values["interpreter"].wordWrap()
        assert window.build_summary_values["interpreter"].height() >= (
            window.build_summary_values["interpreter"].fontMetrics().lineSpacing() * 2
        )
        assert window.build_summary_values["interpreter"].textInteractionFlags() == Qt.NoTextInteraction
        assert window.build_summary_values["interpreter"].focusPolicy() == Qt.NoFocus
        assert qcolor_name(Colors.TEXT_LIGHT) in window.build_summary_values["icon"].styleSheet()
        assert window.build_summary_values["icon"].text() == "(No icon needed to build)"
        assert window.build_summary_values["python_version"].text() == "Not appended"
        assert window.build_summary_values["datetime"].text() == "Not appended"
        window.python_interpreter_path = r"C:\Python314\python.exe"
        window.appened_py_version.setChecked(True)
        assert window.build_summary_values["python_version"].text() == "py3.14"
        window.build_controller._get_datetime_timestamp_suffix = lambda: "2026-05-19_12-34"
        window.date_time_dropdown.setCurrentIndex(
            window.date_time_dropdown.findData("%Y-%m-%d_%H-%M")
        )
        assert window.build_summary_values["datetime"].text() == "ISO_2026-05-19_12-34"
        window.date_time_dropdown.setCurrentIndex(
            window.date_time_dropdown.findText("Build All ISO Date/Time Outputs")
        )
        assert (
            window.build_summary_values["datetime"].text().replace("\u200b", "")
            == "Build All ISO Date/Time Outputs"
        )
        for index, label in ((1, "Continue to icons"), (3, "Continue to output")):
            assert label in [
                button.text()
                for button in window.python_section_stack.widget(index).findChildren(QPushButton)
            ]
        assert window.python_section_nav.geometry().right() < window.python_section_stack.geometry().left()
        assert not bool(window.python_section_nav.item(1).flags() & Qt.ItemIsEnabled)
        assert window.interpreter_continue_btn.isHidden()
        assert window.file_continue_btn.isHidden()
        assert window.output_continue_btn.isHidden()
        for button in (
            window.interpreter_continue_btn,
            window.icon_continue_btn,
            window.file_continue_btn,
            window.output_continue_btn,
        ):
            assert button.width() == 280
            assert button.height() == 42
            assert button.font().bold()

        continue_sync = next(
            button for button in window.python_section_stack.widget(0).findChildren(QPushButton)
            if button.text() == "Continue without syncing"
        )
        continue_sync.click()
        assert window.python_section_stack.currentIndex() == 1
        window.python_entry_input.setText("C:/Python/python.exe")
        assert window.python_section_stack.currentIndex() == 1
        assert not window.interpreter_continue_btn.isHidden()
        assert bool(window.python_section_nav.item(2).flags() & Qt.ItemIsEnabled)
        assert window.build_summary_values["interpreter"].text().replace("\u200b", "") == "C:/Python/python.exe"
        assert window.python_selection_summaries["Icons"][3]["interpreter"].text().replace("\u200b", "") == "C:/Python/python.exe"
        assert window.python_selection_summaries["Output"][3]["interpreter"].text().replace("\u200b", "") == "C:/Python/python.exe"
        window.icon_path_input.setText("C:/icons/app.ico")
        assert bool(window.python_section_nav.item(3).flags() & Qt.ItemIsEnabled)
        assert window.build_summary_values["icon"].text().replace("\u200b", "") == "C:/icons/app.ico"
        assert qcolor_name(Colors.TEXT_LIGHT) in window.build_summary_labels["icon"].styleSheet()
        assert qcolor_name(Colors.TEXT_LIGHT) in window.build_summary_values["icon"].styleSheet()
        assert window.python_selection_summaries["File"][3]["icon"].text().replace("\u200b", "") == "C:/icons/app.ico"
        assert window.python_selection_summaries["Output"][3]["icon"].toolTip() == ""
        window.script_path_input.setText("C:/project/main.py")
        assert bool(window.python_section_nav.item(4).flags() & Qt.ItemIsEnabled)
        assert window.build_summary_values["file"].text().replace("\u200b", "") == "C:/project/main.py"
        assert window.python_selection_summaries["Output"][3]["file"].text().replace("\u200b", "") == "C:/project/main.py"
        long_script_path = "C:\\" + "very-long-folder-name\\" * 12 + "main.py"
        window.script_path_input.setText(long_script_path)
        displayed_path = window.build_summary_values["file"].text()
        assert displayed_path.replace("\u200b", "") == long_script_path
        assert "\\\u200b" in displayed_path
        selection_summary_path = window.python_selection_summaries["Output"][3]["file"].text()
        assert selection_summary_path.replace("\u200b", "") == long_script_path
        assert "\\\u200b" in selection_summary_path
        window.python_section_nav.setCurrentRow(1)
        next_button = next(
            button for button in window.python_section_stack.widget(1).findChildren(QPushButton)
            if button.text() == "Continue to icons"
        )
        next_button.click()
        assert window.python_section_stack.currentIndex() == 2
        window.ui_handlers.clear_icon()
        assert window.icon_continue_btn.text() == "Use no icon and continue"
        assert window.python_selection_summaries["File"][3]["icon"].text() == "No icon"
        assert window.python_selection_summaries["Output"][3]["icon"].text() == "No icon"
        window.icon_path_input.setText("C:/icons/app.ico")
        assert window.icon_continue_btn.text() == "Continue to file"
        assert window.icon_path_input.text() == "C:/icons/app.ico"
        assert window.python_section_stack.currentIndex() == 2
        window.icon_continue_btn.click()
        assert window.python_section_stack.currentIndex() == 3
        continue_file = next(
            button for button in window.python_section_stack.widget(3).findChildren(QPushButton)
            if button.text() == "Continue to output"
        )
        continue_file.click()
        assert window.python_section_stack.currentIndex() == 4
        assert window.output_continue_btn.isHidden()

        window.set_build_mode("dotnet", save=False)
        app.processEvents()
        assert window.size().width() == 850
        assert window.size().height() == 866
        for field in (
            window.dotnet_icon_input,
            window.dotnet_project_input,
            window.dotnet_output_input,
        ):
            assert field.height() >= field.fontMetrics().lineSpacing() * 2
        for index, widgets in (
            (0, (window.dotnet_icon_select_btn, window.dotnet_recent_icons,
                 window.dotnet_icon_delete_btn, window.dotnet_icon_delete_all_btn)),
            (1, (window.dotnet_project_select_btn, window.dotnet_recent_projects,
                 window.dotnet_project_delete_btn, window.dotnet_project_delete_all_btn)),
            (2, (window.dotnet_output_select_btn, window.dotnet_date_time_dropdown)),
        ):
            window.dotnet_section_stack.setCurrentIndex(index)
            app.processEvents()
            assert_selector_row(*widgets)
        for index, field, reset in (
            (0, window.dotnet_icon_input, window.dotnet_icon_reset_btn),
            (1, window.dotnet_project_input, window.dotnet_project_reset_btn),
            (2, window.dotnet_output_input, window.dotnet_output_reset_btn),
        ):
            window.dotnet_section_stack.setCurrentIndex(index)
            app.processEvents()
            assert_path_row(field, reset)
        window.dotnet_section_stack.setCurrentIndex(0)
        dotnet_title_center = window.dotnet_mode_title.mapTo(
            window, QPoint(window.dotnet_mode_title.width() // 2, 0)
        ).x()
        dotnet_content_center = window.dotnet_section_stack.mapTo(
            window, QPoint(window.dotnet_section_stack.width() // 2, 0)
        ).x()
        assert abs(dotnet_title_center - dotnet_content_center) <= 1
        assert window.build_options_btn.parentWidget() is window.dotnet_title_options_slot
        assert window.dotnet_mode_selector.layout().count() == 2
        assert window.dotnet_section_nav.count() == 4
        assert window.dotnet_python_mode_btn.parentWidget() is window.dotnet_mode_selector
        assert window.dotnet_mode_sidebar_btn.parentWidget() is window.dotnet_mode_selector
        assert window.dotnet_section_nav.geometry().right() < window.dotnet_section_stack.geometry().left()
        assert window.dotnet_selection_summaries["File Select"][3]["icon"].text() == "No icon"
        assert window.dotnet_selection_summaries["Output Select"][3]["file"].text() == "Not selected"
        assert window.dotnet_selection_summaries["File Select"][0].parentWidget() is window.dotnet_section_stack.widget(1)
        assert window.dotnet_selection_summaries["Output Select"][0].parentWidget() is window.dotnet_section_stack.widget(2)
        assert window.dotnet_build_title_frame.parentWidget() is window.dotnet_section_stack.widget(3)
        assert window.dotnet_build_summary_frame.width() == 575
        assert all(
            label.width() >= 85 for label in window.dotnet_build_summary_labels.values()
        )
        assert window.dotnet_build_summary_title.font().pointSize() == 15
        assert qcolor_name(Colors.TEXT_LIGHT) in window.dotnet_build_summary_title_frame.styleSheet()
        assert all(
            label.font().pointSize() == 11
            for label in window.dotnet_build_summary_labels.values()
        )
        assert all(
            value.font().pointSize() == 11
            for value in window.dotnet_build_summary_values.values()
        )
        assert (
            window.dotnet_build_summary_values["datetime"].text()
            == "No Date Time Appended"
        )
        window.dotnet_date_time_dropdown.setCurrentIndex(
            window.dotnet_date_time_dropdown.findData("%d-%m-%Y")
        )
        assert window.dotnet_build_summary_values["datetime"].text() == "UK | DD-MM-YYYY"
        window.dotnet_date_time_dropdown.setCurrentIndex(
            window.dotnet_date_time_dropdown.findText("Build All USA Date/Time Outputs")
        )
        assert (
            window.dotnet_build_summary_values["datetime"].text().replace("\u200b", "")
            == "Build All USA Date/Time Outputs"
        )
        for title, frame, labels, values in window.dotnet_selection_summaries.values():
            assert title.layout().itemAt(1).widget().font().pointSize() == 15
            assert frame.width() == 575
            assert all(label.width() == 85 for label in labels.values())
            assert all(label.font().pointSize() == 11 for label in labels.values())
            for value in values.values():
                assert value.font().pointSize() == 11
                assert value.height() >= value.fontMetrics().lineSpacing() * 2
                assert qcolor_name(Colors.TEXT_LIGHT) in value.styleSheet()
            assert qcolor_name(Colors.TEXT_LIGHT) in title.styleSheet()
            assert all(qcolor_name(Colors.TEXT_LIGHT) in label.styleSheet() for label in labels.values())
        assert all(
            qcolor_name(Colors.TEXT_LIGHT) in label.styleSheet()
            for label in window.dotnet_build_summary_labels.values()
        )
        assert all(
            qcolor_name(Colors.TEXT_LIGHT) in value.styleSheet()
            for value in window.dotnet_build_summary_values.values()
        )
        window.dotnet_icon_input.setText("C:/icons/dotnet.ico")
        assert window.dotnet_selection_summaries["File Select"][3]["icon"].text().replace("\u200b", "") == "C:/icons/dotnet.ico"
        assert window.dotnet_selection_summaries["Output Select"][3]["icon"].text().replace("\u200b", "") == "C:/icons/dotnet.ico"
        window.dotnet_project_input.setText("C:/project/app.csproj")
        assert window.dotnet_selection_summaries["Output Select"][3]["file"].text().replace("\u200b", "") == "C:/project/app.csproj"
        window.dotnet_icon_input.clear()
        assert window.dotnet_selection_summaries["File Select"][3]["icon"].text() == "No icon"
        assert window.dotnet_selection_summaries["Output Select"][3]["icon"].text() == "No icon"
        window.set_build_mode("python", save=False)
        app.processEvents()
        assert window.size().width() == 860
        assert window.size().height() == 840
        assert window.python_section_stack.currentIndex() == 4

        window.build_cancellation = BuildCancellation(window, window)
        window.building = True
        window.validation_controller.update_ui_state()
        assert not window.python_section_nav.isEnabled()
        assert not window.dotnet_section_nav.isEnabled()
        assert "item:selected:disabled" in window.python_section_nav.styleSheet()
        for button in (window.python_mode_btn, window.dotnet_mode_btn,
                       window.dotnet_python_mode_btn, window.dotnet_mode_sidebar_btn):
            assert not button.isEnabled()
        QTest.mouseClick(
            window.python_section_nav.viewport(), Qt.LeftButton,
            pos=window.python_section_nav.visualItemRect(window.python_section_nav.item(0)).center(),
        )
        assert window.python_section_nav.currentRow() == 4
        window.building = False
        window.validation_controller.update_ui_state()
        assert window.python_section_nav.isEnabled()
        assert window.dotnet_section_nav.isEnabled()
        assert window.dotnet_mode_btn.isEnabled()
        assert all(bool(window.python_section_nav.item(i).flags() & Qt.ItemIsEnabled)
                   for i in range(5))
        assert not bool(window.python_section_nav.item(5).flags() & Qt.ItemIsEnabled)

        window.set_build_mode("dotnet", save=False)
        window.dotnet_section_nav.setCurrentRow(2)
        window.building = True
        window.dotnet_publish_controller.refresh_ui()
        assert not window.python_section_nav.isEnabled()
        assert not window.dotnet_section_nav.isEnabled()
        for button in (window.python_mode_btn, window.dotnet_mode_btn,
                       window.dotnet_python_mode_btn, window.dotnet_mode_sidebar_btn):
            assert not button.isEnabled()
        QTest.mouseClick(
            window.dotnet_section_nav.viewport(), Qt.LeftButton,
            pos=window.dotnet_section_nav.visualItemRect(window.dotnet_section_nav.item(0)).center(),
        )
        assert window.dotnet_section_nav.currentRow() == 0
        window.building = False
        window.dotnet_publish_controller.refresh_ui()
        assert window.python_section_nav.isEnabled()
        assert window.dotnet_section_nav.isEnabled()
        assert window.dotnet_python_mode_btn.isEnabled()
    finally:
        window._is_closing = True
        window.close()


@pytest.mark.skipif(sys.platform != "win32", reason="The app uses Windows APIs")
def test_dotnet_guided_workflow_requires_each_continue_action(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from exe_builder.controllers.activation_controller import ActivationController

    project = tmp_path / "App.csproj"
    project.write_text('<Project Sdk="Microsoft.NET.Sdk" />', encoding="utf-8")
    output = tmp_path / "publish"
    output.mkdir()

    monkeypatch.setattr(ActivationController, "listen_for_activation", lambda self: None)
    monkeypatch.setattr(ctypes, "GetLastError", lambda: 0)
    from exe_builder.main import EXEBuilderApp

    app = QApplication.instance() or QApplication([])
    window = EXEBuilderApp()

    try:
        window.show()
        window.set_build_mode("dotnet", save=False)
        app.processEvents()

        navigation = window.dotnet_section_nav
        assert bool(navigation.item(0).flags() & Qt.ItemIsEnabled)
        assert not any(
            bool(navigation.item(index).flags() & Qt.ItemIsEnabled)
            for index in (1, 2, 3)
        )
        assert window.dotnet_icon_continue_btn.text() == "Use no icon and continue"
        window.dotnet_icon_input.setText(str(tmp_path / "App.ico"))
        assert window.dotnet_icon_continue_btn.text() == "Continue to file"
        window.dotnet_icon_input.clear()
        assert window.dotnet_icon_continue_btn.text() == "Use no icon and continue"

        window.dotnet_icon_continue_btn.click()
        assert navigation.currentRow() == 1
        assert bool(navigation.item(1).flags() & Qt.ItemIsEnabled)
        assert not bool(navigation.item(2).flags() & Qt.ItemIsEnabled)

        window.dotnet_project_input.setText(str(project))
        app.processEvents()
        assert not window.dotnet_file_continue_btn.isHidden()
        window.dotnet_file_continue_btn.click()
        assert navigation.currentRow() == 2
        assert bool(navigation.item(2).flags() & Qt.ItemIsEnabled)
        assert not bool(navigation.item(3).flags() & Qt.ItemIsEnabled)

        window.dotnet_output_input.setText(str(output))
        window.dotnet_name_input.setText("App")
        app.processEvents()
        assert not window.dotnet_output_continue_btn.isHidden()
        window.dotnet_output_continue_btn.click()
        assert navigation.currentRow() == 3
        assert bool(navigation.item(3).flags() & Qt.ItemIsEnabled)
        assert window._completed_dotnet_steps == {0, 1, 2}

        window.dotnet_project_input.clear()
        app.processEvents()
        assert navigation.currentRow() == 1
        assert not bool(navigation.item(2).flags() & Qt.ItemIsEnabled)
        assert not bool(navigation.item(3).flags() & Qt.ItemIsEnabled)
    finally:
        window._is_closing = True
        window.close()


@pytest.mark.skipif(sys.platform != "win32", reason="The app uses Windows APIs")
def test_saved_dotnet_workflow_restores_the_reachable_build_tab(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from exe_builder.controllers.activation_controller import ActivationController

    project = tmp_path / "Saved.csproj"
    project.write_text('<Project Sdk="Microsoft.NET.Sdk" />', encoding="utf-8")
    output = tmp_path / "publish"
    output.mkdir()
    state_dir = tmp_path / "EXEBuilder"
    state_dir.mkdir()
    (state_dir / "csharp_exe_builder_state.json").write_text(
        json.dumps({
            "project_path": str(project),
            "output_folder": str(output),
            "icon_path": "",
            "executable_name": "Saved",
            "runtime": "win-x64",
            "self_contained": True,
            "single_file": False,
            "trim": False,
            "guided_dotnet_steps": [0, 1, 2],
        }),
        encoding="utf-8",
    )
    (state_dir / "exe_builder_preferences.json").write_text(
        json.dumps({"build_mode": "dotnet"}), encoding="utf-8"
    )

    monkeypatch.setattr(ActivationController, "listen_for_activation", lambda self: None)
    monkeypatch.setattr(ctypes, "GetLastError", lambda: 0)
    from exe_builder.main import EXEBuilderApp

    app = QApplication.instance() or QApplication([])
    window = EXEBuilderApp()

    try:
        window.show()
        app.processEvents()
        assert window.build_mode == "dotnet"
        assert all(
            bool(window.dotnet_section_nav.item(index).flags() & Qt.ItemIsEnabled)
            for index in range(4)
        )
        assert window.dotnet_section_nav.currentRow() == 3
    finally:
        window._is_closing = True
        window.close()


@pytest.mark.skipif(sys.platform != "win32", reason="The app uses Windows APIs")
def test_ready_saved_python_workflow_opens_build_tab(monkeypatch, tmp_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from exe_builder.controllers.activation_controller import ActivationController

    interpreter = tmp_path / "python.exe"
    script = tmp_path / "main.py"
    icon = tmp_path / "app.ico"
    project = tmp_path / "app.csproj"
    output = tmp_path / "output"
    interpreter.write_text("", encoding="utf-8")
    script.write_text("print('ready')", encoding="utf-8")
    icon.write_bytes(b"icon")
    project.write_text('<Project Sdk="Microsoft.NET.Sdk" />', encoding="utf-8")
    output.mkdir()
    state_dir = tmp_path / "EXEBuilder"
    state_dir.mkdir()
    (state_dir / "python_exe_builder_state.json").write_text(
        json.dumps(
            {
                "python_interpreter_path": str(interpreter),
                "last_script_path": str(script),
                "last_icon_path": str(icon),
                "last_output_folder": str(output),
                "last_exe_name": "ReadyApp",
                "guided_python_steps": [0, 1, 2, 3, 4],
            }
        ),
        encoding="utf-8",
    )
    (state_dir / "exe_builder_preferences.json").write_text(
        json.dumps({"build_mode": "python"}),
        encoding="utf-8",
    )
    (state_dir / "csharp_exe_builder_state.json").write_text(
        json.dumps({
            "project_path": str(project),
            "icon_path": str(icon),
            "recent_projects": [str(project)],
            "recent_icons": [str(icon)],
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr(ActivationController, "listen_for_activation", lambda self: None)
    monkeypatch.setattr(ctypes, "GetLastError", lambda: 0)
    from exe_builder.main import EXEBuilderApp

    app = QApplication.instance() or QApplication([])
    window = EXEBuilderApp()
    try:
        window.show()
        app.processEvents()
        assert window.python_section_stack.currentIndex() == 5
        assert window.python_selection_summaries["Icons"][3]["interpreter"].toolTip() == ""
        assert window.python_selection_summaries["File"][3]["icon"].toolTip() == ""
        assert window.python_selection_summaries["Output"][3]["file"].toolTip() == ""
        assert window.dotnet_selection_summaries["File Select"][3]["icon"].toolTip() == ""
        assert window.dotnet_selection_summaries["Output Select"][3]["file"].toolTip() == ""
        assert all(
            bool(window.python_section_nav.item(index).flags() & Qt.ItemIsEnabled)
            for index in range(6)
        )
    finally:
        window._is_closing = True
        window.close()
