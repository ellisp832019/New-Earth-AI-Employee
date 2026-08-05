[CmdletBinding()]
param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$runtimeDir = Join-Path $PWD "data\runtime"
$pidFile = Join-Path $runtimeDir "gaia-backend.pid"
if (-not (Test-Path $pidFile)) {
    throw "Managed backend pid file not found."
}

$pid = [int](Get-Content $pidFile -Raw)
$process = Get-Process -Id $pid -ErrorAction SilentlyContinue
if (-not $process) {
    throw "Managed backend process $pid is not running."
}

$cim = Get-CimInstance Win32_Process -Filter "ProcessId = $pid"
if (-not $cim.CommandLine -or $cim.CommandLine -notmatch '--host 127\.0\.0\.1' -or $cim.CommandLine -notmatch "--port $Port") {
    throw "Process $pid is not the managed GAIA backend."
}

Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 5 | ConvertTo-Json -Compress
