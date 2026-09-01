from exe_builder.controllers.environment_sync_controller import (
    EnvironmentSyncController,
    PythonEnvironmentProfile,
)
from types import SimpleNamespace


def package(name, version):
    return {
        name.lower(): {
            "name": name,
            "version": version,
        }
    }


def make_profile(version, packages):
    normalized = {}
    for name, package_data in packages.items():
        normalized[name.lower()] = package_data

    return PythonEnvironmentProfile(
        version=version,
        executable=f"C:/Python{version.replace('.', '')}/python.exe",
        packages=normalized,
    )


class DummyThread:
    def __init__(self, running=True):
        self.running = running
        self.quit_called = False
        self.wait_timeout = None

    def isRunning(self):
        return self.running

    def quit(self):
        self.quit_called = True

    def wait(self, timeout):
        self.wait_timeout = timeout
        self.running = False
        return True


def test_shutdown_stops_running_thread_and_clears_state():
    app = SimpleNamespace(_is_closing=True)
    controller = EnvironmentSyncController(app)
    thread = DummyThread()
    controller._thread = thread
    controller._worker = object()
    controller.is_running = True

    controller.shutdown(timeout_ms=4321)

    assert thread.quit_called is True
    assert thread.wait_timeout == 4321
    assert controller._thread is None
    assert controller._worker is None
    assert controller.is_running is False


def test_shutdown_restores_busy_ui_when_not_closing():
    app = SimpleNamespace(_is_closing=False)
    controller = EnvironmentSyncController(app)
    thread = DummyThread()
    controller._thread = thread
    controller._worker = object()
    controller.is_running = True
    calls = []
    controller._set_busy_ui = lambda busy: calls.append(busy)

    controller.shutdown()

    assert calls == [False]


def test_union_plan_uses_largest_environment_as_baseline_and_keeps_unique_packages():
    controller = EnvironmentSyncController()

    profile_312 = make_profile(
        "3.12",
        {
            **package("numpy", "2.2.0"),
            **package("pillow", "11.0.0"),
            **package("rich", "13.9.0"),
        },
    )
    profile_313 = make_profile(
        "3.13",
        {
            **package("numpy", "2.3.0"),
            **package("pillow", "11.1.0"),
            **package("PySide6", "6.9.0"),
            **package("pyinstaller", "6.14.0"),
        },
    )

    plan = controller.build_sync_plan([profile_312, profile_313])

    assert plan.baseline_version == "3.13"
    assert set(plan.union_packages) == {"numpy", "pillow", "pyside6", "pyinstaller", "rich"}
    assert plan.union_packages["numpy"]["version"] == "2.3.0"
    assert plan.union_packages["rich"]["version"] == "13.9.0"
    assert set(plan.missing_by_version["3.13"]) == {"rich"}
    assert set(plan.missing_by_version["3.12"]) == {"pyside6", "pyinstaller"}
    assert set(plan.mismatched_by_version["3.12"]) == {"numpy", "pillow"}


def test_install_specs_include_missing_and_mismatched_target_versions():
    controller = EnvironmentSyncController()
    profile_311 = make_profile("3.11", package("numpy", "1.26.0"))
    profile_313 = make_profile(
        "3.13",
        {
            **package("numpy", "2.3.0"),
            **package("PySide6", "6.9.0"),
        },
    )
    plan = controller.build_sync_plan([profile_311, profile_313])

    specs = controller._install_specs_for_profile(profile_311, plan)

    assert specs == ["numpy==2.3.0", "PySide6==6.9.0"]


def test_serialized_profiles_round_trip_and_rebuild_plan():
    controller = EnvironmentSyncController()
    profile_311 = make_profile("3.11", package("numpy", "1.26.0"))
    profile_313 = make_profile(
        "3.13",
        {
            **package("numpy", "2.3.0"),
            **package("PySide6", "6.9.0"),
        },
    )
    controller.last_plan = controller.build_sync_plan([profile_311, profile_313])

    serialized = controller.serialize_profiles()

    restored = EnvironmentSyncController()
    plan = restored.load_serialized_profiles(serialized, update_ui=False)

    assert serialized[0]["version"] == "3.11"
    assert serialized[0]["executable"] == profile_311.executable
    assert serialized[0]["packages"]["numpy"]["version"] == "1.26.0"
    assert plan.baseline_version == "3.13"
    assert set(plan.missing_by_version["3.11"]) == {"pyside6"}
    assert set(plan.mismatched_by_version["3.11"]) == {"numpy"}


def test_serialized_profiles_preserve_scan_errors():
    controller = EnvironmentSyncController()
    controller.last_plan = controller.build_sync_plan(
        [
            PythonEnvironmentProfile(
                version="Python314",
                executable="C:/Python314/python.exe",
                error="pip failed",
            )
        ]
    )

    serialized = controller.serialize_profiles()
    restored = EnvironmentSyncController()
    plan = restored.load_serialized_profiles(serialized, update_ui=False)

    assert serialized[0]["error"] == "pip failed"
    assert plan.profiles[0].error == "pip failed"


def test_sync_continues_when_one_package_fails(monkeypatch):
    controller = EnvironmentSyncController()
    profile_311 = make_profile("3.11", {})
    profile_313 = make_profile(
        "3.13",
        {
            **package("numpy", "2.3.0"),
            **package("PySide6", "6.9.0"),
        },
    )
    controller.last_plan = controller.build_sync_plan([profile_311, profile_313])

    attempted = []

    def fake_install(_executable, spec):
        attempted.append(spec)
        if spec == "numpy==2.3.0":
            return False, "No compatible wheel"
        return True, "Installed"

    monkeypatch.setattr(controller, "_install_package_spec", fake_install)
    monkeypatch.setattr(
        controller,
        "scan_profiles",
        lambda update_ui=True: controller.last_plan,
    )

    results = controller.sync_dependencies(update_ui=False)

    result_311 = next(result for result in results if result.version == "3.11")
    assert attempted == ["numpy==2.3.0", "PySide6==6.9.0"]
    assert result_311.installed == ["PySide6==6.9.0"]
    assert result_311.failed == {"numpy==2.3.0": "No compatible wheel"}
