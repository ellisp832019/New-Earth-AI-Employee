$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. "$PSScriptRoot\python_runtime_common.ps1"
$pythonRuntime = Resolve-GaiaPythonRuntime -RepoRoot $root
Invoke-GaiaPython -PythonPath $pythonRuntime.Path -Arguments @('-m', 'pytest', 'tests\test_provenance.py', '-q', '-k', 'trust_alerts') | Out-Null
