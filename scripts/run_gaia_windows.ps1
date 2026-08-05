[CmdletBinding()]
param(
    [string[]]$FlutterArgs = @()
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment missing. Run scripts\setup_windows.ps1 first."
}

$backendPort = 8000
$backendUrl = "http://127.0.0.1:$backendPort"
$logRoot = Join-Path $PWD "data\logs"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

$stdoutLog = Join-Path $logRoot "gaia_windows-backend.out.log"
$stderrLog = Join-Path $logRoot "gaia_windows-backend.err.log"

$backendProcess = Start-Process `
    -FilePath $python `
    -ArgumentList @("-m", "gaia", "serve", "--host", "127.0.0.1", "--port", "$backendPort") `
    -WorkingDirectory $PWD `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog

function Wait-ForBackend {
    param([string]$Uri, [int]$Attempts = 60)
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            Invoke-RestMethod -Uri "$Uri/health" -TimeoutSec 2 | Out-Null
            return
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    throw "GAIA backend did not become healthy at $Uri."
}

try {
    Wait-ForBackend -Uri $backendUrl
    Push-Location apps\gaia_windows
    try {
        flutter run -d windows @FlutterArgs
    } finally {
        Pop-Location
    }
} finally {
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force
    }
}
