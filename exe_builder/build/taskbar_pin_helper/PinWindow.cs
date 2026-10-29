using System;
using System.Collections.Generic;
using System.Windows.Automation;
using System.Runtime.InteropServices;
using System.Text;
// Called by the PowerShell script in taskbar_pin.py; this is not a standalone app.
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
    // The classic menu is a native popup, which may be outside Explorer's UIA tree.
    // Inspect only the popup owned by the target Explorer thread and active menu.
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
            // Classic menus may expose MSAA children even when UIA exposes none.
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
    // Explorer can report the same visible menu item more than once.
    public static bool SameMenuItem(int[] a, int[] b, System.Windows.Rect rectA, System.Windows.Rect rectB, System.Windows.Rect menuA, System.Windows.Rect menuB) {
        if (a != null && b != null && a.Length > 0 && a.Length == b.Length) {
            bool same = true;
            for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) { same = false; break; }
            if (same) return true;
        }
        return !rectA.IsEmpty && rectA.Width > 0 && rectA.Height > 0 && !menuA.IsEmpty && menuA.Width > 0 && menuA.Height > 0 && rectA == rectB && menuA == menuB;
    }
    // Find the modern context-menu item by name in the target Explorer window.
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
    // Invoke the named item through its accessibility action, never an Enter key.
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
