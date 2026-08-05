$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
& ".\scripts\run_tests.ps1"
& ".\scripts\scan_microgrow.ps1"
& ".\scripts\generate_report.ps1"
Write-Host "First run complete. Open data\reports\MICROGROW_FOUNDATION_REPORT.md" -ForegroundColor Green
