#requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter()]
    [string] $MetadataPath = 'C:\Users\rayxc\Documents\R\data_raw_proper\digital_music\meta_Digital_Music.jsonl',

    [Parameter()]
    [string] $InteractionsPath = 'C:\Users\rayxc\Documents\R\data_raw_proper\digital_music\Digital_Music.jsonl',

    [Parameter()]
    [string] $OutputRoot = 'C:\Users\rayxc\Documents\R\experiments\kg_launch_autoresearch\experiments\h1_launch_support\results'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$RunId = 'run_002'
$RandomSeed = 20260807
$Relations = [string[]] @('store', 'manufacturer', 'label', 'brand', 'category', 'feature')
$AttributeSeparator = [char] 0x1f
$InvariantCulture = [System.Globalization.CultureInfo]::InvariantCulture
$Ordinal = [System.StringComparer]::Ordinal
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Get-JsonPropertyValue {
    param(
        [AllowNull()]
        [object] $Object,
        [Parameter(Mandatory = $true)]
        [string] $Name
    )

    if ($null -eq $Object) {
        return $null
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }
    return $property.Value
}

function ConvertTo-NormalizedAttributeValue {
    param([AllowNull()][object] $Value)

    if ($null -eq $Value) {
        return $null
    }
    if ($Value -isnot [string]) {
        return $null
    }
    $text = [System.Convert]::ToString($Value, $InvariantCulture)
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $null
    }
    $text = [System.Text.RegularExpressions.Regex]::Replace($text.Trim(), '\s+', ' ')
    if ($text.Length -eq 0) {
        return $null
    }
    return $text.ToLowerInvariant()
}

function Add-AttributeValues {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [System.Collections.Generic.HashSet[string]] $Target,
        [Parameter(Mandatory = $true)]
        [string] $Relation,
        [AllowNull()]
        [object] $Value
    )

    if ($null -eq $Value) {
        return
    }
    if ($Value -is [string]) {
        $normalized = ConvertTo-NormalizedAttributeValue -Value $Value
        if ($null -ne $normalized) {
            $null = $Target.Add($Relation + $AttributeSeparator + $normalized)
        }
        return
    }
    if ($Value -is [System.Collections.IEnumerable]) {
        foreach ($element in $Value) {
            Add-AttributeValues -Target $Target -Relation $Relation -Value $element
        }
    }
}

function ConvertTo-ListingDateUtc {
    param([AllowNull()][object] $Value)

    if ($null -eq $Value) {
        return $null
    }
    $text = [System.Convert]::ToString($Value, $InvariantCulture)
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $null
    }
    $parsed = [datetime]::MinValue
    $styles = [System.Globalization.DateTimeStyles]::AllowWhiteSpaces -bor
        [System.Globalization.DateTimeStyles]::AssumeUniversal -bor
        [System.Globalization.DateTimeStyles]::AdjustToUniversal
    if (-not [datetime]::TryParse($text, $InvariantCulture, $styles, [ref] $parsed)) {
        return $null
    }
    return [datetime]::SpecifyKind($parsed.Date, [System.DateTimeKind]::Utc)
}

function Read-MetadataStream {
    param([Parameter(Mandatory = $true)][string] $Path)

    $items = New-Object 'System.Collections.Generic.Dictionary[string,object]' ($Ordinal)
    [long] $rawLines = 0
    [long] $parsedLines = 0
    [long] $parseFailures = 0
    [long] $missingItemKeys = 0
    [long] $duplicateRows = 0
    [long] $missingListingDates = 0
    [long] $unparsableListingDates = 0

    $reader = New-Object System.IO.StreamReader($Path, $Utf8NoBom, $true, 1048576)
    try {
        while (-not $reader.EndOfStream) {
            $line = $reader.ReadLine()
            $rawLines++
            try {
                $record = $line | ConvertFrom-Json -ErrorAction Stop
                $parsedLines++
            }
            catch {
                $parseFailures++
                continue
            }

            $itemValue = Get-JsonPropertyValue -Object $record -Name 'parent_asin'
            $itemId = if ($null -eq $itemValue) { '' } else { [System.Convert]::ToString($itemValue, $InvariantCulture).Trim() }
            if ($itemId.Length -eq 0) {
                $missingItemKeys++
                continue
            }

            if ($items.ContainsKey($itemId)) {
                $item = $items[$itemId]
                $duplicateRows++
            }
            else {
                $item = [pscustomobject]@{
                    Id                 = $itemId
                    ListingDateUtc     = $null
                    Attributes         = New-Object 'System.Collections.Generic.HashSet[string]' ($Ordinal)
                    InteractionCount   = 0
                    AtOrBeforeCount    = 0
                    AfterCount         = 0
                    UniverseIndex      = -1
                }
                $items.Add($itemId, $item)
            }

            $details = Get-JsonPropertyValue -Object $record -Name 'details'
            $dateValue = Get-JsonPropertyValue -Object $details -Name 'Date First Available'
            if ($null -eq $dateValue -or [string]::IsNullOrWhiteSpace([System.Convert]::ToString($dateValue, $InvariantCulture))) {
                $missingListingDates++
            }
            else {
                $listingDate = ConvertTo-ListingDateUtc -Value $dateValue
                if ($null -eq $listingDate) {
                    $unparsableListingDates++
                }
                elseif ($null -eq $item.ListingDateUtc -or $listingDate -lt $item.ListingDateUtc) {
                    $item.ListingDateUtc = $listingDate
                }
            }

            Add-AttributeValues -Target $item.Attributes -Relation 'store' -Value (Get-JsonPropertyValue -Object $record -Name 'store')
            Add-AttributeValues -Target $item.Attributes -Relation 'manufacturer' -Value (Get-JsonPropertyValue -Object $details -Name 'Manufacturer')
            Add-AttributeValues -Target $item.Attributes -Relation 'label' -Value (Get-JsonPropertyValue -Object $details -Name 'Label')
            Add-AttributeValues -Target $item.Attributes -Relation 'brand' -Value (Get-JsonPropertyValue -Object $details -Name 'Brand')
            Add-AttributeValues -Target $item.Attributes -Relation 'category' -Value (Get-JsonPropertyValue -Object $record -Name 'categories')
            Add-AttributeValues -Target $item.Attributes -Relation 'feature' -Value (Get-JsonPropertyValue -Object $record -Name 'features')
        }
    }
    finally {
        $reader.Dispose()
    }

    return [pscustomobject]@{
        Items = $items
        Stats = [ordered]@{
            raw_lines                 = $rawLines
            parsed_lines              = $parsedLines
            parse_failures            = $parseFailures
            missing_item_keys         = $missingItemKeys
            unique_items              = $items.Count
            duplicate_metadata_rows   = $duplicateRows
            missing_listing_date_rows = $missingListingDates
            unparsable_listing_dates  = $unparsableListingDates
        }
    }
}

function Read-InteractionStream {
    param([Parameter(Mandatory = $true)][string] $Path)

    $byItem = New-Object 'System.Collections.Generic.Dictionary[string,object]' ($Ordinal)
    [long] $rawLines = 0
    [long] $parsedLines = 0
    [long] $parseFailures = 0
    [long] $missingKeys = 0
    [long] $invalidTimestamps = 0
    [long] $duplicatePairs = 0

    $reader = New-Object System.IO.StreamReader($Path, $Utf8NoBom, $true, 1048576)
    try {
        while (-not $reader.EndOfStream) {
            $line = $reader.ReadLine()
            $rawLines++
            try {
                $record = $line | ConvertFrom-Json -ErrorAction Stop
                $parsedLines++
            }
            catch {
                $parseFailures++
                continue
            }

            $itemValue = Get-JsonPropertyValue -Object $record -Name 'parent_asin'
            $userValue = Get-JsonPropertyValue -Object $record -Name 'user_id'
            $itemId = if ($null -eq $itemValue) { '' } else { [System.Convert]::ToString($itemValue, $InvariantCulture).Trim() }
            $userId = if ($null -eq $userValue) { '' } else { [System.Convert]::ToString($userValue, $InvariantCulture).Trim() }
            if ($itemId.Length -eq 0 -or $userId.Length -eq 0) {
                $missingKeys++
                continue
            }

            $timestampValue = Get-JsonPropertyValue -Object $record -Name 'timestamp'
            [long] $timestampMs = 0
            $timestampText = if ($null -eq $timestampValue) { '' } else { [System.Convert]::ToString($timestampValue, $InvariantCulture) }
            if (-not [long]::TryParse($timestampText, [System.Globalization.NumberStyles]::Integer, $InvariantCulture, [ref] $timestampMs) -or
                $timestampMs -lt 0 -or $timestampMs -gt 253402300799999) {
                $invalidTimestamps++
                continue
            }

            if (-not $byItem.ContainsKey($itemId)) {
                $byItem.Add($itemId, (New-Object 'System.Collections.Generic.Dictionary[string,long]' ($Ordinal)))
            }
            $userTimes = $byItem[$itemId]
            if ($userTimes.ContainsKey($userId)) {
                $duplicatePairs++
                if ($timestampMs -lt $userTimes[$userId]) {
                    $userTimes[$userId] = $timestampMs
                }
            }
            else {
                $userTimes.Add($userId, $timestampMs)
            }
        }
    }
    finally {
        $reader.Dispose()
    }

    [long] $uniquePairs = 0
    foreach ($userTimes in $byItem.Values) {
        $uniquePairs += $userTimes.Count
    }
    return [pscustomobject]@{
        ByItem = $byItem
        Stats = [ordered]@{
            raw_lines                  = $rawLines
            parsed_lines               = $parsedLines
            parse_failures             = $parseFailures
            missing_user_or_item_keys  = $missingKeys
            invalid_timestamps         = $invalidTimestamps
            unique_items               = $byItem.Count
            unique_user_item_pairs     = $uniquePairs
            duplicate_interaction_pairs = $duplicatePairs
        }
    }
}

function Add-GraphItem {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [System.Collections.Generic.Dictionary[string,object]] $Graph,
        [Parameter(Mandatory = $true)]
        [object] $Item
    )

    foreach ($attribute in $Item.Attributes) {
        if (-not $Graph.ContainsKey($attribute)) {
            $Graph.Add($attribute, (New-Object 'System.Collections.Generic.List[int]'))
        }
        $Graph[$attribute].Add([int] $Item.UniverseIndex)
    }
}

function New-ExclusionMask {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]] $ItemIds,
        [Parameter(Mandatory = $true)][int] $UniverseSize,
        [Parameter(Mandatory = $true)][System.Collections.Generic.Dictionary[string,object]] $Items
    )

    $mask = New-Object 'bool[]' $UniverseSize
    foreach ($itemId in $ItemIds) {
        $mask[[int] $Items[$itemId].UniverseIndex] = $true
    }
    return ,$mask
}

function Get-Median {
    param([Parameter(Mandatory = $true)][AllowEmptyCollection()][int[]] $Values)

    if ($Values.Length -eq 0) {
        return $null
    }
    [array]::Sort($Values)
    $middle = [int] [math]::Floor($Values.Length / 2.0)
    if (($Values.Length % 2) -eq 1) {
        return [double] $Values[$middle]
    }
    return ([double] $Values[$middle - 1] + [double] $Values[$middle]) / 2.0
}

function Measure-CohortSupport {
    param(
        [Parameter(Mandatory = $true)][string] $CohortName,
        [Parameter(Mandatory = $true)][string] $GraphName,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]] $ItemIds,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.Dictionary[string,object]] $Graph,
        [Parameter(Mandatory = $true)][bool[]] $Excluded,
        [Parameter(Mandatory = $true)][System.Collections.Generic.Dictionary[string,object]] $Items,
        [Parameter(Mandatory = $true)][int[]] $NeighborMarks,
        [Parameter(Mandatory = $true)][ref] $StampReference
    )

    $relationLinkedCounts = [ordered]@{}
    foreach ($relation in $Relations) {
        $relationLinkedCounts[$relation] = 0
    }
    $perItem = New-Object 'System.Collections.Generic.Dictionary[string,object]' ($Ordinal)
    $neighborCounts = New-Object 'System.Collections.Generic.List[int]'
    [long] $linkedCount = 0
    [long] $emptyCount = 0
    [long] $neighborSum = 0

    foreach ($itemId in $ItemIds) {
        $item = $Items[$itemId]
        $StampReference.Value = [int] $StampReference.Value + 1
        $stamp = [int] $StampReference.Value
        $relationFlags = [ordered]@{}
        foreach ($relation in $Relations) {
            $relationFlags[$relation] = $false
        }
        if ($item.Attributes.Count -eq 0) {
            $emptyCount++
        }
        [int] $neighborCount = 0
        foreach ($attribute in $item.Attributes) {
            if (-not $Graph.ContainsKey($attribute)) {
                continue
            }
            $separatorPosition = $attribute.IndexOf($AttributeSeparator)
            $relation = if ($separatorPosition -gt 0) { $attribute.Substring(0, $separatorPosition) } else { '' }
            $attributeHasAllowedNeighbor = $false
            foreach ($neighborIndex in $Graph[$attribute]) {
                if ($Excluded[$neighborIndex]) {
                    continue
                }
                $attributeHasAllowedNeighbor = $true
                if ($NeighborMarks[$neighborIndex] -ne $stamp) {
                    $NeighborMarks[$neighborIndex] = $stamp
                    $neighborCount++
                }
            }
            if ($attributeHasAllowedNeighbor -and $relationFlags.Contains($relation)) {
                $relationFlags[$relation] = $true
            }
        }
        $linked = $neighborCount -gt 0
        if ($linked) {
            $linkedCount++
        }
        foreach ($relation in $Relations) {
            if ($relationFlags[$relation]) {
                $relationLinkedCounts[$relation]++
            }
        }
        $neighborCounts.Add($neighborCount)
        $neighborSum += $neighborCount
        $perItem.Add($itemId, [pscustomobject]@{
            linked         = $linked
            neighbor_count = $neighborCount
            relation_links = $relationFlags
        })
    }

    $count = $ItemIds.Length
    $relationRates = [ordered]@{}
    foreach ($relation in $Relations) {
        $relationRates[$relation] = if ($count -gt 0) { [double] $relationLinkedCounts[$relation] / $count } else { $null }
    }
    $neighborArray = $neighborCounts.ToArray()
    return [pscustomobject]@{
        Cohort  = $CohortName
        Graph   = $GraphName
        PerItem = $perItem
        Metrics = [ordered]@{
            item_count              = $count
            linked_count            = $linkedCount
            link_rate               = if ($count -gt 0) { [double] $linkedCount / $count } else { $null }
            empty_attribute_count   = $emptyCount
            empty_attribute_rate    = if ($count -gt 0) { [double] $emptyCount / $count } else { $null }
            mean_distinct_neighbors = if ($count -gt 0) { [double] $neighborSum / $count } else { $null }
            median_distinct_neighbors = Get-Median -Values $neighborArray
            relation_linked_counts  = $relationLinkedCounts
            relation_link_rates     = $relationRates
        }
    }
}

function Get-DeterministicSpots {
    param(
        [Parameter(Mandatory = $true)][string] $CohortName,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]] $ItemIds,
        [Parameter(Mandatory = $true)][System.Collections.Generic.Dictionary[string,object]] $Items,
        [AllowNull()][object] $PrefixEvaluation,
        [AllowNull()][object] $CompletedEvaluation
    )

    $orderedIds = [string[]] $ItemIds.Clone()
    [array]::Sort($orderedIds, $Ordinal)
    $limit = [math]::Min(5, $orderedIds.Length)
    $spots = New-Object 'System.Collections.Generic.List[object]'
    for ($index = 0; $index -lt $limit; $index++) {
        $itemId = $orderedIds[$index]
        $item = $Items[$itemId]
        $attributeArray = [string[]] @($item.Attributes)
        [array]::Sort($attributeArray, $Ordinal)
        $readableAttributes = New-Object 'System.Collections.Generic.List[string]'
        foreach ($attribute in $attributeArray) {
            $position = $attribute.IndexOf($AttributeSeparator)
            if ($position -gt 0) {
                $readableAttributes.Add($attribute.Substring(0, $position) + '=' + $attribute.Substring($position + 1))
            }
            else {
                $readableAttributes.Add($attribute)
            }
        }
        $prefixItem = if ($null -ne $PrefixEvaluation) { $PrefixEvaluation.PerItem[$itemId] } else { $null }
        $completedItem = if ($null -ne $CompletedEvaluation) { $CompletedEvaluation.PerItem[$itemId] } else { $null }
        $spots.Add([pscustomobject]@{
            cohort                    = $CohortName
            item_id                   = $itemId
            listing_date_utc          = $item.ListingDateUtc.ToString('yyyy-MM-dd', $InvariantCulture)
            deduplicated_interactions = $item.InteractionCount
            interactions_at_or_before = $item.AtOrBeforeCount
            interactions_after        = $item.AfterCount
            attributes                = $readableAttributes.ToArray()
            prefix_linked             = if ($null -ne $prefixItem) { $prefixItem.linked } else { $null }
            prefix_neighbors          = if ($null -ne $prefixItem) { $prefixItem.neighbor_count } else { $null }
            completed_linked          = if ($null -ne $completedItem) { $completedItem.linked } else { $null }
            completed_neighbors       = if ($null -ne $completedItem) { $completedItem.neighbor_count } else { $null }
        })
    }
    return $spots.ToArray()
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

function Add-MetricRow {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.List[object]] $Rows,
        [string] $Scope,
        [string] $Cohort,
        [string] $Graph,
        [string] $Relation,
        [string] $Metric,
        [AllowNull()][object] $Value,
        [AllowNull()][object] $Numerator,
        [AllowNull()][object] $Denominator
    )
    $Rows.Add([pscustomobject]@{
        scope       = $Scope
        cohort      = $Cohort
        graph       = $Graph
        relation    = $Relation
        metric      = $Metric
        value       = $Value
        numerator   = $Numerator
        denominator = $Denominator
    })
}

function Add-EvaluationMetricRows {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.List[object]] $Rows,
        [Parameter(Mandatory = $true)][object] $Evaluation
    )
    $metrics = $Evaluation.Metrics
    Add-MetricRow -Rows $Rows -Scope 'cohort' -Cohort $Evaluation.Cohort -Graph $Evaluation.Graph -Relation '' -Metric 'link_rate' -Value $metrics.link_rate -Numerator $metrics.linked_count -Denominator $metrics.item_count
    Add-MetricRow -Rows $Rows -Scope 'cohort' -Cohort $Evaluation.Cohort -Graph $Evaluation.Graph -Relation '' -Metric 'empty_attribute_rate' -Value $metrics.empty_attribute_rate -Numerator $metrics.empty_attribute_count -Denominator $metrics.item_count
    Add-MetricRow -Rows $Rows -Scope 'cohort' -Cohort $Evaluation.Cohort -Graph $Evaluation.Graph -Relation '' -Metric 'mean_distinct_neighbors' -Value $metrics.mean_distinct_neighbors -Numerator '' -Denominator $metrics.item_count
    Add-MetricRow -Rows $Rows -Scope 'cohort' -Cohort $Evaluation.Cohort -Graph $Evaluation.Graph -Relation '' -Metric 'median_distinct_neighbors' -Value $metrics.median_distinct_neighbors -Numerator '' -Denominator $metrics.item_count
    foreach ($relation in $Relations) {
        Add-MetricRow -Rows $Rows -Scope 'relation' -Cohort $Evaluation.Cohort -Graph $Evaluation.Graph -Relation $relation -Metric 'link_rate' -Value $metrics.relation_link_rates[$relation] -Numerator $metrics.relation_linked_counts[$relation] -Denominator $metrics.item_count
    }
}

function ConvertTo-CsvCell {
    param([AllowNull()][object] $Value)

    if ($null -eq $Value) {
        return ''
    }
    $text = if ($Value -is [double] -or $Value -is [single] -or $Value -is [decimal]) {
        ([System.IFormattable] $Value).ToString('G17', $InvariantCulture)
    }
    else {
        [System.Convert]::ToString($Value, $InvariantCulture)
    }
    if ($text.IndexOfAny([char[]] @(',', '"', "`r", "`n")) -ge 0) {
        return '"' + $text.Replace('"', '""') + '"'
    }
    return $text
}

function Convert-MetricRowsToCsv {
    param([Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.List[object]] $Rows)

    $builder = New-Object System.Text.StringBuilder
    $null = $builder.AppendLine('scope,cohort,graph,relation,metric,value,numerator,denominator')
    foreach ($row in $Rows) {
        $cells = @(
            ConvertTo-CsvCell $row.scope
            ConvertTo-CsvCell $row.cohort
            ConvertTo-CsvCell $row.graph
            ConvertTo-CsvCell $row.relation
            ConvertTo-CsvCell $row.metric
            ConvertTo-CsvCell $row.value
            ConvertTo-CsvCell $row.numerator
            ConvertTo-CsvCell $row.denominator
        )
        $null = $builder.AppendLine([string]::Join(',', $cells))
    }
    return $builder.ToString()
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

if (-not [System.IO.File]::Exists($MetadataPath)) {
    throw "Metadata input does not exist: $MetadataPath"
}
if (-not [System.IO.File]::Exists($InteractionsPath)) {
    throw "Interaction input does not exist: $InteractionsPath"
}
$finalDirectory = Join-Path $OutputRoot $RunId
if ([System.IO.Directory]::Exists($finalDirectory) -or [System.IO.File]::Exists($finalDirectory)) {
    throw "Refusing to overwrite existing result path: $finalDirectory"
}

$metadataRead = Read-MetadataStream -Path $MetadataPath
$interactionRead = Read-InteractionStream -Path $InteractionsPath
$items = $metadataRead.Items
$interactionsByItem = $interactionRead.ByItem

$universeIdsList = New-Object 'System.Collections.Generic.List[string]'
$listingTicks = New-Object 'System.Collections.Generic.List[long]'
[long] $interactedMetadataItems = 0
foreach ($entry in $items.GetEnumerator()) {
    $item = $entry.Value
    if (-not $interactionsByItem.ContainsKey($entry.Key) -or $interactionsByItem[$entry.Key].Count -eq 0) {
        continue
    }
    $interactedMetadataItems++
    $item.InteractionCount = $interactionsByItem[$entry.Key].Count
    if ($null -ne $item.ListingDateUtc) {
        $universeIdsList.Add($entry.Key)
        $listingTicks.Add([long] $item.ListingDateUtc.Ticks)
    }
}
if ($listingTicks.Count -eq 0) {
    throw 'No interacted metadata item has a parsable listing date; cutoff cannot be defined.'
}

$sortedTicks = $listingTicks.ToArray()
[array]::Sort($sortedTicks)
$cutoffIndex = [int] [math]::Ceiling(0.9 * $sortedTicks.Length) - 1
$cutoffDate = New-Object System.DateTime($sortedTicks[$cutoffIndex], [System.DateTimeKind]::Utc)
$epochUtc = New-Object System.DateTime(1970, 1, 1, 0, 0, 0, [System.DateTimeKind]::Utc)
$cutoffExclusiveMs = [long] (($cutoffDate.AddDays(1).Ticks - $epochUtc.Ticks) / [System.TimeSpan]::TicksPerMillisecond)
$cutoffInclusiveMs = $cutoffExclusiveMs - 1

$universeIds = $universeIdsList.ToArray()
[array]::Sort($universeIds, $Ordinal)
for ($index = 0; $index -lt $universeIds.Length; $index++) {
    $items[$universeIds[$index]].UniverseIndex = $index
}

$prefixWarmList = New-Object 'System.Collections.Generic.List[string]'
$launchColdList = New-Object 'System.Collections.Generic.List[string]'
foreach ($itemId in $universeIds) {
    $item = $items[$itemId]
    [int] $beforeCount = 0
    [int] $afterCount = 0
    foreach ($timestampMs in $interactionsByItem[$itemId].Values) {
        if ($timestampMs -lt $cutoffExclusiveMs) {
            $beforeCount++
        }
        else {
            $afterCount++
        }
    }
    $item.AtOrBeforeCount = $beforeCount
    $item.AfterCount = $afterCount
    if ($item.ListingDateUtc -le $cutoffDate -and $beforeCount -gt 0) {
        $prefixWarmList.Add($itemId)
    }
    if ($item.ListingDateUtc -gt $cutoffDate -and $beforeCount -eq 0 -and $afterCount -gt 0) {
        $launchColdList.Add($itemId)
    }
}
$prefixWarmIds = $prefixWarmList.ToArray()
$launchColdIds = $launchColdList.ToArray()
[array]::Sort($prefixWarmIds, $Ordinal)
[array]::Sort($launchColdIds, $Ordinal)

$launchSet = New-Object 'System.Collections.Generic.HashSet[string]' ($Ordinal)
foreach ($itemId in $launchColdIds) { $null = $launchSet.Add($itemId) }
$eligibleSyntheticList = New-Object 'System.Collections.Generic.List[string]'
foreach ($itemId in $universeIds) {
    if (-not $launchSet.Contains($itemId)) {
        $eligibleSyntheticList.Add($itemId)
    }
}
$eligibleSyntheticIds = $eligibleSyntheticList.ToArray()
$cohortSize = $launchColdIds.Length
$cohortPoolShortfall = [math]::Max(0, $cohortSize - $eligibleSyntheticIds.Length)
$cohortConstructionValid = $cohortPoolShortfall -eq 0

$bottomFrequencyIds = [string[]] @()
$randomIds = [string[]] @()
if ($cohortConstructionValid) {
    $frequencyBuckets = New-Object 'System.Collections.Generic.SortedDictionary[int,object]'
    foreach ($itemId in $eligibleSyntheticIds) {
        $frequency = [int] $items[$itemId].InteractionCount
        if (-not $frequencyBuckets.ContainsKey($frequency)) {
            $frequencyBuckets.Add($frequency, (New-Object 'System.Collections.Generic.List[string]'))
        }
        $frequencyBuckets[$frequency].Add($itemId)
    }
    $bottomList = New-Object 'System.Collections.Generic.List[string]'
    foreach ($bucket in $frequencyBuckets.GetEnumerator()) {
        $bucketIds = $bucket.Value.ToArray()
        [array]::Sort($bucketIds, $Ordinal)
        foreach ($itemId in $bucketIds) {
            if ($bottomList.Count -ge $cohortSize) { break }
            $bottomList.Add($itemId)
        }
        if ($bottomList.Count -ge $cohortSize) { break }
    }
    $bottomFrequencyIds = $bottomList.ToArray()

    $randomKeys = New-Object 'string[]' $eligibleSyntheticIds.Length
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        for ($index = 0; $index -lt $eligibleSyntheticIds.Length; $index++) {
            $itemId = $eligibleSyntheticIds[$index]
            $bytes = $Utf8NoBom.GetBytes(([string] $RandomSeed) + $AttributeSeparator + $itemId)
            $digest = $sha256.ComputeHash($bytes)
            $key = [System.BitConverter]::ToString($digest, 0, 16).Replace('-', '') + ':' + $itemId
            $randomKeys[$index] = $key
        }
    }
    finally {
        $sha256.Dispose()
    }
    [array]::Sort($randomKeys, $Ordinal)
    $randomIds = New-Object 'string[]' $cohortSize
    for ($index = 0; $index -lt $cohortSize; $index++) {
        $randomIds[$index] = $randomKeys[$index].Substring(33)
    }
}

$completedGraph = New-Object 'System.Collections.Generic.Dictionary[string,object]' ($Ordinal)
foreach ($itemId in $universeIds) {
    Add-GraphItem -Graph $completedGraph -Item $items[$itemId]
}
$prefixGraph = New-Object 'System.Collections.Generic.Dictionary[string,object]' ($Ordinal)
foreach ($itemId in $prefixWarmIds) {
    Add-GraphItem -Graph $prefixGraph -Item $items[$itemId]
}

$neighborMarks = New-Object 'int[]' $universeIds.Length
[int] $stamp = 0
$launchExclusion = New-ExclusionMask -ItemIds $launchColdIds -UniverseSize $universeIds.Length -Items $items
$launchPrefix = Measure-CohortSupport -CohortName 'launch_cold' -GraphName 'prefix' -ItemIds $launchColdIds -Graph $prefixGraph -Excluded $launchExclusion -Items $items -NeighborMarks $neighborMarks -StampReference ([ref] $stamp)
$launchCompleted = Measure-CohortSupport -CohortName 'launch_cold' -GraphName 'completed' -ItemIds $launchColdIds -Graph $completedGraph -Excluded $launchExclusion -Items $items -NeighborMarks $neighborMarks -StampReference ([ref] $stamp)

$bottomCompleted = $null
$randomCompleted = $null
if ($cohortConstructionValid) {
    $bottomExclusion = New-ExclusionMask -ItemIds $bottomFrequencyIds -UniverseSize $universeIds.Length -Items $items
    $randomExclusion = New-ExclusionMask -ItemIds $randomIds -UniverseSize $universeIds.Length -Items $items
    $bottomCompleted = Measure-CohortSupport -CohortName 'bottom_frequency' -GraphName 'completed' -ItemIds $bottomFrequencyIds -Graph $completedGraph -Excluded $bottomExclusion -Items $items -NeighborMarks $neighborMarks -StampReference ([ref] $stamp)
    $randomCompleted = Measure-CohortSupport -CohortName 'random' -GraphName 'completed' -ItemIds $randomIds -Graph $completedGraph -Excluded $randomExclusion -Items $items -NeighborMarks $neighborMarks -StampReference ([ref] $stamp)
}

$launchSemanticsValid = $true
foreach ($itemId in $launchColdIds) {
    $item = $items[$itemId]
    if ($item.ListingDateUtc -le $cutoffDate -or $item.AtOrBeforeCount -ne 0 -or $item.AfterCount -lt 1) {
        $launchSemanticsValid = $false
        break
    }
}
$prefixSemanticsValid = $true
foreach ($itemId in $prefixWarmIds) {
    if ($items[$itemId].AtOrBeforeCount -lt 1) {
        $prefixSemanticsValid = $false
        break
    }
}
$bottomSet = New-Object 'System.Collections.Generic.HashSet[string]' ($Ordinal)
foreach ($itemId in $bottomFrequencyIds) { $null = $bottomSet.Add($itemId) }
$randomSet = New-Object 'System.Collections.Generic.HashSet[string]' ($Ordinal)
foreach ($itemId in $randomIds) { $null = $randomSet.Add($itemId) }
$launchBottomOverlap = 0
$launchRandomOverlap = 0
$bottomRandomOverlap = 0
foreach ($itemId in $launchColdIds) {
    if ($bottomSet.Contains($itemId)) { $launchBottomOverlap++ }
    if ($randomSet.Contains($itemId)) { $launchRandomOverlap++ }
}
foreach ($itemId in $bottomFrequencyIds) {
    if ($randomSet.Contains($itemId)) { $bottomRandomOverlap++ }
}

$sanityChecks = New-Object 'System.Collections.Generic.List[object]'
Add-SanityCheck -Checks $sanityChecks -Name 'metadata_json_parse_failures_reported_diagnostic_only' -Passed $true -Observed $metadataRead.Stats.parse_failures
Add-SanityCheck -Checks $sanityChecks -Name 'interaction_json_parse_failures_reported_diagnostic_only' -Passed $true -Observed $interactionRead.Stats.parse_failures
Add-SanityCheck -Checks $sanityChecks -Name 'interaction_keys_and_timestamps_valid' -Passed (($interactionRead.Stats.missing_user_or_item_keys + $interactionRead.Stats.invalid_timestamps) -eq 0) -Observed ([ordered]@{ missing_keys = $interactionRead.Stats.missing_user_or_item_keys; invalid_timestamps = $interactionRead.Stats.invalid_timestamps })
Add-SanityCheck -Checks $sanityChecks -Name 'launch_cold_semantics' -Passed $launchSemanticsValid -Observed $launchColdIds.Length
Add-SanityCheck -Checks $sanityChecks -Name 'prefix_warm_semantics' -Passed $prefixSemanticsValid -Observed $prefixWarmIds.Length
Add-SanityCheck -Checks $sanityChecks -Name 'synthetic_pool_sufficient' -Passed $cohortConstructionValid -Observed ([ordered]@{ pool = $eligibleSyntheticIds.Length; required = $cohortSize; shortfall = $cohortPoolShortfall })
Add-SanityCheck -Checks $sanityChecks -Name 'cohort_sizes_identical' -Passed ($cohortConstructionValid -and $bottomFrequencyIds.Length -eq $cohortSize -and $randomIds.Length -eq $cohortSize) -Observed ([ordered]@{ launch = $cohortSize; bottom_frequency = $bottomFrequencyIds.Length; random = $randomIds.Length })
Add-SanityCheck -Checks $sanityChecks -Name 'launch_and_synthetic_cohorts_disjoint' -Passed ($launchBottomOverlap -eq 0 -and $launchRandomOverlap -eq 0) -Observed ([ordered]@{ launch_bottom_overlap = $launchBottomOverlap; launch_random_overlap = $launchRandomOverlap; bottom_random_overlap_permitted = $bottomRandomOverlap })

$allSanityPassed = $true
foreach ($check in $sanityChecks) {
    if (-not $check.passed) {
        $allSanityPassed = $false
        break
    }
}
$listingDateCoverage = if ($interactedMetadataItems -gt 0) { [double] $universeIds.Length / $interactedMetadataItems } else { 0.0 }
$totalSupportGapPp = if ($null -ne $bottomCompleted) { 100.0 * ([double] $bottomCompleted.Metrics.link_rate - [double] $launchPrefix.Metrics.link_rate) } else { $null }
$futureGraphOnlyRate = [double] $launchCompleted.Metrics.link_rate - [double] $launchPrefix.Metrics.link_rate
$randomGapPp = if ($null -ne $randomCompleted) { 100.0 * ([double] $randomCompleted.Metrics.link_rate - [double] $launchPrefix.Metrics.link_rate) } else { $null }
$dataAdequate = $allSanityPassed -and $listingDateCoverage -ge 0.80 -and $launchColdIds.Length -ge 500
$passesEffectGate = $false
if ($null -ne $totalSupportGapPp) {
    $passesEffectGate = $totalSupportGapPp -ge 10.0 -or $futureGraphOnlyRate -ge 0.20
}
$verdict = if (-not $dataAdequate) {
    'INCONCLUSIVE'
}
elseif ($passesEffectGate) {
    'ADVANCE_H1_TO_OUTCOME_POC'
}
else {
    'REFUTE_H1_AND_PIVOT_H4'
}

$spots = New-Object 'System.Collections.Generic.List[object]'
foreach ($spot in (Get-DeterministicSpots -CohortName 'launch_cold' -ItemIds $launchColdIds -Items $items -PrefixEvaluation $launchPrefix -CompletedEvaluation $launchCompleted)) { $spots.Add($spot) }
if ($cohortConstructionValid) {
    foreach ($spot in (Get-DeterministicSpots -CohortName 'bottom_frequency' -ItemIds $bottomFrequencyIds -Items $items -PrefixEvaluation $null -CompletedEvaluation $bottomCompleted)) { $spots.Add($spot) }
    foreach ($spot in (Get-DeterministicSpots -CohortName 'random' -ItemIds $randomIds -Items $items -PrefixEvaluation $null -CompletedEvaluation $randomCompleted)) { $spots.Add($spot) }
}

$result = [ordered]@{
    schema_version = 'h1_launch_support.v1'
    run_id         = $RunId
    dataset        = 'Amazon Reviews 2023 / Digital Music'
    protocol       = [ordered]@{
        cutoff_quantile = 0.9
        cutoff_index_rule = 'ceiling(0.9*n)-1'
        random_seed = $RandomSeed
        randomization = 'ascending SHA-256(seed + U+001F + item_id), first 128 digest bits, item-id suffix tie break'
        duplicate_interaction_semantics = 'earliest timestamp retained for each unique (user_id,parent_asin) pair'
        date_resolution_semantics = 'Date First Available parsed as UTC calendar date; interactions on the cutoff date count at-or-before (exclusive boundary is next UTC midnight)'
        synthetic_pool = 'all eligible universe items excluding launch-cold; bottom and random samples are independent and may overlap each other'
        relation_rate_denominator = 'all items in the evaluated cohort'
    }
    inputs = [ordered]@{
        metadata = [System.IO.Path]::GetFullPath($MetadataPath)
        interactions = [System.IO.Path]::GetFullPath($InteractionsPath)
    }
    cutoff = [ordered]@{
        listing_date_utc = $cutoffDate.ToString('yyyy-MM-dd', $InvariantCulture)
        inclusive_interaction_timestamp_ms = $cutoffInclusiveMs
        sorted_index_zero_based = $cutoffIndex
        universe_size = $universeIds.Length
    }
    parsing = [ordered]@{
        metadata = $metadataRead.Stats
        interactions = $interactionRead.Stats
        interacted_metadata_items = $interactedMetadataItems
        interacted_items_with_parsable_listing_date = $universeIds.Length
        listing_date_coverage = $listingDateCoverage
    }
    graph = [ordered]@{
        prefix_warm_items = $prefixWarmIds.Length
        prefix_typed_attributes = $prefixGraph.Count
        completed_items = $universeIds.Length
        completed_typed_attributes = $completedGraph.Count
    }
    cohorts = [ordered]@{
        launch_cold = $launchColdIds.Length
        bottom_frequency = $bottomFrequencyIds.Length
        random = $randomIds.Length
        eligible_synthetic_pool = $eligibleSyntheticIds.Length
        synthetic_pool_shortfall = $cohortPoolShortfall
        bottom_random_overlap_permitted = $bottomRandomOverlap
    }
    metrics = [ordered]@{
        primary = [ordered]@{
            total_support_gap_pp = $totalSupportGapPp
            future_graph_only_rate = $futureGraphOnlyRate
        }
        secondary = [ordered]@{
            random_completed_gap_from_launch_prefix_pp = $randomGapPp
        }
        launch_prefix = $launchPrefix.Metrics
        launch_completed = $launchCompleted.Metrics
        bottom_frequency_completed = if ($null -ne $bottomCompleted) { $bottomCompleted.Metrics } else { $null }
        random_completed = if ($null -ne $randomCompleted) { $randomCompleted.Metrics } else { $null }
    }
    sanity_checks = $sanityChecks.ToArray()
    deterministic_spot_checks = $spots.ToArray()
    decision = [ordered]@{
        verdict = $verdict
        all_sanity_checks_passed = $allSanityPassed
        listing_date_coverage_gate = $listingDateCoverage -ge 0.80
        launch_count_gate = $launchColdIds.Length -ge 500
        support_gap_gate = if ($null -ne $totalSupportGapPp) { $totalSupportGapPp -ge 10.0 } else { $false }
        future_graph_only_gate = $futureGraphOnlyRate -ge 0.20
    }
    artifacts = [ordered]@{
        json = 'result.json'
        compact_csv = 'metrics.csv'
    }
}

$metricRows = New-Object 'System.Collections.Generic.List[object]'
Add-MetricRow -Rows $metricRows -Scope 'primary' -Cohort 'bottom_frequency_minus_launch_cold' -Graph 'completed_minus_prefix' -Relation '' -Metric 'total_support_gap_pp' -Value $totalSupportGapPp -Numerator '' -Denominator ''
Add-MetricRow -Rows $metricRows -Scope 'primary' -Cohort 'launch_cold' -Graph 'completed_minus_prefix' -Relation '' -Metric 'future_graph_only_rate' -Value $futureGraphOnlyRate -Numerator '' -Denominator $launchColdIds.Length
Add-MetricRow -Rows $metricRows -Scope 'secondary' -Cohort 'random_minus_launch_cold' -Graph 'completed_minus_prefix' -Relation '' -Metric 'random_gap_pp' -Value $randomGapPp -Numerator '' -Denominator ''
Add-EvaluationMetricRows -Rows $metricRows -Evaluation $launchPrefix
Add-EvaluationMetricRows -Rows $metricRows -Evaluation $launchCompleted
if ($null -ne $bottomCompleted) { Add-EvaluationMetricRows -Rows $metricRows -Evaluation $bottomCompleted }
if ($null -ne $randomCompleted) { Add-EvaluationMetricRows -Rows $metricRows -Evaluation $randomCompleted }

$jsonContent = ($result | ConvertTo-Json -Depth 16 -Compress) + [Environment]::NewLine
$csvContent = Convert-MetricRowsToCsv -Rows $metricRows

# Publication begins only after all sanity checks, metrics, spots, and the verdict
# have been computed.  Both files are fsynced in a unique sibling directory;
# a single no-overwrite directory rename publishes the complete result bundle.
[System.IO.Directory]::CreateDirectory($OutputRoot) | Out-Null
if ([System.IO.Directory]::Exists($finalDirectory) -or [System.IO.File]::Exists($finalDirectory)) {
    throw "Result path appeared during computation; refusing to overwrite: $finalDirectory"
}
$temporaryDirectory = Join-Path $OutputRoot ('.' + $RunId + '.tmp.' + [guid]::NewGuid().ToString('N'))
[System.IO.Directory]::CreateDirectory($temporaryDirectory) | Out-Null
Write-Utf8Fsync -Path (Join-Path $temporaryDirectory 'result.json') -Content $jsonContent
Write-Utf8Fsync -Path (Join-Path $temporaryDirectory 'metrics.csv') -Content $csvContent
[System.IO.Directory]::Move($temporaryDirectory, $finalDirectory)

foreach ($spot in $spots) {
    Write-Output ('H1_SPOT ' + ($spot | ConvertTo-Json -Depth 8 -Compress))
}
Write-Output ('H1_COMPLETE ' + ([ordered]@{
    run_id = $RunId
    verdict = $verdict
    result_directory = $finalDirectory
    total_support_gap_pp = $totalSupportGapPp
    future_graph_only_rate = $futureGraphOnlyRate
} | ConvertTo-Json -Compress))
