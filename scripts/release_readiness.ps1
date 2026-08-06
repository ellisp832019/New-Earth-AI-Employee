$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
git status --short --branch
git diff --check

& $PSScriptRoot\validate_managed_backend_scripts.ps1
& $PSScriptRoot\validate_vscode_workspace.ps1
& $PSScriptRoot\run_v0_7_validation.ps1
& $PSScriptRoot\validate_provenance_manifests.ps1
& $PSScriptRoot\validate_signatures.ps1
& $PSScriptRoot\validate_signing_key_lifecycle.ps1
& $PSScriptRoot\validate_trust_alerts.ps1
& $PSScriptRoot\generate_retention_report.ps1
& $PSScriptRoot\validate_dashboard_conformance.ps1
& $PSScriptRoot\validate_embedded_operations_workspace.ps1
