[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Push-Location apps\gaia_windows
try {
    flutter analyze
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    flutter test
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}
