$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. "$PSScriptRoot\python_runtime_common.ps1"
$pythonRuntime = Resolve-GaiaPythonRuntime -RepoRoot $root
Invoke-GaiaPython -PythonPath $pythonRuntime.Path -Arguments @('-m', 'gaia', 'receipts', 'chains') | Out-Null
