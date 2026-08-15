from types import SimpleNamespace

import build_cancellation
from build_cancellation import BuildCancellation


def test_cancel_build_trashes_only_current_project_paths(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    target_dir = output_dir / "Builder"
    build_dir = output_dir / "build" / "Builder"
    spec_dir = output_dir / "spec" / "Builder"
    sibling_build = output_dir / "build" / "keep-existing-build"
    for path in (target_dir, build_dir, spec_dir, sibling_build):
        path.mkdir(parents=True, exist_ok=True)

    trashed = []
    monkeypatch.setattr(
        build_cancellation.send2trash,
        "send2trash",
        lambda path: trashed.append(path),
    )
    validation_controller = SimpleNamespace(
        update_ui_state=lambda: None,
        validation_status_message=lambda: None,
    )
    app = SimpleNamespace(
        build_process=None,
        building=True,
        current_build_paths=[
            str(target_dir),
            str(build_dir),
            str(spec_dir),
        ],
        output_path=str(output_dir),
        validation_controller=validation_controller,
        _is_closing=False,
    )

    BuildCancellation(app=app, ui=app).cancel_build()

    assert trashed == [
        str(target_dir),
        str(build_dir),
        str(spec_dir),
    ]
    assert str(output_dir / "build") not in trashed
    assert str(sibling_build) not in trashed
