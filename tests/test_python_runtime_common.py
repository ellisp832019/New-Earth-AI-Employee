from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell portability tests")


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
REPO_PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"


def _run_powershell(command: str, *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=cwd or REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _runtime_from_output(stdout: str) -> dict[str, str]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _version_status_from_output(stdout: str) -> dict[str, object]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _helper_command(extra: str = "") -> str:
    helper = SCRIPTS_DIR / "python_runtime_common.ps1"
    base = (
        f". '{helper}'; "
        f"$runtime = Resolve-GaiaPythonRuntime -RepoRoot '{REPO_ROOT}'{extra}; "
        "$runtime | ConvertTo-Json -Compress"
    )
    return base


def _run_version_status(
    *,
    cwd: Path,
    python_path: Path,
    script_path: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    version_status_script = script_path or (SCRIPTS_DIR / "version_status.ps1")
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(version_status_script),
        "-PythonPath",
        str(python_path),
    ]
    return subprocess.run(command, cwd=cwd, env=env, check=False, capture_output=True, text=True)


def _create_detached_worktree(tmp_path: Path) -> Path:
    worktree = tmp_path / "detached-worktree"
    subprocess.run(
        ["git", "worktree", "add", str(worktree)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(worktree), "switch", "--detach", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    shutil.copy2(SCRIPTS_DIR / "version_status.ps1", worktree / "scripts" / "version_status.ps1")
    return worktree


def test_local_venv_resolution_works() -> None:
    result = _run_powershell(_helper_command())
    assert result.returncode == 0, result.stderr
    runtime = _runtime_from_output(result.stdout)
    assert runtime["Source"] == "venv"
    assert runtime["Path"].lower().endswith(r"\.venv\scripts\python.exe")


def test_explicit_interpreter_selection_works() -> None:
    explicit_python = Path(sys.executable)
    result = _run_powershell(_helper_command(f" -PythonPath '{explicit_python}'"))
    assert result.returncode == 0, result.stderr
    runtime = _runtime_from_output(result.stdout)
    assert runtime["Source"] == "explicit"
    assert Path(runtime["Path"]).resolve() == explicit_python.resolve()


def test_path_based_resolution_works_without_venv(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    python_cmd = stub_dir / "python.cmd"
    python_cmd.write_text(
        textwrap.dedent(
            """
            @echo off
            if "%~1"=="--version" (
              echo Python 3.99.0
              exit /b 0
            )
            echo Python 3.99.0
            exit /b 0
            """
        ).strip()
        + "\r\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.pop("GAIA_PYTHON", None)
    env["PATH"] = f"{stub_dir};{env['PATH']}"
    command = (
        f". '{SCRIPTS_DIR / 'python_runtime_common.ps1'}'; "
        f"$runtime = Resolve-GaiaPythonRuntime -RepoRoot '{repo_root}'; "
        "$runtime | ConvertTo-Json -Compress"
    )
    result = _run_powershell(command, cwd=repo_root, env=env)
    assert result.returncode == 0, result.stderr
    runtime = _runtime_from_output(result.stdout)
    assert runtime["Source"] == "path"
    assert Path(runtime["Path"]).name.lower() == "python.cmd"


def test_invalid_explicit_path_fails() -> None:
    invalid_python = REPO_ROOT / "does-not-exist" / "python.exe"
    result = _run_powershell(_helper_command(f" -PythonPath '{invalid_python}'"))
    assert result.returncode != 0
    combined_output = f"{result.stdout}\n{result.stderr}"
    assert "Explicit Python interpreter not found" in combined_output


def test_openapi_export_is_stable_with_explicit_python() -> None:
    contract = REPO_ROOT / "contracts" / "openapi" / "gaia-v1.json"
    before = contract.read_text(encoding="utf-8")
    explicit_python = REPO_PYTHON
    command = f"& '{SCRIPTS_DIR / 'export_openapi_contract.ps1'}' -PythonPath '{explicit_python}'"
    result = _run_powershell(command, cwd=REPO_ROOT)
    assert result.returncode == 0, result.stderr
    after = contract.read_text(encoding="utf-8")
    assert after == before


def test_scripts_do_not_embed_personal_absolute_paths() -> None:
    forbidden_fragments = [
        r"C:\Users\ellis",
        r"D:\Dev\Projects\New-Earth-AI-Employee",
    ]
    script_paths = [
        path
        for path in SCRIPTS_DIR.glob("*.ps1")
        if path.name not in {"setup_windows.ps1"}
    ]
    for script_path in script_paths:
        content = script_path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in content, f"{fragment} leaked into {script_path}"


def test_version_status_reports_named_branch() -> None:
    explicit_python = REPO_PYTHON
    result = _run_version_status(cwd=REPO_ROOT, python_path=explicit_python)
    assert result.returncode == 0, result.stderr
    status = _version_status_from_output(result.stdout)
    assert status["gitRefState"] == "branch"
    assert status["gitBranch"] == "planning/gaia-v0.9-b1-multi-project-registry"
    assert status["gitSha"] == subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_version_status_reports_detached_head(tmp_path: Path) -> None:
    explicit_python = REPO_PYTHON
    worktree = _create_detached_worktree(tmp_path)
    try:
        result = _run_version_status(
            cwd=worktree,
            python_path=explicit_python,
            script_path=worktree / "scripts" / "version_status.ps1",
        )
        assert result.returncode == 0, result.stderr
        status = _version_status_from_output(result.stdout)
        assert status["gitRefState"] == "detached"
        assert status["gitBranch"] == "detached"
        assert status["gitSha"] == subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )


def test_version_status_honors_github_head_ref(tmp_path: Path) -> None:
    explicit_python = REPO_PYTHON
    worktree = _create_detached_worktree(tmp_path)
    env = os.environ.copy()
    env["GITHUB_HEAD_REF"] = "gaia-v0.6-dashboard-integration-and-trust"
    env["GITHUB_REF_NAME"] = "6/merge"
    try:
        result = _run_version_status(
            cwd=worktree,
            python_path=explicit_python,
            script_path=worktree / "scripts" / "version_status.ps1",
            env=env,
        )
        assert result.returncode == 0, result.stderr
        status = _version_status_from_output(result.stdout)
        assert status["gitRefState"] == "pull_request"
        assert status["gitBranch"] == "gaia-v0.6-dashboard-integration-and-trust"
        assert status["gitSha"] == subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
