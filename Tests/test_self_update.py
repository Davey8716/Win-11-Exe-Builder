from pathlib import Path

import pytest

from exe_builder.build import self_update


def make_plan(tmp_path):
    target = tmp_path / "Builder"
    target.mkdir()
    plan = self_update.create_self_update_plan(
        target,
        "Builder.exe",
        tmp_path / "build.log",
        parent_pid=1234,
    )
    staged = Path(plan.staged_dir)
    staged.mkdir(parents=True)
    (staged / "Builder.exe").write_bytes(b"staged")
    return plan


def test_frozen_self_target_requires_executable_inside_target(tmp_path):
    target = tmp_path / "Builder"
    executable = target / "Builder.exe"

    assert self_update.is_frozen_self_target(
        target, executable=executable, frozen=True
    )
    assert not self_update.is_frozen_self_target(
        target, executable=tmp_path / "Other" / "Builder.exe", frozen=True
    )
    assert not self_update.is_frozen_self_target(
        target, executable=executable, frozen=False
    )


def test_self_update_plan_uses_unique_sibling_staging_folder(tmp_path):
    target = tmp_path / "Builder"
    first = self_update.create_self_update_plan(target, "Builder.exe", "")
    second = self_update.create_self_update_plan(target, "Builder.exe", "")

    assert Path(first.staging_root).parent == tmp_path
    assert Path(first.staged_dir) == Path(first.staging_root) / "Builder"
    assert first.staging_root != second.staging_root


def test_launch_self_update_validates_and_starts_detached_helper(tmp_path, monkeypatch):
    plan = make_plan(tmp_path)
    calls = []
    monkeypatch.setattr(self_update.sys, "platform", "win32")

    script_path = self_update.launch_self_update(
        plan,
        popen=lambda command, **kwargs: calls.append((command, kwargs)),
        temp_dir=tmp_path,
    )

    command, kwargs = calls[0]
    assert command[0] == "powershell.exe"
    assert command[command.index("-TargetDirectory") + 1] == plan.target_dir
    assert command[command.index("-StagedDirectory") + 1] == plan.staged_dir
    assert kwargs["creationflags"] & self_update.DETACHED_PROCESS
    assert not self_update.path_is_within(kwargs["cwd"], plan.target_dir)
    script = Path(script_path).read_text(encoding="utf-8")
    assert "Wait-Process" in script
    assert "Move-Item -LiteralPath $StagedDirectory" in script
    assert "Move-Item -LiteralPath $backup" in script
    assert "Start-Process -FilePath" in script


def test_launch_self_update_rejects_missing_staged_executable(tmp_path):
    target = tmp_path / "Builder"
    target.mkdir()
    plan = self_update.create_self_update_plan(target, "Builder.exe", "")
    Path(plan.staged_dir).mkdir(parents=True)

    with pytest.raises(self_update.SelfUpdateError, match="staged executable"):
        self_update.launch_self_update(plan)


def test_cleanup_staging_never_removes_live_target(tmp_path):
    plan = make_plan(tmp_path)
    live_marker = Path(plan.target_dir) / "running.dll"
    live_marker.write_bytes(b"locked")

    self_update.cleanup_staging(plan)

    assert live_marker.read_bytes() == b"locked"
    assert not Path(plan.staging_root).exists()
