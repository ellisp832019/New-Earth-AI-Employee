import subprocess

from gaia.git_inspector import GitInspector


def test_inspects_repository(sample_repo):
    state = GitInspector().inspect(sample_repo)
    assert state.commit_sha
    assert state.is_clean
    assert state.tracked_file_count == 3
    assert state.branch in {"master", "main"}


def test_detects_untracked(sample_repo):
    (sample_repo / "new.md").write_text("new")
    state = GitInspector().inspect(sample_repo)
    assert not state.is_clean
    assert "new.md" in state.untracked_files


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
