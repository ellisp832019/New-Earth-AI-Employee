$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$tasks = Get-Content .vscode\tasks.json -Raw
@(
  'GAIA: Validate Receipt Chains',
  'GAIA: Create Offline Review Package',
  'GAIA: Verify Offline Review Package',
  'GAIA: List Action Templates',
  'GAIA: Validate Action Templates',
  'GAIA: Retention Dry Run',
  'GAIA: Validate Dashboard Module',
  'GAIA: Run Dashboard Example Host',
  'GAIA: Validate Integration Compatibility',
  'GAIA: Complete v0.6 Validation',
  'GAIA: v0.6 Release Readiness'
) | ForEach-Object {
  if ($tasks -notmatch [regex]::Escape($_)) {
    throw "Missing VS Code task: $_"
  }
}
Write-Host 'VS Code workspace validation passed.'
