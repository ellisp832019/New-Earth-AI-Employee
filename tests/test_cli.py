from typer.testing import CliRunner

from gaia.cli import app
from tests.governance_helpers import FakeGovernanceContextService, sample_governance_context


def test_doctor_and_projects_list(settings_file):
    runner = CliRunner()
    result = runner.invoke(app, ["doctor", "--config", str(settings_file)])
    assert result.exit_code == 0
    assert "GAIA Doctor" in result.output

    result = runner.invoke(app, ["projects", "list", "--config", str(settings_file)])
    assert result.exit_code == 0
    assert "Registered projects" in result.output


def test_ask_and_runs(settings_file):
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["ask", "sample", "What was completed most recently?", "--deterministic-only", "--config", str(settings_file)],
    )
    assert result.exit_code == 0
    assert "Ask Result" in result.output

    result = runner.invoke(app, ["agent", "runs", "list", "--config", str(settings_file)])
    assert result.exit_code == 0
    assert "run_id" in result.output


def test_project_officer_commands(settings_file):
    runner = CliRunner()
    result = runner.invoke(app, ["project-officer", "capabilities", "--config", str(settings_file)])
    assert result.exit_code == 0
    assert "project_officer_portfolio" in result.output

    result = runner.invoke(app, ["project-officer", "health", "sample", "--config", str(settings_file)])
    assert result.exit_code == 0
    assert "normalized_status" in result.output

    result = runner.invoke(app, ["project-officer", "work-packages", "--config", str(settings_file)])
    assert result.exit_code == 0
    assert result.output


def test_governance_commands(settings, settings_file, monkeypatch):
    from gaia.db import Database
    from gaia.service import ProjectService

    service = ProjectService(settings, Database(settings.database_path))
    service.governance_context_service = FakeGovernanceContextService(sample_governance_context())
    monkeypatch.setattr("gaia.cli._service", lambda config=None: service)

    runner = CliRunner()
    result = runner.invoke(app, ["governance", "status", "--config", str(settings_file)])
    assert result.exit_code == 0
    assert "snapshot-001" in result.output

    result = runner.invoke(app, ["governance", "brief", "--config", str(settings_file)])
    assert result.exit_code == 0
    assert "Architecture Governance" in result.output

    result = runner.invoke(app, ["governance", "work-package", "finding-001", "--config", str(settings_file)])
    assert result.exit_code == 0
    assert "NEOS-GOV-001" in result.output
