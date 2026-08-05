param(
  [Parameter(Mandatory = $true)]
  [string]$ActionId
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& .\.venv\Scripts\python.exe -m gaia review-packages create $ActionId
