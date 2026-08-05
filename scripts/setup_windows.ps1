[CmdletBinding()]
param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

function Resolve-Python {
    param([string]$Explicit)
    if ($Explicit) {
        & $Explicit --version | Out-Host
        return $Explicit
    }
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        foreach ($version in @("3.12", "3.11")) {
            try {
                $resolved = & $launcher.Source "-$version" -c "import sys; print(sys.executable)"
                if ($LASTEXITCODE -eq 0 -and $resolved) {
                    & $resolved --version | Out-Host
                    return $resolved.Trim()
                }
            } catch {
                continue
            }
        }
    }
    $candidate = Get-Command python -ErrorAction SilentlyContinue
    if ($candidate) {
        & $candidate.Source --version | Out-Host
        return $candidate.Source
    }
    throw "Python was not found. Install Python 3.11, 3.12 or a compatible interpreter, or run: .\scripts\setup_windows.ps1 -Python 'C:\Path\python.exe'"
}

$pythonExe = Resolve-Python -Explicit $Python
if (-not (Test-Path ".venv")) {
    & $pythonExe -m venv .venv
}

$venvPython = Join-Path $PWD ".venv\Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $venvPython -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

New-Item -ItemType Directory -Force -Path "data\reports", "data\logs" | Out-Null
Write-Host "GAIA setup complete." -ForegroundColor Green
Write-Host "Activate with: .\.venv\Scripts\Activate.ps1"
Write-Host "Then run: gaia doctor"
