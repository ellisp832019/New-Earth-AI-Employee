from pathlib import Path

import pytest
import yaml

from gaia.config import load_settings


def test_load_project(settings_file):
    settings = load_settings(settings_file)
    assert "sample" in settings.projects
    assert ".md" in settings.projects["sample"].approved_extensions
    assert settings.projects["sample"].access == "read_only"
    assert settings.projects["sample"].enabled is True
    assert settings.projects["sample"].repository_type == "git"
    assert settings.projects["sample"].health_rules == {}
    assert settings.projects["sample"].release_rules == {}


def test_load_project_extended_metadata(tmp_path: Path, sample_repo: Path) -> None:
    config = {
        "projects": {
            "sample": {
                "name": "Sample",
                "root": str(sample_repo),
                "access": "read_only",
                "enabled": True,
                "repository_type": "git",
                "inspection_access": "read_only",
                "output_access": "none",
                "sensitivity": "internal",
                "approved_extensions": [".md", ".txt"],
                "excluded_directories": [".git"],
                "excluded_filenames": [".env"],
                "important_paths": ["README.md", "docs"],
                "health_rules": {"required_paths": ["README.md", "docs"]},
                "release_rules": {"assume_unknown_when_no_upstream": True},
                "approval_requirements": {"registry_review": "required"},
                "metadata": {"owner": "sample"},
            }
        }
    }
    path = tmp_path / "projects.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    settings = load_settings(path)
    project = settings.projects["sample"]
    assert project.health_rules["required_paths"] == ["README.md", "docs"]
    assert project.release_rules["assume_unknown_when_no_upstream"] is True
    assert project.metadata["owner"] == "sample"


def test_rejects_duplicate_canonical_roots(tmp_path: Path, sample_repo: Path) -> None:
    config = {
        "projects": {
            "first": {
                "name": "First",
                "root": str(sample_repo),
                "access": "read_only",
                "approved_extensions": [".md"],
            },
            "second": {
                "name": "Second",
                "root": str(sample_repo),
                "access": "read_only",
                "approved_extensions": [".md"],
            },
        }
    }
    path = tmp_path / "projects.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ValueError, match="share the same canonical root"):
        load_settings(path)
