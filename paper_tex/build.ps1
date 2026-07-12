# Build PAPER_TORS.pdf (PowerShell twin of build.sh) -- see build.sh for step documentation.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = if ($env:PYTHON) { $env:PYTHON } else { Join-Path $PSScriptRoot "..\_bestrec_run\.venv\Scripts\python.exe" }
$Tectonic = if ($env:TECTONIC) { $env:TECTONIC } else {
    $cand = Join-Path $env:LOCALAPPDATA "tectonic\tectonic.exe"
    if (Test-Path $cand) { $cand } else { "tectonic" }
}

Write-Host "== [1/4] regenerate table includes from the artifact graph =="
& $Python (Join-Path $PSScriptRoot "..\_bestrec_run\emit_latex_tables.py")
if ($LASTEXITCODE -ne 0) { throw "emit_latex_tables.py failed (numeric cross-check or extraction drift)" }

Write-Host "== [2/4] tectonic compile (acmart TORS, review+anonymous) =="
& $Tectonic main.tex
if ($LASTEXITCODE -ne 0) { throw "tectonic compile failed" }

Write-Host "== [3/4] package PAPER_TORS.pdf =="
Copy-Item -Force main.pdf PAPER_TORS.pdf

Write-Host "== [4/4] hygiene scan =="
& $Python scan_pdf.py PAPER_TORS.pdf
if ($LASTEXITCODE -ne 0) { throw "hygiene scan FAILED" }

Write-Host "BUILD OK: paper_tex/PAPER_TORS.pdf"
