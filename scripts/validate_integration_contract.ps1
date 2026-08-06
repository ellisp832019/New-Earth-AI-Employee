$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. "$PSScriptRoot\python_runtime_common.ps1"
$pythonRuntime = Resolve-GaiaPythonRuntime -RepoRoot $root
Invoke-GaiaPython -PythonPath $pythonRuntime.Path -Arguments @('-m', 'compileall', 'src\gaia') | Out-Null
Set-Location $root\packages\gaia_integration_client
dart test
