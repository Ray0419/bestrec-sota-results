#requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter()]
    [string] $NewsPath = 'C:\Users\rayxc\Documents\R\experiments\kg_launch_autoresearch\data\MINDsmall_dev\MINDsmall_dev\news.tsv',

    [Parameter()]
    [string] $BehaviorsPath = 'C:\Users\rayxc\Documents\R\experiments\kg_launch_autoresearch\data\MINDsmall_dev\MINDsmall_dev\behaviors.tsv',

    [Parameter()]
    [string] $OutputRoot = 'C:\Users\rayxc\Documents\R\experiments\kg_launch_autoresearch\experiments\h5_bitemporal_drift\results',

    [Parameter()]
    [switch] $SelfTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$RunId = 'run_001'
$SampleSize = 50
$MinimumConfidence = 0.90
$ExpectedCutoffText = '2019-11-15T23:58:03Z'
$CurrentOnlyGate = 0.15
$AffectedNewsGate = 0.50
$InvariantCulture = [System.Globalization.CultureInfo]::InvariantCulture
$Ordinal = [System.StringComparer]::Ordinal
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$UserAgent = 'ProviCold-H5/0.1 (academic structural POC; sequential requests)'

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

function Test-JsonProperty {
    param(
        [AllowNull()][object] $Object,
        [Parameter(Mandatory = $true)][string] $Name
    )
    return $null -ne $Object -and $null -ne $Object.PSObject.Properties[$Name]
}

function New-StringSet {
    return ,(New-Object 'System.Collections.Generic.HashSet[string]' ($Ordinal))
}

function Get-NewsQidSet {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyString()][string] $Line,
        [Parameter(Mandatory = $true)][ref] $FieldFailureReference,
        [Parameter(Mandatory = $true)][ref] $EntityJsonFailureReference
    )

    $result = New-StringSet
    $parts = $Line -split "`t", 8
    if ($parts.Count -ne 8) {
        $FieldFailureReference.Value = [long] $FieldFailureReference.Value + 1
        return ,$result
    }

    foreach ($columnIndex in 6, 7) {
        try {
            $entities = $parts[$columnIndex] | ConvertFrom-Json -ErrorAction Stop
        }
        catch {
            $EntityJsonFailureReference.Value = [long] $EntityJsonFailureReference.Value + 1
            continue
        }
        foreach ($entity in @($entities)) {
            if ($null -eq $entity) { continue }
            $qidValue = Get-JsonPropertyValue -Object $entity -Name 'WikidataId'
            $confidenceValue = Get-JsonPropertyValue -Object $entity -Name 'Confidence'
            if ($null -eq $qidValue -or $null -eq $confidenceValue) { continue }
            $qid = [System.Convert]::ToString($qidValue, $InvariantCulture).Trim()
            if ($qid -notmatch '^Q[1-9][0-9]*$') { continue }
            [double] $confidence = 0.0
            $confidenceText = [System.Convert]::ToString($confidenceValue, $InvariantCulture)
            if (-not [double]::TryParse($confidenceText, [System.Globalization.NumberStyles]::Float, $InvariantCulture, [ref] $confidence)) { continue }
            if ($confidence -ge $MinimumConfidence) {
                $null = $result.Add($qid)
            }
        }
    }
    return ,$result
}

function Read-NewsEntityCounts {
    param([Parameter(Mandatory = $true)][string] $Path)

    $counts = New-Object 'System.Collections.Generic.Dictionary[string,long]' ($Ordinal)
    [long] $rawLines = 0
    [long] $fieldFailures = 0
    [long] $entityJsonFailures = 0
    [long] $linkedRows = 0
    $reader = New-Object System.IO.StreamReader($Path, $Utf8NoBom, $true, 1048576)
    try {
        while (-not $reader.EndOfStream) {
            $line = $reader.ReadLine()
            $rawLines++
            $qids = Get-NewsQidSet -Line $line -FieldFailureReference ([ref] $fieldFailures) -EntityJsonFailureReference ([ref] $entityJsonFailures)
            if ($qids.Count -gt 0) { $linkedRows++ }
            foreach ($qid in $qids) {
                if ($counts.ContainsKey($qid)) { $counts[$qid]++ } else { $counts.Add($qid, 1) }
            }
        }
    }
    finally {
        $reader.Dispose()
    }
    return [pscustomobject]@{
        Counts = $counts
        Stats = [ordered]@{
            raw_lines = $rawLines
            field_count_failures = $fieldFailures
            entity_json_failures = $entityJsonFailures
            confidence_linked_news_rows = $linkedRows
            distinct_eligible_qids = $counts.Count
        }
    }
}

function Select-TopQids {
    param(
        [Parameter(Mandatory = $true)][System.Collections.Generic.Dictionary[string,long]] $Counts,
        [Parameter(Mandatory = $true)][int] $Count
    )

    $buckets = New-Object 'System.Collections.Generic.SortedDictionary[long,object]'
    foreach ($entry in $Counts.GetEnumerator()) {
        if (-not $buckets.ContainsKey([long] $entry.Value)) {
            $buckets.Add([long] $entry.Value, (New-Object 'System.Collections.Generic.List[string]'))
        }
        $buckets[[long] $entry.Value].Add([string] $entry.Key)
    }
    $frequencies = [long[]] @($buckets.Keys)
    [array]::Reverse($frequencies)
    $selected = New-Object 'System.Collections.Generic.List[object]'
    foreach ($frequency in $frequencies) {
        $ids = $buckets[$frequency].ToArray()
        [array]::Sort($ids, $Ordinal)
        foreach ($qid in $ids) {
            if ($selected.Count -ge $Count) { break }
            $selected.Add([pscustomobject]@{ qid = $qid; news_frequency = [long] $frequency })
        }
        if ($selected.Count -ge $Count) { break }
    }
    return $selected.ToArray()
}

function Read-BehaviorCutoff {
    param([Parameter(Mandatory = $true)][string] $Path)

    [long] $rawLines = 0
    [long] $fieldFailures = 0
    [long] $timeFailures = 0
    $minimum = [datetime]::MaxValue
    $maximum = [datetime]::MinValue
    $styles = [System.Globalization.DateTimeStyles]::AssumeUniversal -bor [System.Globalization.DateTimeStyles]::AdjustToUniversal
    $reader = New-Object System.IO.StreamReader($Path, $Utf8NoBom, $true, 1048576)
    try {
        while (-not $reader.EndOfStream) {
            $parts = $reader.ReadLine() -split "`t", 5
            $rawLines++
            if ($parts.Count -ne 5) {
                $fieldFailures++
                continue
            }
            $parsed = [datetime]::MinValue
            if (-not [datetime]::TryParseExact($parts[2], 'M/d/yyyy h:mm:ss tt', $InvariantCulture, $styles, [ref] $parsed)) {
                $timeFailures++
                continue
            }
            if ($parsed -lt $minimum) { $minimum = $parsed }
            if ($parsed -gt $maximum) { $maximum = $parsed }
        }
    }
    finally {
        $reader.Dispose()
    }
    return [pscustomobject]@{
        Minimum = $minimum
        Maximum = $maximum
        Stats = [ordered]@{
            raw_lines = $rawLines
            field_count_failures = $fieldFailures
            timestamp_failures = $timeFailures
        }
    }
}

function Invoke-WikidataJson {
    param([Parameter(Mandatory = $true)][string] $Uri)

    $lastMessage = $null
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            $headers = @{ 'User-Agent' = $UserAgent }
            $data = Invoke-RestMethod -Uri $Uri -Headers $headers -Method Get -TimeoutSec 45 -ErrorAction Stop
            return [pscustomobject]@{ success = $true; attempts = $attempt; data = $data; error = $null }
        }
        catch {
            $lastMessage = $_.Exception.Message
            if ($attempt -lt 3) { Start-Sleep -Seconds $attempt }
        }
    }
    return [pscustomobject]@{ success = $false; attempts = 3; data = $null; error = $lastMessage }
}

function Get-DirectEntityFactSet {
    param([AllowNull()][object] $Entity)

    $facts = New-StringSet
    $claims = Get-JsonPropertyValue -Object $Entity -Name 'claims'
    if ($null -eq $claims) { return ,$facts }
    foreach ($property in $claims.PSObject.Properties) {
        $propertyId = [string] $property.Name
        if ($propertyId -notmatch '^P[1-9][0-9]*$') { continue }
        foreach ($statement in @($property.Value)) {
            if ($null -eq $statement) { continue }
            $rank = Get-JsonPropertyValue -Object $statement -Name 'rank'
            if ($null -ne $rank -and [string] $rank -eq 'deprecated') { continue }
            $mainsnak = Get-JsonPropertyValue -Object $statement -Name 'mainsnak'
            if ([string] (Get-JsonPropertyValue -Object $mainsnak -Name 'snaktype') -ne 'value') { continue }
            $dataValue = Get-JsonPropertyValue -Object $mainsnak -Name 'datavalue'
            if ([string] (Get-JsonPropertyValue -Object $dataValue -Name 'type') -ne 'wikibase-entityid') { continue }
            $value = Get-JsonPropertyValue -Object $dataValue -Name 'value'
            $numericValue = Get-JsonPropertyValue -Object $value -Name 'numeric-id'
            [long] $numericId = 0
            if ($null -eq $numericValue -or -not [long]::TryParse([string] $numericValue, [System.Globalization.NumberStyles]::Integer, $InvariantCulture, [ref] $numericId)) { continue }
            if ($numericId -le 0) { continue }
            $null = $facts.Add($propertyId + '|Q' + [string] $numericId)
        }
    }
    return ,$facts
}

function Get-SortedDifference {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.HashSet[string]] $Left,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.HashSet[string]] $Right
    )
    $values = New-Object 'System.Collections.Generic.List[string]'
    foreach ($value in $Left) {
        if (-not $Right.Contains($value)) { $values.Add($value) }
    }
    $array = $values.ToArray()
    [array]::Sort($array, $Ordinal)
    return $array
}

function Get-SortedSetValues {
    param([Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.HashSet[string]] $Set)
    $array = [string[]] @($Set)
    [array]::Sort($array, $Ordinal)
    return $array
}

function Get-Jaccard {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.HashSet[string]] $First,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.HashSet[string]] $Second
    )
    [long] $intersection = 0
    foreach ($value in $First) { if ($Second.Contains($value)) { $intersection++ } }
    [long] $union = $First.Count + $Second.Count - $intersection
    if ($union -eq 0) { return 1.0 }
    return [double] $intersection / $union
}

function Get-Median {
    param([Parameter(Mandatory = $true)][AllowEmptyCollection()][int[]] $Values)
    if ($Values.Length -eq 0) { return $null }
    [array]::Sort($Values)
    $middle = [int] [math]::Floor($Values.Length / 2.0)
    if (($Values.Length % 2) -eq 1) { return [double] $Values[$middle] }
    return ([double] $Values[$middle - 1] + [double] $Values[$middle]) / 2.0
}

function Measure-AffectedNews {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][System.Collections.Generic.HashSet[string]] $Selected,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.HashSet[string]] $Affected
    )
    [long] $rawLines = 0
    [long] $fieldFailures = 0
    [long] $entityJsonFailures = 0
    [long] $selectedNews = 0
    [long] $affectedNews = 0
    $reader = New-Object System.IO.StreamReader($Path, $Utf8NoBom, $true, 1048576)
    try {
        while (-not $reader.EndOfStream) {
            $line = $reader.ReadLine()
            $rawLines++
            $qids = Get-NewsQidSet -Line $line -FieldFailureReference ([ref] $fieldFailures) -EntityJsonFailureReference ([ref] $entityJsonFailures)
            $hasSelected = $false
            $hasAffected = $false
            foreach ($qid in $qids) {
                if ($Selected.Contains($qid)) { $hasSelected = $true }
                if ($Affected.Contains($qid)) { $hasAffected = $true }
            }
            if ($hasSelected) {
                $selectedNews++
                if ($hasAffected) { $affectedNews++ }
            }
        }
    }
    finally {
        $reader.Dispose()
    }
    return [pscustomobject]@{
        raw_lines = $rawLines
        field_count_failures = $fieldFailures
        entity_json_failures = $entityJsonFailures
        selected_news = $selectedNews
        affected_news = $affectedNews
        affected_rate = if ($selectedNews -gt 0) { [double] $affectedNews / $selectedNews } else { $null }
    }
}

function Add-SanityCheck {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.List[object]] $Checks,
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][bool] $Passed,
        [AllowNull()][object] $Observed
    )
    $Checks.Add([pscustomobject]@{ name = $Name; passed = $Passed; observed = $Observed })
}

function Write-Utf8Fsync {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Content
    )
    $stream = New-Object System.IO.FileStream($Path, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None, 1048576, [System.IO.FileOptions]::WriteThrough)
    try {
        $bytes = $Utf8NoBom.GetBytes($Content)
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    }
    finally {
        $stream.Dispose()
    }
}

function Get-Sha256Text {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string] $Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { return ([System.BitConverter]::ToString($sha.ComputeHash($Utf8NoBom.GetBytes($Text)))).Replace('-', '') }
    finally { $sha.Dispose() }
}

if ($SelfTest) {
    $syntheticJson = '{"claims":{"P31":[{"rank":"normal","mainsnak":{"snaktype":"value","datavalue":{"type":"wikibase-entityid","value":{"numeric-id":5}}}}],"P279":[{"rank":"deprecated","mainsnak":{"snaktype":"value","datavalue":{"type":"wikibase-entityid","value":{"numeric-id":1}}}}],"P18":[{"rank":"normal","mainsnak":{"snaktype":"value","datavalue":{"type":"string","value":"x"}}}]}}'
    $synthetic = $syntheticJson | ConvertFrom-Json -ErrorAction Stop
    $facts = Get-DirectEntityFactSet -Entity $synthetic
    if ($facts.Count -ne 1 -or -not $facts.Contains('P31|Q5')) { throw 'Self-test fact extraction failed.' }
    $historical = New-StringSet
    $null = $historical.Add('P31|Q5')
    $null = $facts.Add('P17|Q30')
    $difference = [string[]] @(Get-SortedDifference -Left $facts -Right $historical)
    if ($difference.Length -ne 1 -or $difference[0] -ne 'P17|Q30') { throw 'Self-test set difference failed.' }
    [long] $fieldFailures = 0
    [long] $jsonFailures = 0
    $line = "N1`tcat`tsub`tTitle`tAbstract`thttps://example.test`t[{`"WikidataId`":`"Q5`",`"Confidence`":0.95}]`t[]"
    $qids = Get-NewsQidSet -Line $line -FieldFailureReference ([ref] $fieldFailures) -EntityJsonFailureReference ([ref] $jsonFailures)
    if ($qids.Count -ne 1 -or -not $qids.Contains('Q5') -or $fieldFailures -ne 0 -or $jsonFailures -ne 0) { throw 'Self-test MIND parsing failed.' }
    Write-Output 'H5_SELFTEST_OK'
    exit 0
}

if (-not [System.IO.File]::Exists($NewsPath)) { throw "News input does not exist: $NewsPath" }
if (-not [System.IO.File]::Exists($BehaviorsPath)) { throw "Behaviors input does not exist: $BehaviorsPath" }
$finalDirectory = Join-Path $OutputRoot $RunId
if ([System.IO.Directory]::Exists($finalDirectory) -or [System.IO.File]::Exists($finalDirectory)) { throw "Refusing to overwrite existing result path: $finalDirectory" }

$newsRead = Read-NewsEntityCounts -Path $NewsPath
$behaviorRead = Read-BehaviorCutoff -Path $BehaviorsPath
$selectedRows = [object[]] @(Select-TopQids -Counts $newsRead.Counts -Count $SampleSize)
$selectedSet = New-StringSet
foreach ($row in $selectedRows) { $null = $selectedSet.Add([string] $row.qid) }
$sampleLines = New-Object 'System.Collections.Generic.List[string]'
foreach ($row in $selectedRows) { $sampleLines.Add(([string] $row.qid) + "`t" + ([string] $row.news_frequency)) }
$sampleSha256 = Get-Sha256Text -Text ([string]::Join("`n", $sampleLines.ToArray()))

$cutoff = $behaviorRead.Maximum
$cutoffText = $cutoff.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ', $InvariantCulture)
$requestStartedUtc = [datetime]::UtcNow
$joinedIds = [string]::Join('|', [string[]] @($selectedRows | ForEach-Object { $_.qid }))
$currentUri = 'https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&formatversion=2&ids=' + [uri]::EscapeDataString($joinedIds) + '&props=info%7Cclaims'
$currentRequest = Invoke-WikidataJson -Uri $currentUri
$currentEntities = if ($currentRequest.success) { Get-JsonPropertyValue -Object $currentRequest.data -Name 'entities' } else { $null }

$entityLedgers = New-Object 'System.Collections.Generic.List[object]'
$entityCsvRows = New-Object 'System.Collections.Generic.List[object]'
$affectedSet = New-StringSet
$apiErrors = New-Object 'System.Collections.Generic.List[string]'
if (-not $currentRequest.success) { $apiErrors.Add('current_batch: ' + [string] $currentRequest.error) }

[double] $weightedCurrentFacts = 0.0
[double] $weightedCurrentOnlyFacts = 0.0
[double] $weightedHistoricalFacts = 0.0
[double] $weightedHistoricalOnlyFacts = 0.0
[long] $currentEntitiesFound = 0
[long] $historicalQueriesResolved = 0
[long] $historicallyAbsentCount = 0
$currentOnlyCounts = New-Object 'System.Collections.Generic.List[int]'

foreach ($sampleRow in $selectedRows) {
    $qid = [string] $sampleRow.qid
    $frequency = [long] $sampleRow.news_frequency
    $currentEntity = if ($null -ne $currentEntities) { Get-JsonPropertyValue -Object $currentEntities -Name $qid } else { $null }
    $currentOk = $null -ne $currentEntity -and -not (Test-JsonProperty -Object $currentEntity -Name 'missing')
    if ($currentOk) { $currentEntitiesFound++ }
    $currentFacts = if ($currentOk) { Get-DirectEntityFactSet -Entity $currentEntity } else { New-StringSet }
    $currentRevision = if ($currentOk) { Get-JsonPropertyValue -Object $currentEntity -Name 'lastrevid' } else { $null }
    $currentModified = if ($currentOk) { Get-JsonPropertyValue -Object $currentEntity -Name 'modified' } else { $null }

    $historicalUri = 'https://www.wikidata.org/w/api.php?action=query&format=json&formatversion=2&prop=revisions&titles=' + [uri]::EscapeDataString($qid) + '&rvprop=ids%7Ctimestamp%7Ccontent&rvslots=main&rvstart=' + [uri]::EscapeDataString($cutoffText) + '&rvdir=older&rvlimit=1'
    $historicalRequest = Invoke-WikidataJson -Uri $historicalUri
    $historicalFacts = New-StringSet
    $historicalRevision = $null
    $historicalTimestamp = $null
    $historicalAbsent = $false
    $historicalOk = $false
    $rowError = $null
    if (-not $historicalRequest.success) {
        $rowError = [string] $historicalRequest.error
        $apiErrors.Add($qid + ': ' + $rowError)
    }
    else {
        try {
            $query = Get-JsonPropertyValue -Object $historicalRequest.data -Name 'query'
            $pages = @(Get-JsonPropertyValue -Object $query -Name 'pages')
            if ($pages.Count -ne 1 -or $null -eq $pages[0]) { throw 'Historical query did not return exactly one page.' }
            $revisionsValue = Get-JsonPropertyValue -Object $pages[0] -Name 'revisions'
            $revisions = @($revisionsValue)
            if ($null -eq $revisionsValue -or $revisions.Count -eq 0) {
                $historicalAbsent = $true
                $historicallyAbsentCount++
                $historicalOk = $true
            }
            else {
                $revision = $revisions[0]
                $historicalRevision = Get-JsonPropertyValue -Object $revision -Name 'revid'
                $historicalTimestamp = Get-JsonPropertyValue -Object $revision -Name 'timestamp'
                $slots = Get-JsonPropertyValue -Object $revision -Name 'slots'
                $mainSlot = Get-JsonPropertyValue -Object $slots -Name 'main'
                $content = Get-JsonPropertyValue -Object $mainSlot -Name 'content'
                if ($null -eq $content) { throw 'Historical revision has no main-slot content.' }
                $historicalEntity = ([string] $content) | ConvertFrom-Json -ErrorAction Stop
                $historicalFacts = Get-DirectEntityFactSet -Entity $historicalEntity
                $historicalOk = $true
            }
            $historicalQueriesResolved++
        }
        catch {
            $rowError = $_.Exception.Message
            $apiErrors.Add($qid + ' parse: ' + $rowError)
        }
    }

    $currentOnly = [string[]] @(Get-SortedDifference -Left $currentFacts -Right $historicalFacts)
    $historicalOnly = [string[]] @(Get-SortedDifference -Left $historicalFacts -Right $currentFacts)
    $currentFactArray = [string[]] @(Get-SortedSetValues -Set $currentFacts)
    $historicalFactArray = [string[]] @(Get-SortedSetValues -Set $historicalFacts)
    $jaccard = Get-Jaccard -First $currentFacts -Second $historicalFacts
    if ($currentOk -and $historicalOk) {
        $weightedCurrentFacts += [double] $frequency * $currentFacts.Count
        $weightedCurrentOnlyFacts += [double] $frequency * $currentOnly.Length
        $weightedHistoricalFacts += [double] $frequency * $historicalFacts.Count
        $weightedHistoricalOnlyFacts += [double] $frequency * $historicalOnly.Length
        $currentOnlyCounts.Add([int] $currentOnly.Length)
        if ($currentOnly.Length -gt 0) { $null = $affectedSet.Add($qid) }
    }

    $ledger = [ordered]@{
        qid = $qid
        news_frequency = $frequency
        api_ok = $currentOk -and $historicalOk
        error = $rowError
        current = [ordered]@{
            revision_id = $currentRevision
            modified_utc = $currentModified
            facts = $currentFactArray
        }
        historical = [ordered]@{
            absent_at_cutoff = $historicalAbsent
            revision_id = $historicalRevision
            revision_timestamp_utc = $historicalTimestamp
            facts = $historicalFactArray
        }
        comparison = [ordered]@{
            current_only = $currentOnly
            historical_only = $historicalOnly
            jaccard = $jaccard
        }
    }
    $entityLedgers.Add([pscustomobject] $ledger)
    $entityCsvRows.Add([pscustomobject]@{
        qid = $qid
        news_frequency = $frequency
        api_ok = $currentOk -and $historicalOk
        current_revision = $currentRevision
        current_modified_utc = $currentModified
        historical_absent_at_cutoff = $historicalAbsent
        historical_revision = $historicalRevision
        historical_revision_timestamp_utc = $historicalTimestamp
        current_fact_count = $currentFacts.Count
        historical_fact_count = $historicalFacts.Count
        current_only_count = $currentOnly.Length
        historical_only_count = $historicalOnly.Length
        jaccard = $jaccard
        error = $rowError
    })
}
$requestCompletedUtc = [datetime]::UtcNow

$newsExposure = Measure-AffectedNews -Path $NewsPath -Selected $selectedSet -Affected $affectedSet
$weightedCurrentOnlyFraction = if ($weightedCurrentFacts -gt 0) { $weightedCurrentOnlyFacts / $weightedCurrentFacts } else { $null }
$weightedHistoricalOnlyFraction = if ($weightedHistoricalFacts -gt 0) { $weightedHistoricalOnlyFacts / $weightedHistoricalFacts } else { $null }
$currentOnlyArray = $currentOnlyCounts.ToArray()
$meanCurrentOnly = if ($currentOnlyArray.Length -gt 0) { [double] (($currentOnlyArray | Measure-Object -Sum).Sum) / $currentOnlyArray.Length } else { $null }
$medianCurrentOnly = Get-Median -Values $currentOnlyArray

$sanityChecks = New-Object 'System.Collections.Generic.List[object]'
Add-SanityCheck -Checks $sanityChecks -Name 'behavior_cutoff_matches_lock' -Passed ($cutoffText -eq $ExpectedCutoffText) -Observed $cutoffText
Add-SanityCheck -Checks $sanityChecks -Name 'behavior_rows_parse_cleanly' -Passed (($behaviorRead.Stats.field_count_failures + $behaviorRead.Stats.timestamp_failures) -eq 0) -Observed $behaviorRead.Stats
Add-SanityCheck -Checks $sanityChecks -Name 'news_rows_parse_cleanly_both_passes' -Passed (($newsRead.Stats.field_count_failures + $newsRead.Stats.entity_json_failures + $newsExposure.field_count_failures + $newsExposure.entity_json_failures) -eq 0) -Observed ([ordered]@{ first = $newsRead.Stats; second_field_failures = $newsExposure.field_count_failures; second_json_failures = $newsExposure.entity_json_failures })
Add-SanityCheck -Checks $sanityChecks -Name 'news_pass_row_counts_match' -Passed ($newsRead.Stats.raw_lines -eq $newsExposure.raw_lines) -Observed ([ordered]@{ first = $newsRead.Stats.raw_lines; second = $newsExposure.raw_lines })
Add-SanityCheck -Checks $sanityChecks -Name 'sample_has_exactly_50_unique_qids' -Passed ($selectedRows.Length -eq $SampleSize -and $selectedSet.Count -eq $SampleSize) -Observed ([ordered]@{ rows = $selectedRows.Length; unique = $selectedSet.Count })
Add-SanityCheck -Checks $sanityChecks -Name 'all_current_entities_returned' -Passed ($currentEntitiesFound -eq $SampleSize) -Observed $currentEntitiesFound
Add-SanityCheck -Checks $sanityChecks -Name 'all_historical_queries_resolved' -Passed ($historicalQueriesResolved -eq $SampleSize) -Observed $historicalQueriesResolved
Add-SanityCheck -Checks $sanityChecks -Name 'no_api_or_snapshot_parse_errors' -Passed ($apiErrors.Count -eq 0) -Observed $apiErrors.ToArray()
Add-SanityCheck -Checks $sanityChecks -Name 'weighted_current_fact_denominator_positive' -Passed ($weightedCurrentFacts -gt 0) -Observed $weightedCurrentFacts
Add-SanityCheck -Checks $sanityChecks -Name 'selected_news_denominator_positive' -Passed ($newsExposure.selected_news -gt 0) -Observed $newsExposure.selected_news

$allSanityPassed = $true
foreach ($check in $sanityChecks) { if (-not $check.passed) { $allSanityPassed = $false; break } }
$currentOnlyGatePassed = $null -ne $weightedCurrentOnlyFraction -and $weightedCurrentOnlyFraction -ge $CurrentOnlyGate
$affectedNewsGatePassed = $null -ne $newsExposure.affected_rate -and $newsExposure.affected_rate -ge $AffectedNewsGate
$verdict = if (-not $allSanityPassed) {
    'INCONCLUSIVE'
}
elseif ($currentOnlyGatePassed -and $affectedNewsGatePassed) {
    'ADVANCE_H5_TO_OUTCOME_POC'
}
else {
    'REFUTE_H5_AS_MAIN_DIRECTION'
}

$sampleOutput = New-Object 'System.Collections.Generic.List[object]'
foreach ($row in $selectedRows) { $sampleOutput.Add([pscustomobject]@{ qid = $row.qid; news_frequency = $row.news_frequency }) }
$result = [ordered]@{
    schema_version = 'h5_bitemporal_drift.v1'
    run_id = $RunId
    dataset = 'MIND-small development'
    cutoff_utc = $cutoffText
    protocol = [ordered]@{
        sample_size = $SampleSize
        minimum_entity_link_confidence = $MinimumConfidence
        fact_signature = 'nondeprecated direct entity-valued property_id|Qtarget'
        weighted_current_only_gate = $CurrentOnlyGate
        affected_selected_news_gate = $AffectedNewsGate
    }
    inputs = [ordered]@{
        news = [System.IO.Path]::GetFullPath($NewsPath)
        behaviors = [System.IO.Path]::GetFullPath($BehaviorsPath)
        mind_archive_sha256 = 'B315CDE1C9B9D45008B5A7C4B2E1F87647659F09F74892AE3899C0005D5D6155'
        news_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $NewsPath).Hash
        behaviors_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $BehaviorsPath).Hash
    }
    parsing = [ordered]@{
        news = $newsRead.Stats
        behaviors = $behaviorRead.Stats
        minimum_behavior_utc = $behaviorRead.Minimum.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ', $InvariantCulture)
        maximum_behavior_utc = $cutoffText
    }
    sample = [ordered]@{
        selection_sha256 = $sampleSha256
        qids = $sampleOutput.ToArray()
        selected_news = $newsExposure.selected_news
    }
    api = [ordered]@{
        request_started_utc = $requestStartedUtc.ToString('o', $InvariantCulture)
        request_completed_utc = $requestCompletedUtc.ToString('o', $InvariantCulture)
        current_batch_attempts = $currentRequest.attempts
        current_entities_found = $currentEntitiesFound
        historical_queries_resolved = $historicalQueriesResolved
        historically_absent_entities = $historicallyAbsentCount
        errors = $apiErrors.ToArray()
    }
    metrics = [ordered]@{
        primary = [ordered]@{
            weighted_current_only_edge_fraction = $weightedCurrentOnlyFraction
            affected_selected_news_rate = $newsExposure.affected_rate
        }
        counts = [ordered]@{
            weighted_current_fact_mass = $weightedCurrentFacts
            weighted_current_only_fact_mass = $weightedCurrentOnlyFacts
            selected_news = $newsExposure.selected_news
            affected_selected_news = $newsExposure.affected_news
        }
        secondary = [ordered]@{
            entities_with_current_only_fact = $affectedSet.Count
            entity_any_current_only_rate = if ($SampleSize -gt 0) { [double] $affectedSet.Count / $SampleSize } else { $null }
            mean_current_only_facts = $meanCurrentOnly
            median_current_only_facts = $medianCurrentOnly
            weighted_historical_only_edge_fraction = $weightedHistoricalOnlyFraction
        }
    }
    sanity_checks = $sanityChecks.ToArray()
    decision = [ordered]@{
        verdict = $verdict
        all_sanity_checks_passed = $allSanityPassed
        weighted_current_only_gate_passed = $currentOnlyGatePassed
        affected_selected_news_gate_passed = $affectedNewsGatePassed
    }
    artifacts = [ordered]@{
        result = 'result.json'
        entity_summary = 'entities.csv'
        fact_ledger = 'facts.jsonl'
    }
}

$jsonContent = ($result | ConvertTo-Json -Depth 20 -Compress) + [Environment]::NewLine
$csvLines = @($entityCsvRows.ToArray() | ConvertTo-Csv -NoTypeInformation)
$csvContent = [string]::Join([Environment]::NewLine, $csvLines) + [Environment]::NewLine
$factLines = New-Object 'System.Collections.Generic.List[string]'
foreach ($ledger in $entityLedgers) { $factLines.Add(($ledger | ConvertTo-Json -Depth 16 -Compress)) }
$factsContent = [string]::Join([Environment]::NewLine, $factLines.ToArray()) + [Environment]::NewLine

[System.IO.Directory]::CreateDirectory($OutputRoot) | Out-Null
if ([System.IO.Directory]::Exists($finalDirectory) -or [System.IO.File]::Exists($finalDirectory)) { throw "Result path appeared during computation; refusing to overwrite: $finalDirectory" }
$temporaryDirectory = Join-Path $OutputRoot ('.' + $RunId + '.tmp.' + [guid]::NewGuid().ToString('N'))
[System.IO.Directory]::CreateDirectory($temporaryDirectory) | Out-Null
Write-Utf8Fsync -Path (Join-Path $temporaryDirectory 'result.json') -Content $jsonContent
Write-Utf8Fsync -Path (Join-Path $temporaryDirectory 'entities.csv') -Content $csvContent
Write-Utf8Fsync -Path (Join-Path $temporaryDirectory 'facts.jsonl') -Content $factsContent
[System.IO.Directory]::Move($temporaryDirectory, $finalDirectory)

Write-Output ('H5_COMPLETE ' + ([ordered]@{
    run_id = $RunId
    verdict = $verdict
    weighted_current_only_edge_fraction = $weightedCurrentOnlyFraction
    affected_selected_news_rate = $newsExposure.affected_rate
    result_directory = $finalDirectory
} | ConvertTo-Json -Compress))
