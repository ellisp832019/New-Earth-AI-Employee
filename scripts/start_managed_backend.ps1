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
New-Item -ItemType Directory -Force -Path $paths.RuntimeDir, $paths.LogDir | Out-Null

$stdoutLog = Join-Path $paths.LogDir "gaia-backend.out.log"
$stderrLog = Join-Path $paths.LogDir "gaia-backend.err.log"

$snapshot = Get-GaiaManagedBackendSnapshot -RepoRoot $repoRoot -Port $Port -ExpectedBackendVersion $expectedVersion -PythonPath $python
if ($snapshot.State -eq "healthy") {
    Write-Host "GAIA managed backend already running"
    Write-Host ("Managed backend PID: {0}" -f $snapshot.ManagedPid)
    exit 0
}

if ($snapshot.State -eq "incompatible") {
    throw $snapshot.Reason
}

if ($snapshot.State -eq "external" -or $snapshot.State -eq "unmanaged") {
    throw $snapshot.Reason
}

if ($snapshot.State -eq "stale") {
    if ($snapshot.ListenerOwningProcess) {
        throw $snapshot.Reason
    }
    Remove-GaiaManagedBackendArtifacts -Paths $paths
}

Write-Host "GAIA managed backend starting"

$managedProcess = Start-Process `
    -FilePath $python `
    -ArgumentList @("-m", "gaia", "serve", "--host", "127.0.0.1", "--port", "$Port") `
    -WorkingDirectory $repoRoot `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog

try {
    $health = $null
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        try {
            $health = Invoke-GaiaBackendHealth -Port $Port -TimeoutSec 2
            if ($health.status) {
                break
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    if (-not $health) {
        throw "Backend did not become healthy on 127.0.0.1:$Port."
    }

    if ($health.version -ne $expectedVersion) {
        throw "Backend reported version $($health.version) but expected $expectedVersion."
    }

    $meta = [pscustomobject]@{
        pid = $managedProcess.Id
        port = $Port
        host = "127.0.0.1"
        command = "$python -m gaia serve --host 127.0.0.1 --port $Port"
        repositoryRoot = $repoRoot
        pythonPath = $python
        version = $health.version
        startedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
    }
    $meta | ConvertTo-Json -Compress | Set-Content -Path $paths.MetaFile -Encoding UTF8
    $managedProcess.Id.ToString() | Set-Content -Path $paths.PidFile -Encoding ASCII

    Write-Host "GAIA managed backend ready"
} catch {
    if ($managedProcess -and -not $managedProcess.HasExited) {
        try { Stop-Process -Id $managedProcess.Id -Force } catch {}
    }
    Remove-GaiaManagedBackendArtifacts -Paths $paths
    throw
}
