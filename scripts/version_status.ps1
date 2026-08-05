[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment missing. Run scripts\setup_windows.ps1 first."
}

$packageVersion = & $python -c "import gaia; print(gaia.__version__)"
$flutterVersion = & flutter --version
$branch = & git branch --show-current
$sha = & git rev-parse HEAD
$compatibility = "unreachable"
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2
    $compatibility = $health.version
} catch {
}

[pscustomobject]@{
    pythonPackageVersion = $packageVersion.Trim()
    flutterVersion = ($flutterVersion | Select-Object -First 1).Trim()
    gitBranch = $branch.Trim()
    gitSha = $sha.Trim()
    backendCompatibility = $compatibility
} | Format-List
