import subprocess

from gaia.db import Database
from gaia.service import ProjectService


def git_status(repo):
    return subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=repo, text=True, capture_output=True, check=True
    ).stdout


def test_complete_workflow_is_read_only(settings, sample_repo):
    before = git_status(sample_repo)
    service = ProjectService(settings, Database(settings.database_path))
    documents = service.scan("sample")
    snapshot = service.snapshot("sample")
    report = service.foundation_report("sample")
    after = git_status(sample_repo)
    assert documents
    assert snapshot.project_id == "sample"
    assert "GAIA Foundation Report" in report
    assert before == after
    service.database.close()


def test_snapshot_marks_missing_important_path(settings):
    service = ProjectService(settings, Database(settings.database_path))
    service.scan("sample")
    snapshot = service.snapshot("sample")
    assert snapshot.important_paths["README.md"] is True
    assert snapshot.important_paths["missing.md"] is False
    service.database.close()
