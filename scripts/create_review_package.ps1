param(
  [Parameter(Mandatory = $true)]
  [string]$ActionId,
  [string]$PythonPath = $null
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. "$PSScriptRoot\python_runtime_common.ps1"
$pythonRuntime = Resolve-GaiaPythonRuntime -RepoRoot $root -PythonPath $PythonPath
Invoke-GaiaPython -PythonPath $pythonRuntime.Path -Arguments @('-m', 'gaia', 'review-packages', 'create', $ActionId) | Out-Null
