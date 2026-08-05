[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment missing. Run scripts\setup_windows.ps1 first."
}

$backendPort = 8000
$backendUrl = "http://127.0.0.1:$backendPort"
$logRoot = Join-Path $PWD "data\logs"
$smokeSummaryFile = Join-Path $logRoot "gaia_windows-live-smoke.json"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

$backend = Start-Process -FilePath $python -ArgumentList @("-m", "gaia", "serve", "--host", "127.0.0.1", "--port", "$backendPort") -WorkingDirectory $PWD -WindowStyle Hidden -PassThru
try {
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri "$backendUrl/health" -TimeoutSec 2
            if ($health.status) { break }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $health) {
        throw "Backend did not become healthy at $backendUrl."
    }

    $appStdout = Join-Path $logRoot "gaia_windows-app.out.log"
    $appStderr = Join-Path $logRoot "gaia_windows-app.err.log"
    $app = Start-Process -FilePath "flutter" -ArgumentList @("run", "-d", "windows", "--release") -WorkingDirectory (Join-Path $PWD "apps\gaia_windows") -WindowStyle Hidden -PassThru -RedirectStandardOutput $appStdout -RedirectStandardError $appStderr
    try {
        Start-Sleep -Seconds 25
        $summary = [pscustomobject]@{
            backendHealthy = [bool]$health
            backendVersion = $health.version
            backendStatus = $health.status
            backendPid = $backend.Id
            appPid = $app.Id
            appRunning = -not $app.HasExited
            appExitCode = if ($app.HasExited) { $app.ExitCode } else { $null }
            appStdoutTail = if (Test-Path $appStdout) { (Get-Content $appStdout -Tail 20) -join " | " } else { "" }
            appStderrTail = if (Test-Path $appStderr) { (Get-Content $appStderr -Tail 20) -join " | " } else { "" }
        }
        $summary | ConvertTo-Json -Compress | Set-Content -Path $smokeSummaryFile -Encoding UTF8
        $summary | ConvertTo-Json -Compress
    } finally {
        if ($app -and -not $app.HasExited) {
            Stop-Process -Id $app.Id -Force
        }
        $gaiaAppRoot = Join-Path $PWD "apps\gaia_windows\build\windows\x64\runner"
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -eq 'gaia_windows.exe' -and $_.ExecutablePath -and $_.ExecutablePath.StartsWith($gaiaAppRoot, [System.StringComparison]::OrdinalIgnoreCase)
            } |
            ForEach-Object {
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            }
    }
} finally {
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force
    }
}
