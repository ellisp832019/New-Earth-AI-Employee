[CmdletBinding()]
param()

function Resolve-GaiaPythonRuntime {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [string]$PythonPath
    )

    function Resolve-GaiaPythonCandidate {
        param(
            [Parameter(Mandatory = $true)]
            [string]$CandidatePath,
            [Parameter(Mandatory = $true)]
            [string]$FailureLabel
        )

        if ([string]::IsNullOrWhiteSpace($CandidatePath)) {
            throw "$FailureLabel Python path is empty."
        }

        try {
            $resolvedPath = (Resolve-Path -LiteralPath $CandidatePath -ErrorAction Stop).Path
        } catch {
            throw "$FailureLabel Python interpreter not found or not accessible: $CandidatePath"
        }

        if (-not (Test-Path -LiteralPath $resolvedPath -PathType Leaf)) {
            throw "$FailureLabel Python interpreter not found or not executable: $CandidatePath"
        }

        return $resolvedPath
    }

    function Read-GaiaPythonVersion {
        param(
            [Parameter(Mandatory = $true)]
            [string]$ExecutablePath
        )

        $versionOutput = & $ExecutablePath --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Python interpreter failed version check: $ExecutablePath"
        }

        $versionText = ([string]$versionOutput).Trim()
        if ([string]::IsNullOrWhiteSpace($versionText)) {
            throw "Python interpreter did not report a version: $ExecutablePath"
        }

        if ($versionText -notmatch '^Python\s+\d+\.\d+\.\d+') {
            throw "Python interpreter reported an unexpected version string: $versionText"
        }

        return $versionText
    }

    $selectedPath = $null
    $selectionSource = $null

    if (-not [string]::IsNullOrWhiteSpace($PythonPath)) {
        $selectedPath = Resolve-GaiaPythonCandidate -CandidatePath $PythonPath -FailureLabel "Explicit"
        $selectionSource = "explicit"
    } elseif (-not [string]::IsNullOrWhiteSpace($env:GAIA_PYTHON)) {
        $selectedPath = Resolve-GaiaPythonCandidate -CandidatePath $env:GAIA_PYTHON -FailureLabel "GAIA_PYTHON"
        $selectionSource = "environment"
    } else {
        $venvPath = Join-Path $RepoRoot ".venv\Scripts\python.exe"
        if (Test-Path -LiteralPath $venvPath -PathType Leaf) {
            $selectedPath = Resolve-GaiaPythonCandidate -CandidatePath $venvPath -FailureLabel "Repository .venv"
            $selectionSource = "venv"
        } else {
            $pythonCommand = Get-Command -Name python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($pythonCommand) {
                if ($pythonCommand.Path) {
                    $commandPath = [string]$pythonCommand.Path
                } elseif ($pythonCommand.Source) {
                    $commandPath = [string]$pythonCommand.Source
                } else {
                    $commandPath = $null
                }
                if (-not $commandPath) {
                    throw "Python command was found on PATH but its executable path could not be determined."
                }
                $selectedPath = Resolve-GaiaPythonCandidate -CandidatePath $commandPath -FailureLabel "PATH"
                $selectionSource = "path"
            }
        }
    }

    if (-not $selectedPath) {
        throw "Python was not found. Set GAIA_PYTHON, pass -PythonPath, create .venv\Scripts\python.exe, or ensure python is on PATH."
    }

    $versionText = Read-GaiaPythonVersion -ExecutablePath $selectedPath
    Write-Host ("Selected Python interpreter: {0}" -f $selectedPath)
    Write-Host ("Python version: {0}" -f $versionText)

    return [pscustomobject]@{
        Path = $selectedPath
        Version = $versionText
        Source = $selectionSource
    }
}

function Invoke-GaiaPython {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonPath,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $result = & $PythonPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        $argumentText = ($Arguments -join ' ')
        throw ("Python command failed with exit code {0}: {1} {2}" -f $LASTEXITCODE, $PythonPath, $argumentText)
    }

    return $result
}
