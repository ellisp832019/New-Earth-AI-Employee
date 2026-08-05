[CmdletBinding()]
param(
    [string]$OutputPath = "contracts\openapi\gaia-v1.json"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python interpreter not found: $python"
}

$output = Join-Path $PWD $OutputPath
$outputDir = Split-Path -Parent $output
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$script = @"
from pathlib import Path
import json
from gaia.api import app

target = Path(r"$($output -replace '\\', '\\\\')")
schema = app.openapi()
target.write_text(json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8")
"@

$scriptPath = Join-Path $env:TEMP "gaia_export_openapi.py"
Set-Content -Path $scriptPath -Value $script -Encoding UTF8
& $python $scriptPath
if ($LASTEXITCODE -ne 0) {
    throw "OpenAPI export failed."
}

Write-Host "OpenAPI contract exported to $output" -ForegroundColor Green
