[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

& .\scripts\release_readiness.ps1

Write-Host "GAIA v0.4 validation completed." -ForegroundColor Green
