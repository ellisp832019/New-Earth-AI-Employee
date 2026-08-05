from __future__ import annotations

import re
import subprocess
from pathlib import Path

from gaia.models import GitCommandResult, GitState


class GitInspectionError(RuntimeError):
    pass


class GitInspector:
    def __init__(self, timeout_seconds: int = 15, max_output_bytes: int = 1_000_000) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes

    def _run(self, repo: Path, operation: str, args: list[str], allow_failure: bool = False) -> GitCommandResult:
        fixed = ["git", "-C", str(repo), *args]
        try:
            completed = subprocess.run(
                fixed,
                capture_output=True,
                text=False,
                shell=False,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return GitCommandResult(
                operation=operation,
                args=args,
                return_code=124,
                stdout="",
                stderr=str(exc),
                timed_out=True,
            )
        stdout_bytes = completed.stdout or b""
        stderr_bytes = completed.stderr or b""
        truncated = len(stdout_bytes) > self.max_output_bytes or len(stderr_bytes) > self.max_output_bytes
        stdout = stdout_bytes[: self.max_output_bytes].decode("utf-8", errors="replace")
        stderr = stderr_bytes[: self.max_output_bytes].decode("utf-8", errors="replace")
        result = GitCommandResult(
            operation=operation,
            args=args,
            return_code=completed.returncode,
            stdout=stdout.strip(),
            stderr=stderr.strip(),
            truncated=truncated,
        )
        if completed.returncode != 0 and not allow_failure:
            raise GitInspectionError(f"Git operation '{operation}' failed: {result.stderr}")
        return result

    def inspect(self, repo: Path) -> GitState:
        repo = repo.resolve(strict=True)
        root = self._run(repo, "repository_root", ["rev-parse", "--show-toplevel"]).stdout
        status = self._run(repo, "status_porcelain", ["status", "--porcelain=v1", "--untracked-files=all"]).stdout
        branch_result = self._run(repo, "current_branch", ["branch", "--show-current"], allow_failure=True)
        commit_result = self._run(repo, "commit_sha", ["rev-parse", "HEAD"], allow_failure=True)
        recent = self._run(
            repo,
            "recent_commits",
            ["log", "-n", "20", "--pretty=format:%h%x09%ad%x09%s", "--date=iso-strict"],
            allow_failure=True,
        )
        branches = self._run(repo, "branches", ["branch", "--format=%(refname:short)"], allow_failure=True)
        tags = self._run(repo, "tags", ["tag", "--list"], allow_failure=True)
        remotes = self._run(repo, "remotes", ["remote", "-v"], allow_failure=True)
        tracked = self._run(repo, "tracked_files", ["ls-files"], allow_failure=True)
        upstream = self._run(
            repo,
            "ahead_behind",
            ["rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
            allow_failure=True,
        )

        lines = status.splitlines() if status else []
        untracked = [line[3:] for line in lines if line.startswith("?? ")]
        changed = [line[3:] for line in lines if not line.startswith("?? ") and len(line) >= 4]
        ahead = behind = None
        if upstream.return_code == 0 and upstream.stdout:
            parts = re.split(r"\s+", upstream.stdout.strip())
            if len(parts) == 2 and all(part.isdigit() for part in parts):
                ahead, behind = int(parts[0]), int(parts[1])

        warnings = []
        if recent.truncated or status and len(status.encode()) >= self.max_output_bytes:
            warnings.append("One or more Git outputs were truncated")
        if upstream.return_code != 0:
            warnings.append("No upstream branch was available for ahead/behind calculation")

        return GitState(
            repository_root=root or str(repo),
            branch=branch_result.stdout or None,
            commit_sha=commit_result.stdout or None,
            is_clean=not bool(lines),
            status_porcelain=lines,
            recent_commits=recent.stdout.splitlines() if recent.stdout else [],
            branches=branches.stdout.splitlines() if branches.stdout else [],
            tags=tags.stdout.splitlines() if tags.stdout else [],
            remotes=_redact_remotes(remotes.stdout.splitlines() if remotes.stdout else []),
            ahead=ahead,
            behind=behind,
            tracked_file_count=len(tracked.stdout.splitlines()) if tracked.stdout else 0,
            untracked_files=untracked,
            changed_files=changed,
            warnings=warnings,
        )

    def tracked_files(self, repo: Path) -> set[str]:
        result = self._run(repo, "tracked_files", ["ls-files"], allow_failure=True)
        return {line.replace("\\", "/") for line in result.stdout.splitlines()} if result.stdout else set()


def _redact_remotes(lines: list[str]) -> list[str]:
    redacted = []
    for line in lines:
        line = re.sub(r"https://[^/@\s]+:[^/@\s]+@", "https://***:***@", line)
        line = re.sub(r"https://[^/@\s]+@", "https://***@", line)
        redacted.append(line)
    return redacted
