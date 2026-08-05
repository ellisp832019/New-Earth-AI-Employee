[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

& .\.venv\Scripts\python.exe -m compileall src tests
& .\.venv\Scripts\python.exe -m ruff check src tests
& .\.venv\Scripts\python.exe -m mypy src\gaia
& .\.venv\Scripts\python.exe -m pytest

Push-Location apps\gaia_windows
try {
    flutter analyze
    flutter test
    flutter build windows --debug
    flutter build windows --release
} finally {
    Pop-Location
}

Write-Host "GAIA v0.3 validation completed." -ForegroundColor Green
