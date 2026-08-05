$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Virtual environment missing. Run scripts\setup_windows.ps1 first." }
& $python -m gaia serve
