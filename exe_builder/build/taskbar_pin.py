"""Time-limited Explorer keyboard automation for taskbar pinning."""

import base64
import hashlib
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time


_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
function Trace-Stage($message) { [Console]::Out.WriteLine("TASKBAR_PIN_STAGE: $message"); [Console]::Out.Flush() }
Trace-Stage 'Starting taskbar pin attempt.'
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes, WindowsBase, System.Windows.Forms, Accessibility
Add-Type -ReferencedAssemblies @('System.dll', [System.Windows.Automation.AutomationElement].Assembly.Location, [System.Windows.Automation.ControlType].Assembly.Location, [System.Windows.Rect].Assembly.Location, [Accessibility.IAccessible].Assembly.Location) -TypeDefinition @'
__CS_SOURCE__
'@
$exe = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__EXE__'))
$folder = [IO.Path]::GetDirectoryName($exe)
$shell = New-Object -ComObject Shell.Application
$window = $null
for ($i = 0; $i -lt 30 -and !$window; $i++) {
    foreach ($candidate in $shell.Windows()) {
        try {
            if ([string]::Equals($candidate.Document.Folder.Self.Path, $folder, [StringComparison]::OrdinalIgnoreCase)) {
                $window = $candidate; break
            }
        } catch { }
    }
    if (!$window) { Start-Sleep -Milliseconds 150 }
}
if (!$window) { throw 'Explorer window for the app folder was not found.' }
$item = $window.Document.Folder.ParseName([IO.Path]::GetFileName($exe))
if (!$item -or ![string]::Equals($item.Path, $exe, [StringComparison]::OrdinalIgnoreCase)) { throw 'Built EXE was not found in Explorer.' }
$window.Document.SelectItem($item, 29)
$hwnd = [IntPtr]::new([long]$window.HWND)
[void][PinWindow]::ShowWindow($hwnd, 9)
[void][PinWindow]::SetForegroundWindow($hwnd)
$root = [System.Windows.Automation.AutomationElement]::FromHandle($hwnd)
$condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::ListItem)
$items = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
$found = $null
foreach ($entry in $items) {
    $name = $entry.Current.Name
    if ($name -eq [IO.Path]::GetFileName($exe) -or $name -eq [IO.Path]::GetFileNameWithoutExtension($exe)) {
        $found = $entry; break
    }
}
if (!$found) { throw 'Could not locate the EXE in Explorer.' }
$selection = $null
if (!$found.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern, [ref]$selection) -or !$selection.Current.IsSelected) { throw 'The built EXE is not selected.' }
$found.SetFocus()
Trace-Stage 'Selected the built EXE and requested keyboard focus.'
function Find-Menu($expected) {
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $search = if ($expected -eq 'Pin to taskbar') { [PinWindow]::FindClassicMenu($hwnd, $explorerId, $expected) } else { [PinWindow]::FindMenu($hwnd, $explorerId, $expected) }
        if ($search.Matches -eq 1) {
            if ($search.Diagnostics) { Trace-Stage "Classic menu diagnostics: $($search.Diagnostics -join '; ')." }
            Trace-Stage "Found '$expected': $($search.RawMatches) raw matches, $($search.Matches) distinct; details: $($search.MatchDetails -join '; '); visible menu items: $($search.Observed -join '; ')."
            return $search.Item
        }
        if ($search.Matches -gt 1) {
            if ($search.Diagnostics) { Trace-Stage "Classic menu diagnostics: $($search.Diagnostics -join '; ')." }
            Trace-Stage "Menu search for '$expected': $($search.RawMatches) raw matches, $($search.Matches) distinct matches; details: $($search.MatchDetails -join '; '); visible items: $($search.Observed -join '; ')."
            throw "Found $($search.Matches) matching menu items for '$expected'; refusing to invoke."
        }
        Start-Sleep -Milliseconds 150
    }
    if ($search.Diagnostics) { Trace-Stage "Classic menu diagnostics: $($search.Diagnostics -join '; ')." }
    Trace-Stage "Menu search for '$expected': visible items: $($search.Observed -join '; ')."
    throw "Could not find enabled visible menu item '$expected' in the target Explorer menu."
}
function Invoke-NamedMenu($expected) {
    $element = Find-Menu $expected
    Trace-Stage "Invoking '$expected'."
    $method = [PinWindow]::InvokeItem($element)
    Trace-Stage "Invoked '$expected' using $method."
}
$explorerId = $root.Current.ProcessId
$rect = $found.Current.BoundingRectangle
if ($rect.IsEmpty -or $rect.Width -le 0 -or $rect.Height -le 0) { throw 'Selected EXE has no visible click target.' }
$x = [int]($rect.Left + $rect.Width / 2); $y = [int]($rect.Top + $rect.Height / 2)
if ([PinWindow]::GetForegroundWindow() -ne $hwnd) { throw 'The target Explorer window is not in the foreground.' }
if (![PinWindow]::ClickTarget($hwnd, $x, $y)) { throw 'The selected EXE is obscured by another window.' }
if (![PinWindow]::SetCursorPos($x, $y)) { throw 'Could not move pointer to the EXE.' }
[PinWindow]::mouse_event(0x0008, 0, 0, 0, [UIntPtr]::Zero)
[PinWindow]::mouse_event(0x0010, 0, 0, 0, [UIntPtr]::Zero)
Trace-Stage 'Right-clicked the built EXE; searching for the first menu.'
Invoke-NamedMenu 'Show more options'
Trace-Stage 'Searching for the classic menu.'
Invoke-NamedMenu 'Pin to taskbar'
Trace-Stage 'Pin to taskbar command invoked; taskbar state was not independently verified.'

'''


# The source also ships as data in frozen builds of the builder.
_CS_SOURCE_PATH = Path(__file__).resolve().parent / "taskbar_pin_helper" / "PinWindow.cs"
try:
    _CS_SOURCE = _CS_SOURCE_PATH.read_text(encoding="utf-8")
    _CS_SOURCE_ERROR = ""
except (OSError, UnicodeError) as exc:
    _CS_SOURCE = ""
    _CS_SOURCE_ERROR = str(exc)
_SCRIPT = _SCRIPT.replace("__CS_SOURCE__", _CS_SOURCE)

PIN_TIMEOUT_SECONDS = 25
PIN_IMPLEMENTATION_VERSION = "file-" + hashlib.sha256(_SCRIPT.encode("utf-8")).hexdigest()[:12]


def pin_executable(executable, on_stage=None):
    """Invoke Explorer menu commands and return the result."""
    if sys.platform != "win32" or not os.path.isfile(executable):
        return False, "Windows or the built executable is unavailable."
    if _CS_SOURCE_ERROR:
        return False, f"Taskbar pin C# source is unavailable: {_CS_SOURCE_ERROR}"
    encoded_path = base64.b64encode(os.path.abspath(executable).encode("utf-8")).decode("ascii")
    script = "try {\n" + _SCRIPT.replace("__EXE__", encoded_path) + "\n} catch { [Console]::Error.WriteLine('TASKBAR_PIN_ERROR: ' + $_.Exception.Message + ' | ' + $_.InvocationInfo.PositionMessage); exit 1 }"
    process = None
    script_path = None
    try:
        fd, script_path = tempfile.mkstemp(prefix="exe-builder-pin-", suffix=".ps1")
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="\n") as script_file:
            script_file.write(script)
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-STA", "-ExecutionPolicy", "Bypass", "-File", script_path],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=0x08000000,
        )
        lines = queue.Queue()

        def read_output():
            try:
                for line in iter(process.stdout.readline, b""):
                    lines.put(line)
            finally:
                lines.put(None)

        threading.Thread(target=read_output, daemon=True).start()
        deadline = time.monotonic() + PIN_TIMEOUT_SECONDS
        error = ""
        other_output = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(process.args, PIN_TIMEOUT_SECONDS)
            try:
                raw = lines.get(timeout=remaining)
            except queue.Empty:
                raise subprocess.TimeoutExpired(process.args, PIN_TIMEOUT_SECONDS)
            if raw is None:
                break
            line = raw.decode("utf-8", errors="replace").strip()
            if "TASKBAR_PIN_STAGE: " in line:
                stage = line.split("TASKBAR_PIN_STAGE: ", 1)[1]
                if on_stage is not None:
                    on_stage(stage)
            elif "TASKBAR_PIN_ERROR: " in line:
                error = line.split("TASKBAR_PIN_ERROR: ", 1)[1]
            elif line:
                other_output.append(line)
                if on_stage is not None:
                    on_stage("Helper output: " + line)
        remaining = max(0, deadline - time.monotonic())
        returncode = process.wait(timeout=remaining)
        if returncode == 0:
            return True, "Pin to taskbar command invoked; taskbar state was not independently verified."
        return False, error or ("Helper exited with code " + str(returncode) + ": " + " ".join(other_output)[-2000:])
    except subprocess.TimeoutExpired:
        if process is not None:
            process.kill()
            process.wait()
        return False, f"Taskbar pin attempt timed out after {PIN_TIMEOUT_SECONDS} seconds."
    except Exception as exc:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        return False, f"Taskbar pin helper error ({type(exc).__name__}): {exc}"
    finally:
        if script_path is not None:
            try:
                os.remove(script_path)
            except FileNotFoundError:
                pass
            except OSError as exc:
                if on_stage is not None:
                    try:
                        on_stage(f"Could not remove temporary taskbar pin script: {exc}")
                    except Exception:
                        pass
