import base64
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from exe_builder.build import taskbar_pin


def test_missing_csharp_source_reports_error_without_starting_helper(tmp_path, monkeypatch):
    exe = tmp_path / "app.exe"
    exe.touch()
    monkeypatch.setattr(taskbar_pin.sys, "platform", "win32")
    monkeypatch.setattr(taskbar_pin, "_CS_SOURCE_ERROR", "source missing")
    success, message = taskbar_pin.pin_executable(str(exe))
    assert not success
    assert "C# source is unavailable: source missing" in message


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell integration test")
@pytest.mark.parametrize("failure,expected", [("", ["Show more options", "Pin to taskbar"]), ("close", ["Show more options", "Pin to taskbar"]), ("silentclose", ["Show more options", "Pin to taskbar"]), ("closefailed", ["Show more options", "Pin to taskbar"]), ("missing", []), ("missingsecond", ["Show more options"]), ("duplicate", []), ("unsupported", []), ("second", ["Show more options"])])
def test_named_menu_flow_uses_actions_and_stops_on_failure(failure, expected):
    functions = taskbar_pin._SCRIPT.split("function Find-Menu($expected) {", 1)[1].split("\n$explorerId =", 1)[0]
    sequence = taskbar_pin._SCRIPT.split("Trace-Stage 'Right-clicked the built EXE; searching for the first menu.'", 1)[1]
    harness = r'''
Add-Type @"
public class Search { public int Matches; public int RawMatches; public string[] MatchDetails; public string[] Diagnostics; public string Item; public string[] Observed; }
public static class PinWindow {
    public static string Failure;
    public static bool WindowOpen = true;
    public static bool IsTargetWindow(int hwnd, int id) { return WindowOpen; }
    public static bool RequestClose(int hwnd, int id) {
        System.Console.WriteLine("fallback close");
        if (Failure == "closefailed") return false;
        WindowOpen = false; return true;
    }
    public static Search FindMenu(int hwnd, int id, string expected) {
        int count = Failure == "missing" ? 0 : (Failure == "duplicate" ? 2 : 1);
        return new Search { Matches = count, RawMatches = count, MatchDetails = new string[0], Item = expected, Observed = new[] { expected } };
    }
    public static Search FindClassicMenu(int hwnd, int id, string expected) {
        if (Failure == "missingsecond") return new Search { Matches = 0, RawMatches = 0, Diagnostics = new[] { "classic popup not available" }, Observed = new string[0] };
        return FindMenu(hwnd, id, expected);
    }
    public static string InvokeItem(string item) {
        if (Failure == "unsupported" || (Failure == "second" && item == "Pin to taskbar")) throw new System.Exception("No supported action");
        System.Console.WriteLine("invoked:" + item);
        return "InvokePattern";
    }
}
"@
$hwnd = 1; $explorerId = 2
[PinWindow]::Failure = 'FAILURE'
$window = New-Object PSObject
$window | Add-Member ScriptMethod Quit {
    if ([PinWindow]::Failure -eq 'close') { throw 'close failed' }
    if ([PinWindow]::Failure -eq 'silentclose' -or [PinWindow]::Failure -eq 'closefailed') { return }
    [PinWindow]::WindowOpen = $false
    [Console]::WriteLine('window closed')
}
function Trace-Stage($message) { [Console]::WriteLine("stage:$message") }
function Start-Sleep($Milliseconds) { }
function Find-Menu($expected) {
'''.replace("FAILURE", failure) + functions + "\ntry {\n" + sequence + "\n} catch { Write-Output 'stopped' }"
    encoded = base64.b64encode(harness.encode("utf-16le")).decode("ascii")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-EncodedCommand", encoded], text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert [line.removeprefix("invoked:") for line in result.stdout.splitlines() if line.startswith("invoked:")] == expected
    assert ("stopped" in result.stdout) == (failure not in ("", "close", "silentclose", "closefailed"))
    assert ("window closed" in result.stdout) == (failure == "")
    assert ("fallback close" in result.stdout) == (failure in ("close", "silentclose", "closefailed"))
    assert ("Could not close the Explorer window" in result.stdout) == (failure == "closefailed")
    if failure == "duplicate":
        assert "2 raw matches, 2 distinct matches" in result.stdout
    if failure == "missingsecond":
        assert "classic popup not available" in result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell integration test")
def test_embedded_csharp_helper_compiles(tmp_path):
    script = taskbar_pin._SCRIPT.split("$exe =", 1)[0] + "\nWrite-Output 'compiled'"
    path = tmp_path / "compile.ps1"
    path.write_text(script, encoding="utf-8-sig")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path)], text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert "compiled" in result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell integration test")
def test_menu_identity_deduplicates_only_same_visible_item(tmp_path):
    script = taskbar_pin._SCRIPT.split("$exe =", 1)[0] + r'''
$item = [System.Windows.Rect]::new(10, 20, 100, 30)
$menu = [System.Windows.Rect]::new(0, 0, 200, 300)
$other = [System.Windows.Rect]::new(10, 50, 100, 30)
Write-Output ([PinWindow]::SameMenuItem([int[]](1,2), [int[]](1,2), $item, $other, $menu, $menu))
Write-Output ([PinWindow]::SameMenuItem([int[]](1,2), [int[]](3,4), $item, $item, $menu, $menu))
Write-Output ([PinWindow]::SameMenuItem([int[]](1,2), [int[]](3,4), $item, $other, $menu, $menu))
'''
    path = tmp_path / "identity.ps1"
    path.write_text(script, encoding="utf-8-sig")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path)], text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[-3:] == ["True", "True", "False"]


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell integration test")
def test_classic_popup_requires_matching_thread_process_and_owner(tmp_path):
    script = taskbar_pin._SCRIPT.split("$exe =", 1)[0] + r'''
Write-Output ([PinWindow]::IsTargetMenu(7,7,10,10,$true,$true))
Write-Output ([PinWindow]::IsTargetMenu(7,8,10,10,$true,$true))
Write-Output ([PinWindow]::IsTargetMenu(7,7,11,10,$true,$true))
Write-Output ([PinWindow]::IsTargetMenu(7,7,10,10,$false,$true))
Write-Output ([PinWindow]::IsTargetMenu(7,7,10,10,$true,$false))
'''
    path = tmp_path / "owner.ps1"
    path.write_text(script, encoding="utf-8-sig")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path)], text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[-5:] == ["True", "False", "False", "False", "False"]


def test_pin_returns_readable_error_and_uses_timeout(tmp_path, monkeypatch):
    exe = tmp_path / "app.exe"
    exe.touch()
    captured = {}
    monkeypatch.setattr(taskbar_pin.sys, "platform", "win32")

    real_popen = subprocess.Popen
    def run(command, **kwargs):
        captured.update(kwargs)
        captured["path"] = Path(command[-1])
        captured["script"] = captured["path"].read_text(encoding="utf-8-sig")
        kwargs.pop("creationflags")
        return real_popen([sys.executable, "-u", "-c", "import sys; print('TASKBAR_PIN_ERROR: Expected highlighted menu item \\\'Pin to taskbar\\\' was not verified.'); sys.exit(1)"], **kwargs)

    monkeypatch.setattr(taskbar_pin.subprocess, "Popen", run)
    success, diagnostic = taskbar_pin.pin_executable(str(exe))
    assert not success
    assert diagnostic == "Expected highlighted menu item 'Pin to taskbar' was not verified."
    assert base64.b64encode(str(exe).encode()).decode() in captured["script"]
    assert not captured["path"].exists()


def test_timeout_preserves_last_stage(tmp_path, monkeypatch):
    exe = tmp_path / "app.exe"
    exe.touch()
    monkeypatch.setattr(taskbar_pin.sys, "platform", "win32")
    real_popen = subprocess.Popen
    paths = []
    def launch(command, **kwargs):
        paths.append(Path(command[-1]))
        kwargs.pop("creationflags")
        return real_popen([sys.executable, "-u", "-c", "import time; print('TASKBAR_PIN_STAGE: First menu detected; sending 16 Down keys.', flush=True); time.sleep(10)"], **kwargs)
    monkeypatch.setattr(taskbar_pin.subprocess, "Popen", launch)
    monkeypatch.setattr(taskbar_pin, "PIN_TIMEOUT_SECONDS", 1)
    stages = []
    success, diagnostic = taskbar_pin.pin_executable(str(exe), on_stage=stages.append)
    assert not success
    assert stages == ["First menu detected; sending 16 Down keys."]
    assert "timed out" in diagnostic
    assert not paths[0].exists()


def test_script_removed_when_launch_fails(tmp_path, monkeypatch):
    exe = tmp_path / "app.exe"
    exe.touch()
    monkeypatch.setattr(taskbar_pin.sys, "platform", "win32")
    paths = []

    def launch(command, **kwargs):
        paths.append(Path(command[-1]))
        assert paths[0].exists()
        raise OSError("launch failed")

    monkeypatch.setattr(taskbar_pin.subprocess, "Popen", launch)
    success, diagnostic = taskbar_pin.pin_executable(str(exe))
    assert not success
    assert "launch failed" in diagnostic
    assert not paths[0].exists()


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell integration test")
def test_long_script_runs_from_file_and_is_removed(tmp_path, monkeypatch):
    exe = tmp_path / "app ü.exe"
    exe.touch()
    monkeypatch.setattr(taskbar_pin, "_SCRIPT", "#" + "x" * 40000 + "\n[Console]::Out.WriteLine('TASKBAR_PIN_STAGE: long script ran')")
    real_popen = subprocess.Popen
    paths = []

    def launch(command, **kwargs):
        assert "-File" in command
        assert len(subprocess.list2cmdline(command)) < 32767
        paths.append(Path(command[-1]))
        assert paths[0].stat().st_size > 32767
        return real_popen(command, **kwargs)

    monkeypatch.setattr(taskbar_pin.subprocess, "Popen", launch)
    stages = []
    success, diagnostic = taskbar_pin.pin_executable(str(exe), on_stage=stages.append)
    assert success, diagnostic
    assert stages == ["long script ran"]
    assert not paths[0].exists()


def test_pin_handles_unexpected_output_encoding_and_exit(tmp_path, monkeypatch):
    exe = tmp_path / "app.exe"
    exe.touch()
    monkeypatch.setattr(taskbar_pin.sys, "platform", "win32")
    real_popen = subprocess.Popen
    def launch(_command, **kwargs):
        kwargs.pop("creationflags")
        return real_popen([sys.executable, "-u", "-c", "import sys; sys.stdout.buffer.write(b'bad \\xff\\n'); sys.exit(3)"], **kwargs)
    monkeypatch.setattr(taskbar_pin.subprocess, "Popen", launch)
    success, diagnostic = taskbar_pin.pin_executable(str(exe))
    assert not success
    assert "code 3" in diagnostic
    assert "bad" in diagnostic


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell integration test")
@pytest.mark.parametrize("outcome", ["success", "failure", "timeout"])
def test_real_helper_stages_and_result_reach_build_log(tmp_path, monkeypatch, outcome):
    from exe_builder.controllers.build_controller import BuildController

    target = tmp_path / "app"
    target.mkdir()
    (target / "app.exe").touch()
    log = tmp_path / "build.log"
    script = "[Console]::Out.WriteLine('TASKBAR_PIN_STAGE: first stage'); [Console]::Out.Flush();\n"
    script += "[Console]::Out.WriteLine('TASKBAR_PIN_STAGE: menu snapshot observed'); [Console]::Out.Flush();\n"
    if outcome == "failure":
        script += "throw 'selection could not be verified'"
    elif outcome == "timeout":
        script += "Start-Sleep -Seconds 10"
        monkeypatch.setattr(taskbar_pin, "PIN_TIMEOUT_SECONDS", 2)
    monkeypatch.setattr(taskbar_pin, "_SCRIPT", script)
    controller = BuildController(SimpleNamespace(debug_log_path=str(log)))
    controller._pin_completed_python_output(str(target))
    contents = log.read_text(encoding="utf-8")
    assert contents.index("Taskbar pin started") < contents.index("first stage") < contents.index("menu snapshot observed")
    if outcome == "success":
        assert "Taskbar pin command invoked" in contents
        assert "not independently verified" in contents
    elif outcome == "failure":
        assert "Taskbar pin stopped" in contents
        assert "selection could not be verified" in contents
    else:
        assert "Taskbar pin stopped" in contents
        assert "timed out" in contents
