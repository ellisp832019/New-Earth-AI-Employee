[CmdletBinding()]
param()

function Get-GaiaManagedBackendPaths {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    [pscustomobject]@{
        RepoRoot = $RepoRoot
        PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
        RuntimeDir = Join-Path $RepoRoot "data\runtime"
        LogDir = Join-Path $RepoRoot "data\logs"
        PidFile = Join-Path (Join-Path $RepoRoot "data\runtime") "gaia-backend.pid"
        MetaFile = Join-Path (Join-Path $RepoRoot "data\runtime") "gaia-backend.json"
    }
}

function Read-GaiaManagedPidRecord {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PidFile
    )

    if (-not (Test-Path $PidFile)) {
        return [pscustomobject]@{
            State = "missing"
            ManagedPid = $null
            RawValue = $null
            Reason = "Managed backend pid file not found."
        }
    }

    $rawValue = (Get-Content -Path $PidFile -Raw).Trim()
    if ([string]::IsNullOrWhiteSpace($rawValue)) {
        return [pscustomobject]@{
            State = "stale"
            ManagedPid = $null
            RawValue = $rawValue
            Reason = "Managed backend pid file is empty."
        }
    }

    $managedPid = 0
    if (-not [int]::TryParse($rawValue, [ref]$managedPid) -or $managedPid -le 0) {
        return [pscustomobject]@{
            State = "stale"
            ManagedPid = $null
            RawValue = $rawValue
            Reason = "Managed backend pid file does not contain a valid PID."
        }
    }

    return [pscustomobject]@{
        State = "present"
        ManagedPid = $managedPid
        RawValue = $rawValue
        Reason = $null
    }
}

function Read-GaiaManagedBackendMeta {
    param(
        [Parameter(Mandatory = $true)]
        [string]$MetaFile
    )

    if (-not (Test-Path $MetaFile)) {
        return $null
    }

    try {
        return Get-Content -Path $MetaFile -Raw | ConvertFrom-Json
    } catch {
        return [pscustomobject]@{
            repositoryRoot = $null
            pythonPath = $null
            version = $null
            parseError = $_.Exception.Message
        }
    }
}

function Get-GaiaManagedBackendProcess {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ManagedPid
    )

    $process = Get-Process -Id $ManagedPid -ErrorAction SilentlyContinue
    if (-not $process) {
        return $null
    }

    $cim = Get-CimInstance Win32_Process -Filter "ProcessId = $ManagedPid" -ErrorAction SilentlyContinue
    if (-not $cim) {
        return $null
    }

    [pscustomobject]@{
        Process = $process
        Cim = $cim
        ExecutablePath = $cim.ExecutablePath
        CommandLine = $cim.CommandLine
    }
}

function Get-GaiaManagedBackendProcessTreeIds {
    param(
        [Parameter(Mandatory = $true)]
        [int]$RootProcessId
    )

    $treeIds = New-Object 'System.Collections.Generic.HashSet[int]'
    $pending = New-Object 'System.Collections.Generic.Queue[int]'
    $pending.Enqueue($RootProcessId)

    while ($pending.Count -gt 0) {
        $currentProcessId = $pending.Dequeue()
        if (-not $treeIds.Add($currentProcessId)) {
            continue
        }

        $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $currentProcessId" -ErrorAction SilentlyContinue
        foreach ($child in @($children)) {
            if ($child -and $child.ProcessId -gt 0) {
                $pending.Enqueue([int]$child.ProcessId)
            }
        }
    }

    return $treeIds
}

function Get-GaiaBackendListener {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

function Invoke-GaiaBackendHealth {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [int]$TimeoutSec = 2
    )

    Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec $TimeoutSec -ErrorAction Stop
}

function Test-GaiaManagedBackendIdentity {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [Parameter(Mandatory = $true)]
        [string]$ExpectedPythonPath,
        [pscustomobject]$ProcessRecord,
        [pscustomobject]$MetaRecord
    )

    $identity = [ordered]@{
        IsRepositoryPython = $false
        HasServeCommand = $false
        HasLoopbackHost = $false
        HasPortMatch = $false
        MetaRepositoryRootMatches = $true
        MetaPythonPathMatches = $true
        IsManagedProcess = $false
        Reason = $null
    }

    if (-not $ProcessRecord) {
        $identity.Reason = "Managed backend process is not running."
        return [pscustomobject]$identity
    }

    try {
        $expectedExecutable = [System.IO.Path]::GetFullPath($ExpectedPythonPath)
        $actualExecutable = if ($ProcessRecord.ExecutablePath) {
            [System.IO.Path]::GetFullPath($ProcessRecord.ExecutablePath)
        } else {
            $null
        }
        $identity.IsRepositoryPython = $actualExecutable -and ($actualExecutable -ieq $expectedExecutable)
    } catch {
        $identity.IsRepositoryPython = $false
    }

    $commandLine = [string]$ProcessRecord.CommandLine
    $identity.HasServeCommand = $commandLine -match '(?i)\-m\s+gaia\s+serve'
    $identity.HasLoopbackHost = $commandLine -match '--host\s+127\.0\.0\.1'
    $identity.HasPortMatch = $commandLine -match ("--port\s+{0}(\s|$)" -f [regex]::Escape([string]$Port))

    if ($MetaRecord) {
        if ($MetaRecord.repositoryRoot) {
            try {
                $metaRepositoryRoot = [System.IO.Path]::GetFullPath([string]$MetaRecord.repositoryRoot)
                $repoRootFull = [System.IO.Path]::GetFullPath($RepoRoot)
                $identity.MetaRepositoryRootMatches = $metaRepositoryRoot -ieq $repoRootFull
            } catch {
                $identity.MetaRepositoryRootMatches = $false
            }
        }

        if ($MetaRecord.pythonPath) {
            try {
                $metaPythonPath = [System.IO.Path]::GetFullPath([string]$MetaRecord.pythonPath)
                $expectedPythonFull = [System.IO.Path]::GetFullPath($ExpectedPythonPath)
                $identity.MetaPythonPathMatches = $metaPythonPath -ieq $expectedPythonFull
            } catch {
                $identity.MetaPythonPathMatches = $false
            }
        }
    }

    $identity.IsManagedProcess = $identity.IsRepositoryPython -and $identity.HasServeCommand -and $identity.HasLoopbackHost -and $identity.HasPortMatch -and $identity.MetaRepositoryRootMatches -and $identity.MetaPythonPathMatches
    if (-not $identity.IsManagedProcess) {
        $identity.Reason = "Process identity does not match the managed GAIA backend."
    }

    return [pscustomobject]$identity
}

function Get-GaiaManagedBackendSnapshot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [int]$Port = 8000,
        [string]$ExpectedBackendVersion = $null
    )

    $paths = Get-GaiaManagedBackendPaths -RepoRoot $RepoRoot
    $pidRecord = Read-GaiaManagedPidRecord -PidFile $paths.PidFile
    $listener = Get-GaiaBackendListener -Port $Port
    $metaRecord = Read-GaiaManagedBackendMeta -MetaFile $paths.MetaFile
    $treeIds = $null

    $baseSnapshot = [ordered]@{
        State = $pidRecord.State
        Reason = $pidRecord.Reason
        ManagedPid = $pidRecord.ManagedPid
        Port = $Port
        RepoRoot = $RepoRoot
        PythonExe = $paths.PythonExe
        PidFile = $paths.PidFile
        MetaFile = $paths.MetaFile
        ListenerOwningProcess = if ($listener) { $listener.OwningProcess } else { $null }
        BackendVersion = $null
        BackendCompatibility = "unavailable"
        Health = $null
        ProcessExecutablePath = $null
        ProcessCommandLine = $null
        IsRepositoryPython = $false
        HasServeCommand = $false
        HasLoopbackHost = $false
        HasPortMatch = $false
        MetaRepositoryRootMatches = $true
        MetaPythonPathMatches = $true
        ProcessTreeIds = @()
    }

    if ($pidRecord.State -eq "missing") {
        if ($listener) {
            $baseSnapshot.State = "external"
            $baseSnapshot.Reason = "Port $Port is already occupied by process $($listener.OwningProcess)."
        }
        return [pscustomobject]$baseSnapshot
    }

    if ($pidRecord.State -eq "stale") {
        if ($listener) {
            $baseSnapshot.State = "external"
            $baseSnapshot.Reason = "Port $Port is already occupied by process $($listener.OwningProcess)."
        }
        return [pscustomobject]$baseSnapshot
    }

    $processRecord = Get-GaiaManagedBackendProcess -ManagedPid $pidRecord.ManagedPid
    if (-not $processRecord) {
        $baseSnapshot.State = "stale"
        $baseSnapshot.Reason = "Managed backend process $($pidRecord.ManagedPid) is not running."
        return [pscustomobject]$baseSnapshot
    }

    $identity = Test-GaiaManagedBackendIdentity -RepoRoot $RepoRoot -Port $Port -ExpectedPythonPath $paths.PythonExe -ProcessRecord $processRecord -MetaRecord $metaRecord
    $treeIds = Get-GaiaManagedBackendProcessTreeIds -RootProcessId $pidRecord.ManagedPid
    $baseSnapshot.ProcessTreeIds = @($treeIds | Sort-Object)
    $baseSnapshot.ProcessExecutablePath = $processRecord.ExecutablePath
    $baseSnapshot.ProcessCommandLine = $processRecord.CommandLine
    $baseSnapshot.IsRepositoryPython = $identity.IsRepositoryPython
    $baseSnapshot.HasServeCommand = $identity.HasServeCommand
    $baseSnapshot.HasLoopbackHost = $identity.HasLoopbackHost
    $baseSnapshot.HasPortMatch = $identity.HasPortMatch
    $baseSnapshot.MetaRepositoryRootMatches = $identity.MetaRepositoryRootMatches
    $baseSnapshot.MetaPythonPathMatches = $identity.MetaPythonPathMatches

    if (-not $identity.IsManagedProcess) {
        if ($listener -and $listener.OwningProcess -ne $pidRecord.ManagedPid) {
            $baseSnapshot.State = "external"
            $baseSnapshot.Reason = "Port $Port is owned by external process $($listener.OwningProcess)."
        } else {
            $baseSnapshot.State = "unmanaged"
            $baseSnapshot.Reason = $identity.Reason
        }
        return [pscustomobject]$baseSnapshot
    }

    if (-not $listener -or -not $treeIds.Contains([int]$listener.OwningProcess)) {
        $baseSnapshot.State = "stale"
        $baseSnapshot.Reason = "Managed backend process $($pidRecord.ManagedPid) is not listening on 127.0.0.1:$Port."
        return [pscustomobject]$baseSnapshot
    }

    try {
        $health = Invoke-GaiaBackendHealth -Port $Port -TimeoutSec 2
    } catch {
        $baseSnapshot.State = "stale"
        $baseSnapshot.Reason = "Health endpoint is unavailable on 127.0.0.1:$Port."
        return [pscustomobject]$baseSnapshot
    }

    $backendVersion = [string]$health.version
    $baseSnapshot.Health = $health
    $baseSnapshot.BackendVersion = $backendVersion
    if ($ExpectedBackendVersion) {
        if ($backendVersion -eq $ExpectedBackendVersion) {
            $baseSnapshot.State = "healthy"
            $baseSnapshot.BackendCompatibility = "compatible"
            $baseSnapshot.Reason = $null
        } else {
            $baseSnapshot.State = "incompatible"
            $baseSnapshot.BackendCompatibility = "incompatible"
            $baseSnapshot.Reason = "Backend version $backendVersion does not match expected version $ExpectedBackendVersion."
        }
    } else {
        $baseSnapshot.State = "healthy"
        $baseSnapshot.BackendCompatibility = "managed"
        $baseSnapshot.Reason = $null
    }

    return [pscustomobject]$baseSnapshot
}

function Remove-GaiaManagedBackendArtifacts {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Paths
    )

    Remove-Item -Path $Paths.PidFile, $Paths.MetaFile -ErrorAction SilentlyContinue
}
