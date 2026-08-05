from gaia.db import Database
from gaia.git_inspector import GitInspector
from gaia.scanner import DocumentScanner


def test_index_and_search(settings):
    database = Database(settings.database_path)
    project = settings.projects["sample"]
    records = DocumentScanner().scan(project, GitInspector().tracked_files(project.root))
    database.replace_documents("sample", records)
    results = database.search("sample", "MicroGrow")
    assert results
    assert results[0].relative_path == "README.md"
    database.close()


def test_search_fallback_without_fts(settings):
    database = Database(settings.database_path)
    database.fts5_available = False
    project = settings.projects["sample"]
    records = DocumentScanner().scan(project, GitInspector().tracked_files(project.root))
    database.replace_documents("sample", records)
    results = database.search("sample", "MicroGrow")
    assert results
    assert any(result.relative_path == "README.md" for result in results)
    database.close()


def test_audit_roundtrip(settings):
    from gaia.audit import AuditRecorder

    database = Database(settings.database_path)
    AuditRecorder(database).record(category="test", operation="roundtrip", outcome="success")
    events = database.list_audit_events()
    assert events[0]["operation"] == "roundtrip"
    database.close()
