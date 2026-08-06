[CmdletBinding()]
param(
    [int]$Port = 8000,
    [string]$PythonPath = $null
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

. "$PSScriptRoot\python_runtime_common.ps1"
. "$PSScriptRoot\managed_backend_common.ps1"

$repoRoot = $PWD.Path
$pythonRuntime = Resolve-GaiaPythonRuntime -RepoRoot $repoRoot -PythonPath $PythonPath
$python = $pythonRuntime.Path
$paths = Get-GaiaManagedBackendPaths -RepoRoot $repoRoot -PythonPath $python

$expectedVersion = (Invoke-GaiaPython -PythonPath $python -Arguments @('-c', 'import gaia; print(gaia.__version__)') | Out-String).Trim()
$snapshot = Get-GaiaManagedBackendSnapshot -RepoRoot $repoRoot -Port $Port -ExpectedBackendVersion $expectedVersion -PythonPath $python

$summary = [pscustomobject]@{
    state = $snapshot.State
    reason = $snapshot.Reason
    managedPid = $snapshot.ManagedPid
    port = $snapshot.Port
    repositoryRoot = $snapshot.RepoRoot
    backendVersion = $snapshot.BackendVersion
    backendCompatibility = $snapshot.BackendCompatibility
    listenerOwningProcess = $snapshot.ListenerOwningProcess
}

if ($snapshot.State -eq "healthy") {
    $summary | ConvertTo-Json -Compress
    exit 0
}

$exitCode = switch ($snapshot.State) {
    "missing" { 10 }
    "stale" { 11 }
    "unmanaged" { 12 }
    "external" { 13 }
    "incompatible" { 14 }
    default { 1 }
}

Write-Host ("Managed backend state: {0}" -f $snapshot.State)
if ($snapshot.Reason) {
    Write-Host $snapshot.Reason
}
$summary | ConvertTo-Json -Compress
exit $exitCode
