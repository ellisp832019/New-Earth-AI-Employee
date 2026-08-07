import subprocess

from gaia.git_inspector import GitInspector


def test_inspects_repository(sample_repo):
    state = GitInspector().inspect(sample_repo)
    assert state.commit_sha
    assert state.is_clean
    assert state.tracked_file_count == 3
    assert state.tracked_modifications_count == 0
    assert state.untracked_item_count == 0
    assert state.detached_head is False
    assert state.upstream_name is None
    assert state.branch in {"master", "main"}


def test_detects_untracked(sample_repo):
    (sample_repo / "new.md").write_text("new")
    state = GitInspector().inspect(sample_repo)
    assert not state.is_clean
    assert "new.md" in state.untracked_files
    assert state.untracked_item_count == 1


def test_detects_tracked_modifications(sample_repo):
    (sample_repo / "README.md").write_text("# changed\n")
    state = GitInspector().inspect(sample_repo)
    assert not state.is_clean
    assert state.tracked_modifications_count == 1


def test_reports_upstream_when_configured(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", str(remote), str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "README.md").write_text("# sample\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=repo, check=True, capture_output=True)
    state = GitInspector().inspect(repo)
    assert state.upstream_name in {"origin/main", "origin/master"}
    assert state.ahead == 0
    assert state.behind == 0


def test_redacts_remote_urls(sample_repo):
    subprocess.run(
        ["git", "remote", "add", "origin", "https://user:secret-token@example.com/repo.git"],
        cwd=sample_repo,
        check=True,
        capture_output=True,
    )
    state = GitInspector().inspect(sample_repo)
    assert state.remotes
    assert "secret-token" not in "\n".join(state.remotes)
    assert "***" in "\n".join(state.remotes)


def test_git_run_timeout(monkeypatch, sample_repo):
    inspector = GitInspector(timeout_seconds=1, max_output_bytes=10)

    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=1)

    monkeypatch.setattr("gaia.git_inspector.subprocess.run", fake_run)
    result = inspector._run(sample_repo, "timeout", ["status"])
    assert result.timed_out is True
    assert result.return_code == 124


def test_read_only_inspection_does_not_change_status(sample_repo):
    before = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=sample_repo, text=True, capture_output=True, check=True
    ).stdout
    GitInspector().inspect(sample_repo)
    after = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=sample_repo, text=True, capture_output=True, check=True
    ).stdout
    assert before == after
