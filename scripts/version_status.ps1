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
$flutterMachine = [string](& flutter --version --machine | Out-String)
if ([string]::IsNullOrWhiteSpace($flutterMachine)) {
    throw "flutter --version --machine returned no output."
}

$flutterJsonStart = $flutterMachine.IndexOf("{")
if ($flutterJsonStart -lt 0) {
    throw "flutter --version --machine did not return JSON output."
}
$flutterJson = $flutterMachine.Substring($flutterJsonStart).Trim()
$flutterInfo = $flutterJson | ConvertFrom-Json
$branch = (& git branch --show-current).Trim()
$sha = (& git rev-parse HEAD).Trim()
$expectedVersion = $packageVersion
$snapshot = Get-GaiaManagedBackendSnapshot -RepoRoot $repoRoot -Port 8000 -ExpectedBackendVersion $expectedVersion -PythonPath $python

if (-not $snapshot) {
    throw "Managed backend snapshot was unexpectedly empty."
}

function Get-GaiaJsonPropertyValue {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Object,
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $property = $Object.PSObject.Properties[$Name]
    if ($property) {
        return $property.Value
    }

    return $null
}

$flutterVersion = Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "flutterVersion"
if (-not $flutterVersion) { $flutterVersion = $flutterInfo.frameworkVersion }
$flutterChannel = Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "flutterChannel"
if (-not $flutterChannel) { $flutterChannel = $flutterInfo.channel }
$dartVersion = Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "dartVersion"
if (-not $dartVersion) { $dartVersion = $flutterInfo.dartSdkVersion }
$frameworkRevision = Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "frameworkRevision"

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
