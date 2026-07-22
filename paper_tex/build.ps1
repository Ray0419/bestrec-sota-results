param([string]$Draft = "")
$env:SOURCE_DATE_EPOCH = (git log -1 --format=%ct 2>$null)
$__prevWaiver = $env:DRAFT_WAIVER
try {
if ($Draft -ne "") {
  $env:DRAFT_WAIVER = "1"
  "DRAFT BUILD (waiver logged): $Draft" | Tee-Object -FilePath (Join-Path $PSScriptRoot "draft_waiver.log")
} else { Remove-Item Env:DRAFT_WAIVER -ErrorAction SilentlyContinue }
# Build the TORS LaTeX derivative (PowerShell twin of build.sh; two targets, round-8).
#   review target : main.tex          [manuscript,screen]      -> PAPER_TORS.pdf (gated)
#   preview target: main-acmsmall.tex [acmsmall,screen] -> PAPER_TORS_acmsmall.pdf (untracked)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = if ($env:PYTHON) { $env:PYTHON } else { Join-Path $PSScriptRoot "..\_bestrec_run\.venv\Scripts\python.exe" }
$Tectonic = if ($env:TECTONIC) { $env:TECTONIC } else {
    $cand = Join-Path $env:LOCALAPPDATA "tectonic\tectonic.exe"
    if (Test-Path $cand) { $cand } else { "tectonic" }
}

Write-Host "== [1/4] regenerate table includes from the artifact graph =="
& $Python (Join-Path $PSScriptRoot "..\_bestrec_run\build_hstu_tables.py") --submission
if ($LASTEXITCODE -ne 0) { throw "build_hstu_tables.py --submission failed (strict table build)" }
& $Python (Join-Path $PSScriptRoot "..\_bestrec_run\emit_latex_tables.py")
if ($LASTEXITCODE -ne 0) { throw "emit_latex_tables.py failed (numeric cross-check or extraction drift)" }

Write-Host "== [2/4] tectonic compile: review target (manuscript) =="
$__eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
& $Tectonic --keep-logs main.tex 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath (Join-Path $PSScriptRoot "main_console.log")
$__rc = $LASTEXITCODE; $ErrorActionPreference = $__eap
if ($__rc -ne 0) { throw "tectonic main.tex failed (exit $__rc)" }
if ($LASTEXITCODE -ne 0) { throw "tectonic compile failed (main.tex)" }
Write-Host "== [2/4] tectonic compile: production preview (acmsmall) =="
$__eap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
& $Tectonic main-acmsmall.tex 2>&1 | ForEach-Object { "$_" }
$__rc = $LASTEXITCODE; $ErrorActionPreference = $__eap
if ($__rc -ne 0) { throw "tectonic main-acmsmall.tex failed (exit $__rc)" }
if ($LASTEXITCODE -ne 0) { throw "tectonic compile failed (main-acmsmall.tex)" }

Write-Host "== [3/4] package PAPER_TORS.pdf (review) + PAPER_TORS_acmsmall.pdf (preview, untracked) =="
Copy-Item -Force main.pdf PAPER_TORS.pdf
Copy-Item -Force main-acmsmall.pdf PAPER_TORS_acmsmall.pdf

Write-Host "== [4/5] tex health gate (H1-H10; parity with build.sh) =="
& $Python check_tex_health.py
if ($LASTEXITCODE -ne 0) { throw "tex health gate FAILED" }

Write-Host "== [5/5] hygiene scan of the review artifact =="
& $Python scan_pdf.py PAPER_TORS.pdf
if ($LASTEXITCODE -ne 0) { throw "hygiene scan FAILED" }

Write-Host "BUILD OK: paper_tex/PAPER_TORS.pdf (review, manuscript) + paper_tex/PAPER_TORS_acmsmall.pdf (preview)"

} finally { if ($null -ne $__prevWaiver) { $env:DRAFT_WAIVER = $__prevWaiver } else { Remove-Item Env:DRAFT_WAIVER -ErrorAction SilentlyContinue } }
