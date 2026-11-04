import os
import subprocess
import sys
from pathlib import Path


def test_direct_main_imports_without_project_on_pythonpath(tmp_path):
    script = Path(__file__).resolve().parents[1] / "exe_builder" / "main.py"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-I", "-c", "import runpy, sys; runpy.run_path(sys.argv[1], run_name='startup_check')", str(script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
