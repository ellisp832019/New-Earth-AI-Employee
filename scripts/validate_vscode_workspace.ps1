[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$tasksPath = Join-Path $PWD ".vscode\tasks.json"
$launchPath = Join-Path $PWD ".vscode\launch.json"
$settingsPath = Join-Path $PWD ".vscode\settings.json"
$extensionsPath = Join-Path $PWD ".vscode\extensions.json"

foreach ($path in @($tasksPath, $launchPath, $settingsPath, $extensionsPath)) {
    if (-not (Test-Path $path)) {
        throw "Missing VS Code file: $path"
    }
}

$tasks = Get-Content $tasksPath -Raw | ConvertFrom-Json
$launch = Get-Content $launchPath -Raw | ConvertFrom-Json
$extensions = Get-Content $extensionsPath -Raw | ConvertFrom-Json
$python = Join-Path $PWD ".venv\Scripts\python.exe"

if ($tasks.version -ne "2.0.0") { throw "tasks.json must be version 2.0.0" }
if ($launch.version -ne "0.2.0") { throw "launch.json must be version 0.2.0" }
if (-not $extensions.recommendations) { throw "extensions.json must contain recommendations" }
if (-not (Test-Path $python)) { throw "Python interpreter not found: $python" }

$taskLabels = @{}
foreach ($task in $tasks.tasks) {
    if ($taskLabels.ContainsKey($task.label)) {
        throw "Duplicate task label found: $($task.label)"
    }
    $taskLabels[$task.label] = $true
}

foreach ($task in $tasks.tasks) {
    if ($task.dependsOn) {
        foreach ($dependency in @($task.dependsOn)) {
            if (-not $taskLabels.ContainsKey($dependency)) {
                throw "Task '$($task.label)' depends on missing task '$dependency'"
            }
        }
    }

    if ($task.type -eq 'process' -and $task.command -eq 'powershell.exe') {
        $fileArgIndex = [Array]::IndexOf($task.args, '-File')
        if ($fileArgIndex -ge 0 -and $fileArgIndex + 1 -lt $task.args.Count) {
            $scriptPath = $task.args[$fileArgIndex + 1].Replace('${workspaceFolder}', $PWD.Path)
            if (-not (Test-Path $scriptPath)) {
                throw "Task '$($task.label)' references missing script $scriptPath"
            }
        }
    }

    if ($task.label -like 'GAIA Windows:*' -and $task.options.cwd) {
        $cwdPath = $task.options.cwd.Replace('${workspaceFolder}', $PWD.Path)
        $normalizedCwd = $cwdPath -replace '/', '\'
        if ($normalizedCwd -notlike '*apps\gaia_windows*') {
            throw "Flutter task '$($task.label)' must run from apps\\gaia_windows"
        }
    }
}

foreach ($config in $launch.configurations) {
    if ($config.program) {
        $programPath = $config.program.Replace('${workspaceFolder}', $PWD.Path)
        $configCwd = $config.cwd
        if ($configCwd) {
            $normalizedConfigCwd = $configCwd -replace '/', '\'
        }
        if ($normalizedConfigCwd -like '*apps\gaia_windows*') {
            $cwdPath = $configCwd.Replace('${workspaceFolder}', $PWD.Path)
            if (-not (Test-Path $cwdPath)) {
                throw "Launch cwd does not exist: $cwdPath"
            }
        }
        if ($config.request -eq 'launch' -and $config.type -eq 'python' -and $config.module -and $config.module -eq 'uvicorn') {
            continue
        }
        if ($config.type -eq 'dart' -and $normalizedConfigCwd -notlike '*apps\gaia_windows*') {
            throw "Flutter launch config '$($config.name)' must target apps\\gaia_windows"
        }
    }
}

function Get-TaskByLabel {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    foreach ($task in $tasks.tasks) {
        if ($task.label -eq $Label) {
            return $task
        }
    }

    return $null
}

function Assert-TaskScriptPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TaskLabel,
        [Parameter(Mandatory = $true)]
        [string]$ExpectedScriptName
    )

    $task = Get-TaskByLabel -Label $TaskLabel
    if (-not $task) {
        throw "Missing required VS Code task: $TaskLabel"
    }

    $fileArgIndex = [Array]::IndexOf($task.args, '-File')
    if ($fileArgIndex -lt 0 -or $fileArgIndex + 1 -ge $task.args.Count) {
        throw "Task '$TaskLabel' does not call a PowerShell script."
    }

    $scriptPath = $task.args[$fileArgIndex + 1].Replace('${workspaceFolder}', $PWD.Path)
    if (-not (Test-Path $scriptPath)) {
        throw "Task '$TaskLabel' references missing script $scriptPath"
    }

    if ((Split-Path $scriptPath -Leaf) -ne $ExpectedScriptName) {
        throw "Task '$TaskLabel' must call $ExpectedScriptName."
    }
}

Assert-TaskScriptPath -TaskLabel "GAIA: Start Backend" -ExpectedScriptName "start_managed_backend.ps1"
Assert-TaskScriptPath -TaskLabel "GAIA: Backend Health" -ExpectedScriptName "check_managed_backend.ps1"
Assert-TaskScriptPath -TaskLabel "GAIA: Stop Managed Backend" -ExpectedScriptName "stop_managed_backend.ps1"
Assert-TaskScriptPath -TaskLabel "GAIA: Version Status" -ExpectedScriptName "version_status.ps1"
Assert-TaskScriptPath -TaskLabel "GAIA: Validate Managed Backend Lifecycle" -ExpectedScriptName "validate_managed_backend_scripts.ps1"
Assert-TaskScriptPath -TaskLabel "GAIA: v0.5.1 Release Readiness" -ExpectedScriptName "release_readiness.ps1"

foreach ($scriptFile in Get-ChildItem -Path $PWD\scripts -Filter *.ps1) {
    $scriptText = Get-Content $scriptFile.FullName -Raw
    if ($scriptText -match '(?i)\$(pid|args|input|error|home|host|matches|profile|pwd|this)\s*=') {
        throw "Unsafe automatic-variable assignment found in $($scriptFile.Name)"
    }
}

foreach ($group in @("projects", "project", "models", "agent", "tasks", "drafts", "approvals", "briefs", "permissions", "actions", "receipts")) {
    & $python -m gaia $group --help | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "CLI group '$group' is unavailable"
    }
}

Write-Host "VS Code workspace validation passed." -ForegroundColor Green
