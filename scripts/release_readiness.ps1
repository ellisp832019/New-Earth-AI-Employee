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
    flutter pub get
    flutter analyze
    flutter test
    flutter build windows --debug
    flutter build windows --release
} finally {
    Pop-Location
}

powershell -NoProfile -ExecutionPolicy Bypass -File "${PWD}\scripts\validate_vscode_workspace.ps1"

git diff --check
git status --short --branch
git ls-files

Write-Host "GAIA v0.4 release readiness checks completed." -ForegroundColor Green
