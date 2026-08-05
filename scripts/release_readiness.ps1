[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

& $PSScriptRoot\validate_managed_backend_scripts.ps1
& $PSScriptRoot\validate_vscode_workspace.ps1
& $PSScriptRoot\version_status.ps1 | Out-Null

Write-Host "GAIA v0.5.1 release readiness checks completed." -ForegroundColor Green
