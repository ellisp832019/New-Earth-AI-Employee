import pytest

from gaia.security import PathSecurityError, is_secret_bearing_filename, resolve_project_path


def test_allows_approved_file(settings):
    project = settings.projects["sample"]
    path = resolve_project_path(project, "README.md")
    assert path.name == "README.md"


def test_allows_mixed_separators_and_case(settings):
    project = settings.projects["sample"]
    path = resolve_project_path(project, "DOCS\\STATUS.MD")
    assert path.name == "status.md"


def test_rejects_traversal(settings, tmp_path):
    project = settings.projects["sample"]
    outside = tmp_path / "outside.md"
    outside.write_text("outside")
    with pytest.raises(PathSecurityError):
        resolve_project_path(project, outside)


def test_rejects_nested_traversal(settings, tmp_path):
    project = settings.projects["sample"]
    outside = tmp_path.parent / "outside.md"
    outside.write_text("outside")
    requested = tmp_path / "docs" / ".." / ".." / "outside.md"
    with pytest.raises(PathSecurityError):
        resolve_project_path(project, requested)


def test_rejects_excluded_file(settings):
    project = settings.projects["sample"]
    with pytest.raises(PathSecurityError):
        resolve_project_path(project, ".env")


def test_rejects_disallowed_extension(settings):
    project = settings.projects["sample"]
    file = project.root / "binary.exe"
    file.write_bytes(b"MZ")
    with pytest.raises(PathSecurityError):
        resolve_project_path(project, file)


def test_rejects_excluded_directory(settings):
    project = settings.projects["sample"]
    target = project.root / "build"
    target.mkdir()
    file = target / "notes.md"
    file.write_text("notes")
    with pytest.raises(PathSecurityError):
        resolve_project_path(project, file)


def test_secret_name_detection():
    assert is_secret_bearing_filename("api_key.txt")
    assert is_secret_bearing_filename("credentials.json")
    assert not is_secret_bearing_filename("README.md")
