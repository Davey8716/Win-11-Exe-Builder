import json
import re
from dataclasses import dataclass
from pathlib import Path


MANIFEST_FILENAME = ".python-exe-builder.json"
SCHEMA_VERSION = 1
_MODULE_NAME_PATTERN = re.compile(
    r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$",
    re.ASCII,
)


class ProjectBuildManifestError(ValueError):
    pass


@dataclass(frozen=True)
class ProjectBuildManifest:
    hidden_imports: tuple[str, ...] = ()
    collect_all: tuple[str, ...] = ()
    exclude_modules: tuple[str, ...] = ()

    def pyinstaller_args(self):
        excluded = set(self.exclude_modules)
        return [
            *(f"--hidden-import={name}" for name in self.hidden_imports),
            *(
                f"--collect-all={name}"
                for name in self.collect_all
                if name not in excluded
            ),
            *(f"--exclude-module={name}" for name in self.exclude_modules),
        ]


def load_project_build_manifest(project_root):
    if not project_root:
        return ProjectBuildManifest()

    manifest_path = Path(project_root) / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return ProjectBuildManifest()

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectBuildManifestError(
            f"Cannot read {MANIFEST_FILENAME}: {exc}"
        ) from exc

    _require_object(payload, "manifest")
    _reject_unknown_keys(payload, {"schema_version", "pyinstaller"}, "manifest")

    if set(payload) != {"schema_version", "pyinstaller"}:
        raise ProjectBuildManifestError(
            "Manifest must contain schema_version and pyinstaller."
        )
    if (
        type(payload["schema_version"]) is not int
        or payload["schema_version"] != SCHEMA_VERSION
    ):
        raise ProjectBuildManifestError(
            f"schema_version must be {SCHEMA_VERSION}."
        )

    pyinstaller = payload["pyinstaller"]
    _require_object(pyinstaller, "pyinstaller")
    _reject_unknown_keys(
        pyinstaller,
        {"hidden_imports", "collect_all", "exclude_modules"},
        "pyinstaller",
    )

    return ProjectBuildManifest(
        hidden_imports=_module_names(pyinstaller, "hidden_imports"),
        collect_all=_module_names(pyinstaller, "collect_all"),
        exclude_modules=_module_names(pyinstaller, "exclude_modules"),
    )


def _require_object(value, label):
    if not isinstance(value, dict):
        raise ProjectBuildManifestError(f"{label} must be a JSON object.")


def _reject_unknown_keys(value, allowed, label):
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ProjectBuildManifestError(
            f"Unknown {label} field(s): {', '.join(unknown)}."
        )


def _module_names(pyinstaller, field):
    values = pyinstaller.get(field, [])
    if not isinstance(values, list):
        raise ProjectBuildManifestError(f"pyinstaller.{field} must be an array.")

    names = []
    seen = set()
    for index, value in enumerate(values):
        if not isinstance(value, str) or not _MODULE_NAME_PATTERN.fullmatch(value):
            raise ProjectBuildManifestError(
                f"pyinstaller.{field}[{index}] must be a dotted Python module name."
            )
        if value in seen:
            raise ProjectBuildManifestError(
                f"pyinstaller.{field} contains duplicate module {value!r}."
            )
        seen.add(value)
        names.append(value)
    return tuple(names)
