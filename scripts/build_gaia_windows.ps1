[CmdletBinding()]
param(
    [ValidateSet("debug", "release")]
    [string]$Configuration = "release"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Push-Location apps\gaia_windows
try {
    flutter build windows --$Configuration
} finally {
    Pop-Location
}
