import json

import pytest

from project_build_manifest import (
    MANIFEST_FILENAME,
    ProjectBuildManifestError,
    load_project_build_manifest,
)


def write_manifest(project_root, payload):
    path = project_root / MANIFEST_FILENAME
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_missing_manifest_preserves_default_arguments(tmp_path):
    manifest = load_project_build_manifest(tmp_path)

    assert manifest.pyinstaller_args() == []


def test_valid_manifest_generates_only_supported_arguments(tmp_path):
    write_manifest(
        tmp_path,
        {
            "schema_version": 1,
            "pyinstaller": {
                "hidden_imports": ["package.dynamic_module"],
                "collect_all": ["uiautomation"],
                "exclude_modules": ["tkinter", "_tkinter"],
            },
        },
    )

    manifest = load_project_build_manifest(tmp_path)

    assert manifest.pyinstaller_args() == [
        "--hidden-import=package.dynamic_module",
        "--collect-all=uiautomation",
        "--exclude-module=tkinter",
        "--exclude-module=_tkinter",
    ]


def test_exclusions_override_matching_collect_all_entries(tmp_path):
    write_manifest(
        tmp_path,
        {
            "schema_version": 1,
            "pyinstaller": {
                "collect_all": ["tkinter", "uiautomation"],
                "exclude_modules": ["tkinter"],
            },
        },
    )

    manifest = load_project_build_manifest(tmp_path)

    assert manifest.pyinstaller_args() == [
        "--collect-all=uiautomation",
        "--exclude-module=tkinter",
    ]


@pytest.mark.parametrize(
    "payload, error",
    [
        ("{", "Cannot read"),
        (
            {"schema_version": 1, "pyinstaller": {}, "extra": True},
            "Unknown manifest",
        ),
        ({"schema_version": 2, "pyinstaller": {}}, "schema_version must be 1"),
        (
            {"schema_version": 1, "pyinstaller": {"raw_args": []}},
            "Unknown pyinstaller",
        ),
        (
            {"schema_version": 1, "pyinstaller": {"collect_all": "uiautomation"}},
            "must be an array",
        ),
        (
            {"schema_version": 1, "pyinstaller": {"collect_all": ["bad-name"]}},
            "dotted Python module name",
        ),
        (
            {"schema_version": 1, "pyinstaller": {"exclude_modules": "tkinter"}},
            "must be an array",
        ),
        (
            {"schema_version": 1, "pyinstaller": {"exclude_modules": ["bad-name"]}},
            "dotted Python module name",
        ),
        (
            {
                "schema_version": 1,
                "pyinstaller": {"collect_all": ["pkg", "pkg"]},
            },
            "duplicate module",
        ),
        (
            {
                "schema_version": 1,
                "pyinstaller": {"exclude_modules": ["tkinter", "tkinter"]},
            },
            "duplicate module",
        ),
    ],
)
def test_invalid_manifest_is_rejected(tmp_path, payload, error):
    write_manifest(tmp_path, payload)

    with pytest.raises(ProjectBuildManifestError, match=error):
        load_project_build_manifest(tmp_path)
