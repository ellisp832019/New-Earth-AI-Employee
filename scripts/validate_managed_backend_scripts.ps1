[CmdletBinding()]
param(
    [int]$Port = 8000,
    [string]$PythonPath = $null
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

. "$PSScriptRoot\python_runtime_common.ps1"
. "$PSScriptRoot\managed_backend_common.ps1"

$pythonRuntime = Resolve-GaiaPythonRuntime -RepoRoot $PWD.Path -PythonPath $PythonPath
$python = $pythonRuntime.Path
$paths = Get-GaiaManagedBackendPaths -RepoRoot $PWD.Path -PythonPath $python

$expectedVersion = (Invoke-GaiaPython -PythonPath $python -Arguments @("-c", "import gaia; print(gaia.__version__)") | Out-String).Trim()
$stateBefore = Get-GaiaManagedBackendSnapshot -RepoRoot $PWD.Path -Port $Port -ExpectedBackendVersion $expectedVersion -PythonPath $python
Write-Host ("Managed backend preflight state: {0}" -f $stateBefore.State)
if ($stateBefore.State -eq "external") {
    throw $stateBefore.Reason
}

if ($stateBefore.State -eq "unmanaged") {
    throw $stateBefore.Reason
}

if ($stateBefore.State -in @("healthy", "incompatible")) {
    Write-Host "Existing managed backend detected; stopping it before validation."
    & $PSScriptRoot\stop_managed_backend.ps1 -Port $Port -PythonPath $python
}

$stateBefore = Get-GaiaManagedBackendSnapshot -RepoRoot $PWD.Path -Port $Port -ExpectedBackendVersion $expectedVersion -PythonPath $python
if ($stateBefore.State -notin @("missing", "stale")) {
    throw "Managed backend preflight did not clear cleanly: $($stateBefore.State)"
}

if ($stateBefore.ListenerOwningProcess) {
    throw "Port $Port is already occupied by process $($stateBefore.ListenerOwningProcess)."
}

& $PSScriptRoot\start_managed_backend.ps1 -Port $Port -PythonPath $python

$checkOutput = & $PSScriptRoot\check_managed_backend.ps1 -Port $Port -PythonPath $python
$checkJson = $checkOutput | ConvertFrom-Json
if ($checkJson.state -ne "healthy") {
    throw "Managed backend check did not report a healthy state."
}
if ($checkJson.backendVersion -ne $expectedVersion) {
    throw "Managed backend check reported version $($checkJson.backendVersion) but expected $expectedVersion."
}

$status = & $PSScriptRoot\version_status.ps1 -PythonPath $python | ConvertFrom-Json
foreach ($field in @("flutterVersion", "flutterChannel", "dartVersion", "frameworkRevision", "pythonPackageVersion", "gitBranch", "gitSha", "backendOwnershipState", "backendCompatibility")) {
    if (-not $status.$field) {
        throw "Version status is missing field '$field'."
    }
}

& $PSScriptRoot\stop_managed_backend.ps1 -Port $Port -PythonPath $python

$postStop = Get-GaiaManagedBackendSnapshot -RepoRoot $PWD.Path -Port $Port -ExpectedBackendVersion $expectedVersion -PythonPath $python
if ($postStop.State -ne "missing" -and $postStop.State -ne "stale") {
    throw "Managed backend stop did not clear the managed backend state."
}

if (Get-GaiaBackendListener -Port $Port) {
    throw "Port $Port is still listening after managed backend stop."
}

& $PSScriptRoot\start_managed_backend.ps1 -Port $Port -PythonPath $python

$secondCheck = & $PSScriptRoot\check_managed_backend.ps1 -Port $Port -PythonPath $python | ConvertFrom-Json
if ($secondCheck.state -ne "healthy") {
    throw "Managed backend restart did not become healthy."
}

& $PSScriptRoot\stop_managed_backend.ps1 -Port $Port -PythonPath $python | Out-Null

$finalState = Get-GaiaManagedBackendSnapshot -RepoRoot $PWD.Path -Port $Port -ExpectedBackendVersion $expectedVersion -PythonPath $python
if ($finalState.State -ne "missing" -and $finalState.State -ne "stale") {
    throw "Final shutdown did not clear the managed backend state."
}

if (Get-GaiaBackendListener -Port $Port) {
    throw "Port $Port is still listening after final shutdown."
}

Write-Host "Managed backend lifecycle validation passed." -ForegroundColor Green
