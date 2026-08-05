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
