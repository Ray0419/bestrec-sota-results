#requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter()]
    [string] $NewsPath = 'C:\Users\rayxc\Documents\R\experiments\kg_launch_autoresearch\data\MINDsmall_dev\MINDsmall_dev\news.tsv',

    [Parameter()]
    [string] $BehaviorsPath = 'C:\Users\rayxc\Documents\R\experiments\kg_launch_autoresearch\data\MINDsmall_dev\MINDsmall_dev\behaviors.tsv',

    [Parameter()]
    [string] $FactsPath = 'C:\Users\rayxc\Documents\R\experiments\kg_launch_autoresearch\experiments\h5_bitemporal_drift\results\run_003\facts.jsonl',

    [Parameter()]
    [string] $EntitiesPath = 'C:\Users\rayxc\Documents\R\experiments\kg_launch_autoresearch\experiments\h5_bitemporal_drift\results\run_003\entities.csv',

    [Parameter()]
    [string] $RelationEmbeddingPath = 'C:\Users\rayxc\Documents\R\experiments\kg_launch_autoresearch\data\MINDsmall_dev\MINDsmall_dev\relation_embedding.vec',

    [Parameter()]
    [string] $OutputRoot = 'C:\Users\rayxc\Documents\R\experiments\kg_launch_autoresearch\experiments\h6_ranking_consequence\results',

    [Parameter()]
    [switch] $SelfTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$RunId = 'coverage_run_001'
$Seed = '20260807'
$SampleSize = 50
$MinimumConfidence = 0.90
$ScoreTolerance = 1e-12
$ExpectedCutoffText = '2019-11-15T23:58:03Z'
$ExpectedNewsRows = 42416
$ExpectedBehaviorRows = 73152
$ExpectedRelationCount = 1091
$ExpectedHashes = [ordered]@{
    news = 'E5D144667558C449D16084FE6BFA01940C2F5D5785EA9F9110292BC3B94EB822'
    behaviors = 'B6C460E33B1A8693252DED6E626DA7D3CCF78920EEA2EC11889020BB7D8443EF'
    facts = '13571090E7983035C9FEEFC65AC295BA9C1D45ECC19814327CE311E830AA9E5D'
    entities = '45B83B0AFCB6C1348080984B1373CE50912219DFE247F48E97F7FB09009595ED'
    relations = 'D1BD69F5572714402CA5A3456A0C5F77750444C2F8D9144B0690CE094AD4C12A'
}
$MetadataBlocklistIds = [string[]] @('P1343', 'P1424', 'P5008', 'P6104', 'P7867', 'P8744', 'P9241', 'P2354', 'P8402', 'P10280', 'P1889')
$RemovedAnchorIds = [string[]] @('Q30', 'Q22686')
$InvariantCulture = [System.Globalization.CultureInfo]::InvariantCulture
$Ordinal = [System.StringComparer]::Ordinal
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$LineFeedBytes = [byte[]] @(10)

function Get-JsonPropertyValue {
    param(
        [AllowNull()][object] $Object,
        [Parameter(Mandatory = $true)][string] $Name
    )
    if ($null -eq $Object) { return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function New-OrdinalStringSet {
    return ,(New-Object 'System.Collections.Generic.HashSet[string]' ($Ordinal))
}

function New-SparseFactVector {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.HashSet[string]] $Facts
    )
    $vector = New-Object 'System.Collections.Generic.Dictionary[string,double]' ($Ordinal)
    if ($Facts.Count -eq 0) { return ,$vector }
    $weight = 1.0 / [math]::Sqrt([double] $Facts.Count)
    foreach ($fact in $Facts) { $vector.Add($fact, $weight) }
    return ,$vector
}

function Get-SparseFactDot {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.Dictionary[string,double]] $First,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.Dictionary[string,double]] $Second
    )
    $small = $First
    $large = $Second
    if ($First.Count -gt $Second.Count) { $small = $Second; $large = $First }
    [double] $sum = 0.0
    foreach ($entry in $small.GetEnumerator()) {
        [double] $other = 0.0
        if ($large.TryGetValue($entry.Key, [ref] $other)) { $sum += [double] $entry.Value * $other }
    }
    return $sum
}

function New-GramMatrix {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]] $Vectors
    )
    $count = $Vectors.Length
    $matrix = [double[,]]::new($count, $count)
    for ($firstIndex = 0; $firstIndex -lt $count; $firstIndex++) {
        for ($secondIndex = $firstIndex; $secondIndex -lt $count; $secondIndex++) {
            $value = Get-SparseFactDot -First $Vectors[$firstIndex] -Second $Vectors[$secondIndex]
            $matrix[$firstIndex, $secondIndex] = $value
            $matrix[$secondIndex, $firstIndex] = $value
        }
    }
    return ,$matrix
}

function New-ZeroCoefficientVector {
    return [pscustomobject]@{ Indices = [int[]] @(); Values = [double[]] @() }
}

function New-NewsCoefficientVector {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][int[]] $AnchorIndices,
        [Parameter(Mandatory = $true)][double[,]] $Gram,
        [Parameter(Mandatory = $true)][bool[]] $ExcludedAnchors
    )
    $active = New-Object 'System.Collections.Generic.List[int]'
    foreach ($anchorIndex in $AnchorIndices) {
        if (-not $ExcludedAnchors[$anchorIndex] -and $Gram[$anchorIndex, $anchorIndex] -gt 0.0) {
            $active.Add($anchorIndex)
        }
    }
    if ($active.Count -eq 0) { return New-ZeroCoefficientVector }
    [double] $normSquared = 0.0
    foreach ($firstIndex in $active) {
        foreach ($secondIndex in $active) { $normSquared += $Gram[$firstIndex, $secondIndex] }
    }
    if ([double]::IsNaN($normSquared) -or [double]::IsInfinity($normSquared) -or $normSquared -le 0.0) {
        throw 'A nonempty news anchor sum has a nonpositive or nonfinite squared norm.'
    }
    $coefficient = 1.0 / [math]::Sqrt($normSquared)
    $indices = $active.ToArray()
    $values = New-Object 'double[]' $indices.Length
    for ($position = 0; $position -lt $indices.Length; $position++) { $values[$position] = $coefficient }
    return [pscustomobject]@{ Indices = $indices; Values = $values }
}

function Get-CoefficientNormSquared {
    param(
        [Parameter(Mandatory = $true)][object] $Vector,
        [Parameter(Mandatory = $true)][double[,]] $Gram
    )
    [double] $sum = 0.0
    for ($firstPosition = 0; $firstPosition -lt $Vector.Indices.Length; $firstPosition++) {
        $firstIndex = $Vector.Indices[$firstPosition]
        for ($secondPosition = 0; $secondPosition -lt $Vector.Indices.Length; $secondPosition++) {
            $secondIndex = $Vector.Indices[$secondPosition]
            $sum += $Vector.Values[$firstPosition] * $Gram[$firstIndex, $secondIndex] * $Vector.Values[$secondPosition]
        }
    }
    return $sum
}

function New-UserCoefficientState {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]] $HistoryNews,
        [Parameter(Mandatory = $true)][int] $ViewIndex,
        [Parameter(Mandatory = $true)][ValidateSet('Historical', 'Current')][string] $Snapshot,
        [Parameter(Mandatory = $true)][double[,]] $Gram,
        [Parameter(Mandatory = $true)][int] $AnchorCount
    )
    $dense = New-Object 'double[]' $AnchorCount
    $marked = New-Object 'bool[]' $AnchorCount
    $active = New-Object 'System.Collections.Generic.List[int]'
    foreach ($news in $HistoryNews) {
        $vector = if ($Snapshot -eq 'Historical') { $news.HistoricalVectors[$ViewIndex] } else { $news.CurrentVectors[$ViewIndex] }
        for ($position = 0; $position -lt $vector.Indices.Length; $position++) {
            $anchorIndex = $vector.Indices[$position]
            $dense[$anchorIndex] += $vector.Values[$position]
            if (-not $marked[$anchorIndex]) { $marked[$anchorIndex] = $true; $active.Add($anchorIndex) }
        }
    }
    [double] $normSquared = 0.0
    foreach ($firstIndex in $active) {
        foreach ($secondIndex in $active) { $normSquared += $dense[$firstIndex] * $Gram[$firstIndex, $secondIndex] * $dense[$secondIndex] }
    }
    if ([double]::IsNaN($normSquared) -or [double]::IsInfinity($normSquared) -or $normSquared -lt -$ScoreTolerance) {
        throw 'A user vector has a nonfinite or negative squared norm.'
    }
    $norm = if ($normSquared -gt 0.0) { [math]::Sqrt($normSquared) } else { 0.0 }
    return [pscustomobject]@{ Dense = $dense; Active = $active.ToArray(); Norm = $norm }
}

function Get-KernelScore {
    param(
        [Parameter(Mandatory = $true)][object] $UserState,
        [Parameter(Mandatory = $true)][object] $NewsVector,
        [Parameter(Mandatory = $true)][double[,]] $Gram
    )
    if ($UserState.Norm -le 0.0 -or $NewsVector.Indices.Length -eq 0) { return 0.0 }
    [double] $sum = 0.0
    for ($newsPosition = 0; $newsPosition -lt $NewsVector.Indices.Length; $newsPosition++) {
        $newsIndex = $NewsVector.Indices[$newsPosition]
        [double] $rowDot = 0.0
        foreach ($userIndex in $UserState.Active) {
            $rowDot += $Gram[$newsIndex, $userIndex] * $UserState.Dense[$userIndex]
        }
        $sum += $NewsVector.Values[$newsPosition] * $rowDot
    }
    $score = $sum / $UserState.Norm
    if ([double]::IsNaN($score) -or [double]::IsInfinity($score)) { throw 'A candidate score is nonfinite.' }
    return $score
}

function Get-TieHash {
    param(
        [Parameter(Mandatory = $true)][string] $ImpressionId,
        [Parameter(Mandatory = $true)][string] $NewsId,
        [Parameter(Mandatory = $true)][System.Security.Cryptography.SHA256] $Hasher
    )
    $bytes = $Utf8NoBom.GetBytes($Seed + '|' + $ImpressionId + '|' + $NewsId)
    return ([System.BitConverter]::ToString($Hasher.ComputeHash($bytes))).Replace('-', '')
}

function Get-FrozenRanking {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]] $Candidates,
        [Parameter(Mandatory = $true)][int] $ViewIndex,
        [Parameter(Mandatory = $true)][ValidateSet('HistoricalScores', 'CurrentScores')][string] $ScoreProperty
    )
    $buckets = New-Object 'System.Collections.Generic.SortedDictionary[double,object]'
    foreach ($candidate in $Candidates) {
        $score = [double] $candidate.$ScoreProperty[$ViewIndex]
        if (-not $buckets.ContainsKey($score)) { $buckets.Add($score, (New-Object 'System.Collections.Generic.List[string]')) }
        $buckets[$score].Add($candidate.TieHash + '|' + $candidate.NewsId)
    }
    $scores = [double[]] @($buckets.Keys)
    [array]::Reverse($scores)
    $orderedIds = New-Object 'System.Collections.Generic.List[string]'
    $pendingTieKeys = New-Object 'System.Collections.Generic.List[string]'
    [double] $groupReference = 0.0
    $hasGroup = $false

    $flushGroup = {
        if ($pendingTieKeys.Count -eq 0) { return }
        $keys = $pendingTieKeys.ToArray()
        [array]::Sort($keys, $Ordinal)
        foreach ($key in $keys) { $orderedIds.Add($key.Substring(65)) }
        $pendingTieKeys.Clear()
    }

    foreach ($score in $scores) {
        if (-not $hasGroup) { $groupReference = $score; $hasGroup = $true }
        elseif ([math]::Abs($groupReference - $score) -gt $ScoreTolerance) {
            & $flushGroup
            $groupReference = $score
        }
        foreach ($tieKey in $buckets[$score]) { $pendingTieKeys.Add($tieKey) }
    }
    & $flushGroup

    $ranks = New-Object 'System.Collections.Generic.Dictionary[string,int]' ($Ordinal)
    for ($rankIndex = 0; $rankIndex -lt $orderedIds.Count; $rankIndex++) { $ranks.Add($orderedIds[$rankIndex], $rankIndex + 1) }
    return [pscustomobject]@{ OrderedIds = $orderedIds.ToArray(); Ranks = $ranks }
}

function Test-OrderedIdsEqual {
    param([string[]] $First, [string[]] $Second)
    if ($First.Length -ne $Second.Length) { return $false }
    for ($index = 0; $index -lt $First.Length; $index++) { if ($First[$index] -cne $Second[$index]) { return $false } }
    return $true
}

function Test-TopSetEqual {
    param([string[]] $First, [string[]] $Second, [int] $Count)
    $set = New-OrdinalStringSet
    for ($index = 0; $index -lt $Count; $index++) { $null = $set.Add($First[$index]) }
    for ($index = 0; $index -lt $Count; $index++) { if (-not $set.Contains($Second[$index])) { return $false } }
    return $true
}

function Get-QuantileSummary {
    param([Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.List[double]] $Values)
    if ($Values.Count -eq 0) { return $null }
    $array = $Values.ToArray()
    [array]::Sort($array)
    $output = [ordered]@{}
    foreach ($quantile in 0.0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0) {
        $position = ($array.Length - 1) * $quantile
        $lower = [int] [math]::Floor($position)
        $upper = [int] [math]::Ceiling($position)
        $value = if ($lower -eq $upper) { [double] $array[$lower] } else { [double] $array[$lower] + ($position - $lower) * ([double] $array[$upper] - [double] $array[$lower]) }
        $key = 'q' + ([int] [math]::Round(100.0 * $quantile)).ToString('00', $InvariantCulture)
        $output[$key] = $value
    }
    return $output
}

function New-ViewAccumulator {
    param([Parameter(Mandatory = $true)][string] $Name)
    return [pscustomobject]@{
        Name = $Name
        CandidateCount = [long] 0
        HistoricalNonzero = [long] 0
        CurrentNonzero = [long] 0
        ScoreChanged = [long] 0
        OrderChanged = [long] 0
        Top1Changed = [long] 0
        Top10Changed = [long] 0
        SignedDeltas = New-Object 'System.Collections.Generic.List[double]'
        AbsoluteDeltas = New-Object 'System.Collections.Generic.List[double]'
        ImpressionMaxAbsoluteDeltas = New-Object 'System.Collections.Generic.List[double]'
    }
}

function Add-SanityCheck {
    param(
        [Parameter(Mandatory = $true)][System.Collections.Generic.List[object]] $Checks,
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][bool] $Passed,
        [AllowNull()][object] $Observed
    )
    $Checks.Add([pscustomobject]@{ name = $Name; passed = $Passed; observed = $Observed })
}

function Write-Utf8Fsync {
    param([string] $Path, [string] $Content)
    $stream = New-Object System.IO.FileStream($Path, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None, 1048576, [System.IO.FileOptions]::WriteThrough)
    try {
        $bytes = $Utf8NoBom.GetBytes($Content)
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    }
    finally { $stream.Dispose() }
}

function Test-SafeRunTemporaryDirectory {
    param(
        [string] $Root,
        [string] $Identifier,
        [string] $Path
    )
    $resolvedRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $resolvedPath = [System.IO.Path]::GetFullPath($Path).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $parent = [System.IO.Path]::GetDirectoryName($resolvedPath)
    $leaf = [System.IO.Path]::GetFileName($resolvedPath)
    return $parent.Equals($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase) -and
        $leaf.StartsWith('.' + $Identifier + '.tmp.', [System.StringComparison]::Ordinal) -and
        $leaf.Length -eq (('.' + $Identifier + '.tmp.').Length + 32)
}

function Remove-SafeRunTemporaryDirectory {
    param([string] $Root, [string] $Identifier, [string] $Path)
    if (-not [System.IO.Directory]::Exists($Path)) { return }
    if (-not (Test-SafeRunTemporaryDirectory -Root $Root -Identifier $Identifier -Path $Path)) {
        throw "Refusing unsafe temporary cleanup target: $Path"
    }
    Remove-Item -LiteralPath ([System.IO.Path]::GetFullPath($Path)) -Recurse -Force
}

function Write-ManifestLineAndHash {
    param(
        [Parameter(Mandatory = $true)][System.IO.FileStream] $Stream,
        [Parameter(Mandatory = $true)][System.Security.Cryptography.SHA256] $Hasher,
        [Parameter(Mandatory = $true)][string] $Line
    )
    $bytes = $Utf8NoBom.GetBytes($Line)
    if ($bytes.Length -gt 0) {
        $Stream.Write($bytes, 0, $bytes.Length)
        $null = $Hasher.TransformBlock($bytes, 0, $bytes.Length, $bytes, 0)
    }
    $Stream.Write($LineFeedBytes, 0, 1)
    $null = $Hasher.TransformBlock($LineFeedBytes, 0, 1, $LineFeedBytes, 0)
}

function Complete-ManifestHash {
    param([Parameter(Mandatory = $true)][System.Security.Cryptography.SHA256] $Hasher)
    $empty = New-Object 'byte[]' 0
    $null = $Hasher.TransformFinalBlock($empty, 0, 0)
    return ([System.BitConverter]::ToString($Hasher.Hash)).Replace('-', '')
}

function Get-RetainedAnchorIndices {
    param(
        [string] $Line,
        [System.Collections.Generic.Dictionary[string,int]] $AnchorIndexByQid,
        [ref] $FieldFailureReference,
        [ref] $JsonFailureReference
    )
    $parts = $Line -split ([char] 9), 8
    if ($parts.Count -ne 8) { $FieldFailureReference.Value++; return $null }
    $indices = New-Object 'System.Collections.Generic.HashSet[int]'
    foreach ($columnIndex in 6, 7) {
        try { $annotations = $parts[$columnIndex] | ConvertFrom-Json -ErrorAction Stop }
        catch { $JsonFailureReference.Value++; continue }
        foreach ($annotation in @($annotations)) {
            if ($null -eq $annotation) { continue }
            $qidValue = Get-JsonPropertyValue -Object $annotation -Name 'WikidataId'
            $qid = if ($null -eq $qidValue) { '' } else { [System.Convert]::ToString($qidValue, $InvariantCulture).Trim() }
            if ($qid -notmatch '^Q[1-9][0-9]*$' -or -not $AnchorIndexByQid.ContainsKey($qid)) { continue }
            [double] $confidence = 0.0
            $confidenceValue = Get-JsonPropertyValue -Object $annotation -Name 'Confidence'
            $confidenceText = if ($null -eq $confidenceValue) { '' } else { [System.Convert]::ToString($confidenceValue, $InvariantCulture) }
            if ([double]::TryParse($confidenceText, [System.Globalization.NumberStyles]::Float, $InvariantCulture, [ref] $confidence) -and $confidence -ge $MinimumConfidence) {
                $null = $indices.Add($AnchorIndexByQid[$qid])
            }
        }
    }
    $array = [int[]] @($indices)
    [array]::Sort($array)
    return [pscustomobject]@{ Fields = $parts; Indices = $array }
}

function ConvertTo-CandidateNewsId {
    param([Parameter(Mandatory = $true)][string] $Token)
    if ($Token -cnotmatch '^N[0-9]+-[01]$') { throw 'Malformed candidate token encountered.' }
    $separator = $Token.LastIndexOf('-')
    return $Token.Substring(0, $separator)
}

if ($SelfTest) {
    $factsA = New-OrdinalStringSet
    $null = $factsA.Add('P1|Q1'); $null = $factsA.Add('P2|Q2')
    $factsB = New-OrdinalStringSet
    $null = $factsB.Add('P2|Q2'); $null = $factsB.Add('P3|Q3')
    $vectorA = New-SparseFactVector -Facts $factsA
    $vectorB = New-SparseFactVector -Facts $factsB
    if ([math]::Abs((Get-SparseFactDot -First $vectorA -Second $vectorA) - 1.0) -gt 1e-12 -or [math]::Abs((Get-SparseFactDot -First $vectorA -Second $vectorB) - 0.5) -gt 1e-12) { throw 'Self-test sparse fact kernel failed.' }
    $gram = New-GramMatrix -Vectors ([object[]] @($vectorA, $vectorB))
    $excluded = New-Object 'bool[]' 2
    $newsVector = New-NewsCoefficientVector -AnchorIndices ([int[]] @(0, 1)) -Gram $gram -ExcludedAnchors $excluded
    if ([math]::Abs((Get-CoefficientNormSquared -Vector $newsVector -Gram $gram) - 1.0) -gt 1e-12) { throw 'Self-test news normalization failed.' }
    $candidateZero = ConvertTo-CandidateNewsId -Token 'N10-0'
    $candidateOne = ConvertTo-CandidateNewsId -Token 'N10-1'
    if ($candidateZero -cne 'N10' -or $candidateOne -cne 'N10') { throw 'Self-test label-blind candidate recovery failed.' }
    $candidateA = [pscustomobject]@{ NewsId = 'N10'; TieHash = ('0' * 64); HistoricalScores = [double[]] @(0.5); CurrentScores = [double[]] @(0.5) }
    $candidateB = [pscustomobject]@{ NewsId = 'N20'; TieHash = ('F' * 64); HistoricalScores = [double[]] @(0.5); CurrentScores = [double[]] @(0.5) }
    $rankingFirst = Get-FrozenRanking -Candidates ([object[]] @($candidateA, $candidateB)) -ViewIndex 0 -ScoreProperty HistoricalScores
    $rankingSecond = Get-FrozenRanking -Candidates ([object[]] @($candidateB, $candidateA)) -ViewIndex 0 -ScoreProperty HistoricalScores
    if (-not (Test-OrderedIdsEqual -First $rankingFirst.OrderedIds -Second $rankingSecond.OrderedIds) -or $rankingFirst.OrderedIds[0] -cne 'N10') { throw 'Self-test tie ranking is not candidate-order invariant.' }
    $selfRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('provicold-h6-selftest-' + [guid]::NewGuid().ToString('N'))
    $resolvedTemp = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
    $resolvedSelf = [System.IO.Path]::GetFullPath($selfRoot)
    if (-not $resolvedSelf.StartsWith($resolvedTemp, [System.StringComparison]::OrdinalIgnoreCase) -or [System.IO.Path]::GetFileName($resolvedSelf) -notlike 'provicold-h6-selftest-*') { throw 'Self-test temporary path validation failed.' }
    $selfIdentifier = 'coverage_run_test'
    $selfStage = Join-Path $resolvedSelf ('.' + $selfIdentifier + '.tmp.' + [guid]::NewGuid().ToString('N'))
    try {
        [System.IO.Directory]::CreateDirectory($resolvedSelf) | Out-Null
        if (-not (Test-SafeRunTemporaryDirectory -Root $resolvedSelf -Identifier $selfIdentifier -Path $selfStage)) { throw 'Self-test run staging path validation failed.' }
        [System.IO.Directory]::CreateDirectory($selfStage) | Out-Null
        $selfManifestPath = Join-Path $selfStage 'cohort_manifest.jsonl'
        $selfManifestStream = New-Object System.IO.FileStream($selfManifestPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None, 1048576, [System.IO.FileOptions]::WriteThrough)
        $selfManifestHasher = [System.Security.Cryptography.SHA256]::Create()
        try {
            Write-ManifestLineAndHash -Stream $selfManifestStream -Hasher $selfManifestHasher -Line '{"i":"I1","u":"U1","h":[],"c":[]}'
            $selfManifestStream.Flush($true)
            $hashBefore = Complete-ManifestHash -Hasher $selfManifestHasher
        }
        finally { $selfManifestStream.Dispose(); $selfManifestHasher.Dispose() }
        Write-Utf8Fsync -Path (Join-Path $selfStage 'result.json') -Content ('{"manifest_sha256":"' + $hashBefore + '"}' + [char] 10)
        $published = Join-Path $resolvedSelf $selfIdentifier
        [System.IO.Directory]::Move($selfStage, $published)
        $hashAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $published 'cohort_manifest.jsonl')).Hash
        if ($hashBefore -cne $hashAfter) { throw 'Self-test manifest hashing or atomic publication failed.' }
    }
    finally {
        if ([System.IO.Directory]::Exists($selfStage)) { Remove-SafeRunTemporaryDirectory -Root $resolvedSelf -Identifier $selfIdentifier -Path $selfStage }
        if ([System.IO.Directory]::Exists($resolvedSelf)) {
            $resolvedCandidate = [System.IO.Path]::GetFullPath($resolvedSelf)
            if (-not $resolvedCandidate.StartsWith($resolvedTemp, [System.StringComparison]::OrdinalIgnoreCase) -or [System.IO.Path]::GetFileName($resolvedCandidate) -notlike 'provicold-h6-selftest-*') { throw 'Refusing unsafe self-test cleanup target.' }
            Remove-Item -LiteralPath $resolvedCandidate -Recurse -Force
        }
    }
    Write-Output 'H6_PHASE_A_SELFTEST_OK'
    exit 0
}

$runtimeRunnerPath = [System.IO.Path]::GetFullPath($MyInvocation.MyCommand.Path)
$protocolPath = Join-Path ([System.IO.Path]::GetDirectoryName([System.IO.Path]::GetDirectoryName($runtimeRunnerPath))) 'protocol.md'
if (-not [System.IO.File]::Exists($protocolPath)) { throw "Committed protocol file does not exist: $protocolPath" }
$runtimeRunnerSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $runtimeRunnerPath).Hash
$committedProtocolSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $protocolPath).Hash

$inputPaths = [ordered]@{
    news = $NewsPath
    behaviors = $BehaviorsPath
    facts = $FactsPath
    entities = $EntitiesPath
    relations = $RelationEmbeddingPath
}
$actualHashes = [ordered]@{}
foreach ($inputName in $inputPaths.Keys) {
    $inputPath = [string] $inputPaths[$inputName]
    if (-not [System.IO.File]::Exists($inputPath)) { throw "Immutable input does not exist: $inputPath" }
    $actualHashes[$inputName] = (Get-FileHash -Algorithm SHA256 -LiteralPath $inputPath).Hash
    if ([string] $actualHashes[$inputName] -cne [string] $ExpectedHashes[$inputName]) { throw "Immutable input hash mismatch for $inputName." }
}
$finalDirectory = Join-Path $OutputRoot $RunId
if ([System.IO.Directory]::Exists($finalDirectory) -or [System.IO.File]::Exists($finalDirectory)) { throw "Refusing to overwrite existing result path: $finalDirectory" }

$relationIds = New-OrdinalStringSet
[long] $relationRows = 0
[long] $invalidRelationRows = 0
$reader = New-Object System.IO.StreamReader($RelationEmbeddingPath, $Utf8NoBom, $true, 1048576)
try {
    while (-not $reader.EndOfStream) {
        $line = $reader.ReadLine(); $relationRows++
        $separator = $line.IndexOf([char] 9)
        $relationId = if ($separator -gt 0) { $line.Substring(0, $separator) } else { '' }
        if ($relationId -notmatch '^P[1-9][0-9]*$' -or -not $relationIds.Add($relationId)) { $invalidRelationRows++ }
    }
}
finally { $reader.Dispose() }
if ($invalidRelationRows -ne 0 -or $relationIds.Count -ne $ExpectedRelationCount) { throw 'Frozen relation-ID vocabulary failed integrity checks.' }

$metadataBlocklist = New-OrdinalStringSet
foreach ($propertyId in $MetadataBlocklistIds) { $null = $metadataBlocklist.Add($propertyId) }
$removedAnchors = New-OrdinalStringSet
foreach ($qid in $RemovedAnchorIds) { $null = $removedAnchors.Add($qid) }

$anchorRows = New-Object 'System.Collections.Generic.List[object]'
$anchorIds = New-OrdinalStringSet
$factsReader = New-Object System.IO.StreamReader($FactsPath, $Utf8NoBom, $true, 1048576)
[long] $factsRows = 0
try {
    while (-not $factsReader.EndOfStream) {
        $line = $factsReader.ReadLine()
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $factsRows++
        $row = $line | ConvertFrom-Json -ErrorAction Stop
        $qid = [string] $row.qid
        if ($qid -notmatch '^Q[1-9][0-9]*$' -or -not $anchorIds.Add($qid) -or -not [bool] $row.api_ok) { throw 'H5 anchor ledger has an invalid, duplicate, or unresolved entity.' }
        $currentPrimaryFacts = New-OrdinalStringSet
        $historicalPrimaryFacts = New-OrdinalStringSet
        $currentBlockFacts = New-OrdinalStringSet
        $historicalBlockFacts = New-OrdinalStringSet
        foreach ($snapshotName in 'current', 'historical') {
            $sourceFacts = if ($snapshotName -eq 'current') { @($row.current.facts) } else { @($row.historical.facts) }
            $seenSourceFacts = New-OrdinalStringSet
            foreach ($factValue in $sourceFacts) {
                $fact = [string] $factValue
                if ($fact -notmatch '^P[1-9][0-9]*\|Q[1-9][0-9]*$' -or -not $seenSourceFacts.Add($fact)) { throw 'H5 anchor ledger contains an invalid or duplicate fact signature.' }
                $propertyId = $fact.Substring(0, $fact.IndexOf('|'))
                if ($relationIds.Contains($propertyId)) {
                    if ($snapshotName -eq 'current') { $null = $currentPrimaryFacts.Add($fact) } else { $null = $historicalPrimaryFacts.Add($fact) }
                    if (-not $metadataBlocklist.Contains($propertyId)) {
                        if ($snapshotName -eq 'current') { $null = $currentBlockFacts.Add($fact) } else { $null = $historicalBlockFacts.Add($fact) }
                    }
                }
            }
        }
        $anchorRows.Add([pscustomobject]@{
            Qid = $qid
            CurrentPrimaryVector = New-SparseFactVector -Facts $currentPrimaryFacts
            HistoricalPrimaryVector = New-SparseFactVector -Facts $historicalPrimaryFacts
            CurrentBlockVector = New-SparseFactVector -Facts $currentBlockFacts
            HistoricalBlockVector = New-SparseFactVector -Facts $historicalBlockFacts
        })
    }
}
finally { $factsReader.Dispose() }
if ($factsRows -ne $SampleSize -or $anchorRows.Count -ne $SampleSize -or $anchorIds.Count -ne $SampleSize) { throw 'H5 anchor sample does not contain exactly 50 distinct resolved QIDs.' }

$entityRows = @(Import-Csv -LiteralPath $EntitiesPath)
$entityIds = New-OrdinalStringSet
foreach ($entityRow in $entityRows) {
    if (-not $entityIds.Add([string] $entityRow.qid) -or [string] $entityRow.api_ok -cne 'True') { throw 'H5 entity summary has a duplicate or unresolved row.' }
}
if ($entityRows.Length -ne $SampleSize -or $entityIds.Count -ne $SampleSize -or -not $entityIds.SetEquals($anchorIds)) { throw 'H5 entity summary does not reproduce the facts-ledger sample.' }

$anchorIndexByQid = New-Object 'System.Collections.Generic.Dictionary[string,int]' ($Ordinal)
$currentPrimaryVectors = New-Object 'object[]' $SampleSize
$historicalPrimaryVectors = New-Object 'object[]' $SampleSize
$currentBlockVectors = New-Object 'object[]' $SampleSize
$historicalBlockVectors = New-Object 'object[]' $SampleSize
for ($anchorIndex = 0; $anchorIndex -lt $SampleSize; $anchorIndex++) {
    $anchor = $anchorRows[$anchorIndex]
    $anchorIndexByQid.Add($anchor.Qid, $anchorIndex)
    $currentPrimaryVectors[$anchorIndex] = $anchor.CurrentPrimaryVector
    $historicalPrimaryVectors[$anchorIndex] = $anchor.HistoricalPrimaryVector
    $currentBlockVectors[$anchorIndex] = $anchor.CurrentBlockVector
    $historicalBlockVectors[$anchorIndex] = $anchor.HistoricalBlockVector
}

$primaryExcluded = New-Object 'bool[]' $SampleSize
$removedExcluded = New-Object 'bool[]' $SampleSize
foreach ($qid in $RemovedAnchorIds) {
    if (-not $anchorIndexByQid.ContainsKey($qid)) { throw "Predeclared removed anchor is absent from the H5 sample: $qid" }
    $removedExcluded[$anchorIndexByQid[$qid]] = $true
}
$views = [object[]] @(
    [pscustomobject]@{ Name = 'primary_relation_vocabulary'; HistoricalGram = New-GramMatrix -Vectors $historicalPrimaryVectors; CurrentGram = New-GramMatrix -Vectors $currentPrimaryVectors; ExcludedAnchors = $primaryExcluded },
    [pscustomobject]@{ Name = 'metadata_blocklist'; HistoricalGram = New-GramMatrix -Vectors $historicalBlockVectors; CurrentGram = New-GramMatrix -Vectors $currentBlockVectors; ExcludedAnchors = $primaryExcluded },
    [pscustomobject]@{ Name = 'remove_q30_q22686'; HistoricalGram = New-GramMatrix -Vectors $historicalPrimaryVectors; CurrentGram = New-GramMatrix -Vectors $currentPrimaryVectors; ExcludedAnchors = $removedExcluded }
)

$newsById = New-Object 'System.Collections.Generic.Dictionary[string,object]' ($Ordinal)
[long] $newsRows = 0
[long] $newsFieldFailures = 0
[long] $newsJsonFailures = 0
[long] $newsWithAnchor = 0
[long] $newsVectorNormFailures = 0
$newsReader = New-Object System.IO.StreamReader($NewsPath, $Utf8NoBom, $true, 1048576)
try {
    while (-not $newsReader.EndOfStream) {
        $line = $newsReader.ReadLine(); $newsRows++
        $parsedNews = Get-RetainedAnchorIndices -Line $line -AnchorIndexByQid $anchorIndexByQid -FieldFailureReference ([ref] $newsFieldFailures) -JsonFailureReference ([ref] $newsJsonFailures)
        if ($null -eq $parsedNews) { continue }
        $newsId = [string] $parsedNews.Fields[0]
        if ($newsId -notmatch '^N[0-9]+$' -or $newsById.ContainsKey($newsId)) { throw 'News input has an invalid or duplicate news ID.' }
        $indices = [int[]] $parsedNews.Indices
        if ($indices.Length -gt 0) { $newsWithAnchor++ }
        $historicalVectors = New-Object 'object[]' $views.Length
        $currentVectors = New-Object 'object[]' $views.Length
        for ($viewIndex = 0; $viewIndex -lt $views.Length; $viewIndex++) {
            $historicalVectors[$viewIndex] = New-NewsCoefficientVector -AnchorIndices $indices -Gram $views[$viewIndex].HistoricalGram -ExcludedAnchors $views[$viewIndex].ExcludedAnchors
            $currentVectors[$viewIndex] = New-NewsCoefficientVector -AnchorIndices $indices -Gram $views[$viewIndex].CurrentGram -ExcludedAnchors $views[$viewIndex].ExcludedAnchors
            foreach ($pair in @(@($historicalVectors[$viewIndex], $views[$viewIndex].HistoricalGram), @($currentVectors[$viewIndex], $views[$viewIndex].CurrentGram))) {
                if ($pair[0].Indices.Length -gt 0 -and [math]::Abs((Get-CoefficientNormSquared -Vector $pair[0] -Gram $pair[1]) - 1.0) -gt 1e-10) { $newsVectorNormFailures++ }
            }
        }
        $newsById.Add($newsId, [pscustomobject]@{
            NewsId = $newsId
            HasAnchor = $indices.Length -gt 0
            HistoricalVectors = $historicalVectors
            CurrentVectors = $currentVectors
        })
    }
}
finally { $newsReader.Dispose() }
if ($newsRows -ne $ExpectedNewsRows -or $newsFieldFailures -ne 0 -or $newsJsonFailures -ne 0 -or $newsVectorNormFailures -ne 0) { throw 'News parsing or cached-vector integrity failed.' }

$viewAccumulators = New-Object 'object[]' $views.Length
for ($viewIndex = 0; $viewIndex -lt $views.Length; $viewIndex++) { $viewAccumulators[$viewIndex] = New-ViewAccumulator -Name $views[$viewIndex].Name }
$eligibleUsers = New-OrdinalStringSet
$seenImpressions = New-OrdinalStringSet
[long] $behaviorRows = 0
[long] $behaviorFieldFailures = 0
[long] $behaviorTimestampFailures = 0
[long] $malformedCandidateTokens = 0
[long] $duplicateCandidateIds = 0
[long] $unknownCandidateIds = 0
[long] $unknownHistoryIds = 0
[long] $eligibleImpressions = 0
[long] $totalCandidates = 0
[long] $manifestLineCount = 0
[long] $manifestSuffixLeakLines = 0
$maximumBehaviorTime = [datetime]::MinValue
$timestampStyles = [System.Globalization.DateTimeStyles]::AssumeUniversal -bor [System.Globalization.DateTimeStyles]::AdjustToUniversal
$temporaryDirectory = Join-Path $OutputRoot ('.' + $RunId + '.tmp.' + [guid]::NewGuid().ToString('N'))
if (-not (Test-SafeRunTemporaryDirectory -Root $OutputRoot -Identifier $RunId -Path $temporaryDirectory)) { throw "Refusing unsafe run staging path: $temporaryDirectory" }
$manifestStream = $null
$manifestHasher = $null
$manifestSha256 = $null
$manifestHashFinalized = $false
$publishedDirectory = $null
try {
    [System.IO.Directory]::CreateDirectory($OutputRoot) | Out-Null
    if ([System.IO.Directory]::Exists($finalDirectory) -or [System.IO.File]::Exists($finalDirectory)) { throw "Result path appeared before cohort streaming; refusing to overwrite: $finalDirectory" }
    [System.IO.Directory]::CreateDirectory($temporaryDirectory) | Out-Null
    $manifestPath = Join-Path $temporaryDirectory 'cohort_manifest.jsonl'
    $manifestStream = New-Object System.IO.FileStream($manifestPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None, 1048576, [System.IO.FileOptions]::WriteThrough)
    $manifestHasher = [System.Security.Cryptography.SHA256]::Create()
    $tieHasher = [System.Security.Cryptography.SHA256]::Create()
    $behaviorReader = New-Object System.IO.StreamReader($BehaviorsPath, $Utf8NoBom, $true, 1048576)
try {
    while (-not $behaviorReader.EndOfStream) {
        $line = $behaviorReader.ReadLine(); $behaviorRows++
        $fields = $line -split ([char] 9), 5
        if ($fields.Count -ne 5) { $behaviorFieldFailures++; throw 'Behavior row does not have exactly five fields.' }
        $impressionId = [string] $fields[0]
        $userId = [string] $fields[1]
        if ([string]::IsNullOrWhiteSpace($impressionId) -or [string]::IsNullOrWhiteSpace($userId) -or -not $seenImpressions.Add($impressionId)) { throw 'Behavior input has a missing or duplicate impression/user identifier.' }
        $parsedTime = [datetime]::MinValue
        if (-not [datetime]::TryParseExact($fields[2], 'M/d/yyyy h:mm:ss tt', $InvariantCulture, $timestampStyles, [ref] $parsedTime)) { $behaviorTimestampFailures++; throw 'Behavior timestamp is invalid.' }
        if ($parsedTime -gt $maximumBehaviorTime) { $maximumBehaviorTime = $parsedTime }

        $historyIds = New-Object 'System.Collections.Generic.List[string]'
        if (-not [string]::IsNullOrWhiteSpace($fields[3])) {
            foreach ($historyToken in [System.Text.RegularExpressions.Regex]::Split($fields[3].Trim(), '\s+')) {
                if ($historyToken -notmatch '^N[0-9]+$' -or -not $newsById.ContainsKey($historyToken)) { $unknownHistoryIds++; throw 'Unknown or malformed history news ID encountered.' }
                $historyIds.Add($historyToken)
            }
        }

        $candidateIds = New-Object 'System.Collections.Generic.List[string]'
        $candidateSet = New-OrdinalStringSet
        if ([string]::IsNullOrWhiteSpace($fields[4])) { $malformedCandidateTokens++; throw 'An impression has no candidate tokens.' }
        foreach ($candidateToken in [System.Text.RegularExpressions.Regex]::Split($fields[4].Trim(), '\s+')) {
            try { $candidateId = ConvertTo-CandidateNewsId -Token $candidateToken }
            catch { $malformedCandidateTokens++; throw }
            if (-not $candidateSet.Add($candidateId)) { $duplicateCandidateIds++; throw 'Duplicate candidate news ID encountered.' }
            if (-not $newsById.ContainsKey($candidateId)) { $unknownCandidateIds++; throw 'Unknown candidate news ID encountered.' }
            $candidateIds.Add($candidateId)
        }
        # The validated source field is deliberately discarded before cohort
        # membership or any structural computation.  Only recovered news IDs
        # survive this point.
        $candidateToken = $null
        $fields[4] = $null
        $line = $null

        $historyStart = [math]::Max(0, $historyIds.Count - 50)
        $retainedHistoryIds = New-Object 'System.Collections.Generic.List[string]'
        $retainedHistoryNews = New-Object 'System.Collections.Generic.List[object]'
        $historyHasAnchor = $false
        for ($historyIndex = $historyStart; $historyIndex -lt $historyIds.Count; $historyIndex++) {
            $historyId = $historyIds[$historyIndex]
            $historyNews = $newsById[$historyId]
            $retainedHistoryIds.Add($historyId)
            $retainedHistoryNews.Add($historyNews)
            if ($historyNews.HasAnchor) { $historyHasAnchor = $true }
        }
        if ($candidateIds.Count -lt 2 -or -not $historyHasAnchor) { continue }

        $eligibleImpressions++
        $totalCandidates += $candidateIds.Count
        $null = $eligibleUsers.Add($userId)
        $candidateRecords = New-Object 'System.Collections.Generic.List[object]'
        $candidateRecordById = New-Object 'System.Collections.Generic.Dictionary[string,object]' ($Ordinal)
        $historyNewsArray = $retainedHistoryNews.ToArray()
        $historicalUserStates = New-Object 'object[]' $views.Length
        $currentUserStates = New-Object 'object[]' $views.Length
        for ($viewIndex = 0; $viewIndex -lt $views.Length; $viewIndex++) {
            $historicalUserStates[$viewIndex] = New-UserCoefficientState -HistoryNews $historyNewsArray -ViewIndex $viewIndex -Snapshot Historical -Gram $views[$viewIndex].HistoricalGram -AnchorCount $SampleSize
            $currentUserStates[$viewIndex] = New-UserCoefficientState -HistoryNews $historyNewsArray -ViewIndex $viewIndex -Snapshot Current -Gram $views[$viewIndex].CurrentGram -AnchorCount $SampleSize
        }
        foreach ($candidateId in $candidateIds) {
            $candidateNews = $newsById[$candidateId]
            $historicalScores = New-Object 'double[]' $views.Length
            $currentScores = New-Object 'double[]' $views.Length
            for ($viewIndex = 0; $viewIndex -lt $views.Length; $viewIndex++) {
                $historicalScores[$viewIndex] = Get-KernelScore -UserState $historicalUserStates[$viewIndex] -NewsVector $candidateNews.HistoricalVectors[$viewIndex] -Gram $views[$viewIndex].HistoricalGram
                $currentScores[$viewIndex] = Get-KernelScore -UserState $currentUserStates[$viewIndex] -NewsVector $candidateNews.CurrentVectors[$viewIndex] -Gram $views[$viewIndex].CurrentGram
            }
            $candidateRecord = [pscustomobject]@{ NewsId = $candidateId; TieHash = Get-TieHash -ImpressionId $impressionId -NewsId $candidateId -Hasher $tieHasher; HistoricalScores = $historicalScores; CurrentScores = $currentScores }
            $candidateRecords.Add($candidateRecord)
            $candidateRecordById.Add($candidateId, $candidateRecord)
        }

        $historicalRankings = New-Object 'object[]' $views.Length
        $currentRankings = New-Object 'object[]' $views.Length
        for ($viewIndex = 0; $viewIndex -lt $views.Length; $viewIndex++) {
            $historicalRankings[$viewIndex] = Get-FrozenRanking -Candidates $candidateRecords.ToArray() -ViewIndex $viewIndex -ScoreProperty HistoricalScores
            $currentRankings[$viewIndex] = Get-FrozenRanking -Candidates $candidateRecords.ToArray() -ViewIndex $viewIndex -ScoreProperty CurrentScores
            $accumulator = $viewAccumulators[$viewIndex]
            $accumulator.CandidateCount += $candidateRecords.Count
            [double] $maximumAbsoluteDelta = 0.0
            foreach ($candidate in $candidateRecords) {
                $historicalScore = [double] $candidate.HistoricalScores[$viewIndex]
                $currentScore = [double] $candidate.CurrentScores[$viewIndex]
                if ([math]::Abs($historicalScore) -gt $ScoreTolerance) { $accumulator.HistoricalNonzero++ }
                if ([math]::Abs($currentScore) -gt $ScoreTolerance) { $accumulator.CurrentNonzero++ }
                $delta = $currentScore - $historicalScore
                $absoluteDelta = [math]::Abs($delta)
                $accumulator.SignedDeltas.Add($delta)
                $accumulator.AbsoluteDeltas.Add($absoluteDelta)
                if ($absoluteDelta -gt $maximumAbsoluteDelta) { $maximumAbsoluteDelta = $absoluteDelta }
            }
            $accumulator.ImpressionMaxAbsoluteDeltas.Add($maximumAbsoluteDelta)
            if ($maximumAbsoluteDelta -gt $ScoreTolerance) { $accumulator.ScoreChanged++ }
            if (-not (Test-OrderedIdsEqual -First $historicalRankings[$viewIndex].OrderedIds -Second $currentRankings[$viewIndex].OrderedIds)) { $accumulator.OrderChanged++ }
            if ($historicalRankings[$viewIndex].OrderedIds[0] -cne $currentRankings[$viewIndex].OrderedIds[0]) { $accumulator.Top1Changed++ }
            $topCount = [math]::Min(10, $candidateRecords.Count)
            if (-not (Test-TopSetEqual -First $historicalRankings[$viewIndex].OrderedIds -Second $currentRankings[$viewIndex].OrderedIds -Count $topCount)) { $accumulator.Top10Changed++ }
        }

        $canonicalCandidateIds = $candidateIds.ToArray()
        [array]::Sort($canonicalCandidateIds, $Ordinal)
        $manifestCandidates = New-Object 'System.Collections.Generic.List[object]'
        foreach ($candidateId in $canonicalCandidateIds) {
            $candidate = $candidateRecordById[$candidateId]
            $candidateViewTuples = New-Object 'System.Collections.Generic.List[object]'
            for ($viewIndex = 0; $viewIndex -lt $views.Length; $viewIndex++) {
                $candidateViewTuples.Add([object[]] @(
                    [double] $candidate.HistoricalScores[$viewIndex],
                    [double] $candidate.CurrentScores[$viewIndex],
                    [int] $historicalRankings[$viewIndex].Ranks[$candidateId],
                    [int] $currentRankings[$viewIndex].Ranks[$candidateId]
                ))
            }
            $manifestCandidates.Add([pscustomobject] ([ordered]@{ n = $candidateId; v = $candidateViewTuples.ToArray() }))
        }
        $manifestRecord = [ordered]@{
            i = $impressionId
            u = $userId
            h = $retainedHistoryIds.ToArray()
            c = $manifestCandidates.ToArray()
        }
        $manifestLine = $manifestRecord | ConvertTo-Json -Depth 8 -Compress
        if ([System.Text.RegularExpressions.Regex]::IsMatch($manifestLine, '"N[0-9]+-[01]"')) { $manifestSuffixLeakLines++ }
        Write-ManifestLineAndHash -Stream $manifestStream -Hasher $manifestHasher -Line $manifestLine
        $manifestLineCount++
    }

    $manifestStream.Flush($true)
    $manifestSha256 = Complete-ManifestHash -Hasher $manifestHasher
    $manifestHashFinalized = $true
}
finally {
    $behaviorReader.Dispose()
    $tieHasher.Dispose()
    if ($null -ne $manifestStream) { $manifestStream.Dispose() }
    if ($null -ne $manifestHasher) { $manifestHasher.Dispose() }
}

$manifestSpoolSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash

$maximumBehaviorText = $maximumBehaviorTime.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ', $InvariantCulture)
$viewResults = [ordered]@{}
foreach ($accumulator in $viewAccumulators) {
    $impressionDenominator = [double] $eligibleImpressions
    $candidateDenominator = [double] $accumulator.CandidateCount
    $viewResults[$accumulator.Name] = [ordered]@{
        eligible_impressions = $eligibleImpressions
        candidates = $accumulator.CandidateCount
        candidate_nonzero_score = [ordered]@{
            historical_count = $accumulator.HistoricalNonzero
            historical_rate = if ($candidateDenominator -gt 0) { [double] $accumulator.HistoricalNonzero / $candidateDenominator } else { $null }
            current_count = $accumulator.CurrentNonzero
            current_rate = if ($candidateDenominator -gt 0) { [double] $accumulator.CurrentNonzero / $candidateDenominator } else { $null }
        }
        score_vector_changed = [ordered]@{ count = $accumulator.ScoreChanged; rate = if ($impressionDenominator -gt 0) { [double] $accumulator.ScoreChanged / $impressionDenominator } else { $null } }
        total_order_changed = [ordered]@{ count = $accumulator.OrderChanged; rate = if ($impressionDenominator -gt 0) { [double] $accumulator.OrderChanged / $impressionDenominator } else { $null } }
        top1_changed = [ordered]@{ count = $accumulator.Top1Changed; rate = if ($impressionDenominator -gt 0) { [double] $accumulator.Top1Changed / $impressionDenominator } else { $null } }
        top_min10_set_changed = [ordered]@{ count = $accumulator.Top10Changed; rate = if ($impressionDenominator -gt 0) { [double] $accumulator.Top10Changed / $impressionDenominator } else { $null } }
        score_delta_quantiles = [ordered]@{
            candidate_signed_current_minus_historical = Get-QuantileSummary -Values $accumulator.SignedDeltas
            candidate_absolute = Get-QuantileSummary -Values $accumulator.AbsoluteDeltas
            impression_max_absolute = Get-QuantileSummary -Values $accumulator.ImpressionMaxAbsoluteDeltas
            interpolation = 'linear at (n-1)q'
        }
    }
}

$sanityChecks = New-Object 'System.Collections.Generic.List[object]'
foreach ($inputName in $inputPaths.Keys) { Add-SanityCheck -Checks $sanityChecks -Name ('sha256_' + $inputName) -Passed ([string] $actualHashes[$inputName] -ceq [string] $ExpectedHashes[$inputName]) -Observed $actualHashes[$inputName] }
Add-SanityCheck -Checks $sanityChecks -Name 'news_row_count_and_parse' -Passed ($newsRows -eq $ExpectedNewsRows -and $newsFieldFailures -eq 0 -and $newsJsonFailures -eq 0) -Observed ([ordered]@{ rows = $newsRows; field_failures = $newsFieldFailures; json_failures = $newsJsonFailures })
Add-SanityCheck -Checks $sanityChecks -Name 'behavior_row_count_and_parse' -Passed ($behaviorRows -eq $ExpectedBehaviorRows -and $behaviorFieldFailures -eq 0 -and $behaviorTimestampFailures -eq 0) -Observed ([ordered]@{ rows = $behaviorRows; field_failures = $behaviorFieldFailures; timestamp_failures = $behaviorTimestampFailures })
Add-SanityCheck -Checks $sanityChecks -Name 'cutoff_matches_lock' -Passed ($maximumBehaviorText -ceq $ExpectedCutoffText) -Observed $maximumBehaviorText
Add-SanityCheck -Checks $sanityChecks -Name 'sample_has_50_distinct_qids' -Passed ($anchorIds.Count -eq $SampleSize -and $entityIds.SetEquals($anchorIds)) -Observed $anchorIds.Count
Add-SanityCheck -Checks $sanityChecks -Name 'relation_vocabulary_has_1091_distinct_ids' -Passed ($relationIds.Count -eq $ExpectedRelationCount -and $invalidRelationRows -eq 0) -Observed ([ordered]@{ rows = $relationRows; distinct = $relationIds.Count; invalid_or_duplicate = $invalidRelationRows })
Add-SanityCheck -Checks $sanityChecks -Name 'cached_news_vectors_unit_normalized' -Passed ($newsVectorNormFailures -eq 0) -Observed ([ordered]@{ failures = $newsVectorNormFailures; news_with_anchor = $newsWithAnchor })
Add-SanityCheck -Checks $sanityChecks -Name 'candidate_and_history_integrity' -Passed (($malformedCandidateTokens + $duplicateCandidateIds + $unknownCandidateIds + $unknownHistoryIds) -eq 0) -Observed ([ordered]@{ malformed_candidate_tokens = $malformedCandidateTokens; duplicate_candidate_ids = $duplicateCandidateIds; unknown_candidate_ids = $unknownCandidateIds; unknown_history_ids = $unknownHistoryIds })
Add-SanityCheck -Checks $sanityChecks -Name 'impression_ids_unique' -Passed ($seenImpressions.Count -eq $behaviorRows) -Observed $seenImpressions.Count
Add-SanityCheck -Checks $sanityChecks -Name 'manifest_matches_eligible_cohort' -Passed ($manifestLineCount -eq $eligibleImpressions -and $viewAccumulators[0].CandidateCount -eq $totalCandidates) -Observed ([ordered]@{ manifest = $manifestLineCount; eligible = $eligibleImpressions; candidates = $totalCandidates })
Add-SanityCheck -Checks $sanityChecks -Name 'streamed_manifest_hash_matches_spool' -Passed ($manifestHashFinalized -and $manifestSha256 -match '^[A-F0-9]{64}$' -and $manifestSha256 -ceq $manifestSpoolSha256) -Observed ([ordered]@{ incremental_sha256 = $manifestSha256; spool_sha256 = $manifestSpoolSha256; exact_line_ending = 'LF' })
Add-SanityCheck -Checks $sanityChecks -Name 'candidate_suffix_never_retained' -Passed ($manifestSuffixLeakLines -eq 0) -Observed ([ordered]@{ manifest_lines_with_candidate_suffix = $manifestSuffixLeakLines; handling = 'validated whole token; retained prefix through final hyphen only' })

$publicationHashes = [ordered]@{}
$publicationHashesMatch = $true
foreach ($inputName in $inputPaths.Keys) {
    $publicationHash = (Get-FileHash -Algorithm SHA256 -LiteralPath ([string] $inputPaths[$inputName])).Hash
    $publicationHashes[$inputName] = $publicationHash
    if ($publicationHash -cne [string] $ExpectedHashes[$inputName] -or $publicationHash -cne [string] $actualHashes[$inputName]) { $publicationHashesMatch = $false }
}
Add-SanityCheck -Checks $sanityChecks -Name 'immutable_inputs_unchanged_before_publication' -Passed $publicationHashesMatch -Observed $publicationHashes
if (-not $publicationHashesMatch) { throw 'An immutable input changed during Phase-A execution; refusing publication.' }

$allSanityPassed = $true
foreach ($check in $sanityChecks) { if (-not $check.passed) { $allSanityPassed = $false; break } }
$primaryMetrics = $viewResults['primary_relation_vocabulary']
$impressionGate = $eligibleImpressions -ge 5000
$userGate = $eligibleUsers.Count -ge 2000
$scoreChangeGate = $null -ne $primaryMetrics.score_vector_changed.rate -and $primaryMetrics.score_vector_changed.rate -ge 0.20
$rankChangeGate = ($null -ne $primaryMetrics.total_order_changed.rate -and $primaryMetrics.total_order_changed.rate -ge 0.05) -or ($null -ne $primaryMetrics.top_min10_set_changed.rate -and $primaryMetrics.top_min10_set_changed.rate -ge 0.02)
$verdict = if (-not $allSanityPassed) { 'INCONCLUSIVE' } elseif ($impressionGate -and $userGate -and $scoreChangeGate -and $rankChangeGate) { 'PASS_COVERAGE_AND_OPEN_LABELS' } else { 'KILL_H6_SHARED_FACT_DIRECTION' }

$result = [ordered]@{
    schema_version = 'h6_phase_a_coverage.v1'
    run_id = $RunId
    classification = 'confirmatory label-blind feasibility gate'
    cutoff_utc = $ExpectedCutoffText
    protocol = [ordered]@{
        sample_size = $SampleSize
        confidence_threshold = $MinimumConfidence
        maximum_history_articles = 50
        score_tolerance = $ScoreTolerance
        tie_rule = 'ascending hexadecimal SHA-256 of 20260807|impression_id|news_id'
        primary_relation_policy = 'properties in frozen MIND relation_embedding.vec vocabulary'
        metadata_blocklist = $MetadataBlocklistIds
        removed_anchor_robustness = $RemovedAnchorIds
        graph_implementation = 'exact sparse anchor coefficients with snapshot-specific 50x50 Gram matrices'
    }
    provenance = [ordered]@{
        runtime_runner = [ordered]@{ path = $runtimeRunnerPath; sha256 = $runtimeRunnerSha256 }
        committed_protocol = [ordered]@{ path = [System.IO.Path]::GetFullPath($protocolPath); sha256 = $committedProtocolSha256 }
        immutable_input_sha256_at_start = $actualHashes
        immutable_input_sha256_before_publication = $publicationHashes
        determinism_validation = 'exact full replay is external; this runner does not assert replay equality'
    }
    inputs = [ordered]@{
        news = [ordered]@{ path = [System.IO.Path]::GetFullPath($NewsPath); sha256 = $actualHashes.news }
        behaviors = [ordered]@{ path = [System.IO.Path]::GetFullPath($BehaviorsPath); sha256 = $actualHashes.behaviors }
        facts = [ordered]@{ path = [System.IO.Path]::GetFullPath($FactsPath); sha256 = $actualHashes.facts }
        entities = [ordered]@{ path = [System.IO.Path]::GetFullPath($EntitiesPath); sha256 = $actualHashes.entities }
        relation_embedding = [ordered]@{ path = [System.IO.Path]::GetFullPath($RelationEmbeddingPath); sha256 = $actualHashes.relations; distinct_relation_ids = $relationIds.Count }
    }
    cohort = [ordered]@{
        behavior_rows = $behaviorRows
        eligible_impressions = $eligibleImpressions
        distinct_users = $eligibleUsers.Count
        candidates = $totalCandidates
        known_news = $newsById.Count
        news_with_sampled_anchor = $newsWithAnchor
        manifest = 'cohort_manifest.jsonl'
        manifest_sha256 = $manifestSha256
        manifest_schema = [ordered]@{
            version = 'h6_phase_a_manifest.compact.v1'
            line_format = 'one compact JSON object followed by LF'
            line_order = 'immutable behaviors.tsv row order, eligible rows only'
            top_level_field_order = [string[]] @('i', 'u', 'h', 'c')
            top_level_fields = [ordered]@{ i = 'impression_id'; u = 'user_id'; h = 'retained last-50 history news IDs in supplied order'; c = 'candidate records in ordinal news_id order' }
            candidate_record = [ordered]@{ n = 'news_id'; v = 'view tuples in view_order' }
            view_order = [string[]] @($views.Name)
            view_tuple_order = [string[]] @('historical_score', 'current_score', 'historical_rank', 'current_rank')
        }
        manifest_contains_candidate_suffix = $manifestSuffixLeakLines -gt 0
    }
    views = $viewResults
    sanity_checks = $sanityChecks.ToArray()
    decision = [ordered]@{
        verdict = $verdict
        all_sanity_checks_passed = $allSanityPassed
        eligible_impressions_gate = $impressionGate
        distinct_users_gate = $userGate
        primary_score_vector_change_gate = $scoreChangeGate
        primary_rank_change_gate = $rankChangeGate
        labels_may_be_opened = $verdict -ceq 'PASS_COVERAGE_AND_OPEN_LABELS'
    }
    artifacts = [ordered]@{ result = 'result.json'; cohort_manifest = 'cohort_manifest.jsonl' }
}

$jsonContent = ($result | ConvertTo-Json -Depth 16 -Compress) + [char] 10
Write-Utf8Fsync -Path (Join-Path $temporaryDirectory 'result.json') -Content $jsonContent
if (-not (Test-SafeRunTemporaryDirectory -Root $OutputRoot -Identifier $RunId -Path $temporaryDirectory)) { throw "Run staging path failed final validation: $temporaryDirectory" }
if ([System.IO.Directory]::Exists($finalDirectory) -or [System.IO.File]::Exists($finalDirectory)) { throw "Result path appeared during computation; refusing to overwrite: $finalDirectory" }
[System.IO.Directory]::Move($temporaryDirectory, $finalDirectory)
$publishedDirectory = $finalDirectory
}
catch {
    if ($null -ne $manifestStream) { $manifestStream.Dispose() }
    if ($null -ne $manifestHasher) { $manifestHasher.Dispose() }
    if ([System.IO.Directory]::Exists($temporaryDirectory)) { Remove-SafeRunTemporaryDirectory -Root $OutputRoot -Identifier $RunId -Path $temporaryDirectory }
    throw
}
Write-Output ('H6_PHASE_A_COMPLETE ' + ([ordered]@{ run_id = $RunId; verdict = $verdict; eligible_impressions = $eligibleImpressions; distinct_users = $eligibleUsers.Count; manifest_sha256 = $manifestSha256; result_directory = $publishedDirectory } | ConvertTo-Json -Compress))
