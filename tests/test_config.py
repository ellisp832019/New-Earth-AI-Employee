from gaia.config import load_settings


def test_load_project(settings_file):
    settings = load_settings(settings_file)
    assert "sample" in settings.projects
    assert ".md" in settings.projects["sample"].approved_extensions
    assert settings.projects["sample"].access == "read_only"
