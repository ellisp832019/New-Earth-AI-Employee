$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& .\.venv\Scripts\python.exe -m compileall src\gaia
& .\.venv\Scripts\python.exe -m gaia templates list
& .\.venv\Scripts\python.exe -m gaia receipts chains
