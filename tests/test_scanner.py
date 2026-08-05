from gaia.git_inspector import GitInspector
from gaia.scanner import DocumentScanner


def test_scans_approved_documents(settings):
    project = settings.projects["sample"]
    tracked = GitInspector().tracked_files(project.root)
    records = DocumentScanner().scan(project, tracked)
    paths = {record.relative_path for record in records}
    assert paths == {"README.md", "docs/status.md"}
    assert all(record.indexing_status == "indexed" for record in records)
    assert ".env" not in paths


def test_skips_secret_bearing_names(settings):
    project = settings.projects["sample"]
    (project.root / "api_key.txt").write_text("super-secret", encoding="utf-8")
    records = DocumentScanner().scan(project, GitInspector().tracked_files(project.root))
    assert "api_key.txt" not in {record.relative_path for record in records}


def test_handles_invalid_utf8_and_stable_hash(settings):
    project = settings.projects["sample"]
    target = project.root / "broken.txt"
    target.write_bytes(b"hello\xffworld")
    scanner = DocumentScanner()
    first = {record.relative_path: record for record in scanner.scan(project)}
    second = {record.relative_path: record for record in scanner.scan(project)}
    assert first["broken.txt"].warning == "Invalid UTF-8 bytes were replaced"
    assert "�" in (first["broken.txt"].content or "")
    assert first["broken.txt"].sha256 == second["broken.txt"].sha256


def test_skips_large_file(settings):
    project = settings.projects["sample"]
    (project.root / "large.txt").write_text("x" * 100)
    records = DocumentScanner(max_file_bytes=20).scan(project)
    large = next(record for record in records if record.relative_path == "large.txt")
    assert large.indexing_status == "skipped"
    assert large.content is None
