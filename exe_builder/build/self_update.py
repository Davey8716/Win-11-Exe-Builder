"""Staged replacement support for a frozen builder rebuilding itself."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path


CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
DETACHED_PROCESS = 0x00000008


class SelfUpdateError(RuntimeError):
    """Raised when a staged self-update cannot be prepared or launched."""


@dataclass(frozen=True)
class SelfUpdatePlan:
    parent_pid: int
    target_dir: str
    staging_root: str
    staged_dir: str
    executable_name: str
    log_path: str

    @property
    def staged_executable(self):
        return os.path.join(self.staged_dir, self.executable_name)


def path_is_within(path, directory):
    """Return whether *path* is inside *directory*, using Windows-safe casing."""
    try:
        path = os.path.normcase(os.path.abspath(os.fspath(path)))
        directory = os.path.normcase(os.path.abspath(os.fspath(directory)))
        return os.path.commonpath((path, directory)) == directory
    except (OSError, TypeError, ValueError):
        return False


def is_frozen_self_target(target_dir, *, executable=None, frozen=None):
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if not frozen:
        return False
    executable = executable or sys.executable
    return bool(executable and path_is_within(executable, target_dir))


def create_self_update_plan(target_dir, executable_name, log_path, *, parent_pid=None):
    target = Path(target_dir).resolve()
    staging_root = target.parent / (
        f".{target.name}.exe-builder-update-{uuid.uuid4().hex}"
    )
    staged_dir = staging_root / target.name
    return SelfUpdatePlan(
        parent_pid=parent_pid or os.getpid(),
        target_dir=str(target),
        staging_root=str(staging_root),
        staged_dir=str(staged_dir),
        executable_name=executable_name,
        log_path=os.path.abspath(log_path) if log_path else "",
    )


def cleanup_staging(plan):
    root = Path(plan.staging_root)
    if root.is_dir():
        shutil.rmtree(root, ignore_errors=True)
    elif root.exists():
        try:
            root.unlink()
        except OSError:
            pass


def validate_self_update_plan(plan):
    target = Path(plan.target_dir).resolve()
    staging_root = Path(plan.staging_root).resolve()
    staged = Path(plan.staged_dir).resolve()

    if target.parent != staging_root.parent:
        raise SelfUpdateError("The staging folder is not beside the live output folder.")
    if staged.parent != staging_root or staged.name != target.name:
        raise SelfUpdateError("The staged output layout is invalid.")
    if not Path(plan.staged_executable).is_file():
        raise SelfUpdateError(
            f"The staged executable was not found: {plan.staged_executable}"
        )


UPDATER_SCRIPT = r'''param(
    [Parameter(Mandatory=$true)][int]$ParentProcessId,
    [Parameter(Mandatory=$true)][string]$TargetDirectory,
    [Parameter(Mandatory=$true)][string]$StagedDirectory,
    [Parameter(Mandatory=$true)][string]$StagingRoot,
    [Parameter(Mandatory=$true)][string]$ExecutableName,
    [string]$LogPath
)

$ErrorActionPreference = "Stop"
$backup = "$TargetDirectory.exe-builder-backup-$([guid]::NewGuid().ToString('N'))"

function Write-UpdateLog([string]$Message) {
    if (-not $LogPath) { return }
    try {
        Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value (
            "SELF UPDATE: " + $Message
        )
    } catch {}
}

function Invoke-WithRetry([scriptblock]$Operation) {
    for ($attempt = 1; $attempt -le 40; $attempt++) {
        try {
            & $Operation
            return
        } catch {
            if ($attempt -eq 40) { throw }
            Start-Sleep -Milliseconds 250
        }
    }
}

try {
    Wait-Process -Id $ParentProcessId -ErrorAction SilentlyContinue
    Invoke-WithRetry { Move-Item -LiteralPath $TargetDirectory -Destination $backup }
    try {
        Invoke-WithRetry { Move-Item -LiteralPath $StagedDirectory -Destination $TargetDirectory }
    } catch {
        Invoke-WithRetry { Move-Item -LiteralPath $backup -Destination $TargetDirectory }
        throw
    }

    Start-Process -FilePath (Join-Path $TargetDirectory $ExecutableName) `
        -WorkingDirectory $TargetDirectory
    try { Remove-Item -LiteralPath $backup -Recurse -Force } catch {
        Write-UpdateLog("Replacement succeeded but old-folder cleanup failed: $($_.Exception.Message)")
    }
    try {
        if (Test-Path -LiteralPath $StagingRoot) {
            Remove-Item -LiteralPath $StagingRoot -Recurse -Force
        }
    } catch {}

    Write-UpdateLog("Replacement completed successfully.")
} catch {
    Write-UpdateLog("Replacement failed: $($_.Exception.Message)")
    try {
        if (Test-Path -LiteralPath $backup) {
            if (Test-Path -LiteralPath $TargetDirectory) {
                Invoke-WithRetry { Remove-Item -LiteralPath $TargetDirectory -Recurse -Force }
            }
            Invoke-WithRetry { Move-Item -LiteralPath $backup -Destination $TargetDirectory }
        }
    } catch {
        Write-UpdateLog("Rollback failed: $($_.Exception.Message)")
    }

    $fallback = Join-Path $TargetDirectory $ExecutableName
    if (Test-Path -LiteralPath $fallback) {
        Start-Process -FilePath $fallback -WorkingDirectory $TargetDirectory
    }
} finally {
    try { Remove-Item -LiteralPath $PSCommandPath -Force } catch {}
}
'''


def launch_self_update(plan, *, popen=subprocess.Popen, temp_dir=None):
    validate_self_update_plan(plan)
    if sys.platform != "win32":
        raise SelfUpdateError("Automatic self-update is supported on Windows only.")

    handle, script_path = tempfile.mkstemp(
        prefix="exe-builder-self-update-",
        suffix=".ps1",
        dir=temp_dir,
        text=True,
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as script:
            script.write(UPDATER_SCRIPT)

        command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            script_path,
            "-ParentProcessId",
            str(plan.parent_pid),
            "-TargetDirectory",
            plan.target_dir,
            "-StagedDirectory",
            plan.staged_dir,
            "-StagingRoot",
            plan.staging_root,
            "-ExecutableName",
            plan.executable_name,
            "-LogPath",
            plan.log_path,
        ]
        popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=tempfile.gettempdir(),
            creationflags=(
                CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
            ),
            close_fds=True,
        )
        return script_path
    except Exception as exc:
        try:
            os.remove(script_path)
        except OSError:
            pass
        if isinstance(exc, SelfUpdateError):
            raise
        raise SelfUpdateError(f"Could not launch the self-update helper: {exc}") from exc
