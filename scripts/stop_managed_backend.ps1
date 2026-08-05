[CmdletBinding()]
param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$runtimeDir = Join-Path $PWD "data\runtime"
$pidFile = Join-Path $runtimeDir "gaia-backend.pid"
$metaFile = Join-Path $runtimeDir "gaia-backend.json"

if (-not (Test-Path $pidFile)) {
    Write-Host "No managed backend pid file found."
    exit 0
}

$pid = [int](Get-Content $pidFile -Raw)
$process = Get-Process -Id $pid -ErrorAction SilentlyContinue
if (-not $process) {
    Remove-Item $pidFile, $metaFile -ErrorAction SilentlyContinue
    Write-Host "Managed backend already stopped."
    exit 0
}

$cim = Get-CimInstance Win32_Process -Filter "ProcessId = $pid"
if (-not $cim.CommandLine -or $cim.CommandLine -notmatch '--host 127\.0\.0\.1' -or $cim.CommandLine -notmatch "--port $Port") {
    throw "Refusing to stop process $pid because it is not the managed GAIA backend."
}

Stop-Process -Id $pid -Force
Wait-Process -Id $pid -ErrorAction SilentlyContinue
Remove-Item $pidFile, $metaFile -ErrorAction SilentlyContinue
Write-Host "Managed backend stopped."
