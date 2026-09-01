import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


@dataclass
class PythonEnvironmentProfile:
    version: str
    executable: str
    packages: dict = field(default_factory=dict)
    error: str = ""


@dataclass
class EnvironmentSyncPlan:
    profiles: list
    baseline_version: str = ""
    union_packages: dict = field(default_factory=dict)
    missing_by_version: dict = field(default_factory=dict)
    mismatched_by_version: dict = field(default_factory=dict)

    @property
    def total_actions(self):
        missing = sum(len(items) for items in self.missing_by_version.values())
        mismatched = sum(len(items) for items in self.mismatched_by_version.values())
        return missing + mismatched


@dataclass
class PythonEnvironmentSyncResult:
    version: str
    installed: list = field(default_factory=list)
    failed: dict = field(default_factory=dict)
    message: str = ""

    @property
    def success(self):
        return not self.failed


class EnvironmentSyncWorker(QObject):
    finished = Signal(str, object)
    failed = Signal(str, str)
    progress = Signal(str)

    def __init__(self, controller, action):
        super().__init__()
        self.controller = controller
        self.action = action

    def run(self):
        try:
            if self.action == "scan":
                payload = self.controller.scan_profiles(update_ui=False)
            elif self.action == "sync":
                payload = self.controller.sync_dependencies(
                    update_ui=False,
                    progress_callback=self.progress.emit,
                )
            else:
                raise ValueError(f"Unknown environment sync action: {self.action}")

            self.finished.emit(self.action, payload)
        except Exception as exc:
            self.failed.emit(self.action, str(exc))


class EnvironmentSyncController(QObject):
    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self.last_plan = None
        self._thread = None
        self._worker = None
        self._current_process = None
        self._shutting_down = False
        self.is_running = False

    def start_scan_async(self):
        return self._start_async("scan")

    def start_sync_async(self):
        return self._start_async("sync")

    def _start_async(self, action):
        if self.is_running or self._shutting_down:
            return False

        self.is_running = True
        self._set_busy_ui(True)

        self._thread = QThread()
        self._worker = EnvironmentSyncWorker(self, action)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker_refs)

        self._thread.start()
        return True

    def shutdown(self, timeout_ms=5000):
        self._shutting_down = True

        process = getattr(self, "_current_process", None)
        if process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=2)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

        thread = self._thread
        if thread is not None:
            try:
                is_running = thread.isRunning() if hasattr(thread, "isRunning") else True
                if is_running:
                    thread.quit()
                    if hasattr(thread, "wait"):
                        thread.wait(timeout_ms)
            except RuntimeError:
                pass

        self._thread = None
        self._worker = None
        self._current_process = None
        self.is_running = False
        if not self._app_is_closing():
            self._set_busy_ui(False)

    def default_python_root(self):
        return Path.home() / "AppData" / "Local" / "Programs" / "Python"

    def detect_python_installations(self, root=None):
        root_path = Path(root) if root else self.default_python_root()
        if not root_path.is_dir():
            return []

        executables = []
        for child in root_path.iterdir():
            if not child.is_dir():
                continue

            executable = child / "python.exe"
            if executable.is_file():
                executables.append(executable)

        return sorted(executables, key=lambda path: self._version_key(path.parent.name))

    def scan_profiles(self, root=None, update_ui=True):
        profiles = []

        for executable in self.detect_python_installations(root):
            version = executable.parent.name
            try:
                version = self._read_python_version(executable)
                packages = self._read_installed_packages(executable)
                profiles.append(
                    PythonEnvironmentProfile(
                        version=version,
                        executable=str(executable),
                        packages=packages,
                    )
                )
            except Exception as exc:
                profiles.append(
                    PythonEnvironmentProfile(
                        version=version,
                        executable=str(executable),
                        error=str(exc),
                    )
                )

        self.last_plan = self.build_sync_plan(profiles)
        if update_ui:
            self.update_ui_from_plan(self.last_plan)
        return self.last_plan

    def serialize_profiles(self):
        plan = self.last_plan
        if not plan:
            return []

        serialized = []
        for profile in plan.profiles:
            packages = {}
            for key, package in profile.packages.items():
                packages[str(key)] = {
                    "name": str(package.get("name", key)),
                    "version": str(package.get("version", "")),
                }

            serialized.append(
                {
                    "version": str(profile.version),
                    "executable": str(profile.executable),
                    "packages": packages,
                    "error": str(profile.error or ""),
                }
            )

        return serialized

    def load_serialized_profiles(self, serialized_profiles, update_ui=True):
        profiles = []

        if not isinstance(serialized_profiles, list):
            serialized_profiles = []

        for item in serialized_profiles:
            if not isinstance(item, dict):
                continue

            packages = {}
            raw_packages = item.get("packages", {})
            if isinstance(raw_packages, dict):
                for key, package in raw_packages.items():
                    if not isinstance(package, dict):
                        continue

                    package_name = str(package.get("name", key)).strip()
                    package_version = str(package.get("version", "")).strip()
                    if not package_name:
                        continue

                    packages[str(key).lower()] = {
                        "name": package_name,
                        "version": package_version,
                    }

            profiles.append(
                PythonEnvironmentProfile(
                    version=str(item.get("version", "")),
                    executable=str(item.get("executable", "")),
                    packages=packages,
                    error=str(item.get("error", "") or ""),
                )
            )

        self.last_plan = self.build_sync_plan(profiles)
        if update_ui:
            self.update_ui_from_plan(self.last_plan)

        return self.last_plan

    def sync_dependencies(self, update_ui=True, progress_callback=None):
        if self.last_plan is None:
            self.scan_profiles(update_ui=False)

        plan = self.last_plan
        if not plan or not plan.profiles:
            return []

        results = []
        for profile in plan.profiles:
            if profile.error:
                results.append(
                    PythonEnvironmentSyncResult(
                        version=profile.version,
                        failed={"profile": profile.error},
                        message=profile.error,
                    )
                )
                continue

            specs = self._install_specs_for_profile(profile, plan)
            if not specs:
                results.append(
                    PythonEnvironmentSyncResult(
                        version=profile.version,
                        message="Already synced.",
                    )
                )
                continue

            sync_result = PythonEnvironmentSyncResult(version=profile.version)
            for spec in specs:
                if progress_callback:
                    progress_callback(f"Python {profile.version}: installing {spec}")

                ok, message = self._install_package_spec(profile.executable, spec)
                if ok:
                    sync_result.installed.append(spec)
                else:
                    sync_result.failed[spec] = message

            installed_count = len(sync_result.installed)
            failed_count = len(sync_result.failed)
            sync_result.message = (
                f"Installed {installed_count}; failed {failed_count}."
            )
            results.append(sync_result)

        self.scan_profiles(update_ui=update_ui)
        return results

    def build_sync_plan(self, profiles):
        healthy_profiles = [profile for profile in profiles if not profile.error]
        if not healthy_profiles:
            return EnvironmentSyncPlan(profiles=profiles)

        baseline = max(
            healthy_profiles,
            key=lambda profile: (
                len(profile.packages),
                self._version_key(profile.version),
            ),
        )

        occurrences = {}
        for profile in healthy_profiles:
            for key, package in profile.packages.items():
                occurrences.setdefault(key, []).append((profile, package))

        union_packages = {}
        for key, package_occurrences in occurrences.items():
            baseline_package = baseline.packages.get(key)
            if baseline_package:
                union_packages[key] = baseline_package
                continue

            _, selected_package = max(
                package_occurrences,
                key=lambda item: (
                    self._version_key(item[1]["version"]),
                    self._version_key(item[0].version),
                ),
            )
            union_packages[key] = selected_package

        missing_by_version = {}
        mismatched_by_version = {}
        for profile in healthy_profiles:
            missing = {}
            mismatched = {}

            for key, target_package in union_packages.items():
                current_package = profile.packages.get(key)
                if current_package is None:
                    missing[key] = target_package
                elif current_package["version"] != target_package["version"]:
                    mismatched[key] = target_package

            missing_by_version[profile.version] = missing
            mismatched_by_version[profile.version] = mismatched

        return EnvironmentSyncPlan(
            profiles=profiles,
            baseline_version=baseline.version,
            union_packages=union_packages,
            missing_by_version=missing_by_version,
            mismatched_by_version=mismatched_by_version,
        )

    def update_ui_from_plan(self, plan):
        app = self.app
        if app is None or not hasattr(app, "env_sync_rows_layout"):
            return

        if hasattr(app, "env_sync_row_labels"):
            app.env_sync_row_labels.clear()

        self._clear_layout(app.env_sync_rows_layout)
        if hasattr(app, "env_sync_rows_container"):
            app.env_sync_rows_container.setMinimumWidth(0)
        if hasattr(app, "_sync_center_divider_height"):
            app._sync_center_divider_height()

        if not plan.profiles:
            app.set_env_sync_status(
                "No Python installs found under AppData\\Local\\Programs\\Python."
            )
            app.env_sync_match_btn.setEnabled(False)
            return

        summary = (
            f"{len(plan.profiles)} Python profiles found | "
            f"{len(plan.union_packages)} union packages"
        )
        if plan.baseline_version:
            summary += f" | baseline {plan.baseline_version}"

        app.set_env_sync_status(summary)

        for profile in plan.profiles:
            installed_count = len(profile.packages)
            if profile.error:
                status = "Scan failed"
            else:
                missing_count = len(plan.missing_by_version.get(profile.version, {}))
                mismatch_count = len(plan.mismatched_by_version.get(profile.version, {}))
                if missing_count == 0 and mismatch_count == 0:
                    status = "Synced"
                elif missing_count and mismatch_count:
                    status = (
                        f"Missing {missing_count}: "
                        f"{self._package_preview(plan.missing_by_version[profile.version])} | "
                        f"Mismatch {mismatch_count}: "
                        f"{self._package_preview(plan.mismatched_by_version[profile.version])}"
                    )
                elif missing_count:
                    status = (
                        f"Missing {missing_count}: "
                        f"{self._package_preview(plan.missing_by_version[profile.version])}"
                    )
                else:
                    status = (
                        f"Mismatch {mismatch_count}: "
                        f"{self._package_preview(plan.mismatched_by_version[profile.version])}"
                    )

            app.add_env_sync_status_row(profile.version, str(installed_count), status)

        app.env_sync_match_btn.setEnabled(plan.total_actions > 0)

    def _on_worker_progress(self, message):
        if self._app_is_closing():
            return
        if self.app is not None:
            self.app.set_env_sync_status(message)

    def _on_worker_finished(self, action, payload):
        if self._app_is_closing():
            return

        if action == "scan":
            plan = payload
            self.last_plan = plan
            self.update_ui_from_plan(plan)
            if self.app is not None and hasattr(self.app, "state_ctrl"):
                self.app.state_ctrl.save_state()
            return

        results = payload
        failed_count = sum(len(result.failed) for result in results)
        installed_count = sum(len(result.installed) for result in results)

        if self.last_plan is not None:
            self.update_ui_from_plan(self.last_plan)

        if failed_count:
            failure_preview = self._sync_failure_preview(results)

            self.app.set_env_sync_status(
                f"Dependency sync finished.\n"
                f"Installed {installed_count}; failed {failed_count}: {failure_preview}"
            )
        else:
            self.app.set_env_sync_status(
                f"Dependency sync complete.\nInstalled {installed_count} packages."
            )

    def _on_worker_failed(self, action, message):
        if self._app_is_closing():
            return
        self.app.set_env_sync_status(f"Environment {action} failed.\n{message}")

    def _clear_worker_refs(self):
        self._thread = None
        self._worker = None
        self.is_running = False
        if not self._app_is_closing():
            self._set_busy_ui(False)

    def _app_is_closing(self):
        return bool(getattr(self.app, "_is_closing", False))

    def _set_busy_ui(self, busy):
        app = self.app
        if app is None:
            return

        if hasattr(app, "env_sync_scan_btn"):
            app.env_sync_scan_btn.setEnabled(not busy)

        if hasattr(app, "env_sync_match_btn"):
            can_sync = bool(self.last_plan and self.last_plan.total_actions > 0)
            app.env_sync_match_btn.setEnabled(not busy and can_sync)

    def _install_specs_for_profile(self, profile, plan):
        packages = {}
        packages.update(plan.missing_by_version.get(profile.version, {}))
        packages.update(plan.mismatched_by_version.get(profile.version, {}))

        specs = []
        for package in sorted(packages.values(), key=lambda item: item["name"].lower()):
            specs.append(f"{package['name']}=={package['version']}")
        return specs

    def _install_package_spec(self, executable, spec):
        command = [
            executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            spec,
        ]
        result = self._run_subprocess(command, timeout=600)

        if result.returncode == 0:
            return True, "Installed."

        message = (result.stderr or result.stdout or "pip install failed.").strip()
        return False, self._short_error(message)

    def _read_python_version(self, executable):
        result = self._run_subprocess(
            [str(executable), "--version"],
            timeout=15,
        )

        raw = (result.stdout or result.stderr or executable.parent.name).strip()
        return raw.replace("Python ", "").strip()

    def _read_installed_packages(self, executable):
        result = self._run_subprocess(
            [str(executable), "-m", "pip", "list", "--format=json"],
            timeout=90,
        )

        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "pip list failed.").strip())

        packages = {}
        for package in json.loads(result.stdout or "[]"):
            name = str(package.get("name", "")).strip()
            version = str(package.get("version", "")).strip()
            if not name or not version:
                continue

            packages[self._package_key(name)] = {
                "name": name,
                "version": version,
            }

        return packages

    def _run_subprocess(self, command, timeout):
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=CREATE_NO_WINDOW,
        )
        self._current_process = process
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            raise
        finally:
            if self._current_process is process:
                self._current_process = None

        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)

    def _package_key(self, name):
        return re.sub(r"[-_.]+", "-", name).lower()

    def _package_preview(self, packages, limit=3):
        names = sorted(package["name"] for package in packages.values())
        preview = ", ".join(names[:limit])
        remaining = len(names) - limit
        if remaining > 0:
            preview += f" +{remaining}"
        return preview

    def _short_error(self, message, limit=220):
        compact = " ".join(str(message).split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."

    def _sync_failure_preview(self, results, limit=3):
        failed_specs = []
        for result in results:
            for spec in result.failed:
                failed_specs.append(f"{result.version}: {spec}")

        preview = ", ".join(failed_specs[:limit])
        remaining = len(failed_specs) - limit
        if remaining > 0:
            preview += f" +{remaining}"
        return preview

    def _version_key(self, value):
        parts = re.findall(r"\d+|[a-zA-Z]+", str(value))
        key = []
        for part in parts:
            if part.isdigit():
                key.append((1, int(part)))
            else:
                key.append((0, part.lower()))
        return key

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
