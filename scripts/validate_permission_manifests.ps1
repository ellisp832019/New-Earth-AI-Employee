[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python interpreter not found: $python"
}

$script = @"
from gaia.config import load_settings
from gaia.db import Database
from gaia.output_workspace import OutputWorkspaceService

settings = load_settings()
service = OutputWorkspaceService(settings, Database(settings.database_path))
try:
    manifests = service.list_permission_manifests()
    print(f"Permission manifests: {len(manifests)}")
    for manifest in manifests:
        print(service.validate_permission_manifest(manifest.manifest_id))
finally:
    service.database.close()
"@

$scriptPath = Join-Path $env:TEMP "gaia_validate_permissions.py"
Set-Content -Path $scriptPath -Value $script -Encoding UTF8
& $python $scriptPath
if ($LASTEXITCODE -ne 0) {
    throw "Permission manifest validation failed."
}

Write-Host "Permission manifest validation passed." -ForegroundColor Green
