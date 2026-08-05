[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$exe = Join-Path $PWD "apps\gaia_windows\build\windows\x64\runner\Release\gaia_windows.exe"
$workingDirectory = Split-Path $exe
if (-not (Test-Path $exe)) {
    throw "Release executable not found. Run scripts\\build_gaia_windows.ps1 -Configuration release first."
}

Start-Process -FilePath $exe -WorkingDirectory $workingDirectory
