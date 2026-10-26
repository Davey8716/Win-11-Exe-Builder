from types import SimpleNamespace

from exe_builder.ui import tooltips


def test_dotnet_tooltips_cover_all_publish_controls_and_paths(monkeypatch):
    registered_tooltips = []
    registered_path_hovers = []

    class FakeTooltip:
        def __init__(self, widget, text, **_kwargs):
            registered_tooltips.append((widget, text))

    class FakePathHover:
        def __init__(self, widget, **kwargs):
            registered_path_hovers.append((widget, kwargs))

    monkeypatch.setattr(tooltips, "QtTooltip", FakeTooltip)
    monkeypatch.setattr(tooltips, "PathHover", FakePathHover)

    tooltip_names = (
        "dotnet_project_select_btn", "dotnet_recent_projects", "dotnet_project_delete_btn",
        "dotnet_project_delete_all_btn", "dotnet_project_reset_btn", "dotnet_icon_select_btn",
        "dotnet_ico_convert_btn", "dotnet_recent_icons", "dotnet_icon_delete_btn", "dotnet_icon_delete_all_btn",
        "dotnet_icon_reset_btn", "dotnet_output_select_btn", "dotnet_output_reset_btn",
        "dotnet_name_input", "dotnet_name_reset_btn", "dotnet_runtime_combo",
        "dotnet_self_contained", "dotnet_single_file", "dotnet_trim", "dotnet_status_label",
        "dotnet_publish_btn", "dotnet_open_output_btn", "dotnet_mode_btn",
        "dotnet_save_build_setup_btn", "export_dotnet_build_setups_btn",
        "import_dotnet_build_setups_btn", "dotnet_delete_build_setup_btn",
        "saved_dotnet_build_setup_dropdown",
    )
    path_names = ("dotnet_project_input", "dotnet_icon_input", "dotnet_output_input")
    app = SimpleNamespace(tooltips_enabled=True)
    for name in tooltip_names + path_names:
        setattr(app, name, name)

    tooltips.attach_dotnet_tooltips(app)

    assert {widget for widget, _text in registered_tooltips} == set(tooltip_names)
    assert {widget for widget, _kwargs in registered_path_hovers} == set(path_names)
    assert all(kwargs["help_enabled_getter"]() for _widget, kwargs in registered_path_hovers)
    app.tooltips_enabled = False
    assert not any(kwargs["help_enabled_getter"]() for _widget, kwargs in registered_path_hovers)


def test_python_saved_setup_controls_have_tooltips(monkeypatch):
    registered_tooltips = []

    class FakeTooltip:
        def __init__(self, widget, text, **_kwargs):
            registered_tooltips.append((widget, text))

    monkeypatch.setattr(tooltips, "QtTooltip", FakeTooltip)
    app = SimpleNamespace(
        saved_build_setup_dropdown="saved",
        save_build_setup_btn="save",
        export_python_build_setups_btn="export",
        import_python_build_setups_btn="import",
        delete_build_setup_btn="delete",
    )

    tooltips.attach_saved_setup_tooltips(app, "python")

    assert {widget for widget, _text in registered_tooltips} == {
        "save", "export", "import", "delete", "saved"
    }


def test_sidebar_tooltip_uses_the_hovered_section(monkeypatch):
    captured = {}

    class FakeViewport:
        def setMouseTracking(self, enabled):
            captured["mouse_tracking"] = enabled

        def mapFromGlobal(self, position):
            return position

    class FakeNav:
        def __init__(self):
            self.view = FakeViewport()

        def viewport(self):
            return self.view

        def itemAt(self, position):
            if position == "section":
                return SimpleNamespace(text=lambda: "Output")
            return None

    class FakeTooltip:
        def __init__(self, widget, text, **kwargs):
            captured.update(widget=widget, text=text, kwargs=kwargs)

    monkeypatch.setattr(tooltips, "QtTooltip", FakeTooltip)
    monkeypatch.setattr(tooltips, "QCursor", SimpleNamespace(pos=lambda: "section"))
    nav = FakeNav()
    tooltips.attach_section_nav_tooltips(nav, {"Output": "Choose the output folder."})

    assert captured["widget"] is nav.view
    assert captured["mouse_tracking"] is True
    assert captured["kwargs"]["position_at_cursor"] is True
    assert captured["text"]() == "Choose the output folder."
