param(
    [ValidateSet('SelfTest', 'Run')][string]$Mode = 'SelfTest',
    [string]$ConfirmRun = ''
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Set-StrictMode -Version 2.0
$isSelfTest = $Mode -eq 'SelfTest'
$expectedProtocolHash = 'B1D52DE0A454F8B29A1DB4A6E0627EFC6A60E96010730C7D9427276D6D4C11C9'
$requiredConfirmation = 'RUN_H9A_LABEL_BLIND@B1D52DE0A454F8B29A1DB4A6E0627EFC6A60E96010730C7D9427276D6D4C11C9:522D246FBA9769F7EE3C11C95E2710F0FD956B933B4D83E7D0371FA1FE42BEB5'
if (-not $isSelfTest -and $ConfirmRun -ne $requiredConfirmation) {
    throw 'Real H9A execution requires the exact locked label-blind confirmation token.'
}

# Codex Desktop can expose PATH twice with different casing. Windows
# PowerShell 5.1 Start-Process rejects that environment block, so normalize it.
$canonicalPath = [Environment]::GetEnvironmentVariable(
    'Path', [EnvironmentVariableTarget]::Process
)
if ([String]::IsNullOrWhiteSpace($canonicalPath)) {
    throw 'Process Path is empty; refusing H9A launch.'
}
[Environment]::SetEnvironmentVariable('PATH', $null, [EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable('Path', $null, [EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable('Path', $canonicalPath, [EnvironmentVariableTarget]::Process)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$h9Root = (Resolve-Path -LiteralPath (Join-Path $here '..')).Path
$root = (Resolve-Path -LiteralPath (Join-Path $here '..\..\..\..\..')).Path
$h6PhaseARoot = Join-Path $root 'experiments\kg_launch_autoresearch\experiments\h6_ranking_consequence'
$resultsRoot = Join-Path $h9Root 'results'
$selfTestRoot = Join-Path $h9Root 'selftest_artifacts'
$artifactRoot = if ($isSelfTest) { $selfTestRoot } else { $resultsRoot }
[System.IO.Directory]::CreateDirectory($artifactRoot) | Out-Null
$runner = (Resolve-Path -LiteralPath (Join-Path $here 'run_h9a_revkron.py')).Path
$launcher = (Resolve-Path -LiteralPath $MyInvocation.MyCommand.Path).Path
$protocol = (Resolve-Path -LiteralPath (Join-Path $h9Root 'protocol.md')).Path
$implementationLock = (Resolve-Path -LiteralPath (Join-Path $h9Root 'implementation_lock.md')).Path
$venvLauncher = (Resolve-Path -LiteralPath (Join-Path $root '_bestrec_run\.venv\Scripts\python.exe')).Path
$venvConfig = (Resolve-Path -LiteralPath (Join-Path $root '_bestrec_run\.venv\pyvenv.cfg')).Path
$homeLines = @(Get-Content -LiteralPath $venvConfig | Where-Object { $_ -match '^\s*home\s*=' })
if ($homeLines.Count -ne 1) {
    throw 'Could not resolve exactly one base-Python home from pyvenv.cfg.'
}
$venvHome = ($homeLines[0] -split '=', 2)[1].Trim()
$baseInterpreter = (Resolve-Path -LiteralPath (Join-Path $venvHome 'python.exe')).Path
$outerLock = if ($isSelfTest) {
    Join-Path $h9Root 'H9A_SELFTEST_LAUNCH.lock'
}
else {
    Join-Path $h9Root 'H9A_RUN_001_LAUNCH.lock'
}
$innerLock = Join-Path $h9Root 'H9A_RUN_001_INNER.lock'
$primaryDirectory = Join-Path $resultsRoot 'h9a_run_001'
$replayDirectory = Join-Path $resultsRoot 'h9a_run_001_replay'
$confirmatoryCompletionMarker = Join-Path $resultsRoot 'h9a_run_001_completion.json'

foreach ($name in @(
    'OMP_NUM_THREADS',
    'MKL_NUM_THREADS',
    'OPENBLAS_NUM_THREADS',
    'NUMEXPR_NUM_THREADS',
    'VECLIB_MAXIMUM_THREADS',
    'BLIS_NUM_THREADS'
)) {
    [Environment]::SetEnvironmentVariable($name, '1', [EnvironmentVariableTarget]::Process)
}
[Environment]::SetEnvironmentVariable('CUDA_VISIBLE_DEVICES', '-1', [EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable('PYTHONUNBUFFERED', '1', [EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable('PYTHONDONTWRITEBYTECODE', '1', [EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable('PYTHONHASHSEED', '0', [EnvironmentVariableTarget]::Process)
# Launch the real image directly while retaining the workspace venv prefix.
[Environment]::SetEnvironmentVariable(
    '__PYVENV_LAUNCHER__', $venvLauncher, [EnvironmentVariableTarget]::Process
)

$expectedInputHashes = [ordered]@{
    news = 'E5D144667558C449D16084FE6BFA01940C2F5D5785EA9F9110292BC3B94EB822'
    facts = '13571090E7983035C9FEEFC65AC295BA9C1D45ECC19814327CE311E830AA9E5D'
    relations = 'D1BD69F5572714402CA5A3456A0C5F77750444C2F8D9144B0690CE094AD4C12A'
    phase_a_manifest = '522D246FBA9769F7EE3C11C95E2710F0FD956B933B4D83E7D0371FA1FE42BEB5'
    phase_a_result = 'B70E29455F5FA8BC43FBC480222308E25A513A9D942C125CB943109C3137AABF'
    phase_a_completion = 'AF751E729B427453CDBC5E00BBA22E40E21CA858BD91A0C497843C07FFAEFC06'
}
$inputPaths = [ordered]@{
    news = Join-Path $root 'experiments\kg_launch_autoresearch\data\MINDsmall_dev\MINDsmall_dev\news.tsv'
    facts = Join-Path $root 'experiments\kg_launch_autoresearch\experiments\h5_bitemporal_drift\results\run_003\facts.jsonl'
    relations = Join-Path $root 'experiments\kg_launch_autoresearch\data\MINDsmall_dev\MINDsmall_dev\relation_embedding.vec'
    phase_a_manifest = Join-Path $h6PhaseARoot 'results\coverage_run_002\cohort_manifest.jsonl'
    phase_a_result = Join-Path $h6PhaseARoot 'results\coverage_run_002\result.json'
    phase_a_completion = Join-Path $h6PhaseARoot 'results\coverage_run_002_completion.json'
}
$phaseACommit = 'b1f247abf3185a2eaec8588b358c488af8f78342'

function Get-UnixTimeNs {
    $epochTicks = [Int64]621355968000000000
    return [Int64](([DateTime]::UtcNow.Ticks - $epochTicks) * 100)
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Get-StringSha256 {
    param([Parameter(Mandatory = $true)][string]$Value)
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
        return ([BitConverter]::ToString($algorithm.ComputeHash($bytes))).Replace('-', '').ToUpperInvariant()
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-CommittedTextSha256 {
    param(
        [Parameter(Mandatory = $true)][string]$Commit,
        [Parameter(Mandatory = $true)][string]$RepositoryPath
    )
    $treeText = & git -C $root show ($Commit + ':' + $RepositoryPath)
    if ($LASTEXITCODE -ne 0) { throw "Could not read committed input: $RepositoryPath" }
    $treeBytes = [System.Text.Encoding]::UTF8.GetBytes(($treeText -join "`n") + "`n")
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($algorithm.ComputeHash($treeBytes))).Replace('-', '').ToUpperInvariant()
    }
    finally { $algorithm.Dispose() }
}

function Get-FileRecord {
    param([Parameter(Mandatory = $true)][string]$Path)
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    return [ordered]@{
        path = $resolved
        sha256 = Get-Sha256 -Path $resolved
        bytes = [Int64](Get-Item -LiteralPath $resolved).Length
    }
}

function Get-DirectoryFileRecords {
    param([Parameter(Mandatory = $true)][string]$Directory)
    $records = [ordered]@{}
    foreach ($file in @(Get-ChildItem -LiteralPath $Directory -File | Sort-Object Name)) {
        $records[$file.Name] = Get-FileRecord -Path $file.FullName
    }
    return $records
}

function Write-ExclusiveJson {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)]$Value
    )
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $directory = [System.IO.Path]::GetDirectoryName($fullPath)
    if (-not [System.IO.Directory]::Exists($directory)) {
        throw "Publication directory is missing: $directory"
    }
    $temporary = Join-Path $directory ('.p' + [Guid]::NewGuid().ToString('N').Substring(0, 20))
    $stream = $null
    $created = $false
    try {
        $stream = [System.IO.File]::Open(
            $temporary,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None
        )
        $created = $true
        $json = ($Value | ConvertTo-Json -Depth 40 -Compress) + "`n"
        $bytes = (New-Object System.Text.UTF8Encoding($false)).GetBytes($json)
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
        $stream.Dispose()
        $stream = $null
        [System.IO.File]::Move($temporary, $fullPath)
    }
    finally {
        if ($null -ne $stream) { $stream.Dispose() }
        if ($created -and [System.IO.File]::Exists($temporary)) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }
}

function New-ExclusiveEmptyFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    $stream = [System.IO.File]::Open(
        $Path,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try { $stream.Flush($true) } finally { $stream.Dispose() }
}

function Move-ExclusiveFileWithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )
    if ([System.IO.File]::Exists($Destination)) {
        throw "Refusing move overwrite: $Destination"
    }
    if (-not [System.IO.Directory]::Exists([System.IO.Path]::GetDirectoryName($Destination))) {
        throw "Move destination directory is missing: $Destination"
    }
    $lastMoveError = $null
    for ($attempt = 0; $attempt -lt 5; $attempt++) {
        if (-not [System.IO.File]::Exists($Source)) {
            throw "Move source is missing: $Source"
        }
        try {
            [System.IO.File]::Move($Source, $Destination)
            return
        }
        catch [System.IO.IOException] {
            $lastMoveError = $_
            if ($attempt -lt 4) { Start-Sleep -Milliseconds 100 }
        }
        catch [System.UnauthorizedAccessException] {
            $lastMoveError = $_
            if ($attempt -lt 4) { Start-Sleep -Milliseconds 100 }
        }
    }
    throw $lastMoveError
}

function Test-ProcessAlive {
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        return -not $process.HasExited
    }
    catch { return $false }
}

function Stop-H9AChildExact {
    param(
        [Parameter(Mandatory = $true)][System.Diagnostics.Process]$Process,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $lastStopError = $null
    for ($attempt = 0; $attempt -lt 3; $attempt++) {
        try {
            if (-not $Process.HasExited) { $Process.Kill() }
            if (-not $Process.WaitForExit(10000)) {
                throw "Timed out waiting for terminated child $Label PID $($Process.Id)."
            }
            if (-not $Process.HasExited) {
                throw "Child $Label PID $($Process.Id) remained live after kill/wait."
            }
            return
        }
        catch {
            $lastStopError = $_
            if ($attempt -lt 2) { Start-Sleep -Milliseconds 100 }
        }
    }
    throw $lastStopError
}

function New-H9AAggregateException {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [AllowNull()]$Primary,
        [Parameter(Mandatory = $true)][object[]]$CleanupErrors
    )
    $exceptions = New-Object 'System.Collections.Generic.List[System.Exception]'
    if ($null -ne $Primary) {
        $primaryException = if ($Primary -is [System.Management.Automation.ErrorRecord]) {
            $Primary.Exception
        }
        elseif ($Primary -is [System.Exception]) {
            $Primary
        }
        else {
            [System.Exception]::new([string]$Primary)
        }
        $exceptions.Add($primaryException)
    }
    foreach ($cleanupError in $CleanupErrors) {
        $cleanupException = if ($cleanupError -is [System.Management.Automation.ErrorRecord]) {
            $cleanupError.Exception
        }
        elseif ($cleanupError -is [System.Exception]) {
            $cleanupError
        }
        else {
            [System.Exception]::new([string]$cleanupError)
        }
        $exceptions.Add($cleanupException)
    }
    if ($exceptions.Count -eq 0) {
        throw 'Cannot construct an empty H9A aggregate exception.'
    }
    return [System.AggregateException]::new($Message, $exceptions)
}

function Open-OuterLock {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$RetirementDirectory,
        [Parameter(Mandatory = $true)][string]$ExpectedMode
    )
    $retiredPath = $null
    for ($attempt = 0; $attempt -lt 2; $attempt++) {
        try {
            $stream = [System.IO.File]::Open(
                $Path,
                [System.IO.FileMode]::CreateNew,
                [System.IO.FileAccess]::ReadWrite,
                [System.IO.FileShare]::None
            )
            return [pscustomobject]@{ Stream = $stream; Retired = $retiredPath }
        }
        catch {
            if ($attempt -ne 0) {
                throw 'Outer-lock acquisition raced after one stale-lock retirement.'
            }
            try {
                $existing = [System.IO.File]::ReadAllText($Path) | ConvertFrom-Json
                $expectedOwnerFields = @(
                    'created_unix_ns', 'launch_id', 'launcher_path', 'mode', 'pid', 'runtime'
                ) | Sort-Object
                $actualOwnerFields = @($existing.PSObject.Properties.Name | Sort-Object)
                if ($existing -isnot [pscustomobject] -or
                    ($actualOwnerFields -join '|') -cne ($expectedOwnerFields -join '|') -or
                    $existing.mode -isnot [System.String] -or
                    [string]$existing.mode -cne $ExpectedMode -or
                    (-not (
                        $existing.pid -is [System.Int32] -or
                        $existing.pid -is [System.Int64]
                    )) -or
                    [Int64]$existing.pid -le 0 -or
                    [Int64]$existing.pid -gt [Int32]::MaxValue -or
                    $existing.launch_id -isnot [System.String] -or
                    [string]$existing.launch_id -cnotmatch '\A[0-9]{8}T[0-9]{13}Z_[0-9a-f]{32}\z' -or
                    $existing.launcher_path -isnot [System.String] -or
                    [string]$existing.launcher_path -cne $launcher -or
                    $existing.created_unix_ns -isnot [System.Int64] -or
                    [Int64]$existing.created_unix_ns -le 0 -or
                    $existing.runtime -isnot [pscustomobject]) {
                    throw 'invalid outer-lock owner schema'
                }
                $expectedRuntimeFields = @(
                    'runner_sha256', 'launcher_sha256', 'protocol_sha256', 'lock_sha256',
                    'base_interpreter_sha256', 'venv_launcher_sha256', 'venv_config_sha256'
                ) | Sort-Object
                $actualRuntimeFields = @($existing.runtime.PSObject.Properties.Name | Sort-Object)
                if (($actualRuntimeFields -join '|') -cne ($expectedRuntimeFields -join '|')) {
                    throw 'invalid outer-lock runtime schema'
                }
                foreach ($hashField in $expectedRuntimeFields) {
                    $hashValue = $existing.runtime.$hashField
                    if ($hashValue -isnot [System.String] -or
                        [string]$hashValue -cnotmatch '\A[A-F0-9]{64}\z') {
                        throw "invalid outer-lock runtime hash: $hashField"
                    }
                }
                if ([string]$existing.runtime.protocol_sha256 -cne $expectedProtocolHash) {
                    throw 'outer-lock runtime protocol hash is foreign'
                }
                $ownerPid = [int]$existing.pid
            }
            catch {
                throw "Outer lock is live, unreadable, or malformed; refusing retirement: $Path"
            }
            if (Test-ProcessAlive -ProcessId $ownerPid) {
                throw "Active H9A outer lock is owned by PID $ownerPid."
            }
            $retiredPath = Join-Path $RetirementDirectory (
                'stale_outer_{0}.json' -f [Guid]::NewGuid().ToString('N').Substring(0, 20)
            )
            Move-ExclusiveFileWithRetry -Source $Path -Destination $retiredPath
        }
    }
    throw 'Unreachable outer-lock state.'
}

function Write-HeldLockOwner {
    param(
        [Parameter(Mandatory = $true)][System.IO.FileStream]$Stream,
        [Parameter(Mandatory = $true)]$Owner
    )
    $json = ($Owner | ConvertTo-Json -Depth 20 -Compress) + "`n"
    $bytes = (New-Object System.Text.UTF8Encoding($false)).GetBytes($json)
    $Stream.Write($bytes, 0, $bytes.Length)
    $Stream.Flush($true)
    $Stream.Position = 0
}

function Read-LastJsonSummary {
    param([Parameter(Mandatory = $true)][string]$Path)
    $last = Get-Content -LiteralPath $Path |
        Where-Object { -not [String]::IsNullOrWhiteSpace($_) } |
        Select-Object -Last 1
    if ([String]::IsNullOrWhiteSpace($last)) {
        throw "Child emitted no JSON summary: $Path"
    }
    return $last | ConvertFrom-Json
}

function Assert-FixedHashes {
    param([Parameter(Mandatory = $true)]$Runtime)
    if ((Get-Sha256 -Path $runner) -ne $Runtime.runner_sha256) { throw 'Runner changed during launch.' }
    if ((Get-Sha256 -Path $launcher) -ne $Runtime.launcher_sha256) { throw 'Launcher changed during launch.' }
    if ((Get-Sha256 -Path $protocol) -ne $Runtime.protocol_sha256) { throw 'Protocol changed during launch.' }
    if ($Runtime.protocol_sha256 -ne $expectedProtocolHash) { throw 'Protocol differs from the locked H9A protocol.' }
    if ((Get-Sha256 -Path $implementationLock) -ne $Runtime.lock_sha256) { throw 'H9A implementation lock changed during launch.' }
    if ((Get-Sha256 -Path $baseInterpreter) -ne $Runtime.base_interpreter_sha256) { throw 'Base interpreter changed during launch.' }
    if ((Get-Sha256 -Path $venvLauncher) -ne $Runtime.venv_launcher_sha256) { throw 'Venv launcher changed during launch.' }
    if ((Get-Sha256 -Path $venvConfig) -ne $Runtime.venv_config_sha256) { throw 'Venv config changed during launch.' }
    $lockText = [System.IO.File]::ReadAllText($implementationLock)
    $runnerMatches = [regex]::Matches(
        $lockText,
        '(?m)^Runner-SHA256: `([A-F0-9]{64})`\r?$'
    )
    $launcherMatches = [regex]::Matches(
        $lockText,
        '(?m)^Launcher-SHA256: `([A-F0-9]{64})`\r?$'
    )
    $protocolMatches = [regex]::Matches(
        $lockText,
        '(?m)^Protocol-SHA256: `([A-F0-9]{64})`\r?$'
    )
    if ($runnerMatches.Count -ne 1 -or $launcherMatches.Count -ne 1 -or $protocolMatches.Count -ne 1) {
        throw 'Implementation lock does not contain exactly one finalized runner/launcher/protocol hash.'
    }
    if ((Get-Sha256 -Path $runner) -ne $runnerMatches[0].Groups[1].Value) {
        throw 'Runner differs from the prospective H9A implementation lock.'
    }
    if ((Get-Sha256 -Path $launcher) -ne $launcherMatches[0].Groups[1].Value) {
        throw 'Launcher differs from the prospective H9A implementation lock.'
    }
    if ((Get-Sha256 -Path $protocol) -ne $protocolMatches[0].Groups[1].Value) {
        throw 'Protocol differs from the prospective H9A implementation lock.'
    }
}

function Assert-ImmutableInputs {
    $lockedNames = @('news', 'facts', 'relations', 'phase_a_manifest', 'phase_a_result', 'phase_a_completion')
    if ((@($expectedInputHashes.Keys) -join '|') -ne ($lockedNames -join '|') -or
        (@($inputPaths.Keys) -join '|') -ne ($lockedNames -join '|')) {
        throw 'H9A immutable input surface differs from the locked label-free list.'
    }
    foreach ($name in $expectedInputHashes.Keys) {
        if (-not (Test-Path -LiteralPath $inputPaths[$name] -PathType Leaf)) {
            throw "Immutable input is missing: $name"
        }
        if ((Get-Sha256 -Path $inputPaths[$name]) -ne $expectedInputHashes[$name]) {
            throw "Immutable input hash mismatch: $name"
        }
    }
    if ((Get-Item -LiteralPath $inputPaths.phase_a_manifest).Length -ne 224785295) {
        throw 'Phase-A manifest byte count mismatch.'
    }
    $resolvedCommit = (& git -C $root rev-parse ($phaseACommit + '^{commit}')).Trim()
    if ($LASTEXITCODE -ne 0 -or $resolvedCommit -ne $phaseACommit) {
        throw 'Committed Phase-A result commit is unavailable or mismatched.'
    }
    $resultTreeHash = Get-CommittedTextSha256 `
        -Commit $phaseACommit `
        -RepositoryPath 'experiments/kg_launch_autoresearch/experiments/h6_ranking_consequence/results/coverage_run_002/result.json'
    if ($resultTreeHash -ne $expectedInputHashes.phase_a_result) {
        throw 'Phase-A committed tree result hash mismatch.'
    }
    $completionTreeHash = Get-CommittedTextSha256 `
        -Commit $phaseACommit `
        -RepositoryPath 'experiments/kg_launch_autoresearch/experiments/h6_ranking_consequence/results/coverage_run_002_completion.json'
    if ($completionTreeHash -ne $expectedInputHashes.phase_a_completion) {
        throw 'Phase-A committed tree completion-marker hash mismatch.'
    }
    & git -C $root merge-base --is-ancestor $phaseACommit HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Current HEAD does not descend from the committed Phase-A result.' }
}

function Assert-ImplementationCommitted {
    $paths = @(
        'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/code/run_h9a_revkron.py',
        'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/code/run_h9a_revkron_safe.ps1',
        'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/protocol.md',
        'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/implementation_lock.md'
    )
    foreach ($path in $paths) {
        & git -C $root ls-files --error-unmatch -- $path 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "H9A implementation is not committed: $path" }
    }
    & git -C $root diff --quiet -- $paths
    if ($LASTEXITCODE -ne 0) { throw 'H9A implementation differs from the committed worktree.' }
    & git -C $root diff --cached --quiet -- $paths
    if ($LASTEXITCODE -ne 0) { throw 'H9A implementation has staged but uncommitted changes.' }
}

function Assert-StartRecord {
    param(
        [Parameter(Mandatory = $true)]$Start,
        [Parameter(Mandatory = $true)][string]$Action,
        [Parameter(Mandatory = $true)][string]$LaunchId,
        [Parameter(Mandatory = $true)][int]$LauncherPid,
        [Parameter(Mandatory = $true)][int]$ProcessPid,
        [Parameter(Mandatory = $true)][string]$AuthorizationPath,
        [Parameter(Mandatory = $true)][string]$Token,
        [Parameter(Mandatory = $true)]$Runtime
    )
    if (
        $Start.mode -ne 'h9a-child-process-start' -or
        [string]$Start.action -ne $Action -or
        [string]$Start.launch_id -ne $LaunchId -or
        [int]$Start.launcher_pid -ne $LauncherPid -or
        [int]$Start.process_pid -ne $ProcessPid -or
        [string]$Start.authorization_sha256 -ne (Get-Sha256 -Path $AuthorizationPath) -or
        [string]$Start.token_sha256 -ne (Get-StringSha256 -Value $Token) -or
        [string]$Start.runner_sha256 -ne $Runtime.runner_sha256 -or
        [string]$Start.environment.sys_executable -ne $venvLauncher -or
        [string]$Start.environment.sys_base_executable -ne $baseInterpreter -or
        [string]$Start.environment.sys_prefix -ne (Split-Path -Parent (Split-Path -Parent $venvLauncher)) -or
        [string]$Start.environment.sys_base_prefix -ne (Split-Path -Parent $baseInterpreter) -or
        [bool]$Start.environment.main_thread_only -ne $true -or
        [string]$Start.environment.cuda_visible_devices -ne '-1' -or
        [string]$Start.environment.python_hash_seed -ne '0'
    ) {
        throw "Python start-record identity mismatch for $Action."
    }
    foreach ($name in @(
        'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
        'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS'
    )) {
        if ([string]$Start.environment.thread_bounds.$name -ne '1') {
            throw "Python thread-bound mismatch for $Action/$name."
        }
    }
    foreach ($name in @('runner', 'protocol', 'implementation_lock', 'launcher', 'base_interpreter', 'venv_launcher', 'venv_config')) {
        $expectedHashName = if ($name -eq 'implementation_lock') { 'lock_sha256' } else { $name + '_sha256' }
        if ([string]$Start.environment.runtime_files.$name.sha256 -ne [string]$Runtime.$expectedHashName) {
            throw "Python runtime-file hash mismatch for $Action/$name."
        }
    }
}

function Start-H9AChild {
    param(
        [Parameter(Mandatory = $true)][string]$Action,
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)]$Runtime,
        [Parameter(Mandatory = $true)][string]$LaunchId,
        [Parameter(Mandatory = $true)][string]$LaunchDirectory,
        [Parameter(Mandatory = $true)]$ExtraAuthorization
    )
    Assert-FixedHashes -Runtime $Runtime
    $token = [Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N')
    $authorizationPath = Join-Path $LaunchDirectory ($Label + '_authorization.json')
    $startPath = Join-Path $LaunchDirectory ($Label + '_process_start.json')
    $ackPath = Join-Path $LaunchDirectory ($Label + '_process_ack.json')
    $stdoutPath = Join-Path $LaunchDirectory ($Label + '_stdout.log')
    $stderrPath = Join-Path $LaunchDirectory ($Label + '_stderr.log')
    $asyncLedger = Join-Path $LaunchDirectory ($Label + '_async_errors.jsonl')
    foreach ($path in @($authorizationPath, $startPath, $ackPath, $stdoutPath, $stderrPath, $asyncLedger)) {
        if (Test-Path -LiteralPath $path) { throw "Refusing child-artifact overwrite: $path" }
    }
    New-ExclusiveEmptyFile -Path $asyncLedger
    $authorization = [ordered]@{
        mode = 'h9a-launcher-authorization'
        action = $Action
        launch_id = $LaunchId
        launcher_pid = [int]$PID
        token = $token
        token_sha256 = Get-StringSha256 -Value $token
        runner_sha256 = $Runtime.runner_sha256
        protocol_sha256 = $Runtime.protocol_sha256
        lock_sha256 = $Runtime.lock_sha256
        launcher_path = $launcher
        launcher_sha256 = $Runtime.launcher_sha256
        base_interpreter = $baseInterpreter
        base_interpreter_sha256 = $Runtime.base_interpreter_sha256
        venv_launcher = $venvLauncher
        venv_launcher_sha256 = $Runtime.venv_launcher_sha256
        venv_config = $venvConfig
        venv_config_sha256 = $Runtime.venv_config_sha256
        authorization_path = $authorizationPath
        outer_lock = $outerLock
        inner_lock = $innerLock
        launch_directory = $LaunchDirectory
        async_error_ledger = $asyncLedger
        process_start_path = $startPath
        process_ack_path = $ackPath
        phase_a_commit = $phaseACommit
        phase_a_commit_tree_result_sha256 = $expectedInputHashes.phase_a_result
        immutable_input_sha256 = $expectedInputHashes
        label_free_only = $true
        candidate_suffix_labels_forbidden = $true
        authorized_unix_ns = Get-UnixTimeNs
    }
    foreach ($property in $ExtraAuthorization.Keys) {
        $authorization[$property] = $ExtraAuthorization[$property]
    }
    Write-ExclusiveJson -Path $authorizationPath -Value $authorization
    $arguments = @(
        '-B', '-u', ('"{0}"' -f $runner), $Action,
        '--authorization', ('"{0}"' -f $authorizationPath),
        '--token', $token,
        '--process-start', ('"{0}"' -f $startPath),
        '--process-ack', ('"{0}"' -f $ackPath)
    )
    $process = $null
    $accepted = $false
    $operationFailure = $null
    $terminationFailures = @()
    $childRecord = $null
    $stopwatch = $null
    $launcherElapsedSeconds = $null
    $launcherPeakResidentBytes = $null
    try {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $process = Start-Process `
            -FilePath $baseInterpreter `
            -ArgumentList $arguments `
            -WorkingDirectory $root `
            -WindowStyle Hidden `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath `
            -PassThru
        $script:activeChild = $process
        # Windows PowerShell 5.1 can leave ExitCode null for a redirected
        # Start-Process child unless the native handle is materialized now
        # (PowerShell issue #5421).  A null exit code must never be accepted.
        $nativeHandle = $process.Handle
        if ($nativeHandle -eq [IntPtr]::Zero) {
            throw "Python child $Label returned a zero native process handle."
        }
        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        $start = $null
        while ($null -eq $start) {
            if (Test-Path -LiteralPath $startPath -PathType Leaf) {
                try { $start = [System.IO.File]::ReadAllText($startPath) | ConvertFrom-Json }
                catch { $start = $null }
            }
            if ($null -eq $start -and $process.HasExited) {
                throw "Python child exited before PID handshake for $Label."
            }
            if ($null -eq $start -and [DateTime]::UtcNow -ge $deadline) {
                throw "Python PID handshake timed out for $Label."
            }
            if ($null -eq $start) { Start-Sleep -Milliseconds 50 }
        }
        Assert-StartRecord `
            -Start $start `
            -Action $Action `
            -LaunchId $LaunchId `
            -LauncherPid ([int]$PID) `
            -ProcessPid ([int]$process.Id) `
            -AuthorizationPath $authorizationPath `
            -Token $token `
            -Runtime $Runtime
        Write-ExclusiveJson -Path $ackPath -Value ([ordered]@{
            mode = 'h9a-child-process-acknowledgement'
            action = $Action
            launch_id = $LaunchId
            launcher_pid = [int]$PID
            process_pid = [int]$process.Id
            authorization_sha256 = Get-Sha256 -Path $authorizationPath
            token_sha256 = Get-StringSha256 -Value $token
            acknowledged_unix_ns = Get-UnixTimeNs
        })
        $accepted = $true
        # The 300-second protocol threshold is an adjudication gate, not a
        # destructive timeout.  Wait for the exact PID so a slow completed run
        # can be committed as a valid KILL rather than becoming partial output.
        $process.WaitForExit()
        $rawExitCode = $process.ExitCode
        $launcherPeakResidentBytes = [Int64]$process.PeakWorkingSet64
        $script:activeChild = $null
        if ($null -eq $rawExitCode) {
            throw "Python child $Label exposed no exit code after an exact-PID wait."
        }
        $exitCode = [int]$rawExitCode
        if ($exitCode -ne 0) {
            throw "Python child $Label exited $exitCode; see $stderrPath"
        }
        if ((Get-Item -LiteralPath $stderrPath).Length -ne 0) {
            throw "Python child $Label emitted stderr despite exit zero."
        }
        if ((Get-Item -LiteralPath $asyncLedger).Length -ne 0) {
            throw "Python child $Label recorded an asynchronous error."
        }
        $summary = Read-LastJsonSummary -Path $stdoutPath
        if ([int]$summary.process_pid -ne [int]$process.Id) {
            throw "Python child $Label summary PID mismatch."
        }
        Assert-FixedHashes -Runtime $Runtime
        $stopwatch.Stop()
        $launcherElapsedSeconds = [double]$stopwatch.Elapsed.TotalSeconds
        if ([double]::IsNaN($launcherElapsedSeconds) -or
            [double]::IsInfinity($launcherElapsedSeconds) -or
            $launcherElapsedSeconds -lt 0.0 -or
            $launcherPeakResidentBytes -le 0) {
            throw "Python child $Label exposed invalid launcher-observed runtime evidence."
        }
        $childRecord = [pscustomobject]@{
            label = $Label
            pid = [int]$process.Id
            exit_code = $exitCode
            launcher_elapsed_seconds = $launcherElapsedSeconds
            launcher_peak_resident_bytes = $launcherPeakResidentBytes
            summary = $summary
            authorization = Get-FileRecord -Path $authorizationPath
            process_start = Get-FileRecord -Path $startPath
            process_ack = Get-FileRecord -Path $ackPath
            stdout = Get-FileRecord -Path $stdoutPath
            stderr = Get-FileRecord -Path $stderrPath
            async_error_ledger = Get-FileRecord -Path $asyncLedger
        }
    }
    catch {
        $operationFailure = $_
    }
    finally {
        if ($null -ne $stopwatch -and $stopwatch.IsRunning) {
            $stopwatch.Stop()
        }
        if ($null -ne $process -and (-not $accepted -or $script:activeChild -ne $null)) {
            try {
                Stop-H9AChildExact -Process $process -Label $Label
                $script:activeChild = $null
            }
            catch {
                $terminationFailures += $_
            }
        }
    }
    if ($null -ne $operationFailure) {
        if ($terminationFailures.Count -ne 0) {
            throw (New-H9AAggregateException `
                -Message "Python child $Label failed and exact termination also failed." `
                -Primary $operationFailure `
                -CleanupErrors $terminationFailures)
        }
        throw $operationFailure
    }
    if ($terminationFailures.Count -ne 0) {
        throw (New-H9AAggregateException `
            -Message "Python child $Label exact termination failed." `
            -Primary $null `
            -CleanupErrors $terminationFailures)
    }
    if ($null -eq $childRecord) {
        throw "Python child $Label reached an empty return state."
    }
    return $childRecord
}

function Get-H9ARuntimeEvidence {
    param(
        [Parameter(Mandatory = $true)]$Child,
        [Parameter(Mandatory = $true)][string]$Label
    )
    foreach ($name in @(
        'structural_verdict', 'elapsed_seconds', 'peak_resident_bytes', 'runtime_passed'
    )) {
        if ($null -eq $Child.summary.PSObject.Properties[$name]) {
            throw "Python child $Label omitted required runtime-summary field $name."
        }
    }
    $structuralVerdict = [string]$Child.summary.structural_verdict
    if ($structuralVerdict -notin @(
        'ADVANCE_TO_H9B_PROVENANCE_WORLDS', 'KILL_H9_KRON_DIRECTION'
    )) {
        throw "Python child $Label exposed an invalid structural verdict."
    }
    $runnerElapsedSeconds = [double]$Child.summary.elapsed_seconds
    $runnerPeakResidentBytes = [Int64]$Child.summary.peak_resident_bytes
    if ([double]::IsNaN($runnerElapsedSeconds) -or
        [double]::IsInfinity($runnerElapsedSeconds) -or
        $runnerElapsedSeconds -lt 0.0 -or
        $runnerPeakResidentBytes -le 0) {
        throw "Python child $Label exposed invalid runner runtime evidence."
    }
    if ($Child.summary.runtime_passed -isnot [System.Boolean]) {
        throw "Python child $Label runtime_passed is not Boolean."
    }
    $runnerRuntimePassed = (
        $runnerElapsedSeconds -le 300.0 -and
        $runnerPeakResidentBytes -le [Int64]2147483648
    )
    if ([bool]$Child.summary.runtime_passed -ne $runnerRuntimePassed) {
        throw "Python child $Label runtime diagnostic is internally inconsistent."
    }
    $launcherElapsedSeconds = [double]$Child.launcher_elapsed_seconds
    $launcherPeakResidentBytes = [Int64]$Child.launcher_peak_resident_bytes
    if ([double]::IsNaN($launcherElapsedSeconds) -or
        [double]::IsInfinity($launcherElapsedSeconds) -or
        $launcherElapsedSeconds -lt 0.0 -or
        $launcherElapsedSeconds -lt $runnerElapsedSeconds -or
        $launcherPeakResidentBytes -le 0) {
        throw "Python child $Label exposed invalid launcher runtime evidence."
    }
    $authoritativePeakResidentBytes = if (
        $launcherPeakResidentBytes -gt $runnerPeakResidentBytes
    ) {
        $launcherPeakResidentBytes
    }
    else {
        $runnerPeakResidentBytes
    }
    $authoritativeRuntimePassed = (
        $launcherElapsedSeconds -le 300.0 -and
        $authoritativePeakResidentBytes -le [Int64]2147483648
    )
    return [pscustomobject][ordered]@{
        structural_verdict = $structuralVerdict
        runner_elapsed_seconds = $runnerElapsedSeconds
        launcher_elapsed_seconds = $launcherElapsedSeconds
        runner_peak_resident_bytes = $runnerPeakResidentBytes
        launcher_peak_resident_bytes = $launcherPeakResidentBytes
        authoritative_peak_resident_bytes = $authoritativePeakResidentBytes
        runner_runtime_passed = $runnerRuntimePassed
        authoritative_runtime_passed = $authoritativeRuntimePassed
    }
}

function Assert-H9AVerifierRuntimeGate {
    param(
        [Parameter(Mandatory = $true)]$Gate,
        [Parameter(Mandatory = $true)]$PrimaryRuntime,
        [Parameter(Mandatory = $true)]$ReplayRuntime,
        [Parameter(Mandatory = $true)][string]$Source
    )
    foreach ($name in @(
        'limit_seconds', 'limit_peak_resident_bytes',
        'primary_launcher_elapsed_seconds', 'replay_launcher_elapsed_seconds',
        'primary_peak_resident_bytes', 'replay_peak_resident_bytes',
        'primary_passed', 'replay_passed', 'passed'
    )) {
        if ($null -eq $Gate.PSObject.Properties[$name]) {
            throw "Deep-verifier $Source omitted runtime-gate field $name."
        }
    }
    if ([double]$Gate.limit_seconds -ne 300.0 -or
        [Int64]$Gate.limit_peak_resident_bytes -ne [Int64]2147483648 -or
        [double]$Gate.primary_launcher_elapsed_seconds -ne [double]$PrimaryRuntime.launcher_elapsed_seconds -or
        [double]$Gate.replay_launcher_elapsed_seconds -ne [double]$ReplayRuntime.launcher_elapsed_seconds -or
        [Int64]$Gate.primary_peak_resident_bytes -ne [Int64]$PrimaryRuntime.authoritative_peak_resident_bytes -or
        [Int64]$Gate.replay_peak_resident_bytes -ne [Int64]$ReplayRuntime.authoritative_peak_resident_bytes) {
        throw "Deep-verifier $Source runtime evidence differs from the launcher record."
    }
    foreach ($name in @('primary_passed', 'replay_passed', 'passed')) {
        if ($Gate.$name -isnot [System.Boolean]) {
            throw "Deep-verifier $Source runtime-gate field $name is not Boolean."
        }
    }
    if ([bool]$Gate.primary_passed -ne [bool]$PrimaryRuntime.authoritative_runtime_passed -or
        [bool]$Gate.replay_passed -ne [bool]$ReplayRuntime.authoritative_runtime_passed -or
        [bool]$Gate.passed -ne (
            [bool]$PrimaryRuntime.authoritative_runtime_passed -and
            [bool]$ReplayRuntime.authoritative_runtime_passed
        )) {
        throw "Deep-verifier $Source runtime-gate decision differs from launcher recomputation."
    }
}

$runtime = [ordered]@{
    runner_sha256 = Get-Sha256 -Path $runner
    launcher_sha256 = Get-Sha256 -Path $launcher
    protocol_sha256 = Get-Sha256 -Path $protocol
    lock_sha256 = Get-Sha256 -Path $implementationLock
    base_interpreter_sha256 = Get-Sha256 -Path $baseInterpreter
    venv_launcher_sha256 = Get-Sha256 -Path $venvLauncher
    venv_config_sha256 = Get-Sha256 -Path $venvConfig
}
$launchId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '_' + [Guid]::NewGuid().ToString('N')
$launchPrefix = if ($isSelfTest) { 'h9st_' } else { 'h9_' }
$launchDirectoryToken = [Guid]::NewGuid().ToString('N').Substring(0, 20)
$launchDirectory = Join-Path $artifactRoot ($launchPrefix + $launchDirectoryToken)
$completionMarker = if ($isSelfTest) {
    Join-Path $launchDirectory 'selftest_completion.json'
}
else {
    $confirmatoryCompletionMarker
}
$outerLockMode = if ($isSelfTest) {
    'h9a-selftest-outer-lock'
}
else {
    'h9a-run-001-outer-lock'
}
if ([System.IO.Directory]::Exists($launchDirectory)) { throw 'Launch-directory collision.' }
[System.IO.Directory]::CreateDirectory($launchDirectory) | Out-Null

$lockStream = $null
$lockRetired = $null
$outerReleaseRecord = $null
$completionPayload = $null
$failure = $null
$cleanupFailures = @()
$script:activeChild = $null
try {
    $lock = Open-OuterLock `
        -Path $outerLock `
        -RetirementDirectory $launchDirectory `
        -ExpectedMode $outerLockMode
    $lockStream = $lock.Stream
    $lockRetired = if ($null -ne $lock.Retired) { Get-FileRecord -Path $lock.Retired } else { $null }
    $owner = [ordered]@{
        mode = $outerLockMode
        pid = [int]$PID
        launch_id = $launchId
        launcher_path = $launcher
        runtime = $runtime
        created_unix_ns = Get-UnixTimeNs
    }
    Write-HeldLockOwner -Stream $lockStream -Owner $owner

    if ($isSelfTest) {
        Assert-FixedHashes -Runtime $runtime
        $selfTestChild = Start-H9AChild `
            -Action 'self-test' `
            -Label 'selftest' `
            -Runtime $runtime `
            -LaunchId $launchId `
            -LaunchDirectory $launchDirectory `
            -ExtraAuthorization ([ordered]@{
                self_test_only = $true
                output_id = 'synthetic_selftest'
                run_role = 'selftest'
            })
        if ($selfTestChild.summary.status -ne 'H9A_SELFTEST_COMPLETE' -or
            $selfTestChild.summary.output_id -ne 'synthetic_selftest' -or
            $selfTestChild.summary.run_role -ne 'selftest' -or
            [string]$selfTestChild.summary.runner_sha256 -ne [string]$runtime.runner_sha256 -or
            [string]$selfTestChild.summary.protocol_sha256 -ne [string]$runtime.protocol_sha256 -or
            [string]$selfTestChild.summary.lock_sha256 -ne [string]$runtime.lock_sha256) {
            throw 'Isolated Python self-test summary identity mismatch.'
        }
        Assert-FixedHashes -Runtime $runtime
        $completionPayload = [ordered]@{
            schema_version = 'h9a_selftest_completion.v1'
            status = 'H9A_SELFTEST_COMPLETE'
            launch_id = $launchId
            launcher_pid = [int]$PID
            completed_unix_ns = Get-UnixTimeNs
            isolation = [ordered]@{
                real_input_files_opened = $false
                real_result_directories_opened = $false
                candidate_labels_opened = $false
                disjoint_outer_lock = $outerLock
                artifact_root = $selfTestRoot
            }
            execution_contract = [ordered]@{
                python_flags = @('-B', '-u')
                hidden_child = $true
                working_directory = $root
                bounded_numerical_threads = 1
                cuda_visible_devices = '-1'
                python_hash_seed = '0'
            }
            runtime = [ordered]@{
                runner = Get-FileRecord -Path $runner
                launcher = Get-FileRecord -Path $launcher
                protocol = Get-FileRecord -Path $protocol
                implementation_lock = Get-FileRecord -Path $implementationLock
                base_interpreter = Get-FileRecord -Path $baseInterpreter
                venv_launcher = Get-FileRecord -Path $venvLauncher
                venv_config = Get-FileRecord -Path $venvConfig
            }
            child = $selfTestChild
            retired_stale_outer_lock = $lockRetired
            completion_marker_is_last = $true
            outer_lock_release = $null
        }
    }
    else {
    foreach ($path in @($primaryDirectory, $replayDirectory, $completionMarker)) {
        if (Test-Path -LiteralPath $path) { throw "Refusing to overwrite fixed H9A artifact: $path" }
    }
    Assert-FixedHashes -Runtime $runtime
    Assert-ImmutableInputs
    Assert-ImplementationCommitted

    $primary = Start-H9AChild `
        -Action 'run' `
        -Label 'primary' `
        -Runtime $runtime `
        -LaunchId $launchId `
        -LaunchDirectory $launchDirectory `
        -ExtraAuthorization ([ordered]@{
            output_id = 'h9a_run_001'
            run_role = 'primary'
            inner_lock_release_path = (Join-Path $launchDirectory 'primary_inner_lock_released.json')
        })
    if ($primary.summary.status -ne 'H9A_RUN_COMPLETE' -or
        $primary.summary.output_id -ne 'h9a_run_001' -or
        $primary.summary.run_role -ne 'primary' -or
        [string]$primary.summary.output_directory -ne [string]$primaryDirectory -or
        [string]$primary.summary.result -ne [string](Join-Path $primaryDirectory 'result.json') -or
        [string]$primary.summary.row_manifest -ne [string](Join-Path $primaryDirectory 'row_manifest.jsonl')) {
        throw 'Primary child summary identity mismatch.'
    }
    $primaryRuntime = Get-H9ARuntimeEvidence -Child $primary -Label 'primary'
    if (Test-Path -LiteralPath $innerLock) { throw 'Inner lock remained after primary child.' }
    $primaryRelease = Join-Path $launchDirectory 'primary_inner_lock_released.json'
    if (-not (Test-Path -LiteralPath $primaryRelease -PathType Leaf)) {
        throw 'Primary inner-lock release artifact is missing.'
    }
    Assert-FixedHashes -Runtime $runtime
    Assert-ImmutableInputs

    $replay = Start-H9AChild `
        -Action 'run' `
        -Label 'exact_replay' `
        -Runtime $runtime `
        -LaunchId $launchId `
        -LaunchDirectory $launchDirectory `
        -ExtraAuthorization ([ordered]@{
            output_id = 'h9a_run_001_replay'
            run_role = 'exact_replay'
            inner_lock_release_path = (Join-Path $launchDirectory 'exact_replay_inner_lock_released.json')
        })
    if ($replay.summary.status -ne 'H9A_RUN_COMPLETE' -or
        $replay.summary.output_id -ne 'h9a_run_001_replay' -or
        $replay.summary.run_role -ne 'exact_replay' -or
        [string]$replay.summary.output_directory -ne [string]$replayDirectory -or
        [string]$replay.summary.result -ne [string](Join-Path $replayDirectory 'result.json') -or
        [string]$replay.summary.row_manifest -ne [string](Join-Path $replayDirectory 'row_manifest.jsonl')) {
        throw 'Replay child summary identity mismatch.'
    }
    $replayRuntime = Get-H9ARuntimeEvidence -Child $replay -Label 'exact_replay'
    if (Test-Path -LiteralPath $innerLock) { throw 'Inner lock remained after replay child.' }
    $replayRelease = Join-Path $launchDirectory 'exact_replay_inner_lock_released.json'
    if (-not (Test-Path -LiteralPath $replayRelease -PathType Leaf)) {
        throw 'Replay inner-lock release artifact is missing.'
    }
    Assert-FixedHashes -Runtime $runtime
    Assert-ImmutableInputs
    if (
        [string]$primary.summary.scientific_payload_sha256 -ne [string]$replay.summary.scientific_payload_sha256 -or
        [string]$primaryRuntime.structural_verdict -ne [string]$replayRuntime.structural_verdict
    ) {
        throw 'Exact replay scientific payload or structural verdict differs before deep verification.'
    }
    $primaryManifest = Join-Path $primaryDirectory 'row_manifest.jsonl'
    $replayManifest = Join-Path $replayDirectory 'row_manifest.jsonl'
    if ((Get-Sha256 -Path $primaryManifest) -ne (Get-Sha256 -Path $replayManifest) -or
        (Get-Item -LiteralPath $primaryManifest).Length -ne (Get-Item -LiteralPath $replayManifest).Length) {
        throw 'Exact replay row manifest is not byte-identical to primary.'
    }

    $verificationPath = Join-Path $launchDirectory 'deep_verification.json'
    $allRuntimeGatesPassed = (
        [bool]$primaryRuntime.authoritative_runtime_passed -and
        [bool]$replayRuntime.authoritative_runtime_passed
    )
    $expectedFinalVerdict = if (
        [string]$primaryRuntime.structural_verdict -eq 'ADVANCE_TO_H9B_PROVENANCE_WORLDS' -and
        $allRuntimeGatesPassed
    ) {
        'ADVANCE_TO_H9B_PROVENANCE_WORLDS'
    }
    else {
        'KILL_H9_KRON_DIRECTION'
    }
    $verifier = Start-H9AChild `
        -Action 'verify' `
        -Label 'verifier' `
        -Runtime $runtime `
        -LaunchId $launchId `
        -LaunchDirectory $launchDirectory `
        -ExtraAuthorization ([ordered]@{
            output_id = 'deep_verification'
            run_role = 'verifier'
            verification_path = $verificationPath
            primary_launcher_elapsed_seconds = [double]$primaryRuntime.launcher_elapsed_seconds
            replay_launcher_elapsed_seconds = [double]$replayRuntime.launcher_elapsed_seconds
            primary_peak_resident_bytes = [Int64]$primaryRuntime.authoritative_peak_resident_bytes
            replay_peak_resident_bytes = [Int64]$replayRuntime.authoritative_peak_resident_bytes
            primary_runtime_passed = [bool]$primaryRuntime.authoritative_runtime_passed
            replay_runtime_passed = [bool]$replayRuntime.authoritative_runtime_passed
        })
    if ($verifier.summary.status -ne 'H9A_VERIFY_COMPLETE' -or
        $verifier.summary.output_id -ne 'deep_verification' -or
        $verifier.summary.run_role -ne 'verifier' -or
        [string]$verifier.summary.verification_path -ne [string]$verificationPath -or
        [string]$verifier.summary.structural_verdict -ne [string]$primaryRuntime.structural_verdict) {
        throw 'Deep-verifier summary identity mismatch.'
    }
    Assert-H9AVerifierRuntimeGate `
        -Gate $verifier.summary.runtime_gate `
        -PrimaryRuntime $primaryRuntime `
        -ReplayRuntime $replayRuntime `
        -Source 'summary'
    if (
        [string]$verifier.summary.scientific_payload_sha256 -ne [string]$primary.summary.scientific_payload_sha256 -or
        [string]$verifier.summary.verdict -ne $expectedFinalVerdict
    ) {
        throw 'Deep-verifier scientific hash or final verdict differs from launcher recomputation.'
    }
    if (-not (Test-Path -LiteralPath $verificationPath -PathType Leaf)) {
        throw 'Deep-verification file is missing.'
    }
    if ([string]$verifier.summary.verification_sha256 -ne (Get-Sha256 -Path $verificationPath)) {
        throw 'Deep-verification file hash differs from verifier summary.'
    }
    $verification = [System.IO.File]::ReadAllText($verificationPath) | ConvertFrom-Json
    if ($verification.status -ne 'H9A_DEEP_VERIFY_COMPLETE' -or
        [string]$verification.scientific_payload_sha256 -ne [string]$primary.summary.scientific_payload_sha256 -or
        [string]$verification.structural_verdict -ne [string]$primaryRuntime.structural_verdict -or
        [string]$verification.verdict -ne $expectedFinalVerdict) {
        throw 'Deep-verification file identity mismatch.'
    }
    Assert-H9AVerifierRuntimeGate `
        -Gate $verification.runtime_gate `
        -PrimaryRuntime $primaryRuntime `
        -ReplayRuntime $replayRuntime `
        -Source 'file'
    if (Test-Path -LiteralPath $innerLock) { throw 'Inner lock exists after deep verification.' }
    Assert-FixedHashes -Runtime $runtime
    Assert-ImmutableInputs
    Assert-ImplementationCommitted

    $expectedArtifacts = @('result.json', 'row_manifest.jsonl') | Sort-Object
    foreach ($directory in @($primaryDirectory, $replayDirectory)) {
        $artifactNames = @(Get-ChildItem -LiteralPath $directory | Select-Object -ExpandProperty Name | Sort-Object)
        if (($artifactNames -join '|') -ne ($expectedArtifacts -join '|')) {
            throw "Unexpected final result artifact inventory: $directory"
        }
    }
    $completionPayload = [ordered]@{
        schema_version = 'h9a_run_001_completion.v1'
        status = 'H9A_RUN_001_COMPLETE'
        launch_id = $launchId
        launcher_pid = [int]$PID
        completed_unix_ns = Get-UnixTimeNs
        execution_contract = [ordered]@{
            engine = 'single-process 50-anchor RevKron interval-cache scorer with streamed 812-pattern cohort evaluation'
            parity_claim = 'byte-identical row manifests and identical scientific payloads under primary, exact replay, and independent deep verification'
            python_flags = @('-B', '-u')
            hidden_children = $true
            bounded_numerical_threads = 1
            cuda_visible_devices = '-1'
            python_hash_seed = '0'
            candidate_labels_opened = $false
            label_free_input_surface = $true
        }
        runtime = [ordered]@{
            runner = Get-FileRecord -Path $runner
            launcher = Get-FileRecord -Path $launcher
            protocol = Get-FileRecord -Path $protocol
            implementation_lock = Get-FileRecord -Path $implementationLock
            base_interpreter = Get-FileRecord -Path $baseInterpreter
            venv_launcher = Get-FileRecord -Path $venvLauncher
            venv_config = Get-FileRecord -Path $venvConfig
        }
        immutable_input_sha256 = $expectedInputHashes
        retired_stale_outer_lock = $lockRetired
        children = [ordered]@{
            primary = $primary
            exact_replay = $replay
            verifier = $verifier
        }
        inner_lock_releases = [ordered]@{
            primary = Get-FileRecord -Path $primaryRelease
            exact_replay = Get-FileRecord -Path $replayRelease
        }
        outputs = [ordered]@{
            primary_result = Get-FileRecord -Path (Join-Path $primaryDirectory 'result.json')
            replay_result = Get-FileRecord -Path (Join-Path $replayDirectory 'result.json')
            primary_artifacts = Get-DirectoryFileRecords -Directory $primaryDirectory
            replay_artifacts = Get-DirectoryFileRecords -Directory $replayDirectory
            deep_verification = Get-FileRecord -Path $verificationPath
        }
        exact_replay = [ordered]@{
            scientific_payload_sha256 = [string]$verifier.summary.scientific_payload_sha256
            row_manifest_sha256 = Get-Sha256 -Path $primaryManifest
            row_manifest_bytes = [Int64](Get-Item -LiteralPath $primaryManifest).Length
            structural_verdict = [string]$primaryRuntime.structural_verdict
            verified = $true
        }
        runtime_gate = [ordered]@{
            elapsed_limit_seconds = 300.0
            peak_resident_limit_bytes = [Int64]2147483648
            primary = [ordered]@{
                runner_elapsed_seconds = [double]$primaryRuntime.runner_elapsed_seconds
                launcher_elapsed_seconds = [double]$primaryRuntime.launcher_elapsed_seconds
                runner_peak_resident_bytes = [Int64]$primaryRuntime.runner_peak_resident_bytes
                launcher_peak_resident_bytes = [Int64]$primaryRuntime.launcher_peak_resident_bytes
                authoritative_peak_resident_bytes = [Int64]$primaryRuntime.authoritative_peak_resident_bytes
                runner_diagnostic_passed = [bool]$primaryRuntime.runner_runtime_passed
                passed = [bool]$primaryRuntime.authoritative_runtime_passed
            }
            exact_replay = [ordered]@{
                runner_elapsed_seconds = [double]$replayRuntime.runner_elapsed_seconds
                launcher_elapsed_seconds = [double]$replayRuntime.launcher_elapsed_seconds
                runner_peak_resident_bytes = [Int64]$replayRuntime.runner_peak_resident_bytes
                launcher_peak_resident_bytes = [Int64]$replayRuntime.launcher_peak_resident_bytes
                authoritative_peak_resident_bytes = [Int64]$replayRuntime.authoritative_peak_resident_bytes
                runner_diagnostic_passed = [bool]$replayRuntime.runner_runtime_passed
                passed = [bool]$replayRuntime.authoritative_runtime_passed
            }
            all_passed = [bool]$allRuntimeGatesPassed
            verifier = $verification.runtime_gate
        }
        decision = [ordered]@{
            structural_verdict = [string]$primaryRuntime.structural_verdict
            runtime_gate_passed = [bool]$allRuntimeGatesPassed
            verdict = [string]$verifier.summary.verdict
        }
        completion_marker_is_last = $true
        outer_lock_release = $null
    }
    }
}
catch {
    $failure = $_
}
finally {
    if ($null -ne $script:activeChild) {
        try {
            Stop-H9AChildExact -Process $script:activeChild -Label 'outer-cleanup-active-child'
            $script:activeChild = $null
        }
        catch {
            $cleanupFailures += $_
        }
    }
    if ($null -ne $lockStream) {
        if ($null -ne $script:activeChild) {
            $cleanupFailures += [System.InvalidOperationException]::new(
                'Refusing explicit outer-lock release because exact child termination was not verified.'
            )
        }
        else {
            $lockDisposed = $false
            try {
                $lockStream.Dispose()
                $lockStream = $null
                $lockDisposed = $true
            }
            catch {
                $cleanupFailures += $_
            }
            if ($lockDisposed) {
                $releaseName = if ($null -eq $failure) {
                    'outer_release.json'
                }
                else {
                    'outer_fail_{0}.json' -f [Guid]::NewGuid().ToString('N').Substring(0, 20)
                }
                $releasePath = Join-Path $launchDirectory $releaseName
                try {
                    if (-not [System.IO.File]::Exists($outerLock)) {
                        throw "Held outer lock disappeared before release: $outerLock"
                    }
                    Move-ExclusiveFileWithRetry -Source $outerLock -Destination $releasePath
                    $outerReleaseRecord = Get-FileRecord -Path $releasePath
                }
                catch {
                    $cleanupFailures += $_
                }
            }
        }
    }
}

if ($null -ne $failure) {
    if ($cleanupFailures.Count -ne 0) {
        throw (New-H9AAggregateException `
            -Message 'H9A launcher failed and one or more cleanup operations also failed.' `
            -Primary $failure `
            -CleanupErrors $cleanupFailures)
    }
    throw $failure
}
if ($cleanupFailures.Count -ne 0) {
    throw (New-H9AAggregateException `
        -Message 'H9A launcher cleanup failed.' `
        -Primary $null `
        -CleanupErrors $cleanupFailures)
}
if ($null -eq $completionPayload -or $null -eq $outerReleaseRecord) {
    throw 'H9A launcher reached an invalid completion state.'
}
$completionPayload.outer_lock_release = $outerReleaseRecord
if (Test-Path -LiteralPath $completionMarker) { throw 'Completion marker appeared before publication.' }
Write-ExclusiveJson -Path $completionMarker -Value $completionPayload
# No filesystem mutation is permitted after the line above.
$completionPayload | ConvertTo-Json -Depth 40 -Compress
