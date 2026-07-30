param([string]$Draft = "")
# Match build.sh's fail-closed release-epoch assertion. SOURCE_DATE_EPOCH is
# intentionally fixed for byte-stable archival PDFs, but a release build must
# still prove that the governing manifest is present, parseable, and carries a
# nonempty Git boundary. ALLOW_HEAD_EPOCH=1 is development-only.
$ManifestPath = Join-Path $PSScriptRoot "..\RELEASE_MANIFEST.json"
$ManifestCommit = $null
try {
  $Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $ManifestCommit = [string]$Manifest.git_commit
} catch {
  $ManifestCommit = $null
}
if ([string]::IsNullOrWhiteSpace($ManifestCommit) -and $env:ALLOW_HEAD_EPOCH -ne "1") {
  throw "FATAL: cannot read git_commit from RELEASE_MANIFEST.json (set ALLOW_HEAD_EPOCH=1 only for development builds)"
}
# A fixed archival metadata epoch makes Tectonic's PDF date and file identifier
# independent of the child commit that carries a freshly regenerated manifest.
$env:SOURCE_DATE_EPOCH = "946684800"
$__prevWaiver = $env:DRAFT_WAIVER
try {
if ($Draft -ne "") {
  $env:DRAFT_WAIVER = "1"
  $__wl = "$(Get-Date -Format o) DRAFT BUILD (waiver): $Draft"
Write-Host $__wl
[System.IO.File]::AppendAllText((Join-Path $PSScriptRoot "draft_waiver.log"), $__wl + [Environment]::NewLine, (New-Object System.Text.UTF8Encoding($false)))
} else { Remove-Item Env:DRAFT_WAIVER -ErrorAction SilentlyContinue }
# Build the TORS LaTeX derivative (PowerShell twin of build.sh; three targets).
#   review target : main.tex          [manuscript,screen]      -> PAPER_TORS.pdf (gated)
#   journal target: main-acmsmall.tex [acmsmall,screen]        -> PAPER_TORS_acmsmall.pdf
#   supplement    : supplement.tex    [acmsmall,screen]        -> PAPER_TORS_SUPPLEMENT.pdf
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = if ($env:PYTHON) { $env:PYTHON } else { Join-Path $PSScriptRoot "..\_bestrec_run\.venv\Scripts\python.exe" }
$Tectonic = if ($env:TECTONIC) { $env:TECTONIC } else {
    $cand = Join-Path $env:LOCALAPPDATA "tectonic\tectonic.exe"
    if (Test-Path $cand) { $cand } else {
        $gc = Get-Command tectonic -ErrorAction SilentlyContinue
        if ($gc) { $gc.Source } else { $null }
    }
}
if (-not $Tectonic -or -not (Test-Path $Tectonic)) {
    throw "FATAL: no tectonic executable found (set TECTONIC or install to LOCALAPPDATA\tectonic) -- refusing a false-success build (audit 14:50 P1)"
}
Write-Host "tectonic: $Tectonic"

Write-Host "== [1/5] regenerate table includes from the artifact graph =="
& $Python (Join-Path $PSScriptRoot "..\_bestrec_run\build_hstu_tables.py") --submission
if ($LASTEXITCODE -ne 0) { throw "build_hstu_tables.py --submission failed (strict table build)" }
& $Python (Join-Path $PSScriptRoot "..\_bestrec_run\emit_latex_tables.py")
if ($LASTEXITCODE -ne 0) { throw "emit_latex_tables.py failed (numeric cross-check or extraction drift)" }

Write-Host "== [2/5] tectonic compile: review target (manuscript) =="
$__eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
$__lines = & $Tectonic --keep-logs main.tex 2>&1 | ForEach-Object { "$_" }
$__lines | ForEach-Object { Write-Host $_ }
[System.IO.File]::WriteAllLines((Join-Path $PSScriptRoot "main_console.log"), [string[]]$__lines, (New-Object System.Text.UTF8Encoding($false)))
$__rc = $LASTEXITCODE; $ErrorActionPreference = $__eap
if ($__rc -ne 0) { throw "tectonic main.tex failed (exit $__rc)" }
$__log = Get-Content -Raw (Join-Path $PSScriptRoot "main_console.log")
if ($__log -notmatch 'Writing [`]?main\.pdf') {
    throw "tectonic main.tex: completion marker 'Writing main.pdf' missing from log (audit 14:50 P1)"
}
if ($__log -match 'command not found|CommandNotFound') {
    throw "tectonic log contains a tool-not-found error"
}
if ($LASTEXITCODE -ne 0) { throw "tectonic compile failed (main.tex)" }
Write-Host "== [2/5] tectonic compile: journal-layout main paper (acmsmall) =="
$__eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
$__acmLines = & $Tectonic --keep-intermediates --keep-logs main-acmsmall.tex 2>&1 | ForEach-Object { "$_" }
$__acmLines | ForEach-Object { Write-Host $_ }
[System.IO.File]::WriteAllLines((Join-Path $PSScriptRoot "main-acmsmall_console.log"), [string[]]$__acmLines, (New-Object System.Text.UTF8Encoding($false)))
$__rc = $LASTEXITCODE; $ErrorActionPreference = $__eap
if ($__rc -ne 0) { throw "tectonic main-acmsmall.tex failed (exit $__rc)" }
$__acmLog = Get-Content -Raw (Join-Path $PSScriptRoot "main-acmsmall_console.log")
if ($__acmLog -notmatch 'Writing [`]?main-acmsmall\.pdf') {
    throw "tectonic main-acmsmall.tex: completion marker missing"
}

Write-Host "== [2/5] tectonic compile: reviewer supplement =="
$__eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
$__suppLines = & $Tectonic --keep-logs supplement.tex 2>&1 | ForEach-Object { "$_" }
$__suppLines | ForEach-Object { Write-Host $_ }
[System.IO.File]::WriteAllLines((Join-Path $PSScriptRoot "supplement_console.log"), [string[]]$__suppLines, (New-Object System.Text.UTF8Encoding($false)))
$__rc = $LASTEXITCODE; $ErrorActionPreference = $__eap
if ($__rc -ne 0) { throw "tectonic supplement.tex failed (exit $__rc)" }
$__suppLog = Get-Content -Raw (Join-Path $PSScriptRoot "supplement_console.log")
if ($__suppLog -notmatch 'Writing [`]?supplement\.pdf') {
    throw "tectonic supplement.tex: completion marker missing"
}

Write-Host "== [3/5] package main and supplement PDFs =="
Copy-Item -Force main.pdf PAPER_TORS.pdf
Copy-Item -Force main-acmsmall.pdf PAPER_TORS_acmsmall.pdf
Copy-Item -Force supplement.pdf PAPER_TORS_SUPPLEMENT.pdf
& $Python (Join-Path $PSScriptRoot "..\_bestrec_run\normalize_pdf_metadata.py") PAPER_TORS.pdf PAPER_TORS_acmsmall.pdf PAPER_TORS_SUPPLEMENT.pdf
if ($LASTEXITCODE -ne 0) { throw "PDF metadata normalization failed" }

Write-Host "== [4/5] tex health gate (H1-H10; parity with build.sh) =="
& $Python check_tex_health.py
if ($LASTEXITCODE -ne 0) { throw "tex health gate FAILED" }

Write-Host "== [5/5] hygiene scan of the review and supplement artifacts =="
& $Python scan_pdf.py PAPER_TORS.pdf hygiene_scan_output.txt
if ($LASTEXITCODE -ne 0) { throw "hygiene scan FAILED" }
& $Python scan_pdf.py PAPER_TORS_SUPPLEMENT.pdf hygiene_scan_supplement_output.txt
if ($LASTEXITCODE -ne 0) { throw "supplement hygiene scan FAILED" }

Write-Host "BUILD OK: PAPER_TORS.pdf + PAPER_TORS_acmsmall.pdf + PAPER_TORS_SUPPLEMENT.pdf"

} finally { if ($null -ne $__prevWaiver) { $env:DRAFT_WAIVER = $__prevWaiver } else { Remove-Item Env:DRAFT_WAIVER -ErrorAction SilentlyContinue } }
