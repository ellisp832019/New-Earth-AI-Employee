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

if ($snapshot.State -eq "missing" -or $snapshot.State -eq "stale") {
    Remove-GaiaManagedBackendArtifacts -Paths $paths
    Write-Host "Managed backend already stopped."
    exit 0
}

if ($snapshot.State -eq "external" -or $snapshot.State -eq "unmanaged") {
    throw $snapshot.Reason
}

if ($snapshot.State -eq "healthy" -or $snapshot.State -eq "incompatible") {
    $managedPid = [int]$snapshot.ManagedPid
    $processInfo = Get-GaiaManagedBackendProcess -ManagedPid $managedPid
    if (-not $processInfo) {
        Remove-GaiaManagedBackendArtifacts -Paths $paths
        Write-Host "Managed backend already stopped."
        exit 0
    }

    $identity = Test-GaiaManagedBackendIdentity -RepoRoot $repoRoot -Port $Port -ExpectedPythonPath $paths.PythonExe -ProcessRecord $processInfo -MetaRecord (Read-GaiaManagedBackendMeta -MetaFile $paths.MetaFile)
    $treeIds = Get-GaiaManagedBackendProcessTreeIds -RootProcessId $managedPid
    if (-not $identity.IsManagedProcess -or -not $snapshot.ListenerOwningProcess -or -not $treeIds.Contains([int]$snapshot.ListenerOwningProcess)) {
        throw "Refusing to stop process $managedPid because it is not the managed GAIA backend."
    }

    foreach ($treeProcessId in ($treeIds | Sort-Object -Descending)) {
        Stop-Process -Id $treeProcessId -Force -ErrorAction SilentlyContinue
    }
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        $listener = Get-GaiaBackendListener -Port $Port
        if (-not $listener) {
            break
        }
        Start-Sleep -Seconds 1
    }

    if (Get-GaiaBackendListener -Port $Port) {
        throw "Managed backend port $Port did not close after stop."
    }

    Remove-GaiaManagedBackendArtifacts -Paths $paths
    Write-Host "Managed backend stopped."
    exit 0
}

throw $snapshot.Reason
