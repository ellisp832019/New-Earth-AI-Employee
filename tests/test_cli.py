from typer.testing import CliRunner

from gaia.cli import app


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
