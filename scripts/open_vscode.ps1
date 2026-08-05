$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$code = Get-Command code -ErrorAction SilentlyContinue
if (-not $code) { throw "VS Code command 'code' was not found. Open this folder manually in VS Code." }
& $code.Source .
