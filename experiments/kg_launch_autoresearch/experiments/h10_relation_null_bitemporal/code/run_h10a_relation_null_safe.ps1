
param(
    [ValidateSet('Probe', 'SelfTest', 'Real')][string]$Mode = 'SelfTest',
    [string]$ConfirmReal = ''
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Set-StrictMode -Version 2.0
$isProbe = $Mode -ceq 'Probe'
$isSelfTest = $Mode -ceq 'SelfTest'
$isReal = $Mode -ceq 'Real'
if (-not ($isProbe -or $isSelfTest -or $isReal)) {
    throw 'Mode casing must match Probe, SelfTest, or Real exactly.'
}
$expectedProtocolHash = 'D6083A0BE49DF3C8771F99882DC0A957E81B3DB7E60BFADA47E770CC52E4CEF3'
$requiredConfirmation = 'RUN_H10A_LABEL_BLIND@D6083A0BE49DF3C8771F99882DC0A957E81B3DB7E60BFADA47E770CC52E4CEF3:522D246FBA9769F7EE3C11C95E2710F0FD956B933B4D83E7D0371FA1FE42BEB5'
if ($isReal -and $ConfirmReal -ne $requiredConfirmation) {
    throw 'Real H10A execution requires the exact locked label-blind confirmation token.'
}

# Codex Desktop can expose PATH twice with different casing. Windows
# PowerShell 5.1 Start-Process rejects that environment block, so normalize it.
$canonicalPath = [Environment]::GetEnvironmentVariable(
    'Path', [EnvironmentVariableTarget]::Process
)
if ([String]::IsNullOrWhiteSpace($canonicalPath)) {
    throw 'Process Path is empty; refusing H10A launch.'
}
[Environment]::SetEnvironmentVariable('PATH', $null, [EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable('Path', $null, [EnvironmentVariableTarget]::Process)
[Environment]::SetEnvironmentVariable('Path', $canonicalPath, [EnvironmentVariableTarget]::Process)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$h10Root = (Resolve-Path -LiteralPath (Join-Path $here '..')).Path
$root = (Resolve-Path -LiteralPath (Join-Path $here '..\..\..\..\..')).Path
$h6PhaseARoot = Join-Path $root 'experiments\kg_launch_autoresearch\experiments\h6_ranking_consequence'
$resultsRoot = Join-Path $h10Root 'results'
$selfTestRoot = Join-Path $h10Root 'selftest_artifacts'
$probeRoot = Join-Path $h10Root 'probe_artifacts'
$artifactRoot = if ($isProbe) { $probeRoot } elseif ($isSelfTest) { $selfTestRoot } else { $resultsRoot }
$runner = (Resolve-Path -LiteralPath (Join-Path $here 'run_h10a_relation_null.py')).Path
$verifierCandidate = Join-Path $here 'verify_h10a_relation_null.py'
$verifier = if ($isProbe) {
    [System.IO.Path]::GetFullPath($verifierCandidate)
}
else {
    (Resolve-Path -LiteralPath $verifierCandidate).Path
}
$launcher = (Resolve-Path -LiteralPath $MyInvocation.MyCommand.Path).Path
$protocol = (Resolve-Path -LiteralPath (Join-Path $h10Root 'protocol.md')).Path
$probeLock = Join-Path $h10Root 'pcg_probe_lock.md'
$implementationLock = Join-Path $h10Root 'implementation_lock.md'
$activeLock = if ($isProbe) {
    (Resolve-Path -LiteralPath $probeLock).Path
}
else {
    (Resolve-Path -LiteralPath $implementationLock).Path
}
$syntheticGenerator = Join-Path $here 'generate_h10a_synthetic_fixture.py'
$syntheticFixtureManifest = Join-Path $h10Root 'synthetic_fixture_manifest.json'
$numpyManifest = Join-Path $probeRoot 'h10a_pcg_probe\numpy_package_manifest.jsonl'
$preflightAttestation = Join-Path $h10Root 'preflight_attestation.md'
$venvLauncher = (Resolve-Path -LiteralPath (Join-Path $root '_bestrec_run\.venv\Scripts\python.exe')).Path
$venvConfig = (Resolve-Path -LiteralPath (Join-Path $root '_bestrec_run\.venv\pyvenv.cfg')).Path
$homeLines = @(Get-Content -LiteralPath $venvConfig | Where-Object { $_ -match '^\s*home\s*=' })
if ($homeLines.Count -ne 1) {
    throw 'Could not resolve exactly one base-Python home from pyvenv.cfg.'
}
$venvHome = ($homeLines[0] -split '=', 2)[1].Trim()
$baseInterpreter = (Resolve-Path -LiteralPath (Join-Path $venvHome 'python.exe')).Path
$outerLock = if ($isProbe) {
    Join-Path $h10Root 'H10A_PROBE_LAUNCH.lock'
}
elseif ($isSelfTest) {
    Join-Path $h10Root 'H10A_SELFTEST_LAUNCH.lock'
}
else {
    Join-Path $h10Root 'H10A_RUN_001_LAUNCH.lock'
}
$innerLock = if ($isProbe) {
    Join-Path $h10Root 'H10A_PROBE_INNER.lock'
}
elseif ($isSelfTest) {
    Join-Path $h10Root 'H10A_SELFTEST_INNER.lock'
}
else {
    Join-Path $h10Root 'H10A_RUN_001_INNER.lock'
}
$probeCompletionMarker = Join-Path $probeRoot 'h10a_pcg_probe_completion.json'
$confirmatoryCompletionMarker = Join-Path $resultsRoot 'h10a_run_001_completion.json'
$scientificFileNames = @(
    'scientific_payload.json',
    'state_metrics.jsonl',
    'state_digests.jsonl',
    'chain_diagnostics.jsonl',
    'parity_checks.jsonl'
)
$harnessLimitSeconds = if ($isProbe) { 150 } elseif ($isSelfTest) { 150 } else { 180 }
$harnessLimitTicks = [Int64]$harnessLimitSeconds * [Int64][System.Diagnostics.Stopwatch]::Frequency
$peakResidentLimitBytes = [Int64]2147483648

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

if (-not ('H10A.NativeJob' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;

namespace H10A {
    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
        public long PerProcessUserTimeLimit;
        public long PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass;
        public uint SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct IO_COUNTERS {
        public ulong ReadOperationCount;
        public ulong WriteOperationCount;
        public ulong OtherOperationCount;
        public ulong ReadTransferCount;
        public ulong WriteTransferCount;
        public ulong OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_BASIC_ACCOUNTING_INFORMATION {
        public long TotalUserTime;
        public long TotalKernelTime;
        public long ThisPeriodTotalUserTime;
        public long ThisPeriodTotalKernelTime;
        public uint TotalPageFaultCount;
        public uint TotalProcesses;
        public uint ActiveProcesses;
        public uint TotalTerminatedProcesses;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_MEMORY_COUNTERS_EX {
        public uint cb;
        public uint PageFaultCount;
        public UIntPtr PeakWorkingSetSize;
        public UIntPtr WorkingSetSize;
        public UIntPtr QuotaPeakPagedPoolUsage;
        public UIntPtr QuotaPagedPoolUsage;
        public UIntPtr QuotaPeakNonPagedPoolUsage;
        public UIntPtr QuotaNonPagedPoolUsage;
        public UIntPtr PagefileUsage;
        public UIntPtr PeakPagefileUsage;
        public UIntPtr PrivateUsage;
    }

    public static class NativeJob {
        private const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateJobObject(IntPtr attributes, string name);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool SetInformationJobObject(
            IntPtr job, int infoClass, IntPtr info, uint length);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool QueryInformationJobObject(
            IntPtr job, int infoClass, IntPtr info, uint length, out uint returnedLength);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool TerminateJobObject(IntPtr job, uint exitCode);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr handle);

        [DllImport("kernel32.dll", EntryPoint = "K32GetProcessMemoryInfo", SetLastError = true)]
        private static extern bool K32GetProcessMemoryInfo(
            IntPtr process, out PROCESS_MEMORY_COUNTERS_EX counters, uint size);

        [DllImport("psapi.dll", EntryPoint = "GetProcessMemoryInfo", SetLastError = true)]
        private static extern bool PsapiGetProcessMemoryInfo(
            IntPtr process, out PROCESS_MEMORY_COUNTERS_EX counters, uint size);

        private static void ThrowLast(string operation) {
            throw new Win32Exception(Marshal.GetLastWin32Error(), operation);
        }

        public static IntPtr CreateKillOnCloseJob() {
            IntPtr job = CreateJobObject(IntPtr.Zero, null);
            if (job == IntPtr.Zero) ThrowLast("CreateJobObject failed");
            JOBOBJECT_EXTENDED_LIMIT_INFORMATION info =
                new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            int size = Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));
            IntPtr buffer = Marshal.AllocHGlobal(size);
            try {
                Marshal.StructureToPtr(info, buffer, false);
                if (!SetInformationJobObject(job, 9, buffer, (uint)size)) {
                    int error = Marshal.GetLastWin32Error();
                    CloseHandle(job);
                    throw new Win32Exception(error, "SetInformationJobObject failed");
                }
            }
            finally { Marshal.FreeHGlobal(buffer); }
            return job;
        }

        public static void Assign(IntPtr job, IntPtr process) {
            if (!AssignProcessToJobObject(job, process)) ThrowLast("AssignProcessToJobObject failed");
        }

        public static uint ActiveProcesses(IntPtr job) {
            int size = Marshal.SizeOf(typeof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION));
            IntPtr buffer = Marshal.AllocHGlobal(size);
            try {
                uint returnedLength;
                if (!QueryInformationJobObject(job, 1, buffer, (uint)size, out returnedLength)) {
                    ThrowLast("QueryInformationJobObject failed");
                }
                JOBOBJECT_BASIC_ACCOUNTING_INFORMATION info =
                    (JOBOBJECT_BASIC_ACCOUNTING_INFORMATION)Marshal.PtrToStructure(
                        buffer, typeof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION));
                return info.ActiveProcesses;
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }

        public static ulong PeakWorkingSetBytes(IntPtr process) {
            PROCESS_MEMORY_COUNTERS_EX counters = new PROCESS_MEMORY_COUNTERS_EX();
            counters.cb = (uint)Marshal.SizeOf(typeof(PROCESS_MEMORY_COUNTERS_EX));
            bool succeeded = false;
            try {
                succeeded = K32GetProcessMemoryInfo(process, out counters, counters.cb);
            }
            catch (EntryPointNotFoundException) {
                succeeded = false;
            }
            if (!succeeded) {
                counters = new PROCESS_MEMORY_COUNTERS_EX();
                counters.cb = (uint)Marshal.SizeOf(typeof(PROCESS_MEMORY_COUNTERS_EX));
                if (!PsapiGetProcessMemoryInfo(process, out counters, counters.cb)) {
                    ThrowLast("K32GetProcessMemoryInfo/GetProcessMemoryInfo failed");
                }
            }
            return counters.PeakWorkingSetSize.ToUInt64();
        }

        public static void Terminate(IntPtr job, uint exitCode) {
            if (!TerminateJobObject(job, exitCode)) ThrowLast("TerminateJobObject failed");
        }

        public static void Close(IntPtr job) {
            if (job != IntPtr.Zero && !CloseHandle(job)) ThrowLast("CloseHandle(job) failed");
        }
    }
}
'@
}

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

function Get-H10AJsonInt64 {
    param($Value,[Parameter(Mandatory = $true)][string]$Label)
    if ($Value -isnot [System.Int32] -and $Value -isnot [System.Int64]) {
        throw "JSON integer field is not an exact Int32/Int64: $Label"
    }
    return [Int64]$Value
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
        $candidate = Get-Process -Id $ProcessId -ErrorAction Stop
        return -not $candidate.HasExited
    }
    catch { return $false }
}

function New-H10AAggregateException {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [AllowNull()]$Primary,
        [Parameter(Mandatory = $true)][object[]]$CleanupErrors
    )
    $items = New-Object 'System.Collections.Generic.List[System.Exception]'
    foreach ($item in @($Primary) + @($CleanupErrors)) {
        if ($null -eq $item) { continue }
        if ($item -is [System.Management.Automation.ErrorRecord]) {
            $items.Add($item.Exception)
        }
        elseif ($item -is [System.Exception]) {
            $items.Add($item)
        }
        else {
            $items.Add([System.Exception]::new([string]$item))
        }
    }
    if ($items.Count -eq 0) { throw 'Cannot construct an empty H10A aggregate exception.' }
    return [System.AggregateException]::new($Message, $items)
}

function Get-TreeFileRecords {
    param([Parameter(Mandatory = $true)][string]$Directory)
    $records = @()
    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) { return @() }
    $rootPath = (Resolve-Path -LiteralPath $Directory).Path
    foreach ($file in @(Get-ChildItem -LiteralPath $rootPath -Recurse -Force -File | Sort-Object FullName)) {
        $records += [ordered]@{
            relative_path = $file.FullName.Substring($rootPath.Length).TrimStart('\').Replace('\', '/')
            path = $file.FullName
            sha256 = Get-Sha256 -Path $file.FullName
            bytes = [Int64]$file.Length
        }
    }
    return @($records)
}


function Get-SafePathInventory {
    param([Parameter(Mandatory = $true)][string]$Path)
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $inventory = [ordered]@{
        path = $fullPath
        exists = $false
        kind = 'missing'
        record = $null
        files = @()
        error = $null
    }
    try {
        if ([System.IO.File]::Exists($fullPath)) {
            $inventory.exists = $true
            $inventory.kind = 'file'
            $inventory.record = Get-FileRecord $fullPath
        }
        elseif ([System.IO.Directory]::Exists($fullPath)) {
            $inventory.exists = $true
            $inventory.kind = 'directory'
            $inventory.files = @(Get-TreeFileRecords $fullPath)
        }
    }
    catch {
        $inventory.kind = 'unreadable'
        $inventory.error = [string]$_
    }
    return $inventory
}


function Get-AuthorizedOutputInventories {
    $inventories = @()
    foreach ($binding in @($script:authorizedOutputDirectories)) {
        $outputPath = [System.IO.Path]::GetFullPath([string]$binding.output_directory)
        $parent = [System.IO.Path]::GetDirectoryName($outputPath)
        $name = [System.IO.Path]::GetFileName($outputPath)
        $prefixes = @(
            ('.stage-' + $name + '-')
            ('.' + $name + '.tmp.')
        )
        $stages = @()
        $enumerationError = $null
        try {
            if ([System.IO.Directory]::Exists($parent)) {
                foreach ($directory in @(Get-ChildItem -LiteralPath $parent -Force -Directory)) {
                    $matched = $false
                    foreach ($prefix in $prefixes) {
                        if ($directory.Name.StartsWith(
                            $prefix, [System.StringComparison]::Ordinal
                        )) {
                            $matched = $true
                            break
                        }
                    }
                    if ($matched) {
                        $stages += Get-SafePathInventory $directory.FullName
                    }
                }
            }
        }
        catch { $enumerationError = [string]$_ }
        $inventories += [ordered]@{
            run_role = [string]$binding.run_role
            subject_kind = [string]$binding.subject_kind
            output = Get-SafePathInventory $outputPath
            authorized_stage_prefixes = $prefixes
            stage_directories = @($stages)
            stage_enumeration_error = $enumerationError
        }
    }
    return @($inventories)
}


function Get-RootLockState {
    return [ordered]@{
        outer_lock = Get-SafePathInventory $outerLock
        inner_lock = Get-SafePathInventory $innerLock
    }
}


function Assert-EmbeddedFileRecords {
    param($Value,[string]$Context = 'root')
    if ($null -eq $Value) { return }
    if ($Value -is [System.Collections.IDictionary]) {
        if ($Value.Contains('path') -and $Value.Contains('sha256') -and $Value.Contains('bytes')) {
            $path = [string]$Value['path']
            if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
                (Get-Sha256 $path) -cne [string]$Value['sha256'] -or
                [Int64](Get-Item -LiteralPath $path).Length -ne [Int64]$Value['bytes']) {
                throw "Declared file record changed before terminal publication: $Context"
            }
        }
        foreach ($key in @($Value.Keys)) {
            Assert-EmbeddedFileRecords $Value[$key] ($Context + '.' + [string]$key)
        }
        return
    }
    if ($Value -is [pscustomobject]) {
        $properties = @($Value.PSObject.Properties.Name)
        if ($properties -contains 'path' -and
            $properties -contains 'sha256' -and
            $properties -contains 'bytes') {
            $path = [string]$Value.path
            if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
                (Get-Sha256 $path) -cne [string]$Value.sha256 -or
                [Int64](Get-Item -LiteralPath $path).Length -ne [Int64]$Value.bytes) {
                throw "Declared file record changed before terminal publication: $Context"
            }
        }
        foreach ($property in $Value.PSObject.Properties) {
            Assert-EmbeddedFileRecords $property.Value ($Context + '.' + $property.Name)
        }
        return
    }
    if ($Value -is [System.Collections.IEnumerable] -and $Value -isnot [string]) {
        $index = 0
        foreach ($item in $Value) {
            Assert-EmbeddedFileRecords $item ($Context + '[' + $index + ']')
            $index++
        }
    }
}


function Get-LockHashField {
    param([string]$LockText, [string]$Name)
    $tick = [regex]::Escape([string][char]96)
    $pattern = '(?m)^' + [regex]::Escape($Name) + ': ' + $tick + '([A-F0-9]{64})' + $tick + '\r?$'
    $matches = [regex]::Matches($LockText, $pattern)
    if ($matches.Count -ne 1) { throw "Active lock must contain exactly one $Name hash." }
    return $matches[0].Groups[1].Value
}

function Get-LockTextField {
    param([string]$LockText, [string]$Name)
    $tick = [regex]::Escape([string][char]96)
    $pattern = '(?m)^' + [regex]::Escape($Name) + ': ' + $tick + '([^' + $tick + '\r\n]+)' + $tick + '\r?$'
    $matches = [regex]::Matches($LockText, $pattern)
    if ($matches.Count -ne 1) { throw "Active lock must contain exactly one $Name text field." }
    return $matches[0].Groups[1].Value
}

function Assert-PathUnderH10Root {
    param([string]$Path)
    $candidate = [System.IO.Path]::GetFullPath($Path)
    $prefix = $h10Root.TrimEnd('\') + '\'
    if (-not $candidate.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes the H10A root: $candidate"
    }
    return $candidate
}

function Get-RuntimeFileRecords {
    $records = [ordered]@{
        runner = Get-FileRecord -Path $runner
        verifier = $null
        launcher = Get-FileRecord -Path $launcher
        protocol = Get-FileRecord -Path $protocol
        active_lock = Get-FileRecord -Path $activeLock
        base_interpreter = Get-FileRecord -Path $baseInterpreter
        venv_launcher = Get-FileRecord -Path $venvLauncher
        venv_config = Get-FileRecord -Path $venvConfig
        synthetic_generator = $null
        synthetic_fixture_manifest = $null
        numpy_package_manifest = $null
    }
    if (-not $isProbe) {
        $records.verifier = Get-FileRecord -Path $verifier
        $records.synthetic_generator = Get-FileRecord -Path $syntheticGenerator
        $records.synthetic_fixture_manifest = Get-FileRecord -Path $syntheticFixtureManifest
        $records.numpy_package_manifest = Get-FileRecord -Path $numpyManifest
    }
    return $records
}

function Get-InvalidRuntimeFileEvidence {
    $records = [ordered]@{
        runner = Get-SafePathInventory $runner
        verifier = $null
        launcher = Get-SafePathInventory $launcher
        protocol = Get-SafePathInventory $protocol
        active_lock = Get-SafePathInventory $activeLock
        base_interpreter = Get-SafePathInventory $baseInterpreter
        venv_launcher = Get-SafePathInventory $venvLauncher
        venv_config = Get-SafePathInventory $venvConfig
        synthetic_generator = $null
        synthetic_fixture_manifest = $null
        numpy_package_manifest = $null
        probe_completion = $null
    }
    if (-not $isProbe) {
        $records.verifier = Get-SafePathInventory $verifier
        $records.synthetic_generator = Get-SafePathInventory $syntheticGenerator
        $records.synthetic_fixture_manifest = Get-SafePathInventory $syntheticFixtureManifest
        $records.numpy_package_manifest = Get-SafePathInventory $numpyManifest
        $records.probe_completion = Get-SafePathInventory $probeCompletionMarker
    }
    return $records
}


function Get-RuntimeHashes {
    $hashes = [ordered]@{
        runner_sha256 = Get-Sha256 -Path $runner
        launcher_sha256 = Get-Sha256 -Path $launcher
        protocol_sha256 = Get-Sha256 -Path $protocol
        active_lock_sha256 = Get-Sha256 -Path $activeLock
        base_interpreter_sha256 = Get-Sha256 -Path $baseInterpreter
        venv_launcher_sha256 = Get-Sha256 -Path $venvLauncher
        venv_config_sha256 = Get-Sha256 -Path $venvConfig
    }
    if (-not $isProbe) {
        $lockText = [System.IO.File]::ReadAllText($activeLock)
        $hashes.verifier_sha256 = Get-Sha256 -Path $verifier
        $hashes.synthetic_generator_sha256 = Get-Sha256 -Path $syntheticGenerator
        $hashes.synthetic_fixture_manifest_sha256 = Get-Sha256 -Path $syntheticFixtureManifest
        $hashes.numpy_manifest_sha256 = Get-Sha256 -Path $numpyManifest
        $hashes.probe_completion_sha256 = Get-Sha256 -Path $probeCompletionMarker
        $hashes.expected_pcg_probe_sha256 = Get-LockHashField $lockText 'PCG64DXSM-Probe-SHA256'
    }
    return $hashes
}

function Assert-ProbeCompletionEvidence {
    param($Runtime)
    if ($isProbe) { throw 'Probe completion evidence is unavailable in Probe mode.' }
    $completion = [System.IO.File]::ReadAllText($probeCompletionMarker) | ConvertFrom-Json
    $wantedTop = @(
        'child','launch_id','launcher_pid','mode','numpy_package_manifest',
        'outer_lock_release','pcg_probe_sha256','probe_result',
        'retired_stale_outer_lock','runtime','runtime_files','runtime_hashes',
        'schema_version','status','terminal_marker_is_last'
    ) | Sort-Object
    $gotTop = @($completion.PSObject.Properties.Name | Sort-Object)
    if (($gotTop -join '|') -cne ($wantedTop -join '|')) {
        throw 'Probe completion property inventory differs.'
    }
    $launcherPid = Get-H10AJsonInt64 $completion.launcher_pid 'probe_completion.launcher_pid'
    if ([string]$completion.schema_version -cne 'h10a_probe_completion.v1' -or
        [string]$completion.status -cne 'H10A_PROBE_COMPLETE' -or
        [string]$completion.mode -cne 'Probe' -or
        [String]::IsNullOrWhiteSpace([string]$completion.launch_id) -or
        $launcherPid -le 0 -or
        $completion.terminal_marker_is_last -isnot [System.Boolean] -or
        [bool]$completion.terminal_marker_is_last -ne $true) {
        throw 'Probe completion identity differs.'
    }
    if ([string]$completion.pcg_probe_sha256 -cne
            [string]$Runtime.expected_pcg_probe_sha256 -or
        [string]$completion.numpy_package_manifest.path -cne
            (Resolve-Path -LiteralPath $numpyManifest).Path -or
        [string]$completion.numpy_package_manifest.sha256 -cne
            [string]$Runtime.numpy_manifest_sha256) {
        throw 'Probe completion scientific binding differs.'
    }

    $wantedTransport = @(
        'async_error_ledger','authorization','exit_code','inner_lock_release',
        'job_active_processes_after_exit','label','launcher_elapsed_ticks',
        'launcher_peak_resident_bytes','live_peak_samples','pid',
        'post_exit_peak_query','post_exit_peak_query_succeeded','process_ack',
        'process_start','stderr','stdout','stopwatch_frequency'
    ) | Sort-Object
    $gotTransport = @($completion.child.PSObject.Properties.Name | Sort-Object)
    $childPid = Get-H10AJsonInt64 $completion.child.pid 'probe_completion.child.pid'
    $childExit = Get-H10AJsonInt64 $completion.child.exit_code 'probe_completion.child.exit_code'
    $active = Get-H10AJsonInt64 $completion.child.job_active_processes_after_exit `
        'probe_completion.child.job_active_processes_after_exit'
    if (($gotTransport -join '|') -cne ($wantedTransport -join '|') -or
        [string]$completion.child.label -cne 'probe' -or
        $childPid -le 0 -or $childExit -ne 0 -or $active -ne 0 -or
        [string]$completion.child.post_exit_peak_query -cne 'success' -or
        $completion.child.post_exit_peak_query_succeeded -isnot [System.Boolean] -or
        [bool]$completion.child.post_exit_peak_query_succeeded -ne $true) {
        throw 'Probe completion transport differs.'
    }

    $wantedRuntime = @(
        'authoritative_peak_resident_bytes','launcher_elapsed_ticks',
        'launcher_peak_resident_bytes','module_ns','module_passed','perf_delta_ns',
        'perf_start_ns','perf_stop_ns','runner_peak_resident_bytes',
        'stopwatch_frequency'
    ) | Sort-Object
    $gotRuntime = @($completion.runtime.PSObject.Properties.Name | Sort-Object)
    $perfStart = Get-H10AJsonInt64 $completion.runtime.perf_start_ns `
        'probe_completion.runtime.perf_start_ns'
    $perfStop = Get-H10AJsonInt64 $completion.runtime.perf_stop_ns `
        'probe_completion.runtime.perf_stop_ns'
    $perfDelta = Get-H10AJsonInt64 $completion.runtime.perf_delta_ns `
        'probe_completion.runtime.perf_delta_ns'
    $runnerPeak = Get-H10AJsonInt64 $completion.runtime.runner_peak_resident_bytes `
        'probe_completion.runtime.runner_peak_resident_bytes'
    $launcherTicks = Get-H10AJsonInt64 $completion.runtime.launcher_elapsed_ticks `
        'probe_completion.runtime.launcher_elapsed_ticks'
    $frequency = Get-H10AJsonInt64 $completion.runtime.stopwatch_frequency `
        'probe_completion.runtime.stopwatch_frequency'
    $launcherPeak = Get-H10AJsonInt64 $completion.runtime.launcher_peak_resident_bytes `
        'probe_completion.runtime.launcher_peak_resident_bytes'
    $authoritativePeak = Get-H10AJsonInt64 `
        $completion.runtime.authoritative_peak_resident_bytes `
        'probe_completion.runtime.authoritative_peak_resident_bytes'
    if (($gotRuntime -join '|') -cne ($wantedRuntime -join '|') -or
        $perfStart -lt 0 -or $perfStop -lt $perfStart -or
        $perfDelta -ne ($perfStop-$perfStart) -or $runnerPeak -le 0 -or
        $launcherTicks -lt 0 -or $frequency -le 0 -or $launcherPeak -le 0 -or
        $authoritativePeak -ne [Math]::Max($runnerPeak,$launcherPeak) -or
        $null -ne $completion.runtime.module_ns -or
        $null -ne $completion.runtime.module_passed -or
        $launcherTicks -ne (Get-H10AJsonInt64 $completion.child.launcher_elapsed_ticks `
            'probe_completion.child.launcher_elapsed_ticks') -or
        $frequency -ne (Get-H10AJsonInt64 $completion.child.stopwatch_frequency `
            'probe_completion.child.stopwatch_frequency') -or
        $launcherPeak -ne (Get-H10AJsonInt64 `
            $completion.child.launcher_peak_resident_bytes `
            'probe_completion.child.launcher_peak_resident_bytes')) {
        throw 'Probe completion runtime differs.'
    }

    $wantedHashes = @(
        'active_lock_sha256','base_interpreter_sha256','launcher_sha256',
        'protocol_sha256','runner_sha256','venv_config_sha256',
        'venv_launcher_sha256'
    ) | Sort-Object
    $gotHashes = @($completion.runtime_hashes.PSObject.Properties.Name | Sort-Object)
    if (($gotHashes -join '|') -cne ($wantedHashes -join '|')) {
        throw 'Probe completion runtime-hash inventory differs.'
    }
    foreach ($name in @(
        'runner_sha256','launcher_sha256','protocol_sha256',
        'base_interpreter_sha256','venv_launcher_sha256','venv_config_sha256'
    )) {
        if ([string]$completion.runtime_hashes.$name -cne [string]$Runtime[$name]) {
            throw "Probe completion runtime differs: $name"
        }
    }
    if ([string]$completion.runtime_hashes.active_lock_sha256 -cne
        [string]$completion.runtime_files.active_lock.sha256) {
        throw 'Probe completion lock binding differs.'
    }
    Assert-EmbeddedFileRecords $completion 'probe_completion_evidence'
}

function Assert-FixedHashes {
    param($Runtime)
    $actual = [ordered]@{
        runner_sha256 = Get-Sha256 -Path $runner
        launcher_sha256 = Get-Sha256 -Path $launcher
        protocol_sha256 = Get-Sha256 -Path $protocol
        active_lock_sha256 = Get-Sha256 -Path $activeLock
        base_interpreter_sha256 = Get-Sha256 -Path $baseInterpreter
        venv_launcher_sha256 = Get-Sha256 -Path $venvLauncher
        venv_config_sha256 = Get-Sha256 -Path $venvConfig
    }
    foreach ($name in $actual.Keys) {
        if ([string]$actual[$name] -cne [string]$Runtime[$name]) {
            throw "Runtime changed during launch: $name"
        }
    }
    if ([string]$Runtime.protocol_sha256 -cne $expectedProtocolHash) {
        throw 'Protocol differs from the locked H10A bytes.'
    }
    $text = [System.IO.File]::ReadAllText($activeLock)
    $lockMap = [ordered]@{
        'Runner-SHA256' = $Runtime.runner_sha256
        'Launcher-SHA256' = $Runtime.launcher_sha256
        'Protocol-SHA256' = $Runtime.protocol_sha256
        'Base-Interpreter-SHA256' = $Runtime.base_interpreter_sha256
        'Venv-Launcher-SHA256' = $Runtime.venv_launcher_sha256
        'Venv-Config-SHA256' = $Runtime.venv_config_sha256
    }
    foreach ($name in $lockMap.Keys) {
        if ((Get-LockHashField $text $name) -cne [string]$lockMap[$name]) {
            throw "Runtime differs from lock field $name."
        }
    }
    if ((Get-LockTextField $text 'Python-Version') -cne '3.12.13' -or
        (Get-LockTextField $text 'NumPy-Version') -cne '2.4.4') {
        throw 'Locked Python or NumPy version differs from 3.12.13/2.4.4.'
    }
    if ($isProbe) {
        if ($Runtime.Contains('verifier_sha256') -or
            $Runtime.Contains('probe_completion_sha256') -or
            $Runtime.Contains('expected_pcg_probe_sha256')) {
            throw 'Probe runtime includes a forbidden post-probe binding.'
        }
        return
    }
    $mainActual = [ordered]@{
        verifier_sha256 = Get-Sha256 -Path $verifier
        synthetic_generator_sha256 = Get-Sha256 -Path $syntheticGenerator
        synthetic_fixture_manifest_sha256 = Get-Sha256 -Path $syntheticFixtureManifest
        numpy_manifest_sha256 = Get-Sha256 -Path $numpyManifest
        probe_completion_sha256 = Get-Sha256 -Path $probeCompletionMarker
    }
    $mainLock = [ordered]@{
        'Verifier-SHA256' = 'verifier_sha256'
        'Synthetic-Generator-SHA256' = 'synthetic_generator_sha256'
        'Synthetic-Fixture-Manifest-SHA256' = 'synthetic_fixture_manifest_sha256'
        'NumPy-Package-Manifest-SHA256' = 'numpy_manifest_sha256'
        'Probe-Completion-SHA256' = 'probe_completion_sha256'
    }
    foreach ($field in $mainLock.Keys) {
        $key = $mainLock[$field]
        if ([string]$mainActual[$key] -cne [string]$Runtime[$key] -or
            (Get-LockHashField $text $field) -cne [string]$Runtime[$key]) {
            throw "Main implementation binding differs: $field"
        }
    }
    if ((Get-LockTextField $text 'NumPy-Package-Manifest-Path') -cne
        'probe_artifacts/h10a_pcg_probe/numpy_package_manifest.jsonl') {
        throw 'Locked NumPy manifest path differs.'
    }
    if ((Get-LockTextField $text 'Probe-Completion-Path') -cne
        'probe_artifacts/h10a_pcg_probe_completion.json') {
        throw 'Locked probe-completion path differs.'
    }
    if ((Get-LockHashField $text 'PCG64DXSM-Probe-SHA256') -cne
        [string]$Runtime.expected_pcg_probe_sha256) {
        throw 'Locked PCG digest differs.'
    }
    Assert-ProbeCompletionEvidence $Runtime
}

function Get-ValidatedImmutableInputRecords {
    if (-not $isReal) { throw 'Real-input validation is forbidden outside Real mode.' }
    $records = [ordered]@{}
    foreach ($name in $expectedInputHashes.Keys) {
        if (-not (Test-Path -LiteralPath $inputPaths[$name] -PathType Leaf)) {
            throw "Immutable input missing or changed: $name"
        }
        $record = Get-FileRecord $inputPaths[$name]
        if ([string]$record.sha256 -cne [string]$expectedInputHashes[$name]) {
            throw "Immutable input missing or changed: $name"
        }
        $records[$name] = $record
    }
    if ([Int64]$records.phase_a_manifest.bytes -ne 224785295) {
        throw 'Phase-A manifest byte count mismatch.'
    }
    $resolved = (& git -C $root rev-parse ($phaseACommit + '^{commit}')).Trim()
    if ($LASTEXITCODE -ne 0 -or $resolved -cne $phaseACommit) {
        throw 'Phase-A commit is unavailable.'
    }
    if ((Get-CommittedTextSha256 $phaseACommit 'experiments/kg_launch_autoresearch/experiments/h6_ranking_consequence/results/coverage_run_002/result.json') -cne $expectedInputHashes.phase_a_result -or
        (Get-CommittedTextSha256 $phaseACommit 'experiments/kg_launch_autoresearch/experiments/h6_ranking_consequence/results/coverage_run_002_completion.json') -cne $expectedInputHashes.phase_a_completion) {
        throw 'Committed Phase-A tree hashes differ.'
    }
    & git -C $root merge-base --is-ancestor $phaseACommit HEAD
    if ($LASTEXITCODE -ne 0) { throw 'HEAD does not descend from Phase-A.' }
    return $records
}


function Assert-ImmutableInputs {
    $null = Get-ValidatedImmutableInputRecords
}


function New-ImmutableInputRevalidation {
    param($Child,[string]$RunRole,[string]$LaunchId,[string]$LaunchDirectory)
    if (-not $isReal) { throw 'Immutable-input revalidation evidence is Real-only.' }
    $evidencePath = Join-Path $LaunchDirectory ($RunRole + '_immutable_inputs_revalidated.json')
    if (Test-Path -LiteralPath $evidencePath) {
        throw "Immutable-input revalidation evidence exists: $RunRole"
    }
    $records = Get-ValidatedImmutableInputRecords
    $payload = [ordered]@{
        schema_version = 'h10a_immutable_input_revalidation.v1'
        status = 'H10A_IMMUTABLE_INPUTS_REVALIDATED'
        launch_id = $LaunchId
        run_role = $RunRole
        process_pid = [int]$Child.pid
        authorization = $Child.authorization
        process_start = $Child.process_start
        process_ack = $Child.process_ack
        immutable_inputs = $records
        phase_a_commit = $phaseACommit
        checked_unix_ns = Get-UnixTimeNs
    }
    Write-ExclusiveJson $evidencePath $payload
    $script:lastImmutableInputRecords = $records
    return Get-FileRecord $evidencePath
}

function Assert-ImplementationCommitted {
    $paths = @(
        'experiments/kg_launch_autoresearch/experiments/h10_relation_null_bitemporal/code/run_h10a_relation_null.py',
        'experiments/kg_launch_autoresearch/experiments/h10_relation_null_bitemporal/code/run_h10a_relation_null_safe.ps1',
        'experiments/kg_launch_autoresearch/experiments/h10_relation_null_bitemporal/protocol.md'
    )
    if ($isProbe) {
        $paths += 'experiments/kg_launch_autoresearch/experiments/h10_relation_null_bitemporal/pcg_probe_lock.md'
    }
    else {
        $paths += @(
            'experiments/kg_launch_autoresearch/experiments/h10_relation_null_bitemporal/code/verify_h10a_relation_null.py',
            'experiments/kg_launch_autoresearch/experiments/h10_relation_null_bitemporal/code/generate_h10a_synthetic_fixture.py',
            'experiments/kg_launch_autoresearch/experiments/h10_relation_null_bitemporal/synthetic_fixture_manifest.json',
            'experiments/kg_launch_autoresearch/experiments/h10_relation_null_bitemporal/probe_artifacts/h10a_pcg_probe/numpy_package_manifest.jsonl',
            'experiments/kg_launch_autoresearch/experiments/h10_relation_null_bitemporal/probe_artifacts/h10a_pcg_probe_completion.json',
            'experiments/kg_launch_autoresearch/experiments/h10_relation_null_bitemporal/implementation_lock.md'
        )
        if ($isReal) {
            $paths += 'experiments/kg_launch_autoresearch/experiments/h10_relation_null_bitemporal/preflight_attestation.md'
        }
    }
    foreach ($path in $paths) {
        & git -C $root ls-files --error-unmatch -- $path 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Uncommitted H10A path: $path" }
    }
    & git -C $root diff --quiet -- $paths
    if ($LASTEXITCODE -ne 0) { throw 'H10A paths differ from committed worktree.' }
    & git -C $root diff --cached --quiet -- $paths
    if ($LASTEXITCODE -ne 0) { throw 'H10A paths have staged changes.' }
}

function Assert-PreflightAttestation {
    if (-not $isReal) { throw 'Preflight attestation is Real-only.' }
    if (-not (Test-Path -LiteralPath $preflightAttestation -PathType Leaf)) {
        throw 'Preflight attestation is missing.'
    }
    $text = [System.IO.File]::ReadAllText($preflightAttestation)
    if ((Get-LockTextField $text 'Status') -cne 'PASS_H10A_PREFLIGHT' -or
        (Get-LockHashField $text 'Implementation-Lock-SHA256') -cne (Get-Sha256 $activeLock)) {
        throw 'Preflight attestation status or implementation hash differs.'
    }
    foreach ($binding in @(@('Runner-SHA256',$runner),@('Verifier-SHA256',$verifier),@('Launcher-SHA256',$launcher))) {
        if ((Get-LockHashField $text $binding[0]) -cne (Get-Sha256 $binding[1])) {
            throw "Preflight runtime binding differs: $($binding[0])"
        }
    }
    foreach ($prefix in @('SelfTest-Completion','Static-Audit')) {
        $relative = Get-LockTextField $text ($prefix + '-Path')
        $full = Assert-PathUnderH10Root (Join-Path $h10Root $relative.Replace('/','\'))
        if (-not (Test-Path -LiteralPath $full -PathType Leaf) -or
            (Get-Sha256 $full) -cne (Get-LockHashField $text ($prefix + '-SHA256'))) {
            throw "Preflight evidence differs: $prefix"
        }
    }
}


function Open-OuterLock {
    param([string]$Path, [string]$RetirementDirectory, [string]$ExpectedMode)
    $retired = $null
    for ($attempt = 0; $attempt -lt 2; $attempt++) {
        try {
            $stream = [System.IO.File]::Open(
                $Path,
                [System.IO.FileMode]::CreateNew,
                [System.IO.FileAccess]::ReadWrite,
                [System.IO.FileShare]::None
            )
            return [pscustomobject]@{ Stream = $stream; Retired = $retired }
        }
        catch {
            if ($attempt -ne 0) { throw 'Outer-lock acquisition raced after retirement.' }
            try {
                $owner = [System.IO.File]::ReadAllText($Path) | ConvertFrom-Json
                $expectedOwnerKeys = @(
                    'created_unix_ns','launch_id','launcher_path','mode','pid',
                    'runtime','schema_version'
                ) | Sort-Object
                $actualOwnerKeys = @($owner.PSObject.Properties.Name | Sort-Object)
                $baseRuntimeKeys = @(
                    'active_lock_sha256','base_interpreter_sha256',
                    'launcher_sha256','protocol_sha256','runner_sha256',
                    'venv_config_sha256','venv_launcher_sha256'
                )
                $mainRuntimeKeys = @(
                    'expected_pcg_probe_sha256','numpy_manifest_sha256',
                    'probe_completion_sha256','synthetic_fixture_manifest_sha256',
                    'synthetic_generator_sha256','verifier_sha256'
                )
                $expectedRuntimeKeys = @($baseRuntimeKeys)
                if ($ExpectedMode -cne 'h10a-probe-outer-lock') {
                    $expectedRuntimeKeys += $mainRuntimeKeys
                }
                $expectedRuntimeKeys = @($expectedRuntimeKeys | Sort-Object)
                $actualRuntimeKeys = @($owner.runtime.PSObject.Properties.Name | Sort-Object)
                if (($actualOwnerKeys -join '|') -cne ($expectedOwnerKeys -join '|') -or
                    ($actualRuntimeKeys -join '|') -cne ($expectedRuntimeKeys -join '|')) {
                    throw 'Malformed outer-lock inventory.'
                }
                foreach ($name in $expectedRuntimeKeys) {
                    $value = $owner.runtime.PSObject.Properties[$name].Value
                    if ($value -isnot [string] -or
                        [string]$value -cnotmatch '\A[A-F0-9]{64}\z') {
                        throw "Malformed outer-lock runtime hash: $name"
                    }
                }
                $ownerPid64 = Get-H10AJsonInt64 $owner.pid 'outer_lock.pid'
                $ownerCreatedNs = Get-H10AJsonInt64 `
                    $owner.created_unix_ns 'outer_lock.created_unix_ns'
                if ([string]$owner.schema_version -cne 'h10a_outer_lock.v1' -or
                    [string]$owner.mode -cne $ExpectedMode -or
                    [string]$owner.launcher_path -cne $launcher -or
                    [string]$owner.runtime.protocol_sha256 -cne $expectedProtocolHash -or
                    $ownerPid64 -le 0 -or $ownerPid64 -gt [Int32]::MaxValue -or
                    $ownerCreatedNs -le 0 -or
                    $owner.launch_id -isnot [string] -or
                    [String]::IsNullOrWhiteSpace([string]$owner.launch_id)) {
                    throw 'Malformed outer lock.'
                }
                $ownerPid = [int]$ownerPid64
            }
            catch {
                throw "Outer lock is unreadable or foreign: $Path"
            }
            if (Test-ProcessAlive $ownerPid) {
                throw "Active H10A outer lock belongs to PID $ownerPid."
            }
            $retired = Join-Path $RetirementDirectory (
                'stale_outer_' + [Guid]::NewGuid().ToString('N').Substring(0,20) + '.json'
            )
            Move-ExclusiveFileWithRetry $Path $retired
        }
    }
    throw 'Unreachable outer-lock state.'
}

function Write-HeldLockOwner {
    param([System.IO.FileStream]$Stream, $Owner)
    $json = ($Owner | ConvertTo-Json -Depth 30 -Compress) + [string][char]10
    $bytes = (New-Object System.Text.UTF8Encoding($false)).GetBytes($json)
    $Stream.Write($bytes, 0, $bytes.Length)
    $Stream.Flush($true)
    $Stream.Position = 0
}

function Read-LastJsonSummary {
    param([string]$Path)
    $lines = @(Get-Content -LiteralPath $Path |
        Where-Object { -not [String]::IsNullOrWhiteSpace($_) })
    if ($lines.Count -ne 1) { throw "Child stdout must contain exactly one JSON summary: $Path" }
    return $lines[0] | ConvertFrom-Json
}

function Assert-InnerLockOwner {
    param($Path,$Action,$RunRole,$LaunchId,[int]$ProcessPid,$AuthorizationPath,$Token)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Mandatory inner lock missing for $RunRole."
    }
    $owner = [System.IO.File]::ReadAllText($Path) | ConvertFrom-Json
    $expected = @(
        'action','authorization_sha256','created_unix_ns','launch_id','mode',
        'process_pid','run_role','token_sha256'
    ) | Sort-Object
    $actual = @($owner.PSObject.Properties.Name | Sort-Object)
    $ownerProcessPid = Get-H10AJsonInt64 $owner.process_pid ($RunRole + '.inner_lock.process_pid')
    $ownerCreatedNs = Get-H10AJsonInt64 $owner.created_unix_ns ($RunRole + '.inner_lock.created_unix_ns')
    if (($actual -join '|') -cne ($expected -join '|') -or
        [string]$owner.mode -cne 'h10a-child-inner-lock' -or
        [string]$owner.action -cne $Action -or
        [string]$owner.run_role -cne $RunRole -or
        [string]$owner.launch_id -cne $LaunchId -or
        $ownerProcessPid -ne $ProcessPid -or
        [string]$owner.authorization_sha256 -cne (Get-Sha256 $AuthorizationPath) -or
        [string]$owner.token_sha256 -cne (Get-StringSha256 $Token) -or
        $ownerCreatedNs -le 0) {
        throw "Inner-lock identity mismatch for $RunRole."
    }
}

function Write-InvalidInnerLockEvidence {
    param(
        [string]$EvidencePath,[string]$NormalReleasePath,[string]$ResourceReleasePath,
        [string]$Action,[string]$RunRole,[string]$LaunchId,[int]$ProcessPid,
        [string]$AuthorizationPath,[string]$Token,[bool]$OwnedTreeDeathProved
    )
    $evidence = [ordered]@{
        schema_version = 'h10a_invalid_inner_lock_evidence.v1'
        status = 'INCONCLUSIVE_INVALID_RUN_LOCK_EVIDENCE'
        action = $Action
        run_role = $RunRole
        launch_id = $LaunchId
        process_pid = $ProcessPid
        owned_process_tree_death_proved = $OwnedTreeDeathProved
        normal_release = $null
        normal_release_error = $null
        resource_release = $null
        resource_release_error = $null
        failed_release = $null
        remaining_inner_lock_untrusted_evidence = $null
        remaining_inner_lock_error = $null
        captured_unix_ns = Get-UnixTimeNs
    }

    if (Test-Path -LiteralPath $NormalReleasePath -PathType Leaf) {
        try {
            Assert-InnerLockOwner $NormalReleasePath $Action $RunRole $LaunchId $ProcessPid $AuthorizationPath $Token
            $evidence.normal_release = Get-FileRecord $NormalReleasePath
        }
        catch {
            $evidence.normal_release_error = [string]$_
            $evidence.normal_release = Get-SafePathInventory $NormalReleasePath
        }
    }
    if (Test-Path -LiteralPath $ResourceReleasePath -PathType Leaf) {
        try {
            Assert-InnerLockOwner $ResourceReleasePath $Action $RunRole $LaunchId $ProcessPid $AuthorizationPath $Token
            $evidence.resource_release = Get-FileRecord $ResourceReleasePath
        }
        catch {
            $evidence.resource_release_error = [string]$_
            $evidence.resource_release = Get-SafePathInventory $ResourceReleasePath
        }
    }

    if (Test-Path -LiteralPath $innerLock -PathType Leaf) {
        if (-not $OwnedTreeDeathProved -or $ProcessPid -le 0) {
            $evidence.remaining_inner_lock_error =
                'Inner lock left in place because exact owned-process-tree death was not proved.'
            $evidence.remaining_inner_lock_untrusted_evidence = Get-SafePathInventory $innerLock
        }
        else {
            $failedReleasePath = Join-Path (
                [System.IO.Path]::GetDirectoryName($EvidencePath)
            ) (
                $RunRole + '_inner_lock_failed_' +
                [Guid]::NewGuid().ToString('N').Substring(0,20) + '.json'
            )
            try {
                Assert-InnerLockOwner $innerLock $Action $RunRole $LaunchId $ProcessPid $AuthorizationPath $Token
                Move-ExclusiveFileWithRetry $innerLock $failedReleasePath
                Assert-InnerLockOwner $failedReleasePath $Action $RunRole $LaunchId $ProcessPid $AuthorizationPath $Token
                $evidence.failed_release = Get-FileRecord $failedReleasePath
            }
            catch {
                $evidence.remaining_inner_lock_error = [string]$_
                if (Test-Path -LiteralPath $innerLock) {
                    $evidence.remaining_inner_lock_untrusted_evidence = Get-SafePathInventory $innerLock
                }
                elseif (Test-Path -LiteralPath $failedReleasePath) {
                    $evidence.remaining_inner_lock_untrusted_evidence =
                        Get-SafePathInventory $failedReleasePath
                }
            }
        }
    }
    Write-ExclusiveJson $EvidencePath $evidence
    return Get-FileRecord $EvidencePath
}


function Assert-StartRecord {
    param(
        $Start,$Action,$RunRole,$SubjectKind,$SubjectPath,$OutputId,$LaunchId,
        [int]$ProcessPid,$AuthorizationPath,$Token,$Runtime,$RuntimeFiles
    )
    $expectedStartKeys = @(
        'action','authorization_sha256','environment','launch_id','launcher_pid',
        'mode','output_id','process_pid','run_role','subject_kind','subject_path',
        'subject_sha256','token_sha256'
    ) | Sort-Object
    $actualStartKeys = @($Start.PSObject.Properties.Name | Sort-Object)
    if (($actualStartKeys -join '|') -cne ($expectedStartKeys -join '|')) {
        throw "Start-record field inventory differs for $RunRole."
    }
    $startLauncherPid = Get-H10AJsonInt64 $Start.launcher_pid ($RunRole + '.start.launcher_pid')
    $startProcessPid = Get-H10AJsonInt64 $Start.process_pid ($RunRole + '.start.process_pid')
    if ([string]$Start.mode -cne 'h10a-child-process-start' -or
        [string]$Start.action -cne $Action -or
        [string]$Start.run_role -cne $RunRole -or
        [string]$Start.output_id -cne $OutputId -or
        [string]$Start.subject_kind -cne $SubjectKind -or
        [string]$Start.subject_path -cne $SubjectPath -or
        [string]$Start.subject_sha256 -cne (Get-Sha256 $SubjectPath) -or
        [string]$Start.launch_id -cne $LaunchId -or
        $startLauncherPid -ne [int]$PID -or
        $startProcessPid -ne $ProcessPid -or
        [string]$Start.authorization_sha256 -cne (Get-Sha256 $AuthorizationPath) -or
        [string]$Start.token_sha256 -cne (Get-StringSha256 $Token)) {
        throw "Start-record identity mismatch for $RunRole."
    }
    $environment = $Start.environment
    $expectedEnvironmentKeys = @(
        'cuda_visible_devices','main_thread_only','numpy_tree_manifest_sha256',
        'numpy_tree_validation_passed','numpy_version','pcg_probe_sha256',
        'python_hash_seed','python_version','runtime_files','sys_base_executable',
        'sys_base_prefix','sys_executable','sys_prefix','thread_bounds'
    ) | Sort-Object
    $actualEnvironmentKeys = @($environment.PSObject.Properties.Name | Sort-Object)
    if (($actualEnvironmentKeys -join '|') -cne ($expectedEnvironmentKeys -join '|')) {
        throw "Environment evidence inventory differs for $RunRole."
    }
    if ([string]$environment.sys_executable -cne $venvLauncher -or
        [string]$environment.sys_base_executable -cne $baseInterpreter -or
        [string]$environment.sys_prefix -cne (Split-Path -Parent (Split-Path -Parent $venvLauncher)) -or
        [string]$environment.sys_base_prefix -cne (Split-Path -Parent $baseInterpreter) -or
        $environment.main_thread_only -isnot [System.Boolean] -or
        [bool]$environment.main_thread_only -ne $true -or
        [string]$environment.cuda_visible_devices -cne '-1' -or
        [string]$environment.python_hash_seed -cne '0' -or
        [string]$environment.python_version -cne '3.12.13' -or
        [string]$environment.numpy_version -cne '2.4.4') {
        throw "Environment identity mismatch for $RunRole."
    }
    $threadNames = @(
        'OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS',
        'NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS','BLIS_NUM_THREADS'
    )
    $actualThreadNames = @($environment.thread_bounds.PSObject.Properties.Name | Sort-Object)
    if (($actualThreadNames -join '|') -cne (@($threadNames | Sort-Object) -join '|')) {
        throw "Thread-bound inventory differs for $RunRole."
    }
    foreach ($name in $threadNames) {
        if ([string]$environment.thread_bounds.$name -cne '1') {
            throw "Thread bound differs for $RunRole/$name."
        }
    }
    $actualRuntimeFileNames = @($environment.runtime_files.PSObject.Properties.Name | Sort-Object)
    if (($actualRuntimeFileNames -join '|') -cne (@($RuntimeFiles.Keys | Sort-Object) -join '|')) {
        throw "Runtime-file inventory differs for $RunRole."
    }
    foreach ($name in $RuntimeFiles.Keys) {
        $wanted = $RuntimeFiles[$name]
        $property = $environment.runtime_files.PSObject.Properties[$name]
        if ($null -eq $property) { throw "Start record omits runtime file $name." }
        $got = $property.Value
        if ($null -eq $wanted) {
            if ($null -ne $got) { throw "Unexpected runtime file $name." }
        }
        elseif ((@($got.PSObject.Properties.Name | Sort-Object) -join '|') -cne
                (@('bytes','path','sha256') -join '|') -or
            [string]$got.path -cne [string]$wanted.path -or
            [string]$got.sha256 -cne [string]$wanted.sha256 -or
            (Get-H10AJsonInt64 $got.bytes ($RunRole + '.runtime_files.' + $name + '.bytes')) -ne
                [Int64]$wanted.bytes) {
            throw "Runtime file differs for $RunRole/$name."
        }
    }
    if ($isProbe) {
        if ($null -ne $environment.pcg_probe_sha256 -or
            $null -ne $environment.numpy_tree_manifest_sha256 -or
            $null -ne $environment.numpy_tree_validation_passed) {
            throw 'Probe start record includes forbidden post-probe evidence.'
        }
    }
    elseif ([string]$environment.pcg_probe_sha256 -cne
            [string]$Runtime.expected_pcg_probe_sha256 -or
        [string]$environment.numpy_tree_manifest_sha256 -cne
            [string]$Runtime.numpy_manifest_sha256 -or
        $environment.numpy_tree_validation_passed -isnot [System.Boolean] -or
        [bool]$environment.numpy_tree_validation_passed -ne $true) {
        throw "Main NumPy/PCG start evidence differs for $RunRole."
    }
}


function Stop-H10AJobExact {
    param([IntPtr]$JobHandle,[System.Diagnostics.Process]$Process,[string]$Label)
    [H10A.NativeJob]::Terminate($JobHandle, [uint32]3758096641)
    if (-not $Process.WaitForExit(10000)) {
        throw "Job-root termination timed out for $Label."
    }
    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    do {
        $active = [uint32][H10A.NativeJob]::ActiveProcesses($JobHandle)
        if ($active -eq 0) { return }
        if ([DateTime]::UtcNow -ge $deadline) {
            throw "Job $Label retains $active owned processes."
        }
        Start-Sleep -Milliseconds 100
    } while ($true)
}

function Wait-H10AJobEmpty {
    param([IntPtr]$JobHandle,[int]$TimeoutMilliseconds = 10000)
    $deadline = [DateTime]::UtcNow.AddMilliseconds($TimeoutMilliseconds)
    do {
        $active = [uint32][H10A.NativeJob]::ActiveProcesses($JobHandle)
        if ($active -eq 0) { return $true }
        if ([DateTime]::UtcNow -ge $deadline) { return $false }
        Start-Sleep -Milliseconds 100
    } while ($true)
}

function Release-ResourceInnerLock {
    param(
        $NormalReleasePath,$ResourceReleasePath,$Action,$RunRole,$LaunchId,
        [int]$ProcessPid,$AuthorizationPath,$Token
    )
    if (Test-Path -LiteralPath $NormalReleasePath -PathType Leaf) {
        if (Test-Path -LiteralPath $innerLock) {
            throw 'Resource child exposed both live and released inner locks.'
        }
        Assert-InnerLockOwner $NormalReleasePath $Action $RunRole $LaunchId $ProcessPid $AuthorizationPath $Token
        return Get-FileRecord $NormalReleasePath
    }
    if (-not (Test-Path -LiteralPath $innerLock -PathType Leaf)) {
        throw 'Resource child inner lock and normal release are both missing.'
    }
    Assert-InnerLockOwner $innerLock $Action $RunRole $LaunchId $ProcessPid $AuthorizationPath $Token
    Move-ExclusiveFileWithRetry $innerLock $ResourceReleasePath
    Assert-InnerLockOwner $ResourceReleasePath $Action $RunRole $LaunchId $ProcessPid $AuthorizationPath $Token
    return Get-FileRecord $ResourceReleasePath
}

function Start-H10AChild {
    param(
        [string]$SubjectKind,[string]$SubjectPath,[string]$Action,[string]$RunRole,
        [string]$OutputId,[string]$OutputDirectory,$Runtime,[string]$LaunchId,
        [string]$LaunchDirectory,$ExtraAuthorization
    )
    Assert-FixedHashes $Runtime
    $authorizedOutput = Assert-PathUnderH10Root $OutputDirectory
    if (-not [string]::Equals(
        $authorizedOutput, [System.IO.Path]::GetFullPath($OutputDirectory),
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Output path normalization differs for $RunRole."
    }
    $script:authorizedOutputDirectories += [ordered]@{
        run_role = $RunRole
        subject_kind = $SubjectKind
        output_directory = $authorizedOutput
    }
    if (Test-Path -LiteralPath $innerLock) { throw "Inner lock exists before $RunRole." }
    $token = [Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N')
    $authPath = Join-Path $LaunchDirectory ($RunRole + '_authorization.json')
    $startPath = Join-Path $LaunchDirectory ($RunRole + '_process_start.json')
    $ackPath = Join-Path $LaunchDirectory ($RunRole + '_process_ack.json')
    $stdoutPath = Join-Path $LaunchDirectory ($RunRole + '_stdout.log')
    $stderrPath = Join-Path $LaunchDirectory ($RunRole + '_stderr.log')
    $ledgerPath = Join-Path $LaunchDirectory ($RunRole + '_async_errors.jsonl')
    $releasePath = Join-Path $LaunchDirectory ($RunRole + '_inner_lock_released.json')
    $resourceReleasePath = Join-Path $LaunchDirectory ($RunRole + '_inner_lock_resource_released.json')
    $failureLockEvidencePath = Join-Path $LaunchDirectory ($RunRole + '_inner_lock_failure_evidence.json')
    $cutoffPath = Join-Path $LaunchDirectory ($RunRole + '_resource_cutoff.json')
    foreach ($path in @(
        $authPath,$startPath,$ackPath,$stdoutPath,$stderrPath,$ledgerPath,
        $releasePath,$resourceReleasePath,$failureLockEvidencePath,$cutoffPath
    )) {
        if (Test-Path -LiteralPath $path) { throw "Child artifact exists: $path" }
    }
    New-ExclusiveEmptyFile $ledgerPath
    $runtimeFiles = Get-RuntimeFileRecords
    $authorization = [ordered]@{
        schema_version = 'h10a_launcher_authorization.v1'
        action = $Action
        run_role = $RunRole
        output_id = $OutputId
        output_directory = $OutputDirectory
        subject_kind = $SubjectKind
        subject_path = $SubjectPath
        subject_sha256 = Get-Sha256 $SubjectPath
        synthetic_mode = [bool](-not $isReal)
        probe_mode = [bool]$isProbe
        launch_id = $LaunchId
        launcher_pid = [int]$PID
        token = $token
        token_sha256 = Get-StringSha256 $token
        authorization_path = $authPath
        launch_directory = $LaunchDirectory
        outer_lock = $outerLock
        inner_lock = $innerLock
        inner_lock_release_path = $releasePath
        resource_inner_lock_release_path = $resourceReleasePath
        async_error_ledger = $ledgerPath
        process_start_path = $startPath
        process_ack_path = $ackPath
        protocol_path = $protocol
        protocol_sha256 = [string]$Runtime.protocol_sha256
        launcher_path = $launcher
        launcher_sha256 = [string]$Runtime.launcher_sha256
        active_lock_path = $activeLock
        active_lock_sha256 = [string]$Runtime.active_lock_sha256
        base_interpreter = $baseInterpreter
        base_interpreter_sha256 = [string]$Runtime.base_interpreter_sha256
        venv_launcher = $venvLauncher
        venv_launcher_sha256 = [string]$Runtime.venv_launcher_sha256
        venv_config = $venvConfig
        venv_config_sha256 = [string]$Runtime.venv_config_sha256
        synthetic_generator_path = if ($isProbe) { $null } else { $syntheticGenerator }
        synthetic_generator_sha256 = if ($isProbe) { $null } else { [string]$Runtime.synthetic_generator_sha256 }
        synthetic_fixture_manifest_path = if ($isProbe) { $null } else { $syntheticFixtureManifest }
        synthetic_fixture_manifest_sha256 = if ($isProbe) { $null } else { [string]$Runtime.synthetic_fixture_manifest_sha256 }
        runtime_files = $runtimeFiles
        runtime_hashes = $Runtime
        expected_pcg_probe_sha256 = if ($isProbe) { $null } else { [string]$Runtime.expected_pcg_probe_sha256 }
        pcg_probe_digest_sha256 = if ($isProbe) { $null } else { [string]$Runtime.expected_pcg_probe_sha256 }
        numpy_manifest_path = if ($isProbe) { $null } else { $numpyManifest }
        numpy_manifest_sha256 = if ($isProbe) { $null } else { [string]$Runtime.numpy_manifest_sha256 }
        immutable_input_sha256 = if ($isReal) { $expectedInputHashes } else { [ordered]@{} }
        immutable_input_paths = if ($isReal) { $inputPaths } else { [ordered]@{} }
        phase_a_commit = if ($isReal) { $phaseACommit } else { $null }
        label_free_only = $true
        candidate_labels_forbidden = $true
        candidate_suffix_labels_forbidden = $true
        behaviors_tsv_forbidden = $true
        authorized_unix_ns = Get-UnixTimeNs
    }
    foreach ($name in $ExtraAuthorization.Keys) {
        if ($authorization.Contains($name)) { throw "Duplicate authorization key: $name" }
        $authorization[$name] = $ExtraAuthorization[$name]
    }
    Write-ExclusiveJson $authPath $authorization
    $script:activeChildContext = [ordered]@{
        evidence_path = $failureLockEvidencePath
        normal_release_path = $releasePath
        resource_release_path = $resourceReleasePath
        action = $Action
        run_role = $RunRole
        launch_id = $LaunchId
        process_pid = 0
        authorization_path = $authPath
        token = $token
    }
    $arguments = @(
        '-B','-u',('"{0}"' -f $SubjectPath),$Action,
        '--authorization',('"{0}"' -f $authPath),
        '--token',$token,
        '--process-start',('"{0}"' -f $startPath),
        '--process-ack',('"{0}"' -f $ackPath)
    )

    $process = $null
    $job = [IntPtr]::Zero
    $stopwatch = $null
    $record = $null
    $failure = $null
    $cleanup = @()
    $peak = [Int64]0
    $samples = [Int64]0
    $postExit = 'not_attempted'
    $processPid = 0
    $jobAssigned = $false
    $ownedTreeDeathProved = $false
    $safeProcessHandle = $null
    $nativeHandleReferenceAdded = $false
    $nativeHandle = [IntPtr]::Zero
    try {
        $process = Start-Process -FilePath $baseInterpreter -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru
        $script:activeChild = $process
        $processPid = [int]$process.Id
        $script:activeChildContext.process_pid = $processPid
        # Hold an explicit SafeHandle reference through exact exit and the
        # mandatory post-exit native memory-counter query.
        $safeProcessHandle = $process.SafeHandle
        $safeProcessHandle.DangerousAddRef([ref]$nativeHandleReferenceAdded)
        if (-not $nativeHandleReferenceAdded) {
            throw "Could not retain native process handle for $RunRole."
        }
        $nativeHandle = $safeProcessHandle.DangerousGetHandle()
        if ($nativeHandle -eq [IntPtr]::Zero) { throw "Zero native handle for $RunRole." }
        $job = [H10A.NativeJob]::CreateKillOnCloseJob()
        $script:activeJob = $job
        [H10A.NativeJob]::Assign($job,$nativeHandle)
        $jobAssigned = $true

        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        $start = $null
        while ($null -eq $start) {
            if (Test-Path -LiteralPath $startPath -PathType Leaf) {
                try { $start = [System.IO.File]::ReadAllText($startPath) | ConvertFrom-Json }
                catch { $start = $null }
            }
            if ($null -eq $start -and $process.HasExited) {
                throw "Child exited before handshake: $RunRole"
            }
            if ($null -eq $start -and [DateTime]::UtcNow -ge $deadline) {
                throw "Handshake timed out: $RunRole"
            }
            if ($null -eq $start) { Start-Sleep -Milliseconds 50 }
        }
        Assert-StartRecord $start $Action $RunRole $SubjectKind $SubjectPath $OutputId $LaunchId ([int]$process.Id) $authPath $token $Runtime $runtimeFiles
        Assert-InnerLockOwner $innerLock $Action $RunRole $LaunchId ([int]$process.Id) $authPath $token
        if ([uint32][H10A.NativeJob]::ActiveProcesses($job) -ne 1) {
            throw "Job is not single-process at ack barrier: $RunRole"
        }
        $peak = [Int64][H10A.NativeJob]::PeakWorkingSetBytes($nativeHandle)
        if ($peak -le 0) { throw "No positive live peak sample: $RunRole" }
        $samples = 1
        $acknowledgement = [ordered]@{
            mode = 'h10a-child-process-acknowledgement'
            action = $Action
            run_role = $RunRole
            launch_id = $LaunchId
            launcher_pid = [int]$PID
            process_pid = [int]$process.Id
            authorization_sha256 = Get-Sha256 $authPath
            token_sha256 = Get-StringSha256 $token
            subject_sha256 = Get-Sha256 $SubjectPath
            acknowledged_unix_ns = Get-UnixTimeNs
        }
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        Write-ExclusiveJson $ackPath $acknowledgement

        $reason = $null
        $resourceDetectedBeforeExit = $false
        $detectionTicks = $null
        $detectionPeak = $null
        while (-not $process.WaitForExit(100)) {
            $activeSample = [uint32][H10A.NativeJob]::ActiveProcesses($job)
            if ($activeSample -ne 1) {
                if ($process.HasExited) { break }
                throw "Job ceased to be single-process during $RunRole."
            }
            try {
                $sample = [Int64][H10A.NativeJob]::PeakWorkingSetBytes($nativeHandle)
                if ($sample -le 0) { throw 'Nonpositive live peak sample.' }
                $samples++
                if ($sample -gt $peak) { $peak = $sample }
            }
            catch {
                if ($process.HasExited) { break }
                throw
            }
            if ($peak -gt $peakResidentLimitBytes) {
                $reason = 'rss'
                $resourceDetectedBeforeExit = $true
                $detectionTicks = [Int64]$stopwatch.ElapsedTicks
                $detectionPeak = $peak
                break
            }
            if ([Int64]$stopwatch.ElapsedTicks -gt $harnessLimitTicks) {
                $reason = 'timeout'
                $resourceDetectedBeforeExit = $true
                $detectionTicks = [Int64]$stopwatch.ElapsedTicks
                $detectionPeak = $peak
                break
            }
        }
        if ($resourceDetectedBeforeExit) {
            Stop-H10AJobExact $job $process $RunRole
        }
        else {
            $process.WaitForExit()
        }
        $process.WaitForExit()

        # The post-exit peak query is mandatory and uses the retained native
        # handle directly, never a managed cached working-set property.
        $postSample = [Int64][H10A.NativeJob]::PeakWorkingSetBytes($nativeHandle)
        $postExit = 'success'
        if ($postSample -le 0) { throw 'Typed post-exit peak query returned no positive value.' }
        if ($postSample -gt $peak) { $peak = $postSample }
        if (-not (Wait-H10AJobEmpty $job 10000)) {
            Stop-H10AJobExact $job $process ($RunRole + '-orphan')
            throw "Owned process tree survived root exit: $RunRole"
        }
        $ownedTreeDeathProved = $true
        $stopwatch.Stop()
        $elapsedTicks = [Int64]$stopwatch.ElapsedTicks
        if ($peak -le 0 -or $samples -le 0) { throw 'Authoritative peak evidence missing.' }
        if ($null -eq $reason) {
            if ($peak -gt $peakResidentLimitBytes) {
                $reason = 'rss'
                $detectionTicks = $elapsedTicks
                $detectionPeak = $peak
            }
            elseif ($elapsedTicks -gt $harnessLimitTicks) {
                $reason = 'timeout'
                $detectionTicks = $elapsedTicks
                $detectionPeak = $peak
            }
        }
        $active = [uint32][H10A.NativeJob]::ActiveProcesses($job)
        if ($postExit -cne 'success') {
            throw "Mandatory post-exit peak query was not successful: $RunRole"
        }
        $rawExit = $process.ExitCode
        if ($null -eq $rawExit) { throw "Exit code missing: $RunRole" }
        $exitCode = [int]$rawExit
        if ($exitCode -ne 0 -and -not $resourceDetectedBeforeExit) {
            throw "Child exited nonzero without a launcher-authenticated pre-exit resource cutoff: $RunRole"
        }
        if ((Get-Item -LiteralPath $stderrPath).Length -ne 0) { throw "Nonempty stderr: $RunRole" }
        if ((Get-Item -LiteralPath $ledgerPath).Length -ne 0) { throw "Nonempty async ledger: $RunRole" }
        Assert-FixedHashes $Runtime

        $cutoff = $null
        if ($null -ne $reason) {
            $cutoff = [ordered]@{
                schema_version = 'h10a_resource_cutoff.v1'
                status = 'INCONCLUSIVE_RESOURCE_BUDGET'
                action = $Action
                run_role = $RunRole
                process_pid = [int]$process.Id
                reason = $reason
                detected_before_exact_exit = $resourceDetectedBeforeExit
                process_terminated_for_resource = $resourceDetectedBeforeExit
                detection_stopwatch_ticks = [Int64]$detectionTicks
                detection_peak_resident_bytes = [Int64]$detectionPeak
                exit_code_after_job_termination = $exitCode
                final_stopwatch_elapsed_ticks = $elapsedTicks
                stopwatch_frequency = [Int64][System.Diagnostics.Stopwatch]::Frequency
                limit_ticks = $harnessLimitTicks
                final_peak_resident_bytes = $peak
                peak_resident_limit_bytes = $peakResidentLimitBytes
                live_peak_samples = $samples
                post_exit_peak_query = $postExit
                post_exit_peak_query_succeeded = $true
                authorization_sha256 = Get-Sha256 $authPath
                process_start_sha256 = Get-Sha256 $startPath
                process_ack_sha256 = Get-Sha256 $ackPath
                job_active_processes_after_exit = $active
                cutoff_unix_ns = Get-UnixTimeNs
            }
        }

        $common = [ordered]@{
            label = $RunRole
            pid = [int]$process.Id
            exit_code = $exitCode
            launcher_elapsed_ticks = $elapsedTicks
            stopwatch_frequency = [Int64][System.Diagnostics.Stopwatch]::Frequency
            launcher_peak_resident_bytes = $peak
            live_peak_samples = $samples
            post_exit_peak_query = $postExit
            post_exit_peak_query_succeeded = $true
            job_active_processes_after_exit = $active
            authorization = Get-FileRecord $authPath
            process_start = Get-FileRecord $startPath
            process_ack = Get-FileRecord $ackPath
            stdout = Get-FileRecord $stdoutPath
            stderr = Get-FileRecord $stderrPath
            async_error_ledger = Get-FileRecord $ledgerPath
        }
        if ($null -ne $reason) {
            Write-ExclusiveJson $cutoffPath $cutoff
            $common.outcome = 'resource'
            $common.inner_lock_release = Release-ResourceInnerLock `
                $releasePath $resourceReleasePath $Action $RunRole $LaunchId `
                ([int]$process.Id) $authPath $token
            $common.resource_cutoff = Get-FileRecord $cutoffPath
            $common.partial_output_inventory = Get-TreeFileRecords $OutputDirectory
            $record = [pscustomobject]$common
        }
        else {
            if ($exitCode -ne 0) { throw ("Child exited {0}: {1}" -f $exitCode,$RunRole) }
            $summary = Read-LastJsonSummary $stdoutPath
            $expectedSummaryKeys = if ($SubjectKind -ceq 'runner') {
                @(
                    'module_ns','numpy_tree_manifest_sha256',
                    'numpy_tree_validation_passed','output_directory','output_id',
                    'pcg_probe_sha256','peak_resident_bytes','perf_delta_ns',
                    'perf_start_ns','perf_stop_ns','process_pid','result','run_role',
                    'scientific_verdict','status'
                ) | Sort-Object
            }
            else {
                @(
                    'numpy_tree_manifest_sha256','numpy_tree_validation_passed',
                    'output_directory','output_id','peak_resident_bytes',
                    'perf_delta_ns','perf_start_ns','perf_stop_ns','process_pid',
                    'run_role','scientific_payload_sha256','scientific_verdict',
                    'status','verdict','verification_path','verification_sha256'
                ) | Sort-Object
            }
            $actualSummaryKeys = @($summary.PSObject.Properties.Name | Sort-Object)
            if (($actualSummaryKeys -join '|') -cne ($expectedSummaryKeys -join '|')) {
                throw "Summary field inventory differs: $RunRole"
            }
            $summaryProcessPid = Get-H10AJsonInt64 `
                $summary.process_pid ($RunRole + '.summary.process_pid')
            if ($summaryProcessPid -ne [int]$process.Id -or
                [string]$summary.run_role -cne $RunRole -or
                [string]$summary.output_id -cne $OutputId) {
                throw "Summary identity differs: $RunRole"
            }
            if (-not $isProbe -and (
                $summary.numpy_tree_validation_passed -isnot [System.Boolean] -or
                [bool]$summary.numpy_tree_validation_passed -ne $true -or
                [string]$summary.numpy_tree_manifest_sha256 -cne
                    [string]$Runtime.numpy_manifest_sha256
            )) {
                throw "NumPy tree-validation evidence differs: $RunRole"
            }
            if ($SubjectKind -ceq 'verifier') {
                if (Test-Path -LiteralPath $releasePath) {
                    throw 'Verifier attempted to attest its own inner-lock release.'
                }
                Assert-InnerLockOwner $innerLock $Action $RunRole $LaunchId ([int]$process.Id) $authPath $token
                Move-ExclusiveFileWithRetry $innerLock $releasePath
            }
            else {
                if (Test-Path -LiteralPath $innerLock) { throw "Inner lock remains: $RunRole" }
                if (-not (Test-Path -LiteralPath $releasePath -PathType Leaf)) {
                    throw "Release record missing: $RunRole"
                }
            }
            $common.outcome = 'complete'
            $common.summary = $summary
            Assert-InnerLockOwner $releasePath $Action $RunRole $LaunchId ([int]$process.Id) $authPath $token
            $common.inner_lock_release = Get-FileRecord $releasePath
            $record = [pscustomobject]$common
        }
    }
    catch { $failure = $_ }
    finally {
        if ($null -ne $stopwatch -and $stopwatch.IsRunning) { $stopwatch.Stop() }
        if ($job -ne [IntPtr]::Zero) {
            $jobCanClose = $false
            try {
                if ([uint32][H10A.NativeJob]::ActiveProcesses($job) -ne 0) {
                    Stop-H10AJobExact $job $process ($RunRole + '-failure')
                }
                if ([uint32][H10A.NativeJob]::ActiveProcesses($job) -ne 0) {
                    throw "Job still has active processes during cleanup: $RunRole"
                }
                $jobCanClose = $true
                if ($jobAssigned -and $null -ne $process -and $process.HasExited) {
                    $ownedTreeDeathProved = $true
                }
            }
            catch { $cleanup += $_ }
            if ($jobCanClose) {
                try {
                    [H10A.NativeJob]::Close($job)
                    $job = [IntPtr]::Zero
                    $script:activeJob = [IntPtr]::Zero
                }
                catch { $cleanup += $_ }
            }
        }
        if ($null -ne $process -and -not $process.HasExited) {
            try {
                $process.Kill()
                if (-not $process.WaitForExit(10000)) { throw 'Unassigned child survived.' }
            }
            catch { $cleanup += $_ }
        }
        if ($null -ne $process -and $process.HasExited -and $job -eq [IntPtr]::Zero) {
            $script:activeChild = $null
        }
        if (($null -ne $failure -or $cleanup.Count -ne 0) -and
            ($ownedTreeDeathProved -or $job -eq [IntPtr]::Zero) -and
            -not (Test-Path -LiteralPath $failureLockEvidencePath)) {
            try {
                $failureLockEvidence = Write-InvalidInnerLockEvidence `
                    $failureLockEvidencePath $releasePath $resourceReleasePath `
                    $Action $RunRole $LaunchId $processPid $authPath $token `
                    ([bool]$ownedTreeDeathProved)
                $script:childFailureLockEvidenceRecords += $failureLockEvidence
            }
            catch { $cleanup += $_ }
        }
        if ($nativeHandleReferenceAdded -and $null -ne $safeProcessHandle) {
            try {
                $safeProcessHandle.DangerousRelease()
                $nativeHandleReferenceAdded = $false
                $nativeHandle = [IntPtr]::Zero
            }
            catch { $cleanup += $_ }
        }
        if ($null -ne $process -and $job -eq [IntPtr]::Zero) {
            try { $process.Dispose() } catch { $cleanup += $_ }
        }
        if (($null -ne $failure -or $cleanup.Count -ne 0) -and
            $processPid -gt 0 -and
            -not $ownedTreeDeathProved -and
            $null -eq $script:activeChild -and
            $script:activeJob -eq [IntPtr]::Zero) {
            $script:ownedProcessCleanupUnproved = $true
        }
        if ($null -eq $script:activeChild -and $script:activeJob -eq [IntPtr]::Zero) {
            $script:activeChildContext = $null
        }
    }
    if ($null -ne $failure) {
        if ($cleanup.Count) {
            throw (New-H10AAggregateException "Child $RunRole and cleanup failed." $failure $cleanup)
        }
        throw $failure
    }
    if ($cleanup.Count) {
        throw (New-H10AAggregateException "Child $RunRole cleanup failed." $null $cleanup)
    }
    if ($null -eq $record) { throw "Empty child return: $RunRole" }
    return $record
}


function Get-H10ARuntimeEvidence {
    param($Child,[string]$RunRole,[bool]$RequireModule)
    foreach ($name in @('perf_start_ns','perf_stop_ns','perf_delta_ns','peak_resident_bytes')) {
        if ($null -eq $Child.summary.PSObject.Properties[$name]) {
            throw ("Runtime field omitted by {0}: {1}" -f $RunRole,$name)
        }
    }
    $start = Get-H10AJsonInt64 $Child.summary.perf_start_ns ($RunRole + '.perf_start_ns')
    $stop = Get-H10AJsonInt64 $Child.summary.perf_stop_ns ($RunRole + '.perf_stop_ns')
    $delta = Get-H10AJsonInt64 $Child.summary.perf_delta_ns ($RunRole + '.perf_delta_ns')
    $runnerPeak = Get-H10AJsonInt64 $Child.summary.peak_resident_bytes ($RunRole + '.peak_resident_bytes')
    if ($start -lt 0 -or $stop -lt $start -or $delta -ne ($stop-$start) -or $runnerPeak -le 0) {
        throw "Invalid integer runtime evidence: $RunRole"
    }
    $module = $null
    if ($RequireModule) {
        if ($null -eq $Child.summary.PSObject.Properties['module_ns']) {
            throw "module_ns omitted: $RunRole"
        }
        $module = Get-H10AJsonInt64 $Child.summary.module_ns ($RunRole + '.module_ns')
        if ($module -lt 0 -or $module -gt $delta) { throw "Invalid module_ns: $RunRole" }
    }
    $authoritativePeak = [Math]::Max($runnerPeak,[Int64]$Child.launcher_peak_resident_bytes)
    if ($authoritativePeak -gt $peakResidentLimitBytes -or
        [Int64]$Child.launcher_elapsed_ticks -gt $harnessLimitTicks) {
        throw "Normal role bypassed resource cutoff: $RunRole"
    }
    return [pscustomobject][ordered]@{
        perf_start_ns = $start
        perf_stop_ns = $stop
        perf_delta_ns = $delta
        module_ns = $module
        runner_peak_resident_bytes = $runnerPeak
        launcher_elapsed_ticks = [Int64]$Child.launcher_elapsed_ticks
        stopwatch_frequency = [Int64]$Child.stopwatch_frequency
        launcher_peak_resident_bytes = [Int64]$Child.launcher_peak_resident_bytes
        authoritative_peak_resident_bytes = $authoritativePeak
        module_passed = if ($RequireModule) { [bool]($module -le [Int64]30000000000) } else { $null }
    }
}

function Get-ScientificOutputRecords {
    param([string]$Directory)
    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) {
        throw "Output directory missing: $Directory"
    }
    $expected = @($scientificFileNames + 'result.json' | Sort-Object)
    $actual = @(Get-ChildItem -LiteralPath $Directory -Force |
        Select-Object -ExpandProperty Name | Sort-Object)
    if (($actual -join '|') -cne ($expected -join '|')) {
        throw "Output inventory differs from six locked files: $Directory"
    }
    $records = [ordered]@{}
    foreach ($name in $scientificFileNames + 'result.json') {
        $records[$name] = Get-FileRecord (Join-Path $Directory $name)
    }
    return $records
}

function Assert-ScientificReplay {
    param($Primary,$Replay)
    foreach ($name in $scientificFileNames) {
        if ([string]$Primary[$name].sha256 -cne [string]$Replay[$name].sha256 -or
            [Int64]$Primary[$name].bytes -ne [Int64]$Replay[$name].bytes) {
            throw "Replay scientific bytes differ: $name"
        }
    }
}

function Get-TransportBinding {
    param($Child)
    if ([string]$Child.post_exit_peak_query -cne 'success' -or
        $Child.post_exit_peak_query_succeeded -isnot [System.Boolean] -or
        [bool]$Child.post_exit_peak_query_succeeded -ne $true -or
        [Int64]$Child.launcher_elapsed_ticks -lt 0 -or
        [Int64]$Child.launcher_peak_resident_bytes -le 0 -or
        [uint32]$Child.job_active_processes_after_exit -ne 0) {
        throw "Transport evidence is internally inconsistent: $($Child.label)"
    }
    return [ordered]@{
        label = [string]$Child.label
        pid = [int]$Child.pid
        exit_code = [int]$Child.exit_code
        launcher_elapsed_ticks = [Int64]$Child.launcher_elapsed_ticks
        stopwatch_frequency = [Int64]$Child.stopwatch_frequency
        launcher_peak_resident_bytes = [Int64]$Child.launcher_peak_resident_bytes
        live_peak_samples = [Int64]$Child.live_peak_samples
        post_exit_peak_query = [string]$Child.post_exit_peak_query
        post_exit_peak_query_succeeded = $true
        job_active_processes_after_exit = [uint32]$Child.job_active_processes_after_exit
        authorization = $Child.authorization
        process_start = $Child.process_start
        process_ack = $Child.process_ack
        stdout = $Child.stdout
        stderr = $Child.stderr
        async_error_ledger = $Child.async_error_ledger
        inner_lock_release = $Child.inner_lock_release
    }
}

function New-VerificationCrosslink {
    param(
        $Path,$Primary,$Replay,$PrimaryRuntime,$ReplayRuntime,
        $PrimaryOutputs,$ReplayOutputs,$PrimaryDirectory,$ReplayDirectory,$LaunchId
    )
    $payload = [ordered]@{
        schema_version = 'h10a_verification_crosslink.v1'
        launch_id = $LaunchId
        mode = 'h10a-verification-crosslink'
        execution_mode = $Mode
        protocol_sha256 = $expectedProtocolHash
        implementation_lock = Get-FileRecord $activeLock
        primary = [ordered]@{
            role = [string]$Primary.label
            output_directory = $PrimaryDirectory
            transport = Get-TransportBinding $Primary
            runtime = $PrimaryRuntime
            outputs = $PrimaryOutputs
        }
        exact_replay = [ordered]@{
            role = [string]$Replay.label
            output_directory = $ReplayDirectory
            transport = Get-TransportBinding $Replay
            runtime = $ReplayRuntime
            outputs = $ReplayOutputs
        }
        required_scientific_files = $scientificFileNames
        scientific_files_byte_identical = $true
        created_unix_ns = Get-UnixTimeNs
    }
    Write-ExclusiveJson $Path $payload
    return Get-FileRecord $Path
}

function New-ResourceTerminalPayload {
    param($Child,[string[]]$SkippedRoles,$LaunchId,$Runtime)
    return [ordered]@{
        schema_version = 'h10a_resource_terminal.v1'
        status = 'INCONCLUSIVE_RESOURCE_BUDGET'
        mode = $Mode
        launch_id = $LaunchId
        launcher_pid = [int]$PID
        reached_role = [string]$Child.label
        skipped_roles = $SkippedRoles
        resource_child = $Child
        runtime_hashes = $Runtime
        runtime_files = Get-RuntimeFileRecords
        probe_completion = if ($isProbe) { $null } else { Get-FileRecord $probeCompletionMarker }
        authorized_output_inventories = Get-AuthorizedOutputInventories
        retired_stale_outer_lock = $null
        outer_lock_release = $null
        terminal_marker_is_last = $true
    }
}


function New-InvalidTerminalPayload {
    param([AllowNull()]$PrimaryFailure,[object[]]$CleanupFailureList)
    $messages = @()
    if ($null -ne $PrimaryFailure) { $messages += [string]$PrimaryFailure }
    foreach ($item in $CleanupFailureList) { $messages += [string]$item }
    return [ordered]@{
        schema_version = 'h10a_invalid_terminal.v1'
        status = 'INCONCLUSIVE_INVALID_RUN'
        mode = $Mode
        launch_id = $launchId
        launcher_pid = [int]$PID
        errors = $messages
        runtime_hashes = $runtime
        runtime_files = Get-InvalidRuntimeFileEvidence
        launch_artifacts_before_terminal = Get-SafePathInventory $launchDirectory
        authorized_output_inventories = Get-AuthorizedOutputInventories
        root_lock_state = Get-RootLockState
        child_failure_lock_evidence = @($script:childFailureLockEvidenceRecords)
        retired_stale_outer_lock = $lockRetired
        outer_lock_release = $outerReleaseRecord
        all_owned_processes_dead = [bool](
            $null -eq $script:activeChild -and
            $script:activeJob -eq [IntPtr]::Zero -and
            -not $script:ownedProcessCleanupUnproved
        )
        owned_process_cleanup_unproved = [bool]$script:ownedProcessCleanupUnproved
        terminal_marker_is_last = $true
    }
}


$runtime = Get-RuntimeHashes
Assert-FixedHashes $runtime
Assert-ImplementationCommitted
if ($isReal) {
    Assert-ImmutableInputs
    Assert-PreflightAttestation
}

$fixedSuccessMarker = if ($isProbe) {
    $probeCompletionMarker
}
elseif ($isReal) {
    $confirmatoryCompletionMarker
}
else {
    $null
}
if ($null -ne $fixedSuccessMarker -and
    (Test-Path -LiteralPath $fixedSuccessMarker)) {
    throw "Fixed terminal marker exists: $fixedSuccessMarker"
}
[System.IO.Directory]::CreateDirectory($artifactRoot) | Out-Null
$launchId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '_' + [Guid]::NewGuid().ToString('N')
$launchPrefix = if ($isProbe) { 'h10probe_' } elseif ($isSelfTest) { 'h10st_' } else { 'h10_' }
$launchDirectory = Join-Path $artifactRoot (
    $launchPrefix + [Guid]::NewGuid().ToString('N').Substring(0,20)
)
if (Test-Path -LiteralPath $launchDirectory) { throw 'Launch-directory collision.' }
[System.IO.Directory]::CreateDirectory($launchDirectory) | Out-Null
$successMarker = if ($isProbe) {
    $probeCompletionMarker
}
elseif ($isSelfTest) {
    Join-Path $launchDirectory 'selftest_completion.json'
}
else {
    $confirmatoryCompletionMarker
}
$resourceMarker = Join-Path $launchDirectory 'resource_terminal.json'
$invalidMarker = Join-Path $launchDirectory 'invalid_terminal.json'
$outerLockMode = if ($isProbe) {
    'h10a-probe-outer-lock'
}
elseif ($isSelfTest) {
    'h10a-selftest-outer-lock'
}
else {
    'h10a-run-001-outer-lock'
}
foreach ($path in @($resourceMarker,$invalidMarker)) {
    if (Test-Path -LiteralPath $path) { throw "Terminal marker exists: $path" }
}
if ($isSelfTest -and (Test-Path -LiteralPath $successMarker)) {
    throw "Terminal marker exists: $successMarker"
}

$lockStream = $null
$lockRetired = $null
$outerReleaseRecord = $null
$terminalKind = $null
$terminalPayload = $null
$failure = $null
$cleanupFailures = @()
$script:activeChild = $null
$script:activeJob = [IntPtr]::Zero
$script:activeChildContext = $null
$script:authorizedOutputDirectories = @()
$script:childFailureLockEvidenceRecords = @()
$script:ownedProcessCleanupUnproved = $false
$script:lastImmutableInputRecords = $null
try {
    $lock = Open-OuterLock $outerLock $launchDirectory $outerLockMode
    $lockStream = $lock.Stream
    $lockRetired = if ($null -ne $lock.Retired) { Get-FileRecord $lock.Retired } else { $null }
    Write-HeldLockOwner $lockStream ([ordered]@{
        schema_version = 'h10a_outer_lock.v1'
        mode = $outerLockMode
        pid = [int]$PID
        launch_id = $launchId
        launcher_path = $launcher
        runtime = $runtime
        created_unix_ns = Get-UnixTimeNs
    })
    if ($isProbe) {
        $probeOutput = Join-Path $probeRoot 'h10a_pcg_probe'
        if (Test-Path -LiteralPath $probeOutput) { throw 'Fixed probe output exists.' }
        $probe = Start-H10AChild 'runner' $runner 'probe' 'probe' 'h10a_pcg_probe' $probeOutput $runtime $launchId $launchDirectory ([ordered]@{
            publish_numpy_manifest_path = Join-Path $probeOutput 'numpy_package_manifest.jsonl'
        })
        if ($probe.outcome -ceq 'resource') {
            $terminalKind = 'resource'
            $terminalPayload = New-ResourceTerminalPayload $probe @() $launchId $runtime
        }
        else {
            if ([string]$probe.summary.status -cne 'H10A_PROBE_COMPLETE' -or
                [string]$probe.summary.pcg_probe_sha256 -cnotmatch '\A[A-F0-9]{64}\z' -or
                [string]$probe.summary.output_directory -cne $probeOutput -or
                [string]$probe.summary.result -cne (Join-Path $probeOutput 'result.json') -or
                $probe.summary.numpy_tree_validation_passed -isnot [System.Boolean] -or
                [bool]$probe.summary.numpy_tree_validation_passed -ne $true -or
                [string]$probe.summary.numpy_tree_manifest_sha256 -cne
                    (Get-Sha256 (Join-Path $probeOutput 'numpy_package_manifest.jsonl'))) {
                throw 'Probe summary identity differs.'
            }
            $probeRuntime = Get-H10ARuntimeEvidence $probe 'probe' $false
            $wanted = @('numpy_package_manifest.jsonl','result.json') | Sort-Object
            $got = @(Get-ChildItem -LiteralPath $probeOutput -Force |
                Select-Object -ExpandProperty Name | Sort-Object)
            if (($wanted -join '|') -cne ($got -join '|')) { throw 'Probe inventory differs.' }
            $terminalKind = 'success'
            $terminalPayload = [ordered]@{
                schema_version = 'h10a_probe_completion.v1'
                status = 'H10A_PROBE_COMPLETE'
                mode = 'Probe'
                launch_id = $launchId
                launcher_pid = [int]$PID
                pcg_probe_sha256 = [string]$probe.summary.pcg_probe_sha256
                numpy_package_manifest = Get-FileRecord (Join-Path $probeOutput 'numpy_package_manifest.jsonl')
                probe_result = Get-FileRecord (Join-Path $probeOutput 'result.json')
                child = Get-TransportBinding $probe
                runtime = $probeRuntime
                runtime_hashes = $runtime
                runtime_files = Get-RuntimeFileRecords
                retired_stale_outer_lock = $lockRetired
                outer_lock_release = $null
                terminal_marker_is_last = $true
            }
        }
    }
    else {

        $immutableInputRevalidations = @()
        $primaryDirectory = if ($isSelfTest) {
            Join-Path $launchDirectory 'h10a_selftest_primary'
        }
        else {
            Join-Path $resultsRoot 'h10a_run_001'
        }
        $replayDirectory = if ($isSelfTest) {
            Join-Path $launchDirectory 'h10a_selftest_replay'
        }
        else {
            Join-Path $resultsRoot 'h10a_run_001_replay'
        }
        foreach ($directory in @($primaryDirectory,$replayDirectory)) {
            if (Test-Path -LiteralPath $directory) { throw "Role output exists: $directory" }
        }
        $runnerAction = if ($isSelfTest) { 'self-test' } else { 'run' }
        $primaryRole = if ($isSelfTest) { 'selftest_primary' } else { 'primary' }
        $primaryId = if ($isSelfTest) { 'h10a_selftest_primary' } else { 'h10a_run_001' }
        $replayRole = if ($isSelfTest) { 'selftest_replay' } else { 'exact_replay' }
        $replayId = if ($isSelfTest) { 'h10a_selftest_replay' } else { 'h10a_run_001_replay' }
        $fixture = if ($isSelfTest) { $syntheticFixtureManifest } else { $null }

        $primary = Start-H10AChild 'runner' $runner $runnerAction $primaryRole $primaryId $primaryDirectory $runtime $launchId $launchDirectory ([ordered]@{
            synthetic_fixture_manifest = $fixture
            forced_full_path = [bool]$isSelfTest
        })
        if ($isReal) {
            $immutableInputRevalidations += New-ImmutableInputRevalidation `
                $primary $primaryRole $launchId $launchDirectory
        }
        if ($primary.outcome -ceq 'resource') {
            $terminalKind = 'resource'
            $terminalPayload = New-ResourceTerminalPayload $primary @($replayRole,'verifier') $launchId $runtime
        }
        else {
            if ([string]$primary.summary.status -cne 'H10A_RUN_COMPLETE' -or
                [string]$primary.summary.output_directory -cne $primaryDirectory -or
                [string]$primary.summary.result -cne (Join-Path $primaryDirectory 'result.json') -or
                [string]$primary.summary.pcg_probe_sha256 -cne [string]$runtime.expected_pcg_probe_sha256) {
                throw 'Primary summary identity differs.'
            }
            $primaryRuntime = Get-H10ARuntimeEvidence $primary $primaryRole $true
            $primaryOutputs = Get-ScientificOutputRecords $primaryDirectory
            Assert-FixedHashes $runtime

            $replay = Start-H10AChild 'runner' $runner $runnerAction $replayRole $replayId $replayDirectory $runtime $launchId $launchDirectory ([ordered]@{
                synthetic_fixture_manifest = $fixture
                forced_full_path = [bool]$isSelfTest
            })
            if ($isReal) {
                $immutableInputRevalidations += New-ImmutableInputRevalidation `
                    $replay $replayRole $launchId $launchDirectory
            }
            if ($replay.outcome -ceq 'resource') {
                $terminalKind = 'resource'
                $terminalPayload = New-ResourceTerminalPayload $replay @('verifier') $launchId $runtime
                $terminalPayload.completed_primary = [ordered]@{
                    transport = Get-TransportBinding $primary
                    runtime = $primaryRuntime
                    outputs = $primaryOutputs
                }
            }
            else {
                if ([string]$replay.summary.status -cne 'H10A_RUN_COMPLETE' -or
                    [string]$replay.summary.output_directory -cne $replayDirectory -or
                    [string]$replay.summary.result -cne (Join-Path $replayDirectory 'result.json') -or
                    [string]$replay.summary.pcg_probe_sha256 -cne [string]$runtime.expected_pcg_probe_sha256) {
                    throw 'Replay summary identity differs.'
                }
                $replayRuntime = Get-H10ARuntimeEvidence $replay $replayRole $true
                $replayOutputs = Get-ScientificOutputRecords $replayDirectory
                Assert-ScientificReplay $primaryOutputs $replayOutputs
                if ([string]$primary.summary.scientific_verdict -cne
                    [string]$replay.summary.scientific_verdict) {
                    throw 'Primary/replay scientific verdict differs.'
                }
                Assert-FixedHashes $runtime

                $crosslinkPath = Join-Path $launchDirectory 'verification_crosslink.json'
                $crosslink = New-VerificationCrosslink $crosslinkPath $primary $replay $primaryRuntime $replayRuntime $primaryOutputs $replayOutputs $primaryDirectory $replayDirectory $launchId
                $verifierOutput = Join-Path $launchDirectory 'deep_verification'
                $verificationPath = Join-Path $verifierOutput 'verification.json'
                $verifierAction = if ($isSelfTest) { 'self-test' } else { 'verify' }
                $verification = Start-H10AChild 'verifier' $verifier $verifierAction 'verifier' 'deep_verification' $verifierOutput $runtime $launchId $launchDirectory ([ordered]@{
                    verification_path = $verificationPath
                    verification_crosslink = $crosslink
                    primary_directory = $primaryDirectory
                    replay_directory = $replayDirectory
                    primary_output_directory = $primaryDirectory
                    replay_output_directory = $replayDirectory
                })
                if ($isReal) {
                    $immutableInputRevalidations += New-ImmutableInputRevalidation `
                        $verification 'verifier' $launchId $launchDirectory
                }
                if ($verification.outcome -ceq 'resource') {
                    $terminalKind = 'resource'
                    $terminalPayload = New-ResourceTerminalPayload $verification @('success_completion') $launchId $runtime
                    $terminalPayload.completed_primary = [ordered]@{
                        transport = Get-TransportBinding $primary
                        runtime = $primaryRuntime
                        outputs = $primaryOutputs
                    }
                    $terminalPayload.completed_replay = [ordered]@{
                        transport = Get-TransportBinding $replay
                        runtime = $replayRuntime
                        outputs = $replayOutputs
                    }
                    $terminalPayload.verification_crosslink = $crosslink
                }
                else {
                    $verifyStatus = if ($isSelfTest) {
                        'H10A_SELFTEST_VERIFY_COMPLETE'
                    }
                    else {
                        'H10A_VERIFY_COMPLETE'
                    }
                    if ([string]$verification.summary.status -cne $verifyStatus -or
                        [string]$verification.summary.output_directory -cne $verifierOutput -or
                        [string]$verification.summary.verification_path -cne $verificationPath -or
                        -not (Test-Path -LiteralPath $verificationPath -PathType Leaf) -or
                        [string]$verification.summary.verification_sha256 -cne (Get-Sha256 $verificationPath)) {
                        throw 'Verifier summary identity differs.'
                    }
                    $verifierNames = @(Get-ChildItem -LiteralPath $verifierOutput -Force |
                        Select-Object -ExpandProperty Name)
                    if ($verifierNames.Count -ne 1 -or
                        [string]$verifierNames[0] -cne 'verification.json') {
                        throw 'Verifier output inventory differs.'
                    }
                    $verificationRuntime = Get-H10ARuntimeEvidence $verification 'verifier' $false
                    if ([string]$verification.summary.scientific_payload_sha256 -cne
                        [string]$primaryOutputs['scientific_payload.json'].sha256) {
                        throw 'Verifier scientific payload hash differs.'
                    }

                    if ($isSelfTest) {
                        if ([string]$verification.summary.verdict -cne 'PASS_H10A_PREFLIGHT') {
                            throw 'Verifier did not pass synthetic preflight.'
                        }
                        $expectedFinal = 'PASS_H10A_PREFLIGHT'
                    }
                    else {
                        $scientificVerdict = [string]$primary.summary.scientific_verdict
                        if ($scientificVerdict -notin @(
                            'PASS_H10A_RELATION_NULL_FEASIBILITY',
                            'KILL_H10_RELATION_NULL_DIRECTION'
                        )) {
                            throw 'Invalid runner scientific verdict.'
                        }
                        $expectedFinal = if (
                            $scientificVerdict -ceq 'PASS_H10A_RELATION_NULL_FEASIBILITY' -and
                            [bool]$primaryRuntime.module_passed -and
                            [bool]$replayRuntime.module_passed
                        ) {
                            'PASS_H10A_RELATION_NULL_FEASIBILITY'
                        }
                        else {
                            'KILL_H10_RELATION_NULL_DIRECTION'
                        }
                        if ([string]$verification.summary.scientific_verdict -cne $scientificVerdict -or
                            [string]$verification.summary.verdict -cne $expectedFinal) {
                            throw 'Verifier verdict differs from integer-gate recomputation.'
                        }
                    }
                    Assert-FixedHashes $runtime
                    if ($isReal) {
                        Assert-PreflightAttestation
                    }
                    Assert-ImplementationCommitted
                    $terminalKind = 'success'
                    $terminalPayload = [ordered]@{
                        schema_version = if ($isSelfTest) {
                            'h10a_selftest_completion.v1'
                        }
                        else {
                            'h10a_run_001_completion.v1'
                        }
                        status = if ($isSelfTest) {
                            'H10A_SELFTEST_COMPLETE'
                        }
                        else {
                            'H10A_RUN_001_COMPLETE'
                        }
                        mode = $Mode
                        launch_id = $launchId
                        launcher_pid = [int]$PID
                        protocol_sha256 = $expectedProtocolHash
                        implementation_lock = Get-FileRecord $activeLock
                        probe_completion = Get-FileRecord $probeCompletionMarker
                        runtime_hashes = $runtime
                        runtime_files = Get-RuntimeFileRecords
                        pcg_probe_sha256 = [string]$runtime.expected_pcg_probe_sha256
                        scientific_payload_sha256 = [string]$primaryOutputs['scientific_payload.json'].sha256
                        primary = [ordered]@{
                            transport = Get-TransportBinding $primary
                            runtime = $primaryRuntime
                            outputs = $primaryOutputs
                        }
                        exact_replay = [ordered]@{
                            transport = Get-TransportBinding $replay
                            runtime = $replayRuntime
                            outputs = $replayOutputs
                        }
                        verifier = [ordered]@{
                            transport = Get-TransportBinding $verification
                            runtime = $verificationRuntime
                            verification = Get-FileRecord $verificationPath
                        }
                        verification_crosslink = $crosslink
                        decision = [ordered]@{
                            scientific_verdict = if ($isSelfTest) {
                                'SYNTHETIC_NOT_SCIENTIFIC'
                            }
                            else {
                                [string]$primary.summary.scientific_verdict
                            }
                            primary_module_passed = [bool]$primaryRuntime.module_passed
                            replay_module_passed = [bool]$replayRuntime.module_passed
                            verdict = $expectedFinal
                        }
                        execution_contract = [ordered]@{
                            hidden_start_process = $true
                            direct_base_interpreter = $baseInterpreter
                            python_flags = @('-B','-u')
                            numerical_threads = 1
                            cuda_visible_devices = '-1'
                            job_object_tree_containment = $true
                            peak_sample_interval_ms = 100
                            harness_limit_seconds = $harnessLimitSeconds
                            peak_resident_limit_bytes = $peakResidentLimitBytes
                            scientific_files_compared_as_raw_sha256 = $true
                            convert_from_json_scientific_float_roundtrip = $false
                        }
                        retired_stale_outer_lock = $lockRetired
                        outer_lock_release = $null
                        terminal_marker_is_last = $true
                    }
                }
            }
        }
    }
    if ($isReal -and $null -ne $terminalPayload) {
        if ($null -eq $script:lastImmutableInputRecords -or
            $immutableInputRevalidations.Count -eq 0) {
            throw 'Real terminal lacks post-exit immutable-input evidence.'
        }
        $terminalPayload.immutable_input_revalidations =
            @($immutableInputRevalidations)
        $terminalPayload.final_immutable_input_records =
            $script:lastImmutableInputRecords
    }
}
catch {
    $failure = $_
}

finally {
    $outerTreeDeathProved = $false
    $outerChildToDispose = $script:activeChild
    if ($script:activeJob -ne [IntPtr]::Zero) {
        $outerJobCanClose = $false
        try {
            if ([uint32][H10A.NativeJob]::ActiveProcesses($script:activeJob) -ne 0) {
                if ($null -eq $script:activeChild) {
                    throw 'Retained active job has no exact root-process handle.'
                }
                Stop-H10AJobExact $script:activeJob $script:activeChild 'outer-finally'
            }
            if ([uint32][H10A.NativeJob]::ActiveProcesses($script:activeJob) -ne 0) {
                throw 'Retained job remains nonempty after outer cleanup.'
            }
            $outerTreeDeathProved = $true
            $outerJobCanClose = $true
            if ($null -ne $script:activeChild -and $script:activeChild.HasExited) {
                $script:activeChild = $null
            }
        }
        catch { $cleanupFailures += $_ }
        if ($outerJobCanClose) {
            try {
                [H10A.NativeJob]::Close($script:activeJob)
                $script:activeJob = [IntPtr]::Zero
            }
            catch { $cleanupFailures += $_ }
        }
    }
    if ($script:activeJob -eq [IntPtr]::Zero -and
        $null -ne $script:activeChild -and
        -not $script:activeChild.HasExited) {
        try {
            $script:activeChild.Kill()
            if (-not $script:activeChild.WaitForExit(10000)) {
                throw 'Outer cleanup exact child survived.'
            }
            $script:activeChild = $null
        }
        catch { $cleanupFailures += $_ }
    }
    elseif ($script:activeJob -eq [IntPtr]::Zero -and
        $null -ne $script:activeChild -and
        $script:activeChild.HasExited) {
        $script:activeChild = $null
    }
    if ($null -ne $script:activeChildContext) {
        $context = $script:activeChildContext
        if (-not (Test-Path -LiteralPath ([string]$context.evidence_path))) {
            try {
                $outerEvidence = Write-InvalidInnerLockEvidence `
                    ([string]$context.evidence_path) `
                    ([string]$context.normal_release_path) `
                    ([string]$context.resource_release_path) `
                    ([string]$context.action) ([string]$context.run_role) `
                    ([string]$context.launch_id) ([int]$context.process_pid) `
                    ([string]$context.authorization_path) ([string]$context.token) `
                    ([bool]$outerTreeDeathProved)
                $script:childFailureLockEvidenceRecords += $outerEvidence
            }
            catch { $cleanupFailures += $_ }
        }
        if ($null -eq $script:activeChild -and
            $script:activeJob -eq [IntPtr]::Zero) {
            if (-not $outerTreeDeathProved -and [int]$context.process_pid -gt 0) {
                $script:ownedProcessCleanupUnproved = $true
            }
            $script:activeChildContext = $null
        }
    }
    if ($script:activeJob -eq [IntPtr]::Zero -and
        $null -ne $outerChildToDispose -and
        $outerChildToDispose.HasExited) {
        try { $outerChildToDispose.Dispose() }
        catch { $cleanupFailures += $_ }
    }
    if ($null -ne $lockStream) {
        if ($null -ne $script:activeChild -or $script:activeJob -ne [IntPtr]::Zero) {
            $cleanupFailures += [System.InvalidOperationException]::new(
                'Outer lock retained because owned-process cleanup is unproved.'
            )
        }
        else {
            $disposed = $false
            try {
                $lockStream.Dispose()
                $lockStream = $null
                $disposed = $true
            }
            catch { $cleanupFailures += $_ }
            if ($disposed) {
                $releaseName = if ($null -eq $failure -and $cleanupFailures.Count -eq 0) {
                    'outer_lock_released.json'
                }
                else {
                    'outer_lock_failed_' + [Guid]::NewGuid().ToString('N').Substring(0,20) + '.json'
                }
                $releasePath = Join-Path $launchDirectory $releaseName
                try {
                    if (-not (Test-Path -LiteralPath $outerLock -PathType Leaf)) {
                        throw 'Held outer lock disappeared.'
                    }
                    Move-ExclusiveFileWithRetry $outerLock $releasePath
                    $outerReleaseRecord = Get-FileRecord $releasePath
                }
                catch { $cleanupFailures += $_ }
            }
        }
    }
}

if ($null -ne $failure -or $cleanupFailures.Count -ne 0) {
    if ($null -eq $outerReleaseRecord -or $null -ne $lockStream -or
        $null -ne $script:activeChild -or $script:activeJob -ne [IntPtr]::Zero -or
        $script:ownedProcessCleanupUnproved) {
        throw (New-H10AAggregateException `
            'Cannot publish an invalid terminal before exact process death and outer-lock release.' `
            $failure $cleanupFailures)
    }
    $invalidPayload = New-InvalidTerminalPayload $failure $cleanupFailures
    if (Test-Path -LiteralPath $invalidMarker) {
        throw (New-H10AAggregateException 'Invalid terminal already exists.' $failure $cleanupFailures)
    }
    Assert-EmbeddedFileRecords $invalidPayload 'invalid_terminal'
    Write-ExclusiveJson $invalidMarker $invalidPayload
    $invalidPayload | ConvertTo-Json -Depth 50 -Compress
    if ($cleanupFailures.Count -ne 0) {
        throw (New-H10AAggregateException 'H10A invalid run had cleanup failures.' $failure $cleanupFailures)
    }
    throw $failure
}

if ($null -eq $terminalPayload -or $null -eq $outerReleaseRecord -or
    [String]::IsNullOrWhiteSpace([string]$terminalKind)) {
    throw 'H10A reached an empty terminal state.'
}
$terminalPayload.outer_lock_release = $outerReleaseRecord
$terminalPayload.retired_stale_outer_lock = $lockRetired
$terminalMarker = if ($terminalKind -ceq 'resource') { $resourceMarker } else { $successMarker }
if (Test-Path -LiteralPath $terminalMarker) { throw 'Terminal marker appeared early.' }
$terminalPublicationFailure = $null
try {
    Assert-EmbeddedFileRecords $terminalPayload 'terminal'
    Write-ExclusiveJson $terminalMarker $terminalPayload
}
catch { $terminalPublicationFailure = $_ }
if ($null -ne $terminalPublicationFailure) {
    if ((Test-Path -LiteralPath $terminalMarker) -or
        (Test-Path -LiteralPath $invalidMarker)) {
        throw (New-H10AAggregateException `
            'A terminal path appeared during failed terminal publication.' `
            $terminalPublicationFailure @())
    }
    $invalidPayload = New-InvalidTerminalPayload $terminalPublicationFailure @()
    Assert-EmbeddedFileRecords $invalidPayload 'invalid_terminal_after_publication_failure'
    Write-ExclusiveJson $invalidMarker $invalidPayload
    $invalidPayload | ConvertTo-Json -Depth 50 -Compress
    throw $terminalPublicationFailure
}
# No filesystem mutation is permitted after terminal publication.
$terminalPayload | ConvertTo-Json -Depth 50 -Compress
