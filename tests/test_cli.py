from typer.testing import CliRunner

from gaia.cli import app
from tests.governance_helpers import FakeGovernanceContextService, sample_governance_context
from tests.test_programme_intelligence import (
    _analyse_shared_contract_change,
    _build_settings,
    _seed_release_graph,
    _service_for,
)
from tests.test_programme_packages import _seed_reviewable_work_packages


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


def test_programme_commands(settings, monkeypatch, tmp_path):
    config = _build_settings(tmp_path, alpha_missing_path=False)
    service, database = _service_for(config, tmp_path, monkeypatch, db_name="cli-programme.db")

    class _ServiceProxy:
        def __init__(self, wrapped):
            self._wrapped = wrapped

        def close(self):
            return None

        def __getattr__(self, name):
            return getattr(self._wrapped, name)

    try:
        _seed_release_graph(service, relationship_order=["alpha", "beta"])
        impact = _analyse_shared_contract_change(service)
        _seed_reviewable_work_packages(service, ["alpha", "beta", "shared"])
        package_portfolio = service.programme_packages(change_impact_results=[impact])
        package_id = package_portfolio.programme_packages[0].programme_package_id

        monkeypatch.setattr("gaia.cli._service", lambda config=None: _ServiceProxy(service))
        runner = CliRunner()

        result = runner.invoke(app, ["programme", "overview", "--config", str(config)])
        assert result.exit_code == 0
        assert "selected_project_id" in result.output
        assert "trust_alert_count" in result.output

        result = runner.invoke(app, ["architecture", "list", "--config", str(config)])
        assert result.exit_code == 0
        assert "Shared Library" in result.output

        result = runner.invoke(app, ["architecture", "graph", "--config", str(config)])
        assert result.exit_code == 0
        assert "node_count" in result.output

        result = runner.invoke(app, ["impact", "analyse", "--config", str(config)])
        assert result.exit_code == 0
        assert "analysis_id" in result.output

        result = runner.invoke(app, ["release-train", "list", "--config", str(config)])
        assert result.exit_code == 0
        assert "release_train_id" in result.output

        result = runner.invoke(app, ["programme-package", "list", "--config", str(config)])
        assert result.exit_code == 0
        assert "programme_package_id" in result.output

        result = runner.invoke(
            app,
            ["programme-package", "show", package_id, "--config", str(config)],
        )
        assert result.exit_code == 0
        assert package_id in result.output
    finally:
        database.close()
