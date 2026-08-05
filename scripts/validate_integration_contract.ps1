[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$contract = Join-Path $PWD "contracts\openapi\gaia-v1.json"
if (-not (Test-Path $contract)) {
    throw "Missing OpenAPI contract: $contract"
}

$schema = Get-Content $contract -Raw | ConvertFrom-Json
$paths = $schema.paths.PSObject.Properties.Name
foreach ($required in @("/integration/v1/compatibility", "/actions", "/receipts")) {
    if ($paths -notcontains $required) {
        throw "OpenAPI contract is missing path $required"
    }
}

Write-Host "Integration contract validation passed." -ForegroundColor Green
