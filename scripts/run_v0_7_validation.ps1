$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

. "$PSScriptRoot\python_runtime_common.ps1"
$pythonRuntime = Resolve-GaiaPythonRuntime -RepoRoot $root

Invoke-GaiaPython -PythonPath $pythonRuntime.Path -Arguments @('-m', 'pytest', 'tests\test_api.py', 'tests\test_provenance.py', 'tests\test_trust.py', 'tests\test_workflows.py') | Out-Null
Invoke-GaiaPython -PythonPath $pythonRuntime.Path -Arguments @('-m', 'ruff', 'check', 'src', 'tests') | Out-Null
