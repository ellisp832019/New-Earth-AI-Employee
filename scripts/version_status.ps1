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
$previousErrorActionPreference = $ErrorActionPreference
$flutterMachine = $null
try {
    $ErrorActionPreference = "Continue"
    $flutterMachine = & flutter --version --machine 2>&1 | Out-String
} finally {
    $ErrorActionPreference = $previousErrorActionPreference
}
if ($null -eq $flutterMachine) {
    throw "flutter --version --machine returned no output."
}
$flutterMachine = [string]$flutterMachine
if ([string]::IsNullOrWhiteSpace($flutterMachine)) {
    throw "flutter --version --machine returned no output."
}

$flutterJsonStart = $flutterMachine.IndexOf("{")
if ($flutterJsonStart -lt 0) {
    throw "flutter --version --machine did not return JSON output."
}
$flutterJson = $flutterMachine.Substring($flutterJsonStart).Trim()
$flutterInfo = $flutterJson | ConvertFrom-Json
if ($null -eq $flutterInfo) {
    throw "flutter --version --machine output did not contain parseable JSON."
}
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

    if ($null -eq $Object) {
        return $null
    }

    $property = $Object.PSObject.Properties[$Name]
    if ($property) {
        return $property.Value
    }

    return $null
}

$flutterVersion = Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "flutterVersion"
$flutterVersion = if (-not $flutterVersion) { Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "frameworkVersion" } else { $flutterVersion }
$flutterChannel = Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "flutterChannel"
$flutterChannel = if (-not $flutterChannel) { Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "channel" } else { $flutterChannel }
$dartVersion = Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "dartVersion"
$dartVersion = if (-not $dartVersion) { Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "dartSdkVersion" } else { $dartVersion }
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
