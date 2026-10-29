"""Time-limited Explorer keyboard automation for taskbar pinning."""

import base64
import hashlib
import os
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
using System;
using System.Collections.Generic;
using System.Windows.Automation;
using System.Runtime.InteropServices;
using System.Text;
public static class PinWindow {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, uint data, UIntPtr extra);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern IntPtr GetAncestor(IntPtr h, uint flags);
    [DllImport("user32.dll")] public static extern bool IsChild(IntPtr parent, IntPtr child);
    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
    [DllImport("user32.dll")] public static extern IntPtr WindowFromPoint(POINT point);
    [DllImport("oleacc.dll")] private static extern int AccessibleObjectFromPoint(POINT point, out Accessibility.IAccessible accessible, [MarshalAs(UnmanagedType.Struct)] out object child);
    [DllImport("oleacc.dll")] private static extern int AccessibleObjectFromWindow(IntPtr hwnd, uint objectId, ref Guid iid, out Accessibility.IAccessible accessible);
    private delegate bool EnumProc(IntPtr hwnd, IntPtr param);
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumProc callback, IntPtr param);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] private static extern int GetClassName(IntPtr hwnd, StringBuilder name, int length);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint processId);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int left, top, right, bottom; }
    [StructLayout(LayoutKind.Sequential)] public struct GUITHREADINFO {
        public int cbSize, flags; public IntPtr hwndActive, hwndFocus, hwndCapture, hwndMenuOwner, hwndMoveSize, hwndCaret; public RECT rcCaret;
    }
    [DllImport("user32.dll")] private static extern bool GetGUIThreadInfo(uint thread, ref GUITHREADINFO info);
    public static bool ClickTarget(IntPtr target, int x, int y) {
        IntPtr atPoint = WindowFromPoint(new POINT { X = x, Y = y });
        return atPoint == target || IsChild(target, atPoint);
    }
    public sealed class MenuSearch {
        public object Item;
        public string[] Observed;
        public string[] MatchDetails;
        public string[] Diagnostics;
        public int RawMatches;
        public int Matches;
    }
    private sealed class ClassicAccessibleItem {
        public Accessibility.IAccessible Accessible;
        public object Child;
        public string Expected;
    }
    public static bool IsTargetMenu(uint targetThread, uint popupThread, uint popupPid, uint targetPid, bool menuActive, bool ownerMatches) {
        return targetThread != 0 && targetThread == popupThread && targetPid == popupPid && menuActive && ownerMatches;
    }
    public static MenuSearch FindClassicMenu(IntPtr target, int explorerId, string expected) {
        var result = new MenuSearch();
        var observed = new List<string>();
        var diagnostics = new List<string>();
        var matches = new List<object>();
        uint targetPid;
        uint targetThread = GetWindowThreadProcessId(target, out targetPid);
        var info = new GUITHREADINFO(); info.cbSize = Marshal.SizeOf(typeof(GUITHREADINFO));
        bool gotInfo = GetGUIThreadInfo(targetThread, ref info);
        bool active = gotInfo && (info.flags & 20) != 0;
        bool ownerMatches = gotInfo && (info.hwndMenuOwner == target || IsChild(target, info.hwndMenuOwner));
        diagnostics.Add("target=" + target + ", thread=" + targetThread + ", menuFlags=" + info.flags + ", menuOwner=" + info.hwndMenuOwner + ", active=" + active + ", ownerMatches=" + ownerMatches);
        var menuType = new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.MenuItem);
        EnumWindows((popup, unused) => {
            if (!IsWindowVisible(popup)) return true;
            var name = new StringBuilder(256); GetClassName(popup, name, name.Capacity);
            if (name.ToString() != "#32768") return true;
            uint pid; uint thread = GetWindowThreadProcessId(popup, out pid);
            bool accepted = IsTargetMenu(targetThread, thread, pid, targetPid, active, ownerMatches) && pid == (uint)explorerId;
            diagnostics.Add("popup=" + popup + ", class=" + name + ", pid=" + pid + ", thread=" + thread + ", rootOwner=" + GetAncestor(popup, 3) + ", accepted=" + accepted);
            if (!accepted) return true;
            var localMatches = new List<AutomationElement>();
            try {
                var root = AutomationElement.FromHandle(popup);
                var elements = root.FindAll(TreeScope.Descendants, menuType);
                diagnostics.Add("popup=" + popup + " UIA menu items=" + elements.Count);
                foreach (AutomationElement entry in elements) {
                    try {
                        var c = entry.Current;
                        if (observed.Count < 100) observed.Add("UIA: " + c.Name + " (enabled=" + c.IsEnabled + ", offscreen=" + c.IsOffscreen + ")");
                        if (!c.IsOffscreen && c.IsEnabled && String.Equals((c.Name ?? "").Trim().Replace("&", ""), expected, StringComparison.OrdinalIgnoreCase)) {
                            bool duplicate = false;
                            foreach (var old in localMatches) if (SameMenuItem(entry.GetRuntimeId(), old.GetRuntimeId(), c.BoundingRectangle, old.Current.BoundingRectangle, root.Current.BoundingRectangle, root.Current.BoundingRectangle)) { duplicate = true; break; }
                            result.RawMatches++;
                            if (!duplicate) localMatches.Add(entry);
                        }
                    } catch (ElementNotAvailableException) { }
                }
            } catch (Exception ex) { diagnostics.Add("popup=" + popup + " UIA error: " + ex.Message); }
            foreach (var match in localMatches) matches.Add(match);
            if (localMatches.Count == 0) {
                try {
                    Guid iid = new Guid("618736e0-3c3d-11cf-810c-00aa00389b71");
                    Accessibility.IAccessible acc;
                    int hr = AccessibleObjectFromWindow(popup, 0xFFFFFFFC, ref iid, out acc);
                    diagnostics.Add("popup=" + popup + " MSAA result=" + hr + (acc == null ? " no object" : " children=" + acc.accChildCount));
                    if (hr == 0 && acc != null) {
                        for (int i = 1; i <= acc.accChildCount && i <= 100; i++) {
                            try {
                                object child = i; string label = acc.get_accName(child); object state = acc.get_accState(child); object role = acc.get_accRole(child);
                                string action = acc.get_accDefaultAction(child);
                                observed.Add("MSAA: " + label + " (role=" + role + ", state=" + state + ", action=" + action + ")");
                                if (role is int && (int)role == 12 && state is int && (((int)state & 0x8001) == 0) && String.Equals((label ?? "").Trim().Replace("&", ""), expected, StringComparison.OrdinalIgnoreCase)) {
                                    result.RawMatches++;
                                    matches.Add(new ClassicAccessibleItem { Accessible = acc, Child = child, Expected = expected });
                                }
                            } catch (Exception ex) { diagnostics.Add("MSAA child " + i + ": " + ex.Message); }
                        }
                    }
                } catch (Exception ex) { diagnostics.Add("popup=" + popup + " MSAA error: " + ex.Message); }
            }
            return true;
        }, IntPtr.Zero);
        result.Observed = observed.ToArray(); result.Diagnostics = diagnostics.ToArray(); result.MatchDetails = new string[0];
        result.Matches = matches.Count;
        if (matches.Count == 1) result.Item = matches[0];
        return result;
    }
    public static bool SameMenuItem(int[] a, int[] b, System.Windows.Rect rectA, System.Windows.Rect rectB, System.Windows.Rect menuA, System.Windows.Rect menuB) {
        if (a != null && b != null && a.Length > 0 && a.Length == b.Length) {
            bool same = true;
            for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) { same = false; break; }
            if (same) return true;
        }
        return !rectA.IsEmpty && rectA.Width > 0 && rectA.Height > 0 && !menuA.IsEmpty && menuA.Width > 0 && menuA.Height > 0 && rectA == rectB && menuA == menuB;
    }
    public static MenuSearch FindMenu(IntPtr target, int explorerId, string expected) {
        var result = new MenuSearch();
        var observed = new List<string>();
        var details = new List<string>();
        var unique = new List<AutomationElement>();
        var menuRects = new List<System.Windows.Rect>();
        var menuType = new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.MenuItem);
        var windows = AutomationElement.RootElement.FindAll(TreeScope.Children, Condition.TrueCondition);
        foreach (AutomationElement top in windows) {
            try {
                var current = top.Current;
                if (current.IsOffscreen || current.ProcessId != explorerId) continue;
                IntPtr handle = new IntPtr(current.NativeWindowHandle);
                if (handle != target && GetAncestor(handle, 3) != target) continue;
                var items = top.FindAll(TreeScope.Descendants, menuType);
                foreach (AutomationElement entry in items) {
                    try {
                        var c = entry.Current;
                        if (c.IsOffscreen) continue;
                        var parent = TreeWalker.ControlViewWalker.GetParent(entry);
                        bool inMenu = false;
                        while (parent != null && !parent.Equals(top)) {
                            if (parent.Current.ControlType == ControlType.Menu) { inMenu = true; break; }
                            parent = TreeWalker.ControlViewWalker.GetParent(parent);
                        }
                        if (!inMenu && top.Current.ControlType != ControlType.Menu) continue;
                        if (observed.Count < 80) observed.Add(c.Name + " (enabled=" + c.IsEnabled + ")");
                        if (c.IsEnabled && String.Equals(c.Name.Trim().Replace("&", ""), expected, StringComparison.OrdinalIgnoreCase)) {
                            result.RawMatches++;
                            var menu = inMenu ? parent : top;
                            var menuRect = menu.Current.BoundingRectangle;
                            var runtimeId = entry.GetRuntimeId();
                            details.Add("window=" + handle + ", runtimeId=" + (runtimeId == null ? "unavailable" : String.Join(".", Array.ConvertAll(runtimeId, x => x.ToString()))) + ", itemBounds=" + c.BoundingRectangle + ", menuBounds=" + menuRect);
                            bool duplicate = false;
                            for (int i = 0; i < unique.Count; i++) {
                                if (SameMenuItem(runtimeId, unique[i].GetRuntimeId(), c.BoundingRectangle, unique[i].Current.BoundingRectangle, menuRect, menuRects[i])) { duplicate = true; break; }
                            }
                            if (!duplicate) { unique.Add(entry); menuRects.Add(menuRect); }
                        }
                    } catch (ElementNotAvailableException) { }
                }
            } catch (ElementNotAvailableException) { }
        }
        result.Observed = observed.ToArray();
        result.MatchDetails = details.ToArray();
        result.Matches = unique.Count;
        if (unique.Count == 1) result.Item = unique[0];
        return result;
    }
    public static string InvokeItem(object found) {
        var classic = found as ClassicAccessibleItem;
        if (classic != null) {
            string classicName = classic.Accessible.get_accName(classic.Child);
            object classicState = classic.Accessible.get_accState(classic.Child);
            object classicRole = classic.Accessible.get_accRole(classic.Child);
            string action = classic.Accessible.get_accDefaultAction(classic.Child);
            if (!String.Equals((classicName ?? "").Trim().Replace("&", ""), classic.Expected, StringComparison.OrdinalIgnoreCase) || !(classicState is int) || (((int)classicState & 0x8001) != 0) || !(classicRole is int) || (int)classicRole != 12 || String.IsNullOrEmpty(action)) throw new InvalidOperationException("Classic menu item is no longer enabled or has no default action.");
            classic.Accessible.accDoDefaultAction(classic.Child);
            return "MSAA default action (" + action + ")";
        }
        var item = found as AutomationElement;
        if (item == null || item.Current.IsOffscreen || !item.Current.IsEnabled) throw new InvalidOperationException("Menu item is no longer available and enabled.");
        object pattern;
        if (item.TryGetCurrentPattern(InvokePattern.Pattern, out pattern)) {
            ((InvokePattern)pattern).Invoke();
            return "InvokePattern";
        }
        var rect = item.Current.BoundingRectangle;
        if (rect.IsEmpty || rect.Width <= 0 || rect.Height <= 0) throw new InvalidOperationException("Menu item has no accessible action or visible bounds.");
        var point = new POINT { X = (int)(rect.Left + rect.Width / 2), Y = (int)(rect.Top + rect.Height / 2) };
        Accessibility.IAccessible accessible; object child;
        if (AccessibleObjectFromPoint(point, out accessible, out child) != 0 || accessible == null) throw new InvalidOperationException("Menu item has no InvokePattern or accessible default action.");
        string name = accessible.get_accName(child);
        object role = accessible.get_accRole(child);
        object state = accessible.get_accState(child);
        if (!String.Equals((name ?? "").Trim().Replace("&", ""), item.Current.Name.Trim().Replace("&", ""), StringComparison.OrdinalIgnoreCase) || !(role is int) || (int)role != 12 || !(state is int) || (((int)state & 1) != 0))
            throw new InvalidOperationException("Accessible default action did not match the enabled menu item.");
        if (String.IsNullOrEmpty(accessible.get_accDefaultAction(child))) throw new InvalidOperationException("Menu item has no accessible default action.");
        accessible.accDoDefaultAction(child);
        return "MSAA default action";
    }

}
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


PIN_TIMEOUT_SECONDS = 25
PIN_IMPLEMENTATION_VERSION = "file-" + hashlib.sha256(_SCRIPT.encode("utf-8")).hexdigest()[:12]


def pin_executable(executable, on_stage=None):
    """Invoke Explorer menu commands and return the result."""
    if sys.platform != "win32" or not os.path.isfile(executable):
        return False, "Windows or the built executable is unavailable."
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
