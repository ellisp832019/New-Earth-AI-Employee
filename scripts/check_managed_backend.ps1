[CmdletBinding()]
param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

. "$PSScriptRoot\managed_backend_common.ps1"

$repoRoot = $PWD.Path
$paths = Get-GaiaManagedBackendPaths -RepoRoot $repoRoot
$python = $paths.PythonExe
if (-not (Test-Path $python)) {
    throw "Virtual environment missing. Run scripts\setup_windows.ps1 first."
}

$expectedVersion = (& $python -c "import gaia; print(gaia.__version__)").Trim()
$snapshot = Get-GaiaManagedBackendSnapshot -RepoRoot $repoRoot -Port $Port -ExpectedBackendVersion $expectedVersion

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
