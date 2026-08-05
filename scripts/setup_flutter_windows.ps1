[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) {
    throw "Flutter was not found on PATH."
}

flutter config --enable-windows-desktop | Out-Host
Push-Location apps\gaia_windows
try {
    flutter pub get
} finally {
    Pop-Location
}

Write-Host "GAIA Windows Flutter setup complete." -ForegroundColor Green
