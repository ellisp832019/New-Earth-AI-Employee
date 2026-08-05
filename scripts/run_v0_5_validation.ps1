[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python interpreter not found: $python"
}

& $python -m compileall src tests
& $python -m ruff check src tests
& $python -m mypy src\gaia
& $python -m pytest

Push-Location apps\gaia_windows
try {
    flutter pub get
    flutter analyze
    flutter test
    flutter build windows --debug
    flutter build windows --release
} finally {
    Pop-Location
}

Push-Location packages\gaia_integration_client
try {
    dart pub get
    dart analyze
    dart test
} finally {
    Pop-Location
}

& $PSScriptRoot\export_openapi_contract.ps1
& $PSScriptRoot\validate_permission_manifests.ps1
& $PSScriptRoot\validate_integration_contract.ps1

Write-Host "GAIA v0.5 validation completed." -ForegroundColor Green
