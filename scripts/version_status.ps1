[CmdletBinding()]
param(
    [string]$PythonPath = $null
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

. "$PSScriptRoot\python_runtime_common.ps1"
. "$PSScriptRoot\managed_backend_common.ps1"

$repoRoot = $PWD.Path
$pythonRuntime = Resolve-GaiaPythonRuntime -RepoRoot $repoRoot -PythonPath $PythonPath
$python = $pythonRuntime.Path
$paths = Get-GaiaManagedBackendPaths -RepoRoot $repoRoot -PythonPath $python

$packageVersion = (Invoke-GaiaPython -PythonPath $python -Arguments @('-c', 'import gaia; print(gaia.__version__)') | Out-String).Trim()
$flutterMachine = (& flutter --version --machine | Out-String).Trim()
$flutterInfo = $flutterMachine | ConvertFrom-Json
$branch = (& git branch --show-current).Trim()
$sha = (& git rev-parse HEAD).Trim()
$expectedVersion = $packageVersion
$snapshot = Get-GaiaManagedBackendSnapshot -RepoRoot $repoRoot -Port 8000 -ExpectedBackendVersion $expectedVersion -PythonPath $python

$flutterVersion = $flutterInfo.flutterVersion
if (-not $flutterVersion) { $flutterVersion = $flutterInfo.frameworkVersion }
$flutterChannel = $flutterInfo.flutterChannel
if (-not $flutterChannel) { $flutterChannel = $flutterInfo.channel }
$dartVersion = $flutterInfo.dartVersion
if (-not $dartVersion) { $dartVersion = $flutterInfo.dartSdkVersion }
$frameworkRevision = $flutterInfo.frameworkRevision

[pscustomobject]@{
    pythonPackageVersion = $packageVersion
    flutterVersion = $flutterVersion
    flutterChannel = $flutterChannel
    dartVersion = $dartVersion
    frameworkRevision = $frameworkRevision
    gitBranch = $branch
    gitSha = $sha
    backendOwnershipState = $snapshot.State
    backendCompatibility = $snapshot.BackendCompatibility
    backendVersion = $snapshot.BackendVersion
    backendManagedPid = $snapshot.ManagedPid
} | ConvertTo-Json -Compress
