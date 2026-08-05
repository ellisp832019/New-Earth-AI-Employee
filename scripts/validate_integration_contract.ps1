$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& .\.venv\Scripts\python.exe -m compileall src\gaia
Set-Location $root\packages\gaia_integration_client
dart test
