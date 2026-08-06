param(
    [ValidateSet('Audit', 'Recover')][string]$Mode = 'Audit',
    [string]$ConfirmRecovery = ''
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Set-StrictMode -Version 2.0

$expectedProtocolHash = 'B1D52DE0A454F8B29A1DB4A6E0627EFC6A60E96010730C7D9427276D6D4C11C9'
$expectedRunnerHash = 'F16034E938A2C228887B517831F10DD2E799312D53F4220F4DEBF507A4351D8E'
$expectedLauncherHash = '798861EC6D81386D40C4C90F139FD85E848A978BE7C28EA18A2FECB42549304A'
$expectedLockHash = '7DD125FE3C4895470A67A72C846E62D57D62248181EAFD028B93472CB1004065'
$expectedLaunchName = 'h9_3105834790a84ed2970a'
$expectedLaunchId = '20260806T2101376938001Z_cec7c18e689a4879ab3a305bb8c90ed2'
$expectedLauncherPid = 34104
$expectedPrimaryPid = 4848
$expectedReplayPid = 15780
$expectedVerifierPid = 36088
$expectedScientificHash = '5D06E54AEDADD5ED2260D005C28A60536E1D06AC7A7CF5C5A63E8E45A2D3C1DC'
$expectedManifestHash = '3728557242572C5ADF76A969B0B2B531B080BF1C67BEBD20CBC0713F5B66A67C'
$expectedDeepHash = '6BBFBB8EDDED827382344DA5EEB8C9009AEF7C1925D3B01A3B9B50D6B1B9E83E'
$expectedPhaseACommit = 'b1f247abf3185a2eaec8588b358c488af8f78342'
$expectedLaunchCommit = '639fa43b3c2dd4c4b967f591388d38bf916ec239'
$requiredConfirmation = 'RECOVER_H9A_UNCOMMITTED_CHAIN@' + $expectedLaunchName + ':' + $expectedDeepHash
$expectedLaunchBlobs = [ordered]@{
    'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/code/run_h9a_revkron.py' = 'c03dfb23784676d353fc66f2fd7ec9f149bc58a6'
    'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/code/run_h9a_revkron_safe.ps1' = 'b20ddef0498e107969fb6d3fa7c7c3ed4b882a0a'
    'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/protocol.md' = 'c71f34e2b43cc7aecfe6987a781c476cc5650e6d'
    'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/implementation_lock.md' = '2888191f6fba541ede65a5add8a9ed8413fb9be2'
}
if ($Mode -ceq 'Recover' -and $ConfirmRecovery -cne $requiredConfirmation) {
    throw "Recovery requires -ConfirmRecovery '$requiredConfirmation'."
}
if ($Mode -ceq 'Audit' -and -not [string]::IsNullOrEmpty($ConfirmRecovery)) {
    throw 'Audit mode does not accept a recovery confirmation token.'
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$h9Root = (Resolve-Path -LiteralPath (Join-Path $here '..')).Path
$root = (Resolve-Path -LiteralPath (Join-Path $here '..\..\..\..\..')).Path
$resultsRoot = Join-Path $h9Root 'results'
$launchDirectory = Join-Path $resultsRoot $expectedLaunchName
$primaryDirectory = Join-Path $resultsRoot 'h9a_run_001'
$replayDirectory = Join-Path $resultsRoot 'h9a_run_001_replay'
$normalCompletionMarker = Join-Path $resultsRoot 'h9a_run_001_completion.json'
$completionMarker = Join-Path $resultsRoot 'h9a_run_001_RECOVERED_completion.json'
$outerLock = Join-Path $h9Root 'H9A_RUN_001_LAUNCH.lock'
$innerLock = Join-Path $h9Root 'H9A_RUN_001_INNER.lock'
$recoveryScript = (Resolve-Path -LiteralPath $MyInvocation.MyCommand.Path).Path
$runner = Join-Path $here 'run_h9a_revkron.py'
$launcher = Join-Path $here 'run_h9a_revkron_safe.ps1'
$protocol = Join-Path $h9Root 'protocol.md'
$implementationLock = Join-Path $h9Root 'implementation_lock.md'
$recoveryLockFile = Join-Path $h9Root 'recovery_lock.md'
$venvLauncher = (Resolve-Path -LiteralPath (Join-Path $root '_bestrec_run\.venv\Scripts\python.exe')).Path
$venvConfig = (Resolve-Path -LiteralPath (Join-Path $root '_bestrec_run\.venv\pyvenv.cfg')).Path
$venvHomeLines = @(Get-Content -LiteralPath $venvConfig | Where-Object { $_ -match '^\s*home\s*=' })
if ($venvHomeLines.Count -ne 1) { throw 'Recovery could not resolve one base-interpreter home.' }
$baseInterpreter = (Resolve-Path -LiteralPath (Join-Path (($venvHomeLines[0] -split '=', 2)[1].Trim()) 'python.exe')).Path

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
    phase_a_manifest = Join-Path $root 'experiments\kg_launch_autoresearch\experiments\h6_ranking_consequence\results\coverage_run_002\cohort_manifest.jsonl'
    phase_a_result = Join-Path $root 'experiments\kg_launch_autoresearch\experiments\h6_ranking_consequence\results\coverage_run_002\result.json'
    phase_a_completion = Join-Path $root 'experiments\kg_launch_autoresearch\experiments\h6_ranking_consequence\results\coverage_run_002_completion.json'
}

$expectedArtifacts = [ordered]@{
    'launch/deep_verification.json' = [ordered]@{ bytes = [Int64]875; sha256 = '6BBFBB8EDDED827382344DA5EEB8C9009AEF7C1925D3B01A3B9B50D6B1B9E83E' }
    'launch/exact_replay_async_errors.jsonl' = [ordered]@{ bytes = [Int64]0; sha256 = 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855' }
    'launch/exact_replay_authorization.json' = [ordered]@{ bytes = [Int64]3621; sha256 = '19860947805473841557BA65E436052A6442D85106F6EF76CA78872D749C02ED' }
    'launch/exact_replay_inner_lock_released.json' = [ordered]@{ bytes = [Int64]393; sha256 = 'F8F67CB07446512BC5AFA3EBFC2E75DE1866DDDE99FE58BCF3F057DB6C88F3FF' }
    'launch/exact_replay_process_ack.json' = [ordered]@{ bytes = [Int64]387; sha256 = '900256A08352DB639F29EFAD2F75E35BFB4C1FCDC38657DE8595449D1F38BAF2' }
    'launch/exact_replay_process_start.json' = [ordered]@{ bytes = [Int64]2691; sha256 = 'CA62997E0DA45D5DC346A39547A2D6D0A746E63070667FDC90313990A8FACE81' }
    'launch/exact_replay_stderr.log' = [ordered]@{ bytes = [Int64]0; sha256 = 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855' }
    'launch/exact_replay_stdout.log' = [ordered]@{ bytes = [Int64]1332; sha256 = '2ABE2F7979D1ACAF93394977756CEB4B3ADB0CA1B2D1E3F6AB7498FEAD062121' }
    'launch/outer_fail_1b852251c15e40c88d29.json' = [ordered]@{ bytes = [Int64]927; sha256 = '59B151EF4D986296DA76336141DEB5E973C3F8DFDCF597DBECB43EB8DE239B73' }
    'launch/primary_async_errors.jsonl' = [ordered]@{ bytes = [Int64]0; sha256 = 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855' }
    'launch/primary_authorization.json' = [ordered]@{ bytes = [Int64]3584; sha256 = '9E354617407D5ED643D02895F75DFBC5913B27CC1BDCD7ACE71A890714763314' }
    'launch/primary_inner_lock_released.json' = [ordered]@{ bytes = [Int64]387; sha256 = '2117982C11444DD30C49B3A93FA43D7D709D2AA0D9E7CA17076AA1FC453C4CE8' }
    'launch/primary_process_ack.json' = [ordered]@{ bytes = [Int64]386; sha256 = '2E1BC32EC0C4CA7727D85037F9BCA6913069CCB4256419BC18B11C390500FA3B' }
    'launch/primary_process_start.json' = [ordered]@{ bytes = [Int64]2678; sha256 = '0DFE9F1D8867F1A84CD6289F84999BE4657EEEE70A3C7B4725AA96EA44E5E5B0' }
    'launch/primary_stderr.log' = [ordered]@{ bytes = [Int64]0; sha256 = 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855' }
    'launch/primary_stdout.log' = [ordered]@{ bytes = [Int64]1293; sha256 = '31A47267A2807854FF35F127B8797344B2B39BC06664A3D9936E473C553CA0B1' }
    'launch/verifier_async_errors.jsonl' = [ordered]@{ bytes = [Int64]0; sha256 = 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855' }
    'launch/verifier_authorization.json' = [ordered]@{ bytes = [Int64]3822; sha256 = '02F80B6E081926F9511D1181F0DC350CCD1106FFE1F8049917FED5AE9BEA2F3E' }
    'launch/verifier_process_ack.json' = [ordered]@{ bytes = [Int64]390; sha256 = '1CC59FB7DB6B9F6BB09696DD3683AFD46D434E9A971057F4065E6BC652769CDE' }
    'launch/verifier_process_start.json' = [ordered]@{ bytes = [Int64]2689; sha256 = '4AF7E76FF6537B23CA6EF00D9D4EBC67D71DAA0A2F9B66B4A60EB7DDF10820B1' }
    'launch/verifier_stderr.log' = [ordered]@{ bytes = [Int64]0; sha256 = 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855' }
    'launch/verifier_stdout.log' = [ordered]@{ bytes = [Int64]874; sha256 = 'E17BACE93D09CC2F9635738835A99C6C0433FBDF8C932BC06FBDA5B50E72F322' }
    'primary/result.json' = [ordered]@{ bytes = [Int64]68658; sha256 = 'E155C9FDAA11B5862FBCECFA6977A859BCE11B13B635F3F7AE976F18AF58EEC2' }
    'primary/row_manifest.jsonl' = [ordered]@{ bytes = [Int64]91622274; sha256 = '3728557242572C5ADF76A969B0B2B531B080BF1C67BEBD20CBC0713F5B66A67C' }
    'replay/result.json' = [ordered]@{ bytes = [Int64]68682; sha256 = 'E60102466EF24CB911151EE83761B31E67038F3BA219AD4AF36F2C8CE6EBDE3C' }
    'replay/row_manifest.jsonl' = [ordered]@{ bytes = [Int64]91622274; sha256 = '3728557242572C5ADF76A969B0B2B531B080BF1C67BEBD20CBC0713F5B66A67C' }
}

function Get-UnixTimeNs {
    $epochTicks = [Int64]621355968000000000
    return [Int64](([DateTime]::UtcNow.Ticks - $epochTicks) * 100)
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Get-BytesSha256 {
    param([Parameter(Mandatory = $true)][byte[]]$Bytes)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($Bytes))).Replace('-', '') }
    finally { $algorithm.Dispose() }
}

function Get-StringSha256 {
    param([Parameter(Mandatory = $true)][string]$Value)
    return Get-BytesSha256 -Bytes ([Text.Encoding]::UTF8.GetBytes($Value))
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

function Test-SamePath {
    param([string]$Left, [string]$Right)
    try {
        return [string]::Equals(
            [IO.Path]::GetFullPath($Left),
            [IO.Path]::GetFullPath($Right),
            [StringComparison]::OrdinalIgnoreCase
        )
    }
    catch { return $false }
}

function Assert-ContainedNoReparsePath {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$AllowedRoot,
        [Parameter(Mandatory = $true)][string]$Context,
        [bool]$LeafMayBeMissing = $false
    )
    $trimCharacters = [char[]]@([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $rootFull = [IO.Path]::GetFullPath($AllowedRoot).TrimEnd($trimCharacters)
    $pathFull = [IO.Path]::GetFullPath($Path).TrimEnd($trimCharacters)
    $rootPrefix = $rootFull + [IO.Path]::DirectorySeparatorChar
    if (-not [string]::Equals($pathFull, $rootFull, [StringComparison]::OrdinalIgnoreCase) -and
        -not $pathFull.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "$Context escapes its allowed root."
    }
    $probe = $pathFull
    if (-not (Test-Path -LiteralPath $probe)) {
        if (-not $LeafMayBeMissing) { throw "$Context is missing." }
        $probe = [IO.Path]::GetDirectoryName($probe)
    }
    while (-not [string]::IsNullOrEmpty($probe)) {
        $item = Get-Item -LiteralPath $probe -Force
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "$Context traverses a reparse point: $probe"
        }
        if ([string]::Equals($probe.TrimEnd($trimCharacters), $rootFull, [StringComparison]::OrdinalIgnoreCase)) {
            return
        }
        $parent = [IO.Path]::GetDirectoryName($probe.TrimEnd($trimCharacters))
        if ([string]::IsNullOrEmpty($parent) -or
            [string]::Equals($parent, $probe, [StringComparison]::OrdinalIgnoreCase)) {
            break
        }
        $probe = $parent
    }
    throw "$Context did not terminate at its allowed root."
}

function Assert-RecoveryPathSafety {
    $expectedH9Root = Join-Path $root 'experiments\kg_launch_autoresearch\experiments\h9_revkron_certificate'
    $expectedCode = Join-Path $expectedH9Root 'code'
    if (-not (Test-SamePath $h9Root $expectedH9Root) -or -not (Test-SamePath $here $expectedCode)) {
        throw 'Recovery script is not located under the exact H9A repository path.'
    }
    $repositoryVolume = [IO.Path]::GetPathRoot($root)
    Assert-ContainedNoReparsePath -Path $root -AllowedRoot $repositoryVolume -Context 'repository root ancestry'
    $existingRepositoryPaths = @(
        $root, $h9Root, $here, $resultsRoot, $launchDirectory, $primaryDirectory,
        $replayDirectory, $recoveryScript, $runner, $launcher, $protocol,
        $implementationLock, $recoveryLockFile, $venvLauncher, $venvConfig
    )
    foreach ($path in $inputPaths.Values) { $existingRepositoryPaths += [string]$path }
    foreach ($key in $expectedArtifacts.Keys) { $existingRepositoryPaths += Resolve-ArtifactPath -Key $key }
    foreach ($path in $existingRepositoryPaths) {
        Assert-ContainedNoReparsePath -Path $path -AllowedRoot $root -Context ('repository path ' + $path)
    }
    foreach ($entry in @(Get-ChildItem -LiteralPath $resultsRoot -Force -Recurse)) {
        if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "H9A results contain a reparse point: $($entry.FullName)"
        }
    }
    foreach ($path in @($normalCompletionMarker, $completionMarker, $outerLock, $innerLock)) {
        Assert-ContainedNoReparsePath -Path $path -AllowedRoot $root -Context ('prospective path ' + $path) -LeafMayBeMissing $true
    }
    $baseVolume = [IO.Path]::GetPathRoot($baseInterpreter)
    Assert-ContainedNoReparsePath -Path $baseInterpreter -AllowedRoot $baseVolume -Context 'base interpreter'
}

function Test-ProcessAlive {
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        return -not $process.HasExited
    }
    catch { return $false }
}

function Assert-ExactFields {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string[]]$Fields,
        [Parameter(Mandatory = $true)][string]$Context
    )
    if ($Object -isnot [pscustomobject]) { throw "$Context is not a JSON object." }
    $actual = @($Object.PSObject.Properties.Name | Sort-Object)
    $expected = @($Fields | Sort-Object)
    if (($actual -join '|') -cne ($expected -join '|')) {
        throw "$Context has a non-exact field schema."
    }
}

function Assert-String {
    param($Value, [string]$Context, $Expected = $null, $Pattern = $null)
    if ($Value -isnot [string]) { throw "$Context is not a string." }
    if ($null -ne $Expected -and [string]$Value -cne $Expected) {
        throw "$Context differs from its frozen value."
    }
    if ($null -ne $Pattern -and [string]$Value -cnotmatch $Pattern) {
        throw "$Context has an invalid string form."
    }
}

function Assert-RateFromCounts {
    param($Rate, [Int64]$Numerator, [Int64]$Denominator, [string]$Context)
    if ($Numerator -lt 0 -or $Denominator -le 0 -or $Numerator -gt $Denominator) {
        throw "$Context has invalid count bounds."
    }
    $actualBits = Get-DoubleBits -Value $Rate -Context ($Context + ' persisted')
    $expected = [double]$Numerator / [double]$Denominator
    if ([BitConverter]::Int64BitsToDouble($actualBits) -lt 0.0 -or
        [BitConverter]::Int64BitsToDouble($actualBits) -gt 1.0) {
        throw "$Context is outside [0,1]."
    }
    $expectedBits = [BitConverter]::DoubleToInt64Bits($expected)
    $ulpDelta = [Int64]($actualBits - $expectedBits)
    if ($ulpDelta -lt -1 -or $ulpDelta -gt 1) {
        throw "$Context differs from its count ratio by more than one binary64 ULP."
    }
}

function Assert-JsonEquivalent {
    param($Left, $Right, [string]$Context)
    $leftJson = $Left | ConvertTo-Json -Depth 30 -Compress
    $rightJson = $Right | ConvertTo-Json -Depth 30 -Compress
    if ([string]$leftJson -cne [string]$rightJson) { throw "$Context differs." }
}

function Get-UniqueRawJsonNumber {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Field,
        $ConvertedValue,
        [Parameter(Mandatory = $true)][string]$ExpectedToken,
        [Parameter(Mandatory = $true)][string]$ExpectedRawBits,
        [Parameter(Mandatory = $true)][string]$ExpectedConvertedBits,
        [Parameter(Mandatory = $true)][Int64]$ExpectedConvertedDeltaUlp
    )
    $bytes = [IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 2 -or $bytes[$bytes.Length - 1] -ne 0x0A) {
        throw "Raw runtime source is not one LF-terminated JSON line: $Path"
    }
    $text = [Text.Encoding]::UTF8.GetString($bytes, 0, $bytes.Length - 1)
    $numberPattern = '-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?'
    $pattern = '(?:\A|[,{])"' + [regex]::Escape($Field) + '":(?<number>' + $numberPattern + ')(?=[,}])'
    $matches = [regex]::Matches($text, $pattern, [Text.RegularExpressions.RegexOptions]::CultureInvariant)
    if ($matches.Count -ne 1) { throw "Raw runtime field is not unique in $Path`: $Field" }
    $token = $matches[0].Groups['number'].Value
    if ($token -cne $ExpectedToken) { throw "Raw runtime token differs in $Path`: $Field" }
    $number = [double]::Parse(
        $token,
        [Globalization.NumberStyles]::Float,
        [Globalization.CultureInfo]::InvariantCulture
    )
    if ([double]::IsNaN($number) -or [double]::IsInfinity($number)) {
        throw "Raw runtime token is non-finite in $Path`: $Field"
    }
    $rawBits = [BitConverter]::DoubleToInt64Bits($number)
    $convertedBits = Get-DoubleBits -Value $ConvertedValue -Context ($Path + ':' + $Field + ' ConvertFrom-Json')
    $rawHex = '{0:X16}' -f [UInt64]$rawBits
    $convertedHex = '{0:X16}' -f [UInt64]$convertedBits
    $delta = [Int64]($convertedBits - $rawBits)
    if ($rawHex -cne $ExpectedRawBits -or $convertedHex -cne $ExpectedConvertedBits -or
        $delta -ne $ExpectedConvertedDeltaUlp) {
        throw "Raw/ConvertFrom-Json binary64 evidence differs in $Path`: $Field"
    }
    return [pscustomobject]@{
        token = $token
        parsed_value = $number
        converted_value = [double]$ConvertedValue
        raw_binary64 = $rawHex
        convert_from_json_binary64 = $convertedHex
        convert_from_json_delta_ulp = $delta
    }
}

function Get-RuntimeRawPair {
    param([string]$Path, $RuntimeObject)
    return [pscustomobject]@{
        primary = Get-UniqueRawJsonNumber `
            -Path $Path `
            -Field 'primary_launcher_elapsed_seconds' `
            -ConvertedValue $RuntimeObject.primary_launcher_elapsed_seconds `
            -ExpectedToken '239.2070628' `
            -ExpectedRawBits '406DE6A0422A46FB' `
            -ExpectedConvertedBits '406DE6A0422A46FB' `
            -ExpectedConvertedDeltaUlp 0
        replay = Get-UniqueRawJsonNumber `
            -Path $Path `
            -Field 'replay_launcher_elapsed_seconds' `
            -ConvertedValue $RuntimeObject.replay_launcher_elapsed_seconds `
            -ExpectedToken '238.68075969999998' `
            -ExpectedRawBits '406DD5C8C890FDE9' `
            -ExpectedConvertedBits '406DD5C8C890FDEA' `
            -ExpectedConvertedDeltaUlp 1
    }
}

function Assert-RuntimeRawPairEqual {
    param($Authority, $Candidate, [string]$Context)
    foreach ($role in @('primary', 'replay')) {
        foreach ($field in @(
            'token', 'raw_binary64', 'convert_from_json_binary64', 'convert_from_json_delta_ulp'
        )) {
            if ([string]$Authority.$role.$field -cne [string]$Candidate.$role.$field) {
                throw "$Context raw serialized runtime differs: $role.$field"
            }
        }
    }
}

function Assert-Boolean {
    param($Value, [string]$Context, [bool]$Expected)
    if ($Value -isnot [bool] -or [bool]$Value -ne $Expected) {
        throw "$Context is not the expected Boolean."
    }
}

function Assert-Integer {
    param(
        $Value,
        [string]$Context,
        [Int64]$Minimum = [Int64]::MinValue,
        [Int64]$Maximum = [Int64]::MaxValue
    )
    if (-not ($Value -is [Int32] -or $Value -is [Int64])) {
        throw "$Context is not an integer JSON value."
    }
    $integer = [Int64]$Value
    if ($integer -lt $Minimum -or $integer -gt $Maximum) {
        throw "$Context is outside its allowed integer range."
    }
}

function Get-DoubleBits {
    param($Value, [string]$Context)
    if (-not (
        $Value -is [Decimal] -or $Value -is [Double] -or
        $Value -is [Int32] -or $Value -is [Int64]
    )) {
        throw "$Context is not a JSON number."
    }
    $number = [double]$Value
    if ([double]::IsNaN($number) -or [double]::IsInfinity($number)) {
        throw "$Context is not finite."
    }
    return [BitConverter]::DoubleToInt64Bits($number)
}

function Assert-DoubleEqual {
    param($Left, $Right, [string]$Context)
    if ((Get-DoubleBits -Value $Left -Context ($Context + ' left')) -ne
        (Get-DoubleBits -Value $Right -Context ($Context + ' right'))) {
        throw "$Context differs after serialized binary64 recovery."
    }
}

function Read-ExactSingleLineJson {
    param([Parameter(Mandatory = $true)][string]$Path, [string]$Context)
    $bytes = [IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 3 -or
        ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) -or
        $bytes[$bytes.Length - 1] -ne 0x0A) {
        throw "$Context is not BOM-free UTF-8 JSON plus one LF."
    }
    $lfCount = 0
    foreach ($value in $bytes) {
        if ($value -eq 0x0D) { throw "$Context contains a carriage return." }
        if ($value -eq 0x0A) { $lfCount++ }
    }
    if ($lfCount -ne 1) { throw "$Context is not exactly one JSON line." }
    $text = [Text.Encoding]::UTF8.GetString($bytes, 0, $bytes.Length - 1)
    try { return $text | ConvertFrom-Json }
    catch { throw "$Context is not valid JSON: $($_.Exception.Message)" }
}

function Write-ExclusiveJson {
    param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)]$Value)
    $fullPath = [IO.Path]::GetFullPath($Path)
    $directory = [IO.Path]::GetDirectoryName($fullPath)
    if (-not [IO.Directory]::Exists($directory) -or [IO.File]::Exists($fullPath)) {
        throw "Refusing missing-directory or overwrite publication: $fullPath"
    }
    $temporary = Join-Path $directory ('.p' + [Guid]::NewGuid().ToString('N').Substring(0, 20))
    $stream = $null
    try {
        $stream = [IO.File]::Open(
            $temporary, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None
        )
        $json = ($Value | ConvertTo-Json -Depth 60 -Compress) + "`n"
        $bytes = (New-Object Text.UTF8Encoding($false)).GetBytes($json)
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
        $stream.Dispose()
        $stream = $null
        [IO.File]::Move($temporary, $fullPath)
    }
    finally {
        if ($null -ne $stream) { $stream.Dispose() }
        if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
    }
}

function Move-ExclusiveFile {
    param([Parameter(Mandatory = $true)][string]$Source, [Parameter(Mandatory = $true)][string]$Destination)
    if (-not [IO.File]::Exists($Source) -or [IO.File]::Exists($Destination)) {
        throw 'Recovery-lock move source/destination state is invalid.'
    }
    [IO.File]::Move($Source, $Destination)
}

function Resolve-ArtifactPath {
    param([Parameter(Mandatory = $true)][string]$Key)
    $parts = $Key -split '/', 2
    if ($parts.Count -ne 2) { throw "Invalid frozen artifact key: $Key" }
    $base = switch ($parts[0]) {
        'launch' { $launchDirectory }
        'primary' { $primaryDirectory }
        'replay' { $replayDirectory }
        default { throw "Invalid frozen artifact prefix: $Key" }
    }
    return Join-Path $base $parts[1]
}

function Assert-FrozenArtifacts {
    $records = [ordered]@{}
    foreach ($key in $expectedArtifacts.Keys) {
        $path = Resolve-ArtifactPath -Key $key
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Frozen recovery artifact is missing: $key"
        }
        $record = Get-FileRecord -Path $path
        if ([Int64]$record.bytes -ne [Int64]$expectedArtifacts[$key].bytes -or
            [string]$record.sha256 -cne [string]$expectedArtifacts[$key].sha256) {
            throw "Frozen recovery artifact bytes/hash differ: $key"
        }
        $records[$key] = $record
    }
    return $records
}

function Assert-RecordsUnchanged {
    param([Parameter(Mandatory = $true)]$Records, [string]$Context)
    foreach ($key in $Records.Keys) {
        $prior = $Records[$key]
        $current = Get-FileRecord -Path ([string]$prior.path)
        if ([string]$current.path -cne [string]$prior.path -or
            [string]$current.sha256 -cne [string]$prior.sha256 -or
            [Int64]$current.bytes -ne [Int64]$prior.bytes) {
            throw "$Context changed after validation: $key"
        }
    }
}

function Assert-FileRecordObject {
    param($Record, [string]$ExpectedPath, [string]$Context)
    Assert-ExactFields -Object $Record -Fields @('path', 'sha256', 'bytes') -Context $Context
    Assert-String -Value $Record.path -Context ($Context + '.path')
    Assert-String -Value $Record.sha256 -Context ($Context + '.sha256') -Pattern '\A[A-F0-9]{64}\z'
    Assert-Integer -Value $Record.bytes -Context ($Context + '.bytes') -Minimum 0
    if (-not (Test-SamePath -Left ([string]$Record.path) -Right $ExpectedPath)) {
        throw "$Context path differs from its exact location."
    }
    $actual = Get-FileRecord -Path $ExpectedPath
    if ([string]$actual.sha256 -cne [string]$Record.sha256 -or
        [Int64]$actual.bytes -ne [Int64]$Record.bytes) {
        throw "$Context does not bind the current file."
    }
}

function Get-ScientificPayloadText {
    param([Parameter(Mandatory = $true)][string]$ResultPath)
    $text = [IO.File]::ReadAllText($ResultPath, [Text.Encoding]::UTF8)
    $marker = '"scientific_payload":'
    $start = $text.IndexOf($marker, [StringComparison]::Ordinal)
    if ($start -lt 0 -or $start -ne $text.LastIndexOf($marker, [StringComparison]::Ordinal)) {
        throw 'Result does not contain exactly one scientific-payload field.'
    }
    $start += $marker.Length
    if ($start -ge $text.Length -or $text[$start] -ne '{') {
        throw 'Scientific payload is not a JSON object.'
    }
    $depth = 0
    $inString = $false
    $escaped = $false
    for ($index = $start; $index -lt $text.Length; $index++) {
        $character = $text[$index]
        if ($inString) {
            if ($escaped) { $escaped = $false; continue }
            if ($character -eq '\') { $escaped = $true; continue }
            if ($character -eq '"') { $inString = $false }
            continue
        }
        if ($character -eq '"') { $inString = $true; continue }
        if ($character -eq '{') { $depth++ }
        elseif ($character -eq '}') {
            $depth--
            if ($depth -eq 0) { return $text.Substring($start, $index - $start + 1) }
            if ($depth -lt 0) { break }
        }
    }
    throw 'Scientific payload JSON object is unterminated.'
}

function Get-LfCount {
    param([Parameter(Mandatory = $true)][string]$Path)
    $stream = [IO.File]::OpenRead($Path)
    $buffer = New-Object byte[] (1024 * 1024)
    $count = [Int64]0
    try {
        while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
            for ($index = 0; $index -lt $read; $index++) {
                if ($buffer[$index] -eq 0x0A) { $count++ }
            }
        }
    }
    finally { $stream.Dispose() }
    return $count
}

function Assert-RecoveryLockFile {
    if (-not (Test-Path -LiteralPath $recoveryLockFile -PathType Leaf)) {
        throw 'Prospective recovery_lock.md is missing.'
    }
    $bytes = [IO.File]::ReadAllBytes($recoveryLockFile)
    if ($bytes.Length -lt 3 -or
        ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)) {
        throw 'recovery_lock.md is empty or has a UTF-8 BOM.'
    }
    $text = [Text.Encoding]::UTF8.GetString($bytes)
    if ($text.Contains("`r")) { throw 'recovery_lock.md must use LF only.' }
    $pattern = '\A# H9A completion recovery lock\n\n' +
        'Recovery-Script-SHA256: `(?<script>[A-F0-9]{64})`\n' +
        'Original-Runner-SHA256: `' + $expectedRunnerHash + '`\n' +
        'Original-Launcher-SHA256: `' + $expectedLauncherHash + '`\n' +
        'Protocol-SHA256: `' + $expectedProtocolHash + '`\n' +
        'Implementation-Lock-SHA256: `' + $expectedLockHash + '`\n' +
        'Original-Launch-Commit: `' + $expectedLaunchCommit + '`\n' +
        'Target-Launch: `' + [regex]::Escape($expectedLaunchName) + '`\n' +
        'Target-Deep-SHA256: `' + $expectedDeepHash + '`\n' +
        'Confirmation-Token: `' + [regex]::Escape($requiredConfirmation) + '`\n\z'
    $match = [regex]::Match($text, $pattern, [Text.RegularExpressions.RegexOptions]::CultureInvariant)
    if (-not $match.Success) { throw 'recovery_lock.md does not have the exact frozen schema/values.' }
    $scriptHash = Get-Sha256 -Path $recoveryScript
    if ($match.Groups['script'].Value -cne $scriptHash) {
        throw 'Recovery script differs from recovery_lock.md.'
    }
    return [pscustomobject]@{
        record = Get-FileRecord -Path $recoveryLockFile
        recovery_script_sha256 = $scriptHash
        confirmation_token_sha256 = Get-StringSha256 -Value $requiredConfirmation
    }
}

function Assert-GitAndInputs {
    $implementationPaths = @(
        'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/code/run_h9a_revkron.py',
        'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/code/run_h9a_revkron_safe.ps1',
        'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/code/recover_h9a_completion_safe.ps1',
        'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/protocol.md',
        'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/implementation_lock.md',
        'experiments/kg_launch_autoresearch/experiments/h9_revkron_certificate/recovery_lock.md',
        '.gitattributes'
    )
    foreach ($path in $implementationPaths) {
        & git -C $root ls-files --error-unmatch -- $path 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Recovery implementation is not committed: $path" }
    }
    & git -C $root diff --quiet -- $implementationPaths
    if ($LASTEXITCODE -ne 0) { throw 'Recovery implementation differs from committed worktree bytes.' }
    & git -C $root diff --cached --quiet -- $implementationPaths
    if ($LASTEXITCODE -ne 0) { throw 'Recovery implementation has staged but uncommitted changes.' }
    $head = (& git -C $root rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $head -cnotmatch '\A[0-9a-f]{40}\z') {
        throw 'Recovery could not bind one Git HEAD.'
    }
    & git -C $root merge-base --is-ancestor $expectedPhaseACommit $head
    if ($LASTEXITCODE -ne 0) { throw 'Recovery HEAD does not descend from frozen H6 Phase A.' }
    & git -C $root cat-file -e ($expectedLaunchCommit + '^{commit}')
    if ($LASTEXITCODE -ne 0) { throw 'Frozen original-launch Git commit is unavailable.' }
    & git -C $root merge-base --is-ancestor $expectedLaunchCommit $head
    if ($LASTEXITCODE -ne 0) { throw 'Recovery HEAD does not descend from the frozen original-launch commit.' }
    foreach ($path in $expectedLaunchBlobs.Keys) {
        $blob = (& git -C $root rev-parse ($expectedLaunchCommit + ':' + $path)).Trim()
        if ($LASTEXITCODE -ne 0 -or $blob -cne [string]$expectedLaunchBlobs[$path]) {
            throw "Original-launch Git tree differs for $path"
        }
    }

    if ((Get-Sha256 -Path $runner) -cne $expectedRunnerHash -or
        (Get-Sha256 -Path $launcher) -cne $expectedLauncherHash -or
        (Get-Sha256 -Path $protocol) -cne $expectedProtocolHash -or
        (Get-Sha256 -Path $implementationLock) -cne $expectedLockHash) {
        throw 'Original H9A implementation bytes differ from the recovered launch.'
    }
    $lockText = [IO.File]::ReadAllText($implementationLock)
    $lockBindings = [ordered]@{
        'Runner-SHA256' = $expectedRunnerHash
        'Launcher-SHA256' = $expectedLauncherHash
        'Protocol-SHA256' = $expectedProtocolHash
    }
    foreach ($name in $lockBindings.Keys) {
        $pattern = '(?m)^' + [regex]::Escape($name) + ': `' + $lockBindings[$name] + '`\r?$'
        if ([regex]::Matches($lockText, $pattern).Count -ne 1) {
            throw "Implementation lock does not uniquely bind $name."
        }
    }
    $inputRecords = [ordered]@{}
    foreach ($name in $expectedInputHashes.Keys) {
        $record = Get-FileRecord -Path $inputPaths[$name]
        if ([string]$record.sha256 -cne [string]$expectedInputHashes[$name]) {
            throw "Immutable H9A input differs: $name"
        }
        $inputRecords[$name] = $record
    }
    if ([Int64]$inputRecords.phase_a_manifest.bytes -ne [Int64]224785295) {
        throw 'Frozen Phase-A manifest byte count differs.'
    }
    return [pscustomobject]@{
        head = $head
        original_launch_commit = $expectedLaunchCommit
        original_launch_blobs = $expectedLaunchBlobs
        phase_a_commit = $expectedPhaseACommit
        implementation_paths = $implementationPaths
        inputs = $inputRecords
        implementation = [ordered]@{
            runner = Get-FileRecord -Path $runner
            launcher = Get-FileRecord -Path $launcher
            protocol = Get-FileRecord -Path $protocol
            implementation_lock = Get-FileRecord -Path $implementationLock
            recovery_script = Get-FileRecord -Path $recoveryScript
            recovery_lock = Get-FileRecord -Path $recoveryLockFile
            base_interpreter = Get-FileRecord -Path $baseInterpreter
            venv_launcher = Get-FileRecord -Path $venvLauncher
            venv_config = Get-FileRecord -Path $venvConfig
        }
    }
}

function Assert-PreRecoveryInventory {
    param([bool]$RecoveryLockHeld = $false)
    if (Test-Path -LiteralPath $normalCompletionMarker) {
        throw 'Normal H9A completion marker already exists; recovery is forbidden.'
    }
    if (Test-Path -LiteralPath $completionMarker) {
        throw 'Recovered H9A completion marker already exists.'
    }
    if (Test-Path -LiteralPath $innerLock) { throw 'H9A inner lock exists; refusing recovery.' }
    if ($RecoveryLockHeld) {
        if (-not (Test-Path -LiteralPath $outerLock -PathType Leaf)) {
            throw 'Held H9A recovery lock disappeared.'
        }
    }
    elseif (Test-Path -LiteralPath $outerLock) {
        throw 'H9A outer/recovery lock exists; refusing recovery.'
    }
    foreach ($directory in @($launchDirectory, $primaryDirectory, $replayDirectory)) {
        if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
            throw "Required recovery directory is missing: $directory"
        }
    }
    $launchExpected = @(
        $expectedArtifacts.Keys | Where-Object { $_ -like 'launch/*' } |
        ForEach-Object { ($_ -split '/', 2)[1] } | Sort-Object
    )
    $launchActual = @(
        Get-ChildItem -LiteralPath $launchDirectory -Force | Sort-Object Name |
        ForEach-Object {
            if (-not $_.PSIsContainer) { $_.Name } else { throw 'Recovered launch contains a directory.' }
        }
    )
    if (($launchActual -join '|') -cne ($launchExpected -join '|')) {
        throw 'Recovered launch inventory differs from the frozen 22-file chain.'
    }
    foreach ($pair in @(
        [pscustomobject]@{ directory = $primaryDirectory; names = @('result.json', 'row_manifest.jsonl') },
        [pscustomobject]@{ directory = $replayDirectory; names = @('result.json', 'row_manifest.jsonl') }
    )) {
        $actual = @(Get-ChildItem -LiteralPath $pair.directory -Force | Sort-Object Name)
        if (@($actual | Where-Object { $_.PSIsContainer }).Count -ne 0 -or
            ((@($actual.Name) -join '|') -cne ((@($pair.names | Sort-Object)) -join '|'))) {
            throw "Fixed result inventory differs: $($pair.directory)"
        }
    }
    $launches = @(Get-ChildItem -LiteralPath $resultsRoot -Directory | Where-Object {
        $_.Name -cmatch '\Ah9_[0-9a-f]{20}\z'
    } | Sort-Object Name)
    $deepCandidates = @($launches | Where-Object {
        Test-Path -LiteralPath (Join-Path $_.FullName 'deep_verification.json') -PathType Leaf
    })
    if ($deepCandidates.Count -ne 1 -or $deepCandidates[0].Name -cne $expectedLaunchName) {
        throw 'There is not exactly one deep uncommitted H9A chain.'
    }
    $priorRecovery = @(Get-ChildItem -LiteralPath $resultsRoot -Recurse -File | Where-Object {
        $_.Name -cmatch '\A(recovery_attestation|recovery_lock_released)_[0-9a-f]{20}\.json\z'
    })
    if ($priorRecovery.Count -ne 0) { throw 'A prior H9A recovery artifact already exists.' }
    return [ordered]@{
        launch_directories = @($launches.Name)
        deep_candidate = $deepCandidates[0].Name
        deep_candidate_count = $deepCandidates.Count
    }
}

function Assert-Authorization {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Action,
        [Parameter(Mandatory = $true)][string]$Role,
        [Parameter(Mandatory = $true)][string]$OutputId
    )
    $path = Join-Path $launchDirectory ($Label + '_authorization.json')
    $authorization = Read-ExactSingleLineJson -Path $path -Context ($Label + ' authorization')
    $commonFields = @(
        'mode', 'action', 'launch_id', 'launcher_pid', 'token', 'token_sha256',
        'runner_sha256', 'protocol_sha256', 'lock_sha256', 'launcher_path',
        'launcher_sha256', 'base_interpreter', 'base_interpreter_sha256',
        'venv_launcher', 'venv_launcher_sha256', 'venv_config', 'venv_config_sha256',
        'authorization_path', 'outer_lock', 'inner_lock', 'launch_directory',
        'async_error_ledger', 'process_start_path', 'process_ack_path', 'phase_a_commit',
        'phase_a_commit_tree_result_sha256', 'immutable_input_sha256', 'label_free_only',
        'candidate_suffix_labels_forbidden', 'authorized_unix_ns', 'output_id', 'run_role'
    )
    $extra = if ($Action -ceq 'run') {
        @('inner_lock_release_path')
    }
    else {
        @(
            'verification_path', 'primary_launcher_elapsed_seconds',
            'replay_launcher_elapsed_seconds', 'primary_peak_resident_bytes',
            'replay_peak_resident_bytes', 'primary_runtime_passed', 'replay_runtime_passed'
        )
    }
    Assert-ExactFields -Object $authorization -Fields @($commonFields + $extra) -Context ($Label + ' authorization')
    Assert-String $authorization.mode ($Label + '.mode') 'h9a-launcher-authorization'
    Assert-String $authorization.action ($Label + '.action') $Action
    Assert-String $authorization.launch_id ($Label + '.launch_id') $expectedLaunchId
    Assert-Integer $authorization.launcher_pid ($Label + '.launcher_pid') 1 ([Int32]::MaxValue)
    if ([int]$authorization.launcher_pid -ne $expectedLauncherPid) { throw "$Label launcher PID differs." }
    Assert-String $authorization.token ($Label + '.token') $null '\A[0-9a-f]{64}\z'
    Assert-String $authorization.token_sha256 ($Label + '.token_sha256') $null '\A[A-F0-9]{64}\z'
    if ((Get-StringSha256 -Value ([string]$authorization.token)) -cne [string]$authorization.token_sha256) {
        throw "$Label token hash differs."
    }
    $hashBindings = [ordered]@{
        runner_sha256 = $expectedRunnerHash
        launcher_sha256 = $expectedLauncherHash
        protocol_sha256 = $expectedProtocolHash
        lock_sha256 = $expectedLockHash
    }
    foreach ($name in $hashBindings.Keys) {
        Assert-String $authorization.$name ($Label + '.' + $name) $hashBindings[$name]
    }
    $pathBindings = [ordered]@{
        launcher_path = $launcher
        base_interpreter = $baseInterpreter
        venv_launcher = $venvLauncher
        venv_config = $venvConfig
        authorization_path = $path
        outer_lock = $outerLock
        inner_lock = $innerLock
        launch_directory = $launchDirectory
        async_error_ledger = Join-Path $launchDirectory ($Label + '_async_errors.jsonl')
        process_start_path = Join-Path $launchDirectory ($Label + '_process_start.json')
        process_ack_path = Join-Path $launchDirectory ($Label + '_process_ack.json')
    }
    foreach ($name in $pathBindings.Keys) {
        Assert-String $authorization.$name ($Label + '.' + $name)
        if (-not (Test-SamePath ([string]$authorization.$name) $pathBindings[$name])) {
            throw "$Label authorization path differs: $name"
        }
    }
    $runtimeHashBindings = [ordered]@{
        base_interpreter_sha256 = '4F461F0C0DE64E82EB54FBCED0FD1D678D79D34EDA38660B07781E2BBA8064D6'
        venv_launcher_sha256 = 'BAD34B1F39DAD6A375E594AAF006FE84CD96A7AE46F6F2FA84C0536003234AC9'
        venv_config_sha256 = 'A59AE8BCAFF3472F99A259F89DFF2BE70AB8674AADEB5B26D574A237A7FF2426'
    }
    foreach ($name in $runtimeHashBindings.Keys) {
        Assert-String $authorization.$name ($Label + '.' + $name) $runtimeHashBindings[$name]
    }
    Assert-String $authorization.phase_a_commit ($Label + '.phase_a_commit') $expectedPhaseACommit
    Assert-String $authorization.phase_a_commit_tree_result_sha256 ($Label + '.phase_a_tree') $expectedInputHashes.phase_a_result
    Assert-ExactFields $authorization.immutable_input_sha256 @($expectedInputHashes.Keys) ($Label + '.inputs')
    foreach ($name in $expectedInputHashes.Keys) {
        Assert-String $authorization.immutable_input_sha256.$name ($Label + '.inputs.' + $name) $expectedInputHashes[$name]
    }
    Assert-Boolean $authorization.label_free_only ($Label + '.label_free_only') $true
    Assert-Boolean $authorization.candidate_suffix_labels_forbidden ($Label + '.labels_forbidden') $true
    Assert-Integer $authorization.authorized_unix_ns ($Label + '.authorized_unix_ns') 1
    Assert-String $authorization.output_id ($Label + '.output_id') $OutputId
    Assert-String $authorization.run_role ($Label + '.run_role') $Role
    if ($Action -ceq 'run') {
        $release = Join-Path $launchDirectory ($Label + '_inner_lock_released.json')
        Assert-String $authorization.inner_lock_release_path ($Label + '.inner_release')
        if (-not (Test-SamePath ([string]$authorization.inner_lock_release_path) $release)) {
            throw "$Label inner-lock release path differs."
        }
    }
    else {
        Assert-String $authorization.verification_path ($Label + '.verification_path')
        if (-not (Test-SamePath ([string]$authorization.verification_path) (Join-Path $launchDirectory 'deep_verification.json'))) {
            throw 'Verifier output path differs.'
        }
        foreach ($field in @('primary_launcher_elapsed_seconds', 'replay_launcher_elapsed_seconds')) {
            $bits = Get-DoubleBits $authorization.$field ('verifier.' + $field)
            if ([BitConverter]::Int64BitsToDouble($bits) -lt 0.0) { throw "Verifier $field is negative." }
        }
        foreach ($field in @('primary_peak_resident_bytes', 'replay_peak_resident_bytes')) {
            Assert-Integer $authorization.$field ('verifier.' + $field) 1
        }
        foreach ($field in @('primary_runtime_passed', 'replay_runtime_passed')) {
            if ($authorization.$field -isnot [bool]) { throw "Verifier $field is not Boolean." }
        }
    }
    return $authorization
}

function Assert-RuntimeFileRecords {
    param($RuntimeFiles, $Authorization, [string]$Label)
    $paths = [ordered]@{
        base_interpreter = $baseInterpreter
        implementation_lock = $implementationLock
        launcher = $launcher
        protocol = $protocol
        runner = $runner
        venv_config = $venvConfig
        venv_launcher = $venvLauncher
    }
    Assert-ExactFields $RuntimeFiles @($paths.Keys) ($Label + '.runtime_files')
    foreach ($name in $paths.Keys) {
        Assert-FileRecordObject $RuntimeFiles.$name $paths[$name] ($Label + '.runtime_files.' + $name)
    }
    $bindings = [ordered]@{
        base_interpreter = 'base_interpreter_sha256'
        implementation_lock = 'lock_sha256'
        launcher = 'launcher_sha256'
        protocol = 'protocol_sha256'
        runner = 'runner_sha256'
        venv_config = 'venv_config_sha256'
        venv_launcher = 'venv_launcher_sha256'
    }
    foreach ($name in $bindings.Keys) {
        if ([string]$RuntimeFiles.$name.sha256 -cne [string]$Authorization.($bindings[$name])) {
            throw "$Label runtime/auth hash differs: $name"
        }
    }
}

function Assert-Handshake {
    param(
        [string]$Label,
        [string]$Action,
        [string]$Role,
        [string]$OutputId,
        [int]$ExpectedPid,
        $Authorization
    )
    $startPath = Join-Path $launchDirectory ($Label + '_process_start.json')
    $ackPath = Join-Path $launchDirectory ($Label + '_process_ack.json')
    $start = Read-ExactSingleLineJson $startPath ($Label + ' process start')
    $ack = Read-ExactSingleLineJson $ackPath ($Label + ' process acknowledgement')
    Assert-ExactFields $start @(
        'action', 'authorization_sha256', 'environment', 'launch_id', 'launcher_pid',
        'mode', 'output_id', 'process_pid', 'run_role', 'runner_sha256', 'token_sha256'
    ) ($Label + '.start')
    $startBindings = [ordered]@{
        mode = 'h9a-child-process-start'
        action = $Action
        launch_id = $expectedLaunchId
        output_id = $OutputId
        run_role = $Role
        runner_sha256 = $expectedRunnerHash
        token_sha256 = [string]$Authorization.token_sha256
        authorization_sha256 = Get-Sha256 -Path ([string]$Authorization.authorization_path)
    }
    foreach ($name in $startBindings.Keys) {
        Assert-String $start.$name ($Label + '.start.' + $name) $startBindings[$name]
    }
    Assert-Integer $start.launcher_pid ($Label + '.start.launcher_pid') 1 ([Int32]::MaxValue)
    Assert-Integer $start.process_pid ($Label + '.start.process_pid') 1 ([Int32]::MaxValue)
    if ([int]$start.launcher_pid -ne $expectedLauncherPid -or [int]$start.process_pid -ne $ExpectedPid) {
        throw "$Label start PID identity differs."
    }
    Assert-ExactFields $start.environment @(
        'cuda_visible_devices', 'main_thread_only', 'python_hash_seed', 'runtime_files',
        'sys_base_executable', 'sys_base_prefix', 'sys_executable', 'sys_prefix', 'thread_bounds'
    ) ($Label + '.environment')
    Assert-String $start.environment.cuda_visible_devices ($Label + '.cuda') '-1'
    Assert-Boolean $start.environment.main_thread_only ($Label + '.main_thread') $true
    Assert-String $start.environment.python_hash_seed ($Label + '.hash_seed') '0'
    $pythonPathBindings = [ordered]@{
        sys_executable = $venvLauncher
        sys_base_executable = $baseInterpreter
        sys_prefix = (Split-Path -Parent (Split-Path -Parent $venvLauncher))
        sys_base_prefix = (Split-Path -Parent $baseInterpreter)
    }
    foreach ($name in $pythonPathBindings.Keys) {
        Assert-String $start.environment.$name ($Label + '.' + $name)
        if (-not (Test-SamePath ([string]$start.environment.$name) $pythonPathBindings[$name])) {
            throw "$Label Python runtime path differs: $name"
        }
    }
    $threadNames = @(
        'BLIS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS',
        'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'
    )
    Assert-ExactFields $start.environment.thread_bounds $threadNames ($Label + '.thread_bounds')
    foreach ($name in $threadNames) { Assert-String $start.environment.thread_bounds.$name ($Label + '.' + $name) '1' }
    Assert-RuntimeFileRecords $start.environment.runtime_files $Authorization ($Label + '.start')

    Assert-ExactFields $ack @(
        'mode', 'action', 'launch_id', 'launcher_pid', 'process_pid',
        'authorization_sha256', 'token_sha256', 'acknowledged_unix_ns'
    ) ($Label + '.ack')
    $ackBindings = [ordered]@{
        mode = 'h9a-child-process-acknowledgement'
        action = $Action
        launch_id = $expectedLaunchId
        token_sha256 = [string]$Authorization.token_sha256
        authorization_sha256 = Get-Sha256 -Path ([string]$Authorization.authorization_path)
    }
    foreach ($name in $ackBindings.Keys) {
        Assert-String $ack.$name ($Label + '.ack.' + $name) $ackBindings[$name]
    }
    Assert-Integer $ack.launcher_pid ($Label + '.ack.launcher_pid') 1 ([Int32]::MaxValue)
    Assert-Integer $ack.process_pid ($Label + '.ack.process_pid') 1 ([Int32]::MaxValue)
    Assert-Integer $ack.acknowledged_unix_ns ($Label + '.ack.time') 1
    if ([int]$ack.launcher_pid -ne $expectedLauncherPid -or [int]$ack.process_pid -ne $ExpectedPid) {
        throw "$Label acknowledgement PID identity differs."
    }
    if (Test-ProcessAlive -ProcessId $ExpectedPid) { throw "$Label original process PID is still alive." }
    return [pscustomobject]@{ start = $start; acknowledgement = $ack }
}

function Assert-InnerRelease {
    param([string]$Label, [string]$Role, [int]$ExpectedPid, $Authorization)
    $path = Join-Path $launchDirectory ($Label + '_inner_lock_released.json')
    $release = Read-ExactSingleLineJson $path ($Label + ' inner-lock release')
    Assert-ExactFields $release @(
        'created_time_ns', 'launch_id', 'launcher_pid', 'mode', 'pid', 'role',
        'runner_sha256', 'schema_version', 'token_sha256'
    ) ($Label + '.inner_release')
    $releaseBindings = [ordered]@{
        schema_version = 'h9a_inner_lock.v1'
        mode = 'h9a-inner-lock'
        launch_id = $expectedLaunchId
        role = $Role
        runner_sha256 = $expectedRunnerHash
        token_sha256 = [string]$Authorization.token_sha256
    }
    foreach ($name in $releaseBindings.Keys) {
        Assert-String $release.$name ($Label + '.release.' + $name) $releaseBindings[$name]
    }
    Assert-Integer $release.pid ($Label + '.release.pid') 1 ([Int32]::MaxValue)
    Assert-Integer $release.launcher_pid ($Label + '.release.launcher_pid') 1 ([Int32]::MaxValue)
    Assert-Integer $release.created_time_ns ($Label + '.release.time') 1
    if ([int]$release.pid -ne $ExpectedPid -or [int]$release.launcher_pid -ne $expectedLauncherPid) {
        throw "$Label inner-lock release PID identity differs."
    }
    return $release
}

function Assert-OuterRelease {
    param($PrimaryAuthorization)
    $path = Resolve-ArtifactPath 'launch/outer_fail_1b852251c15e40c88d29.json'
    $release = Read-ExactSingleLineJson $path 'original outer-lock release'
    Assert-ExactFields $release @('mode', 'pid', 'launch_id', 'launcher_path', 'runtime', 'created_unix_ns') 'outer release'
    Assert-String $release.mode 'outer.mode' 'h9a-run-001-outer-lock'
    Assert-String $release.launch_id 'outer.launch_id' $expectedLaunchId
    Assert-String $release.launcher_path 'outer.launcher_path'
    if (-not (Test-SamePath ([string]$release.launcher_path) $launcher)) { throw 'Outer launcher path differs.' }
    Assert-Integer $release.pid 'outer.pid' 1 ([Int32]::MaxValue)
    Assert-Integer $release.created_unix_ns 'outer.created_unix_ns' 1
    if ([int]$release.pid -ne $expectedLauncherPid) { throw 'Outer launcher PID differs.' }
    Assert-ExactFields $release.runtime @(
        'runner_sha256', 'launcher_sha256', 'protocol_sha256', 'lock_sha256',
        'base_interpreter_sha256', 'venv_launcher_sha256', 'venv_config_sha256'
    ) 'outer.runtime'
    foreach ($field in $release.runtime.PSObject.Properties.Name) {
        Assert-String $release.runtime.$field ('outer.runtime.' + $field) ([string]$PrimaryAuthorization.$field)
    }
    if (Test-ProcessAlive -ProcessId $expectedLauncherPid) { throw 'Original H9A launcher PID is still alive.' }
    return $release
}

function Assert-StringArrayExact {
    param($Value, [string[]]$Expected, [string]$Context)
    if ($Value -isnot [object[]]) { throw "$Context is not a JSON array." }
    $actual = @($Value)
    if ($actual.Count -ne $Expected.Count) { throw "$Context length differs." }
    for ($index = 0; $index -lt $actual.Count; $index++) {
        Assert-String $actual[$index] ($Context + '[' + $index + ']') $Expected[$index]
    }
}

function Assert-ConfigurationReport {
    param($Report, [string]$ExpectedView, [string]$ExpectedGamma, [string]$Context)
    Assert-ExactFields $Report @(
        'certificate', 'direct_one_hyperedge_diagnostic', 'gamma', 'global_cofact_path',
        'guarded_score_vector_change', 'h6_shared_fact_top10_disagreement', 'impressions',
        'nonvacuous_impressions', 'numerical_enclosure', 'resolved_h9_vs_graph_free_top10',
        'resolved_historical_current_top10_change', 'view'
    ) $Context
    Assert-String $Report.view ($Context + '.view') $ExpectedView
    Assert-String $Report.gamma ($Context + '.gamma') $ExpectedGamma
    Assert-Integer $Report.impressions ($Context + '.impressions') 64443 64443
    Assert-Integer $Report.nonvacuous_impressions ($Context + '.nonvacuous') 48422 48422

    foreach ($name in @('guarded_score_vector_change', 'resolved_historical_current_top10_change')) {
        $entry = $Report.$name
        Assert-ExactFields $entry @('count', 'rate') ($Context + '.' + $name)
        Assert-Integer $entry.count ($Context + '.' + $name + '.count') 0 64443
        $denominator = if ($name -ceq 'guarded_score_vector_change') { [Int64]64443 } else { [Int64]48422 }
        Assert-RateFromCounts $entry.rate ([Int64]$entry.count) $denominator ($Context + '.' + $name + '.rate')
    }

    $dependence = $Report.resolved_h9_vs_graph_free_top10
    Assert-ExactFields $dependence @('current_count', 'current_rate', 'historical_count', 'historical_rate') ($Context + '.dependence')
    foreach ($state in @('historical', 'current')) {
        $countField = $state + '_count'
        $rateField = $state + '_rate'
        Assert-Integer $dependence.$countField ($Context + '.dependence.' + $countField) 0 48422
        Assert-RateFromCounts $dependence.$rateField ([Int64]$dependence.$countField) 48422 ($Context + '.dependence.' + $rateField)
    }

    $certificate = $Report.certificate
    Assert-ExactFields $certificate @(
        'certified_historical_current_disagreements', 'count', 'exposed_certified_count',
        'exposed_certified_rate', 'rate', 'uncertainty_exposed_count', 'uncertainty_exposed_rate'
    ) ($Context + '.certificate')
    foreach ($field in @('count', 'uncertainty_exposed_count', 'exposed_certified_count', 'certified_historical_current_disagreements')) {
        Assert-Integer $certificate.$field ($Context + '.certificate.' + $field) 0 48422
    }
    if ([Int64]$certificate.exposed_certified_count -gt [Int64]$certificate.uncertainty_exposed_count) {
        throw "$Context certificate exposed counts are inconsistent."
    }
    Assert-RateFromCounts $certificate.rate ([Int64]$certificate.count) 48422 ($Context + '.certificate.rate')
    Assert-RateFromCounts $certificate.uncertainty_exposed_rate ([Int64]$certificate.uncertainty_exposed_count) 48422 ($Context + '.certificate.exposed_rate')
    Assert-RateFromCounts $certificate.exposed_certified_rate ([Int64]$certificate.exposed_certified_count) ([Int64]$certificate.uncertainty_exposed_count) ($Context + '.certificate.exposed_certified_rate')

    $globalPath = $Report.global_cofact_path
    Assert-ExactFields $globalPath @(
        'current_impressions', 'current_occurrence_rate', 'current_occurrences',
        'historical_impressions', 'historical_occurrence_rate', 'historical_occurrences'
    ) ($Context + '.global_path')
    foreach ($state in @('historical', 'current')) {
        $occurrences = $state + '_occurrences'
        $rate = $state + '_occurrence_rate'
        $impressions = $state + '_impressions'
        Assert-Integer $globalPath.$occurrences ($Context + '.global_path.' + $occurrences) 0 512071
        Assert-Integer $globalPath.$impressions ($Context + '.global_path.' + $impressions) 0 64443
        Assert-RateFromCounts $globalPath.$rate ([Int64]$globalPath.$occurrences) 512071 ($Context + '.global_path.' + $rate)
    }

    $direct = $Report.direct_one_hyperedge_diagnostic
    Assert-ExactFields $direct @('current_positive_occurrences', 'historical_positive_occurrences') ($Context + '.direct')
    Assert-Integer $direct.current_positive_occurrences ($Context + '.direct.current') 0 512071
    Assert-Integer $direct.historical_positive_occurrences ($Context + '.direct.historical') 0 512071

    $h6 = $Report.h6_shared_fact_top10_disagreement
    Assert-ExactFields $h6 @('current_count', 'current_rate', 'historical_count', 'historical_rate') ($Context + '.h6')
    foreach ($state in @('historical', 'current')) {
        $countField = $state + '_count'
        $rateField = $state + '_rate'
        Assert-Integer $h6.$countField ($Context + '.h6.' + $countField) 0 48422
        Assert-RateFromCounts $h6.$rateField ([Int64]$h6.$countField) 48422 ($Context + '.h6.' + $rateField)
    }

    $numerical = $Report.numerical_enclosure
    Assert-ExactFields $numerical @(
        'maximum_audit_center_discrepancy', 'maximum_delta_E',
        'maximum_delta_path', 'maximum_score_parity_error'
    ) ($Context + '.numerical')
    foreach ($field in $numerical.PSObject.Properties.Name) {
        $bits = Get-DoubleBits $numerical.$field ($Context + '.numerical.' + $field)
        $number = [BitConverter]::Int64BitsToDouble($bits)
        if ($number -lt 0.0) { throw "$Context numerical enclosure is negative: $field" }
    }
    return $Report
}

function Get-RecomputedStructuralVerdict {
    param($Payload)
    Assert-ExactFields $Payload @(
        'claim_boundary', 'classification', 'cohort', 'configurations', 'decision',
        'graph_theorem_audit', 'inputs_sha256', 'inverse_cache_audit', 'ordered_anchors',
        'protocol', 'row_manifest', 'schema_version'
    ) 'scientific payload'
    Assert-String $Payload.schema_version 'payload.schema' 'h9a_revkron_scientific_payload.v1'
    Assert-String $Payload.classification 'payload.classification' 'prospective label-blind mechanism and certificate-coverage gate'
    Assert-ExactFields $Payload.protocol @(
        'anchor_count', 'audit_selection', 'confidence_threshold', 'gammas', 'sha256', 'states', 'views'
    ) 'payload.protocol'
    Assert-Integer $Payload.protocol.anchor_count 'payload.protocol.anchor_count' 50 50
    Assert-String $Payload.protocol.audit_selection 'payload.protocol.audit_selection' 'SHA256(H9A-AUDIT|20260807| || impression_id || NUL || row_index)'
    Assert-DoubleEqual $Payload.protocol.confidence_threshold 0.9 'payload.protocol.confidence_threshold'
    Assert-StringArrayExact $Payload.protocol.gammas @('1/1', '1/10', '10/1') 'payload.protocol.gammas'
    Assert-StringArrayExact $Payload.protocol.states @('intersection', 'historical', 'current', 'union') 'payload.protocol.states'
    Assert-StringArrayExact $Payload.protocol.views @('primary_relation_vocabulary', 'metadata_blocklist', 'remove_q30_q22686') 'payload.protocol.views'
    Assert-String $Payload.protocol.sha256 'payload.protocol.sha256' $expectedProtocolHash
    Assert-ExactFields $Payload.inputs_sha256 @($expectedInputHashes.Keys) 'payload.inputs'
    foreach ($name in $expectedInputHashes.Keys) {
        Assert-String $Payload.inputs_sha256.$name ('payload.inputs.' + $name) $expectedInputHashes[$name]
    }
    Assert-ExactFields $Payload.row_manifest @('format', 'rows', 'schema_version', 'sha256') 'payload.row_manifest'
    Assert-String $Payload.row_manifest.format 'payload.row_manifest.format' 'canonical compact JSON plus LF; g follows view-major/gamma order'
    Assert-String $Payload.row_manifest.schema_version 'payload.row_manifest.schema' 'h9a_row_manifest.compact.v1'
    Assert-String $Payload.row_manifest.sha256 'payload.row_manifest.sha256' $expectedManifestHash
    Assert-Integer $Payload.row_manifest.rows 'payload.row_manifest.rows' 64443 64443

    $cohortExpected = [ordered]@{
        audit_rows = [Int64]1024
        candidate_occurrences = [Int64]2422258
        distinct_patterns = [Int64]812
        histories_with_support = [Int64]64443
        impressions = [Int64]64443
        news_rows = [Int64]42416
        nonvacuous_impressions = [Int64]48422
        supported_candidate_occurrences = [Int64]512071
        supported_ge2 = [Int64]44341
        supported_gt10 = [Int64]17436
        supported_news = [Int64]12060
        users = [Int64]43374
    }
    Assert-ExactFields $Payload.cohort @($cohortExpected.Keys) 'payload.cohort'
    foreach ($name in $cohortExpected.Keys) {
        Assert-Integer $Payload.cohort.$name ('payload.cohort.' + $name) $cohortExpected[$name] $cohortExpected[$name]
    }

    if ($Payload.configurations -isnot [object[]]) { throw 'Payload configurations is not a JSON array.' }
    $expectedConfigurations = @(
        [pscustomobject]@{ view = 'primary_relation_vocabulary'; gamma = '1/1' },
        [pscustomobject]@{ view = 'primary_relation_vocabulary'; gamma = '1/10' },
        [pscustomobject]@{ view = 'primary_relation_vocabulary'; gamma = '10/1' },
        [pscustomobject]@{ view = 'metadata_blocklist'; gamma = '1/1' },
        [pscustomobject]@{ view = 'metadata_blocklist'; gamma = '1/10' },
        [pscustomobject]@{ view = 'metadata_blocklist'; gamma = '10/1' },
        [pscustomobject]@{ view = 'remove_q30_q22686'; gamma = '1/1' },
        [pscustomobject]@{ view = 'remove_q30_q22686'; gamma = '1/10' },
        [pscustomobject]@{ view = 'remove_q30_q22686'; gamma = '10/1' }
    )
    $configurations = @($Payload.configurations)
    if ($configurations.Count -ne $expectedConfigurations.Count) { throw 'Payload configuration count differs.' }
    $byKey = [ordered]@{}
    for ($index = 0; $index -lt $configurations.Count; $index++) {
        $expected = $expectedConfigurations[$index]
        $report = Assert-ConfigurationReport $configurations[$index] $expected.view $expected.gamma ('payload.configuration[' + $index + ']')
        $key = $expected.view + '|' + $expected.gamma
        if ($byKey.Contains($key)) { throw 'Payload has a duplicate configuration key.' }
        $byKey[$key] = $report
    }

    $primary = $byKey['primary_relation_vocabulary|1/1']
    $metadata = $byKey['metadata_blocklist|1/1']
    $removed = $byKey['remove_q30_q22686|1/1']
    $supportedPassed = (
        [Int64]$Payload.cohort.supported_gt10 -eq 17436 -and
        [Int64]$Payload.cohort.supported_gt10 -ge 5000 -and
        [Int64]$Payload.cohort.supported_gt10 * 10 -ge [Int64]$Payload.cohort.nonvacuous_impressions
    )
    $revisionPassed = (
        [Int64]$primary.guarded_score_vector_change.count * 5 -ge [Int64]$primary.impressions -and
        [Int64]$primary.resolved_historical_current_top10_change.count * 50 -ge [Int64]$primary.nonvacuous_impressions
    )
    $dependencePassed = (
        [Int64]$primary.resolved_h9_vs_graph_free_top10.historical_count * 20 -ge [Int64]$primary.nonvacuous_impressions -and
        [Int64]$primary.resolved_h9_vs_graph_free_top10.current_count * 20 -ge [Int64]$primary.nonvacuous_impressions
    )
    $globalPassed = (
        [Int64]$primary.global_cofact_path.historical_occurrences * 100 -ge [Int64]$Payload.cohort.supported_candidate_occurrences -and
        [Int64]$primary.global_cofact_path.current_occurrences * 100 -ge [Int64]$Payload.cohort.supported_candidate_occurrences -and
        [Int64]$primary.global_cofact_path.historical_impressions -ge 1000 -and
        [Int64]$primary.global_cofact_path.current_impressions -ge 1000
    )
    $certificatePassed = (
        [Int64]$primary.certificate.count * 5 -ge [Int64]$primary.nonvacuous_impressions -and
        [Int64]$primary.certificate.uncertainty_exposed_count -ge 1000 -and
        [Int64]$primary.certificate.uncertainty_exposed_count * 50 -ge [Int64]$primary.nonvacuous_impressions -and
        [Int64]$primary.certificate.exposed_certified_count * 10 -ge [Int64]$primary.certificate.uncertainty_exposed_count -and
        [Int64]$primary.certificate.certified_historical_current_disagreements -eq 0
    )
    $robustness = @()
    foreach ($report in @($metadata, $removed)) {
        $robustness += [bool](
            [Int64]$report.guarded_score_vector_change.count * 10 -ge [Int64]$report.impressions -and
            [Int64]$report.resolved_historical_current_top10_change.count * 100 -ge [Int64]$report.nonvacuous_impressions -and
            [Int64]$report.certificate.count * 10 -ge [Int64]$report.nonvacuous_impressions -and
            [Int64]$report.resolved_h9_vs_graph_free_top10.historical_count * 40 -ge [Int64]$report.nonvacuous_impressions -and
            [Int64]$report.resolved_h9_vs_graph_free_top10.current_count * 40 -ge [Int64]$report.nonvacuous_impressions
        )
    }
    $fixedReports = @($configurations | Where-Object { $_.gamma -cne '1/1' })
    $fixedPassed = $fixedReports.Count -eq 6
    foreach ($report in $fixedReports) {
        if ([Int64]$report.certificate.certified_historical_current_disagreements -ne 0) { $fixedPassed = $false }
    }

    $expectedGateNames = @(
        'supported_scale', 'primary_revision_sensitivity', 'primary_graph_dependence',
        'primary_global_cofact_paths', 'primary_certificate_utility',
        'robustness_metadata_blocklist', 'robustness_remove_q30_q22686',
        'fixed_gamma_numerical_audit'
    )
    $recomputed = @(
        [bool]$supportedPassed, [bool]$revisionPassed, [bool]$dependencePassed,
        [bool]$globalPassed, [bool]$certificatePassed, [bool]$robustness[0],
        [bool]$robustness[1], [bool]$fixedPassed
    )
    $observed = @(
        [Int64]$Payload.cohort.supported_gt10,
        [pscustomobject][ordered]@{ score = $primary.guarded_score_vector_change; top10 = $primary.resolved_historical_current_top10_change },
        $primary.resolved_h9_vs_graph_free_top10,
        $primary.global_cofact_path,
        $primary.certificate,
        $metadata,
        $removed,
        [pscustomobject][ordered]@{ audited_configurations = [Int64]6 }
    )
    Assert-ExactFields $Payload.decision @('all_structural_gates_passed', 'gates', 'labels_opened', 'verdict') 'payload.decision'
    Assert-Boolean $Payload.decision.labels_opened 'payload.decision.labels_opened' $false
    if ($Payload.decision.all_structural_gates_passed -isnot [bool] -or $Payload.decision.gates -isnot [object[]]) {
        throw 'Payload decision Boolean/gate array types differ.'
    }
    $gates = @($Payload.decision.gates)
    if ($gates.Count -ne $expectedGateNames.Count) { throw 'Payload gate count differs.' }
    for ($index = 0; $index -lt $gates.Count; $index++) {
        $gate = $gates[$index]
        Assert-ExactFields $gate @('name', 'observed', 'passed') ('payload.gate[' + $index + ']')
        Assert-String $gate.name ('payload.gate[' + $index + '].name') $expectedGateNames[$index]
        Assert-Boolean $gate.passed ('payload.gate[' + $index + '].passed') $recomputed[$index]
        if ($index -eq 0) {
            Assert-Integer $gate.observed 'payload.gate[0].observed' 17436 17436
        }
        else {
            Assert-JsonEquivalent $gate.observed $observed[$index] ('payload.gate[' + $index + '].observed')
        }
    }
    $allPassed = -not ($recomputed -contains $false)
    Assert-Boolean $Payload.decision.all_structural_gates_passed 'payload.decision.all_structural_gates_passed' $allPassed
    $verdict = if ($allPassed) { 'ADVANCE_TO_H9B_PROVENANCE_WORLDS' } else { 'KILL_H9_KRON_DIRECTION' }
    Assert-String $Payload.decision.verdict 'payload.decision.verdict' $verdict
    return $verdict
}

function Assert-ResultAndSummary {
    param(
        [string]$Label,
        [string]$Role,
        [string]$OutputId,
        [int]$ExpectedPid,
        [string]$Directory,
        $Authorization,
        $Handshake,
        $InnerRelease
    )
    $resultPath = Join-Path $Directory 'result.json'
    $manifestPath = Join-Path $Directory 'row_manifest.jsonl'
    $result = Read-ExactSingleLineJson $resultPath ($Label + ' result')
    Assert-ExactFields $result @(
        'artifacts', 'decision', 'execution', 'output_id', 'provenance', 'run_role',
        'schema_version', 'scientific_payload', 'scientific_payload_sha256'
    ) ($Label + '.result')
    Assert-String $result.schema_version ($Label + '.result.schema') 'h9a_revkron_result.v1'
    Assert-String $result.output_id ($Label + '.result.output_id') $OutputId
    Assert-String $result.run_role ($Label + '.result.role') $Role
    Assert-String $result.scientific_payload_sha256 ($Label + '.result.scientific_hash') $expectedScientificHash
    $payloadText = Get-ScientificPayloadText -ResultPath $resultPath
    $payloadHash = Get-StringSha256 -Value $payloadText
    if ($payloadHash -cne $expectedScientificHash) { throw "$Label nested scientific payload hash differs." }
    $structuralVerdict = Get-RecomputedStructuralVerdict -Payload $result.scientific_payload

    Assert-ExactFields $result.artifacts @('result', 'row_manifest') ($Label + '.artifacts')
    Assert-String $result.artifacts.result ($Label + '.artifact.result') 'result.json'
    Assert-ExactFields $result.artifacts.row_manifest @('bytes', 'name', 'sha256') ($Label + '.artifact.manifest')
    Assert-String $result.artifacts.row_manifest.name ($Label + '.artifact.manifest.name') 'row_manifest.jsonl'
    Assert-String $result.artifacts.row_manifest.sha256 ($Label + '.artifact.manifest.sha') $expectedManifestHash
    Assert-Integer $result.artifacts.row_manifest.bytes ($Label + '.artifact.manifest.bytes') 91622274 91622274
    if ((Get-Sha256 -Path $manifestPath) -cne $expectedManifestHash -or
        (Get-LfCount -Path $manifestPath) -ne [Int64]64443) {
        throw "$Label row manifest hash/row count differs."
    }

    Assert-ExactFields $result.execution @(
        'elapsed_seconds', 'peak_resident_bytes', 'elapsed_limit_seconds',
        'peak_resident_limit_bytes', 'one_thread', 'gpu_disabled', 'passed'
    ) ($Label + '.execution')
    $elapsed = [BitConverter]::Int64BitsToDouble((Get-DoubleBits $result.execution.elapsed_seconds ($Label + '.elapsed')))
    $elapsedLimit = [BitConverter]::Int64BitsToDouble((Get-DoubleBits $result.execution.elapsed_limit_seconds ($Label + '.elapsed_limit')))
    Assert-DoubleEqual $result.execution.elapsed_limit_seconds 300.0 ($Label + '.elapsed_limit')
    Assert-Integer $result.execution.peak_resident_bytes ($Label + '.peak') 1
    Assert-Integer $result.execution.peak_resident_limit_bytes ($Label + '.peak_limit') 2147483648 2147483648
    Assert-Boolean $result.execution.one_thread ($Label + '.one_thread') $true
    Assert-Boolean $result.execution.gpu_disabled ($Label + '.gpu_disabled') $true
    if ($result.execution.passed -isnot [bool]) { throw "$Label execution passed is not Boolean." }
    $executionPassed = ($elapsed -le $elapsedLimit -and [Int64]$result.execution.peak_resident_bytes -le [Int64]2147483648)
    if ([bool]$result.execution.passed -ne $executionPassed) { throw "$Label execution gate does not recompute." }
    Assert-ExactFields $result.decision @(
        'final_runtime_adjudication', 'labels_opened',
        'prepublication_runtime_diagnostic_passed', 'structural_verdict'
    ) ($Label + '.decision')
    Assert-String $result.decision.final_runtime_adjudication ($Label + '.pending') 'PENDING_LAUNCHER_AND_DEEP_VERIFIER'
    Assert-Boolean $result.decision.labels_opened ($Label + '.labels_opened') $false
    Assert-Boolean $result.decision.prepublication_runtime_diagnostic_passed ($Label + '.prepub_gate') $executionPassed
    Assert-String $result.decision.structural_verdict ($Label + '.structural') $structuralVerdict

    Assert-ExactFields $result.provenance @(
        'async_error_ledger', 'authorization_token_sha256', 'inner_lock',
        'input_sha256_at_start', 'input_sha256_before_publication', 'launch_id',
        'launcher_pid', 'process_pid', 'runtime_files'
    ) ($Label + '.provenance')
    Assert-String $result.provenance.authorization_token_sha256 ($Label + '.provenance.token') ([string]$Authorization.token_sha256)
    Assert-String $result.provenance.launch_id ($Label + '.provenance.launch') $expectedLaunchId
    Assert-Integer $result.provenance.launcher_pid ($Label + '.provenance.launcher_pid') 1 ([Int32]::MaxValue)
    Assert-Integer $result.provenance.process_pid ($Label + '.provenance.process_pid') 1 ([Int32]::MaxValue)
    if ([int]$result.provenance.launcher_pid -ne $expectedLauncherPid -or [int]$result.provenance.process_pid -ne $ExpectedPid) {
        throw "$Label provenance PID identity differs."
    }
    Assert-FileRecordObject $result.provenance.async_error_ledger ([string]$Authorization.async_error_ledger) ($Label + '.provenance.ledger')
    foreach ($field in @('input_sha256_at_start', 'input_sha256_before_publication')) {
        Assert-ExactFields $result.provenance.$field @($expectedInputHashes.Keys) ($Label + '.provenance.' + $field)
        foreach ($name in $expectedInputHashes.Keys) {
            Assert-String $result.provenance.$field.$name ($Label + '.' + $field + '.' + $name) $expectedInputHashes[$name]
        }
    }
    Assert-RuntimeFileRecords $result.provenance.runtime_files $Authorization ($Label + '.provenance')
    Assert-ExactFields $result.provenance.inner_lock @('owner', 'retired_stale_lock') ($Label + '.inner_lock')
    if ($null -ne $result.provenance.inner_lock.retired_stale_lock) { throw "$Label reports a retired stale inner lock." }
    $owner = $result.provenance.inner_lock.owner
    Assert-ExactFields $owner @(
        'created_time_ns', 'launch_id', 'launcher_pid', 'mode', 'pid', 'role',
        'runner_sha256', 'schema_version', 'token_sha256'
    ) ($Label + '.inner_owner')
    foreach ($field in $owner.PSObject.Properties.Name) {
        if ($field -eq 'created_time_ns' -or $field -eq 'pid' -or $field -eq 'launcher_pid') {
            Assert-Integer $owner.$field ($Label + '.inner_owner.' + $field) 1
            if ([Int64]$owner.$field -ne [Int64]$InnerRelease.$field) { throw "$Label inner owner integer differs: $field" }
        }
        else {
            Assert-String $owner.$field ($Label + '.inner_owner.' + $field)
            if ([string]$owner.$field -cne [string]$InnerRelease.$field) { throw "$Label inner owner differs: $field" }
        }
    }

    $summaryPath = Join-Path $launchDirectory ($Label + '_stdout.log')
    $summary = Read-ExactSingleLineJson $summaryPath ($Label + ' stdout summary')
    Assert-ExactFields $summary @(
        'status', 'process_pid', 'output_id', 'run_role', 'output_directory',
        'result', 'row_manifest', 'result_sha256', 'row_manifest_sha256',
        'scientific_payload_sha256', 'structural_verdict', 'elapsed_seconds',
        'peak_resident_bytes', 'runtime_passed', 'verdict', 'inner_lock_release'
    ) ($Label + '.summary')
    $summaryBindings = [ordered]@{
        status = 'H9A_RUN_COMPLETE'
        output_id = $OutputId
        run_role = $Role
        result_sha256 = Get-Sha256 -Path $resultPath
        row_manifest_sha256 = $expectedManifestHash
        scientific_payload_sha256 = $expectedScientificHash
        structural_verdict = $structuralVerdict
    }
    foreach ($name in $summaryBindings.Keys) {
        Assert-String $summary.$name ($Label + '.summary.' + $name) $summaryBindings[$name]
    }
    $summaryPathBindings = [ordered]@{
        output_directory = $Directory
        result = $resultPath
        row_manifest = $manifestPath
    }
    foreach ($name in $summaryPathBindings.Keys) {
        Assert-String $summary.$name ($Label + '.summary.' + $name)
        if (-not (Test-SamePath ([string]$summary.$name) $summaryPathBindings[$name])) { throw "$Label summary path differs." }
    }
    Assert-Integer $summary.process_pid ($Label + '.summary.pid') 1 ([Int32]::MaxValue)
    Assert-Integer $summary.peak_resident_bytes ($Label + '.summary.peak') 1
    $summaryElapsed = [BitConverter]::Int64BitsToDouble((Get-DoubleBits $summary.elapsed_seconds ($Label + '.summary.elapsed')))
    if ($summary.runtime_passed -isnot [bool]) { throw "$Label summary runtime gate is not Boolean." }
    $summaryPassed = ($summaryElapsed -le 300.0 -and [Int64]$summary.peak_resident_bytes -le [Int64]2147483648)
    if ([bool]$summary.runtime_passed -ne $summaryPassed -or [int]$summary.process_pid -ne $ExpectedPid) {
        throw "$Label summary runtime/PID does not recompute."
    }
    $localVerdict = if ($summaryPassed) { $structuralVerdict } else { 'KILL_H9_KRON_DIRECTION' }
    Assert-String $summary.verdict ($Label + '.summary.verdict') $localVerdict
    Assert-FileRecordObject $summary.inner_lock_release ([string]$Authorization.inner_lock_release_path) ($Label + '.summary.inner_release')
    return [pscustomobject]@{
        result = $result
        summary = $summary
        payload_text = $payloadText
        structural_verdict = $structuralVerdict
        manifest_path = $manifestPath
        result_path = $resultPath
    }
}

function Assert-RuntimeGate {
    param($Gate, $VerifierAuthorization, $SerializedAuthority, [string]$Context)
    Assert-ExactFields $Gate @(
        'limit_seconds', 'limit_peak_resident_bytes', 'primary_launcher_elapsed_seconds',
        'replay_launcher_elapsed_seconds', 'primary_peak_resident_bytes',
        'replay_peak_resident_bytes', 'primary_passed', 'replay_passed', 'passed'
    ) $Context
    Assert-DoubleEqual $Gate.limit_seconds 300.0 ($Context + '.limit_seconds')
    Assert-Integer $Gate.limit_peak_resident_bytes ($Context + '.peak_limit') 2147483648 2147483648
    foreach ($field in @('primary_launcher_elapsed_seconds', 'replay_launcher_elapsed_seconds')) {
        Assert-DoubleEqual $Gate.$field $VerifierAuthorization.$field ($Context + '.' + $field)
    }
    foreach ($field in @('primary_peak_resident_bytes', 'replay_peak_resident_bytes')) {
        Assert-Integer $Gate.$field ($Context + '.' + $field) 1
        if ([Int64]$Gate.$field -ne [Int64]$VerifierAuthorization.$field) {
            throw "$Context $field differs from serialized verifier authorization."
        }
    }
    foreach ($field in @('primary_passed', 'replay_passed', 'passed')) {
        if ($Gate.$field -isnot [bool]) { throw "$Context $field is not Boolean." }
    }
    $primaryElapsed = [double]$SerializedAuthority.primary.parsed_value
    $replayElapsed = [double]$SerializedAuthority.replay.parsed_value
    $primaryPassed = ($primaryElapsed -le 300.0 -and [Int64]$VerifierAuthorization.primary_peak_resident_bytes -le [Int64]2147483648)
    $replayPassed = ($replayElapsed -le 300.0 -and [Int64]$VerifierAuthorization.replay_peak_resident_bytes -le [Int64]2147483648)
    $allPassed = $primaryPassed -and $replayPassed
    if ([bool]$VerifierAuthorization.primary_runtime_passed -ne $primaryPassed -or
        [bool]$VerifierAuthorization.replay_runtime_passed -ne $replayPassed -or
        [bool]$Gate.primary_passed -ne $primaryPassed -or
        [bool]$Gate.replay_passed -ne $replayPassed -or
        [bool]$Gate.passed -ne $allPassed) {
        throw "$Context does not recompute from serialized verifier authorization."
    }
    return [pscustomobject]@{
        primary_elapsed_token = [string]$SerializedAuthority.primary.token
        replay_elapsed_token = [string]$SerializedAuthority.replay.token
        primary_elapsed_raw_bits = [string]$SerializedAuthority.primary.raw_binary64
        replay_elapsed_raw_bits = [string]$SerializedAuthority.replay.raw_binary64
        primary_elapsed_convert_from_json_bits = [string]$SerializedAuthority.primary.convert_from_json_binary64
        replay_elapsed_convert_from_json_bits = [string]$SerializedAuthority.replay.convert_from_json_binary64
        primary_convert_from_json_delta_ulp = [Int64]$SerializedAuthority.primary.convert_from_json_delta_ulp
        replay_convert_from_json_delta_ulp = [Int64]$SerializedAuthority.replay.convert_from_json_delta_ulp
        primary_peak_resident_bytes = [Int64]$VerifierAuthorization.primary_peak_resident_bytes
        replay_peak_resident_bytes = [Int64]$VerifierAuthorization.replay_peak_resident_bytes
        primary_passed = $primaryPassed
        replay_passed = $replayPassed
        passed = $allPassed
    }
}

function Assert-DeepVerification {
    param($VerifierAuthorization, [string]$StructuralVerdict)
    $deepPath = Join-Path $launchDirectory 'deep_verification.json'
    $deep = Read-ExactSingleLineJson $deepPath 'deep verification'
    Assert-ExactFields $deep @(
        'all_outward_bounds_recomputed', 'eigendecomposition_rank_parity',
        'independent_clique_assembly', 'output_id', 'primary_replay_exact',
        'process_pid', 'row_manifest_sha256', 'run_role', 'runtime_gate',
        'schema_version', 'scientific_payload_sha256', 'status',
        'structural_verdict', 'verdict'
    ) 'deep verification'
    $deepBindings = [ordered]@{
        schema_version = 'h9a_deep_verification.v1'
        status = 'H9A_DEEP_VERIFY_COMPLETE'
        output_id = 'deep_verification'
        run_role = 'verifier'
        row_manifest_sha256 = $expectedManifestHash
        scientific_payload_sha256 = $expectedScientificHash
        structural_verdict = $StructuralVerdict
    }
    foreach ($name in $deepBindings.Keys) { Assert-String $deep.$name ('deep.' + $name) $deepBindings[$name] }
    foreach ($field in @(
        'all_outward_bounds_recomputed', 'eigendecomposition_rank_parity',
        'independent_clique_assembly', 'primary_replay_exact'
    )) { Assert-Boolean $deep.$field ('deep.' + $field) $true }
    Assert-Integer $deep.process_pid 'deep.process_pid' 1 ([Int32]::MaxValue)
    if ([int]$deep.process_pid -ne $expectedVerifierPid -or (Test-ProcessAlive $expectedVerifierPid)) {
        throw 'Deep-verifier PID is mismatched or live.'
    }
    $authorizationPath = Join-Path $launchDirectory 'verifier_authorization.json'
    $authorizationRawRuntime = Get-RuntimeRawPair -Path $authorizationPath -RuntimeObject $VerifierAuthorization
    $deepRawRuntime = Get-RuntimeRawPair -Path $deepPath -RuntimeObject $deep.runtime_gate
    Assert-RuntimeRawPairEqual $authorizationRawRuntime $deepRawRuntime 'authorization/deep'
    $deepRuntime = Assert-RuntimeGate $deep.runtime_gate $VerifierAuthorization $authorizationRawRuntime 'deep.runtime_gate'
    $expectedFinalVerdict = if ([bool]$deepRuntime.passed) { $StructuralVerdict } else { 'KILL_H9_KRON_DIRECTION' }
    Assert-String $deep.verdict 'deep.verdict' $expectedFinalVerdict

    $summary = Read-ExactSingleLineJson (Join-Path $launchDirectory 'verifier_stdout.log') 'verifier stdout summary'
    Assert-ExactFields $summary @(
        'status', 'output_id', 'run_role', 'process_pid', 'verification_path',
        'verification_sha256', 'scientific_payload_sha256', 'structural_verdict',
        'runtime_gate', 'verdict'
    ) 'verifier summary'
    $verifierSummaryBindings = [ordered]@{
        status = 'H9A_VERIFY_COMPLETE'
        output_id = 'deep_verification'
        run_role = 'verifier'
        verification_sha256 = $expectedDeepHash
        scientific_payload_sha256 = $expectedScientificHash
        structural_verdict = $StructuralVerdict
        verdict = $expectedFinalVerdict
    }
    foreach ($name in $verifierSummaryBindings.Keys) {
        Assert-String $summary.$name ('verifier.summary.' + $name) $verifierSummaryBindings[$name]
    }
    Assert-String $summary.verification_path 'verifier.summary.path'
    if (-not (Test-SamePath ([string]$summary.verification_path) $deepPath)) { throw 'Verifier summary path differs.' }
    Assert-Integer $summary.process_pid 'verifier.summary.pid' 1 ([Int32]::MaxValue)
    if ([int]$summary.process_pid -ne $expectedVerifierPid) { throw 'Verifier summary PID differs.' }
    $summaryPath = Join-Path $launchDirectory 'verifier_stdout.log'
    $summaryRawRuntime = Get-RuntimeRawPair -Path $summaryPath -RuntimeObject $summary.runtime_gate
    Assert-RuntimeRawPairEqual $authorizationRawRuntime $summaryRawRuntime 'authorization/verifier-stdout'
    $summaryRuntime = Assert-RuntimeGate $summary.runtime_gate $VerifierAuthorization $authorizationRawRuntime 'verifier.summary.runtime_gate'
    foreach ($field in @(
        'primary_elapsed_token', 'replay_elapsed_token',
        'primary_elapsed_raw_bits', 'replay_elapsed_raw_bits',
        'primary_elapsed_convert_from_json_bits', 'replay_elapsed_convert_from_json_bits',
        'primary_convert_from_json_delta_ulp', 'replay_convert_from_json_delta_ulp',
        'primary_peak_resident_bytes', 'replay_peak_resident_bytes',
        'primary_passed', 'replay_passed', 'passed'
    )) {
        if ([string]$summaryRuntime.$field -cne [string]$deepRuntime.$field) {
            throw "Verifier summary/deep runtime differs: $field"
        }
    }
    return [pscustomobject]@{
        deep = $deep
        summary = $summary
        runtime = $deepRuntime
        final_verdict = $expectedFinalVerdict
    }
}

function Invoke-H9ARecoveryAudit {
    param([bool]$RecoveryLockHeld = $false)
    Assert-RecoveryPathSafety
    $recoverySeal = Assert-RecoveryLockFile
    $inventory = Assert-PreRecoveryInventory -RecoveryLockHeld $RecoveryLockHeld
    $gitAndInputs = Assert-GitAndInputs
    if ([string]$gitAndInputs.implementation.recovery_script.sha256 -cne
        [string]$recoverySeal.recovery_script_sha256 -or
        [string]$gitAndInputs.implementation.recovery_lock.sha256 -cne
        [string]$recoverySeal.record.sha256) {
        throw 'Recovery lock/script records differ across validation layers.'
    }
    $artifactRecords = Assert-FrozenArtifacts
    foreach ($key in @(
        'launch/primary_stderr.log', 'launch/primary_async_errors.jsonl',
        'launch/exact_replay_stderr.log', 'launch/exact_replay_async_errors.jsonl',
        'launch/verifier_stderr.log', 'launch/verifier_async_errors.jsonl'
    )) {
        if ([Int64]$artifactRecords[$key].bytes -ne 0) { throw "Nonempty failure evidence: $key" }
    }

    $primaryAuthorization = Assert-Authorization 'primary' 'run' 'primary' 'h9a_run_001'
    $replayAuthorization = Assert-Authorization 'exact_replay' 'run' 'exact_replay' 'h9a_run_001_replay'
    $verifierAuthorization = Assert-Authorization 'verifier' 'verify' 'verifier' 'deep_verification'
    $tokenHashes = @(
        [string]$primaryAuthorization.token_sha256,
        [string]$replayAuthorization.token_sha256,
        [string]$verifierAuthorization.token_sha256
    ) | Sort-Object -Unique
    if ($tokenHashes.Count -ne 3) { throw 'Original children did not use three distinct authorization tokens.' }

    $primaryHandshake = Assert-Handshake 'primary' 'run' 'primary' 'h9a_run_001' $expectedPrimaryPid $primaryAuthorization
    $replayHandshake = Assert-Handshake 'exact_replay' 'run' 'exact_replay' 'h9a_run_001_replay' $expectedReplayPid $replayAuthorization
    $verifierHandshake = Assert-Handshake 'verifier' 'verify' 'verifier' 'deep_verification' $expectedVerifierPid $verifierAuthorization
    $primaryRelease = Assert-InnerRelease 'primary' 'primary' $expectedPrimaryPid $primaryAuthorization
    $replayRelease = Assert-InnerRelease 'exact_replay' 'exact_replay' $expectedReplayPid $replayAuthorization
    $outerRelease = Assert-OuterRelease $primaryAuthorization

    $primary = Assert-ResultAndSummary `
        'primary' 'primary' 'h9a_run_001' $expectedPrimaryPid $primaryDirectory `
        $primaryAuthorization $primaryHandshake $primaryRelease
    $replay = Assert-ResultAndSummary `
        'exact_replay' 'exact_replay' 'h9a_run_001_replay' $expectedReplayPid $replayDirectory `
        $replayAuthorization $replayHandshake $replayRelease
    if (-not [string]::Equals(
        [string]$primary.payload_text, [string]$replay.payload_text, [StringComparison]::Ordinal
    ) -or [string]$primary.structural_verdict -cne [string]$replay.structural_verdict) {
        throw 'Primary/replay scientific payload or structural verdict is not exact.'
    }
    if ((Get-Sha256 -Path $primary.manifest_path) -cne (Get-Sha256 -Path $replay.manifest_path) -or
        (Get-Item -LiteralPath $primary.manifest_path).Length -ne
        (Get-Item -LiteralPath $replay.manifest_path).Length) {
        throw 'Primary/replay raw row manifests are not byte-identical by length/SHA-256.'
    }
    $deep = Assert-DeepVerification $verifierAuthorization ([string]$primary.structural_verdict)
    if ([string]$deep.final_verdict -cne 'KILL_H9_KRON_DIRECTION') {
        throw 'Frozen recovered chain does not recompute to its expected KILL verdict.'
    }
    foreach ($pid in @($expectedLauncherPid, $expectedPrimaryPid, $expectedReplayPid, $expectedVerifierPid)) {
        if (Test-ProcessAlive -ProcessId $pid) { throw "Original chain PID is live: $pid" }
    }
    if (Test-Path -LiteralPath $innerLock) { throw 'Inner lock appeared during audit.' }
    return [pscustomobject]@{
        recovery_seal = $recoverySeal
        inventory = $inventory
        git = $gitAndInputs
        artifacts = $artifactRecords
        primary_authorization = $primaryAuthorization
        replay_authorization = $replayAuthorization
        verifier_authorization = $verifierAuthorization
        primary_handshake = $primaryHandshake
        replay_handshake = $replayHandshake
        verifier_handshake = $verifierHandshake
        primary_release = $primaryRelease
        replay_release = $replayRelease
        outer_release = $outerRelease
        primary = $primary
        replay = $replay
        deep = $deep
    }
}

$initialAudit = Invoke-H9ARecoveryAudit -RecoveryLockHeld $false
if ($Mode -ceq 'Audit') {
    [ordered]@{
        schema_version = 'h9a_completion_recovery_audit.v1'
        status = 'H9A_RECOVERY_AUDIT_PASS'
        target_launch = $expectedLaunchName
        original_launch_id = $expectedLaunchId
        scientific_payload_sha256 = $expectedScientificHash
        row_manifest_sha256 = $expectedManifestHash
        deep_verification_sha256 = $expectedDeepHash
        structural_verdict = [string]$initialAudit.primary.structural_verdict
        runtime_gate_passed = [bool]$initialAudit.deep.runtime.passed
        runtime_raw_evidence = [ordered]@{
            primary_token = [string]$initialAudit.deep.runtime.primary_elapsed_token
            primary_binary64 = [string]$initialAudit.deep.runtime.primary_elapsed_raw_bits
            primary_convert_from_json_delta_ulp = [Int64]$initialAudit.deep.runtime.primary_convert_from_json_delta_ulp
            replay_token = [string]$initialAudit.deep.runtime.replay_elapsed_token
            replay_binary64 = [string]$initialAudit.deep.runtime.replay_elapsed_raw_bits
            replay_convert_from_json_delta_ulp = [Int64]$initialAudit.deep.runtime.replay_convert_from_json_delta_ulp
        }
        verdict = [string]$initialAudit.deep.final_verdict
        outcome_recomputed = $false
        decision_recomputed_from_frozen_artifacts = $true
        writes_performed = $false
        recovery_script = $initialAudit.git.implementation.recovery_script
        recovery_lock = $initialAudit.recovery_seal.record
        git_head = [string]$initialAudit.git.head
        original_launch_commit = [string]$initialAudit.git.original_launch_commit
    } | ConvertTo-Json -Depth 20 -Compress
    return
}

$recoveryGuid = [Guid]::NewGuid().ToString('N')
$recoveryId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ') + '_' + $recoveryGuid
$attestationPath = Join-Path $launchDirectory (
    'recovery_attestation_{0}.json' -f $recoveryGuid.Substring(0, 20)
)
$releasePath = Join-Path $launchDirectory (
    'recovery_lock_released_{0}.json' -f $recoveryGuid.Substring(0, 20)
)
$failureReleasePath = Join-Path $launchDirectory (
    'recovery_fail_{0}.json' -f $recoveryGuid.Substring(0, 20)
)
foreach ($path in @($attestationPath, $releasePath, $failureReleasePath, $completionMarker)) {
    if (Test-Path -LiteralPath $path) { throw "Refusing recovery artifact overwrite: $path" }
}

$recoveryOwner = [ordered]@{
    schema_version = 'h9a_completion_recovery_lock.v1'
    mode = 'h9a-run-001-completion-recovery-lock'
    pid = [int]$PID
    recovery_id = $recoveryId
    target_launch = $expectedLaunchName
    target_deep_sha256 = $expectedDeepHash
    git_head = [string]$initialAudit.git.head
    recovery_script_sha256 = [string]$initialAudit.recovery_seal.recovery_script_sha256
    recovery_lock_file_sha256 = [string]$initialAudit.recovery_seal.record.sha256
    created_unix_ns = Get-UnixTimeNs
}
$recoveryOwnerJson = ($recoveryOwner | ConvertTo-Json -Depth 20 -Compress) + "`n"
$recoveryOwnerBytes = (New-Object Text.UTF8Encoding($false)).GetBytes($recoveryOwnerJson)
$expectedRecoveryReleaseRecord = [ordered]@{
    path = $releasePath
    sha256 = Get-BytesSha256 -Bytes $recoveryOwnerBytes
    bytes = [Int64]$recoveryOwnerBytes.Length
}

$lockStream = $null
$lockReleaseRecord = $null
$attestationRecord = $null
$completionPayload = $null
$failure = $null
$cleanupFailure = $null
try {
    $lockStream = [IO.File]::Open(
        $outerLock, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None
    )
    $lockStream.Write($recoveryOwnerBytes, 0, $recoveryOwnerBytes.Length)
    $lockStream.Flush($true)

    $lockedAudit = Invoke-H9ARecoveryAudit -RecoveryLockHeld $true
    Assert-RecordsUnchanged $initialAudit.artifacts 'Original chain artifact'
    Assert-RecordsUnchanged $initialAudit.git.inputs 'Immutable input'
    Assert-RecordsUnchanged $initialAudit.git.implementation 'Implementation/recovery source'
    if ([string]$lockedAudit.git.head -cne [string]$initialAudit.git.head -or
        [string]$lockedAudit.recovery_seal.record.sha256 -cne
        [string]$initialAudit.recovery_seal.record.sha256) {
        throw 'Git HEAD or recovery seal changed across recovery-lock acquisition.'
    }

    $attestation = [ordered]@{
        schema_version = 'h9a_completion_recovery_attestation.v1'
        status = 'H9A_UNCOMMITTED_CHAIN_RECOVERY_ATTESTED'
        recovery_id = $recoveryId
        recovery_pid = [int]$PID
        verified_unix_ns = Get-UnixTimeNs
        scientific_outputs_recomputed = $false
        decision_recomputed_from_frozen_artifacts = $true
        target = [ordered]@{
            launch_directory = $launchDirectory
            launch_name = $expectedLaunchName
            original_launch_id = $expectedLaunchId
            recovered_completion_marker = $completionMarker
            normal_completion_marker = $normalCompletionMarker
            normal_completion_marker_verified_absent = $true
            sole_deep_chain = $lockedAudit.inventory
        }
        original_processes = [ordered]@{
            launcher_pid = $expectedLauncherPid
            primary_pid = $expectedPrimaryPid
            exact_replay_pid = $expectedReplayPid
            verifier_pid = $expectedVerifierPid
            all_dead_verified = $true
        }
        git = [ordered]@{
            head = [string]$lockedAudit.git.head
            original_launch_commit = [string]$lockedAudit.git.original_launch_commit
            original_launch_blobs = $lockedAudit.git.original_launch_blobs
            implementation_paths = $lockedAudit.git.implementation_paths
            worktree_and_index_clean_for_bound_paths = $true
            phase_a_ancestor = $expectedPhaseACommit
            original_launch_commit_verified_ancestor = $true
        }
        implementation = $lockedAudit.git.implementation
        immutable_inputs = $lockedAudit.git.inputs
        original_chain_files = $lockedAudit.artifacts
        process_crosslinks = [ordered]@{
            primary = [ordered]@{
                authorization = $lockedAudit.artifacts['launch/primary_authorization.json']
                process_start = $lockedAudit.artifacts['launch/primary_process_start.json']
                process_ack = $lockedAudit.artifacts['launch/primary_process_ack.json']
                stdout = $lockedAudit.artifacts['launch/primary_stdout.log']
                stderr = $lockedAudit.artifacts['launch/primary_stderr.log']
                async_error_ledger = $lockedAudit.artifacts['launch/primary_async_errors.jsonl']
                inner_lock_release = $lockedAudit.artifacts['launch/primary_inner_lock_released.json']
            }
            exact_replay = [ordered]@{
                authorization = $lockedAudit.artifacts['launch/exact_replay_authorization.json']
                process_start = $lockedAudit.artifacts['launch/exact_replay_process_start.json']
                process_ack = $lockedAudit.artifacts['launch/exact_replay_process_ack.json']
                stdout = $lockedAudit.artifacts['launch/exact_replay_stdout.log']
                stderr = $lockedAudit.artifacts['launch/exact_replay_stderr.log']
                async_error_ledger = $lockedAudit.artifacts['launch/exact_replay_async_errors.jsonl']
                inner_lock_release = $lockedAudit.artifacts['launch/exact_replay_inner_lock_released.json']
            }
            verifier = [ordered]@{
                authorization = $lockedAudit.artifacts['launch/verifier_authorization.json']
                process_start = $lockedAudit.artifacts['launch/verifier_process_start.json']
                process_ack = $lockedAudit.artifacts['launch/verifier_process_ack.json']
                stdout = $lockedAudit.artifacts['launch/verifier_stdout.log']
                stderr = $lockedAudit.artifacts['launch/verifier_stderr.log']
                async_error_ledger = $lockedAudit.artifacts['launch/verifier_async_errors.jsonl']
                deep_verification = $lockedAudit.artifacts['launch/deep_verification.json']
            }
            original_outer_lock_release = $lockedAudit.artifacts['launch/outer_fail_1b852251c15e40c88d29.json']
        }
        scientific_validation = [ordered]@{
            scientific_payload_sha256 = $expectedScientificHash
            primary_replay_payload_exact = $true
            row_manifest_sha256 = $expectedManifestHash
            row_manifest_bytes = [Int64]91622274
            row_manifest_rows = [Int64]64443
            primary_replay_manifest_exact = $true
            deep_verification_sha256 = $expectedDeepHash
            deep_verifier_booleans_all_true = $true
            structural_verdict_recomputed_from_payload_gates = [string]$lockedAudit.primary.structural_verdict
        }
        runtime_authority = [ordered]@{
            source = $lockedAudit.artifacts['launch/verifier_authorization.json']
            comparison = 'unique raw JSON number tokens parsed with invariant Double.Parse and matched exactly across authorization, deep verification, and verifier stdout; ConvertFrom-Json bits recorded only as defect evidence'
            primary_elapsed_token = [string]$lockedAudit.deep.runtime.primary_elapsed_token
            replay_elapsed_token = [string]$lockedAudit.deep.runtime.replay_elapsed_token
            primary_elapsed_raw_binary64 = [string]$lockedAudit.deep.runtime.primary_elapsed_raw_bits
            replay_elapsed_raw_binary64 = [string]$lockedAudit.deep.runtime.replay_elapsed_raw_bits
            primary_elapsed_convert_from_json_binary64 = [string]$lockedAudit.deep.runtime.primary_elapsed_convert_from_json_bits
            replay_elapsed_convert_from_json_binary64 = [string]$lockedAudit.deep.runtime.replay_elapsed_convert_from_json_bits
            primary_convert_from_json_delta_ulp = [Int64]$lockedAudit.deep.runtime.primary_convert_from_json_delta_ulp
            replay_convert_from_json_delta_ulp = [Int64]$lockedAudit.deep.runtime.replay_convert_from_json_delta_ulp
            primary_peak_resident_bytes = [Int64]$lockedAudit.deep.runtime.primary_peak_resident_bytes
            replay_peak_resident_bytes = [Int64]$lockedAudit.deep.runtime.replay_peak_resident_bytes
            primary_passed = [bool]$lockedAudit.deep.runtime.primary_passed
            replay_passed = [bool]$lockedAudit.deep.runtime.replay_passed
            passed = [bool]$lockedAudit.deep.runtime.passed
        }
        decision = [ordered]@{
            structural_verdict = [string]$lockedAudit.primary.structural_verdict
            runtime_gate_passed = [bool]$lockedAudit.deep.runtime.passed
            verdict = [string]$lockedAudit.deep.final_verdict
        }
        recovery = [ordered]@{
            outcome_recomputed = $false
            script = $lockedAudit.git.implementation.recovery_script
            prospective_recovery_lock = $lockedAudit.recovery_seal.record
            confirmation_token_sha256 = [string]$lockedAudit.recovery_seal.confirmation_token_sha256
            held_lock_path = $outerLock
            held_lock_owner_sha256 = [string]$expectedRecoveryReleaseRecord.sha256
            held_lock_owner_bytes = [Int64]$expectedRecoveryReleaseRecord.bytes
            intended_release_path = $releasePath
        }
    }
    Write-ExclusiveJson -Path $attestationPath -Value $attestation
    $attestationRecord = Get-FileRecord -Path $attestationPath

    Assert-RecordsUnchanged $lockedAudit.artifacts 'Original chain artifact'
    Assert-RecordsUnchanged $lockedAudit.git.inputs 'Immutable input'
    Assert-RecordsUnchanged $lockedAudit.git.implementation 'Implementation/recovery source'
    if ((Test-Path -LiteralPath $normalCompletionMarker) -or
        (Test-Path -LiteralPath $completionMarker) -or
        (Test-Path -LiteralPath $innerLock)) {
        throw 'Normal/recovered completion or inner lock appeared before recovery publication.'
    }
    foreach ($pid in @($expectedLauncherPid, $expectedPrimaryPid, $expectedReplayPid, $expectedVerifierPid)) {
        if (Test-ProcessAlive $pid) { throw "Original PID revived before recovery publication: $pid" }
    }

    $completionPayload = [ordered]@{
        schema_version = 'h9a_run_001_recovered_completion.v1'
        status = 'H9A_RUN_001_RECOVERED_COMPLETE'
        completion_mode = 'recovered_uncommitted_chain'
        launch_id = $expectedLaunchId
        launcher_pid = $expectedLauncherPid
        recovery_id = $recoveryId
        recovery_pid = [int]$PID
        completed_unix_ns = Get-UnixTimeNs
        outcome_recomputed = $false
        decision_recomputed_from_frozen_artifacts = $true
        label_free_input_surface = $true
        candidate_labels_opened = $false
        runtime = $lockedAudit.git.implementation
        immutable_inputs = $lockedAudit.git.inputs
        recovery_attestation = $attestationRecord
        original_outer_lock_release = $lockedAudit.artifacts['launch/outer_fail_1b852251c15e40c88d29.json']
        children = [ordered]@{
            primary = [ordered]@{
                pid = $expectedPrimaryPid
                summary = $lockedAudit.primary.summary
                authorization = $lockedAudit.artifacts['launch/primary_authorization.json']
                process_start = $lockedAudit.artifacts['launch/primary_process_start.json']
                process_ack = $lockedAudit.artifacts['launch/primary_process_ack.json']
                stdout = $lockedAudit.artifacts['launch/primary_stdout.log']
                stderr = $lockedAudit.artifacts['launch/primary_stderr.log']
                async_error_ledger = $lockedAudit.artifacts['launch/primary_async_errors.jsonl']
            }
            exact_replay = [ordered]@{
                pid = $expectedReplayPid
                summary = $lockedAudit.replay.summary
                authorization = $lockedAudit.artifacts['launch/exact_replay_authorization.json']
                process_start = $lockedAudit.artifacts['launch/exact_replay_process_start.json']
                process_ack = $lockedAudit.artifacts['launch/exact_replay_process_ack.json']
                stdout = $lockedAudit.artifacts['launch/exact_replay_stdout.log']
                stderr = $lockedAudit.artifacts['launch/exact_replay_stderr.log']
                async_error_ledger = $lockedAudit.artifacts['launch/exact_replay_async_errors.jsonl']
            }
            verifier = [ordered]@{
                pid = $expectedVerifierPid
                summary = $lockedAudit.deep.summary
                authorization = $lockedAudit.artifacts['launch/verifier_authorization.json']
                process_start = $lockedAudit.artifacts['launch/verifier_process_start.json']
                process_ack = $lockedAudit.artifacts['launch/verifier_process_ack.json']
                stdout = $lockedAudit.artifacts['launch/verifier_stdout.log']
                stderr = $lockedAudit.artifacts['launch/verifier_stderr.log']
                async_error_ledger = $lockedAudit.artifacts['launch/verifier_async_errors.jsonl']
            }
        }
        inner_lock_releases = [ordered]@{
            primary = $lockedAudit.artifacts['launch/primary_inner_lock_released.json']
            exact_replay = $lockedAudit.artifacts['launch/exact_replay_inner_lock_released.json']
        }
        outputs = [ordered]@{
            primary_result = $lockedAudit.artifacts['primary/result.json']
            primary_row_manifest = $lockedAudit.artifacts['primary/row_manifest.jsonl']
            replay_result = $lockedAudit.artifacts['replay/result.json']
            replay_row_manifest = $lockedAudit.artifacts['replay/row_manifest.jsonl']
            deep_verification = $lockedAudit.artifacts['launch/deep_verification.json']
        }
        exact_replay = [ordered]@{
            scientific_payload_sha256 = $expectedScientificHash
            row_manifest_sha256 = $expectedManifestHash
            row_manifest_bytes = [Int64]91622274
            structural_verdict = [string]$lockedAudit.primary.structural_verdict
            verified = $true
        }
        runtime_gate = [ordered]@{
            authority = $lockedAudit.artifacts['launch/verifier_authorization.json']
            primary_elapsed_token = [string]$lockedAudit.deep.runtime.primary_elapsed_token
            replay_elapsed_token = [string]$lockedAudit.deep.runtime.replay_elapsed_token
            primary_elapsed_raw_binary64 = [string]$lockedAudit.deep.runtime.primary_elapsed_raw_bits
            replay_elapsed_raw_binary64 = [string]$lockedAudit.deep.runtime.replay_elapsed_raw_bits
            primary_elapsed_convert_from_json_binary64 = [string]$lockedAudit.deep.runtime.primary_elapsed_convert_from_json_bits
            replay_elapsed_convert_from_json_binary64 = [string]$lockedAudit.deep.runtime.replay_elapsed_convert_from_json_bits
            primary_convert_from_json_delta_ulp = [Int64]$lockedAudit.deep.runtime.primary_convert_from_json_delta_ulp
            replay_convert_from_json_delta_ulp = [Int64]$lockedAudit.deep.runtime.replay_convert_from_json_delta_ulp
            primary_peak_resident_bytes = [Int64]$lockedAudit.deep.runtime.primary_peak_resident_bytes
            replay_peak_resident_bytes = [Int64]$lockedAudit.deep.runtime.replay_peak_resident_bytes
            primary_passed = [bool]$lockedAudit.deep.runtime.primary_passed
            replay_passed = [bool]$lockedAudit.deep.runtime.replay_passed
            passed = [bool]$lockedAudit.deep.runtime.passed
        }
        decision = [ordered]@{
            structural_verdict = [string]$lockedAudit.primary.structural_verdict
            runtime_gate_passed = [bool]$lockedAudit.deep.runtime.passed
            verdict = [string]$lockedAudit.deep.final_verdict
        }
        normal_completion_marker = $normalCompletionMarker
        normal_completion_marker_verified_absent = $true
        recovered_completion_marker_is_last = $true
        recovery_lock_release = $null
    }
}
catch {
    $failure = $_
}
finally {
    if ($null -ne $lockStream) {
        try {
            $lockStream.Dispose()
            $lockStream = $null
            $destination = if ($null -eq $failure) { $releasePath } else { $failureReleasePath }
            Move-ExclusiveFile -Source $outerLock -Destination $destination
            $lockReleaseRecord = Get-FileRecord -Path $destination
        }
        catch { $cleanupFailure = $_ }
    }
}

if ($null -ne $failure) {
    if ($null -ne $cleanupFailure) {
        throw ([System.AggregateException]::new(
            'H9A recovery validation and lock cleanup both failed.',
            [Exception[]]@($failure.Exception, $cleanupFailure.Exception)
        ))
    }
    throw $failure
}
if ($null -ne $cleanupFailure) { throw $cleanupFailure }
if ($null -eq $completionPayload -or $null -eq $attestationRecord -or $null -eq $lockReleaseRecord) {
    throw 'Recovery reached an incomplete publication state.'
}
if ([string]$lockReleaseRecord.path -cne [string]$expectedRecoveryReleaseRecord.path -or
    [string]$lockReleaseRecord.sha256 -cne [string]$expectedRecoveryReleaseRecord.sha256 -or
    [Int64]$lockReleaseRecord.bytes -ne [Int64]$expectedRecoveryReleaseRecord.bytes) {
    throw 'Released recovery lock differs from the attested owner bytes.'
}
$completionPayload.recovery_lock_release = $lockReleaseRecord
if ((Test-Path -LiteralPath $normalCompletionMarker) -or (Test-Path -LiteralPath $completionMarker)) {
    throw 'Normal/recovered completion marker appeared before recovery commit.'
}
Write-ExclusiveJson -Path $completionMarker -Value $completionPayload
# No filesystem mutation is permitted after the line above.
$completionPayload | ConvertTo-Json -Depth 60 -Compress
