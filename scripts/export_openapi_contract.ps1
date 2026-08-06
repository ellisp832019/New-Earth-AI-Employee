[CmdletBinding()]
param(
    [string]$OutputPath = "contracts\openapi\gaia-v1.json",
    [string]$PythonPath = $null
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

. "$PSScriptRoot\python_runtime_common.ps1"

$pythonRuntime = Resolve-GaiaPythonRuntime -RepoRoot $PWD.Path -PythonPath $PythonPath

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
Invoke-GaiaPython -PythonPath $pythonRuntime.Path -Arguments @($scriptPath) | Out-Null

Write-Host "OpenAPI contract exported to $output" -ForegroundColor Green
