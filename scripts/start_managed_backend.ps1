[CmdletBinding()]
param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment missing. Run scripts\setup_windows.ps1 first."
}

$runtimeDir = Join-Path $PWD "data\runtime"
$logDir = Join-Path $PWD "data\logs"
New-Item -ItemType Directory -Force -Path $runtimeDir, $logDir | Out-Null

$pidFile = Join-Path $runtimeDir "gaia-backend.pid"
$metaFile = Join-Path $runtimeDir "gaia-backend.json"
$stdoutLog = Join-Path $logDir "gaia-backend.out.log"
$stderrLog = Join-Path $logDir "gaia-backend.err.log"

Write-Host "GAIA managed backend starting"

$process = Start-Process `
    -FilePath $python `
    -ArgumentList @("-m", "gaia", "serve", "--host", "127.0.0.1", "--port", "$Port") `
    -WorkingDirectory $PWD `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog

$meta = [pscustomobject]@{
    pid = $process.Id
    port = $Port
    host = "127.0.0.1"
    command = "$python -m gaia serve --host 127.0.0.1 --port $Port"
    startedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
}
$meta | ConvertTo-Json -Compress | Set-Content -Path $metaFile -Encoding UTF8
$process.Id | Set-Content -Path $pidFile -Encoding ASCII

try {
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2 | Out-Null
            Write-Host "GAIA managed backend ready"
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not (Test-Path $pidFile)) {
        throw "Managed backend pid file missing."
    }
    Wait-Process -Id $process.Id
} finally {
    if (-not $process.HasExited) {
        try { Stop-Process -Id $process.Id -Force } catch {}
    }
}
