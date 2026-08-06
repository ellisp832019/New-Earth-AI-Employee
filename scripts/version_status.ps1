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
if (-not $flutterVersion) { $flutterVersion = Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "frameworkVersion" }
$flutterChannel = Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "flutterChannel"
if (-not $flutterChannel) { $flutterChannel = Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "channel" }
$dartVersion = Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "dartVersion"
if (-not $dartVersion) { $dartVersion = Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "dartSdkVersion" }
$frameworkRevision = Get-GaiaJsonPropertyValue -Object $flutterInfo -Name "frameworkRevision"

function Get-GaiaGitStatus {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    function Get-GaiaTrimmedNativeOutput {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Command,
            [Parameter(Mandatory = $true)]
            [string[]]$Arguments
        )

        $output = & $Command @Arguments 2>$null | Out-String
        return ([string]$output).Trim()
    }

    $branchName = Get-GaiaTrimmedNativeOutput -Command git -Arguments @("branch", "--show-current")
    if ($branchName) {
        return [pscustomobject]@{
            GitBranch = $branchName
            GitRefState = "branch"
        }
    }

    $headRef = ([string]$env:GITHUB_HEAD_REF).Trim()
    if ($headRef) {
        return [pscustomobject]@{
            GitBranch = $headRef
            GitRefState = "pull_request"
        }
    }

    $refType = ([string]$env:GITHUB_REF_TYPE).Trim()
    $refName = ([string]$env:GITHUB_REF_NAME).Trim()
    if ($refType -ieq "tag" -and $refName) {
        return [pscustomobject]@{
            GitBranch = $refName
            GitRefState = "tag"
        }
    }

    $tagName = Get-GaiaTrimmedNativeOutput -Command git -Arguments @("tag", "--points-at", "HEAD")
    if ($tagName) {
        $tagLines = @($tagName -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        if ($tagLines.Count -gt 0) {
            return [pscustomobject]@{
                GitBranch = $tagLines[0].Trim()
                GitRefState = "tag"
            }
        }
    }

    if ($refName -and $refName -notmatch '^\d+/merge$') {
        return [pscustomobject]@{
            GitBranch = $refName
            GitRefState = "branch"
        }
    }

    return [pscustomobject]@{
        GitBranch = "detached"
        GitRefState = "detached"
    }
}

$gitStatus = Get-GaiaGitStatus -RepoRoot $repoRoot
$branch = $gitStatus.GitBranch
$gitRefState = $gitStatus.GitRefState

[string]$shaOutput = & git rev-parse HEAD 2>$null | Out-String
$sha = $shaOutput.Trim()
if (-not $sha) {
    throw "git rev-parse HEAD did not return a commit SHA."
}

[pscustomobject]@{
    pythonPackageVersion = $packageVersion
    flutterVersion = $flutterVersion
    flutterChannel = $flutterChannel
    dartVersion = $dartVersion
    frameworkRevision = $frameworkRevision
    gitBranch = $branch
    gitRefState = $gitRefState
    gitSha = $sha
    backendOwnershipState = $snapshot.State
    backendCompatibility = $snapshot.BackendCompatibility
    backendVersion = $snapshot.BackendVersion
    backendManagedPid = $snapshot.ManagedPid
} | ConvertTo-Json -Compress
