**Updated as of 2026-05-20 to use PySide6 QtWidgets**

# Win 11 → Python → EXE Builder

If this tool saved you time or simplified your workflow, consider giving the repo a ⭐.

There is also a sponsor option available if you would like to support continued development.

---

## Overview

Win 11 → Python → EXE Builder is a Windows GUI tool for converting Python scripts and projects into standalone executable folders using PyInstaller.

It handles interpreter selection, input validation, output naming, and build execution through a controlled PySide6 workflow. The builder runs PyInstaller through the Python interpreter you select, using `python -m PyInstaller`.

---

## Core Features

* Select and validate Python interpreters
* Keep recent interpreter, Python file, and icon selections
* Select a single Python file or choose an entry script from a project folder
* Choose an output folder and EXE name with reset helpers
* Validate build readiness before enabling the build action
* Build with PyInstaller through the selected interpreter
* Cancel an active build and clean up known generated output
* Optional `.ico` selection, recent icons, and a built-in `No Icon` choice
* Direct links to Python.org and ICO conversion sites
* Optional output-folder opening after successful builds
* Optional minimize-after-build, close-after-build, suppress-exit-dialogue, and tooltip toggles
* Environment Sync for scanning and matching package sets across local Python installs

---

## Environment Sync

Environment Sync scans Python installs under:

```text
AppData\Local\Programs\Python
```

It compares installed package sets across discovered Python profiles, identifies missing or mismatched packages, and can install matching package versions where needed.

This feature does not decide whether a package is compatible with a Python version. It only attempts to align installed package names and versions across the local Python environments it can scan.

---

## Protected Folders

Avoid building in protected or restricted folders, such as Pictures or Music.

These locations may block file writes and cause build failures or stalled output. The app checks whether the selected output folder is writable before starting a build.

---

## Icon Behavior

Windows aggressively caches application icons.

If you rebuild an EXE with the same filename:

* The EXE updates correctly
* The embedded icon updates correctly
* Windows may still display the old icon

This is Windows Explorer caching behavior, not a bug in the builder or PyInstaller.

Recommended solution:

Use a unique filename for each build.

Built-in naming options:

* No date/time appended
* ISO date/time formats
* UK date/time formats
* USA date/time formats
* Build all date/time output variants
* Append Python version

Practical rule:

* Same filename: possible stale icon
* Unique filename: correct icon display is much more reliable

---

## Output Naming and Multiple Builds

The generated app folder name is based on the EXE name, with optional additions:

* The parent folder name for common entry files such as `main.py`, `app.py`, or `run.py`
* The selected date/time format
* The selected Python-version suffix

If two builds produce the same final name in the same output folder, the later build can replace the earlier generated folder. Choose a date/time format with enough precision, enable the Python-version suffix when useful, or change the EXE name when you need separate outputs.

---

## Requirements

* Windows 11
* Python 3.11+ recommended for running the PySide6 GUI
* Runtime packages for the GUI, including:
  * `PySide6`
  * `psutil`
  * `send2trash`
* PyInstaller installed in the selected build interpreter

The selected build interpreter is the interpreter used for `python -m PyInstaller`. If PyInstaller is missing from that interpreter, the build will not start and the app will show an install prompt.

Test coverage is intended to be run from a compatible Python 3.11+ environment with PySide6 installed. On this machine, the default `python` currently resolves to Python 3.9, and `pytest -q` fails during PySide6/Shiboken import, so that default interpreter is not a valid local test environment for this app.

### Project-specific PyInstaller dependencies

A project can add `.python-exe-builder.json` at its project root when
PyInstaller cannot discover a dynamically imported dependency. Version 1
supports only validated Python module names:

```json
{
  "schema_version": 1,
  "pyinstaller": {
    "hidden_imports": ["package.dynamic_module"],
    "collect_all": ["package_with_data_or_binaries"],
    "exclude_modules": ["unused_optional_package"]
  }
}
```

`hidden_imports` maps to PyInstaller's `--hidden-import` option. `collect_all`
maps to `--collect-all`, which includes the package's submodules, data files,
and binaries. `exclude_modules` maps to `--exclude-module`; exclusions override
matching `collect_all` entries, including any builder default collection.
Tkinter is not forced into every application; PyInstaller discovers it when
the project actually imports it.
All arrays are optional. Unknown fields, duplicate or invalid module names,
malformed JSON, and unsupported schema versions stop the build with an error.
Raw PyInstaller arguments and filesystem paths are not accepted.

---

## Limitations

This tool does not:

* Determine compatibility of libraries with specific Python versions
* Fix broken or unsupported dependencies
* Modify, downgrade, or patch packages except when Environment Sync is explicitly used to install matching versions
* Automatically resolve PyInstaller-specific issues that are not declared in a project manifest

It assumes a working Python environment and focuses on providing a safer, more predictable build process.

---

## Distribution

* This repository contains source code only
* Users must run locally or build their own executable. Users can build the  python builder from its own source code.

---

## Local State and Portability

Settings and recent selections are stored locally on the user's machine at:

```text
%LOCALAPPDATA%\EXEBuilder\exe_builder_state.json
```

No app state is embedded inside generated executables, and no data is uploaded or transmitted.

For PyInstaller onedir output, the generated EXE and its `_internal` folder must remain together. The generated application can be moved as long as that output structure is preserved.

---

## Building and Running from Source

1. Install Python 3.11 or newer.
2. Install the GUI runtime packages:

   ```text
   python -m pip install PySide6 psutil send2trash
   ```

3. Install PyInstaller into any interpreter you want to use for building:

   ```text
   python -m pip install pyinstaller
   ```

4. Clone the repository.
5. Run the app from source:

   ```text
   python main.py
   ```

6. In the app, select the Python interpreter that has PyInstaller installed.
7. Select the entry script, optional icon, output folder, and EXE name.
8. Start the build.

---

## Build Output

PyInstaller creates output under the selected output folder:

* `build`
* `spec`
* the final onedir app folder

The final onedir app folder contains the generated executable and its supporting files.

---

## Debug Log Path

The application writes debug logs directly into the selected output folder during builds.

Debug logs use timestamped names similar to:

```text
EXE_BUILDER_DEBUG_<name>_<date_time>.log
```

The log is created alongside the generated build output as a sibling of:

* `build`
* `spec`
* the final bundled app folder

Debug logs are used for diagnostics and troubleshooting. Changing this behavior incorrectly may interfere with diagnostics or cause unexpected behavior.
