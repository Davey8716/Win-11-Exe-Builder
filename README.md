**Updated as of 2026-09-22 for the PySide6 QtWidgets Python and C#/.NET build workflows**

# Win 11 → EXE Builder

If this tool saved you time or simplified your workflow, consider giving the repo a ⭐.

There is also a sponsor option available if you would like to support continued development.

---

## Overview

Win 11 → Python → EXE Builder is a Windows GUI tool with two independent build modes:

* **Python EXE Builder** converts Python scripts and projects into standalone executable folders with PyInstaller.
* **C# .NET Publish** publishes SDK-style C# projects with the installed .NET SDK.

Both modes provide controlled PySide6 workflows for selection, validation, output naming, live build output, cancellation, and opening the published output. Python builds run PyInstaller through the interpreter you select, using `python -m PyInstaller`.

---

## Core Features

* Switch between independent Python and C#/.NET build modes; each retains its own recent selections and build inputs
* Select and validate Python interpreters, scripts or project entry scripts, `.ico` files, output folders, and executable names
* Select SDK-style C# `.csproj` files, optional `.ico` files, output folders, executable names, target runtimes, and publish options
* Validate readiness before enabling a build or publish action
* Run PyInstaller through the selected Python interpreter or publish C# projects in Release configuration through `dotnet`
* Stream build output to debug logs while a build is running
* Cancel an active build or publish
* Offer a built-in `No Icon` choice, recent file lists, reset helpers, and an explicit output-folder action
* Provide global build options for opening the output directory, minimizing or closing after a build, exit confirmation, and tooltips
* Environment Sync for scanning and matching package sets across local Python installs

---

## C#/.NET Publish Mode

Choose **C# .NET Publish** from the build-mode toggle to publish an SDK-style
`.csproj` using the installed .NET SDK. The builder publishes `Release` output
to `<output folder>\<executable name>`. It supports `win-x64` and `win-arm64`
targets, with self-contained publishing enabled by default and optional
single-file and trim publishing.

The executable name and optional `.ico` are passed as publish-time MSBuild
properties; the selected project file is never changed. With **No Icon**, the
builder clears `ApplicationIcon` for this publish, including a value set in the
project. A project that supplies a separate `Win32Resource` must remove that
resource itself before **No Icon** can be guaranteed. Trim can reduce output
size, but applications that rely on reflection or dynamic loading may require
additional project configuration. C# publishing runs `dotnet clean` first so
an icon embedded by an earlier build is not reused from .NET build outputs.
The output folder has an explicit **Open
Output Folder** action as well as the existing post-build option.

When an icon is selected, the builder also copies it beside the published EXE
as `_exe_builder_tray_icon.ico`, including for single-file output. A C# app can
opt in by using this file when it has no explicit tray icon:

```csharp
var path = Path.Combine(AppContext.BaseDirectory, "_exe_builder_tray_icon.ico");
if (notifyIcon.Icon is null && File.Exists(path))
    notifyIcon.Icon = new System.Drawing.Icon(path);
```

Add this where a WinForms app configures its `NotifyIcon`, before making the
icon visible. Other tray frameworks can use the same file path. When **No Icon**
is selected, the builder removes its previously generated tray file; an app's
explicit tray icon remains under the app's control. The builder also leaves any
file with that name that it did not generate untouched.

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
* PyInstaller installed in each Python interpreter used for Python builds
* An installed .NET SDK for C#/.NET Publish mode

The selected Python build interpreter is the interpreter used for `python -m PyInstaller`. If PyInstaller is missing from that interpreter, the build will not start and the app will show an install prompt. C#/.NET Publish requires an SDK-style `.csproj` and a `dotnet` SDK available on the system path.

Test coverage is intended to be run from a compatible Python 3.11+ environment with PySide6 installed.

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
* Users must run locally or build their own executable from the source code.

---

## Local State and Portability

Settings and recent selections are stored locally on the user's machine in:

```text
%LOCALAPPDATA%\EXEBuilder\
```

The app stores the two workflows and global preferences separately:

```text
python_exe_builder_state.json
csharp_exe_builder_state.json
exe_builder_preferences.json
```

On first run after upgrading, a legacy `exe_builder_state.json` file is split
into these files when no newer state files already exist.

No app state is embedded inside generated executables, and no data is uploaded or transmitted.

For PyInstaller onedir output, the generated EXE and its `_internal` folder must remain together. The generated application can be moved as long as that output structure is preserved.

---

## Building and Running from Source

1. Install Python 3.11 or newer.
2. Install the GUI runtime packages:

   ```text
   python -m pip install PySide6 psutil send2trash
   ```

3. Install PyInstaller into every Python interpreter you want to use for Python builds:

   ```text
   python -m pip install pyinstaller
   ```

4. Clone the repository.
5. Run the app from source:

   ```text
   python -m exe_builder
   ```

6. In the app, select the Python interpreter that has PyInstaller installed.
7. Select the entry script, optional icon, output folder, and EXE name.
8. Start the build.

For C#/.NET publishing, install a .NET SDK, start the app, choose **C# .NET
Publish**, then select an SDK-style `.csproj`, output folder, executable name,
target runtime, and publish options before selecting **Publish**.

---

## Build Output

For Python mode, PyInstaller creates output under the selected output folder:

* `build`
* `spec`
* the final onedir app folder

The final onedir app folder contains the generated executable and its supporting files.
Use Python mode's **Open Output Folder** button to open the latest complete app
folder that matches the current EXE and script naming base.

For C#/.NET Publish mode, the builder writes Release publish output to:

```text
<output folder>\<executable name>
```

The C# Output Select menu also offers the same ISO, UK, and USA date-only and
date-plus-time naming choices as Python mode. A selected format appends the
region and date/time to both the folder and executable name. Build All publishes
the no-date output plus all six dated outputs, or the two formats for one region.
Each output has its own publish log in the selected output folder. Each
published folder contains its executable and any files required by the selected
publish options. **Open Output Folder** opens the latest completed output for
the current selection.

---

## Debug Log Path

The application writes debug logs directly into the selected output folder during builds.

PyInstaller and `dotnet` output are written live, so the log can be opened
while a build is running to see its latest stage. Startup failures are also
recorded. The compiled builder clears its bundled DLL search paths when
launching the selected Python interpreter, then restores them for its own use.

For builds with a selected icon, the builder writes its embedded tray-icon runtime
hook to a temporary Python file. This also works from the packaged builder without
requiring loose Python source files in its `_internal` folder.

Python debug logs use timestamped names similar to:

```text
EXE_BUILDER_DEBUG_<name>_<date_time>.log
```

C#/.NET publish logs use the selected output folder and a name similar to:

```text
DOTNET_PUBLISH_DEBUG_<generated name>.log
```

The log is created alongside the generated build output as a sibling of:

* `build`
* `spec`
* the final bundled app folder

Debug logs are used for diagnostics and troubleshooting. Changing this behavior incorrectly may interfere with diagnostics or cause unexpected behavior.
