# Test Results

## Focused Governance Tests

- `python -m pytest -q tests/test_governance_context.py tests/test_api.py::test_governance_api_endpoints tests/test_cli.py::test_governance_commands`
- passed

## Regression Tests

- `python -m pytest -q tests/test_project_health.py tests/test_programme_registry.py tests/test_workflows.py::test_database_migration_preserves_existing_data`
- passed

## Validation

- `python -m pip install -e ".[dev]"`
- passed
- `python -m pytest -q`
- passed
- `python -m ruff check src tests`
- passed
- `python -m mypy src\gaia`
- passed
- `python -m gaia doctor`
- passed
- `python -m gaia --help`
- passed
- full pytest count: 131 collected tests
- `python -m pytest -q`
- passed

## OpenAPI

- `powershell -ExecutionPolicy Bypass -File .\scripts\export_openapi_contract.ps1`
- passed
