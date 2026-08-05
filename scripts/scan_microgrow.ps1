$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Virtual environment missing. Run scripts\setup_windows.ps1 first." }
& $python -m gaia project scan microgrow-v1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $python -m gaia project snapshot microgrow-v1
