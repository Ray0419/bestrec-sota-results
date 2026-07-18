# Paper Review Audit

This file is cumulative. Each run should add a timestamped section, keep the
prior rejection-risk list current, and distinguish confirmed problems from
plausible risks.

## Current Prioritized Rejection-Risk List

1. **Confirmed generated-artifact/state hazard: `_bestrec_run/hstu_tables.json`
   is currently non-submission-mode in the worktree.** The file differs from
   `HEAD` only by `"mode": "default"` and `"submission_gate.enforced": false`.
   A fresh strict build to a temporary output is green, so the numbers are not
   currently contradicted; the risk is that the tracked generated JSON no longer
   satisfies the assumption documented by `emit_latex_tables.py` and
   `paper_tex/BUILD_NOTES.md` ("strict-build JSON"). The LaTeX build scripts run
   `emit_latex_tables.py` directly and do not themselves force
   `build_hstu_tables.py --submission` or assert that the JSON was generated in
   submission mode.
2. **Confirmed prior cover-letter stale-version blocker is fixed.**
   `COVER_LETTER_TORS.md` now uses version-agnostic current-deposit wording and
   points to `DOI_DEPOSIT_INSTRUCTIONS.md`; no `v1.1.4-deposit` occurrence
   remains in the cover letter, compiled TORS PDF, or canonical paper.
3. **Confirmed v1.1.5 repairs the prior v1.1.4 byte-boundary defect for the
   deposited package.** Local and remote `v1.1.5-deposit` resolve to
   `a3eaf1b01a14152c48101c7126ae76a956631ea2`; the uploaded/local zip digest is
   `b4faeb42b67a0637e0be667a65e403026bef61c0bec28e7b8294d65a71b1817c`; the
   zip has `66` entries, `65` SHA rows, `0` missing payloads, and `0` payload
   mismatches; and bundled/tag/release `RELEASE_MANIFEST.json` bytes match
   exactly at SHA256 `72d0068fa5825d7608f4ff4f45a5152e951413f57a7b42353802dd7212aef8bb`.
4. **Residual local-checkout line-ending caveat.** `.gitattributes` now pins LF
   and the v1.1.5 builder normalizes text payloads to LF at bundle time, but
   this existing Windows working tree still has CRLF worktree bytes for several
   tracked text files (`RELEASE_MANIFEST.json`, `README.md`, `CITATION.cff`,
   `.zenodo.json`, `VENUE_PLAN.md`, `DOI_DEPOSIT_INSTRUCTIONS.md`). This is not
   a v1.1.5 bundle defect; it is a local-round-trip hazard if future
   instructions compare `Get-FileHash` on the current worktree file to the
   tag/release asset without first using Git-blob or bundle bytes.
5. **Venue-template drift remains a freeze blocker.** The TeX build still
   vendors `paper_tex/acmart.cls` v2.03 from `2024/02/04`. ACM's author page
   currently instructs review manuscripts to use single-column `manuscript`
   format with the ACM Primary Article Template v2.16 (`2025-08-28`), while
   CTAN lists production `acmart` v2.19 (`2026-06-27`). `VENUE_PLAN.md` records
   the portal-vs-CTAN decision point, but the refresh/rebuild/hygiene pass is
   still pending.
6. **No current hard numerical blocker in the local strict gate.** Fresh
   strict checks at `2026-07-18 19:23 Australia/Sydney` pass HSTU parity,
   `168` recomputed empirical cells, `0` paper mismatches, `0` untraceable
   cells, all `14` declared claim families, and release-manifest hash
   verification for `153` local files. The strict table check was deliberately
   written to a temporary JSON to avoid overwriting the currently modified
   worktree copy.
7. **Office V3 and FIR-breadth mechanical evidence remain green.** Office V3
   adjudication at `2026-07-18 19:23` passes under frozen wording: K=16 mean
   `0.03047`, CI-LB `0.03033`; K=8 mean `0.03029`, CI-LB `0.03024`; all 10
   seeds above both `0.0279` and `0.0271`; comparability conditions OK.
   FIR-breadth remains confirmed: `Industrial_and_Scientific` mean `+0.00240`,
   95% CI `[+0.00183,+0.00297]`, 5/5 positive; `CDs_and_Vinyl` mean
   `+0.00566`, 95% CI `[+0.00493,+0.00639]`, 5/5 positive. These support only
   the stated per-category point-estimate and internal paired filter claims,
   not paired superiority or SOTA.
8. **Current HEAD is beyond the deposit tag by audit-response and companion
   documentation commits.** HEAD is
   `b41555021625d252e9149ddec6b3dc37015a80e4`, after
   `v1.1.5-deposit`. The post-deposit commits fix/answer audit issues and add
   companion-documentation checks; this is acceptable only if the archival
   boundary remains the deposit tag/release, not "latest branch HEAD."
9. **Plausible related-work risk: SILLM4Rec remains under-inspected.** The
   current paper discloses direct full-text protocol inspection as pending and
   excludes SILLM4Rec based on ACM metadata plus the public repository workflow
   (image-description generation, user-preference summaries, candidate-product
   ranking tasks, SFT/DPO training data). That exclusion is directionally
   defensible but still weaker than inspecting the ACM paper itself.
10. **GrIT FIR-breadth literature fence is now present, but should stay guarded.**
    The manuscript now explicitly says GrIT also reports
    `Industrial_and_Scientific` and `CDs_and_Vinyl` numbers and that the paper's
    FIR-breadth result is only an internal paired filter-vs-no-filter contrast.
    That resolves the prior omission, but any future prose must avoid converting
    this into a comparator claim.
11. **TORS cover letter remains a maintainer-fill freeze item.** Bracketed
    fields for identity/contact, conflicts, reviewer suggestions, and preprint
    status remain. That is acceptable as a tracked draft, not as a final
    ScholarOne upload.
12. **Persistent scientific boundary: novelty remains narrow/incremental and
    must stay framed that way.** FIR is defensible only as a leak-free,
    left-causal, zero-init adaptation inside this HSTU-style artifact-gated
    setting; TAPE remains a secondary soft-prototype ablation. Any future
    abstract, conclusion, cover letter, DOI metadata, README, or release note
    must keep Video_Games as competitive but not SOTA; MI and Office V3 as
    per-category point-estimate comparisons against single-run/single-seed
    comparators; and FIR breadth as internal paired filter-vs-no-filter
    evidence only.

## Audit Run - 2026-07-18 19:20 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` /
  `b41555021625d252e9149ddec6b3dc37015a80e4`.
- Current run time: `2026-07-18 19:20:41` through `19:23:13 +10:00` for
  local validation commands; audit text written immediately after.
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  using the `$HOME\.codex` fallback because `CODEX_HOME` remains unset in this
  PowerShell session.
- New commits since the remembered 17:18 audit: `22569ee7` fixes the
  cover-letter current-deposit wording, generalizes the deposit gate, adds the
  GrIT breadth fence, and refreshes PDFs/manifests; `c5f62a46` answers that
  audit in writing; `b4155502` updates the plain-language companion's standing
  number-source map.
- Working tree before this audit edit: tracked modification only in
  `_bestrec_run/hstu_tables.json`; untracked files remain
  `_bestrec_run/impact_program.DONE`, `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Sources/artifacts inspected this run: `PAPER_REVIEW_AUDIT.md`,
  `PAPER_SUBMISSION.md`, `paper_tex/sections/*.tex`,
  `_bestrec_run/hstu_tables.json`, `git show HEAD:_bestrec_run/hstu_tables.json`,
  `_bestrec_run/build_hstu_tables.py`, `_bestrec_run/rebuild_hstu_submission.py`,
  `_bestrec_run/emit_latex_tables.py`, `paper_tex/build.ps1`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `paper_tex/tables/TABLES_PROVENANCE.json`, `COVER_LETTER_TORS.md`,
  `CANONICAL_SUBMISSION.md`, `README.md`, `DOI_DEPOSIT_INSTRUCTIONS.md`,
  `VENUE_PLAN.md`, and `PLAIN_LANGUAGE_COMPANION.md`.
- No manuscript, code, result, or generated table file was edited in this run;
  only this audit file was updated. The strict table build was deliberately
  redirected to a temp JSON at
  `C:\Users\rayxc\AppData\Local\Temp\hstu_tables_submission_audit_hourly.json`
  to avoid overwriting the user's modified worktree artifact.

### Verdict

**The prior cover-letter and GrIT-breadth issues were materially fixed.** The
cover letter no longer names `v1.1.4-deposit`, and Section 5.1 now fences GrIT's
Industrial_and_Scientific / CDs_and_Vinyl numbers as literature context only,
not a comparator claim.

**The new top rejection risk is a generated-artifact integrity gap, not a
numerical contradiction.** The current worktree copy of
`_bestrec_run/hstu_tables.json` has been regenerated in default mode
(`"mode": "default"`, `"submission_gate.enforced": false`) while the committed
`HEAD` version is submission mode. `emit_latex_tables.py` and
`paper_tex/BUILD_NOTES.md` both state/assume the JSON is strict-build output, but
the LaTeX build path does not assert that condition or run
`build_hstu_tables.py --submission` before emitting tables. A top-journal
reviewer would read this as a bypass path around the claimed fail-closed
artifact discipline, even though the strict gate itself still passes when
invoked.

### Commands And Evidence Checked

- `git diff -- _bestrec_run/hstu_tables.json`
  - Confirmed the only tracked data-artifact diff is:
    `"mode": "submission" -> "default"` and
    `"submission_gate.enforced": true -> false`.
  - No cell values, tables, warnings, violations, or sources changed in this
    diff.
- `uv --project _bestrec_run run python _bestrec_run/build_hstu_tables.py --submission --tables-out "$env:TEMP\hstu_tables_submission_audit_hourly.json"`
  - PASS: `168` cells recomputed OK.
  - PASS: `149` exact paper checks, `19` within-rounding, `0` MISMATCH,
    `0` UNTRACEABLE, `4` retired `REMOVED_FROM_PAPER`.
  - PASS: all `14` declared claim families sourced.
- `uv --project _bestrec_run run python _bestrec_run/update_release_manifest.py --verify`
  - PASS: `153` files verified, `0` release-asset files missing locally.
- `uv --project _bestrec_run run python _bestrec_run/test_hstu_parity.py`
  - PASS: HSTU core-block parity exact in all asserted stages; max asserted
    diff `0.000e+00`.
- `uv --project _bestrec_run run python _bestrec_run/adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-18 19:23:13`, block `196799e7c46d`.
  - K=16 mean `0.03047`, sd `0.00011`, CI-LB `0.03033`, `5/5` seeds above
    both `0.0279` and `0.0271`.
  - K=8 mean `0.03029`, sd `0.00005`, CI-LB `0.03024`, `5/5` seeds above both
    references; comparability conditions OK.
- `uv --project _bestrec_run run python _bestrec_run/adjudicate_fir_breadth.py --no-append`
  - CONFIRMED at `2026-07-18 19:23:13`, block `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: `40` pages, `0` placeholder/forbidden failures, `20` informational
    SOTA/negated-claim review hits.
- `rg "v1\.1\.4-deposit|outcome pending|not part of any counted claim|Office never a passed category|SILLM4Rec|GrIT" ...`
  - Confirmed `COVER_LETTER_TORS.md` now uses version-agnostic deposit wording.
  - Confirmed the compiled/canonical paper contains the new GrIT breadth fence
    and no stale Office pending/no-claim wording.
- `paper_tex/BUILD_NOTES.md` and `_bestrec_run/emit_latex_tables.py`
  - Confirmed both describe `hstu_tables.json` as strict `--submission` output.
  - Confirmed `paper_tex/build.ps1` runs only `emit_latex_tables.py` before TeX
    compilation and hygiene scanning; it does not regenerate or assert the
    strict table JSON itself.

### External Fact-Check / Novelty Notes

- ACM's submissions page still instructs review manuscripts to use
  single-column `manuscript` format and names Primary Article Template LaTeX
  v2.16 for review submissions. Source:
  https://www.acm.org/publications/authors/submissions
- CTAN lists production `acmart` v2.19 dated `2026-06-27`; the local vendored
  `paper_tex/acmart.cls` remains v2.03 (`2024/02/04`). Source:
  https://ctan.org/tex-archive/macros/latex/contrib/acmart?lang=en
- Amazon Reviews 2023's official site confirms a 2023 McAuley Lab release with
  reviews, item metadata, links, standard splits, and 571.54M reviews. Source:
  https://amazon-reviews-2023.github.io/
- HSTU-BLaIR v3 confirms the manuscript's comparator constants: Video Games
  HSTU-BLaIR NDCG@10 `0.0760`, Office Products `0.0271`, Musical Instruments
  `0.0406`, with the same AR2023 5-core category statistics used by the
  manuscript. Source: https://arxiv.org/html/2504.10545v3
- GrIT confirms the manuscript's new literature fence: it uses AR2023
  Video Games, Industrial & Scientific, and CDs & Vinyl with matching 5-core
  statistics, standard leave-one-out, and full-item-set ranking; reported
  GrIT NDCG@10 values include Video Games `0.0588`, Industrial & Scientific
  `0.0286`, and CDs & Vinyl `0.0608`. Source:
  https://arxiv.org/html/2602.19728v1
- SID-MLP confirms another close same-statistics AR2023 semantic-ID line:
  Table 10 uses Musical Instruments `57,439 / 24,587 / 511,836`, Industrial &
  Scientific `50,985 / 25,848 / 412,947`, and Video Games
  `94,762 / 25,612 / 814,586`, with leave-one-out evaluation. Its reported
  Sid-Mlp++ NDCG@10 values in Table 14 (`0.0328`, `0.0244`, `0.0486`) do not
  threaten the paper's MI/Video_Games point-estimate framing, but the paper is
  right to cite it as same-statistics concurrent context. Source:
  https://arxiv.org/html/2605.12617v1
- UniSGR is correctly out of scope for AR2023 full-catalog LLOO comparison: it
  is an industrial semantic-ID generation-plus-ranking framework using
  multi-scenario pretraining, scenario-specific alignment, and online A/B
  testing on a real e-commerce platform. Source:
  https://arxiv.org/html/2607.04068v1
- DIGER is also correctly out of scope: it studies differentiable semantic IDs
  on B-Shop, I-Shop, and Yelp, with full-item-set leave-one-out, not this
  AR2023 HSTU-BLaIR category family. Source:
  https://arxiv.org/html/2601.19711v3
- ACERec is correctly out of scope for AR2023 claims: it uses the older
  Amazon Reviews collection cited to McAuley et al. (2015) across Sports,
  Beauty, Toys, Instruments, Office, and Baby, not AR2023. Source:
  https://arxiv.org/html/2602.13573v1
- SILLM4Rec remains a plausible under-inspection risk. The public repository
  supports the manuscript's non-comparability caveat because it generates image
  descriptions, user preference summaries, candidate ranking tasks, and SFT/DPO
  data; direct ACM full-text inspection is still better if accessible. Source:
  https://github.com/MKC-Lab/SILLM4Rec

### Confirmed Problems

1. **`_bestrec_run/hstu_tables.json` is in default mode in the current worktree.**
   This contradicts the standing submission-ready invariant that this generated
   JSON is strict `--submission` output. The strict output to temp is green, but
   the checked-in worktree artifact should not remain in non-submission mode.
2. **The LaTeX build path trusts `hstu_tables.json` without checking its mode.**
   `emit_latex_tables.py` says the source JSON is strict-build output, but it
   only loads the file and cross-checks numbers; it does not require
   `mode == "submission"`, `submission_gate.enforced == true`, and zero
   violations.
3. **`paper_tex/build.ps1`/`build.sh` do not force strict table regeneration.**
   They run the emitter, compile TeX, and scan the PDF. If the JSON was last
   produced by a default build, the PDF build can still succeed while the
   artifact-provenance claim says it used strict-build JSON.

### Confirmed Fixes / Non-Problems

- The stale cover-letter `v1.1.4-deposit` parenthetical is fixed.
- The GrIT breadth-category caveat is now present in the manuscript and TeX
  result section.
- The empirical numbers remain mechanically supported under a fresh strict
  table build to a temp output; no mismatches or untraceable cells were found.
- Release-manifest verification, HSTU parity, Office V3 adjudication,
  FIR-breadth adjudication, and TORS PDF hygiene all passed.
- The current post-deposit HEAD changes are response/companion/support
  documentation; the release boundary still needs to remain the `v1.1.5-deposit`
  tag rather than branch HEAD.

### Plausible Risks / Items Requiring Author Verification

- Decide whether generated artifacts are required to be submission-mode clean in
  the worktree at all times, or whether only the strict command output is
  authoritative. The current documentation implies the former.
- If authors intentionally allow default-mode table builds during development,
  the JSON should carry a loud non-submission warning and the LaTeX emitter
  should refuse it for submission builds.
- Direct SILLM4Rec ACM full-text inspection remains pending. Repository-based
  exclusion is plausible but weaker than full-paper protocol inspection.
- The vendored `acmart.cls` remains materially old relative to both ACM's review
  template guidance and CTAN production. This is still a venue-freeze decision,
  not just a cosmetic issue.

### Concrete Fixes To Make Next

1. Regenerate `_bestrec_run/hstu_tables.json` with
   `uv --project _bestrec_run run python _bestrec_run/build_hstu_tables.py --submission`
   before any submission freeze or PDF rebuild, and commit the strict-mode JSON.
2. Add a fail-closed assertion at the start of `_bestrec_run/emit_latex_tables.py`:
   require `mode == "submission"`, `submission_gate.enforced is true`,
   `submission_gate.violations == []`, `paper_check_summary.MISMATCH == 0`, and
   `paper_check_summary.UNTRACEABLE == 0`.
3. Preferably make `paper_tex/build.ps1` and `paper_tex/build.sh` run
   `build_hstu_tables.py --submission` before `emit_latex_tables.py`, so a
   clean TORS PDF cannot be produced from a default-mode generated JSON.
4. Keep the GrIT/SID-MLP/Latte/ChronoSID/DiffuReason paragraph fenced as
   "point-estimate/literature context only"; do not add any comparative claim
   against concurrent arXiv work without protocol-level audit.
5. Inspect the SILLM4Rec ACM full text if available, or retain the current
   explicit "pending direct full-text protocol inspection" caveat.
6. Make the acmart decision before freeze: either update to the current ACM/CTAN
   package and rebuild/hygiene-scan, or document why the Tectonic-compatible
   vendored v2.03 class is the chosen review artifact.

### Open Questions

- Was `_bestrec_run/hstu_tables.json` intentionally left in default mode after a
  development run, or should the automation restore/commit the strict-mode JSON?
- Should `emit_latex_tables.py` be treated as a submission-only tool that refuses
  default-mode JSON, or should it accept default mode only under an explicit
  `--dev` flag?
- Is the ACM SILLM4Rec full text accessible to the authors for a final protocol
  comparison?
- Will the final TORS upload use the 40-page `paper_tex/PAPER_TORS.pdf` and not
  the reader-format `PAPER_SUBMISSION.pdf`?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate current manuscript, TeX, PDF, cover-letter, release, companion, and
      generated-table artifacts.
- [x] Check commits since the prior remembered run.
- [x] Inspect working-tree status and diff for `_bestrec_run/hstu_tables.json`.
- [x] Run strict table build to a temporary output.
- [x] Verify release manifest.
- [x] Run HSTU parity test.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Re-run TORS PDF hygiene scan.
- [x] Search stale version and stale Office wording.
- [x] Inspect LaTeX emitter/build path for strict-mode enforcement.
- [x] Fact-check ACM/CTAN, AR2023, HSTU-BLaIR, GrIT, SID-MLP, UniSGR, DIGER,
      ACERec, and SILLM4Rec sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Restore/commit strict-mode `_bestrec_run/hstu_tables.json`.
- [ ] Add mode/assertion gate to `_bestrec_run/emit_latex_tables.py`.
- [ ] Make `paper_tex/build.*` force or verify strict table JSON before TeX.
- [ ] Inspect SILLM4Rec full text or keep the current caveat.
- [ ] Resolve the acmart class-version decision before freeze.

## Audit Run - 2026-07-18 17:18 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` /
  `2da36ea8a3c8b4809389af4105932acc3ffcf0d9`.
- Current run time: `2026-07-18 17:18:00` through `17:23:03 +10:00` for local
  commands and documentation.
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  using the `$HOME\.codex` fallback because `CODEX_HOME` is unset in this
  PowerShell session.
- New commits since the remembered 15:17 run:
  `a3eaf1b0` (`v1.1.5-deposit`) adds `.gitattributes`, bumps metadata and
  package builder to v1.1.5, updates `VENUE_PLAN.md`, and normalizes bundled
  text payloads to LF; `2da36ea8` adds the response section only.
- Working tree before this audit edit: no tracked modifications; untracked
  files remain `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Sources/artifacts inspected this run: `PAPER_REVIEW_AUDIT.md`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, `RELEASE_MANIFEST.json`,
  `.gitattributes`, `CANONICAL_SUBMISSION.md`, `README.md`,
  `DOI_DEPOSIT_INSTRUCTIONS.md`, `VENUE_PLAN.md`, `COVER_LETTER_TORS.md`,
  `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/hygiene_scan_output.txt`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/sections/*.tex`, `_bestrec_run/build_deposit_bundle.py`,
  `_release/bestrec_deposit_v1.1.5.zip`, local/remote tag metadata, and GitHub
  release metadata for `v1.1.5-deposit`.
- No manuscript, code, or release source was edited in this run; only this audit
  file was updated.

### Verdict

**The previous hard release-byte blocker is fixed in v1.1.5, and the empirical
claim machinery remains green.** The v1.1.5 zip, sidecar, bundled
`RELEASE_MANIFEST.json`, tag blob, and GitHub release asset metadata now agree
at the byte level for the manifest and at the payload-hash level for the zip.
Fresh strict rebuild, Office V3, and FIR-breadth adjudicators all pass.

**The main current rejection-risk item is narrower but still submission-facing:
the TORS cover letter still names `v1.1.4-deposit`.** Because it is a tracked
draft intended for editor upload, a top-journal reviewer/editor package should
not contain that stale parenthetical. The consistency gate should also inspect
cover-letter deposit mentions, or the cover letter should use only
version-agnostic wording.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` empirical cells recomputed; `0` untraceable; `0` paper
    mismatches; all `14` declared claim families sourced.
  - PASS: release-manifest hash verification OK for `153` files.
  - PASS: MI V2 gate and legacy Office V1 descriptive/VOID adjudication.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-18 17:19:23 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds above
    both references; comparability conditions OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - CONFIRMED at `2026-07-18 17:19:23 Australia/Sydney`, block
    `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- Release/tag/package checks:
  - `git rev-parse HEAD` = `2da36ea8a3c8b4809389af4105932acc3ffcf0d9`.
  - Local and remote `v1.1.5-deposit` resolve to
    `a3eaf1b01a14152c48101c7126ae76a956631ea2`.
  - `gh release view v1.1.5-deposit` reports `targetCommitish =
    a3eaf1b01a14152c48101c7126ae76a956631ea2`, not draft, not prerelease,
    published `2026-07-18T05:32:23Z`.
  - GitHub asset digests match local artifacts for the zip
    (`b4faeb42b67a0637e0be667a65e403026bef61c0bec28e7b8294d65a71b1817c`),
    sidecar asset (`272dd11e7a13f5061fd13464270a728b9ac96a5df32be66e1c14fa22890b177c`),
    `PAPER_SUBMISSION.pdf`
    (`ed6ba9c240a2a689907024cce8982a61a9758502541fd9a40d74acb3efd0e88c`),
    and `paper_tex/PAPER_TORS.pdf`
    (`6a40018016a3f428eb482d42559aa4a99f9c10963772c8f845c6f571bfe8356c`).
  - `_release/bestrec_deposit_v1.1.5.zip` has `66` entries; internal
    `SHA256SUMS.txt` has `65` payload rows; `0` missing payloads; `0` payload
    hash mismatches.
  - Bundled `RELEASE_MANIFEST.json` has `0` CRLFs, SHA256
    `72d0068fa5825d7608f4ff4f45a5152e951413f57a7b42353802dd7212aef8bb`;
    `git show v1.1.5-deposit:RELEASE_MANIFEST.json` has the same SHA256 and
    bytes. This directly fixes the v1.1.4 byte-drift defect.
- Line-ending checks:
  - `.gitattributes` now pins LF for text-like release inputs and binary mode
    for PDFs/zips/gz/png/pt/npz.
  - `git ls-files --eol` still reports `w/crlf` in the existing working tree for
    `.zenodo.json`, `CITATION.cff`, `DOI_DEPOSIT_INSTRUCTIONS.md`,
    `PAPER_SUBMISSION.md`, `README.md`, `RELEASE_MANIFEST.json`,
    `VENUE_PLAN.md`, and `paper_tex/paper-shared.tex`, while Git blobs are LF.
  - The v1.1.5 builder's payload normalization makes this harmless for the
    deposited zip, but it remains a local-documentation caveat for future
    byte-hash instructions.
- Stale-trigger sweep:
  - `COVER_LETTER_TORS.md` line 28 still says the current deposit tag is
    `v1.1.4-deposit`.
  - `DOI_DEPOSIT_INSTRUCTIONS.md` names `v1.1.5-deposit` as the current release;
    old v1.1.x tags appear there only in an explicit historical/superseded list.
  - `VENUE_PLAN.md` no longer names a stale concrete current tag; it points to
    `DOI_DEPOSIT_INSTRUCTIONS.md`.
  - `PAPER_SUBMISSION.pdf` and `paper_tex/PAPER_TORS.pdf` contain zero
    occurrences of `v1.1.4-deposit`, `outcome pending`, `Office is not counted`,
    or `not part of any counted claim`.
- PDF/hygiene checks:
  - `PAPER_SUBMISSION.pdf`: `46` pages.
  - `paper_tex/PAPER_TORS.pdf`: `40` pages.
  - `paper_tex/hygiene_scan_output.txt`: PASS, `40` pages, `0`
    placeholder/forbidden failures, `20` informational SOTA/non-claim review
    hits.

### External Fact-Check / Venue And Literature Notes

- ACM's author-submission page still instructs authors to submit review
  manuscripts in single-column format and says LaTeX authors should use
  `\documentclass[manuscript]{acmart}` with the ACM Primary Article Template
  v2.16, published August 28, 2025. Source:
  https://www.acm.org/publications/authors/submissions
- CTAN lists production `acmart` v2.19 dated `2026-06-27` and says the CTAN/ACM
  sites carry the production version while GitHub is development/experimental.
  Source: https://ctan.org/tex-archive/macros/latex/contrib/acmart
- The Amazon Reviews 2023 official page confirms the dataset is a 2023 McAuley
  Lab release with user reviews, item metadata, links, and standard splits.
  Source: https://amazon-reviews-2023.github.io/
- HSTU-BLaIR v3 reports the same 5-core AR2023 category statistics and the
  comparator NDCG@10 values used by the paper: Video Games `0.0760`, Office
  Products `0.0271`, Musical Instruments `0.0406`. Source:
  https://arxiv.org/html/2504.10545v3
- SILLM4Rec's public repository supports the current non-interchangeability
  caveat: it instructs users to download AR2023 5-core data, then generate image
  descriptions, user preference summaries, candidate product ranking tasks, and
  SFT/DPO training data. Source: https://github.com/MKC-Lab/SILLM4Rec
- Recent semantic-ID checks support the manuscript's caution around concurrent
  literature: Latte reports MI `0.0331` and Games `0.0515` in its AR2023
  experiments; ChronoSID reports MI output-level NDCG@10 `0.0345` vs ReSID
  `0.0325` and uses filtered MI statistics `57,359 / 23,742 / 490,522`, not the
  HSTU-BLaIR-family `57,439 / 24,587 / ~511,835`; DiffuReason reports a
  different "Video & Games" universe with `67,658 / 25,535 / 654,867`. Sources:
  https://arxiv.org/html/2605.06331,
  https://arxiv.org/html/2607.03918, and
  https://arxiv.org/html/2602.09744
- GrIT is the new related-work nuance for FIR breadth: its arXiv table reports
  AR2023 Video Games NDCG@10 `0.0588`, and also reports Industrial & Scientific
  and CDs & Vinyl NDCG@10 values. The paper's no-comparator boundary for FIR
  breadth remains defensible, but the existence of these external same-category
  numbers should be acknowledged or explicitly fenced before freeze. Source:
  https://arxiv.org/html/2602.19728v1

### Confirmed Problems

1. **`COVER_LETTER_TORS.md` still names `v1.1.4-deposit` as current.** This is
   stale after v1.1.5. It is not in the deposit bundle, but it is a
   submission-facing file and should not be sent to editors unchanged.
2. **The builder consistency gate does not check `COVER_LETTER_TORS.md`.** The
   previous audit's stale-doc class moved from `VENUE_PLAN.md` to the cover
   letter; a top-level sweep should cover every file intended for submission or
   DOI/upload support, even if not bundled.
3. **The local worktree still has CRLF bytes for several LF-pinned text files.**
   The tag and bundle are byte-clean, but local hash instructions must not imply
   that `Get-FileHash RELEASE_MANIFEST.json` in this current checkout equals the
   release asset; it does not (`2dc52f50...` locally vs `72d0068f...` in the tag,
   bundle, and GitHub asset).

### Confirmed Fixes / Non-Problems

- The v1.1.4 `RELEASE_MANIFEST.json` byte-boundary defect is fixed in the
  v1.1.5 deposit bundle and release asset.
- `VENUE_PLAN.md` now uses version-agnostic current-deposit wording and points
  to `DOI_DEPOSIT_INSTRUCTIONS.md`.
- `DOI_DEPOSIT_INSTRUCTIONS.md`, `README.md`, `CANONICAL_SUBMISSION.md`,
  `CITATION.cff`, and `.zenodo.json` are synchronized to v1.1.5 or
  version-agnostic current-deposit wording.
- Fresh strict rebuild, Office V3 adjudication, and FIR-breadth adjudication all
  pass; no numerical or claim-family mismatch was found.
- The compiled PDFs no longer contain stale Office pending/no-claim wording or
  the stale v1.1.4 tag.

### Plausible Risks / Items Requiring Author Verification

- SILLM4Rec still needs direct ACM full-text inspection if access is available.
  The current repo-based exclusion is plausible, but a reviewer may demand the
  protocol comparison from the paper itself.
- GrIT should be explicitly fenced for Industrial_and_Scientific and
  CDs_and_Vinyl before freeze, because those are now FIR-breadth categories with
  external concurrent same-category numbers. This is not a license to add a
  comparator claim; it is a literature-completeness disclosure.
- The existing checkout's CRLF files are harmless for v1.1.5 packaging but could
  cause confusion in future manual hash checks unless future instructions say
  "tag blob / release asset / bundled payload" rather than "local worktree
  file."
- `PAPER_SUBMISSION.pdf` is 46 pages while the TORS artifact is 40 pages. This
  appears intentional (reader edition vs ACM TORS format), but the upload plan
  must ensure the 40-page TORS PDF is the reviewed manuscript if TORS formatting
  is the chosen route.

### Concrete Fixes To Make Next

1. Update `COVER_LETTER_TORS.md` line 28 to remove the `v1.1.4-deposit`
   parenthetical or replace it with `v1.1.5-deposit`; version-agnostic wording
   is safer.
2. Extend `_bestrec_run/build_deposit_bundle.py::consistency_gate()` or add a
   separate release-readiness sweep to include `COVER_LETTER_TORS.md` and any
   other submission-support documents, not only bundled files.
3. Add a short note in DOI/release instructions that byte-level comparisons for
   text files should use Git blobs, release assets, or bundled payloads; do not
   compare the current CRLF worktree copy directly.
4. Before submission freeze, inspect SILLM4Rec's ACM full text if accessible; if
   not, keep the inspection-pending caveat and cite the repository workflow as
   the accessible basis.
5. Add one sentence in the related-work/freeze notes acknowledging that GrIT
   reports Industrial_and_Scientific and CDs_and_Vinyl numbers, while FIR
   breadth remains strictly an internal paired filter-vs-no-filter claim.
6. Keep the acmart refresh/build decision as a freeze blocker: ACM portal v2.16
   vs CTAN production v2.19 must be decided and verified with a rebuilt PDF.

### Open Questions

- Should `COVER_LETTER_TORS.md` be included in the deposit-readiness gate even
  though it is intentionally excluded from the archival zip?
- Should the project force-renormalize or re-checkout LF-pinned text files in
  this Windows workspace, or is builder-time normalization plus clear
  instructions sufficient?
- Is the ACM SILLM4Rec full text accessible through the maintainer's
  institution, or should the paper permanently disclose that the exclusion rests
  on repository/metadata evidence?
- Should `PAPER_SUBMISSION.pdf` remain a released reader edition once the TORS
  PDF is the actual venue artifact?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Identify current manuscript, TeX, PDF, release, response, and DOI/venue
      artifacts.
- [x] Check commits since the previous run and current working tree state.
- [x] Re-run strict rebuild.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Verify local/remote `v1.1.5-deposit` tag and GitHub release metadata.
- [x] Verify v1.1.5 zip payload hashes and manifest tag-vs-bundle bytes.
- [x] Check line-ending policy and current worktree EOL state.
- [x] Search current submission docs and PDFs for stale deposit/Office wording.
- [x] Check compiled PDF page counts and hygiene output.
- [x] Fact-check venue-template, AR2023, HSTU-BLaIR, SILLM4Rec, Latte,
      ChronoSID, DiffuReason, and GrIT sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Fix stale `COVER_LETTER_TORS.md` deposit parenthetical.
- [ ] Extend stale-version gate coverage to cover-letter/submission-support
      files.
- [ ] Inspect SILLM4Rec full paper or retain the inspection-pending caveat.
- [ ] Decide and execute acmart refresh at submission freeze.

## Audit Run - 2026-07-18 15:17 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` /
  `3d4748307ceaf60b742c6357e76cf5c070f24b53`.
- Current run time: `2026-07-18 15:17:59` through `15:21:31 +10:00` for the
  dynamic gates and release checks; audit documentation completed immediately
  afterward.
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  using the `$HOME\.codex` fallback because `CODEX_HOME` is unset in this
  PowerShell session.
- Working tree before this audit edit: no tracked modifications; untracked
  files remain `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- New commits since the remembered 13:16 run: `5df2512b` cut
  `v1.1.4-deposit`; `74163ecd` added the response section; `3d474830` changed
  only companion/explainer material (`PLAIN_LANGUAGE_COMPANION.md`,
  `companion_site/explainer.html`).
- Sources/artifacts inspected this run: `PAPER_REVIEW_AUDIT.md`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, `RELEASE_MANIFEST.json`,
  `CANONICAL_SUBMISSION.md`, `VENUE_PLAN.md`, `README.md`, `CITATION.cff`,
  `.zenodo.json`, `DOI_DEPOSIT_INSTRUCTIONS.md`, `COVER_LETTER_TORS.md`,
  `PAPER_SUBMISSION.md`, `paper_tex/main.tex`, `paper_tex/sections/*.tex`,
  `paper_tex/hygiene_scan_output.txt`, `_bestrec_run/build_deposit_bundle.py`,
  `_release/bestrec_deposit_v1.1.4.zip`, `_release/*.sha256`, local and remote
  `v1.1.4-deposit` tag metadata, and downloaded GitHub release assets.
- No manuscript, code, or package source was edited in this run; only this audit
  file was updated.

### Verdict

**The empirical paper is still green and the v1.1.3 semantic release defect is
largely repaired, but the package is not yet freeze-clean.** The new v1.1.4
release fixes the serious prior contradictions: CFF/Zenodo are now `1.1.4`, the
cover letter no longer names the old deposit, uploaded assets match local
hashes, the zip payload hashes verify, and the strict artifact graph still
passes.

The new top problem is narrower but real: the v1.1.4 response and release title
say the tag tree and assets are "provably identical," yet the tag's
`RELEASE_MANIFEST.json` blob is LF-normalized by Git while the uploaded/bundled
manifest is the Windows working-tree CRLF copy. Normalized content is identical,
so this is not a stale-manifest semantic defect; byte hashes differ, so the
public byte-identity claim is false.

The second concrete miss is documentation coverage: `VENUE_PLAN.md` still says
the current deposit tag is `v1.1.3-deposit`. The new consistency gate does not
cover that file, even though the bundle includes it.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` empirical cells recomputed; `0` untraceable; `0` paper
    mismatches; all `14` declared claim families sourced.
  - PASS: release-manifest hash verification OK for `153` files.
  - PASS: MI V2 gate; legacy Office V1 descriptive/VOID check remains OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-18 15:19:18 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds
    above both references.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - CONFIRMED at `2026-07-18 15:19:18 Australia/Sydney`, block
    `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- Release/tag checks:
  - Local and remote `v1.1.4-deposit` tag both resolve to
    `5df2512bce92658139c114bcf4c38263b3295b27`.
  - `gh release view v1.1.4-deposit` reports `targetCommitish =
    5df2512bce92658139c114bcf4c38263b3295b27`, not draft, not prerelease,
    published `2026-07-18T03:31:25Z`.
  - Downloaded GitHub assets match local hashes:
    `bestrec_deposit_v1.1.4.zip` =
    `85ae31b79951c3d2f102f2bd419c0297575dc0bc351b7913893d6486c23de97f`;
    `RELEASE_MANIFEST.json` =
    `6a2c337a98ee612e2a66fb80856f0021f0197720694233f1a54e09f7a2e39641`;
    `PAPER_TORS.pdf` =
    `6a40018016a3f428eb482d42559aa4a99f9c10963772c8f845c6f571bfe8356c`;
    `PAPER_SUBMISSION.pdf` =
    `ed6ba9c240a2a689907024cce8982a61a9758502541fd9a40d74acb3efd0e88c`.
  - Local `_release/bestrec_deposit_v1.1.4.zip.sha256` matches the local zip
    hash exactly.
- Bundle checks:
  - `_release/bestrec_deposit_v1.1.4.zip` has `66` entries; internal
    `SHA256SUMS.txt` has `65` payload rows; `0` missing payloads; `0` payload
    hash mismatches.
  - Bundled `CITATION.cff` contains `version: "1.1.4"`.
  - Bundled `.zenodo.json` contains `"version": "1.1.4"`.
  - Bundled manifest has `git_commit =
    f05ed267a9c79f9200ccd81468b85008f252a507`, consistent with the documented
    "parent commit whose tree was hashed" semantics.
  - `git show v1.1.4-deposit:RELEASE_MANIFEST.json` and the bundled manifest
    are semantically equal after CRLF-to-LF normalization, but not byte-equal:
    tag blob SHA256
    `caf61ec59d919fa884fa5ee9b0c8a75b8017b5d1713104f3f479492ccb69ee38`;
    bundled/uploaded/local SHA256
    `6a2c337a98ee612e2a66fb80856f0021f0197720694233f1a54e09f7a2e39641`;
    tag CRLF count `0`, bundled CRLF count `380`.
- Line-ending checks:
  - `.gitattributes`: missing.
  - `git config --get core.autocrlf`: `true`.
  - `git ls-files --eol` reports `i/lf w/crlf` for `.zenodo.json`,
    `CITATION.cff`, `DOI_DEPOSIT_INSTRUCTIONS.md`, `README.md`,
    `RELEASE_MANIFEST.json`, `VENUE_PLAN.md`, and
    `_bestrec_run/build_deposit_bundle.py`.
- Stale-trigger sweep:
  - `VENUE_PLAN.md` line 37 still says current deposit tag
    `v1.1.3-deposit`.
  - `DOI_DEPOSIT_INSTRUCTIONS.md` names `v1.1.4-deposit` and correctly says
    `SHA256SUMS.txt` covers every payload entry, not itself.
  - `CANONICAL_SUBMISSION.md` and `COVER_LETTER_TORS.md` now use the v1.1.4
    boundary or a version-agnostic current-deposit reference.
- Compiled artifact checks:
  - `paper_tex/hygiene_scan_output.txt`: PASS, `PAPER_TORS.pdf`, 40 pages,
    `0` placeholder/forbidden failures, `20` informational SOTA/non-claim
    review hits.

### External Fact-Check / Venue And Literature Notes

- ACM's author-submission page still instructs authors to submit review
  manuscripts in single-column format and says LaTeX authors should use
  `\documentclass[manuscript]{acmart}` with the ACM Primary Article Template
  v2.16, published August 28, 2025. Source:
  https://www.acm.org/publications/authors/submissions
- CTAN lists production `acmart` v2.19 dated `2026-06-27`; its README says the
  production version is on CTAN and ACM sites, while GitHub is development or
  experimental. Source:
  https://ctan.org/tex-archive/macros/latex/contrib/acmart
- The Amazon Reviews 2023 official page confirms the dataset is a 2023 McAuley
  Lab release with user reviews, item metadata, links, and standard splits.
  Source: https://amazon-reviews-2023.github.io/
- HSTU-BLaIR v3 reports 5-core AR2023 Video Games, Office Products, and Musical
  Instruments statistics and the comparator NDCG@10 values used by the paper:
  Video Games `0.0760`, Office Products `0.0271`, Musical Instruments
  `0.0406`. Source: https://arxiv.org/html/2504.10545v3
- SILLM4Rec's public repository instructs users to download AR2023 5-core files
  and then generate image descriptions, user preference summaries, candidate
  product ranking tasks, and SFT/DPO data. This supports the current
  non-interchangeability caveat, but it is still weaker than direct full-paper
  protocol inspection. Source: https://github.com/MKC-Lab/SILLM4Rec
- FMLP-Rec and BSARec remain strong prior art for frequency-filter motivation:
  FMLP-Rec proposes learnable frequency-domain filters for sequential
  recommendation, and BSARec explicitly argues self-attention is low-pass and
  uses frequency rescaling. This supports the paper's narrow "incremental,
  left-causal FIR realization" novelty boundary. Sources:
  https://arxiv.org/abs/2202.13556 and https://arxiv.org/html/2312.10325v1

### Confirmed Problems

1. **v1.1.4's byte-identity claim is false for `RELEASE_MANIFEST.json`.** The
   contents normalize to the same text, but the tag blob is LF and the release
   asset/bundle copy is CRLF. The response and release title should not claim
   byte identity unless the release assets are generated from normalized Git
   blobs or `.gitattributes` enforces a stable on-disk line ending.
2. **`VENUE_PLAN.md` still names `v1.1.3-deposit` as current.** Because the
   deposit bundle includes `VENUE_PLAN.md`, this stale tag pointer can be seen
   by a reviewer and contradicts the v1.1.4 DOI instructions.
3. **The new consistency gate is incomplete for files included in the deposit
   bundle.** It checks README/CANONICAL/DOI/CFF/Zenodo/manifest boundary, but
   not `VENUE_PLAN.md` and not line-ending/byte-identity invariants.
4. **Cross-platform bundle reproducibility is not defined.** With no
   `.gitattributes` and `core.autocrlf=true`, a Linux reviewer rebuilding the
   bundle from the same tag can produce different text-file bytes and therefore
   different internal payload hashes.
5. **Submission freeze items remain open.** The acmart refresh, SILLM4Rec
   full-text inspection, DOI minting, and cover-letter bracket fields are still
   pending.

### Confirmed Fixes / Non-Problems

- The prior v1.1.3 semantic/source mismatch is repaired by a fresh v1.1.4 tag
  and release; local and remote tags agree.
- The v1.1.4 zip, sidecar, manifest asset, and both PDF release assets match
  local hashes.
- The v1.1.4 bundle's internal payload hashes verify with `0` missing and `0`
  mismatching payloads.
- Bundled CFF and Zenodo metadata now say `1.1.4`.
- `DOI_DEPOSIT_INSTRUCTIONS.md` correctly describes `SHA256SUMS.txt` as
  covering payload entries rather than itself.
- The strict empirical/artifact graph, Office V3 adjudicator, FIR-breadth
  adjudicator, and compiled-PDF hygiene scan all remain green.
- The manuscript's novelty/SOTA boundaries remain cautious on the checked
  claims: Video_Games is competitive but not SOTA; MI and Office V3 are
  per-category point-estimate comparisons only; FIR breadth is internal paired
  filter-vs-no-filter evidence only.

### Plausible Risks / Items Requiring Author Verification

- If the project intends normalized text equality, rather than byte equality,
  to define the release boundary, say so plainly and remove "provably identical"
  byte-style wording.
- If byte-for-byte reproducibility is desired, the builder should read text
  payloads from Git blobs or normalize them to LF before zipping, and a
  `.gitattributes` file should pin repository text files.
- The post-deposit companion commit is probably outside the paper deposit
  boundary, but the README/DOI docs should avoid implying latest branch HEAD is
  the archival snapshot.
- SILLM4Rec remains accessible only through ACM metadata and repository
  workflow in this audit; full-text protocol inspection is still the stronger
  freeze-time check.

### Concrete Fixes To Make Next

1. Add an explicit line-ending policy, preferably `.gitattributes` with LF for
   repository text artifacts that enter releases, then regenerate/rebuild the
   bundle from normalized content.
2. Either re-cut a `v1.1.5-deposit` with byte-stable assets or revise the
   v1.1.4 response/release wording to say "normalized content equal" instead of
   "tag tree and assets provably identical."
3. Update `VENUE_PLAN.md`'s DOI section to `v1.1.4-deposit` or make it
   version-agnostic like the cover letter.
4. Extend `_bestrec_run/build_deposit_bundle.py::consistency_gate()` to check
   every bundled documentation file that names the current deposit, including
   `VENUE_PLAN.md`, and add a release-round-trip check for tag-vs-bundle
   normalized/byte equality according to the chosen policy.
5. Keep the freeze checklist live: SILLM4Rec full-text inspection, acmart
   v2.16-vs-v2.19 decision plus rebuild, DOI minting, and cover-letter
   maintainer fields.

### Open Questions

- Does the archival standard require byte identity between Git blobs and release
  text assets, or is normalized textual equivalence sufficient if documented?
- Should future deposit zips be generated from the tag tree (`git archive` or
  `git show` blobs) rather than the local working tree?
- Should `VENUE_PLAN.md` be included in the deposit bundle if it is a live
  maintainer checklist rather than a stable archival artifact?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Confirm branch, HEAD, working-tree status, recent commits, and
      local/remote release-tag state.
- [x] Inspect response, canonical map, venue plan, DOI instructions,
      citation/Zenodo metadata, cover letter, release manifest, and bundle
      builder.
- [x] Re-run strict artifact graph rebuild.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Verify local and downloaded `v1.1.4` zip/manifest/PDF hashes.
- [x] Verify zip payload hashes against bundle-internal `SHA256SUMS.txt`.
- [x] Compare tag `RELEASE_MANIFEST.json` with bundled/uploaded/current
      `RELEASE_MANIFEST.json`, including line-ending normalization.
- [x] Check repository line-ending policy and Git EOL status.
- [x] Check compiled PDF hygiene output.
- [x] Check ACM/CTAN template guidance, AR2023/HSTU-BLaIR constants,
      SILLM4Rec public workflow evidence, and frequency-filter prior art.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Define and enforce the tag-vs-bundle byte/normalization policy.
- [ ] Repair stale `VENUE_PLAN.md` v1.1.3 DOI pointer.
- [ ] Verify ACM-current template compatibility.
- [ ] Inspect SILLM4Rec full paper or retain the inspection-pending caveat.

## Audit Run - 2026-07-18 13:16 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` /
  `f05ed267a9c79f9200ccd81468b85008f252a507`.
- Current run time: `2026-07-18 13:16:49` through `13:17:41 +10:00` for the
  dynamic gates; audit documentation completed immediately afterward.
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  using the `$HOME\.codex` fallback because `CODEX_HOME` is unset in this
  PowerShell session.
- Working tree before this audit edit: no tracked modifications; untracked
  files remain `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Sources/artifacts inspected this run: `PAPER_REVIEW_AUDIT.md`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, `RELEASE_MANIFEST.json`,
  `CANONICAL_SUBMISSION.md`, `VENUE_PLAN.md`, `README.md`, `CITATION.cff`,
  `.zenodo.json`, `DOI_DEPOSIT_INSTRUCTIONS.md`, `COVER_LETTER_TORS.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.md`, `paper_tex/main.tex`,
  `paper_tex/paper-shared.tex`, `paper_tex/acmart.cls`,
  `paper_tex/hygiene_scan_output.txt`, `paper_tex/sections/*.tex`,
  `_release/bestrec_deposit_v1.1.3.zip`, and the public GitHub
  `v1.1.3-deposit` release metadata.
- No manuscript, code, or package source was edited in this run; only this audit
  file was updated.

### Verdict

**The empirical paper remains green, but the release package is still not
freeze-ready.** The new response commits fixed much of the prior canonical-map
drift: `CANONICAL_SUBMISSION.md` now points at `v1.1.3-deposit`, includes Office
V3 and FIR-breadth evidence, and uses the safer "per-category point-estimate
comparisons" wording. The public `v1.1.3` release exists; uploaded zip,
sidecar, and manifest hashes match the local files; the zip's payload hashes
verify; and the strict empirical gate passes.

The hard problem is provenance topology. The release tag itself still points at
commit `160e08d5`, whose repository copy of `RELEASE_MANIFEST.json` is stale:
it names `v1.1.2-deposit` and records `git_commit = 89d7bb6...`. The release
assets and local HEAD contain the corrected manifest instead. This makes the
source tag, release assets, and current tree non-identical at exactly the file
that is supposed to define the artifact boundary. A top-journal artifact
reviewer can reasonably reject or request repair for that alone.

A second package problem is metadata drift: the `v1.1.3` bundle includes
`CITATION.cff` and `.zenodo.json`, but both still say version `1.1.2`. The cover
letter also still points at `v1.1.2-deposit`. These are easy fixes, but they are
submission-facing contradictions.

No new empirical contradiction, table mismatch, Office V3 failure, FIR-breadth
failure, or compiled-PDF hygiene failure was found.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` empirical cells recomputed; `0` untraceable; `0` paper
    mismatches; all `14` declared claim families sourced.
  - PASS: release-manifest hash verification OK for `153` local files.
  - PASS: MI V2 gate; legacy Office V1 descriptive/VOID check remains OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-18 13:17:41 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds
    above both references.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - CONFIRMED at `2026-07-18 13:17:41 Australia/Sydney`, block
    `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- Release/tag checks:
  - Local `_release/bestrec_deposit_v1.1.3.zip` SHA256:
    `8f8b7a33dfbd71657476eabdb0cc1b9794adec1f0d14553627ff92e04e1054db`.
  - Local `.zip.sha256` sidecar matches the same hash.
  - `gh release view v1.1.3-deposit` shows uploaded zip digest
    `sha256:8f8b7a33dfbd71657476eabdb0cc1b9794adec1f0d14553627ff92e04e1054db`;
    uploaded `RELEASE_MANIFEST.json` digest
    `sha256:a4bd6faf0ed358c624bf8a4c73ce319f580f6e97fa4e9e02bcb228fe979a7eb5`;
    release published `2026-07-18T02:32:03Z`; not draft/prerelease.
  - Downloaded `RELEASE_MANIFEST.json` from the release matches local HEAD hash
    `a4bd6faf0ed358c624bf8a4c73ce319f580f6e97fa4e9e02bcb228fe979a7eb5`.
  - `git ls-remote --tags origin v1.1.3-deposit` and local
    `git rev-parse 'v1.1.3-deposit^{commit}'` both resolve to
    `160e08d5761fd89e6cf5a5f84b1623710092499f`.
  - `git show v1.1.3-deposit:RELEASE_MANIFEST.json` still reports
    `release = ... v1.1.2-deposit ...` and
    `git_commit = 89d7bb695760bb9ab9e140831f24983e4192f064`.
  - The `v1.1.3` zip's bundled `RELEASE_MANIFEST.json` reports the corrected
    version-agnostic release label and
    `git_commit = 160e08d5761fd89e6cf5a5f84b1623710092499f`.
- Bundle checks:
  - `_release/bestrec_deposit_v1.1.3.zip` contains `66` files including
    `SHA256SUMS.txt`; `SHA256SUMS.txt` covers `65` payload files with `0`
    missing and `0` hash mismatches. The DOI row's "65 entries" is defensible
    only if it means payload entries; its "SHA256SUMS covers every entry"
    wording should say "every payload entry" because it does not self-hash.
  - Bundled `.zenodo.json` contains `"version": "1.1.2"`.
  - Bundled `CITATION.cff` contains `version: "1.1.2"`.
- Stale-trigger sweep:
  - `CANONICAL_SUBMISSION.md` now names `v1.1.3-deposit`, lists
    `PREREG_OFFICE_V3.md` and `PREREG_FIR_BREADTH.md`, and uses
    "per-category point-estimate comparisons" rather than "comparator wins".
  - `DOI_DEPOSIT_INSTRUCTIONS.md` points upload instructions at
    `bestrec_deposit_v1.1.3.zip`.
  - `COVER_LETTER_TORS.md` still names `v1.1.2-deposit`.
  - `CITATION.cff` and `.zenodo.json` still say version `1.1.2`.
  - `PAPER_DRAFT.md` still contains the old `Office stays VOID` /
    `outcome is pending` phrase in a historical v3.8 line, but the top banner
    now explicitly says those older entries are superseded and not current
    claims.
- Compiled artifact checks:
  - `paper_tex/hygiene_scan_output.txt`: PASS, `PAPER_TORS.pdf`, 40 pages, `0`
    placeholder/forbidden failures, `20` informational SOTA/non-claim review
    hits.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages, 612 x 792 pt.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 42 pages, 486 x 720 pt.
  - `PAPER_SUBMISSION.pdf`: 46 pages, 612 x 792 pt.

### External Fact-Check / Venue And Literature Notes

- ACM's author-submission page says review manuscripts should be single-column
  and tells LaTeX authors to use `\documentclass[manuscript]{acmart}` with the
  ACM Primary Article Template. It currently names portal version `2.16`
  published `2025-08-28`. Source:
  https://www.acm.org/publications/authors/submissions
- ACM's Primary Article Template page likewise lists the LaTeX template as
  `Version 2.16` with last update `August 28, 2025`. Source:
  https://www.acm.org/publications/proceedings-template
- CTAN now lists `acmart` `Version 2.19 2026-06-27`; the acmart repository
  changelog also lists v2.19 after v2.18/v2.17/v2.16 and says production
  versions are on CTAN/ACM sites. This means the freeze checklist should not
  hard-code only v2.16 without deciding whether TORS wants ACM's portal bundle
  or the latest CTAN production package. Sources:
  https://ctan.org/pkg/acmart and https://github.com/borisveytsman/acmart
- SILLM4Rec's public repository instructs users to download AR2023 5-core files
  and then generate image descriptions, user preference summaries, candidate
  product ranking tasks, and SFT/DPO training data. This supports the paper's
  non-interchangeability caveat, but direct full-text inspection of DOI
  `10.1145/3743093.3771011` remains the stronger freeze-time check. Source:
  https://github.com/MKC-Lab/SILLM4Rec

### Confirmed Problems

1. **`v1.1.3-deposit` tag/source and release assets are inconsistent.** The
   tag points at a commit whose `RELEASE_MANIFEST.json` is stale; the uploaded
   manifest and zip contain the corrected file from a later commit. This should
   be repaired with a clean new deposit tag or an explicitly documented retag
   policy plus a fresh round-trip check from a tag checkout.
2. **Deposit DOI metadata is stale inside the current bundle.** Both
   `CITATION.cff` and `.zenodo.json` in `bestrec_deposit_v1.1.3.zip` still say
   version `1.1.2`.
3. **Cover letter still references the superseded deposit.** Its artifact
   statement names `v1.1.2-deposit`, not `v1.1.3-deposit`, and maintainer
   bracket fields remain.
4. **Venue template target is stale/underspecified.** Local `acmart.cls` is
   v2.03; `VENUE_PLAN.md` says to refresh to v2.16, but CTAN now exposes v2.19.
   The final rule should be "current ACM/CTAN package as required by TORS",
   tested by a real rebuild, not a fixed old version string.
5. **DOI instructions overstate zip hash coverage.** The bundle has 66 files
   including `SHA256SUMS.txt`; the sidecar covers the 65 payload files. This is
   expected, but the text should say "payload entries" rather than "every
   entry".

### Confirmed Fixes / Non-Problems

- `CANONICAL_SUBMISSION.md` no longer carries the prior v1.0/v1.1.2 source-map
  drift; it now lists current prereg/results artifacts and the v1.1.3 deposit
  chain.
- Local and uploaded `v1.1.3` zip hashes match; uploaded and local corrected
  release-manifest hashes match.
- The strict empirical/artifact graph remains green at current HEAD.
- Office V3 and FIR-breadth adjudicators remain green under frozen wording.
- `PAPER_DRAFT.md` now has a sufficiently explicit historical-status banner;
  the stale phrase is a search-risk, not a current-claim contradiction.
- The compiled TORS hygiene scan remains PASS.

### Plausible Risks / Items Requiring Author Verification

- If the authors intend release assets, not the git tag, to be the only
  authoritative deposit boundary, that needs to be stated plainly. Most
  artifact reviewers will inspect both the tag and the assets.
- The CFF/Zenodo version may have been intentionally left at `1.1.2` as a
  semantic software version, but the current DOI instructions and GitHub release
  naming treat `1.1.3` as the active archival bundle. The versioning policy
  needs one story.
- SILLM4Rec remains accessible only through metadata/repo evidence in this
  audit. Full-text protocol inspection should remain a freeze blocker or the
  manuscript should keep its current inspection-pending caveat.
- The ACM portal currently lags CTAN on the displayed version. TORS may prefer
  the ACM portal bundle over CTAN; the final submission checklist should record
  which authority was followed.

### Concrete Fixes To Make Next

1. Cut a fresh `v1.1.4-deposit` at a commit whose repository
   `RELEASE_MANIFEST.json`, bundled `RELEASE_MANIFEST.json`, uploaded manifest
   asset, and release tag all agree; alternatively retag `v1.1.3` only if the
   project policy explicitly permits mutable deposit tags.
2. Update `.zenodo.json` and `CITATION.cff` to version `1.1.3` (or document a
   deliberate semantic-version exception) before any DOI minting.
3. Update `COVER_LETTER_TORS.md` to point at the current deposit and leave only
   true maintainer-only fields bracketed.
4. Refresh `VENUE_PLAN.md`'s acmart freeze item to account for CTAN v2.19 vs ACM
   portal v2.16, then test the final paper under the chosen current template.
5. Clarify `DOI_DEPOSIT_INSTRUCTIONS.md`: `SHA256SUMS.txt` covers every payload
   entry, not itself.
6. Inspect the SILLM4Rec ACM full text if accessible, or keep the explicit
   inspection-pending exclusion rationale.

### Open Questions

- Is a deposit tag expected to be an immutable source snapshot, or only a handle
  for GitHub release assets? The current package implicitly uses both.
- Should Zenodo/CFF `version` always match the current deposit patch tag, or is
  there a separate artifact/software-version policy?
- For TORS, should the final build use ACM's portal-published template bundle
  or CTAN's current production `acmart` package when the two differ?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Confirm branch, HEAD, working-tree status, and release-tag state.
- [x] Inspect current canonical map, venue plan, DOI instructions, citation/
      Zenodo metadata, cover letter, release manifest, and response file.
- [x] Verify local and uploaded `v1.1.3` zip/manifest hashes.
- [x] Verify zip payload hashes against bundle-internal `SHA256SUMS.txt`.
- [x] Compare release-tag `RELEASE_MANIFEST.json` with bundled/uploaded/current
      `RELEASE_MANIFEST.json`.
- [x] Re-run strict artifact graph rebuild.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Check compiled PDF page counts and hygiene output.
- [x] Check ACM/CTAN template guidance and SILLM4Rec public workflow evidence.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair release tag/source/asset boundary.
- [ ] Synchronize CFF/Zenodo/cover-letter versions with the current deposit.
- [ ] Clarify the zip `SHA256SUMS` payload boundary.
- [ ] Verify ACM-current template compatibility.
- [ ] Inspect SILLM4Rec full paper or retain the inspection-pending caveat.

## Audit Run - 2026-07-18 12:16 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` /
  `89d7bb695760bb9ab9e140831f24983e4192f064`.
- Current run time: `2026-07-18 12:16:10` through `12:18:12 +10:00` for the
  dynamic gates; audit documentation completed immediately afterward.
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  using the `$HOME\.codex` fallback because `CODEX_HOME` is unset in this
  PowerShell session.
- Working tree before this audit edit: no tracked modifications; untracked
  files remain `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Sources/artifacts inspected this run: `README.md`,
  `README_LC2C_HISTORICAL.md`, `CITATION.cff`, `.zenodo.json`,
  `DOI_DEPOSIT_INSTRUCTIONS.md`, `COVER_LETTER_TORS.md`,
  `RELEASE_MANIFEST.json`, `CANONICAL_SUBMISSION.md`, `VENUE_PLAN.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.md`, `paper_tex/acmart.cls`,
  `paper_tex/hygiene_scan_output.txt`, `paper_tex/sections/*.tex`,
  `_bestrec_run/build_deposit_bundle.py`,
  `_release/bestrec_deposit_v1.1.2.zip`, and the public GitHub
  `v1.1.2-deposit` release metadata.
- No manuscript or code source was edited in this run; only this audit file was
  updated.

### Verdict

**The prior package fire drill is mostly fixed, but the submission is still not
freeze-ready.** The root README no longer points reviewers at the wrong LC2C
paper; citation/Zenodo metadata now reflect the current claim boundary; the DOI
manual-upload instruction points to the current `v1.1.2` zip; a TORS cover
letter draft exists; and the public GitHub release contains a zip whose digest
matches the local bundle.

The new top risk is the provenance boundary: `RELEASE_MANIFEST.json` now names
`v1.1.2-deposit` but still records `git_commit = c4cb410...`, while HEAD is
`89d7bb6...` and the intervening commits changed several public/package files.
Because the manifest says its hashes describe files as of `git_commit`, this is
a reviewer-visible self-consistency defect even though the strict hash verifier
passes.

The second risk is canonical documentation drift. `CANONICAL_SUBMISSION.md`
correctly states the current claim set, but its artifact graph still names
`v1.0-deposit` as the deposit bundle and omits the Office V3 and FIR-breadth
pre-registrations from its prereg chain bullet. Since that file says it governs
the submission, a reviewer can reasonably treat this as the authoritative
package map.

The numerical and claim gates remain green. No empirical-cell mismatch, Office
V3 adjudicator failure, FIR-breadth adjudicator failure, or compiled-PDF hygiene
failure was found.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` empirical cells recomputed; `0` untraceable; `0` paper
    mismatches; all `14` declared claim families sourced.
  - PASS: release-manifest hash verification OK for `153` local files.
  - PASS: MI V2 gate; legacy Office V1 descriptive/VOID check remains OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-18 12:18:12 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds
    above both references.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - CONFIRMED at `2026-07-18 12:18:12 Australia/Sydney`, block
    `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- Deposit/release checks:
  - Local `_release/bestrec_deposit_v1.1.2.zip` SHA256:
    `11926b8d3d6ba9712a6245d9642dc04676627e299f7df1e7e424205be373fd9a`.
  - Local `.zip.sha256` sidecar matches the same hash.
  - `gh release view v1.1.2-deposit` shows uploaded asset
    `bestrec_deposit_v1.1.2.zip` with digest
    `sha256:11926b8d3d6ba9712a6245d9642dc04676627e299f7df1e7e424205be373fd9a`,
    plus `PAPER_SUBMISSION.pdf`, `PAPER_TORS.pdf`, and
    `RELEASE_MANIFEST.json`; release published `2026-07-17T21:53:53Z`.
  - Zip inventory contains 65 entries and includes the updated README,
    citation/Zenodo metadata, DOI instructions, `PAPER_SUBMISSION.md/.pdf`,
    `paper_tex/PAPER_TORS.pdf`, prereg/results docs, adjudicators, and manifest.
- Stale-trigger sweep:
  - `README.md` no longer presents the LC2C/EASE paper as current; LC2C is
    preserved only through `README_LC2C_HISTORICAL.md`.
  - `CITATION.cff` and `.zenodo.json` now describe version `1.1.2`, Office V3,
    FIR breadth, and no SOTA/no paired-superiority boundaries.
  - `DOI_DEPOSIT_INSTRUCTIONS.md` Option B now points to
    `bestrec_deposit_v1.1.2.zip`.
  - `PAPER_DRAFT.md` still contains the stale phrases `Office stays VOID` and
    `outcome is pending` in a historical v3.8 status paragraph, but the file
    now opens with v3.9 stating that Office V3 passed and v3.8 is superseded.
  - `paper_tex/hygiene_scan_output.txt` remains PASS: `PAPER_TORS.pdf`,
    40 pages, `0` placeholder/forbidden failures, `20` informational
    SOTA/non-claim review hits.

### External Fact-Check / Venue And Literature Notes

- ACM's current submission instructions say review manuscripts should be single
  column and tell LaTeX authors to use the latest Primary Article Template with
  the `manuscript` option; the page names version `2.16`, published
  `2025-08-28`. Source:
  https://www.acm.org/publications/authors/submissions
- ACM's Primary Article Template page also lists the LaTeX template as version
  `2.16` with last update `2025-08-28`. This confirms that the vendored
  `paper_tex/acmart.cls` v2.03 (`2024/02/04`) is stale. Source:
  https://www.acm.org/publications/proceedings-template
- SILLM4Rec's ACM record identifies the paper
  "Self-Improving with Chain of Thought Enhanced Preference Optimization for
  Multimodal Recommendation" with DOI `10.1145/3743093.3771011`; the public
  GitHub repository describes image-description generation, user preference
  summaries, candidate product ranking tasks, and SFT/DPO training data. This
  supports the manuscript's current non-interchangeability caveat, but not as
  strongly as full-paper protocol inspection would. Sources:
  https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec

### Confirmed Problems

1. **Manifest commit boundary is stale.** `RELEASE_MANIFEST.json` records
   `git_commit = c4cb410...`; current HEAD is `89d7bb6...`; the manifest says
   its hashes describe files as of `git_commit`. Fix by regenerating the
   manifest at the actual deposit/source boundary, or explicitly redefining the
   field so it no longer pretends to be the current source-state commit.
2. **Canonical source map is stale.** `CANONICAL_SUBMISSION.md` still says the
   GitHub deposit is `v1.0-deposit`, and its prereg chain bullet omits
   `PREREG_OFFICE_V3.md` and `PREREG_FIR_BREADTH.md`.
3. **Venue template remains outdated.** The local `acmart.cls` is v2.03; ACM's
   current official instructions point to v2.16. This can stay deferred only if
   the paper is not being submitted yet.
4. **Cover letter is a draft, not a submission artifact.** Required
   declarations are present, but bracketed maintainer fields remain.

### Confirmed Fixes / Non-Problems

- The root README now represents the current paper and clearly quarantines the
  old LC2C README as historical.
- Citation and Zenodo metadata now carry the current version and narrow claim
  boundary.
- DOI manual-upload instructions now point to `bestrec_deposit_v1.1.2.zip`, not
  the stale v1.0 zip.
- The `v1.1.2-deposit` release is public, not draft/prerelease, and the uploaded
  zip digest matches the local zip.
- No strict-gate numerical failure, Office V3 failure, FIR-breadth failure, or
  PDF hygiene failure was found.

### Plausible Risks / Items Requiring Author Verification

- `PAPER_DRAFT.md` remains in the deposit and still contains obsolete status
  phrases in historical changelog text. This is probably defensible if the
  archive treats it as a working draft, but a top-journal package would be
  cleaner if the deposit included only canonical/submission artifacts or moved
  historical status logs out of the DOI bundle.
- The SILLM4Rec exclusion remains pending direct full-text inspection. The
  public repository strongly suggests a non-full-catalog ranking workflow, but
  the ACM paper's experiment protocol should be inspected or the manuscript
  should keep the current "pending" disclosure.
- Local `git tag --list 'v1.1.2-deposit'` did not show the release tag even
  though `gh release view` can see the GitHub release. This may simply be a
  local tag-fetch issue, but a release checklist should verify the tag object
  and source commit before DOI minting.

### Concrete Fixes To Make Next

1. Regenerate or amend `RELEASE_MANIFEST.json` so its `git_commit` and
   `manifest_scope` accurately describe the source state behind
   `v1.1.2-deposit`.
2. Update `CANONICAL_SUBMISSION.md`: current deposit release =
   `v1.1.2-deposit`; prereg chain includes `PREREG_OFFICE_V3.md` and
   `PREREG_FIR_BREADTH.md`; replace "comparator wins" with
   "per-category point-estimate comparisons".
3. Update `VENUE_PLAN.md`'s DOI paragraph and cover-letter checklist to reflect
   `v1.1.2-deposit` and the existing but still-draft `COVER_LETTER_TORS.md`.
4. Decide whether `PAPER_DRAFT.md` belongs in the DOI bundle. If it stays,
   add a top-level warning that historical status entries are superseded and not
   current claims; if it leaves, rebuild and re-upload a `v1.1.3-deposit`.
5. Test the manuscript with ACM's current Primary Article Template/acmart class,
   then rebuild `PAPER_TORS.pdf` and rerun the hygiene scan.
6. Inspect the SILLM4Rec full text if accessible, or keep the current
   inspection-pending caveat in the freeze checklist.

### Open Questions

- Should the manifest `git_commit` point to the commit whose tree was zipped,
  the parent whose hashes are described, or the current HEAD? The current text
  says the first interpretation, but the current value matches none of the
  visible `v1.1.2` package commits.
- Does the author want the working draft included in the archival DOI package,
  or should the deposit be submission-only?
- Will final TORS submission be built locally with updated `acmart`, or moved to
  Overleaf/TeX Live for ACM-current compatibility?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Confirm branch, HEAD, working-tree status, and intervening commits.
- [x] Inspect README, citation/Zenodo metadata, DOI instructions, cover letter,
      canonical source map, venue plan, release manifest, and deposit builder.
- [x] Inspect local `v1.1.2` zip, sidecar hash, and public GitHub release
      digest.
- [x] Re-run strict artifact graph rebuild.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Check ACM template guidance against the local vendored `acmart.cls`.
- [x] Check SILLM4Rec public evidence against the manuscript caveat.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Fix manifest commit/scope metadata.
- [ ] Refresh `CANONICAL_SUBMISSION.md` and `VENUE_PLAN.md`.
- [ ] Decide whether `PAPER_DRAFT.md` belongs in the deposit.
- [ ] Verify ACM-current template compatibility.
- [ ] Finish maintainer-specific cover-letter fields.

## Audit Run - 2026-07-18 06:13 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` /
  `88fc0c7fd48d01065a628402e6483e8dc2c2c39a`.
- Current run time: `2026-07-18 06:13:21` through `06:13:39 +10:00` for the
  dynamic gates; audit documentation completed immediately afterward.
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  using the `$HOME\.codex` fallback because `CODEX_HOME` is unset in this
  PowerShell session.
- Working tree before this audit edit: tracked modifications in
  `PAPER_REVIEW_AUDIT.md` and `_bestrec_run/hstu_tables.json`; known untracked
  files remain `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Sources/artifacts inspected this run: `README.md`, `CITATION.cff`,
  `.zenodo.json`, `DOI_DEPOSIT_INSTRUCTIONS.md`, `RELEASE_MANIFEST.json`,
  `CANONICAL_SUBMISSION.md`, `PAPER_SUBMISSION.md`, `VENUE_PLAN.md`,
  `paper_tex/main.tex`, `paper_tex/main-acmsmall.tex`,
  `paper_tex/paper-shared.tex`, `paper_tex/acmart.cls`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `paper_tex/sections/01-introduction.tex`,
  `paper_tex/sections/02-related.tex`, and
  `paper_tex/sections/08-availability.tex`.
- No manuscript or code source was edited in this run; only this audit file was
  updated.

### Verdict

**The empirical paper remains green; the submission package remains
rejectable.** The strict artifact graph, Office V3 adjudicator, and FIR-breadth
adjudicator all pass again with the same values as the previous hour. The
current TeX front matter includes CCS concepts and keywords, and the review
target is single-column `manuscript` format, which is directionally consistent
with ACM review-submission guidance.

The new submission-readiness finding is template drift: the paper vendors
`paper_tex/acmart.cls` v2.03 (`2024/02/04`), while ACM's current author page
instructs LaTeX authors to use the latest Primary Article Template and names a
later version on that page. This may be acceptable as a local build workaround
only if the final submission is regenerated with ACM's current template or the
exception is explicitly tested. A strict editorial check could return the
manuscript before review for using obsolete template files.

The second new package finding is that no cover-letter artifact exists. This is
not a scientific defect in the paper, but it is a real TORS submission blocker:
the venue plan correctly lists a cover letter, and TORS author guidance requires
a declaration that the work is original, unpublished, and not currently under
review elsewhere.

The highest scientific/artifact risks are unchanged: the public repository
landing page is still for the wrong LC2C/EASE paper; DOI/citation metadata and
the deposit bundle are still stale; and release instructions still contain the
wrong v1.0 zip reference.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release-manifest hash verification OK for `153` files.
  - PASS: MI V2 gate; legacy Office V1 descriptive/VOID check remains OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-18 06:13:39 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds
    above both references.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - CONFIRMED at `2026-07-18 06:13:39 Australia/Sydney`, block
    `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- Claim/package sweep:
  - `README.md` still describes `BEST-Rec v5: SBERT-Augmented EASE + Novel
    Cold-Item Algorithm (LC2C)` and old LC2C reproduction paths, not the
    current HSTU/FIR/TORS artifact.
  - `CITATION.cff` still reports version `1.0`, date `2026-07-11`, and only
    the Musical_Instruments confirmation boundary.
  - `.zenodo.json` still omits Office V3 and FIR-breadth/four-category
    evidence.
  - `RELEASE_MANIFEST.json` still names `v1.1-deposit`, date `2026-07-12`, and
    parent commit `882b839a`.
  - `DOI_DEPOSIT_INSTRUCTIONS.md` still says Option B should upload
    `bestrec_deposit_v1.0.zip`.
- Venue-format sweep:
  - `paper_tex/main.tex` uses `\documentclass[manuscript,review,anonymous]{acmart}`.
  - `paper_tex/paper-shared.tex` contains `\acmJournal{TORS}`, CCS XML,
    `\ccsdesc[500]{Information systems~Recommender systems}`,
    `\ccsdesc[300]{Information systems~Personalization}`, and a nonempty
    `\keywords{...}` list.
  - `paper_tex/acmart.cls` is vendored as
    `[2024/02/04 v2.03 Typesetting articles for the Association for Computing Machinery]`.
  - `paper_tex/hygiene_scan_output.txt` remains PASS: `PAPER_TORS.pdf`,
    40 pages, `0` placeholder/forbidden failures, informational SOTA/non-claim
    review hits only.
- Cover-letter search:
  - File-name and content searches found `VENUE_PLAN.md`'s freeze-checklist
    item for a cover letter, but no actual cover-letter artifact in the
    workspace.

### External Fact-Check / Venue Notes

- ACM's current author-submission page says journal manuscripts must use ACM's
  authoring template, tells authors to submit review manuscripts in single
  column, instructs LaTeX authors to use the latest Primary Article Template
  with the `manuscript` option, and states that CCS concepts and keywords are
  required for articles over two pages. Source:
  https://www.acm.org/publications/authors/submissions
- The same ACM page says ACM journal/transaction articles are prepared for
  print and digital display through ACM's production workflow, so local PDFs are
  not the final production format; this supports keeping an ACM-current source
  package ready rather than relying on a vendored 2024 class. Source:
  https://www.acm.org/publications/authors/submissions
- The ACM TORS author-guidelines page states that authors must submit a cover
  letter declaring that the work is original, unpublished, and not currently
  under review with another journal. Source:
  https://dl.acm.org/journal/tors/author-guidelines
- ACM TORS describes its scope as high-quality work on recommender-systems
  research, so the manuscript topic is venue-relevant; the blocker is package
  readiness and claim discipline, not gross venue mismatch. Source:
  https://dl.acm.org/journal/tors

### Confirmed Problems

1. **Root `README.md` still presents the wrong paper.** This remains the top
   reviewer-facing contradiction.
2. **DOI/citation/release metadata is still stale.** `CITATION.cff`,
   `.zenodo.json`, `RELEASE_MANIFEST.json`, and
   `DOI_DEPOSIT_INSTRUCTIONS.md` still disagree with the current paper
   boundary.
3. **The local TeX toolchain is not ACM-current.** The review target is the
   right format family, but the vendored `acmart.cls` is v2.03 from 2024, not
   the current ACM template version advertised on ACM's submission page.
4. **No TORS cover letter exists yet.** This is a submission-package blocker,
   especially because the paper's delicate claim boundary must be stated
   consistently in the cover letter.

### Confirmed Non-Problems

- No empirical-cell mismatch, untraceable value, missing claim family, HSTU
  parity failure, Office V3 adjudicator failure, or FIR-breadth adjudicator
  failure was found.
- The compiled TeX front matter now has CCS concepts and keywords.
- The review PDF target is single-column `manuscript` format and the hygiene
  scan remains PASS.
- The availability section is current on the tracked-artifact boundary for
  Office V3 and FIR-breadth; it no longer carries the older "not counted" sidecar
  contradiction.

### Concrete Fixes To Make Next

1. Replace root `README.md` with a current HSTU/FIR/TORS artifact README, and
   archive the old LC2C README if it must be preserved.
2. Refresh `CITATION.cff`, `.zenodo.json`, `RELEASE_MANIFEST.json`, and
   `DOI_DEPOSIT_INSTRUCTIONS.md` before any DOI or release action.
3. Remove or rewrite `PAPER_DRAFT.md` in the deposit builder before rebuilding
   the next deposit archive.
4. Test the manuscript with ACM's current Primary Article Template/acmart class,
   or document a deliberate, editor-approved local-build exception. Rebuild and
   re-run the hygiene scan after any class/toolchain change.
5. Create a TORS cover letter that states: originality, unpublished/not under
   review elsewhere, no broad SOTA claim, MI and Office V3 only as
   per-category point-estimate comparisons, FIR-breadth only as internal
   paired filter evidence, and Office V1 permanently VOID.
6. Cut a clean `v1.1.2-deposit` only after the repository landing page,
   metadata, manifest, DOI instructions, and bundled file inventory are all
   synchronized.

### Open Questions

- Can the current Tectonic-based build compile with ACM's latest `acmart`, or
  does final packaging need TeX Live/Overleaf instead?
- Should the cover letter be maintained as a tracked workspace file
  (`COVER_LETTER_TORS.md`) before ScholarOne submission?
- Should the next deposit omit `PAPER_DRAFT.md` entirely, or keep it only after
  rewriting it to match `PAPER_SUBMISSION.md`?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Confirm branch, HEAD, dirty tracked files, and known untracked files.
- [x] Re-run strict artifact graph rebuild.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Search public package files for stale release/DOI/status wording.
- [x] Check TeX review/prod drivers, shared front matter, CCS concepts, and
      keyword metadata.
- [x] Check vendored `acmart.cls` version against ACM submission guidance.
- [x] Search for a TORS cover-letter artifact.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Replace repository README.
- [ ] Refresh DOI/citation/release metadata.
- [ ] Rebuild a clean deposit archive.
- [ ] Verify ACM-current template compatibility.
- [ ] Draft and check TORS cover letter.

## Audit Run - 2026-07-18 05:10 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` /
  `88fc0c7fd48d01065a628402e6483e8dc2c2c39a`.
- Current run time: `2026-07-18 05:10:51` through `05:16:39 +10:00`;
  adjudicators printed `2026-07-18 05:12:03` and `05:12:11`.
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  using the `$HOME\.codex` fallback because `CODEX_HOME` is unset in this
  PowerShell session.
- Working tree before this audit edit: tracked modifications in
  `PAPER_REVIEW_AUDIT.md` and `_bestrec_run/hstu_tables.json`; known untracked
  files remain `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Sources/artifacts inspected this run: `README.md`, `CITATION.cff`,
  `.zenodo.json`, `CANONICAL_SUBMISSION.md`, `PAPER_DRAFT.md`,
  `PAPER_SUBMISSION.md`, live `paper_tex/sections/*.tex`,
  `paper_tex/tables/table0_novelty.tex`, `paper_tex/references.bib`,
  `paper_tex/PAPER_TORS.pdf`, `DOI_DEPOSIT_INSTRUCTIONS.md`,
  `RELEASE_MANIFEST.json`, `_bestrec_run/build_deposit_bundle.py`,
  `_release/bestrec_deposit_v1.1.1.zip`, the public GitHub release
  `v1.1.1-deposit`, and fresh PDF renders under
  `tmp/pdfs/hourly_audit_20260718_0510/`.

### Verdict

**The math is still green; the public artifact story is not.** The strict build,
Office V3 adjudicator, and FIR-breadth adjudicator all pass again. The compiled
TORS PDF sample pages render without obvious layout defects.

The new top rejection risk is the repository landing page: `README.md` is still
for the older LC2C/EASE cold-item paper, with old datasets, old reproduction
commands, old SOTA language, and old LC2C claims. A reviewer following the
paper's artifact link would land on a repository that appears to support a
different manuscript. This is more serious than an archived stale draft because
it is the default public face of the code release.

The prior packaging blockers also remain confirmed: the uploaded `v1.1.1`
archive still contains the stale `PAPER_DRAFT.md`, stale manifest metadata, and
stale DOI manual-upload instruction. `CITATION.cff` and `.zenodo.json` add a
new DOI-metadata problem: they are bundled, but still describe the earlier
v1.0/Musical_Instruments-only evidence boundary.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release-manifest hash verification OK for `153` files.
  - PASS: MI V2 gate; legacy Office V1 descriptive/VOID check remains OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-18 05:12:03 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds
    above both references.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - CONFIRMED at `2026-07-18 05:12:11 Australia/Sydney`, block
    `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- Public GitHub release check:
  - `gh release view v1.1.1-deposit --repo Ray0419/bestrec-sota-results` reports
    uploaded `bestrec_deposit_v1.1.1.zip` digest
    `sha256:70b2612b19e430b8a1a0ace3576c82805dc95fd40f3e08e6982f041273a4ac6d`,
    size `1,793,791`, published `2026-07-17T15:34:05Z`.
  - Local zip hash and sidecar match that digest, so the stale archive content
    is already public, not local-only drift.
- Archive inspection:
  - `_release/bestrec_deposit_v1.1.1.zip` has `65` entries and includes
    `.zenodo.json`, `CITATION.cff`, `PAPER_DRAFT.md`,
    `DOI_DEPOSIT_INSTRUCTIONS.md`, `RELEASE_MANIFEST.json`,
    `PAPER_SUBMISSION.md`, and `paper_tex/PAPER_TORS.pdf`.
  - Bundled `PAPER_DRAFT.md` contains `Office stays VOID` and
    `outcome is pending`.
  - Bundled `RELEASE_MANIFEST.json` reports release
    `v0.9-audit-evidence (immutable data assets) + v1.1-deposit (document bundle)`,
    date `2026-07-12`, and commit
    `882b839abc12a871a874f2538afacef1088caa6d`, not current HEAD `88fc0c7f`.
  - Bundled `DOI_DEPOSIT_INSTRUCTIONS.md` still contains
    `upload bestrec_deposit_v1.0.zip` in Option B.
- Repository/metadata inspection:
  - `README.md` opens with `BEST-Rec v5: SBERT-Augmented EASE + Novel Cold-Item
    Algorithm (LC2C)` and reports old Beauty/Fashion/Instruments/Books warm and
    cold-item LC2C results, not the HSTU/FIR/TORS manuscript.
  - `CITATION.cff` says `version: "1.0"` and
    `date-released: "2026-07-11"` and mentions the
    Musical_Instruments confirmation, but not Office V3 or FIR-breadth.
  - `.zenodo.json` similarly describes the pre-registered
    Musical_Instruments point-estimate confirmation and omits Office V3 and the
    FIR-breadth/four-category claim boundary.
  - `CANONICAL_SUBMISSION.md` itself is mostly current: it names the HSTU/FIR
    manuscript, Office V3 pass, four-category FIR evidence, and no-SOTA
    boundary. The stale files are therefore inconsistent with the canonical
    source-of-truth file.
- PDF visual check:
  - Rendered representative pages `1, 8, 9, 15, 18, 19, 20, 27, 28, 35, 36`
    of `paper_tex/PAPER_TORS.pdf` with PyMuPDF to
    `tmp/pdfs/hourly_audit_20260718_0510/`.
  - Inspected the contact sheet plus dense pages 9 and 28. No clipping,
    overlapping text, missing glyphs, broken tables, or black-box rendering was
    observed. Tables are dense but readable at full page scale.

### External Fact-Check / Novelty Notes

- FEARec is a SIGIR 2023 frequency-domain sequential recommendation model that
  explicitly starts from the claim that self-attention models behave as
  low-pass filters and designs frequency-domain attention/regularization. This
  supports the paper's narrow FIR novelty boundary, not a broad frequency
  novelty claim. Source: https://arxiv.org/abs/2304.09184
- WPGRec is listed on arXiv as submitted `2026-04-23`, accepted to SIGIR 2026,
  and uses wavelet-packet/time-frequency modeling plus graph propagation for
  sequential recommendation. This further broadens the time-frequency prior-art
  neighborhood. Source: https://arxiv.org/abs/2604.21305
- Caser already framed sequential recommendation around convolutional sequence
  embedding in time/latent spaces and local convolutional filters. Source:
  https://arxiv.org/abs/1809.07426
- NextItNet already used stacked holed/dilated convolutional layers for next
  item recommendation, supporting the manuscript's statement that causal
  convolutional sequence encoders are prior art. Source:
  https://arxiv.org/abs/1808.05163
- Amazon Reviews 2023 official materials support the dataset framing as a 2023
  McAuley Lab release with user reviews, item metadata, links, and standard
  splitting materials. Source: https://amazon-reviews-2023.github.io/
- BLaIR public materials support the paper's use of BLaIR as an Amazon Reviews
  2023 language-item representation family, but do not rescue any stale
  repository metadata. Sources: https://arxiv.org/html/2403.03952v1 and
  https://github.com/hyp1231/AmazonReviews2023/blob/main/blair/README.md

### Confirmed Problems

1. **Root `README.md` is for the wrong paper.** This is public-facing and
   directly conflicts with the current paper title, methods, results, datasets,
   and reproduction path.
2. **DOI/citation metadata is stale and bundled.** `CITATION.cff` and
   `.zenodo.json` will under-describe or misdate the artifact if a DOI is minted
   from the current release.
3. **The uploaded `v1.1.1` deposit zip still contains stale `PAPER_DRAFT.md`.**
   This repeats the Office V3 pending/VOID contradiction inside the public,
   hashed archive.
4. **The uploaded and bundled manifest metadata is stale.** It still identifies
   `v1.1-deposit`, date `2026-07-12`, and commit `882b839a`.
5. **The DOI manual-upload instruction still names the obsolete v1.0 zip.**
   This is inside both the workspace file and the current deposit bundle.
6. **`_bestrec_run/build_deposit_bundle.py` still carries `PAPER_DRAFT.md`
   forward from the v1.0 inventory.** Unless this is changed, any rebuild will
   keep reintroducing the stale draft unless the draft itself is updated.

### Confirmed Non-Problems

- No empirical-cell mismatch, untraceable value, or missing claim family was
  found in the fresh strict rebuild.
- Office V3 and FIR-breadth adjudicators remain green under their frozen
  wording.
- Canonical manuscript/TeX sources continue to keep broad SOTA and paired
  superiority boundaries narrow.
- The current TORS PDF sample renders cleanly on inspected pages.
- The new FEARec/WPGRec/Caser/NextItNet related-work additions move the novelty
  boundary in the right direction: narrower and more defensible, not broader.

### Concrete Fixes To Make Next

1. Replace root `README.md` with a current HSTU/FIR/TORS artifact README:
   title, canonical paper files, one-command strict verification, current
   claim boundaries, release assets, DOI status, and explicit non-SOTA wording.
   Move the LC2C README to `archive_noncanonical/` if it must be preserved.
2. Update `CITATION.cff` and `.zenodo.json` before DOI minting: version/date,
   title if needed, Office V3, FIR-breadth/four-category boundary, no broad
   SOTA, no paired superiority, and current release URL.
3. Decide whether `PAPER_DRAFT.md` belongs in the deposit at all. Best fix:
   remove it from `V10_FILES` in `_bestrec_run/build_deposit_bundle.py`, or
   rewrite the status header so it cannot contradict `PAPER_SUBMISSION.md`.
4. Regenerate `RELEASE_MANIFEST.json` so release/date/commit metadata reflect
   the actual intended deposit boundary.
5. Fix `DOI_DEPOSIT_INSTRUCTIONS.md` Option B to name
   `bestrec_deposit_v1.1.1.zip` or the next rebuilt version, not v1.0.
6. Rebuild and re-upload as a fresh `v1.1.2-deposit` rather than silently
   replacing `v1.1.1`, so the DOI/reviewer trail is unambiguous.
7. After rebuilding, verify: local zip hash, sidecar hash, GitHub asset digest,
   bundled manifest metadata, absence/fixed state of `PAPER_DRAFT.md`, and
   bundled DOI/Citation/Zenodo metadata.

### Open Questions

- Should the next public artifact be a corrected `v1.1.1` asset replacement or
  a new `v1.1.2-deposit` release? Reviewer clarity favors `v1.1.2-deposit`.
- Should `PAPER_DRAFT.md` remain in any archival bundle once
  `PAPER_SUBMISSION.md` and `paper_tex/PAPER_TORS.pdf` are the canonical
  manuscript artifacts?
- Should `README.md` be manuscript-specific, or should it become a short
  repository index with separate links to the old LC2C and current HSTU/FIR
  tracks? For top-journal review, manuscript-specific is safer.
- Does the artifact release need a separate `ARTIFACTS.md` to keep root README
  concise while still giving reviewers exact commands and claim boundaries?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, release, DOI, citation, README, and
      audit artifacts.
- [x] Re-run strict manuscript/artifact gate.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Inspect public GitHub `v1.1.1-deposit` asset metadata.
- [x] Inspect local/public zip hash and bundled stale files.
- [x] Inspect root README, `CITATION.cff`, `.zenodo.json`, and canonical source
      boundary file.
- [x] Render and visually inspect representative TORS PDF pages.
- [x] Fact-check the expanded frequency/convolution prior-art boundary against
      FEARec, WPGRec, Caser, NextItNet, AR2023, and BLaIR sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Replace or archive stale root README.
- [ ] Refresh DOI/citation/Zenodo metadata.
- [ ] Repair or exclude `PAPER_DRAFT.md` from the deposit bundle.
- [ ] Regenerate manifest release/date/commit metadata.
- [ ] Fix DOI manual-upload instructions.
- [ ] Rebuild/re-upload a corrected deposit archive before DOI minting.

## Audit Run - 2026-07-18 04:10 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` /
  `88fc0c7fd48d01065a628402e6483e8dc2c2c39a`.
- Current run time: `2026-07-18 04:10:44 +10:00`; adjudicators printed
  `2026-07-18 04:11:07`.
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  using the `$HOME\.codex` fallback because `CODEX_HOME` is unset in this
  PowerShell session.
- Working tree before this audit edit: tracked modifications in
  `PAPER_REVIEW_AUDIT.md` and `_bestrec_run/hstu_tables.json`; the latter is
  the known strict-gate generated-state change from `"mode": "default"` /
  `"enforced": false` to `"mode": "submission"` / `"enforced": true`. Known
  untracked files remain `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Sources/artifacts inspected this run: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `paper_tex/sections/*.tex`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `paper_tex/tables/TABLES_PROVENANCE.json`, `DOI_DEPOSIT_INSTRUCTIONS.md`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, `RELEASE_MANIFEST.json`,
  `_bestrec_run/build_deposit_bundle.py`,
  `_release/bestrec_deposit_v1.1.1.zip`, and
  `_release/bestrec_deposit_v1.1.1.zip.sha256`.

### Verdict

**Numerically green, but archive not submission-clean.** The strict rebuild,
Office V3 adjudicator, and FIR-breadth adjudicator all pass again. The major
new finding is packaging, not math: the current `v1.1.1` deposit archive ships
`PAPER_DRAFT.md`, and that draft still says Office stays VOID while V3 is only
pending. That directly conflicts with the canonical paper's Office V3 pass.

The previous manifest problem is also confirmed inside the archive: bundled
`RELEASE_MANIFEST.json` still says `v1.1-deposit`, date `2026-07-12`, and
`git_commit` `882b839abc12a871a874f2538afacef1088caa6d`. A DOI/package reviewer
can fairly conclude that the artifact bundle is not provenance-clean even
though the empirical tables are recomputable.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release-manifest hash verification OK for `153` files.
  - PASS: MI V2 gate; legacy Office V1 descriptive/VOID check remains OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-18 04:11:07 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds
    above both references.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - CONFIRMED at `2026-07-18 04:11:07 Australia/Sydney`, block
    `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- Manifest/release-metadata search:
  - `RELEASE_MANIFEST.json` still begins with
    `v0.9-audit-evidence (immutable data assets) + v1.1-deposit (document bundle)`.
  - It still records date `2026-07-12` and `git_commit`
    `882b839abc12a871a874f2538afacef1088caa6d`, while current HEAD is
    `88fc0c7fd48d01065a628402e6483e8dc2c2c39a`.
  - The embedded archive copy has the same stale values.
- Deposit archive inspection:
  - `_bestrec_run/build_deposit_bundle.py` includes `PAPER_DRAFT.md`,
    `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`, `RELEASE_MANIFEST.json`,
    `DOI_DEPOSIT_INSTRUCTIONS.md`, and `paper_tex/PAPER_TORS.pdf` in the
    v1.1.1 inventory.
  - `_release/bestrec_deposit_v1.1.1.zip` contains
    `bestrec_deposit_v1.1.1/PAPER_DRAFT.md`.
  - The archive copy of `PAPER_DRAFT.md` contains:
    `Office stays VOID (the V3 prereg is cited only as a committed
    pre-registration whose outcome is pending, PREREG_OFFICE_V3.md)`.
  - Local zip SHA256 remains
    `70b2612b19e430b8a1a0ace3576c82805dc95fd40f3e08e6982f041273a4ac6d`,
    matching `_release/bestrec_deposit_v1.1.1.zip.sha256`. This confirms the
    contradictory draft is in the currently hashed archive, not a post-hash
    local drift.
- Source consistency scans:
  - `PAPER_SUBMISSION.md` and live `paper_tex/sections/*.tex` keep the narrow
    Office V3 wording and explicit non-SOTA / no-paired-superiority boundaries.
  - `rg` finds the stale Office-pending wording in `PAPER_DRAFT.md` only among
    manuscript-like sources, plus `paper_tex/BUILD_NOTES.md` entries that say
    the stale TeX phrase was replaced.
  - `paper_tex/hygiene_scan_output.txt` remains PASS: 40 pages, 0
    placeholder/forbidden failures, 20 informational SOTA/nonclaim hits.
- DOI instructions check:
  - Artifact table says the current bundle is GitHub release
    `v1.1.1-deposit` asset `bestrec_deposit_v1.1.1.zip`.
  - Option B still instructs manual Zenodo upload of `bestrec_deposit_v1.0.zip`
    "from the `v1.1.1-deposit` release assets, or `_release/` locally", which
    is internally contradictory and operationally dangerous.

### External Fact-Check / Novelty Notes

- FMLP-Rec already proposes learnable filters for sequential recommendation and
  motivates them as frequency-domain noise attenuation. Source:
  https://arxiv.org/abs/2202.13556
- BSARec frames Transformer self-attention in sequential recommendation as
  low-pass / oversmoothing and uses Fourier-based mitigation. Source:
  https://arxiv.org/abs/2312.10325
- TIGER uses RQ-VAE semantic IDs and autoregressive generative retrieval for
  recommendation; this supports the paper's claim that TAPE is adjacent to
  semantic-ID work, not wholly new. Sources:
  https://arxiv.org/abs/2305.05065 and
  https://papers.neurips.cc/paper_files/paper/2023/file/20dcab0f14046a5c6b02b61da9f13229-Paper-Conference.pdf
- VQ-Rec maps item text into discrete item codes for transferable sequential
  recommendation; this narrows any TAPE novelty claim to its continuous soft
  text-prototype realization. Source: https://arxiv.org/abs/2210.12316
- ProtoMF is prototype-based matrix factorization for effective and explainable
  recommendations; it supports treating prototype use as prior art. Source:
  https://dl.acm.org/doi/10.1145/3523227.3546756
- Amazon Reviews 2023 official materials confirm the dataset is a McAuley Lab
  2023 release with reviews, item metadata, links, and 5-core processing docs.
  Sources: https://amazon-reviews-2023.github.io/ and
  https://amazon-reviews-2023.github.io/data_processing/5core.html
- SILLM4Rec remains a comparison-scope caveat: ACM metadata and accessible
  pages support its existence and high-level recommender framing, but I did not
  establish direct full-catalog LLOO comparability from the available public
  text in this run. Source: https://dl.acm.org/doi/10.1145/3743093.3771011

### Confirmed Problems

1. **The current deposit zip contains a stale, manuscript-like draft that
   contradicts the canonical Office V3 claim.** This is now the top rejection
   risk because it is already in the hashed archive.
2. **The bundled release manifest is metadata-stale.** It verifies local file
   hashes, but its release/date/commit fields describe neither the current
   `v1.1.1` archive nor current HEAD.
3. **The manual DOI upload instructions name the obsolete v1.0 zip.** This can
   cause the wrong archive to be uploaded even if the v1.1.1 artifact exists.
4. **`RESPONSE_TO_PAPER_REVIEW_AUDIT.md` still overclaims the manifest fix.**
   It says the release label now names both releases, but both local and
   bundled manifests still say only `v1.1-deposit` for the document bundle.

### Confirmed Non-Problems

- The current strict rebuild has no empirical-cell mismatch or untraceable
  table value.
- Office V3 remains a narrow pass under its frozen wording; FIR-breadth remains
  confirmed on the two extra categories.
- Canonical manuscript sources and TeX sections no longer carry the stale broad
  Office non-counting phrase.
- The current TORS hygiene scan passes with no forbidden-claim failures.

### Concrete Fixes To Make Next

1. Decide the status of `PAPER_DRAFT.md`: either update its status header to
   match the canonical Office V3/V1 two-track statement, or remove it from
   `_bestrec_run/build_deposit_bundle.py` and state that only
   `PAPER_SUBMISSION.md` / `paper_tex/PAPER_TORS.pdf` are manuscript sources.
2. Regenerate `RELEASE_MANIFEST.json` so `release`, `date`, and `git_commit`
   reflect the actual intended deposit boundary, not the stale `v1.1` /
   `882b839a` boundary.
3. Fix `DOI_DEPOSIT_INSTRUCTIONS.md` Option B to name
   `bestrec_deposit_v1.1.1.zip` or the next rebuilt version, not
   `bestrec_deposit_v1.0.zip`.
4. Rebuild `_release/bestrec_deposit_v1.1.1.zip` or cut a fresh
   `v1.1.2-deposit`, update the sidecar SHA256, and re-upload the release
   assets. Do not mint a DOI from the current zip.
5. Keep FIR/TAPE novelty language narrow; do not let DOI metadata, cover
   letters, README text, or response files call the method broadly novel or
   SOTA.

### Open Questions

- Should `PAPER_DRAFT.md` remain in any archival bundle at all, given that it is
  explicitly noncanonical and can carry stale status metadata?
- What exact commit should `RELEASE_MANIFEST.json` name after the packaging
  repair: the source state before the regenerated manifest, or the commit that
  includes the regenerated manifest and rebuilt bundle instructions?
- Should the next archive be a corrected `v1.1.1` asset replacement or a new
  `v1.1.2-deposit` release for DOI clarity?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, release, and audit artifacts.
- [x] Re-run strict manuscript/artifact gate.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Search source files for stale Office V3 pending/no-claim wording.
- [x] Inspect deposit builder inventory.
- [x] Inspect current v1.1.1 zip contents and embedded stale text.
- [x] Check local zip SHA256 against the sidecar.
- [x] Fact-check novelty boundaries against FMLP-Rec, BSARec, TIGER, VQ-Rec,
      ProtoMF, AR2023, and SILLM4Rec public sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair or exclude `PAPER_DRAFT.md` from the deposit bundle.
- [ ] Regenerate manifest release/date/commit metadata.
- [ ] Fix DOI manual-upload instructions.
- [ ] Rebuild/re-upload a corrected deposit archive before DOI minting.

## Audit Run - 2026-07-18 03:10 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `88fc0c7f`.
- Current run time: `2026-07-18 03:10:16 +10:00`; adjudicators printed
  `2026-07-18 03:11:37`.
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`;
  `CODEX_HOME` remains unset in this PowerShell session.
- Working tree before this audit edit: tracked modification in
  `_bestrec_run/hstu_tables.json` only, changing generated metadata from
  `"mode": "default"` / `"enforced": false` to `"mode": "submission"` /
  `"enforced": true`; known untracked files remain
  `_bestrec_run/impact_program.DONE`, `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Canonical sources/artifacts inspected this run:
  `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`, `PAPER_DRAFT.md`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/sections/*.tex`,
  `paper_tex/tables/office_confirmation.tex`, `paper_tex/references.bib`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `DOI_DEPOSIT_INSTRUCTIONS.md`, `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`,
  `RELEASE_MANIFEST.json`, `_release/bestrec_deposit_v1.1.1.zip`, and GitHub
  release `v1.1.1-deposit`.

### Verdict

**Numerically green, packaging improved, but still not provenance-clean.** The
last audit's hard public-release blocker is fixed in the narrow byte sense:
`v1.1.1-deposit` exists, and GitHub asset digests match local files. The strict
build, Office V3 adjudicator, and FIR-breadth adjudicator are all green.

The new top rejection risk is subtler but still serious: the manifest shipped
with those current artifacts still says `v1.1-deposit` and `git_commit`
`882b839a`, while the repository and DOI instructions now direct reviewers to
`v1.1.1-deposit` from HEAD `88fc0c7f`. A skeptical reviewer will treat that as
weak release discipline unless it is corrected before DOI/submission.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release-manifest verification OK for `153` files.
  - PASS: MI V2 gate; legacy Office V1 descriptive/VOID check remains OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-18 03:11:37 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds
    above both references.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - CONFIRMED at `2026-07-18 03:11:37 Australia/Sydney`, block `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- GitHub/local release hash check
  - `gh release view v1.1.1-deposit` reports uploaded bundle digest
    `sha256:70b2612b19e430b8a1a0ace3576c82805dc95fd40f3e08e6982f041273a4ac6d`.
  - Local `_release/bestrec_deposit_v1.1.1.zip` has the same SHA256 and size
    `1,793,791` bytes; the `.sha256`, `PAPER_SUBMISSION.pdf`,
    `paper_tex/PAPER_TORS.pdf`, and `RELEASE_MANIFEST.json` also match the
    GitHub asset digests.
  - Release URL checked:
    https://github.com/Ray0419/bestrec-sota-results/releases/tag/v1.1.1-deposit
- Manifest metadata check
  - `RELEASE_MANIFEST.json` line 2 still says
    `v0.9-audit-evidence (immutable data assets) + v1.1-deposit (document bundle)`.
  - It records `git_commit` `882b839abc12a871a874f2538afacef1088caa6d`, while
    current HEAD is `88fc0c7fd48d01065a628402e6483e8dc2c2c39a`.
  - `DOI_DEPOSIT_INSTRUCTIONS.md` now correctly points to `v1.1.1-deposit`;
    `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` claims the manifest release label was
    refreshed, but the checked manifest contradicts that claim.
- PDF/source extraction with `pypdf` and `rg`
  - `PAPER_SUBMISSION.pdf`: 46 pages; `Office_Products V3` on page 22;
    `SILLM4Rec` on page 19; no `Office is not counted`, `NOT counted`, or
    `Musical_Instruments only` hits.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; `Office_Products V3` on page 20;
    `SILLM4Rec` on pages 18 and 36; no old broad Office hits.
  - `paper_tex/hygiene_scan_output.txt`: PASS, 40 pages, `0`
    placeholder/forbidden failures, `20` informational review hits.
- Visual PDF sample
  - Rendered and inspected TORS pages 1, 18, 20, and 36 via PyMuPDF.
  - Text and tables are readable; no clipped text or broken glyphs in sampled
    pages.
  - Minor risk: page 1 has visible line numbers and a duplicated
    "Manuscript submitted to ACM" footer; page 20 has a cramped split table
    header. Confirm these are acceptable under the target ACM review format.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR arXiv v3 confirms AR2023 5-core Video Games, Office Products, and
  Musical Instruments, plus the comparator NDCG@10 values used here: Video Games
  `0.0760`, Office Products `0.0271`, Musical Instruments `0.0406`.
  Source: https://arxiv.org/html/2504.10545v3
- Amazon Reviews 2023 official site confirms the dataset framing: collected by
  McAuley Lab, 571.54M reviews, 48.19M items, 33 domains, interactions through
  September 2023, plus 5-core processing documentation. Sources:
  https://amazon-reviews-2023.github.io/ and
  https://amazon-reviews-2023.github.io/data_processing/5core.html
- SILLM4Rec citation metadata is confirmed via Crossref/DOI: Yuhao Wu, Fang
  Quan, Maoqi Liu, Xiaowen Huang, Jitao Sang, MMAsia 2025, pages 1-8, DOI
  `10.1145/3743093.3771011`. The public repository describes candidate-product
  ranking tasks and SFT/DPO training data, supporting non-interchangeability
  with full-catalog LLOO. Sources:
  https://doi.org/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec
- FIR novelty boundary remains narrow: FMLP-Rec already uses learnable filters
  for sequential recommendation, and BSARec already frames self-attention as
  low-pass/oversmoothing with Fourier-based mitigation. Sources:
  https://arxiv.org/abs/2202.13556 and https://arxiv.org/abs/2312.10325

### Confirmed Problems

1. **`RELEASE_MANIFEST.json` metadata is stale relative to the current release.**
   It verifies file hashes but still names `v1.1-deposit` and parent commit
   `882b839a`, not the current `v1.1.1-deposit` / `88fc0c7f` state.
2. **`RESPONSE_TO_PAPER_REVIEW_AUDIT.md` overclaims the manifest fix.** It says
   "the `release` label now names both releases"; the checked manifest does not.
3. **`PAPER_DRAFT.md` remains unsafe as a manuscript-like artifact.** Its status
   line still says Office V3 was pending and Office stays VOID. This is
   noncanonical, but a workspace or bundle sweep could confuse it with a live
   source.
4. **PDF review-mode polish needs one final human choice.** The sampled TORS PDF
   is readable, but the page-1 duplicate footer/line-number presentation should
   be confirmed against the actual target submission settings.

### Confirmed Non-Problems

- The old broad Office contradiction is gone from canonical Markdown, TeX, and
  both checked PDFs.
- The `v1.1.1-deposit` GitHub upload matches local files by SHA256; the previous
  stale-upload problem is superseded if and only if reviewers are pointed to
  `v1.1.1-deposit`.
- Local strict numerical/provenance checks, Office V3 adjudication, and
  FIR-breadth adjudication are green.
- SILLM4Rec citation metadata in `paper_tex/references.bib` matches Crossref.

### Concrete Fixes To Make Next

1. Regenerate or patch `RELEASE_MANIFEST.json` so its `release`, `date`, and
   `git_commit` fields describe the intended `v1.1.1-deposit` source state.
   Then rebuild `_release/bestrec_deposit_v1.1.1.zip` and re-upload if the
   manifest is bundled.
2. Update `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` to say the prior manifest-label
   fix was incomplete, or amend it after the manifest is actually fixed.
3. Either archive/rename `PAPER_DRAFT.md` as historical or update its first
   status line so it cannot contradict the canonical submission.
4. Confirm the ACM target mode: if line numbers and duplicate footer are not
   required, render a clean final view; if they are required for review, record
   that explicitly in `BUILD_NOTES.md`.
5. Keep the SILLM4Rec caveat unless the ACM full text is directly archived and
   its evaluation protocol is summarized.

### Open Questions

- Should the manifest's `git_commit` describe the exact commit used to build the
  release bundle (`88fc0c7f`) or the parent state whose hashes it records? The
  current text says it should be the source state it describes, but the
  v1.1.1 release workflow now makes that ambiguous.
- Is `PAPER_DRAFT.md` supposed to remain a live manuscript source, or should it
  be clearly marked/excluded from all submission/deposit bundles?
- Is the visible review-line-number layout in `PAPER_TORS.pdf` the intended ACM
  review artifact?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate current canonical manuscript, TeX, PDF, release, and result
      artifacts.
- [x] Re-run strict manuscript/artifact gate.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Verify `v1.1.1-deposit` GitHub asset digests against local files.
- [x] Check `RELEASE_MANIFEST.json` release metadata and commit pointer.
- [x] Search canonical sources and PDFs for stale Office contradiction phrases.
- [x] Render and inspect representative TORS PDF pages.
- [x] Fact-check key external claims against HSTU-BLaIR, Amazon Reviews 2023,
      SILLM4Rec/Crossref, FMLP-Rec, and BSARec sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Fix manifest release/commit metadata and rebuild/re-upload if bundled.
- [ ] Decide whether `PAPER_DRAFT.md` is historical or live, then align it.
- [ ] Confirm final ACM PDF review-vs-clean rendering settings.
- [ ] Inspect SILLM4Rec full paper directly or keep exclusion explicitly pending.

## Audit Run - 2026-07-18 01:10 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `882b839a`.
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`;
  `CODEX_HOME` is still unset in this PowerShell session.
- Current run time: `2026-07-18 01:10:37 +10:00`; adjudicators printed
  `2026-07-18 01:09:38`.
- Working tree before this audit edit: no tracked modifications; untracked
  `_bestrec_run/impact_program.DONE`, `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Canonical sources/artifacts inspected this run:
  `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/PAPER_TORS_acmsmall.pdf`,
  `paper_tex/sections/01-introduction.tex`,
  `paper_tex/sections/02-related.tex`,
  `paper_tex/sections/05-results.tex`,
  `paper_tex/sections/06-discussion.tex`,
  `paper_tex/sections/07-conclusion.tex`,
  `paper_tex/sections/08-availability.tex`,
  `paper_tex/sections/appendix-a0.tex`,
  `paper_tex/tables/office_confirmation.tex`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `paper_tex/references.bib`, `RELEASE_MANIFEST.json`,
  `DOI_DEPOSIT_INSTRUCTIONS.md`, `_bestrec_run/build_hstu_tables.py`,
  `_bestrec_run/hstu_tables.json`, `_release/bestrec_deposit_v1.1.zip`, and the
  GitHub release `v1.1-deposit` via `gh`.

### Verdict

**The local paper/artifact graph is green, but the public release state is not
submission-ready.** The previous hard blockers are mostly fixed locally:
Appendix A.0 and the generated Office table now scope the non-counted language
to the old V1 Office campaign, SILLM4Rec/UniSGR/DIGER/ACERec are cited or
scoped, `RELEASE_MANIFEST.json` covers Office V3 and FIR-breadth, and the local
`v1.1` deposit bundle contains the expected 65 entries.

The new hard blocker is external packaging: the already-uploaded GitHub
`v1.1-deposit` assets do not match the committed local artifacts. That is a
top-journal rejection risk because a reviewer or DOI archive could download a
bundle/PDF/manifest that is not the same as the local, strict-gate-verified
state. Numerically, I found no new failure.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release-manifest verification OK for `153` files.
  - PASS: MI V2 gate; legacy Office V1 descriptive/VOID check remains OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-18 01:09:38 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds
    above both references.
  - Dataset identity, reference artifacts, treestate sidecars, code hashes,
    and data SHA256s verified.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - CONFIRMED at `2026-07-18 01:09:38 Australia/Sydney`, block `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- PDF/source extraction with `pypdf` and `rg`
  - `PAPER_SUBMISSION.pdf`: 46 pages; `SILLM4Rec` on page 19;
    `Office_Products V3` on page 22; no broad "Office is not counted"; V1-scoped
    `Musical_Instruments only` on page 41.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; `SILLM4Rec` on pages 18 and 36;
    `Office_Products V3` on page 20; V1-scoped `Musical_Instruments only` and
    `NOT counted as a second-category pass` on page 37.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 42 pages; no `Musical_Instruments only`
    or `NOT counted as a second-category pass` hits.
  - Current sources confirm the V1 scoping:
    `paper_tex/sections/appendix-a0.tex` says "From this (V1) campaign";
    `paper_tex/tables/office_confirmation.tex` says "this V1 campaign is NOT
    counted" and immediately points to passed Office V3.
- Local deposit inspection
  - `_release/bestrec_deposit_v1.1.zip`: 1,793,411 bytes, SHA256
    `71a2f120716b032fc7bdadfb3f8a11741cc959fa996d83cf258c210250ed96e7`,
    65 entries.
  - Contains `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
    `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`,
    `paper_tex/PAPER_TORS.pdf`, `RELEASE_MANIFEST.json`,
    `DOI_DEPOSIT_INSTRUCTIONS.md`, `_bestrec_run/adjudicate_office_v3.py`, and
    `_bestrec_run/adjudicate_fir_breadth.py`.
- GitHub release inspection
  - `gh release view v1.1-deposit` reports uploaded `bestrec_deposit_v1.1.zip`
    as 1,793,364 bytes, SHA256
    `58f7dfc42df03f89e3df884614c59e992dc2034ed8af3ab6cfedbc0ea9a251b4`.
  - Downloaded release zip also has 65 entries and all required file names, but
    content differs from local for four files:
    `RELEASE_MANIFEST.json`, `SHA256SUMS.txt`, `_bestrec_run/hstu_tables.json`,
    and `paper_tex/PAPER_TORS.pdf`.
  - GitHub standalone release assets are likewise stale relative to local:
    release `PAPER_TORS.pdf` digest
    `8b6023480fae05c36ea9f3e1c000445bacb757243232e5ded5b71004711d7372` vs
    local `71b7b8b56a0f7f1becb3198e44d720969415e80e1df929717ce5df20372a7403`;
    release `RELEASE_MANIFEST.json` digest
    `b8244e68b954e628909997c67f93f221081ff85c0a920edd5ee37f205cb6d45c` vs
    local `ac7f57d3603831381e2cf6b4e70a7159b6829e3c98fb67037a040b7ca08f6f86`.

### External Fact-Check / Novelty Notes

- Amazon Reviews 2023 official documentation supports the dataset framing:
  McAuley Lab release, 571.54M reviews, interactions through September 2023,
  rich metadata, links, and standard splitting. Source:
  https://amazon-reviews-2023.github.io/
- HSTU-BLaIR remains a relevant AR2023 5-core reference named by the paper; the
  arXiv page records v3 as the current version and KDD 2025 workshop acceptance.
  Source: https://arxiv.org/abs/2504.10545
- SILLM4Rec is now formally cited. The ACM DOI exists, and the public repository
  documents 5-core AR2023 data preparation plus image descriptions, user
  preference summaries, candidate ranking tasks, and SFT/DPO training data,
  supporting the current "non-interchangeable pending full-text inspection"
  framing. Sources: https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec
- UniSGR is correctly scoped out based on checked evidence: it evaluates on
  private Lazada "Guess You Like" logs, omits production statistics for
  confidentiality, and is not a public AR2023 LLOO comparator. Source:
  https://arxiv.org/html/2607.04068v1
- DIGER and ACERec are related semantic-ID/generative-recommendation work, not
  direct AR2023 full-catalog LLOO comparators based on the checked abstracts.
  DIGER studies differentiable semantic IDs; ACERec targets long semantic IDs
  and reports average NDCG@10 gains across six benchmarks. Sources:
  https://arxiv.org/abs/2601.19711 and https://arxiv.org/abs/2602.13573

### Confirmed Problems

1. **Uploaded release assets are stale relative to the current local bundle and
   committed manifest.** This is now the top submission-readiness blocker.
2. **The release tag is internally self-consistent but externally inconsistent
   with HEAD.** The downloaded release zip's `.sha256` sidecar matches the
   downloaded zip, not the local one; so this is not a corrupt upload, it is a
   stale upload.
3. **Appendix A.0 still carries reviewer-triggering phrases even though they are
   now scoped correctly.** This is not a contradiction, but the phrases
   "Musical_Instruments only" and "NOT counted as a second-category pass" remain
   findable in the review PDF.
4. **`BUILD_NOTES.md` still embeds obsolete historical output blocks.** They are
   labeled historical, but the file remains noisy and easy to misread.

### Confirmed Non-Problems

- No hard numerical, table, or provenance failure reproduced in the local strict
  gate.
- Office V3 and FIR-breadth adjudications remain green.
- The prior broad Appendix A.0 contradiction ("Office is not counted") is gone
  from the checked PDFs/sources.
- SILLM4Rec and the main 2026 semantic-ID related-work gaps have citations or
  explicit scope-out language.
- The local `v1.1` deposit bundle contains the expected Office V3 and
  FIR-breadth evidence files.

### Concrete Fixes To Make Next

1. Re-upload the GitHub `v1.1-deposit` assets from the current local artifacts,
   or cut `v1.1.1-deposit` from HEAD `882b839a`. Verify with `gh release view`
   and a downloaded-asset hash check, not just local files.
2. Replace the V1 appendix/table phrases that trigger false contradiction hits:
   avoid "Musical_Instruments only" and "NOT counted as a second-category pass"
   in favor of "the V1 Office campaign counts in no claim; Office V3 is reported
   separately in Section 5.2."
3. Move or fence the historical 35/36-page blocks in `paper_tex/BUILD_NOTES.md`.
4. If ACM access is available, inspect and archive the SILLM4Rec full-text
   protocol details; otherwise keep the current "pending full-text inspection"
   caveat.
5. Before submission/DOI minting, run the strict gate plus a release-download
   round trip: local hash, uploaded hash, downloaded zip entry hashes, and
   standalone PDF/manifest hashes must all agree.

### Open Questions

- Should the release be repaired in-place as `v1.1-deposit`, or should a fresh
  `v1.1.1-deposit` tag be cut to avoid ambiguity?
- Should `PAPER_SUBMISSION.pdf` be re-rendered after any wording cleanup even if
  only Appendix A.0 phrasing changes?
- Is SILLM4Rec full-text access available for a final protocol inspection before
  freeze?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Re-run strict manuscript/artifact gate.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Check PDFs for stale Office contradiction phrases.
- [x] Check local `v1.1` deposit bundle contents and hashes.
- [x] Download and compare GitHub `v1.1-deposit` release assets.
- [x] Fact-check current related-work/scope-out claims against external sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair or supersede uploaded `v1.1-deposit` assets.
- [ ] Rephrase V1 Office appendix/table wording to remove false-positive
      contradiction phrases.
- [ ] Clean or archive stale historical blocks in `paper_tex/BUILD_NOTES.md`.
- [ ] Inspect SILLM4Rec full paper or keep the caveat explicit.

## Audit Run - 2026-07-18 00:08 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74`.
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`;
  `CODEX_HOME` is not set in this PowerShell session, so the user-profile Codex
  home remains the effective memory location.
- Current run time: `2026-07-18 00:07:32 +10:00`; adjudicators printed
  `2026-07-18 00:08:48`.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Canonical sources/artifacts inspected this run:
  `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`,
  `paper_tex/main.tex`, `paper_tex/paper-shared.tex`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/PAPER_TORS_acmsmall.pdf`,
  `paper_tex/sections/abstract.tex`,
  `paper_tex/sections/01-introduction.tex`,
  `paper_tex/sections/02-related.tex`,
  `paper_tex/sections/03-method.tex`,
  `paper_tex/sections/04-experiments.tex`,
  `paper_tex/sections/05-results.tex`,
  `paper_tex/sections/06-discussion.tex`,
  `paper_tex/sections/07-conclusion.tex`,
  `paper_tex/sections/08-availability.tex`,
  `paper_tex/sections/appendix-a0.tex`,
  `paper_tex/tables/office_confirmation.tex`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `paper_tex/references.bib`, `RELEASE_MANIFEST.json`,
  `DOI_DEPOSIT_INSTRUCTIONS.md`, `_bestrec_run/build_hstu_tables.py`,
  `_bestrec_run/hstu_results_manifest.json`, `_release/bestrec_deposit_v1.0.zip`.

### Verdict

**The numerical artifact graph remains green, but the paper is still not ready
for top-journal submission.** The strict rebuild, Office V3 adjudicator, and
FIR-breadth adjudicator all pass again on July 18. The main narrative is now
much closer to coherent than the July 15 state: abstract, introduction, related
work, Section 5.2, discussion, conclusion, and Section 8 all generally carry the
two-track Office story (V1 VOID, V3 passed and counted only under frozen
point-estimate wording).

The remaining hard contradiction is narrower but still damaging: Appendix A.0
and the regenerated Office V1 table still say the confirmed per-category claim
remains Musical_Instruments only / Office is not counted. That stale wording is
visible in all live PDFs, so a reviewer can still quote an internal
contradiction from the submitted artifact.

The second hard blocker is packaging: the current deposit bundle remains the old
`v1.0-deposit` package and omits the newer Office V3 and FIR-breadth evidence.
The local strict gate can recompute the claims, but the archival story no longer
matches the paper's current claim set.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release manifest verification OK for `113` declared files.
  - PASS: MI V2 gate; legacy Office V1 descriptive/VOID check remains OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-18 00:08:48 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds
    above both references.
  - Dataset identity, reference artifacts, treestate sidecars, code hashes,
    and data SHA256s verified.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - CONFIRMED at `2026-07-18 00:08:48 Australia/Sydney`, block `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- PDF extraction with project-managed `uv` Python / `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; `SILLM4Rec` on page 19;
    `Office_Products V3` on page 22; stale "Office is not counted" and
    "Musical_Instruments only" on page 41.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; `SILLM4Rec` on page 18;
    `Office_Products V3` on page 20; stale "Office is not counted" and
    "Musical_Instruments only" on page 36; generated "NOT counted as a
    second-category pass" on page 37.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; `SILLM4Rec` on page 18;
    `Office_Products V3` on page 20; stale Office wording and generated
    "NOT counted as a second-category pass" on page 37.
- Source/release searches
  - Stale Office wording remains in `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`,
    `paper_tex/sections/appendix-a0.tex`,
    `paper_tex/tables/office_confirmation.tex`, and
    `_bestrec_run/build_hstu_tables.py`.
  - `paper_tex/references.bib` still has no `SILLM4Rec`, `UniSGR`, `DIGER`,
    `ACERec`, or semantic-planning entry.
  - `paper_tex/hygiene_scan_output.txt` remains PASS: `PAPER_TORS.pdf`,
    40 pages, `0` placeholder/forbidden failures, `20` informational review
    hits.
  - `_release/bestrec_deposit_v1.0.zip`: 780,381 bytes, SHA256
    `8FD3EB58E35E695D910B960B4CACF85C50E23E6FF77EC0A637953655F1D08770`,
    48 entries under `bestrec_deposit_v1.0/`. It contains no Office V3
    prereg/results files, no FIR-breadth prereg/results files, no current
    `paper_tex/PAPER_TORS.pdf`, and no `DOI_DEPOSIT_INSTRUCTIONS.md`.
  - `DOI_DEPOSIT_INSTRUCTIONS.md` still says the prepared deposit bundle has
    `46` files and points to GitHub release `v1.0-deposit`; the local zip has
    48 entries.

### External Fact-Check / Novelty Notes

- Amazon Reviews 2023 official documentation supports the dataset framing:
  McAuley Lab release, 571.54M reviews, interactions through September 2023,
  rich metadata, links, and standard splitting. Source:
  https://amazon-reviews-2023.github.io/
- HSTU-BLaIR remains the relevant stronger AR2023 5-core reference named by
  the paper; the arXiv record is current at `2504.10545`. Source:
  https://arxiv.org/abs/2504.10545
- SILLM4Rec is now too concrete to leave uncited. ACM metadata says the MMAsia
  2025 paper uses three 5-core Amazon Reviews 2023 datasets, while the public
  repository describes image descriptions, user-preference summaries, candidate
  product-ranking tasks, and SFT/DPO training data. This supports the
  manuscript's non-interchangeability rationale, but the named exclusion needs
  a formal citation and preferably a direct protocol note. Sources:
  https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec
- ChronoSID is cited and the checked arXiv abstract supports the manuscript's
  characterization as semantic-ID generative recommendation with temporal-gap
  augmentation. Source: https://arxiv.org/abs/2607.03918
- UniSGR is a current semantic-ID generation-and-ranking paper, but its checked
  evidence is private/industrial Lazada evaluation plus online A/B testing, not
  the AR2023 full-catalog LLOO protocol. It is a related-work coverage risk,
  not a direct comparator. Source: https://arxiv.org/html/2607.04068
- Additional 2026 semantic-ID/generative-recommendation work found in this run
  but absent from the bibliography: DIGER, which aligns semantic ID learning
  with recommendation gradients via differentiable SIDs, and ACERec, which
  targets long semantic IDs and reports average NDCG@10 improvement across six
  benchmarks. These are plausible scope-out/citation items if the paper keeps
  a broad 2026 semantic-ID paragraph. Sources:
  https://arxiv.org/abs/2601.19711 and https://arxiv.org/abs/2602.13573
- The 2026 semantic-planning position paper is not a comparator, but it is a
  current framing paper on raw IDs, semantic IDs, and semantic planning; cite or
  ignore intentionally, not accidentally. Source:
  https://arxiv.org/pdf/2607.09540

### Confirmed Problems

1. **Appendix A.0 still contradicts Office V3.** The V1 Office campaign should
   remain VOID, but the broad "confirmed per-category claim remains
   Musical_Instruments only; Office is not counted" sentence is false after the
   separate V3 pre-registration passed and was counted under its narrow frozen
   wording.
2. **The generated Office table/template preserves the contradiction.** The
   stale status line is emitted by `_bestrec_run/build_hstu_tables.py`, so the
   repair must update the generator, regenerate `paper_tex/tables/office_confirmation.tex`,
   and rebuild the PDFs.
3. **The deposit zip is stale.** It omits Office V3, FIR-breadth, current TORS
   PDF/source boundary material, and current deposit instructions.
4. **Build notes are stale.** `paper_tex/BUILD_NOTES.md` still mixes current
   40/40 claims, a current 41-page acmsmall PDF, old 35/36-page notes, and an
   old 35-page hygiene block.
5. **SILLM4Rec is named but uncited.** The exclusion is defensible from the
   public workflow evidence, but top-journal related work should cite the ACM
   DOI/repo or avoid naming the work.

### Confirmed Fixes / Non-Problems Since The Prior Section

- The main paper narrative is substantially repaired: abstract, introduction,
  related work, Section 5.2, Section 6.4/6.5, conclusion, and Section 8 now
  generally distinguish Office V1 VOID from Office V3 PASSED.
- Section 8 now states a coherent tracked-artifact boundary for Office V3
  printed claims and local-only per-user sidecars.
- The strict artifact graph remains green; no numerical mismatch, untraceable
  empirical cell, missing claim family, or HSTU parity failure was found.
- Office V3 and FIR-breadth adjudicators remain mechanically green on fresh
  runs.
- A manuscript-source search for obvious mojibake markers (`â`, `Ã`, `Â`, `�`)
  found no matches in `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, or `paper_tex`;
  the odd glyphs visible in PowerShell output appear to be console decoding of
  UTF-8 text/PDF extraction rather than source corruption.

### Plausible Risks Requiring Author Verification

- Whether the final submission requires a DOI/deposit at submission time or can
  rely on the tracked-artifact boundary with sidecars provided on request. The
  current paper text chooses the latter for per-user sidecars, but the existing
  deposit instructions still present an obsolete ready-to-mint package.
- Whether `PAPER_SUBMISSION.pdf` remains a live artifact now that it is 45 pages
  while TORS review PDF is 40 pages and acmsmall preview is 41 pages.
- Whether the SILLM4Rec ACM PDF should be directly inspected and archived in
  the audit chain, or whether the public repo/ACM metadata is enough for a
  cautious non-comparability statement.
- Which of UniSGR, DIGER, ACERec, and the semantic-planning position paper
  should enter the related-work paragraph versus be explicitly out of scope.

### Concrete Fixes To Make Next

1. Replace the Appendix A.0 stale sentence with a two-track statement: V1 Office
   is VOID and not counted; V3 Office is a separate passed pre-registration
   counted only as a per-category point-estimate comparison, not paired
   superiority or SOTA.
2. Update `_bestrec_run/build_hstu_tables.py` so regenerated
   `paper_tex/tables/office_confirmation.tex` says the Office V1 table is not
   counted, while Office V3 is handled separately in Section 5.2.
3. Regenerate TeX/PDFs and rerun the strict gate plus PDF phrase checks.
4. Refresh `paper_tex/BUILD_NOTES.md` page counts, compile status, and hygiene
   block.
5. Rebuild `_release/bestrec_deposit_v1.0.zip` or create a new deposit version
   that matches the current Section 8 reproducibility boundary, and update
   `DOI_DEPOSIT_INSTRUCTIONS.md`.
6. Add a SILLM4Rec bibliography entry and revise the exclusion sentence to cite
   the ACM paper/repo evidence; decide whether UniSGR/DIGER/ACERec require
   citations or explicit scope-out language.

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, release, and audit
      artifacts.
- [x] Re-run strict manuscript/artifact gate.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Re-check PDF page counts and stale Office/SILLM/V3 phrase locations.
- [x] Re-check DOI/deposit zip contents and hash.
- [x] Fact-check dataset, comparator, SILLM4Rec, and current semantic-ID
      related-work claims against external sources.
- [x] Refresh the current prioritized rejection-risk list.
- [x] Insert this timestamped audit section.
- [ ] Repair Appendix A.0 plus generated Office table/template wording.
- [ ] Rebuild current PDFs after the wording fix.
- [ ] Refresh build notes and release/deposit package.
- [ ] Add SILLM4Rec citation and decide UniSGR/DIGER/ACERec scope.

## Audit Run - 2026-07-15 04:17 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74`.
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`;
  `$CODEX_HOME` is unset in this PowerShell session, so the user-profile Codex
  home remains the effective memory location.
- Current run time: `2026-07-15 04:17:16 +10:00`.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Canonical sources/artifacts inspected this run:
  `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/PAPER_TORS_acmsmall.pdf`,
  `paper_tex/sections/05-results.tex`,
  `paper_tex/sections/06-discussion.tex`,
  `paper_tex/sections/08-availability.tex`,
  `paper_tex/sections/appendix-a0.tex`,
  `paper_tex/tables/office_confirmation.tex`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `paper_tex/references.bib`, `PREREG_OFFICE_V3.md`,
  `OFFICE_V3_RESULTS.md`, `PREREG_FIR_BREADTH.md`,
  `FIR_BREADTH_RESULTS.md`, `RELEASE_MANIFEST.json`,
  `DOI_DEPOSIT_INSTRUCTIONS.md`, `_bestrec_run/build_hstu_tables.py`,
  `_bestrec_run/hstu_results_manifest.json`, and
  `_release/bestrec_deposit_v1.0.zip`.

### Verdict

**No numerical/provenance failure was found; the paper is still not
submission-ready.** The strict rebuild, Office V3 adjudicator, and FIR-breadth
adjudicator all pass again at 04:17. The strongest remaining rejection risk is
not the numbers; it is that the live appendix and generated Office table still
say Office is not counted while the abstract, Section 5.2, discussion, and
availability text count the separate Office V3 pass under its frozen claim.

The release/deposit story is still stale relative to the current claim set.
Section 8 now states a coherent tracked-artifact boundary, but the actual DOI
deposit zip remains the old 48-entry package and includes none of the Office V3
or FIR-breadth prereg/results artifacts. A top-journal reviewer would treat that
as a packaging/reproducibility defect even though the strict gate verifies its
declared local scope.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release manifest verification OK for `113` declared files.
  - PASS: MI V2 gate; legacy Office V1 descriptive/VOID check remains OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-15 04:17:37 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds
    above both references.
  - Dataset identity, reference artifacts, treestate sidecars, code hashes,
    and data SHA256s verified.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - CONFIRMED at `2026-07-15 04:17:37 Australia/Sydney`, block `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- PDF extraction with project-managed `uv` Python / `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; stale Office wording on page 41;
    `SILLM4Rec` on page 19; `Office_Products V3` on page 22.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; stale Office wording on page 36;
    `SILLM4Rec` on page 18; `Office_Products V3` on page 20.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; stale "Office is not
    counted" and generated "NOT counted as a second-category pass" wording on
    page 37; `SILLM4Rec` on page 18; `Office_Products V3` on page 20.
- Source/release searches
  - `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`,
    `paper_tex/sections/appendix-a0.tex`,
    `paper_tex/tables/office_confirmation.tex`, and
    `_bestrec_run/build_hstu_tables.py` still contain the stale
    `Musical_Instruments only` / `Office is not counted` boundary.
  - `paper_tex/references.bib` still has no SILLM4Rec or UniSGR entry.
  - `paper_tex/hygiene_scan_output.txt` remains PASS: `PAPER_TORS.pdf`,
    40 pages, `0` placeholder/forbidden failures, `20` informational review
    hits.
  - `_release/bestrec_deposit_v1.0.zip`: 780,381 bytes, SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`,
    `48` entries, and `0` matches for `OFFICE_V3`, `PREREG_OFFICE_V3`,
    `FIR_BREADTH`, `PREREG_FIR_BREADTH`, `PAPER_TORS`,
    `DOI_DEPOSIT_INSTRUCTIONS`, `results_OFFICEV3`, or `results_FIRB`.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR v3 supports the paper's comparator constants and dataset-stat
  framing: it evaluates AR2023 5-core Video Games, Office Products, and
  Musical Instruments, with table values including Video Games HSTU-BLaIR
  `0.0760`, Office Products `0.0271`, and Musical Instruments `0.0406` for
  NDCG@10. Source: https://arxiv.org/html/2504.10545v3
- Amazon Reviews 2023 official documentation supports the dataset framing:
  McAuley Lab release, 571.54M reviews, interactions through September 2023,
  rich metadata, links, and standard splitting. Source:
  https://amazon-reviews-2023.github.io/
- SILLM4Rec remains a live citation problem, not a direct comparator. The ACM
  page frames it as a reranking/LLM recommendation paper, and the public GitHub
  workflow uses AR2023 5-core files but generates candidate-product ranking
  tasks plus SFT/DPO data. That supports the manuscript's non-interchangeability
  rationale, but the named exclusion needs a formal citation and/or inspection
  note. Sources: https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec
- UniSGR remains a plausible related-work coverage risk. It is not an AR2023
  comparator because it reports industrial/private e-commerce evaluation, but it
  is current semantic-ID generation/ranking work that explicitly unifies
  generative retrieval with discriminative ranking. Source:
  https://arxiv.org/html/2607.04068v1

### Confirmed Problems

1. **Appendix A.0 contradicts Office V3.** The V1 Office campaign should remain
   VOID, but the broad "Office is not counted" sentence is now false because
   the separate V3 pre-registration passed and is counted under its narrow
   frozen wording.
2. **The generated Office table/template preserves the contradiction.**
   Updating only the prose appendix will not be enough; the generated
   `office_confirmation.tex` source text in `_bestrec_run/build_hstu_tables.py`
   must change too.
3. **The deposit zip is stale.** The current DOI/deposit bundle omits Office
   V3, FIR-breadth, current TORS PDF, and current deposit instructions.
4. **Build notes/presentation remain stale.** `PAPER_TORS_acmsmall.pdf` is
   currently 41 pages while `BUILD_NOTES.md` still says current builds are
   40/40 and embeds old 35/36-page and 14-hit hygiene notes.
5. **SILLM4Rec is named but uncited.** The exclusion is directionally
   defensible, but top-journal related work should cite the ACM DOI/repo or
   state that direct PDF inspection is pending.

### Plausible Risks Requiring Author Verification

- Whether the final deposit should include local-only Office/FIR per-user
  sidecars or only the tracked aggregate JSON/provenance boundary. Section 8
  chooses the latter, but the DOI/deposit package must match that policy.
- Whether UniSGR, OneRec-style industrial generative-ranking work, or adjacent
  semantic-ID/ranking unification papers should be cited in the same paragraph
  as SID-MLP/Latte/ReSID/ChronoSID.
- Whether `PAPER_SUBMISSION.pdf` remains a live deliverable now that it is 45
  pages while the TORS review artifact is 40 pages and the acmsmall preview is
  41 pages.

### Concrete Fixes To Make Next

1. Replace the Appendix A.0 sentence with a two-track statement: V1 Office is
   VOID and not counted; V3 Office is a separate passed pre-registration counted
   only as a per-category point-estimate comparison, not paired superiority or
   SOTA.
2. Update `_bestrec_run/build_hstu_tables.py` so regenerated
   `paper_tex/tables/office_confirmation.tex` says the Office V1 table is
   not counted, while Office V3 is handled separately in Section 5.2.
3. Regenerate the TeX/PDFs and rerun the strict build plus PDF phrase checks.
4. Refresh `paper_tex/BUILD_NOTES.md` page counts and hygiene block.
5. Rebuild `_release/bestrec_deposit_v1.0.zip` or create a new deposit version
   that matches the current Section 8 reproducibility boundary, and update
   `DOI_DEPOSIT_INSTRUCTIONS.md`.
6. Add a SILLM4Rec bibliography entry and revise the exclusion sentence to cite
   the ACM paper/repo evidence; add or explicitly scope out UniSGR.

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, release, and audit
      artifacts.
- [x] Re-run strict manuscript/artifact gate.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Re-check PDF page counts and stale Office/SILLM/V3 phrase locations.
- [x] Re-check DOI/deposit zip contents and hash.
- [x] Fact-check comparator/dataset/related-work claims against external
      sources.
- [x] Refresh the current prioritized rejection-risk list.
- [x] Insert this timestamped audit section.
- [ ] Repair Appendix A.0 plus generated Office table/template wording.
- [ ] Rebuild current PDFs after the wording fix.
- [ ] Refresh build notes and release/deposit package.
- [ ] Add SILLM4Rec citation and decide UniSGR scope.

## Audit Run - 2026-07-15 02:15 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74`.
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`;
  `$CODEX_HOME` remains unset in this PowerShell session, so the user-profile
  Codex home is the effective memory location.
- Current run time: `2026-07-15 02:15:49 +10:00`.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Canonical sources/artifacts inspected:
  `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, `CANONICAL_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/sections/abstract.tex`,
  `paper_tex/sections/02-related.tex`, `paper_tex/sections/05-results.tex`,
  `paper_tex/sections/08-availability.tex`,
  `paper_tex/sections/appendix-a0.tex`,
  `paper_tex/tables/table0_novelty.tex`,
  `paper_tex/tables/office_confirmation.tex`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `paper_tex/references.bib`, `PREREG_OFFICE_V3.md`,
  `OFFICE_V3_RESULTS.md`, `PREREG_FIR_BREADTH.md`,
  `FIR_BREADTH_RESULTS.md`, `RELEASE_MANIFEST.json`,
  `DOI_DEPOSIT_INSTRUCTIONS.md`, `_bestrec_run/build_hstu_tables.py`,
  `_bestrec_run/hstu_results_manifest.json`, and
  `_release/bestrec_deposit_v1.0.zip`.

### Verdict

**No new numerical/provenance failure appeared, but the manuscript remains
rejectable on presentation and packaging.** The strict artifact graph, Office V3
adjudicator, and FIR-breadth adjudicator all pass again at 02:13. The hard
submission-facing contradiction is still rendered in all live PDFs: Appendix A.0
and the generated Office V1 table say Office is not counted, while the
abstract/Section 5.2 correctly count the separate Office V3 pass.

The packaging blocker is unchanged: the release manifest verifies within its
declared scope, but the actual DOI/deposit zip is still the old 48-entry bundle
and contains none of the current Office V3, FIR-breadth, TORS, or deposit
instruction artifacts. This will look careless to a top-journal reviewer even
though the Section 8 tracked-artifact policy is now coherent.

This run also found one new **plausible novelty-coverage risk**: UniSGR
(arXiv:2607.04068, posted 2026-07-05) is a current semantic-ID
generation-and-ranking paper. It is not a direct AR2023 comparator because it
uses private Lazada homepage logs, but the manuscript's 2026 generative-retrieval
paragraph should cite or explicitly scope it out to avoid an "incomplete related
work" objection.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release manifest verification OK for `113` declared files.
  - PASS: MI V2 gate; legacy Office V1 descriptive/VOID check remains OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-15 02:13:32 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds
    above both references.
  - Dataset identity, reference artifact hashes, treestate sidecars, code
    hashes, and data SHA256s verified.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - CONFIRMED at `2026-07-15 02:13:32 Australia/Sydney`, block `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- PDF extraction with project-managed `uv` Python / `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; stale Office wording on page 41;
    `SILLM4Rec` on page 19; `Office_Products V3` on page 22.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; stale Office wording on page 36;
    `SILLM4Rec` on page 18; `Office_Products V3` on page 20.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; stale Office wording on
    page 37; `SILLM4Rec` on page 18; `Office_Products V3` on page 20.
- Source/release searches
  - `paper_tex/sections/appendix-a0.tex`,
    `paper_tex/tables/office_confirmation.tex`, and
    `_bestrec_run/build_hstu_tables.py` still contain the stale
    `Musical_Instruments only; Office is not counted` boundary.
  - `paper_tex/references.bib` has the recently added SID-MLP, Latte, GrIT,
    ReSID, ChronoSID, Augment-or-Not, DiffuReason, FEARec, and WPGRec entries.
    It still has no SILLM4Rec or UniSGR entry.
  - `rg "UniSGR|OneRec|VA-PMTP|Task-Aware Tokens"` found no coverage in the
    paper sources or bibliography.
  - `paper_tex/hygiene_scan_output.txt` remains PASS: `PAPER_TORS.pdf`, 40
    pages, `0` placeholder/forbidden failures, `20` informational review hits.
  - `_release/bestrec_deposit_v1.0.zip`: 780,381 bytes, SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`,
    `48` entries, and `0` matches for `OFFICE_V3`, `PREREG_OFFICE_V3`,
    `FIR_BREADTH`, `PREREG_FIR_BREADTH`, `PAPER_TORS`,
    `DOI_DEPOSIT_INSTRUCTIONS`, `results_OFFICEV3`, or `results_FIRB`.
  - `git ls-files` confirms Office V3 and FIR-breadth prereg/results JSONs are
    tracked, including Office V3 treestate sidecars and 20 FIR-breadth result
    JSONs.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR v3 continues to support the comparator framing: it evaluates AR2023
  Video Games, Office Products, and Musical Instruments 5-core subsets; the
  visible table gives the matching Video Games statistics, and the task section
  states chronological leave-one-out evaluation. Source:
  https://arxiv.org/html/2504.10545v3
- Amazon Reviews 2023 official documentation still supports the dataset
  framing: 571.54M reviews, interactions through September 2023, rich item
  metadata, links, and standard splits. Source:
  https://amazon-reviews-2023.github.io/
- SILLM4Rec remains a live related-work/citation problem. ACM metadata/PDF
  snippets state that it uses three 5-core AR2023 subdatasets and reports
  NDCG@K, while the public repo describes generated candidate-product ranking
  tasks, image-description generation, user-preference summaries, SFT, and DPO.
  This supports non-interchangeability, not omission. Sources:
  https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec
- UniSGR is new novelty-pressure evidence since the paper's last related-work
  expansion. It introduces a unified semantic-ID generation/ranking framework
  with Task-Aware Tokens, VA-PMTP, STARK beam-search/KV-cache engineering, and
  evaluations on private Lazada homepage logs. Because the dataset is private
  and not AR2023, it is not a comparator; because it is same-month semantic-ID
  generative recommendation work, it is a related-work coverage risk. Source:
  https://arxiv.org/html/2607.04068v1
- Latte remains correctly treated as same-statistics AR2023 LLOO novelty
  pressure rather than a validated comparator; its appendix reports NDCG@10
  values of `0.0331`, `0.0249`, and `0.0515` for Instruments, Scientific, and
  Games. Source: https://arxiv.org/html/2605.06331
- ChronoSID remains correctly treated as a different SID-line universe rather
  than a direct comparator; it uses leave-one-out with generated semantic ID
  tuples and beam search, and prior audits found its MI statistics differ from
  the HSTU-BLaIR-family statistics. Source:
  https://arxiv.org/html/2607.03918

### Confirmed Problems

1. **Appendix A.0 still contradicts Office V3.** The V1 Office campaign can and
   should remain VOID, but the broad sentence "Office is not counted" is false
   after the separate V3 pre-registration passed.
2. **The generated Office table/template will preserve the contradiction.**
   Repairing only the TeX appendix is insufficient; the generated table and
   `_bestrec_run/build_hstu_tables.py` wording must also be updated.
3. **The deposit zip is stale relative to current claims.** The tracked
   reproducibility boundary is now clearly stated in Section 8, but the archival
   bundle and DOI instructions still advertise the old package.
4. **Rendered presentation still has readiness defects.** The acmsmall PDF is
   41 pages while `BUILD_NOTES.md` still describes current builds as 40/40; the
   notes also retain older 35/36-page hygiene text. Prior visual audit also
   found Table 2's caption split from its body.
5. **SILLM4Rec is still uncited.** The paper names it and excludes it pending
   direct inspection, but no bibliography entry or inspection note exists.
6. **UniSGR is missing from related work.** This is a plausible risk, not a hard
   flaw: it is not a direct benchmark comparator, but it is recent enough and
   close enough to the semantic-ID line that a strict reviewer may expect a
   sentence.

### Confirmed Non-Problems

- The strict artifact graph still recomputes the printed empirical cells and
  sees Office V3 and FIR-breadth evidence.
- Office V3 aggregate evidence is mechanically green and properly scoped as a
  point-estimate comparison, not paired superiority or SOTA.
- FIR-breadth is mechanically green and properly scoped as internal
  filter-vs-no-filter evidence, not a comparator claim.
- Section 8's tracked-artifact vs local-only-sidecar policy is now coherent; the
  unresolved release issue is the stale zip/DOI package, not an undefined
  reproducibility boundary.
- The current Section 5.1 "no comparative claim against concurrent arXiv-only
  work" wording remains necessary and defensible.

### Concrete Fixes To Make Next

1. Rewrite Appendix A.0 so the V1 Office VOID stands, but all global "Office is
   not counted" wording is qualified as "V1 is not counted; V3 is counted under
   its separate redesigned pre-registration."
2. Regenerate/fix `paper_tex/tables/office_confirmation.tex` and
   `_bestrec_run/build_hstu_tables.py` so the stale V1-only claim cannot return.
3. Refresh `_release/bestrec_deposit_v1.0.zip`, `_release/SHA256SUMS.txt`, and
   `DOI_DEPOSIT_INSTRUCTIONS.md`, or mark the existing zip as a historical
   pre-Office-V3/pre-FIR-breadth bundle and add a current package.
4. Refresh `paper_tex/BUILD_NOTES.md` against the actual 40-page TORS and
   41-page acmsmall PDFs; fix the Table 2 caption/body split before final
   submission.
5. Add a formal SILLM4Rec citation and a concrete exclusion sentence based on
   ACM DOI plus the public repo workflow, or archive a full-paper protocol
   inspection.
6. Add one related-work sentence for UniSGR: current semantic-ID
   generation/ranking work on private Lazada logs, not AR2023 and therefore not
   a direct comparator.

### Open Questions

- Is the current DOI/deposit zip meant to be submission-current, or should the
  manuscript/release docs label it as a historical package while the tracked
  repository remains the live reproducibility boundary?
- Should Appendix A.0 remain in the main submission after V3 passed, or should
  V1 VOID details move to supplementary material to reduce reader confusion?
- Can the authors access and archive the SILLM4Rec ACM full text, or should the
  paper cite the DOI/repo and explicitly state that only public workflow evidence
  was inspected?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Re-run strict manuscript/artifact gate.
- [x] Re-run Office V3 adjudicator dynamically.
- [x] Re-run FIR-breadth adjudicator dynamically.
- [x] Extract live PDF page counts and stale Office/SILLM4Rec/Office V3 hits.
- [x] Check release/deposit zip contents and SHA256.
- [x] Check bibliography coverage for 2026 semantic-ID/generative retrieval
      sources.
- [x] Perform fresh external novelty search; flag UniSGR.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair Appendix A.0 and generated Office V1 table/template.
- [ ] Refresh stale release/deposit packaging and DOI instructions.
- [ ] Refresh stale `paper_tex/BUILD_NOTES.md` and table layout.
- [ ] Add/inspect SILLM4Rec citation evidence.
- [ ] Add/scope UniSGR in the semantic-ID related-work paragraph.

## Audit Run - 2026-07-15 01:13 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read from
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`;
  `$CODEX_HOME` is unset in this PowerShell session, so the user-profile Codex
  home is the effective memory location.
- Current run time: `2026-07-15 01:16:17 +10:00`.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Canonical sources/artifacts inspected:
  `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, `CANONICAL_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/sections/05-results.tex`,
  `paper_tex/sections/appendix-a0.tex`, `paper_tex/tables/office_confirmation.tex`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `paper_tex/references.bib`, `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
  `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`,
  `RELEASE_MANIFEST.json`, `DOI_DEPOSIT_INSTRUCTIONS.md`,
  `_bestrec_run/build_hstu_tables.py`,
  `_bestrec_run/hstu_results_manifest.json`, and
  `_release/bestrec_deposit_v1.0.zip`.

### Verdict

**The empirical gates remain green, but the paper is still rejectable on a
submission-facing contradiction and stale release packaging.** Office V3 is
mechanically supported and correctly described in Section 5.2 / Section 6.5 /
Section 8, but Appendix A.0 and the generated Office V1 table still state that
Office is not counted and the confirmed per-category claim remains
Musical_Instruments only. That sentence is present in the live PDFs, so a
reviewer will see the contradiction.

The second live blocker is archival: the current strict gate sees Office V3 and
FIR-breadth evidence, but the deposit zip and DOI instructions still reflect the
older pre-Office-V3/pre-FIR-breadth bundle. This is a readiness problem even if
the manuscript itself says DOI minting is deferred.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release manifest verification OK for `113` files.
  - PASS: MI V2 gate; legacy Office V1 descriptive/VOID check remains OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-15 01:13 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds
    above both references.
  - Comparability conditions OK: dataset identity, reference artifact hashes,
    treestate sidecars, embedded code hashes, and data SHA256s.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS/CONFIRMED at `2026-07-15 01:16 Australia/Sydney`, block
    `9a38ad66bd75`.
  - Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - CDs_and_Vinyl: mean `+0.00566`, 95% CI `[+0.00493,+0.00639]`,
    `5/5` positive.
- PDF extraction with project-managed `uv` Python / `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; "The confirmed per-category claim
    remains" and "Office is not counted" on page 41; `SILLM4Rec` on page 19;
    `Office_Products V3` on page 22.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; stale Office wording on page 36;
    `SILLM4Rec` on page 18; `Office_Products V3` on page 20.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; "Office is not counted" on
    page 37; `SILLM4Rec` on page 18; `Office_Products V3` on page 20.
- Source searches
  - `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
    `paper_tex/sections/appendix-a0.tex` still contain the stale
    "Musical_Instruments only; Office is not counted" sentence.
  - `paper_tex/tables/office_confirmation.tex` still says the V1 table is not a
    second-category pass and that the confirmed per-category claim remains
    Musical_Instruments only.
  - `_bestrec_run/build_hstu_tables.py` still contains the generated table
    template text that will reintroduce this stale boundary.
  - `paper_tex/references.bib` still has no `SILLM4Rec`,
    `10.1145/3743093.3771011`, or `MKC-Lab` entry.
  - `paper_tex/hygiene_scan_output.txt` reports `PAPER_TORS.pdf`, 40 pages,
    `0` placeholder/forbidden failures, and `20` informational
    SOTA/negated-claim review hits.
- `_release/bestrec_deposit_v1.0.zip` check
  - Timestamp `2026-07-11T22:11:05`, length `780381`, SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`,
    `48` entries.
  - Contains `0` matches for `OFFICE_V3`, `PREREG_OFFICE_V3`, `FIR_BREADTH`,
    `PREREG_FIR_BREADTH`, `PAPER_TORS`, `DOI_DEPOSIT_INSTRUCTIONS`,
    `results_OFFICEV3`, and `results_FIRB`.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR arXiv v3 continues to support the comparator constants used here:
  HSTU-BLaIR NDCG@10 is `0.0760` for Video Games, `0.0271` for Office Products,
  and `0.0406` for Musical Instruments. Source:
  https://arxiv.org/abs/2504.10545
- Amazon Reviews 2023's official site confirms the dataset is a 2023 McAuley
  Lab release with reviews, item metadata, links, 571.54M reviews,
  interactions through September 2023, and standard splitting. Source:
  https://amazon-reviews-2023.github.io/
- SID-MLP is close novelty pressure, not a clean comparator. Its arXiv paper
  evaluates Musical Instruments, Industrial & Scientific, and Video Games from
  Amazon Reviews 2023 and reports MI `57,439` users / `24,587` items /
  `511,836` interactions and Games `94,762` / `25,612` / `814,586`. Source:
  https://arxiv.org/html/2605.12617
- Latte is also close novelty pressure. Its arXiv paper reports Amazon Reviews
  2023 Instruments/Scientific/Game leave-one-out results, including Latte
  NDCG@10 `0.0331` for Instruments and `0.0515` for Game. Source:
  https://arxiv.org/pdf/2605.06331
- GrIT's paper supports the manuscript's statement that it uses matching
  Video_Games statistics (`94,762` users / `25,612` items / `814,586`
  interactions), full-item-set evaluation, and Video_Games NDCG@10 `0.0588`.
  Source: https://arxiv.org/html/2602.19728
- ChronoSID/ReSID remain a distinct-protocol boundary: ChronoSID reports MI
  `57,359` users / `23,742` items / `490,522` interactions and VG `94,515` /
  `24,685` / `772,218`, which differ from the HSTU-BLaIR-family statistics.
  ReSID reports MI NDCG@10 `0.0346` in its own filtered setup. Sources:
  https://arxiv.org/html/2607.03918v1 and https://arxiv.org/html/2602.02338v1
- `Augment or Not?` supports the manuscript's non-comparability framing: it
  uses AR2023 Musical_Instruments / Industrial_and_Scientific under 5-core
  leave-one-out and reports LETTER-TIGER MI NDCG@10 `0.0282`. Source:
  https://arxiv.org/html/2505.23053v1
- DiffuReason supports the manuscript's non-interchangeable-protocol warning:
  it reports a "Video & Games" dataset with `67,658` users / `25,535` items /
  `654,867` interactions, uses rating `> 3` positives, length 20 histories, and
  full ranking over its item set. Source: https://arxiv.org/pdf/2602.09744
- SILLM4Rec remains under-cited. ACM metadata identifies a 2025 MMAsia paper
  using Amazon Reviews 2023 5-core subdatasets and NDCG metrics, while the
  public repository describes 5-core AR2023 inputs followed by image
  descriptions, user preference summaries, candidate product ranking tasks, and
  SFT/DPO training. That supports non-interchangeability with full-catalog LLOO,
  but the manuscript still needs a formal citation or direct full-paper
  inspection record. Sources: https://dl.acm.org/doi/10.1145/3743093.3771011
  and https://github.com/MKC-Lab/SILLM4Rec

### Confirmed Problems

1. **Appendix A.0 remains internally false after Office V3.** The V1 campaign
   can remain VOID, but the broad "Office is not counted" sentence contradicts
   the counted V3 campaign.
2. **The generated Office V1 table and template will reintroduce the same
   contradiction.** `paper_tex/tables/office_confirmation.tex` and
   `_bestrec_run/build_hstu_tables.py` still say the confirmed per-category
   claim remains Musical_Instruments only.
3. **The deposit bundle is stale relative to current claims.** The local zip and
   `DOI_DEPOSIT_INSTRUCTIONS.md` still describe the older deposit and omit
   Office V3, FIR-breadth, and TORS artifacts needed for the current paper.
4. **Build-note/page-count documentation is not reliable.** The acmsmall preview
   is 41 pages by fresh extraction, while `paper_tex/BUILD_NOTES.md` still
   describes the production preview/current builds as 40/40 and embeds older
   35/36-page hygiene text.
5. **SILLM4Rec remains a citation-readiness defect.** The paper names it, and
   accessible evidence supports a non-interchangeable protocol, but a top
   reviewer can object to an uncited exclusion of a 2025 AR2023/NDCG work.

### Confirmed Non-Problems

- No numerical mismatch, untraceable empirical cell, or strict-gate failure was
  found.
- Office V3 aggregate evidence remains mechanically green under its frozen
  point-estimate wording.
- FIR-breadth remains mechanically confirmed under the frozen internal
  filter-vs-no-filter rule.
- Section 8's tracked-artifact vs local-only-sidecar deposit policy is now
  coherent; the remaining release problem is the stale deposit bundle, not the
  manuscript's sidecar boundary wording.
- The HSTU-BLaIR comparator constants and the 2026 related-work protocol
  boundaries remain externally supported by the checked sources.

### Concrete Fixes To Make Next

1. Rewrite the Appendix A.0 Office sentence in `PAPER_SUBMISSION.md`,
   `PAPER_DRAFT.md`, and `paper_tex/sections/appendix-a0.tex`: "The V1 campaign
   is not counted; the separate V3 campaign passed and is counted only under
   frozen per-category point-estimate wording."
2. Update `_bestrec_run/build_hstu_tables.py` and regenerate
   `paper_tex/tables/office_confirmation.tex` so the Office V1 table cannot
   reintroduce "Musical_Instruments only" after V3.
3. Refresh `_release/bestrec_deposit_v1.0.zip`, `_release/SHA256SUMS.txt`, and
   `DOI_DEPOSIT_INSTRUCTIONS.md`, or explicitly mark the existing deposit as
   superseded/pre-V3 and create a current `v1.1`/`v1.0-refresh` bundle.
4. Refresh `paper_tex/BUILD_NOTES.md`: current page counts are TORS 40,
   acmsmall 41, `PAPER_SUBMISSION.pdf` 45; replace the stale embedded hygiene
   block with the current 40-page / 20-review-hit PASS block.
5. Add a formal SILLM4Rec citation/repo note or inspect the ACM PDF directly
   before freeze; keep the exclusion tied to candidate-ranking/SFT-DPO workflow
   evidence rather than vague "pending direct protocol inspection" alone.

### Open Questions

- Is the deposit bundle intended to be submission-current now, or should the
  paper explicitly say release/deposit packaging will be refreshed only at
  acceptance?
- Should `RELEASE_MANIFEST.json` gain explicit Office V3 and FIR-breadth
  documentation/result families, or is `hstu_results_manifest.json` plus git
  tracking the intended source of truth?
- Is `PAPER_SUBMISSION.pdf` still a live deliverable now that the TORS artifact
  is the named review artifact and page counts differ?
- Can the authors access the SILLM4Rec ACM full text, or should the paper cite
  ACM metadata plus the public repo workflow as the explicit exclusion basis?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Search manuscript, TeX, generated tables, and table generators for stale
      Office V1/V3 wording.
- [x] Re-run Office V3 adjudicator dynamically.
- [x] Re-run strict manuscript/artifact gate.
- [x] Re-run FIR-breadth adjudicator dynamically.
- [x] Check compiled PDF page counts and stale-phrase locations.
- [x] Check release/deposit zip contents and SHA256.
- [x] Fact-check current related-literature claims against HSTU-BLaIR,
      AR2023, SID-MLP, Latte, GrIT, ReSID/ChronoSID, Augment-or-Not,
      DiffuReason, and SILLM4Rec sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair Appendix A.0 and the generated Office V1 table/template.
- [ ] Refresh stale release/deposit packaging and DOI instructions.
- [ ] Refresh stale `paper_tex/BUILD_NOTES.md`.
- [ ] Add/inspect SILLM4Rec citation evidence.

## Audit Run - 2026-07-14 23:12 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  (`$CODEX_HOME` was unset in this shell, so the standard user-profile Codex
  home was used).
- Current run time: `2026-07-14 23:12:10 +10:00`.
- User-provided previous cutoff: `2026-07-14T12:10:43.242Z` (`2026-07-14
  22:10:43 +10:00`). Before this audit's own commands, the only workspace file
  newer than that cutoff was `_bestrec_run/hstu_tables.json` at `22:12:00`;
  `git diff -- _bestrec_run/hstu_tables.json` was empty before the strict run
  and remains empty after it.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Canonical sources/artifacts inspected:
  `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, `CANONICAL_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/sections/*.tex`,
  `paper_tex/tables/office_confirmation.tex`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/hygiene_scan_output.txt`, `paper_tex/references.bib`,
  `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
  `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`,
  `RELEASE_MANIFEST.json`, `DOI_DEPOSIT_INSTRUCTIONS.md`, and
  `_release/bestrec_deposit_v1.0.zip`.

### Verdict

**No new source-level repair occurred since the provided cutoff; the empirical
gate remains green, but the paper is still rejectable on consistency and
deposit readiness.** The only post-cutoff non-audit artifact was the generated
`hstu_tables.json`, and it has no git diff. Fresh strict rebuild, Office V3
adjudication, and FIR-breadth adjudication all pass. The live blocker remains
the contradiction between counted Office V3 prose and the older Appendix A.0 /
generated Office V1 table wording that still says the confirmed per-category
claim is Musical_Instruments only and Office is not counted.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release manifest verification OK for `113` files.
  - PASS: MI V2 gate; legacy Office V1 descriptive/VOID check remains OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 23:12 Australia/Sydney`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds
    above both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds
    above both references.
  - Comparability conditions OK: dataset identity, reference artifact hashes,
    treestate sidecars, code hashes, and data SHA256s.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS/CONFIRMED for Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - PASS/CONFIRMED for CDs_and_Vinyl: mean `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, `5/5` positive.
- PDF extraction with project-managed `uv` Python / `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; stale "Office is not counted" and
    "confirmed per-category claim remains" on page 41; `SILLM4Rec` on page 19;
    `Office_Products V3` on page 22.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; stale Office wording on page 36;
    `SILLM4Rec` on page 18; `Office_Products V3` on page 20.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; stale Office wording on
    page 37; `SILLM4Rec` on page 18; `Office_Products V3` on page 20.
- `_release/bestrec_deposit_v1.0.zip` check
  - Timestamp `2026-07-11T22:11:05`, length `780381`, SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`,
    `48` entries.
  - Contains `0` matches for `OFFICE_V3`, `PREREG_OFFICE_V3`, `FIR_BREADTH`,
    `PREREG_FIR_BREADTH`, `PAPER_TORS`, `DOI_DEPOSIT_INSTRUCTIONS`,
    `results_OFFICEV3`, and `results_FIRB`.
- Source searches
  - `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`,
    `paper_tex/sections/appendix-a0.tex`,
    `paper_tex/tables/office_confirmation.tex`, and
    `_bestrec_run/build_hstu_tables.py` still contain the stale
    Musical_Instruments-only / Office-not-counted boundary.
  - `paper_tex/references.bib` still has no `SILLM4Rec`,
    `10.1145/3743093.3771011`, or `MKC-Lab` entry.
  - `paper_tex/hygiene_scan_output.txt` still reports `PAPER_TORS.pdf`,
    40 pages, `0` placeholder/forbidden failures, and `20` informational
    SOTA/negated-claim review hits.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR arXiv v3 continues to support the comparator constants used here:
  HSTU-BLaIR NDCG@10 is `0.0760` for Video Games, `0.0271` for Office Products,
  and `0.0406` for Musical Instruments; the paper states chronological
  leave-one-out evaluation. Source: https://arxiv.org/html/2504.10545v3
- Amazon Reviews 2023's official site confirms the dataset is a 2023 McAuley
  Lab release with reviews, item metadata, links, 571.54M reviews, interactions
  through September 2023, and standard splitting. Source:
  https://amazon-reviews-2023.github.io/
- SID-MLP is close novelty pressure, not a clean comparator. Its arXiv paper
  evaluates Musical Instruments, Industrial & Scientific, and Video Games from
  Amazon Reviews 2023 and reports the same 5-core-style statistics for MI
  (`57,439` users / `24,587` items / `511,836` interactions) and Games
  (`94,762` / `25,612` / `814,586`) in Appendix C.1. Source:
  https://arxiv.org/html/2605.12617
- Latte is also close novelty pressure. Its arXiv table reports Amazon Reviews
  2023 Instruments/Scientific/Game leave-one-out results, including Latte
  NDCG@10 `0.0331` for Instruments and `0.0515` for Game, matching the
  manuscript's cautionary related-work paragraph. Source:
  https://arxiv.org/html/2605.06331
- ChronoSID/ReSID remain a distinct-protocol boundary: ChronoSID reports MI
  `57,359` users / `23,742` items / `490,522` interactions and VG `94,515` /
  `24,685` / `772,218`, which differ from the HSTU-BLaIR-family statistics.
  Source: https://arxiv.org/html/2607.03918v1
- SILLM4Rec remains under-cited. ACM metadata identifies a 2025 MMAsia paper
  using three Amazon Reviews 2023 5-core subdatasets and NDCG metrics, while
  the public repository describes 5-core AR2023 inputs followed by image
  descriptions, user preference summaries, candidate product ranking tasks, and
  SFT/DPO training. That supports non-interchangeability with full-catalog
  LLOO, but the manuscript still needs a formal citation or a direct full-paper
  inspection record. Sources: https://dl.acm.org/doi/10.1145/3743093.3771011
  and https://github.com/MKC-Lab/SILLM4Rec

### Confirmed Problems

1. **Appendix A.0 remains internally false after Office V3.** The V1 campaign
   can remain VOID, but the broad "Office is not counted" sentence contradicts
   the counted V3 campaign.
2. **The generated Office V1 table and template will reintroduce the same
   contradiction.** `paper_tex/tables/office_confirmation.tex` and
   `_bestrec_run/build_hstu_tables.py` still say the confirmed per-category
   claim remains Musical_Instruments only.
3. **The deposit bundle is stale relative to current claims.** The local zip and
   `DOI_DEPOSIT_INSTRUCTIONS.md` still describe the older deposit and omit
   Office V3, FIR-breadth, and TORS artifacts needed for the current paper.
4. **Build-note/page-count documentation is not reliable.** The acmsmall preview
   is 41 pages by fresh extraction, while `paper_tex/BUILD_NOTES.md` still
   describes the production preview as 40 pages/current builds 40/40 and embeds
   older 35/36-page hygiene text.
5. **SILLM4Rec remains a citation-readiness defect.** The paper names it, and
   accessible evidence supports a non-interchangeable protocol, but a top
   reviewer can object to an uncited exclusion of a 2025 AR2023/NDCG work.

### Confirmed Non-Problems

- No numerical mismatch, untraceable empirical cell, or strict-gate failure was
  found.
- Office V3 aggregate evidence remains mechanically green under its frozen
  point-estimate wording.
- FIR-breadth remains mechanically confirmed under the frozen internal
  filter-vs-no-filter rule.
- No post-cutoff manuscript source change was found; the only newer generated
  artifact has an empty git diff after the strict rebuild.
- The HSTU-BLaIR comparator constants and the SID/ChronoSID protocol-boundary
  wording remain externally supported by the checked sources.

### Concrete Fixes To Make Next

1. Rewrite the Appendix A.0 Office sentence in `PAPER_SUBMISSION.md`,
   `PAPER_DRAFT.md`, and `paper_tex/sections/appendix-a0.tex`: "The V1 campaign
   is not counted; the separate V3 campaign passed and is counted only under
   frozen per-category point-estimate wording."
2. Update `_bestrec_run/build_hstu_tables.py` and regenerate
   `paper_tex/tables/office_confirmation.tex` so the V1 table cannot reintroduce
   the Musical_Instruments-only boundary.
3. Rebuild all live PDFs and verify the stale strings are absent from
   `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`, and
   `paper_tex/PAPER_TORS_acmsmall.pdf`.
4. Regenerate or supersede `_release/bestrec_deposit_v1.0.zip`; update
   `DOI_DEPOSIT_INSTRUCTIONS.md` and/or `RELEASE_MANIFEST.json` so Office V3,
   FIR-breadth, and current TORS evidence are explicitly covered.
5. Add a formal SILLM4Rec citation with DOI `10.1145/3743093.3771011` and cite
   the inspected exclusion basis, or record that the ACM full paper was
   inaccessible and cite the public repository workflow as the exclusion basis.
6. Refresh `paper_tex/BUILD_NOTES.md` so current page counts and hygiene state
   match the live PDFs, with historical round-8 counts clearly separated or
   removed.

### Open Questions

- Should the stale `bestrec_deposit_v1.0.zip` be replaced in place, or should a
  new `v1.0.1`/current-deposit bundle supersede it?
- Should `RELEASE_MANIFEST.json` explicitly name Office V3 and FIR-breadth
  result families, or is `_bestrec_run/hstu_results_manifest.json` intended as
  the live evidence layer for generated empirical cells?
- Can the authors access and archive the SILLM4Rec ACM full text before
  submission freeze?
- Is `PAPER_TORS_acmsmall.pdf` a deliverable whose 41-page count must be fixed,
  or only an untracked local preview?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, table, bibliography, prereg,
      result, release, and audit artifacts.
- [x] Check files changed since the user-provided previous cutoff.
- [x] Re-run the strict rebuild.
- [x] Re-run Office V3 and FIR-breadth adjudicators.
- [x] Extract live PDF page counts and stale Office/SILLM4Rec occurrences.
- [x] Check deposit zip contents and DOI instructions.
- [x] Fact-check HSTU-BLaIR, AR2023, SID-MLP, Latte, ChronoSID, and SILLM4Rec
      boundaries against external sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair Appendix A.0 and generated Office V1 table wording.
- [ ] Rebuild PDFs and verify stale Office wording is gone.
- [ ] Refresh/supersede release/deposit bundle and DOI instructions.
- [ ] Add/inspect SILLM4Rec formal citation before freeze.

## Audit Run - 2026-07-14 21:10 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74`.
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  (`$CODEX_HOME` was unset in this shell, so the standard user-profile Codex
  home was used).
- Current run time: `2026-07-14 21:10:37 +10:00`.
- User-provided previous cutoff: `2026-07-14T10:09:11.006Z` (`2026-07-14
  20:09:11 +10:00`). Before this audit's own commands, the only files newer
  than that cutoff were `PAPER_REVIEW_AUDIT.md` and
  `_bestrec_run/hstu_tables.json`; `git diff -- _bestrec_run/hstu_tables.json`
  remains empty after the strict rebuild.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Canonical sources/artifacts inspected:
  `CANONICAL_SUBMISSION.md`, `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/sections/*.tex`,
  `paper_tex/tables/office_confirmation.tex`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/hygiene_scan_output.txt`, `paper_tex/references.bib`,
  `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
  `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`,
  `RELEASE_MANIFEST.json`, `DOI_DEPOSIT_INSTRUCTIONS.md`, and
  `_release/bestrec_deposit_v1.0.zip`.

### Verdict

**The numerical/provenance spine remains green, but the paper is still
rejectable on internal consistency and release packaging.** The strict rebuild,
Office V3 adjudicator, FIR-breadth adjudicator, and TORS hygiene scan all pass.
The live hard problem is that Appendix A.0 and the generated Office V1 table
still say Office is not counted, while the abstract, Section 5.2, Section 6.4,
and Section 6.5 count the separate Office V3 pre-registration as the second
pre-registered per-category comparison.

This run also updates two prior audit lines. First, the Office V3 sidecar
mechanics are now documented in `PREREG_OFFICE_V3.md` Erratum E2 and
`OFFICE_V3_RESULTS.md`; that is no longer the live blocker. Second, Section 8
now gives a coherent tracked-artifact boundary for printed claims versus
local-only per-user sidecars. The public deposit bundle, however, still predates
Office V3 and FIR-breadth.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release manifest verification OK for `113` files.
  - PASS: MI V2 gate; legacy Office V1 remains descriptive/VOID.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 21:11 Australia/Sydney`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds above
    both references.
  - Comparability conditions OK: dataset identity, reference artifacts, tree
    provenance, embedded code hashes, and data SHA256s.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS/CONFIRMED for Industrial_and_Scientific: mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, `5/5` positive.
  - PASS/CONFIRMED for CDs_and_Vinyl: mean `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, `5/5` positive.
- PDF extraction with `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; stale "Office is not counted" and
    "confirmed per-category claim remains" on page 41; `SILLM4Rec` on page 19;
    `Office_Products V3` on page 22.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; stale Office wording on page 36;
    `SILLM4Rec` on page 18; `Office_Products V3` on page 20.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; stale Office wording on
    page 37; `SILLM4Rec` on page 18; `Office_Products V3` on page 20.
- `paper_tex/hygiene_scan_output.txt`
  - PASS: `PAPER_TORS.pdf`, 40 pages, `0` placeholder/forbidden failures,
    `20` informational SOTA/negated-claim review hits.
- `_release/bestrec_deposit_v1.0.zip` check
  - Timestamp `2026-07-11T22:11:05`, length `780381`, SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`,
    `48` entries.
  - Contains `PAPER_SUBMISSION.pdf` and `RELEASE_MANIFEST.json`.
  - Contains `0` Office V3 matches, `0` FIR-breadth matches, `0` `PAPER_TORS`
    matches, and no `DOI_DEPOSIT_INSTRUCTIONS.md`.
- Source searches
  - `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`,
    `paper_tex/sections/appendix-a0.tex`,
    `paper_tex/tables/office_confirmation.tex`, and
    `_bestrec_run/build_hstu_tables.py` still contain stale Office-count wording.
  - `paper_tex/references.bib` still has no `SILLM4Rec`,
    `10.1145/3743093.3771011`, or `MKC-Lab` entry.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR arXiv v3 confirms the comparator-family dataset statistics and
  key NDCG constants used by this paper: Video_Games `25,612` items /
  `94,762` users / `814,585` interactions with HSTU-BLaIR NDCG@10 `0.0760`;
  Office_Products `77,551` / `223,308` / `1,800,877` with NDCG@10 `0.0271`;
  Musical_Instruments `24,587` / `57,439` / `511,835` with NDCG@10 `0.0406`.
  Source: https://arxiv.org/html/2504.10545v3
- The official Amazon Reviews 2023 site confirms the dataset is a 2023 McAuley
  Lab release with reviews, item metadata, links, larger/newer interactions,
  richer metadata, and standard splitting. Source:
  https://amazon-reviews-2023.github.io/
- SILLM4Rec remains close enough that it needs formal handling. ACM metadata
  identifies the paper as an MMAsia 2025 work and search/open snippets say it
  uses three AR2023 5-core subdatasets and reports NDCG; the public repo,
  however, instructs users to generate image descriptions, user preference
  summaries, candidate product ranking tasks, and SFT/DPO training data. That
  supports non-interchangeability with full-catalog LLOO, but not an uncited
  dismissal. Sources: https://dl.acm.org/doi/full/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec
- ChronoSID's arXiv HTML supports the manuscript's SID-line boundary: it uses
  AR2023 subsets but reports a processed universe distinct from the
  HSTU-BLaIR-family statistics, and its table reports ChronoSID/ReSID numbers
  under that separate protocol. Source: https://arxiv.org/html/2607.03918v1

### Confirmed Problems

1. **Appendix A.0 is still contradictory.** The V1 appendix can and should say
   the V1 campaign is VOID and not counted, but the broad sentence "Office is
   not counted" is false after Office V3 passed and is counted under frozen
   wording.
2. **The generated Office V1 table repeats the stale claim boundary.**
   `paper_tex/tables/office_confirmation.tex` says the confirmed per-category
   claim remains Musical_Instruments only; the template in
   `_bestrec_run/build_hstu_tables.py` needs the same V1/V3 split or the next
   table regeneration will reintroduce the contradiction.
3. **The deposit bundle is stale.** The advertised DOI-ready zip omits Office
   V3, FIR-breadth, and TORS artifacts now needed to support the current claim
   set and venue target. `DOI_DEPOSIT_INSTRUCTIONS.md` still describes the old
   46-file bundle even though the actual zip has 48 entries.
4. **Build notes are still not a trustworthy current-state document.**
   `paper_tex/BUILD_NOTES.md` says current builds are 40/40, but the current
   `PAPER_TORS_acmsmall.pdf` is 41 pages. It also carries historical 35/36-page
   details that are easy to misread as current.
5. **SILLM4Rec is named but uncited.** The current repo-evidence exclusion is
   plausible, but a top reviewer can reasonably object that an MMAsia 2025
   AR2023 5-core/NDCG work is mentioned without a bibliography entry or direct
   full-paper inspection record.

### Confirmed Non-Problems

- No new numerical mismatch, untraceable empirical cell, or strict-gate failure
  was found.
- Office V3 aggregate evidence is mechanically green, and E2 now explains the
  three regular-sidecar-equals-final-sidecar cases.
- Section 8 now states the tracked-artifact boundary coherently: printed claims
  recompute from tracked artifacts; local-only per-user sidecars are
  supplementary, hash-pinned audit material.
- FIR-breadth remains mechanically confirmed under the frozen internal
  filter-vs-no-filter decision rule.
- The HSTU-BLaIR comparator constants used for MI, Office, and Video_Games are
  externally supported by the cited arXiv v3 paper.

### Concrete Fixes To Make Next

1. Rewrite the Appendix A.0 sentence in `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`,
   and `paper_tex/sections/appendix-a0.tex`: "The V1 campaign is not counted;
   the separate V3 campaign passed and is counted only under the frozen
   per-category point-estimate wording."
2. Update `_bestrec_run/build_hstu_tables.py` and regenerate
   `paper_tex/tables/office_confirmation.tex` so the generated Office V1 table
   cannot reintroduce "Musical_Instruments only" wording.
3. Rebuild `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`, and
   `paper_tex/PAPER_TORS_acmsmall.pdf`; rerun the hygiene scan and explicitly
   verify `Office is not counted` is absent from live PDFs.
4. Regenerate or supersede `_release/bestrec_deposit_v1.0.zip` and update
   `DOI_DEPOSIT_INSTRUCTIONS.md` so the deposit story includes current Office
   V3/FIR-breadth prereg/results docs, relevant result JSONs/manifests, and the
   current TORS artifact, or clearly declares a new release/deposit name.
5. Add a formal SILLM4Rec citation with DOI `10.1145/3743093.3771011` and cite
   the inspected exclusion basis, or record that the ACM full paper was
   inaccessible and cite the public repo workflow as the basis for exclusion.
6. Refresh `paper_tex/BUILD_NOTES.md` current-state page counts and separate
   historical round-8 notes from current build status.

### Open Questions

- Should the stale `bestrec_deposit_v1.0.zip` be replaced in place, or should a
  new `v1.0.1`/current-deposit bundle supersede it?
- Should `RELEASE_MANIFEST.json` explicitly name Office V3 and FIR-breadth
  result families, or is `_bestrec_run/hstu_results_manifest.json` the intended
  live evidence layer for generated empirical cells?
- Can the authors access the SILLM4Rec ACM full text before submission freeze?
- Is `PAPER_TORS_acmsmall.pdf` intended to be part of the current deliverable,
  or only a local preview whose page count should not appear in release notes?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, PDF, TeX, tables, preregistration, result,
      release, and audit artifacts.
- [x] Check files changed since the previous automation cutoff.
- [x] Re-run the strict rebuild.
- [x] Re-run Office V3 and FIR-breadth adjudicators.
- [x] Extract live PDF page counts and stale Office/SILLM4Rec occurrences.
- [x] Check deposit zip contents and DOI instructions.
- [x] Fact-check HSTU-BLaIR, AR2023, SILLM4Rec, and ChronoSID boundaries against
      external sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair Appendix A.0 and generated Office V1 table wording.
- [ ] Rebuild PDFs and verify stale Office wording is gone.
- [ ] Refresh/supersede release/deposit bundle and DOI instructions.
- [ ] Add/inspect SILLM4Rec formal citation before freeze.

## Audit Run - 2026-07-14 20:10 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  (`$CODEX_HOME` was unset in this shell, so the standard user-profile Codex
  home was used).
- Current run time: `2026-07-14 20:10:13 +10:00`.
- User-provided previous cutoff: `2026-07-14T09:07:09.905Z` (`2026-07-14
  19:07:09 +10:00`). Before this audit's own commands, no files in the
  workspace had modification times newer than that cutoff.
- The strict rebuild rewrote `_bestrec_run/hstu_tables.json` at `20:11:31`, but
  `git diff -- _bestrec_run/hstu_tables.json` is empty.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- This audit edited only `PAPER_REVIEW_AUDIT.md` and the automation memory.

### Verdict

**No new manuscript/result change was found since the user-provided previous
run, and the empirical gate remains green. The paper is still rejectable on
consistency and packaging.** The live blocker is not the aggregate evidence:
Office V3, FIR-breadth, and the 168-cell strict artifact graph all pass. The
live blocker is that the rendered manuscript still contains the old Appendix
A.0 statement that Office is not counted, while the abstract and Section 5.2
count Office V3. The deposit bundle also remains stale and omits the newer
claim evidence.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 20:11:08`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`; 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`; 5/5 seeds above
    both references.
  - Comparability conditions OK; frozen wording remains a per-category
    point-estimate comparison only, not paired/distributional superiority and
    not SOTA.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 20:11:08`, block `9a38ad66bd75`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS.
  - HSTU core-block parity exact.
  - `168` empirical cells recomputed; `0` paper mismatches; `0` untraceable;
    all `14` declared claim families sourced.
  - Release manifest verification OK for its declared `113` files.
  - MI V2 gate OK; legacy Office V1 descriptive/VOID adjudication OK.
- PDF extraction with `pypdf`
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; `Office is not counted` and
    `confirmed per-category claim remains` on page 36; `SILLM4Rec` on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; stale Office phrases on
    page 37; `SILLM4Rec` on page 18.
  - `PAPER_SUBMISSION.pdf`: 45 pages; stale Office phrases on page 41;
    `SILLM4Rec` on page 19.
  - No `outcome pending` phrase was found in the rendered PDFs.
- Release/deposit zip check
  - `_release/bestrec_deposit_v1.0.zip`: timestamp `2026-07-11 22:11:05`,
    `780381` bytes, SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`,
    `48` entries.
  - `0` entries for `OFFICE_V3_RESULTS.md`, `PREREG_OFFICE_V3.md`,
    `FIR_BREADTH_RESULTS.md`, `PREREG_FIR_BREADTH.md`,
    `paper_tex/PAPER_TORS.pdf`, `results_OFFICEV3`, or `results_FIRB`.
  - `RELEASE_MANIFEST.json` result families remain `MI_gate_EXEC2`,
    `MI_gate_EXEC2_rest`, `MI_rebuild`, `OFFICE_gate`,
    `OFFICE_idonly_floor`, and `FIR_ablations`; this is internally verified
    but not aligned with the current Office V3/FIR-breadth deposit needs.
- Targeted source search
  - `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
    `paper_tex/sections/appendix-a0.tex` still contain "The confirmed
    per-category claim remains Musical_Instruments only; Office is not
    counted."
  - `PAPER_DRAFT.md` still has a stale opening status line saying Office stays
    VOID and the V3 outcome is pending.
  - `paper_tex/references.bib` still has no SILLM4Rec entry, and
    `VENUE_PLAN.md` still marks SILLM4Rec full-paper inspection pending.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's public paper/repository still supports the comparator framing:
  it evaluates AR2023 Video Games, Office Products, and Musical Instruments
  under a 5-core setup, gives the same category statistics used by this paper,
  and reports the relevant HSTU-BLaIR NDCG@10 point estimates
  (`0.0760`, `0.0271`, `0.0406`). Sources:
  https://arxiv.org/html/2504.10545v3 and https://github.com/snapfinger/HSTU-BLaIR
- The official Amazon Reviews 2023 site supports the dataset framing and scale:
  McAuley Lab's 2023 release has reviews, metadata, links, standard splits,
  `571.54M` reviews, `54.51M` users, `48.19M` items, and interactions through
  September 2023. Source: https://amazon-reviews-2023.github.io/
- SILLM4Rec remains close enough to require formal citation or inspection. ACM
  metadata says it reports experiments on three 5-core Amazon Reviews 2023
  datasets, while the public repository describes image-description generation,
  user preference summaries, candidate product ranking tasks, and SFT/DPO data
  generation. That supports non-interchangeability with full-catalog LLOO, but
  the manuscript should cite the ACM DOI/repo or inspect the full PDF directly.
  Sources: https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec
- ChronoSID/ReSID remain protocol-pressure related work rather than a direct
  comparator. ChronoSID's accessible paper reports output-level MI NDCG@10
  `0.0345` versus ReSID `0.0325` under its own semantic-ID setup, reinforcing
  that the manuscript's "no comparative claim against concurrent arXiv-only
  work" fence must remain. Source: https://arxiv.org/html/2607.03918v1

### Confirmed Problems

1. **Appendix A.0 still contradicts the counted Office V3 claim.** The appendix
   sentence should distinguish the original Office V1 VOID from the separate
   Office V3 pass; the current wording makes the rendered paper internally
   inconsistent.
2. **The deposit/release package is stale.** The zip omits Office V3,
   FIR-breadth, current TORS PDF, and corresponding prereg/results evidence.
3. **The build/readiness notes remain inconsistent with rendered artifacts.**
   `paper_tex/PAPER_TORS_acmsmall.pdf` is 41 pages; `paper_tex/BUILD_NOTES.md`
   still says the current builds are 40/40 and retains old 35/36-page notes.
4. **SILLM4Rec is still not submission-ready in the bibliography.** It is
   discussed in the manuscript, but not formally cited in `references.bib`.
5. **No current numerical blocker was found.** This is a confirmed non-problem:
   Office V3, FIR-breadth, and the strict artifact graph all passed on fresh
   commands this run.

### Concrete Fixes To Make Next

1. Replace the Appendix A.0 sentence with a two-track statement: Office V1
   remains VOID under the original floor-check preregistration; Office V3 passed
   under the separate environment-matched preregistration and counts only as a
   per-category point-estimate comparison.
2. Rebuild/update the release/deposit bundle so it includes `PREREG_OFFICE_V3.md`,
   `OFFICE_V3_RESULTS.md`, Office V3 result evidence, `PREREG_FIR_BREADTH.md`,
   `FIR_BREADTH_RESULTS.md`, FIR-breadth result evidence, and the current TORS
   artifact, or explicitly document why the deposit boundary excludes them.
3. Refresh `paper_tex/BUILD_NOTES.md`: remove old 35/36 page-count blocks,
   correct the acmsmall page count, and replace stale hygiene/readiness notes
   with the current 40-page TORS hygiene PASS.
4. Add a SILLM4Rec bibliography entry and cite the exact exclusion basis, or
   inspect/archive the ACM PDF before freeze.
5. Decide whether `PAPER_DRAFT.md` is still live. If it is, update its status
   line and Appendix A.0 text; if it is archival, mark it clearly as stale.

### Open Questions

- Are Office V3 and FIR-breadth artifacts intended to be in the public DOI
  bundle now that their claims are counted?
- Should `RELEASE_MANIFEST.json` list Office V3/FIR-breadth result families
  directly, or is `_bestrec_run/hstu_results_manifest.json` the intended
  claim-source boundary?
- Is `PAPER_SUBMISSION.pdf` still a live deliverable despite being 45 pages,
  while the TORS review artifact is 40 pages?
- Can the authors access the SILLM4Rec full ACM PDF, or should the paper cite
  only the DOI/repository-backed protocol evidence?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Check files changed since the user-provided previous cutoff.
- [x] Search manuscript and TeX for stale Office V3 no-claim wording.
- [x] Re-run Office V3 adjudicator dynamically.
- [x] Re-run FIR-breadth adjudicator dynamically.
- [x] Re-run strict manuscript/artifact gate.
- [x] Check compiled PDF page counts and stale-phrase locations.
- [x] Check deposit zip contents and release-manifest family boundary.
- [x] Fact-check current comparator/dataset/related-work claims against
      HSTU-BLaIR, AR2023, SILLM4Rec, and ChronoSID sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair Appendix A.0 Office V1/V3 wording.
- [ ] Refresh stale release/deposit bundle and manifest boundary.
- [ ] Refresh stale `paper_tex/BUILD_NOTES.md`.
- [ ] Add/verify SILLM4Rec citation or inspect the full ACM paper.

## Audit Run - 2026-07-14 17:08 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  (`$CODEX_HOME` was unset in this shell, so the standard user-profile Codex
  home was used).
- Current run time: `2026-07-14 17:08:30 +10:00`.
- Files with modification times after the previous automation cutoff
  (`2026-07-14T06:04:06.591Z`): `PAPER_REVIEW_AUDIT.md` and
  `_bestrec_run/hstu_tables.json`. The strict rebuild rewrote
  `_bestrec_run/hstu_tables.json` at `17:07:32`, but `git diff --
  _bestrec_run/hstu_tables.json` is empty.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- This audit edited only `PAPER_REVIEW_AUDIT.md` and the automation memory.

### Verdict

**No new empirical/provenance failure was found, but the submission remains
rejectable on consistency and packaging.** The Office V3 adjudicator, the
FIR-breadth adjudicator, and the full strict artifact rebuild are all green.
The paper still fails the top-journal readiness bar because the live appendix
and all rendered PDFs still say Office is not counted, while the abstract and
Section 5.2 count Office V3 under the redesigned pre-registration. The DOI
deposit zip also remains stale relative to the current claim set.

This run found no manuscript/source/result repair since the prior run. The only
non-audit file timestamp change was the expected strict-build rewrite of
`_bestrec_run/hstu_tables.json`, with no content diff.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 17:07:27`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`; 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`; 5/5 seeds above
    both references.
  - Comparability conditions OK; frozen wording remains a per-category
    point-estimate comparison only, with no paired/distributional superiority
    and no SOTA claim.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 17:07:27`, block `9a38ad66bd75`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS.
  - HSTU core-block parity exact.
  - `168` empirical cells recomputed; `0` paper mismatches; `0` untraceable;
    all `14` declared claim families sourced.
  - Release manifest verification OK for its declared `113` files.
  - MI V2 gate OK; legacy Office V1 descriptive/VOID adjudication OK.
- PDF extraction with `pypdf`
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; `Office is not counted` and
    `confirmed per-category claim remains` on page 36; `SILLM4Rec` on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; stale Office phrases on
    page 37; `SILLM4Rec` on page 18.
  - `PAPER_SUBMISSION.pdf`: 45 pages; stale Office phrases on page 41;
    `SILLM4Rec` on page 19.
  - No `outcome pending` phrase was found in the rendered PDFs.
- Release/deposit zip check
  - `_release/bestrec_deposit_v1.0.zip`: timestamp `2026-07-11 22:11:05`,
    `780381` bytes, SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`,
    `48` entries.
  - `0` entries for `OFFICE_V3_RESULTS.md`, `PREREG_OFFICE_V3.md`,
    `FIR_BREADTH_RESULTS.md`, `PREREG_FIR_BREADTH.md`,
    `paper_tex/PAPER_TORS.pdf`, `results_OFFICEV3`, or `results_FIRB`.
  - `RELEASE_MANIFEST.json` result families remain `FIR_ablations`,
    `MI_gate_EXEC2`, `MI_gate_EXEC2_rest`, `MI_rebuild`, `OFFICE_gate`, and
    `OFFICE_idonly_floor`; `_bestrec_run/hstu_results_manifest.json` does
    contain Office V3 and FIR-breadth evidence strings.
- Targeted source search
  - `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
    `paper_tex/sections/appendix-a0.tex` still contain "The confirmed
    per-category claim remains Musical_Instruments only; Office is not
    counted."
  - `PAPER_DRAFT.md` still has a stale opening status line saying Office stays
    VOID and the V3 outcome is pending.
  - `paper_tex/references.bib` still has no SILLM4Rec entry, and
    `VENUE_PLAN.md` still marks SILLM4Rec full-paper inspection pending.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's public repository still supports the comparator constants used
  by this paper: AR2023 Video Games HSTU-BLaIR NDCG@10 `0.0760`, Office
  Products `0.0271`, and Musical Instruments `0.0406`; it also states the
  implementation was tested on Ubuntu 22.04 / Python 3.9 / CUDA 12.6 / RTX
  4090. Source: https://github.com/snapfinger/HSTU-BLaIR
- The official Amazon Reviews 2023 site supports the dataset framing: McAuley
  Lab's 2023 release includes reviews, metadata, links, standard splits, and
  headline scale `571.54M` reviews, `54.51M` users, `48.19M` items, with
  interactions through September 2023. Source:
  https://amazon-reviews-2023.github.io/
- SILLM4Rec remains close enough to require formal handling. Its public
  repository asks users to download Amazon Reviews 2023 5-core files, generate
  image descriptions, user preference summaries, candidate product ranking
  tasks, and SFT/DPO training data. This supports the manuscript's
  non-interchangeability rationale, but the paper still needs a formal citation
  or direct ACM full-paper protocol inspection. Sources:
  https://github.com/MKC-Lab/SILLM4Rec and
  https://dl.acm.org/doi/10.1145/3743093.3771011
- The current concurrent-work fence remains necessary: accessible evidence
  supports treating semantic-ID/generative-retrieval papers as related but not
  directly claimed-against unless their training/protocol details are audited.

### Confirmed Problems

1. **Appendix A.0 still contradicts the counted Office V3 claim.** The appendix
   sentence is too broad for the current paper: it should say the V1 campaign is
   not counted, while the separate V3 campaign passed only under its frozen
   point-estimate wording.
2. **The deposit/release package is stale.** The advertised zip and release
   manifest boundary do not include the Office V3/FIR-breadth prereg/results
   evidence that the current manuscript and strict gate rely on.
3. **The production notes/rendered package are inconsistent.** The acmsmall PDF
   is 41 pages while `paper_tex/BUILD_NOTES.md` still describes 40/40 current
   builds and retains older 35/36-page historical blocks.
4. **SILLM4Rec remains under-cited.** The exclusion rationale is plausible, but
   a named adjacent MMAsia 2025 paper should not be left uncited and
   inspection-pending in a top-journal submission.

### Plausible Risks / Author Verification Needed

- Confirm whether `_release/bestrec_deposit_v1.0.zip` should be regenerated in
  place, superseded by a new `v1.0.1`/current bundle, or explicitly marked
  historical.
- Confirm whether `PAPER_DRAFT.md` is live. If it is not live, remove it from
  the submission/release boundary; if it is live, fix its stale Office status.
- Confirm whether reviewers will get local-only Office/FIR per-user sidecars
  upon request only, or whether those sidecars should be deposited before
  review.
- Confirm whether the SILLM4Rec ACM full text is accessible before freeze.

### Concrete Fixes To Make Next

1. Rewrite the broad Appendix A.0 sentence in `PAPER_SUBMISSION.md`,
   `PAPER_DRAFT.md`, and `paper_tex/sections/appendix-a0.tex`: V1 remains VOID
   and non-counted; V3 is separate, passed, and counted only as the frozen
   point-estimate comparison in Section 5.2.
2. Re-render `paper_tex/PAPER_TORS.pdf`, `paper_tex/PAPER_TORS_acmsmall.pdf`,
   and `PAPER_SUBMISSION.pdf`, then rerun PDF hygiene/extraction.
3. Rebuild or supersede the DOI/deposit package so it includes current PDFs,
   Office V3 and FIR-breadth prereg/results docs, and either the relevant result
   JSONs or a manifest that enumerates their hashes.
4. Refresh `paper_tex/BUILD_NOTES.md` to match the current 40/41/45-page state
   and remove or clearly historical-label stale old scan blocks.
5. Add a SILLM4Rec bibliography entry and cite the ACM DOI/repo evidence, or
   remove the named mention until direct protocol inspection is done.

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Check files modified since the previous hourly run.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Re-run strict manuscript/artifact gate.
- [x] Extract current PDF page counts and stale Office/SILLM4Rec occurrences.
- [x] Recheck release/deposit zip contents and manifest result-family boundary.
- [x] Fact-check current comparator/dataset/SILLM4Rec boundaries against public
      sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Fix Appendix A.0 Office V1/V3 status.
- [ ] Refresh release/deposit bundle and manifest boundary.
- [ ] Refresh `paper_tex/BUILD_NOTES.md`.
- [ ] Add/inspect SILLM4Rec citation or remove the named exclusion.

## Audit Run - 2026-07-14 16:07 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`.
- Current run time: `2026-07-14 16:07:15 +10:00`.
- Files with modification times after the previous automation cutoff
  (`2026-07-14T05:02:05.396Z`): `PAPER_REVIEW_AUDIT.md` and
  `_bestrec_run/hstu_tables.json`. The latter was regenerated by the strict
  build with no content diff (`git diff -- _bestrec_run/hstu_tables.json`
  empty).
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- This audit edited only `PAPER_REVIEW_AUDIT.md` and the automation memory.

### Verdict

**No new hard empirical failure was found, but the paper is still not
submission-ready.** The Office V3, FIR-breadth, and strict artifact gates remain
green. The reject-level risks are still presentation and release integrity: live
sources and PDFs still say Office is not counted in Appendix A.0, while the
current abstract/results count Office V3; the declared DOI/deposit zip still
does not contain the Office V3 or FIR-breadth evidence needed for the current
claim set.

This hour adds one small delta from the prior run: `_bestrec_run/hstu_tables.json`
has a new filesystem timestamp because the strict build rewrote it, but its
tracked content is unchanged. There was no manuscript/PDF/release repair after
the previous audit.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 16:05:43`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`; 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`; 5/5 seeds above
    both references.
  - Frozen claim remains a per-category point-estimate comparison only; no
    paired/distributional superiority and no SOTA claim.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 16:05:48`, block `9a38ad66bd75`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS.
  - HSTU core-block parity exact.
  - `168` empirical cells recomputed; `0` paper mismatches; `0` untraceable;
    all `14` declared claim families sourced.
  - Release manifest verification OK for its declared `113` files.
  - MI V2 gate OK; legacy Office V1 descriptive/VOID adjudication OK.
- PDF extraction with project `pypdf`
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; `Office is not counted` and
    `confirmed per-category claim remains` on page 36; `SILLM4Rec` on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; stale Office phrases on
    page 37; `SILLM4Rec` on page 18.
  - `PAPER_SUBMISSION.pdf`: 45 pages; stale Office phrases on page 41;
    `SILLM4Rec` on page 19.
- Release/deposit zip check
  - `_release/bestrec_deposit_v1.0.zip`: SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`, `48`
    entries.
  - `0` entries for `OFFICE_V3_RESULTS.md`, `PREREG_OFFICE_V3.md`,
    `FIR_BREADTH_RESULTS.md`, `PREREG_FIR_BREADTH.md`,
    `paper_tex/PAPER_TORS.pdf`, `results_OFFICEV3`, or `results_FIRB`.
- Targeted source search
  - `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
    `paper_tex/sections/appendix-a0.tex` still contain "The confirmed
    per-category claim remains Musical_Instruments only; Office is not
    counted."
  - `paper_tex/BUILD_NOTES.md` still says the acmsmall preview is 40 pages,
    while fresh extraction finds 41 pages.
  - `paper_tex/references.bib` still lacks a SILLM4Rec entry; `VENUE_PLAN.md`
    still marks full-paper inspection pending.
  - `RELEASE_MANIFEST.json` still has the old `result_families` boundary, while
    `_bestrec_run/hstu_results_manifest.json` does include `results_OFFICEV3_*`
    and `results_FIRB_*`.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's repository still supports the comparator constants used by this
  paper: Video Games HSTU-BLaIR NDCG@10 `0.0760`, Office Products `0.0271`,
  and Musical Instruments `0.0406`, and documents evaluation on Amazon Reviews
  2023 subsets plus Steam. Source: https://github.com/snapfinger/HSTU-BLaIR
- Amazon Reviews 2023 remains correctly framed as a McAuley Lab 2023 dataset
  with reviews, metadata, links, standard splits, 571.54M reviews, 54.51M users,
  48.19M items, and interactions through September 2023. Source:
  https://amazon-reviews-2023.github.io/
- SILLM4Rec remains a close adjacent work that cannot be left as an uncited
  aside. Its public repository requires Amazon Reviews 2023 5-core files and
  builds image-description, user-preference-summary, candidate-ranking, SFT, and
  DPO workflows; ACM metadata/search text describes reranking tasks. That
  supports non-interchangeability with full-catalog LLOO, but the manuscript
  still needs a formal citation or direct full-paper inspection. Sources:
  https://github.com/MKC-Lab/SILLM4Rec and
  https://dl.acm.org/doi/10.1145/3743093.3771011
- Concurrent semantic-ID work still pressures novelty. Latte proposes latent
  tokens for autoregressive semantic-ID generation and reports AR2023 MI/VG
  experiments; ChronoSID reports an adjacent SID-line universe and MI N@10
  values around `0.0345`/`0.0346` under its own protocol. These do not replace
  the HSTU-BLaIR-family comparator, but they make the manuscript's
  "no comparative claim against concurrent arXiv-only work" fence necessary.
  Sources: https://arxiv.org/pdf/2605.06331 and
  https://arxiv.org/html/2607.03918v1

### Confirmed Problems

1. **Appendix A.0 remains contradictory in both source and PDF.** It must split
   Office V1 VOID from Office V3 PASS; the current text still collapses them
   into "Office is not counted."
2. **The deposit/release boundary remains stale.** A reviewer following the DOI
   instructions will not receive the current Office V3 or FIR-breadth evidence.
3. **The production notes remain stale.** The current acmsmall PDF extracts as
   41 pages, not 40, and old round-8 page-count notes remain.
4. **SILLM4Rec is still not submission-ready.** The manuscript mentions it by
   name without a bibliography entry and with full-paper inspection still
   pending.

### Plausible Risks / Author Verification Needed

- Confirm whether Office V3 and FIR-breadth evidence should be added directly
  to `RELEASE_MANIFEST.json`, the DOI zip, or both.
- Confirm whether `PAPER_DRAFT.md` and `PAPER_SUBMISSION.pdf` are live
  deliverables. If either can circulate, they currently carry the same stale
  Office contradiction.
- Confirm whether SILLM4Rec full text is accessible before freeze. If not, cite
  the public repository/ACM DOI and make the exclusion explicitly evidence-based.

### Concrete Fixes To Make Next

1. Rewrite Appendix A.0 in `paper_tex/sections/appendix-a0.tex`,
   `PAPER_SUBMISSION.md`, and `PAPER_DRAFT.md`: Office V1 remains VOID; Office
   V3 separately passed and counts only under frozen point-estimate wording.
2. Rebuild all PDFs after that fix and rerun PDF hygiene/extraction.
3. Rebuild the DOI/deposit package and release manifest so Office V3,
   FIR-breadth, and the current TORS PDF are actually deposited.
4. Refresh `paper_tex/BUILD_NOTES.md` with the current 40/41/45-page state and
   remove or clearly historical-label stale round-8 notes.
5. Add a SILLM4Rec citation/full-paper inspection note, or remove the named
   mention until it is citable.

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Check files modified since the previous hourly run.
- [x] Rerun Office V3 adjudicator.
- [x] Rerun FIR-breadth adjudicator.
- [x] Rerun strict manuscript/artifact gate.
- [x] Extract current PDF page counts and stale Office/SILLM4Rec occurrences.
- [x] Recheck release/deposit zip contents and manifest result-family boundary.
- [x] Fact-check live comparator/dataset/SILLM4Rec/semantic-ID boundaries
      against public sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Fix Appendix A.0 Office V1/V3 status.
- [ ] Refresh release/deposit bundle and manifest boundary.
- [ ] Refresh `paper_tex/BUILD_NOTES.md`.
- [ ] Add/inspect SILLM4Rec citation or remove the named exclusion.

## Audit Run - 2026-07-14 15:04 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`.
- Current run time: `2026-07-14 15:04:31 +10:00`.
- Files changed since the previous audit cutoff (`2026-07-14 14:04
  Australia/Sydney`): only `PAPER_REVIEW_AUDIT.md`. No manuscript source,
  result JSON, PDF, release, bibliography, figure, or table source had a newer
  filesystem timestamp.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- This audit edited only `PAPER_REVIEW_AUDIT.md` and the automation memory.

### Verdict

**No new numerical or provenance failure was found, but the paper remains
unready for a top-journal submission.** Because no manuscript/result artifacts
changed since the prior run, the live rejection risks are unchanged and now
freshly re-confirmed: Appendix A.0 contradicts the Office V3 pass, and the
deposit/release bundle still omits the evidence for current Office V3 and
FIR-breadth claims.

The strict empirical apparatus is still green. That does not neutralize the
presentation risk: a reviewer reading the PDF sees Office V1/V3 status mixed in
one appendix paragraph, while a reviewer following the deposit instructions
cannot retrieve the current claim families from the declared zip.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 15:03:24`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`; 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`; 5/5 seeds above
    both references.
  - Frozen claim remains a per-category point-estimate comparison only; no
    paired/distributional superiority and no SOTA claim.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 15:03:29`, block `9a38ad66bd75`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS.
  - HSTU core-block parity exact.
  - `168` empirical cells recomputed; `0` paper mismatches; `0` untraceable;
    all `14` declared claim families sourced.
  - Release manifest verification OK for its declared `113` files.
  - MI V2 gate OK; legacy Office V1 descriptive/VOID adjudication OK.
- PDF extraction with `pypdf`
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; `Office is not counted` on page 36;
    `confirmed per-category claim remains` on page 36; `SILLM4Rec` on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; `Office is not counted` on
    page 37; `confirmed per-category claim remains` on page 37; `SILLM4Rec` on
    page 18.
  - `PAPER_SUBMISSION.pdf`: 45 pages; `Office is not counted` on page 41;
    `confirmed per-category claim remains` on page 41; `SILLM4Rec` on page 19.
- Release/deposit zip check
  - `_release/bestrec_deposit_v1.0.zip`: SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`, `48`
    entries.
  - `0` entries for `OFFICE_V3_RESULTS.md`, `PREREG_OFFICE_V3.md`,
    `FIR_BREADTH_RESULTS.md`, `PREREG_FIR_BREADTH.md`,
    `paper_tex/PAPER_TORS.pdf`, `results_OFFICEV3`, or `results_FIRB`.
- Targeted text search
  - `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
    `paper_tex/sections/appendix-a0.tex` still contain "The confirmed
    per-category claim remains Musical_Instruments only; Office is not
    counted."
  - `paper_tex/BUILD_NOTES.md` still mixes current 40/40 wording with old
    35/36-page round-8 notes.
  - `VENUE_PLAN.md` still marks SILLM4Rec full-paper inspection pending.
  - `paper_tex/references.bib` still lacks a SILLM4Rec entry.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's public repository still supports the comparator constants used
  by this paper: Video Games HSTU-BLaIR NDCG@10 `0.0760`, Office Products
  `0.0271`, and Musical Instruments `0.0406`; it also states experiments cover
  three Amazon Reviews 2023 subsets and Steam. Source:
  https://github.com/snapfinger/HSTU-BLaIR
- The official Amazon Reviews 2023 site and benchmark-script README support the
  paper's dataset framing: the dataset is a 2023 McAuley Lab release with
  reviews, metadata, links, standard splits, 5-core filtering, and leave-last-out
  benchmark files. Sources: https://amazon-reviews-2023.github.io/ and
  https://github.com/hyp1231/AmazonReviews2023/blob/main/benchmark_scripts/README.md
- SILLM4Rec remains a close adjacent work, not a safe uncited aside. Its public
  repo says it uses Amazon Reviews 2023 5-core files, image-to-text conversion,
  user preference summaries, candidate product ranking tasks, and SFT/DPO data;
  ACM metadata describes a multimodal recommendation paper using SFT and DPO.
  This supports non-interchangeability with full-catalog LLOO, but it also
  means the manuscript needs either a formal citation/full-paper inspection or a
  more cautious removal. Sources: https://github.com/MKC-Lab/SILLM4Rec and
  https://dl.acm.org/doi/10.1145/3743093.3771011
- Latte and ChronoSID remain novelty pressure but not audited comparator
  replacements. Latte reports AR2023 Instruments/Scientific/Games NDCG@10
  values including Instruments `0.0331` and Games `0.0515`; ChronoSID reports a
  distinct SID-line filtered universe, e.g. MI `57,359` users / `23,742` items /
  `490,522` interactions. Sources: https://arxiv.org/pdf/2605.06331 and
  https://arxiv.org/html/2607.03918v1

### Confirmed Problems

1. **Appendix A.0 is still contradictory.** It describes the original Office V1
   pre-registration VOID and then concludes that Office is not counted. That was
   correct for V1, but it is now false for the separate Office V3
   pre-registration counted in the abstract and Section 5.2.
2. **The deposit bundle is stale.** The declared `v1.0` zip lacks Office V3 and
   FIR-breadth prereg/results documentation and lacks the current TORS PDF,
   while the manuscript now depends on those claim families.
3. **Build/readiness notes are internally stale.** `BUILD_NOTES.md` still
   carries round-8 35/36-page statements, while current extracted PDFs are
   40/41/45 pages depending on artifact.
4. **SILLM4Rec is still not submission-ready.** It is mentioned in the
   manuscript without a bibliography entry, and the venue plan still marks
   direct full-paper inspection pending.

### Plausible Risks / Author Verification Needed

- Confirm whether Office V3 per-user sidecars are intended to be deposited,
  supplied on reviewer request, or declared out-of-scope with enough aggregate
  JSON evidence for reproducibility.
- Confirm whether `PAPER_DRAFT.md` remains a live draft. If it is live, it must
  be repaired in lockstep with `PAPER_SUBMISSION.md`; if not, mark it obsolete.
- Confirm whether `PAPER_SUBMISSION.pdf` is still a deliverable. Its 45-page
  length and stale Office sentence make it dangerous if circulated alongside the
  40-page TORS artifact.

### Concrete Fixes To Make Next

1. Rewrite Appendix A.0 so the final Office-status sentence explicitly says:
   Office V1 remains VOID and not counted; Office V3 is a separate redesigned
   pre-registration that passed and is counted only under its frozen
   point-estimate wording.
2. Rebuild and redeclare the deposit/release package to include Office V3,
   FIR-breadth, the current TORS PDF, and a manifest boundary that matches the
   paper's current claim families.
3. Refresh `paper_tex/BUILD_NOTES.md` to remove old round-8 35/36-page language
   and report the current 40-page TORS / 41-page acmsmall / 45-page reader-PDF
   state, or clearly mark historical counts as historical only.
4. Add a SILLM4Rec bibliography entry and direct inspected exclusion rationale,
   or remove the named mention until the ACM paper is inspected.
5. Re-render all live PDFs after the Appendix A.0 fix and rerun the hygiene scan
   plus strict rebuild before considering the manuscript frozen.

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Check files modified since the previous hourly run.
- [x] Rerun Office V3 adjudicator.
- [x] Rerun FIR-breadth adjudicator.
- [x] Rerun strict manuscript/artifact gate.
- [x] Extract current PDF page counts and stale Office/SILLM4Rec occurrences.
- [x] Recheck release/deposit zip contents and hash.
- [x] Fact-check live comparator/dataset/SILLM4Rec/Latte/ChronoSID boundaries
      against primary public sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Fix Appendix A.0 Office V1/V3 status.
- [ ] Refresh release/deposit bundle and manifest boundary.
- [ ] Refresh `paper_tex/BUILD_NOTES.md`.
- [ ] Add/inspect SILLM4Rec citation or remove the named exclusion.

## Audit Run - 2026-07-14 14:02 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`.
- Current run time: `2026-07-14 14:04:07 +10:00`; main adjudicators completed
  at `2026-07-14 14:02:05 Australia/Sydney`.
- Active sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `paper_tex/main.tex`,
  `paper_tex/sections/*.tex`, `paper_tex/references.bib`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/PAPER_TORS_acmsmall.pdf`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `CANONICAL_SUBMISSION.md`, `VENUE_PLAN.md`, `RELEASE_MANIFEST.json`,
  `_bestrec_run/hstu_results_manifest.json`, `_release/bestrec_deposit_v1.0.zip`,
  `DOI_DEPOSIT_INSTRUCTIONS.md`, `OFFICE_V3_RESULTS.md`,
  `FIR_BREADTH_RESULTS.md`, and `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- This audit edited only `PAPER_REVIEW_AUDIT.md` and the automation memory.

### Verdict

**No empirical gate failed, but the paper is still not submission-ready.** The
strict artifact graph, Office V3 adjudicator, FIR-breadth adjudicator, and TORS
hygiene scan are all green. The top rejection risk remains internal
contradiction: Appendix A.0 still says "Office is not counted" in live sources
and rendered PDFs, while the abstract and Section 5.2 count Office V3 as the
second pre-registered per-category point-estimate comparison.

The second live risk is archival: the tracked result JSONs and strict gate know
about Office V3 and FIR-breadth, but `RELEASE_MANIFEST.json` and the assembled
`v1.0` deposit zip still do not. A reviewer following the deposit instructions
would not receive the evidence for two current claim families.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS.
  - HSTU core-block parity exact.
  - `168` cells recomputed; `0` paper mismatches; `0` untraceable cells; all
    `14` declared claim families sourced.
  - Release manifest verification OK for its declared `113` files.
  - MI V2 gate OK; legacy Office V1 descriptive/VOID adjudication OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 14:02:05`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`; 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`; 5/5 seeds above
    both references.
  - Frozen claim remains per-category point-estimate only, not paired
    superiority and not SOTA.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 14:02:05`, block `9a38ad66bd75`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, 5/5 positive.
- PDF extraction with `pypdf`
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; `Office is not counted` on page 36;
    `SILLM4Rec` on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; `Office is not counted` on
    page 37; `confirmed per-category claim remains Musical_Instruments only`
    on page 37; `SILLM4Rec` on page 18.
  - `PAPER_SUBMISSION.pdf`: 45 pages; `Office is not counted` on page 41;
    `SILLM4Rec` on page 19.
- Text search
  - `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
    `paper_tex/sections/appendix-a0.tex` still contain the stale Appendix A.0
    sentence that the confirmed per-category claim remains Musical_Instruments
    only and Office is not counted.
  - `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` still claims those Office sites were
    fixed and that zero stale occurrences remain; the live sources and PDFs
    contradict that response.
  - `paper_tex/references.bib` has no SILLM4Rec entry, although Section 5.1
    discusses SILLM4Rec by name.
  - `paper_tex/BUILD_NOTES.md` still contains historical 35/36 page notes and
    current 40/40 wording, while the current PDFs are 40 pages for TORS and 41
    pages for acmsmall.
- Release/deposit check
  - `_release/bestrec_deposit_v1.0.zip`: 48 entries, 780,381 bytes, SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`.
  - Deposit zip contains `0` entries for `OFFICE_V3_RESULTS.md`,
    `PREREG_OFFICE_V3.md`, `FIR_BREADTH_RESULTS.md`, `PREREG_FIR_BREADTH.md`,
    `paper_tex/PAPER_TORS.pdf`, `results_OFFICEV3`, or `results_FIRB`.
  - `RELEASE_MANIFEST.json` contains none of `office_v3`, `fir_breadth`,
    `results_OFFICEV3`, `results_FIRB`, `OFFICE_V3_RESULTS.md`,
    `FIR_BREADTH_RESULTS.md`, `PREREG_OFFICE_V3.md`, or
    `PREREG_FIR_BREADTH.md`.
- TORS hygiene scan
  - `paper_tex/hygiene_scan_output.txt`: PASS, 40 pages, `0`
    placeholder/forbidden-claim failures, 20 informational SOTA/non-claim
    review hits.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's arXiv record confirms v3 was revised on 2025-06-19 and evaluates
  three Amazon Reviews 2023 subsets plus Steam; the public repository table
  reports the comparator constants used here: Video Games HSTU-BLaIR NDCG@10
  `0.0760`, Office Products `0.0271`, and Musical Instruments `0.0406`.
  Sources: https://arxiv.org/abs/2504.10545,
  https://github.com/snapfinger/HSTU-BLaIR
- The official Amazon Reviews 2023 site supports the dataset framing: McAuley
  Lab collected the 2023 dataset, it includes reviews, metadata, and links, and
  provides standard splitting/benchmarking materials. Source:
  https://amazon-reviews-2023.github.io/
- Latte (arXiv:2605.06331) reports AR2023 Instruments/Scientific/Games, LOO
  evaluation, and Table 3 values including Instruments `0.0331` and Games
  `0.0515`, matching the manuscript's cautious point-estimate summary. Source:
  https://arxiv.org/pdf/2605.06331
- ChronoSID (arXiv:2607.03918) reports same-test-instance comparisons against
  ReSID and frames temporal gap modeling as improving both popular and
  unpopular regimes, but this is still a SID-line setup rather than an audited
  apples-to-apples HSTU-BLaIR-family comparison. Source:
  https://arxiv.org/html/2607.03918v1
- SILLM4Rec remains close enough to require a formal citation or inspected
  exclusion. ACM metadata says its experiments use three 5-core Amazon Reviews
  2023 sub-datasets; the public repo describes image-description generation,
  user preference summaries, candidate product ranking tasks, and SFT/DPO
  training data. That supports non-interchangeability with full-catalog LLOO,
  but does not justify mentioning it without a bibliography entry. Sources:
  https://dl.acm.org/doi/10.1145/3743093.3771011,
  https://github.com/MKC-Lab/SILLM4Rec
- GrIT and Augment-or-Not are appropriately treated as adjacent rather than
  proven-comparable unless their preprocessing/evaluation details are audited.
  Sources: https://arxiv.org/pdf/2602.19728,
  https://arxiv.org/html/2505.23053v1

### Confirmed Problems

1. **Appendix A.0 contradicts the counted Office V3 claim.** The V1 appendix can
   say V1 is void, but it cannot generically say Office is not counted after
   V3 is counted in the main paper.
2. **The deposit/release boundary is stale.** The current deposit package omits
   Office V3 and FIR-breadth prereg/results docs and result families.
3. **`RELEASE_MANIFEST.json` is green only for an outdated declared scope.** The
   strict gate includes the new claim families, but the release manifest text
   does not name them.
4. **SILLM4Rec is under-cited.** The sentence is directionally defensible, but a
   top-journal reviewer will expect a citation and a precise protocol boundary.
5. **`paper_tex/BUILD_NOTES.md` is stale.** It mixes current 40-page state with
   old 35/36-page notes and claims a 40/40 current build despite acmsmall being
   41 pages.
6. **`PAPER_DRAFT.md` is stale relative to the canonical submission.** It still
   contains a status note saying Office V3 is pending. If the draft is not live,
   mark it as archival; otherwise update it.

### Confirmed Non-Problems

- No strict numerical/provenance gate failed.
- Office V3 aggregate evidence remains mechanically supported.
- FIR-breadth evidence remains mechanically supported.
- HSTU-BLaIR comparator constants are externally supported by the public
  arXiv/repository materials.
- The TORS hygiene scan is PASS; the detected SOTA strings are informational
  non-claim/negated-claim contexts.

### Concrete Fixes To Make Next

1. Rewrite Appendix A.0 in `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
   `paper_tex/sections/appendix-a0.tex`: V1 remains VOID and no V1 claim counts;
   V3 separately passed and counts only under its frozen point-estimate wording.
2. Rebuild the PDFs after that source fix and verify `Office is not counted` no
   longer appears in rendered artifacts except in an explicitly V1-scoped form.
3. Regenerate/supersede the deposit bundle and `DOI_DEPOSIT_INSTRUCTIONS.md` so
   Office V3 and FIR-breadth prereg/results docs, result JSONs, and TORS PDF are
   present, or clearly state the new release artifact name.
4. Update `RELEASE_MANIFEST.json` or its scope note so Office V3 and FIR-breadth
   are not invisible to the archival manifest.
5. Add a SILLM4Rec bibliography entry and cite the ACM DOI/repo in Section 5.1,
   or inspect the ACM PDF and revise the exclusion with page/table-specific
   evidence.
6. Refresh `paper_tex/BUILD_NOTES.md` to match current page counts and hygiene
   output.

### Open Questions

- Is `_release/bestrec_deposit_v1.0.zip` meant to be replaced, or should a
  `v1.0.1`/new DOI-deposit bundle supersede it?
- Should Office V3/FIR-breadth per-user sidecars remain local-only until
  reviewer request, or be deposited now as supplementary evidence?
- Is `PAPER_DRAFT.md` still a live manuscript source, or should it be marked
  archival to avoid stale-status review confusion?
- Can the authors access the SILLM4Rec ACM full text before final freeze?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Re-run strict artifact gate.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Check rendered PDFs for stale Office wording.
- [x] Check release/deposit zip and release manifest scope.
- [x] Fact-check HSTU-BLaIR, AR2023, Latte, ChronoSID, SILLM4Rec, GrIT, and
      Augment-or-Not against external sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair Appendix A.0 Office V1/V3 contradiction in all live sources/PDFs.
- [ ] Refresh release/deposit package and manifest boundary.
- [ ] Add/inspect SILLM4Rec formally before freeze.
- [ ] Refresh `paper_tex/BUILD_NOTES.md`.

## Audit Run - 2026-07-14 09:58 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  (file absent at run start; directory created later for this automation).
- Last automation run supplied by scheduler: `2026-07-13T22:57:29.048Z`
  (`2026-07-14 08:57:29 Australia/Sydney`).
- Current run time: `2026-07-14 09:58:38 +10:00`; main adjudicators completed
  at `2026-07-14 09:58:57 Australia/Sydney`.
- Active sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `paper_tex/sections/*.tex`,
  `paper_tex/references.bib`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/hygiene_scan_output.txt`, `CANONICAL_SUBMISSION.md`,
  `VENUE_PLAN.md`, `RELEASE_MANIFEST.json`,
  `_bestrec_run/hstu_results_manifest.json`, `_release/bestrec_deposit_v1.0.zip`,
  `DOI_DEPOSIT_INSTRUCTIONS.md`, and `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`.
- Workspace changes since the last scheduled run: only `PAPER_REVIEW_AUDIT.md`,
  the prior Table 2 render PNGs under `tmp/pdfs/`, `_bestrec_run/hstu_tables.json`,
  and `paper_tex/hygiene_scan_output.txt` were newer than `08:57:29`.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- This audit edited only `PAPER_REVIEW_AUDIT.md`.

### Verdict

**No new empirical failure appeared, but the same top-journal blockers remain
live.** The strict artifact graph, Office V3 adjudicator, FIR-breadth
adjudicator, and TORS hygiene scan all pass. The paper is still not
submission-ready because Appendix A.0 and all rendered PDFs still say Office is
not counted, while the abstract/Section 5.2 count Office V3 as the second
pre-registered per-category comparison. The release/deposit bundle is also still
stale relative to Office V3 and FIR-breadth.

The important change since the previous hour is negative evidence: no manuscript
source changed after the 08:58 audit, so the earlier blockers were not repaired.
The current run therefore confirms persistence rather than discovering a new
numerical defect.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS.
  - HSTU core-block parity exact.
  - `168` cells recomputed; `0` paper mismatches; `0` untraceable; all `14`
    declared claim families sourced.
  - Release manifest verification OK for its declared `113` files.
  - MI V2 gate OK; legacy Office V1 descriptive/VOID adjudication OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 09:58:56`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`; 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`; 5/5 seeds above
    both references.
  - Comparability conditions OK; frozen claim remains per-category
    point-estimate only, not paired superiority or SOTA.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 09:58:57`, block `9a38ad66bd75`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: 40 pages; `0` placeholder/forbidden-claim failures; 20 informational
    SOTA/non-claim review hits.
- PDF extraction with `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; `Office is not counted` on page 41;
    `SILLM4Rec` on page 19.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; `Office is not counted` on page 36;
    `SILLM4Rec` on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; `Office is not counted` on
    page 37; `SILLM4Rec` on page 18.
- Text search
  - `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
    `paper_tex/sections/appendix-a0.tex` still contain the stale Appendix A.0
    sentence that the confirmed per-category claim remains Musical_Instruments
    only and Office is not counted.
  - `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` still claims those Office status sites
    were fixed and that zero stale occurrences remain; the live sources and PDFs
    contradict that response.
  - `paper_tex/references.bib` has entries for SID-MLP, Latte, ChronoSID,
    ReSID, GrIT, Augment-or-Not, and DiffuReason, but still has no SILLM4Rec
    entry.
  - `paper_tex/BUILD_NOTES.md` still says the acmsmall preview is 40 pages near
    the top, still embeds old round-8 35/36-page compile notes, and the current
    `paper_tex/PAPER_TORS_acmsmall.pdf` is 41 pages.
- Release/deposit check
  - `_release/bestrec_deposit_v1.0.zip`: SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`, 48
    entries.
  - Missing from zip: `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
    `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`, and
    `paper_tex/PAPER_TORS.pdf`.
  - `DOI_DEPOSIT_INSTRUCTIONS.md` still describes a 46-file `v1.0-deposit`
    release asset rather than the current Office V3/FIR-breadth claim set.

### External Fact-Check / Novelty Notes

- The official Amazon Reviews 2023 site supports the dataset framing: it
  describes a 2023 McAuley Lab release with user reviews, item metadata, links,
  standard splits, and corpus scale of `571.54M` reviews / `54.51M` users /
  `48.19M` items. Source: https://amazon-reviews-2023.github.io/
- HSTU-BLaIR v3 continues to support the comparator constants and dataset family:
  it reports AR2023 5-core Video Games, Office Products, and Musical Instruments
  statistics matching the paper's protocol family, with HSTU-BLaIR NDCG@10
  `0.0760`, `0.0271`, and `0.0406`. Source:
  https://arxiv.org/html/2504.10545v3
- SID-MLP is a close same-statistics generative-retrieval pressure point: it
  evaluates AR2023 Musical Instruments, Industrial & Scientific, and Video Games
  with the HSTU-family statistics (`57,439 / 24,587 / 511,836` for MI and
  `94,762 / 25,612 / 814,586` for Video Games) and reports multi-seed NDCG
  values around MI `0.0332` and Games `0.0512` for its distilled variant. Source:
  https://arxiv.org/html/2605.12617v1
- ChronoSID/ReSID are correctly fenced as non-interchangeable with this paper's
  HSTU-BLaIR-family comparison: ChronoSID's Table 1 reports MI `57,359` users /
  `23,742` items / `490,522` interactions and VG `94,515` / `24,685` /
  `772,218`, not this paper's MI/VG statistics. Its output-level analysis also
  reports ChronoSID improvements over ReSID, so it remains relevant literature
  for the tail/temporal-modeling discussion even if not directly comparable.
  Source: https://arxiv.org/html/2607.03918v1
- SILLM4Rec remains close enough that the current no-bibliography posture is
  risky. Its public repository says the workflow uses AR2023 5-core files and
  creates image descriptions, user-preference summaries, candidate-product
  ranking tasks, and SFT/DPO data; ACM/DBLP identify it as an MMAsia 2025 paper
  with DOI `10.1145/3743093.3771011`. This supports a repository-based
  non-interchangeability rationale, but a top-journal submission should either
  inspect/cite the full paper or explicitly cite the repo/DOI as the basis for
  exclusion. Sources: https://github.com/MKC-Lab/SILLM4Rec,
  https://dl.acm.org/doi/10.1145/3743093.3771011,
  https://dblp.org/rec/conf/mmasia/WuQL0025

### Confirmed Problems

1. **Appendix A.0 still contradicts the counted Office V3 claim.** This is in
   both markdown sources, the TeX appendix, and all rendered PDFs.
2. **The release/deposit bundle is stale.** A reviewer following the deposit
   instructions would not receive the Office V3 or FIR-breadth prereg/results
   evidence.
3. **`RELEASE_MANIFEST.json` remains narrower than the current public claim
   family story.** The strict gate sees `office_v3` and `fir_breadth` through
   `_bestrec_run/hstu_results_manifest.json`, while the public release manifest
   does not name those families.
4. **`RESPONSE_TO_PAPER_REVIEW_AUDIT.md` overstates fixes.** It says the Office
   wording was repaired; live sources and PDFs disprove that.
5. **`paper_tex/BUILD_NOTES.md` is stale relative to current artifacts.**
   Current acmsmall is 41 pages, but notes still claim 40 and retain old 35/36
   page compile-status material.
6. **SILLM4Rec remains under-cited.** The current exclusion sentence is more
   concrete than before, but no formal bibliography entry exists.

### Confirmed Non-Problems

- No strict-gate numerical/provenance failure was found.
- Office V3 still passes mechanically under the frozen per-category
  point-estimate wording.
- FIR-breadth still passes mechanically for both added categories.
- The paper's SID-line/non-comparability fence is factually supported for
  ChronoSID/ReSID, and the "no comparative claim against concurrent arXiv-only
  work" stance remains appropriate.
- The SILLM4Rec repository evidence supports non-interchangeability; the defect
  is citation/protocol-inspection completeness, not a proven false exclusion.

### Concrete Fixes To Make Next

1. Rewrite Appendix A.0 in `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
   `paper_tex/sections/appendix-a0.tex` so the V1 VOID is scoped to V1 and the
   V3 pass is counted consistently under its frozen no-SOTA/no-paired-
   superiority wording.
2. Re-render `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`, and
   `paper_tex/PAPER_TORS_acmsmall.pdf`; then re-run PDF extraction for the stale
   Office phrase.
3. Regenerate/supersede the deposit bundle and `DOI_DEPOSIT_INSTRUCTIONS.md` so
   Office V3 and FIR-breadth prereg/results evidence are included or explicitly
   linked.
4. Align `RELEASE_MANIFEST.json` with the current claim-family story, or make it
   explicitly delegate Office V3/FIR-breadth family detail to
   `_bestrec_run/hstu_results_manifest.json`.
5. Refresh `paper_tex/BUILD_NOTES.md` for the actual 40-page review PDF and
   41-page acmsmall preview.
6. Add a formal SILLM4Rec citation/protocol note, or record that full-paper
   inspection remains pending and the exclusion rests on repository evidence.

### Open Questions

- Should the stale `_release/bestrec_deposit_v1.0.zip` be replaced in place,
  superseded as `v1.0.1`, or left historical with a new current release asset?
- Should `RELEASE_MANIFEST.json` become the single public manifest for Office
  V3/FIR-breadth, or should it point reviewers to
  `_bestrec_run/hstu_results_manifest.json` for claim-family detail?
- Can the authors access the SILLM4Rec ACM PDF/full text before freeze, or
  should the paper cite the public repo and DOI as the concrete inspected
  evidence?
- Is the 41-page acmsmall preview acceptable, or should layout be compressed
  before any production-preview distribution?

### Running Checklist

- [x] Read automation memory status and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Check file changes since the prior scheduled run.
- [x] Re-run strict manuscript/artifact gate.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Re-run TORS PDF hygiene scan.
- [x] Extract PDF page counts and stale phrase locations.
- [x] Check release zip entries and SHA256.
- [x] Check current references/literature coverage for SID-MLP, ChronoSID, and
      SILLM4Rec.
- [x] Fact-check AR2023, HSTU-BLaIR, SID-MLP, ChronoSID, and SILLM4Rec against
      external sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair Appendix A.0 Office V1/V3 contradiction in all live sources/PDFs.
- [ ] Refresh the release/deposit package and manifest boundary.
- [ ] Refresh stale build notes and decide the acmsmall page-count target.
- [ ] Add/inspect SILLM4Rec formally before freeze.

## Audit Run - 2026-07-14 08:58 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  (`Last run: 2026-07-14 08:02 Australia/Sydney`).
- Current run time: `2026-07-14 08:58:16 +10:00`; main adjudicators completed
  at `2026-07-14 08:58:45 Australia/Sydney`.
- Active sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `paper_tex/main.tex`,
  `paper_tex/paper-shared.tex`, `paper_tex/sections/*.tex`,
  `paper_tex/references.bib`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/hygiene_scan_output.txt`, `VENUE_PLAN.md`,
  `CANONICAL_SUBMISSION.md`, `RELEASE_MANIFEST.json`,
  `_bestrec_run/hstu_results_manifest.json`, `_release/bestrec_deposit_v1.0.zip`,
  `DOI_DEPOSIT_INSTRUCTIONS.md`, `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, and fresh
  Table 2 page renders.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- This audit edited only `PAPER_REVIEW_AUDIT.md`.

### Verdict

**No empirical gate failed, but the paper is still not top-journal
submission-ready.** The strict artifact graph, Office V3 adjudicator, FIR
breadth adjudicator, and TORS hygiene scan all passed again. The live rejection
risk is therefore not "the numbers do not recompute"; it is that the manuscript
and release package still tell incompatible stories about what is counted and
what is deposited.

The most damaging issue remains the Office contradiction: the abstract/Section
5.2 count Office V3 as a second passed pre-registered per-category comparison,
but Appendix A.0 in Markdown, TeX, and all rendered PDFs still says the
confirmed per-category claim is Musical_Instruments only and that Office is not
counted. A top-journal reviewer will treat this as a basic claim-control failure
even though the underlying V3 mechanics pass.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS.
  - HSTU core-block parity exact.
  - `168` cells recomputed; `0` paper mismatches; `0` untraceable; all `14`
    declared claim families sourced.
  - Release manifest verification OK for its declared `113` files.
  - MI V2 gate OK; legacy Office V1 descriptive/VOID check OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 08:58:45`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`; 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`; 5/5 seeds above
    both references.
  - Comparability conditions OK; frozen claim remains per-category
    point-estimate only, not paired superiority or SOTA.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 08:58:45`, block `9a38ad66bd75`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: 40 pages; `0` placeholder/forbidden-claim failures; 20 informational
    SOTA/non-claim review hits.
- PDF extraction with `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; stale Office non-counted wording on page
    41; SILLM4Rec on page 19.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; stale Office non-counted wording on
    page 36; SILLM4Rec on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; stale Office non-counted
    wording on page 37; SILLM4Rec on page 18.
- Text search
  - `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
    `paper_tex/sections/appendix-a0.tex` still contain the stale Appendix A.0
    Office V1 sentence.
  - `PAPER_DRAFT.md` still starts with Draft v3.8 status text saying "Office
    stays VOID" and Office V3's outcome is pending.
  - `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` still claims those sites were fixed and
    that zero stale occurrences remain; the live sources and PDFs contradict
    that response.
  - `paper_tex/references.bib` still has no SILLM4Rec entry.
  - `paper_tex/BUILD_NOTES.md` still contains round-8 `35 pages` / `36 pages`
    notes and "current builds are 40/40" while `PAPER_TORS_acmsmall.pdf` is 41
    pages.
- Release/deposit check
  - `_release/bestrec_deposit_v1.0.zip`: SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`, 48
    entries.
  - Missing from zip: `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
    `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`, and
    `paper_tex/PAPER_TORS.pdf`.
  - `DOI_DEPOSIT_INSTRUCTIONS.md` still says the deposit is "fully assembled"
    and describes an older 46-file bundle.
  - `RELEASE_MANIFEST.json` verifies only its declared scope and still has
    `result_families` = `MI_gate_EXEC2`, `MI_gate_EXEC2_rest`, `MI_rebuild`,
    `OFFICE_gate`, `OFFICE_idonly_floor`, and `FIR_ablations`; it does not
    mention `office_v3`, `fir_breadth`, or their prereg/results docs. The
    generated `_bestrec_run/hstu_results_manifest.json` does contain
    `office_v3` and `fir_breadth`.
- Fresh Table 2 render
  - Rendered `paper_tex/PAPER_TORS.pdf` pages 27-28 to
    `tmp/pdfs/tors_table2_20260714_0858-27.png` and
    `tmp/pdfs/tors_table2_20260714_0858-28.png`.
  - Visual inspection confirms the caption is stranded at the bottom of page 27
    while the table body starts on page 28.

### External Fact-Check / Novelty Notes

- The Amazon Reviews 2023 official site still supports the paper's broad dataset
  framing: it describes a 2023 McAuley Lab release with reviews, item metadata,
  links, and standard splits, and gives the 571.54M-review scale. Source:
  https://amazon-reviews-2023.github.io/
- SILLM4Rec is close enough that omission from the bibliography is risky. ACM
  and dblp identify it as "SILLM4Rec: Self-Improving with Chain of Thought
  Enhanced Preference Optimization for Multimodal Recommendation", MMAsia 2025,
  DOI `10.1145/3743093.3771011`, pages 65:1-65:8. The public repo says it uses
  AR2023 5-core files, then generates image descriptions, user preference
  summaries, candidate ranking tasks, and SFT/DPO data. This supports the
  paper's non-interchangeability rationale, but not a no-citation posture.
  Sources: https://dl.acm.org/doi/10.1145/3743093.3771011,
  https://dblp.org/rec/conf/mmasia/WuQL0025,
  https://github.com/MKC-Lab/SILLM4Rec
- The current caution around 2026 concurrent semantic-ID/generative-retrieval
  work remains necessary. Latte and GrIT are real AR2023-adjacent comparator
  pressure points, but the manuscript's "no comparative claim against concurrent
  arXiv-only work" fence is appropriate unless their protocols/training details
  are audited. Sources: https://arxiv.org/abs/2605.06331 and
  https://arxiv.org/abs/2602.19728
- The FIR novelty boundary remains appropriately narrow. WPGRec is confirmed as
  accepted on the SIGIR 2026 accepted-papers page and as a wavelet-packet/time-
  frequency sequential recommender on arXiv. This reinforces that this paper
  must claim only the left-causal depthwise FIR regularizer in the HSTU-style
  artifact-gated setting, not broad time-frequency novelty. Sources:
  https://arxiv.org/abs/2604.21305 and
  https://sigir2026.org/en-AU/pages/program/accepted-papers

### Confirmed Problems

1. **Appendix A.0 still contradicts the counted Office V3 claim.** Fix all live
   sources and rendered artifacts so the old V1 VOID is clearly scoped to V1
   and the V3 pass is stated consistently.
2. **The release/deposit package is stale relative to the current claim set.**
   A reviewer following `DOI_DEPOSIT_INSTRUCTIONS.md` or the deposit zip would
   not receive the Office V3/FIR-breadth prereg/results evidence or the TORS PDF.
3. **`RELEASE_MANIFEST.json` and `_bestrec_run/hstu_results_manifest.json` are
   not aligned at the family-documentation level.** The strict table gate sees
   the new claim families; the public release manifest does not name them.
4. **`PAPER_DRAFT.md` carries stale top-level status prose.** Because
   `CANONICAL_SUBMISSION.md` says `PAPER_DRAFT.md` is a canonical working copy,
   this is not harmless archive noise.
5. **`RESPONSE_TO_PAPER_REVIEW_AUDIT.md` overstates fixes.** It says all Office
   status sites were updated and zero stale occurrences remain, but the live
   sources/PDFs disprove that. This weakens the response audit trail.
6. **Table 2 layout remains production-weak.** The caption/body split across
   pages is not fatal science, but it reads as unpolished for TORS.
7. **SILLM4Rec is under-cited.** The paper's non-comparability rationale is
   plausible, but a formal citation and/or direct full-text protocol inspection
   should be done before freeze.

### Confirmed Non-Problems

- No current hard numerical/provenance failure was found in the strict gate.
- Office V3's mechanical evidence remains green under its frozen narrow wording.
- FIR breadth remains confirmed under its frozen internal filter-vs-no-filter
  wording.
- The SILLM4Rec public repo evidence supports non-interchangeability with
  full-catalog LLOO; the problem is incomplete citation/protocol inspection, not
  a proven false exclusion.
- The current paper wording around concurrent arXiv-only work is cautious
  enough; do not convert those point-estimate observations into claims.

### Concrete Fixes To Make Next

1. Rewrite Appendix A.0 in `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
   `paper_tex/sections/appendix-a0.tex` so V1 remains VOID but Office V3 is
   counted exactly as frozen: per-category point-estimate comparison only; no
   paired superiority; no SOTA.
2. Re-render `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`, and
   `paper_tex/PAPER_TORS_acmsmall.pdf`; then rerun PDF extraction for the stale
   Office phrase.
3. Rebuild the deposit/release boundary: include Office V3 and FIR-breadth
   prereg/results docs, decide whether `paper_tex/PAPER_TORS.pdf` belongs in the
   deposit zip, update `DOI_DEPOSIT_INSTRUCTIONS.md`, and regenerate any hashes.
4. Extend or supplement `RELEASE_MANIFEST.json` so the public manifest names
   `office_v3` and `fir_breadth` or explicitly points to
   `_bestrec_run/hstu_results_manifest.json` as the source of truth.
5. Either remove the stale `PAPER_DRAFT.md` status line or update it to the
   post-V3 reality.
6. Add a formal SILLM4Rec bibliographic entry and cite it in the exclusion
   sentence, or inspect the ACM full text and record the exact protocol verdict
   in `VENUE_PLAN.md`.
7. Fix Table 2's layout before submission freeze, preferably by splitting the
   negative-result map or forcing the caption/table body to stay together.

### Open Questions

- Is `_release/bestrec_deposit_v1.0.zip` intended to be regenerated immediately,
  or should it be superseded by a new `v1.0.1`/freeze bundle after all text
  fixes land?
- Should `RELEASE_MANIFEST.json` become the sole public manifest for Office
  V3/FIR-breadth, or should it explicitly delegate claim-family detail to
  `_bestrec_run/hstu_results_manifest.json`?
- Will the authors inspect the SILLM4Rec ACM PDF directly before freeze, or
  settle for the repository/ACM/dblp evidence plus a cautious non-comparability
  citation?
- Is `PAPER_DRAFT.md` truly live/canonical, or should `CANONICAL_SUBMISSION.md`
  be narrowed to avoid treating old draft status notes as submission evidence?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and response artifacts.
- [x] Search manuscript and TeX for stale Office V3 pending/no-claim wording.
- [x] Re-run strict manuscript/artifact gate.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Check compiled PDF page counts and stale phrase locations.
- [x] Check TORS PDF hygiene scan.
- [x] Check release zip entries, SHA256, and public manifest family coverage.
- [x] Render and visually inspect Table 2 pages 27-28.
- [x] Fact-check SILLM4Rec, AR2023, Latte/GrIT, and WPGRec-related claims
      against external sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair Appendix A.0 Office V1/V3 contradiction in all live sources/PDFs.
- [ ] Refresh the release/deposit package and manifest boundary.
- [ ] Fix or split Table 2 layout.
- [ ] Add/inspect SILLM4Rec formally before freeze.

## Audit Run - 2026-07-14 07:58 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  (`Last run: 2026-07-14 07:01 Australia/Sydney`).
- Current run time: `2026-07-14 07:58:22 +10:00`; main adjudicators completed
  at `2026-07-14 07:58:41 Australia/Sydney`.
- Active sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `paper_tex/main.tex`,
  `paper_tex/paper-shared.tex`, `paper_tex/sections/*.tex`,
  `paper_tex/references.bib`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/hygiene_scan_output.txt`, `VENUE_PLAN.md`,
  `RELEASE_MANIFEST.json`, `_bestrec_run/hstu_results_manifest.json`,
  `_release/bestrec_deposit_v1.0.zip`, and refreshed Table 2 page renders.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- This audit edited only `PAPER_REVIEW_AUDIT.md`.

### Verdict

**No new empirical gate failure was found, but the manuscript remains
not submission-ready.** The hourly rerun confirms the same split: strict
artifact evidence is green, while top-journal rejection risk is concentrated in
internal consistency, archival packaging, rendered table quality, and one
under-cited related-work exclusion.

The most severe live contradiction is unchanged: Appendix A.0 still says
`Office is not counted` in Markdown, TeX, and all compiled PDFs, while the main
paper elsewhere counts Office V3 as a passed pre-registered per-category
comparison. `PAPER_DRAFT.md` also still carries the old Draft v3.8 status note
saying Office V3 was pending and Office stays VOID.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS.
  - HSTU core-block parity exact.
  - `168` cells recomputed; `0` paper mismatches; `0` untraceable; all `14`
    declared claim families sourced.
  - Release manifest verification OK for its declared `113` files.
  - MI V2 gate OK; legacy Office V1 descriptive/VOID check OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 07:58:41`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`; 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`; 5/5 seeds above
    both references.
  - Comparability conditions OK; frozen claim remains per-category
    point-estimate only, not paired superiority or SOTA.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 07:58:41`, block `9a38ad66bd75`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: 40 pages; `0` placeholder/forbidden-claim failures; 20 informational
    SOTA/non-claim review hits.
- PDF extraction with `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; `Office is not counted` on page 41;
    `SILLM4Rec` on page 19.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; `Office is not counted` on page 36;
    `SILLM4Rec` on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; `Office is not counted` on
    page 37; `SILLM4Rec` on page 18.
- Text search
  - `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
    `paper_tex/sections/appendix-a0.tex` still contain the stale Appendix A.0
    Office V1 wording.
  - `PAPER_DRAFT.md` still starts with Draft v3.8 status text saying "Office
    stays VOID" and Office V3's outcome is pending.
  - `paper_tex/references.bib` still has no SILLM4Rec entry.
  - `paper_tex/BUILD_NOTES.md` still contains old round-8 `35 pages` /
    `36 pages` notes despite the current PDF counts.
- Release/deposit check
  - `_release/bestrec_deposit_v1.0.zip`: SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`, 48
    entries.
  - Missing from zip: `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
    `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`, and
    `paper_tex/PAPER_TORS.pdf`.
  - `RELEASE_MANIFEST.json` result families remain only `FIR_ablations`,
    `MI_gate_EXEC2`, `MI_gate_EXEC2_rest`, `MI_rebuild`, `OFFICE_gate`, and
    `OFFICE_idonly_floor`; it still contains neither `office_v3` nor
    `fir_breadth`.
  - `_bestrec_run/hstu_results_manifest.json` still includes `office_v3` and
    `fir_breadth`.
- Visual PDF render with direct Poppler executable
  - Rendered `paper_tex/PAPER_TORS.pdf` pages 27-28 to
    `tmp/pdfs/tors_table2_20260714_0758-27.png` and
    `tmp/pdfs/tors_table2_20260714_0758-28.png`.
  - Visual inspection confirms the Table 2 caption remains stranded at the
    bottom of page 27 while the table body starts on page 28.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR continues to support the paper's comparator constants and AR2023
  5-core subset statistics: Video Games `25,612 / 94,762 / 814,585`, Office
  Products `77,551 / 223,308 / 1,800,877`, Musical Instruments `24,587 /
  57,439 / 511,835`, with HSTU-BLaIR NDCG@10 `0.0760`, `0.0271`, and
  `0.0406`. Source: https://arxiv.org/pdf/2504.10545
- Amazon Reviews 2023 official documentation still supports the high-level
  dataset framing: 571.54M reviews, 54.51M users, 48.19M items, interactions
  through September 2023, rich review/item/link metadata, and standard splits.
  Source: https://amazon-reviews-2023.github.io/
- SILLM4Rec remains a citation/readiness risk rather than a proven comparator
  threat. ACM metadata identifies the paper, and the public GitHub workflow
  says to use AR2023 5-core files, generate image descriptions and preference
  summaries, create candidate product ranking tasks, and generate SFT/DPO
  training data. That supports the manuscript's non-interchangeability
  rationale, but the paper still needs a formal citation or direct full-paper
  inspection before freeze. Sources: https://dl.acm.org/doi/10.1145/3743093.3771011
  and https://github.com/MKC-Lab/SILLM4Rec
- Latte remains close same-family novelty pressure: it uses AR2023 Instruments,
  Scientific, and Games with leave-one-out splitting and reports Latte NDCG@10
  `0.0331` on Instruments and `0.0515` on Games. The manuscript's no-claim
  wording against concurrent arXiv work remains necessary. Source:
  https://arxiv.org/html/2605.06331
- GrIT still reports Video Games full-item-set NDCG@10 `0.0588` under matching
  broad AR2023 Video Games statistics; the paper's point estimate is higher,
  but the current "point-estimate observation, not a claim" wording remains the
  safest boundary. Source: https://arxiv.org/html/2602.19728v1
- ChronoSID/ReSID still use a different filtered universe, e.g. MI `57,359`
  users / `23,742` items / `490,522` interactions and output-level MI NDCG@10
  `0.0345` for ChronoSID vs `0.0325` for ReSID, supporting non-interchangeable
  protocol caveats. Source: https://arxiv.org/html/2607.03918v1

### Confirmed Problems

1. **Appendix A.0 contradiction persists in all live forms.** The phrase
   `Office is not counted` remains in `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`,
   `paper_tex/sections/appendix-a0.tex`, and all compiled PDFs.
2. **`PAPER_DRAFT.md` still carries stale draft-status prose.** Its v3.8
   status note says Office stays VOID and the V3 outcome is pending, while
   current paper sections count Office V3.
3. **The release/deposit boundary is stale.** The deposit zip and
   `RELEASE_MANIFEST.json` omit Office V3 and FIR-breadth even though the
   generated HSTU results manifest and printed claims include them.
4. **Table 2 remains visually defective.** A caption-only page ending followed
   by the table body on the next page is not production-quality for TORS review.
5. **SILLM4Rec is still under-cited.** The current exclusion is plausible, but
   `references.bib` lacks a SILLM4Rec entry and `VENUE_PLAN.md` still marks
   direct full-paper inspection as pending.
6. **`paper_tex/BUILD_NOTES.md` is still stale.** Old 35/36-page notes remain
   alongside current 40/41-page PDF reality.

### Confirmed Non-Problems

- No empirical table mismatch, untraceable value, or strict artifact-graph
  failure was found on the fresh rerun.
- Office V3 aggregate evidence remains mechanically green under its frozen
  point-estimate wording.
- FIR-breadth evidence remains mechanically green for both internal
  filter-vs-no-filter categories.
- The TORS PDF hygiene scan remains PASS with only informational SOTA/non-claim
  review hits.
- The major HSTU-BLaIR dataset statistics and NDCG constants remain externally
  supported by the cited arXiv PDF.

### Concrete Fixes To Make Next

1. Replace the Appendix A.0 sentence in `PAPER_SUBMISSION.md`,
   `PAPER_DRAFT.md`, and `paper_tex/sections/appendix-a0.tex` with a scoped
   V1/V3 statement: V1 Office remains VOID; V3 Office is separate, passed under
   its frozen pre-registration, and is reported in Section 5.2.
2. Update or mark noncanonical the stale Draft v3.8 status note in
   `PAPER_DRAFT.md`.
3. Rebuild `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`, and
   `paper_tex/PAPER_TORS_acmsmall.pdf`; verify `Office is not counted`
   disappears from all PDF text.
4. Regenerate the release/deposit package so Office V3 docs, FIR-breadth docs,
   the current TORS PDF, and the intended sidecar policy are in the archival
   bundle/manifest.
5. Fix Table 2 placement by forcing the caption and table body to travel
   together, splitting the table, or moving the table to an appendix/landscape
   presentation.
6. Add a formal SILLM4Rec bibliography entry or remove the named exclusion until
   the ACM full text has been inspected.
7. Refresh `paper_tex/BUILD_NOTES.md` to the current 40-page TORS / 41-page
   acmsmall state and remove old round-8 page-count language.

### Open Questions

- Is `PAPER_DRAFT.md` still a live source, or should it be explicitly labeled
  as stale/noncanonical?
- Should the final DOI/deposit bundle include Office V3 and FIR-breadth
  per-user sidecars, or only aggregate JSON/treestate evidence?
- Should `RELEASE_MANIFEST.json` enumerate `office_v3` and `fir_breadth`
  directly, or should it point readers to `_bestrec_run/hstu_results_manifest.json`
  as the live claim-family source of truth?
- Can the authors access the SILLM4Rec ACM PDF before freeze, or should the
  manuscript cite only the public repository/metadata and soften the exclusion?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate active Markdown, TeX, PDF, figure/table, result, release, and
      bibliography artifacts.
- [x] Rerun strict HSTU submission rebuild.
- [x] Rerun Office V3 adjudicator.
- [x] Rerun FIR-breadth adjudicator.
- [x] Rerun TORS PDF hygiene scan.
- [x] Search live sources for stale Office, pending, SILLM4Rec, and build-note
      wording.
- [x] Extract PDF text for stale Office/SILLM occurrences and page counts.
- [x] Check deposit zip and release-manifest scope.
- [x] Render and visually inspect TORS Table 2 pages.
- [x] Fact-check key comparator/dataset/concurrent-literature claims against
      external sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Scope/fix Appendix A.0 Office V1/V3 wording in all live sources.
- [ ] Rebuild PDFs after manuscript fix and verify stale phrase removal.
- [ ] Refresh deposit/release package for Office V3 and FIR-breadth.
- [ ] Fix Table 2 caption/body layout.
- [ ] Add/inspect/cite SILLM4Rec or remove the named exclusion.
- [ ] Refresh `paper_tex/BUILD_NOTES.md`.

## Audit Run - 2026-07-14 06:58 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  (`Last run: 2026-07-14 06:01 Australia/Sydney`).
- Current run time: `2026-07-14 07:01:02 +10:00`; main adjudicators completed
  at `2026-07-14 06:58:25 Australia/Sydney`.
- Active manuscript/artifact path inspected: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `paper_tex/main.tex`,
  `paper_tex/main-acmsmall.tex`, `paper_tex/paper-shared.tex`,
  `paper_tex/sections/*.tex`, `paper_tex/tables/*.tex`,
  `paper_tex/references.bib`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/hygiene_scan_output.txt`, figures/tables, `VENUE_PLAN.md`,
  `RELEASE_MANIFEST.json`, `_bestrec_run/hstu_results_manifest.json`,
  Office V3/FIR-breadth result JSONs, `_release/bestrec_deposit_v1.0.zip`,
  and `DOI_DEPOSIT_INSTRUCTIONS.md`.
- Inventory note: one `.docx` exists at
  `_bestrec_sota_lab/paper_draft/build/lc2c_retrieval_ltr_paper.docx`, but it
  appears to be a legacy/noncanonical lab draft rather than the active TORS
  submission path.
- Working tree before this audit edit: tracked modification in
  `PAPER_REVIEW_AUDIT.md`; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- This audit edited only `PAPER_REVIEW_AUDIT.md`.

### Verdict

**The mechanical evidence is green, but the paper is still not
submission-ready for a top journal.** This run found no new numerical failure:
the strict rebuild, Office V3 adjudicator, FIR-breadth adjudicator, and TORS PDF
hygiene scan all pass. The live rejection risks remain presentation and
archival integrity:

1. Appendix A.0 still contains the unscoped sentence "Office is not counted" in
   Markdown, TeX, and all compiled PDFs, contradicting the current Office V3
   counted-claim wording elsewhere.
2. The DOI/deposit package is stale relative to Office V3 and FIR-breadth, and
   `RELEASE_MANIFEST.json` still omits those result families even though the
   generated HSTU manifest includes them.
3. Table 2 remains visually defective in the TORS PDF: the caption is stranded
   at the bottom of page 27 and the table body starts on page 28.
4. SILLM4Rec is still a named exclusion without a formal bibliography entry or
   direct full-paper protocol inspection.
5. `PAPER_DRAFT.md` has a stale status line saying Office V3's outcome was
   pending, despite later body text correctly saying V3 passed.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS.
  - HSTU core-block parity exact.
  - `168` cells recomputed; `0` paper mismatches; `0` untraceable; all `14`
    declared claim families sourced.
  - Release manifest verification OK for its declared `113` files.
  - MI V2 gate OK; legacy Office V1 descriptive/VOID check OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 06:58:25`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`; 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`; 5/5 seeds above
    both references.
  - Comparability conditions OK; frozen claim remains per-category
    point-estimate only, not paired superiority or SOTA.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 06:58:25`, block `9a38ad66bd75`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: 40 pages; `0` placeholder/forbidden-claim failures; 20 informational
    SOTA/non-claim review hits.
- PDF extraction with `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; "Office is not counted" on page 41;
    `SILLM4Rec` on page 19.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; "Office is not counted" on page 36;
    `SILLM4Rec` on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; "Office is not counted" on
    page 37; `SILLM4Rec` on page 18.
- Visual PDF render with Poppler direct executable
  - The bundled `pdftoppm.cmd` wrapper failed in this shell, but the real
    Poppler executable worked:
    `...\dependencies\native\poppler\Library\bin\pdftoppm.exe`.
  - Rendered `paper_tex/PAPER_TORS.pdf` pages 27-28 to
    `tmp/pdfs/tors_table2_20260714_0658-27.png` and `...-28.png`.
  - Visual inspection confirmed page 27 ends with only the Table 2 caption and
    page 28 begins the table body.
- Release/deposit check
  - `_release/bestrec_deposit_v1.0.zip`: SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`,
    48 entries.
  - Missing from zip: `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
    `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`, and
    `paper_tex/PAPER_TORS.pdf`.
  - `RELEASE_MANIFEST.json` result families remain only `MI_gate_EXEC2`,
    `MI_gate_EXEC2_rest`, `MI_rebuild`, `OFFICE_gate`,
    `OFFICE_idonly_floor`, and `FIR_ablations`; it does not contain
    `office_v3`, `fir_breadth`, `OFFICE_V3_RESULTS`, or
    `FIR_BREADTH_RESULTS`.
  - `_bestrec_run/hstu_results_manifest.json` does include `office_v3` and
    `fir_breadth`.
- Office V3 sidecar metadata
  - All 10 Office V3 aggregate JSONs exist.
  - Three JSONs still lack `provenance.user_records_final_path`:
    `results_OFFICEV3_k16_seed20260729.json`,
    `results_OFFICEV3_k16_seed20260731.json`, and
    `results_OFFICEV3_k8_seed20260731.json`.
  - Each has `provenance.best_test_epoch = 20` and history length 20, so
    `user_records_path` may be the final-epoch sidecar, but that remains an
    author/release-boundary item to state explicitly.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR v3 supports the paper's comparator constants and AR2023 5-core
  dataset statistics: Video Games `25,612 / 94,762 / 814,585`, Office Products
  `77,551 / 223,308 / 1,800,877`, Musical Instruments `24,587 / 57,439 /
  511,835`, and HSTU-BLaIR NDCG@10 `0.0760`, `0.0271`, `0.0406`. Source:
  https://arxiv.org/html/2504.10545v3
- Amazon Reviews 2023 official documentation supports the dataset framing:
  571.54M reviews, 54.51M users, 48.19M items, interactions through September
  2023, richer metadata, and standard splits. Source:
  https://amazon-reviews-2023.github.io/
- SILLM4Rec remains a citation/readiness risk. DBLP/ACM metadata identify it as
  an MMAsia 2025 paper, pages 65:1-65:8, DOI `10.1145/3743093.3771011`.
  The public GitHub repository instructs users to build generated image
  descriptions, preference summaries, candidate product ranking tasks, and SFT
  / DPO training data from AR2023 5-core files. That supports the manuscript's
  non-interchangeability rationale, but not a final citation-ready exclusion
  without citing the ACM paper/repo or inspecting the full paper. Sources:
  https://github.com/MKC-Lab/SILLM4Rec,
  https://dl.acm.org/doi/10.1145/3743093.3771011,
  https://dblp.org/rec/conf/mmasia/WuQL0025
- Latte / SID-line and ChronoSID remain close novelty pressure. Latte states it
  uses AR2023 Instruments, Scientific, and Games with leave-one-out splitting;
  ChronoSID reports semantic-ID temporal augmentation and output-level MI
  NDCG@10 `0.0345` versus ReSID `0.0325`. GrIT reports full-item-set ranking on
  AR2023 Video Games with statistics matching this paper's VG family and NDCG
  evidence that is below this paper's VG point estimate, but the manuscript's
  "no comparative claim against concurrent arXiv-only work" wording remains
  necessary because protocols/training details were not fully audited. Sources:
  https://arxiv.org/html/2605.06331,
  https://arxiv.org/html/2607.03918v1,
  https://arxiv.org/html/2602.19728

### Confirmed Problems

1. **Appendix A.0 contradiction persists.** The sentence should be scoped to
   V1: "no claim counts the V1 campaign." As written, "Office is not counted"
   conflicts with Office V3 counted as the second pre-registered per-category
   comparison.
2. **Stale package/deposit boundary persists.** The strict gate verifies the
   repository's declared 113-file scope, but the deposit zip and
   `RELEASE_MANIFEST.json` do not yet reflect the current Office V3 and
   FIR-breadth claim set.
3. **Table 2 layout is still not production-quality.** A top-journal reviewer
   will see a caption separated from its table body in the main review PDF.
4. **SILLM4Rec is under-cited.** The manuscript names it in Section 5.1, but
   `paper_tex/references.bib` has no SILLM4Rec entry, and `VENUE_PLAN.md`
   correctly marks full-paper inspection as pending.
5. **`PAPER_DRAFT.md` header is stale.** The body has updated Office V3 text,
   but the draft status line still says V3 outcome was pending and Office stays
   VOID. If `PAPER_DRAFT.md` is kept, its status header needs repair or
   explicit noncanonical labeling.

### Confirmed Non-Problems

- The strict artifact graph remains green, with no empirical cell mismatch or
  untraceable value.
- Office V3 aggregate evidence remains mechanically green under its frozen
  point-estimate wording.
- FIR-breadth evidence remains mechanically green for the two internal
  filter-vs-no-filter categories.
- The TORS PDF hygiene scan has no placeholder/forbidden-claim hard failures;
  SOTA hits are informational non-claim contexts.
- The major HSTU-BLaIR comparator constants still match external arXiv v3
  evidence.

### Concrete Fixes To Make Next

1. Replace Appendix A.0's stale sentence in `PAPER_SUBMISSION.md`,
   `PAPER_DRAFT.md`, and `paper_tex/sections/appendix-a0.tex` with:
   "The confirmed per-category claim from the V1 campaign remains
   Musical_Instruments only; no claim counts the V1 Office campaign. The
   redesigned V3 Office pre-registration is separate and is reported in
   Section 5.2."
2. Rebuild the TeX PDFs after that edit and verify the phrase "Office is not
   counted" disappears from `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`,
   and `paper_tex/PAPER_TORS_acmsmall.pdf`.
3. Regenerate the deposit bundle and/or release manifest so Office V3 and
   FIR-breadth prereg/results docs, the current TORS PDF, and the intended
   sidecar policy are part of the archival story.
4. Fix Table 2 placement, likely by moving the caption with the table body,
   splitting the table, shrinking/rotating the table, or forcing a page break
   before the caption.
5. Add a formal SILLM4Rec citation or remove the named exclusion until the ACM
   full text has been inspected and archived.
6. Refresh `paper_tex/BUILD_NOTES.md` so page counts, hygiene-hit counts, and
   historical 35/36-page notes cannot be mistaken for current build facts.

### Open Questions

- Is `PAPER_DRAFT.md` intended to remain a live source, or should it be marked
  noncanonical now that `PAPER_SUBMISSION.md` and `paper_tex/` are the active
  submission path?
- Will the local-only Office V3 and FIR-breadth per-user sidecars be deposited
  with the final package, or only provided on reviewer/editor request?
- Should `RELEASE_MANIFEST.json` itself enumerate `office_v3` and
  `fir_breadth`, or is `_bestrec_run/hstu_results_manifest.json` the intended
  source of truth for live claim families?
- Can the authors access the ACM SILLM4Rec PDF before freeze, or should the
  manuscript cite only the public repository/metadata and soften the exclusion?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Inventory active Markdown/TeX/PDF sources, figures, tables, result files,
      manifests, release bundle, and legacy docx.
- [x] Re-run strict HSTU submission rebuild.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Re-run TORS PDF hygiene scan.
- [x] Extract PDF text for stale Office/SILLM occurrences and page counts.
- [x] Render and inspect TORS Table 2 pages.
- [x] Check deposit zip and release-manifest scope.
- [x] Fact-check key comparator/dataset/concurrent-literature claims against
      external sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Scope/fix Appendix A.0 Office V1/V3 wording in all live sources.
- [ ] Rebuild PDFs after manuscript fix and verify stale phrase removal.
- [ ] Refresh deposit/release package for Office V3 and FIR-breadth.
- [ ] Fix Table 2 caption/body layout.
- [ ] Add/inspect/cite SILLM4Rec or remove the named exclusion.
- [ ] Refresh `paper_tex/BUILD_NOTES.md`.

## Audit Run - 2026-07-14 05:58 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  (`Last run: 2026-07-14 04:57 Australia/Sydney`).
- Current run time: `2026-07-14T06:01:40.3620727+10:00`; main adjudicators
  completed at `2026-07-14 05:58:22 Australia/Sydney`.
- Live sources/artifacts inspected: `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/sections/*.tex`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/PAPER_TORS_acmsmall.pdf`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/references.bib`,
  `paper_tex/tables/table2.tex`, `paper_tex/hygiene_scan_output.txt`,
  `VENUE_PLAN.md`, `RELEASE_MANIFEST.json`,
  `_bestrec_run/hstu_results_manifest.json`, Office V3/FIR-breadth result
  JSONs, `_release/bestrec_deposit_v1.0.zip`, and
  `DOI_DEPOSIT_INSTRUCTIONS.md`.
- Working tree before this audit edit: tracked modification only in
  `PAPER_REVIEW_AUDIT.md`; untracked files still include
  `_bestrec_run/impact_program.DONE`, `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- This audit edited only `PAPER_REVIEW_AUDIT.md`.

### Verdict

**No new hard numerical failure was found, but the paper remains not
submission-ready.** The empirical artifact graph is green again, yet a strict
reviewer can still reject on internal contradiction and packaging:

1. Appendix A.0 in both Markdown and TeX still says "Office is not counted",
   while the abstract, Section 5.2, and Section 6.4 count Office V3 as a passed
   redesigned pre-registration.
2. The DOI/deposit package is stale relative to the live claims: the zip lacks
   Office V3 and FIR-breadth prereg/results documentation and does not include
   `paper_tex/PAPER_TORS.pdf`.
3. The TORS rendered PDF still has a layout defect: Table 2's caption is alone
   at the bottom of page 27 and the table body starts on page 28.
4. SILLM4Rec is still named in Section 5.1 without a bibliography entry or full
   protocol inspection; `VENUE_PLAN.md` correctly marks that inspection as
   freeze-blocking.
5. `paper_tex/BUILD_NOTES.md` remains stale: it says the acmsmall preview is 40
   pages and still embeds old 35/36-page compile notes, but the live acmsmall
   PDF is 41 pages.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS.
  - HSTU core-block parity exact.
  - `168` cells recomputed; `0` paper mismatches; `0` untraceable; all `14`
    declared claim families sourced.
  - Release manifest verification OK for its declared `113` files.
  - MI V2 gate OK; legacy Office V1 descriptive/VOID check OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 05:58:22`, block `196799e7c46d`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, 5/5 seeds above
    both references.
  - Comparability conditions OK; frozen claim remains a per-category
    point-estimate comparison only.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 05:58:22`, block `9a38ad66bd75`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: 40 pages; `0` placeholder/forbidden-claim failures; 20 informational
    SOTA/non-claim review hits.
- PDF extraction with `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; "Office is not counted" on page 41;
    `SILLM4Rec` on page 19.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; "Office is not counted" on page 36;
    `SILLM4Rec` on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; "Office is not counted" on
    page 37; `SILLM4Rec` on page 18.
- Visual PDF render with Poppler direct executable
  - Rendered `paper_tex/PAPER_TORS.pdf` pages 27-28 to
    `tmp/pdfs/tors_table2_20260714_0558-27.png` and `...-28.png`.
  - Confirmed page 27 ends with only the Table 2 caption and page 28 begins the
    table body.
- Release/deposit check
  - `_release/bestrec_deposit_v1.0.zip`: SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`,
    48 entries, timestamped `2026-07-11`.
  - Missing from zip: `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
    `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`, and
    `paper_tex/PAPER_TORS.pdf`.
  - `RELEASE_MANIFEST.json` still has only six older `result_families`
    (`MI_gate_EXEC2`, `MI_gate_EXEC2_rest`, `MI_rebuild`, `OFFICE_gate`,
    `OFFICE_idonly_floor`, `FIR_ablations`); generated
    `_bestrec_run/hstu_results_manifest.json` does include `office_v3` and
    `fir_breadth`.
- Office V3 sidecar metadata
  - All 10 Office V3 aggregate JSONs exist.
  - Three JSONs still lack `provenance.user_records_final_path`:
    `results_OFFICEV3_k16_seed20260729.json`,
    `results_OFFICEV3_k16_seed20260731.json`, and
    `results_OFFICEV3_k8_seed20260731.json`.
  - In those files `provenance.best_test_epoch = 20` and the history reaches
    epoch 20, so the regular `user_records_path` may be the final sidecar, but
    this remains author/release-boundary verification.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR v3 still supports the comparator constants and dataset statistics
  used here: AR2023 5-core Video Games, Office Products, and Musical
  Instruments are listed with 25,612/94,762/814,585; 77,551/223,308/1,800,877;
  and 24,587/57,439/511,835 item/user/interaction counts, and Table 2 reports
  HSTU-BLaIR NDCG@10 `0.0760`, `0.0271`, and `0.0406`. Source:
  https://arxiv.org/html/2504.10545v3
- The Amazon Reviews 2023 official site confirms the dataset release,
  571.54M reviews, rich review/metadata/link features, and standard splits.
  Source: https://amazon-reviews-2023.github.io/
- The current SILLM4Rec exclusion is directionally supported but not
  citation-ready. The public repository tells users to process AR2023 5-core
  files, generate user preference summaries, create candidate-product ranking
  tasks, and generate SFT/DPO training data. ACM metadata describes the work as
  re-ranking/candidate sorting, not established full-catalog LLOO. Sources:
  https://github.com/MKC-Lab/SILLM4Rec and
  https://dl.acm.org/doi/10.1145/3743093.3771011
- ChronoSID is a very recent pressure point, not a direct blocker. It reports
  AR2023/SID-line numbers and output-level MI NDCG@10 `0.0345` for ChronoSID
  versus `0.0325` for ReSID; its filtered universe remains distinct from the
  HSTU-BLaIR-family statistics used here. Source:
  https://arxiv.org/html/2607.03918v1
- GrIT confirms another close but non-identical AR2023 5-core full-ranking
  reference family: Video Games 94,762 users / 25,612 items / 814,586
  interactions and GrIT NDCG@10 `0.0588`. Source:
  https://arxiv.org/html/2602.19728v1
- DiffuReason reinforces why the paper must avoid loose Video_Games claims: it
  uses a "Video & Games" AR2023 universe with 67,658 users / 25,535 items /
  654,867 interactions, not the HSTU-BLaIR-family 94,762 / 25,612 / ~814,586
  universe. Source: https://arxiv.org/html/2602.09744v1

### Confirmed Problems

1. **Appendix A.0 is still internally contradictory.** It retains the old Office
   V1-only conclusion and says Office is not counted, despite the newer Office
   V3 pass being counted elsewhere.
2. **The current release/deposit story cannot support the paper's live claims.**
   The strict gate sees `office_v3` and `fir_breadth`, but the archival zip and
   top-level release manifest do not carry the corresponding prereg/results
   files as first-class release families.
3. **Table 2 remains visually unprofessional in the TORS artifact.** The caption
   and table body are split across pages; this is a submission-readiness defect
   even though the hygiene scanner passes.
4. **SILLM4Rec remains uncited in `references.bib`.** If the method is named in
   Section 5.1, add a formal citation or remove/soften the mention until the
   full protocol inspection is done.
5. **`paper_tex/BUILD_NOTES.md` is stale.** It conflicts with the current
   acmsmall page count and embeds old hygiene/page-count blocks.

### Plausible Risks / Author Verification

- Office V3 sidecars: confirm whether the regular `user_records_path` is the
  intended final-epoch sidecar for the three runs whose
  `user_records_final_path` is missing.
- SILLM4Rec: direct full-paper inspection may reveal a closer protocol than the
  public repository implies; keep the "excluded pending direct protocol
  inspection" wording until resolved.
- Concurrent 2026 literature: the paper's no-comparative-claim fence remains
  necessary because several recent arXiv works report AR2023/SID-line numbers
  near the same benchmark neighborhood.

### Concrete Fixes To Make Next

1. Rewrite Appendix A.0 to split Office V1 and Office V3 cleanly:
   - V1 remains VOID under the original floor-check pre-registration.
   - V3 passed under the redesigned environment-matched pre-registration and is
     counted only under its frozen point-estimate wording.
2. Regenerate the release/deposit package after deciding the release boundary:
   include Office V3 and FIR-breadth prereg/results docs, relevant JSONs or
   manifest entries, and the live `paper_tex/PAPER_TORS.pdf`.
3. Repair Table 2 pagination by forcing the caption to travel with the table
   body or splitting the long table intentionally.
4. Add a SILLM4Rec BibTeX entry and inspect the ACM full text, or remove the
   named method from the manuscript until inspection is complete.
5. Refresh `paper_tex/BUILD_NOTES.md` so the page counts, hygiene output, and
   compile notes reflect the current 40-page review artifact and 41-page
   acmsmall preview.
6. Add an Office V3 sidecar erratum/manifest note for the three missing
   `user_records_final_path` fields.

### Open Questions

- Is `PAPER_SUBMISSION.pdf` still intended as a live deliverable despite being
  45 pages and carrying the same Appendix A.0 contradiction?
- Are Office V3 and FIR-breadth sidecars intended for DOI/deposit release, or
  are aggregate result JSONs plus embedded sidecar hashes the declared boundary?
- Should `RELEASE_MANIFEST.json` become the single source of truth for
  `office_v3` and `fir_breadth`, or is `_bestrec_run/hstu_results_manifest.json`
  intentionally the live empirical manifest?
- Should the acmsmall build be kept in the workflow if it is only a preview and
  currently diverges from the documented page count?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Re-run strict manuscript/artifact gate.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Re-run TORS PDF hygiene scan.
- [x] Extract PDF page counts and stale phrase locations.
- [x] Render and visually inspect the Table 2 pages.
- [x] Check release zip and manifest scope.
- [x] Check Office V3 final-sidecar metadata.
- [x] Fact-check comparator, dataset, and related-literature pressure points
      against external sources.
- [x] Refresh the current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair Appendix A.0 Office V1/V3 contradiction.
- [ ] Regenerate release/deposit package and manifest scope.
- [ ] Fix Table 2 pagination.
- [ ] Inspect/cite SILLM4Rec.
- [ ] Refresh `paper_tex/BUILD_NOTES.md`.

## Audit Run - 2026-07-14 04:57 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`.
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  (`Last run: 2026-07-14 03:57 Australia/Sydney`).
- Current run time: `2026-07-14T04:57:41.0221360+10:00`; main adjudicators
  completed at `2026-07-14 04:58 Australia/Sydney`.
- Live sources/artifacts inspected: `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/sections/*.tex`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/PAPER_TORS_acmsmall.pdf`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/references.bib`,
  `paper_tex/tables/table2.tex`, `paper_tex/tables/table0_novelty.tex`,
  `RELEASE_MANIFEST.json`, `_bestrec_run/hstu_results_manifest.json`,
  `_release/bestrec_deposit_v1.0.zip`, `DOI_DEPOSIT_INSTRUCTIONS.md`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, `OFFICE_V3_RESULTS.md`, and
  `FIR_BREADTH_RESULTS.md`.
- Working tree before this audit edit: tracked modifications in
  `PAPER_REVIEW_AUDIT.md` and, after the strict rebuild, `_bestrec_run/hstu_tables.json`;
  untracked files still include `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.

### Verdict

**The empirical core remains mechanically green, but the paper is still not
submission-ready.** The current run reproduced the strict gate, Office V3 gate,
FIR-breadth gate, and TORS hygiene pass. The top rejection risks are all
paper/release consistency risks:

1. Appendix A.0 still says the confirmed per-category claim is
   Musical_Instruments only and Office is not counted, contradicting the
   abstract and Section 5.2 Office V3 pass.
2. The deposit bundle and DOI instructions still describe the old pre-V3 /
   pre-FIR-breadth package, while the live artifact graph now requires
   `office_v3` and `fir_breadth`.
3. The rendered TORS artifact still strands Table 2's caption at the bottom of
   page 27 while the table body starts on page 28.
4. SILLM4Rec is now cautiously worded, but remains uncited in the manuscript and
   absent from `paper_tex/references.bib`.
5. `PAPER_DRAFT.md` retains an obsolete status paragraph saying Office stays
   VOID and V3 is pending; `PAPER_SUBMISSION.md` is cleaner but still inherits
   the Appendix A.0 contradiction.

### Commands And Evidence Checked

- `git log -1 --pretty='%h %s'`; `git status --short`
  - HEAD: `174b5a74`.
  - No source/manuscript changes since the prior run except the cumulative audit
    work and generated strict-build output.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS.
  - HSTU core-block parity exact.
  - `168` cells recomputed; `0` paper mismatches; `0` untraceable; all `14`
    declared claim families sourced.
  - Release manifest verification OK for `113` declared files.
  - MI V2 gate OK; legacy Office V1 descriptive/VOID check OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 04:58:27`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, 5/5 seeds above
    both `0.0279` and `0.0271`.
  - Frozen wording remains only a per-category point-estimate comparison, not
    paired/distributional superiority and not SOTA.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 04:58:27`.
  - `Industrial_and_Scientific`: mean paired delta `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: mean paired delta `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: 40 pages; `0` placeholder/forbidden-claim failures; 20
    informational SOTA/non-claim review hits.
- PDF text extraction with `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; stale Office phrases on page 41;
    `SILLM4Rec` on page 19.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; stale Office phrases on page 36;
    `SILLM4Rec` on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; stale Office phrases on
    page 37; Table 2 text on page 27.
- Visual PDF render with Poppler direct executable
  - The PATH wrapper `pdftoppm.cmd` points at a stale internal path, but the
    actual runtime binary works at
    `C:\Users\rayxc\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe`.
  - Rendered `paper_tex/PAPER_TORS.pdf` pages 27-28 to `tmp/pdfs/`.
  - Page 27: Table 2 caption alone at the bottom margin area.
  - Page 28: table body begins at the top of the next page.
- Deposit zip and manifest checks
  - `_release/bestrec_deposit_v1.0.zip` SHA256 remains
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`;
    48 entries.
  - Zip includes older `SOTA_CONFIRM_PREREG_OFFICE.md` and
    `SOTA_CONFIRM_OFFICE_RESULTS.md`, but not `PREREG_OFFICE_V3.md`,
    `OFFICE_V3_RESULTS.md`, `PREREG_FIR_BREADTH.md`,
    `FIR_BREADTH_RESULTS.md`, or `paper_tex/PAPER_TORS.pdf`.
  - `RELEASE_MANIFEST.json` still names result families
    `FIR_ablations`, `MI_gate_EXEC2`, `MI_gate_EXEC2_rest`, `MI_rebuild`,
    `OFFICE_gate`, and `OFFICE_idonly_floor`.
  - `_bestrec_run/hstu_results_manifest.json` required families include
    `office_v3` and `fir_breadth`, which is the live paper's current evidence
    boundary.
- Source search
  - `PAPER_SUBMISSION.md` line 621,
    `paper_tex/sections/appendix-a0.tex` line 4, and `PAPER_DRAFT.md` line 640
    still say "The confirmed per-category claim remains Musical_Instruments
    only; Office is not counted."
  - `PAPER_DRAFT.md` line 8 still says "Office stays VOID" and "V3 prereg ...
    outcome is pending."
  - `paper_tex/references.bib` still has no SILLM4Rec entry.
  - `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` claims the Office prose contradiction
    is fixed; live Appendix A.0 proves that claim false.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR still supports the comparator constants used by the paper:
  AR2023 5-core Video Games NDCG@10 `0.0760`, Office Products `0.0271`, and
  Musical Instruments `0.0406`, with dataset statistics matching the paper's
  parity framing. Source: https://arxiv.org/pdf/2504.10545
- Amazon Reviews 2023 official documentation supports the dataset framing:
  McAuley Lab 2023 release, `571.54M` reviews, interactions through September
  2023, richer metadata, and standard splits. Source:
  https://amazon-reviews-2023.github.io/
- ChronoSID is correctly treated as a separate SID-line protocol pressure point,
  not a directly interchangeable HSTU-BLaIR-family comparator: its own table
  reports MI statistics `57,359` users / `23,742` items / `490,522`
  interactions, which differ from this paper's HSTU-BLaIR-family MI statistics.
  Source: https://arxiv.org/html/2607.03918v1
- SILLM4Rec remains a citation/readiness risk rather than a proved comparator:
  the public repository describes image-to-text conversion, user-preference
  summaries, candidate product ranking tasks, and SFT/DPO training data; that
  supports the paper's non-interchangeability rationale, but a top-journal
  reviewer will expect a formal citation or direct protocol inspection. Source:
  https://github.com/MKC-Lab/SILLM4Rec ; ACM DOI:
  https://dl.acm.org/doi/10.1145/3743093.3771011

### Confirmed Problems

1. **Appendix A.0 contradicts the live Office V3 claim.** The main body now says
   V3 passed and is counted under frozen narrow wording; Appendix A.0 and the
   compiled PDFs still say Office is not counted.
2. **Deposit/DOI package is stale.** The package advertised as ready for DOI
   minting lacks the Office V3 and FIR-breadth evidence docs now needed to
   support the live manuscript.
3. **Table 2 pagination is reviewer-hostile.** Caption and table body split
   across pages in the TORS PDF; this is visually confirmed, not just inferred
   from text extraction.
4. **SILLM4Rec is named without a formal reference.** The sentence is cautious,
   but a named related work in a top-journal related-results paragraph should
   be in the bibliography.
5. **Response-file closure claims are unreliable.** The response file says the
   Office prose contradiction is fixed; the live source/PDF still contain it.

### Plausible Risks / Author Verification Needed

- The current §8 sidecar boundary may be acceptable, but the deposit/manifest
  boundary must say the same thing as the live paper. If local-only sidecars are
  only on request, the DOI package should still include the hash inventories and
  the V3/FIR result documents.
- `PAPER_SUBMISSION.pdf` remains 45 pages while TORS is 40 pages and acmsmall is
  41 pages. Author should decide which PDF is the actual submission/readable
  artifact and retire or relabel the others.
- The SILLM4Rec ACM full text should be inspected before freeze if access is
  available; otherwise cite the DOI/repository and explicitly state that the
  exclusion is based on accessible repository protocol evidence, not full-paper
  adjudication.
- The Poppler command wrappers in the bundled runtime are locally mispointed;
  direct binaries work. If build scripts ever depend on the wrappers, fix the
  path or call the `Library\bin` executables directly.

### Concrete Fixes To Make Next

1. Replace the stale Appendix A.0 sentence with V1-scoped language:
   "The V1 campaign remains counted in no claim; the redesigned V3 campaign is
   separately reported in §5.2 and counts only under its frozen per-category
   point-estimate wording."
2. Regenerate `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`, and
   `paper_tex/PAPER_TORS_acmsmall.pdf`; re-run `scan_pdf.py` and text-extract
   for "Office is not counted."
3. Repackage the release/deposit bundle to include `PREREG_OFFICE_V3.md`,
   `OFFICE_V3_RESULTS.md`, `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`,
   the current manifest(s), and the intended submission PDF; update
   `DOI_DEPOSIT_INSTRUCTIONS.md` with the new file count/hash.
4. Update `RELEASE_MANIFEST.json` or add a clear companion manifest that names
   the live `office_v3` and `fir_breadth` evidence families.
5. Fix Table 2 with a page-break/float strategy that keeps the caption with the
   table body, then visually re-render pages 27-28.
6. Add a SILLM4Rec bibliography entry and cite the Section 5.1 sentence, or
   remove the named work until direct protocol inspection is complete.

### Open Questions

- Should the DOI package include the TORS PDF, the 45-page reader PDF, or both?
- Is `RELEASE_MANIFEST.json` intended to be updated for every live claim family,
  or should `_bestrec_run/hstu_results_manifest.json` become the explicit
  submission-time claim-family manifest?
- Should local-only Office/FIR sidecars be deposited now as supplementary files,
  or is hash-embedded, on-request delivery the chosen policy until acceptance?
- Can the authors access the SILLM4Rec ACM PDF before freeze?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, release, and audit
      artifacts.
- [x] Re-run strict artifact rebuild.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Re-run TORS hygiene scan.
- [x] Search source and PDFs for stale Office wording.
- [x] Render and inspect Table 2 PDF pages.
- [x] Check release/deposit zip and manifest scope.
- [x] Fact-check current comparator/literature boundary against external
      HSTU-BLaIR, Amazon Reviews 2023, ChronoSID, and SILLM4Rec sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair Appendix A.0 Office V1/V3 wording.
- [ ] Regenerate PDFs after the wording fix.
- [ ] Refresh release/deposit package and DOI instructions.
- [ ] Fix Table 2 caption/body pagination.
- [ ] Add or remove formal SILLM4Rec citation before submission freeze.

## Audit Run - 2026-07-14 03:57 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`
  (`Last run: 2026-07-14 01:57 Australia/Sydney`).
- Current run time: `2026-07-14T03:57:20.9427523+10:00`; main adjudicator
  commands completed at `2026-07-14 03:58 Australia/Sydney`.
- Canonical/live artifacts inspected this run: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `paper_tex/sections/*.tex`,
  `paper_tex/tables/table2.tex`, `paper_tex/tables/table0_novelty.tex`,
  `paper_tex/references.bib`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/hygiene_scan_output.txt`, `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`,
  `CANONICAL_SUBMISSION.md`, `DOI_DEPOSIT_INSTRUCTIONS.md`,
  `RELEASE_MANIFEST.json`, `_release/bestrec_deposit_v1.0.zip`,
  `_bestrec_run/hstu_results_manifest.json`, `OFFICE_V3_RESULTS.md`, and
  `FIR_BREADTH_RESULTS.md`.
- Working tree before this audit edit: tracked modification only
  `PAPER_REVIEW_AUDIT.md`; untracked files unchanged from the prior run:
  `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Temporary visual renders were created under
  `tmp/hourly-strict-paper-audit-20260714-0357/`, inspected, and then removed.

### Verdict

**No new numerical/provenance failure appeared, but the manuscript remains
not submission-ready for a top journal.** The strict artifact gate, Office V3
adjudicator, FIR-breadth adjudicator, and TORS hygiene scan all pass freshly.
The rejection risk is still in consistency, packaging, and reviewer-facing
polish:

1. The live source and all PDFs still contain Appendix A.0 wording saying the
   confirmed per-category claim is Musical_Instruments only and Office is not
   counted, contradicting the main-body Office V3 pass.
2. The advertised deposit bundle and DOI instructions still predate Office V3
   and FIR-breadth, even though the live paper now counts those evidence layers.
3. Table 2 remains visually broken: the caption is stranded at the bottom of
   TORS page 27 and the table body starts on page 28.
4. `paper_tex/BUILD_NOTES.md` still asserts a 40-page acmsmall production
   preview, while the current `PAPER_TORS_acmsmall.pdf` has 41 pages.
5. The SILLM4Rec exclusion is better worded than in older drafts, but still
   lacks a formal citation/BibTeX entry despite appearing in the live
   related-results paragraph.

### Commands And Evidence Checked

- `Get-Date -Format o`
  - Current run time: `2026-07-14T03:57:20.9427523+10:00`.
- `git log -1 --pretty='%h %s'`; `git status --short`
  - HEAD unchanged from the prior audit: `174b5a74`.
  - No tracked source/manuscript changes other than the cumulative audit file.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS.
  - HSTU core-block parity exact.
  - `168` cells recomputed; `0` paper mismatches; `0` untraceable; all `14`
    declared claim families sourced.
  - Release manifest verification OK for `113` declared files.
  - MI V2 gate OK; legacy Office V1 descriptive/VOID check OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 03:58:16`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, 5/5 seeds above
    both `0.0279` and `0.0271`.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 03:58:16`.
  - `Industrial_and_Scientific`: mean paired delta `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: mean paired delta `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: 40 pages; `0` placeholder/forbidden-claim failures; 20
    informational SOTA/non-claim review hits.
- PDF text extraction with `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; stale Office phrases on page 41;
    `SILLM4Rec` on page 19.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; stale Office phrases on page 36;
    `SILLM4Rec` on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; stale Office phrases on
    page 37; `SILLM4Rec` on page 18.
- Visual PDF render with PyMuPDF and manual image inspection
  - `paper_tex/PAPER_TORS.pdf` page 27: Table 2 caption appears alone at the
    bottom of the page.
  - `paper_tex/PAPER_TORS.pdf` page 28: Table 2 body starts at the top of the
    next page.
- Deposit zip inspection
  - `_release/bestrec_deposit_v1.0.zip` exists, 48 entries, SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`.
  - It contains `PAPER_SUBMISSION.md` and `PAPER_SUBMISSION.pdf`.
  - It does not contain `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
    `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`, or
    `paper_tex/PAPER_TORS.pdf`.
- Manifest comparison
  - `RELEASE_MANIFEST.json` release: `v0.9-audit-evidence`.
  - `RELEASE_MANIFEST.json` result families remain only
    `FIR_ablations`, `MI_gate_EXEC2`, `MI_gate_EXEC2_rest`, `MI_rebuild`,
    `OFFICE_gate`, and `OFFICE_idonly_floor`.
  - `_bestrec_run/hstu_results_manifest.json` required families include the
    current live families `office_v3` and `fir_breadth`.
- Source search
  - `PAPER_SUBMISSION.md` line 621 and
    `paper_tex/sections/appendix-a0.tex` line 4 still say the confirmed
    per-category claim remains Musical_Instruments only and Office is not
    counted.
  - `PAPER_DRAFT.md` line 8 still says Office stays VOID and V3 is pending.
  - `paper_tex/references.bib` has entries for Latte, ChronoSID, ReSID, GrIT,
    WPGRec, Augment-or-Not, DiffuReason, FMLP-Rec, BSARec, Caser, NextItNet,
    TIGER, and LIGER, but no SILLM4Rec entry.

### External Fact-Check / Novelty Notes

- Amazon Reviews 2023 official documentation supports the dataset framing:
  collected by McAuley Lab, `571.54M` reviews, interactions through September
  2023, richer metadata, and standard splitting. Source:
  https://amazon-reviews-2023.github.io/
- HSTU-BLaIR v3 supports the comparator constants and dataset statistics used
  as external references: Video Games NDCG@10 `0.0760`, Office Products
  `0.0271`, Musical Instruments `0.0406`; statistics include Video Games
  `25,612` items / `94,762` users / `814,585` interactions, Office Products
  `77,551` / `223,308` / `1,800,877`, and Musical Instruments `24,587` /
  `57,439` / `511,835`. Source: https://arxiv.org/html/2504.10545v3
- FMLP-Rec and BSARec confirm that filtering sequential representations and
  frequency-domain/oversmoothing motivation are prior art, not novel here.
  Sources: https://arxiv.org/abs/2202.13556 and
  https://arxiv.org/abs/2312.10325
- Caser confirms convolutional sequence modeling is old prior art, reinforcing
  that the paper must not sell the FIR layer as a new convolutional sequence
  architecture. Source: https://arxiv.org/abs/1809.07426
- Latte remains a close concurrent pressure point: it reports AR2023
  Instruments/Scientific/Games LLOO NDCG@10 values including Instruments
  `0.0331` and Games `0.0515`. The paper's "point-estimate observation, not a
  comparative claim" wording remains necessary. Source:
  https://arxiv.org/pdf/2605.06331
- GrIT also overlaps the AR2023 sequential-recommendation space and explicitly
  discusses FMLP-Rec, Caser, and BSARec-style prior art. Its presence reinforces
  the need for a final literature sweep and cautious priority wording. Source:
  https://arxiv.org/html/2602.19728v1
- ChronoSID frames a 2026 SID-based generative-recommendation line on Amazon
  2023 subsets and reports improvements over ReSID; it uses a distinct SID
  protocol/universe, so the paper's non-interchangeability caveat is
  appropriate. Source: https://arxiv.org/html/2607.03918v1
- SILLM4Rec's public repository documents AR2023 5-core data preparation,
  candidate product ranking tasks, and SFT/DPO training data. That supports
  exclusion from full-catalog LLOO comparisons, but the paper needs a formal
  citation and/or direct ACM PDF inspection. Sources:
  https://github.com/MKC-Lab/SILLM4Rec and
  https://dl.acm.org/doi/10.1145/3743093.3771011

### Confirmed Problems

1. **Appendix A.0 contradiction persists in source and PDFs.** The Appendix A.0
   Office V1 text says Office is not counted, while the abstract/body count
   Office V3 as a passed second pre-registered per-category point-estimate
   comparison.
2. **Stale draft status persists.** `PAPER_DRAFT.md` line 8 still says Office
   V3 is pending.
3. **Response-file closure claim is false in the live workspace.**
   `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` claims stale Office sites were fixed,
   but current `rg` and PDF extraction disprove that.
4. **Deposit/release layer is stale.** The zip and DOI instructions still point
   to `v1.0-deposit` and exclude Office V3/FIR-breadth prereg/results files.
5. **Release-manifest scope is behind the current claim graph.**
   `RELEASE_MANIFEST.json` lacks `office_v3` and `fir_breadth` result
   families, while the strict HSTU manifest requires them.
6. **Table 2 layout is visibly unacceptable.** A top-journal PDF should not
   strand a dense table caption on one page and the table body on the next.
7. **SILLM4Rec mention is not properly cited.** The manuscript discusses it in
   Section 5.1, but `references.bib` has no SILLM4Rec entry and the text has no
   citation command.
8. **Build notes remain unreliable as current-state documentation.**
   `PAPER_TORS_acmsmall.pdf` is 41 pages, while `BUILD_NOTES.md` still says the
   production preview is 40 pages/current builds are 40/40.

### Plausible Risks / Author Verification Needed

- **SILLM4Rec final protocol boundary:** accessible repository evidence supports
  non-comparability, but a reviewer may not accept an exclusion of an ACM paper
  without a direct paper citation and a concise protocol note.
- **Deposit policy:** Section 8 says local-only sidecars can be provided later;
  that is defensible only if the public deposit bundle clearly contains the
  tracked aggregate evidence for every counted printed claim.
- **Generated-source boundary:** `paper_tex/sections/abstract.tex` says it is
  generated from `PAPER_SUBMISSION.md`, but both Markdown and TeX contain stale
  Appendix A.0 text. Fixing only one layer risks reintroducing the contradiction.

### Confirmed Non-Problems This Run

- No strict artifact-gate failure, empirical-cell mismatch, untraceable printed
  cell, Office V3 adjudicator failure, FIR-breadth adjudicator failure, or PDF
  hygiene forbidden-claim failure was observed.
- The current novelty boundary around the FIR layer is scientifically safer
  than earlier drafts: the paper explicitly cites FMLP-Rec/BSARec, Caser,
  NextItNet, and WPGRec-like frequency/wavelet prior art, and grades the FIR
  contribution as incremental.
- The Section 8 sidecar boundary is clearer than earlier audits: it now
  distinguishes tracked aggregate evidence from local-only per-user sidecars.
  The remaining issue is that the external deposit bundle does not match this
  live contract.

### Concrete Fixes To Make Next

1. Rewrite Appendix A.0 everywhere so it is explicitly Office V1-scoped:
   Office V1 remains VOID; Office V3 is separate, passed, and counted only
   under its frozen point-estimate wording.
2. Update or remove `PAPER_DRAFT.md` line 8 so no live draft says Office V3 is
   pending.
3. Add a dated correction to `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` acknowledging
   that its "zero stale occurrences" statement was false.
4. Rebuild the deposit bundle after Office V3/FIR-breadth, include the current
   manuscript/PDF and prereg/results docs, and update
   `DOI_DEPOSIT_INSTRUCTIONS.md`.
5. Decide whether `RELEASE_MANIFEST.json` should add `office_v3` and
   `fir_breadth` families, or explicitly state that
   `_bestrec_run/hstu_results_manifest.json` is now the live claim-family
   source of truth.
6. Fix Table 2 as a float or otherwise keep the caption and body together, then
   rebuild and visually inspect pages 27-28.
7. Add a SILLM4Rec BibTeX entry and cite it in Section 5.1, or remove the named
   paper until the ACM full text is inspected.
8. Refresh `paper_tex/BUILD_NOTES.md` so current page counts and hygiene output
   match the files on disk.

### Open Questions

- Should the next archival bundle be `v1.0.1-deposit`, or is the Office V3 /
  FIR-breadth integration substantial enough to warrant a new release series?
- Is `RELEASE_MANIFEST.json` intentionally frozen to older release assets, or
  should it track every current counted claim?
- Can the authors access the SILLM4Rec ACM PDF before freeze, or should the
  paper rely only on the public repository/DOI metadata and say so explicitly?
- Is `PAPER_DRAFT.md` still a live manuscript source, or should it be marked
  historical to avoid review/package confusion?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Search manuscript/TeX/PDFs for stale Office V3 pending/no-claim wording.
- [x] Re-run strict artifact gate.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Check compiled PDF page counts and hygiene output.
- [x] Inspect Table 2 page split visually.
- [x] Inspect release/deposit zip contents and manifest-family scope.
- [x] Fact-check current dataset/comparator/novelty claims against AR2023,
      HSTU-BLaIR, FMLP-Rec/BSARec, Caser, Latte, GrIT, ChronoSID, and SILLM4Rec
      sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair Office V1/V3 consistency in Appendix A.0 and generated PDFs.
- [ ] Rebuild/reissue deposit bundle and update DOI instructions.
- [ ] Fix Table 2 caption/body split.
- [ ] Add or remove the SILLM4Rec citation before submission.
- [ ] Refresh `paper_tex/BUILD_NOTES.md`.

## Audit Run - 2026-07-14 01:57 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory read:
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`.
- Prior audit section carried forward: `2026-07-14 01:00 Australia/Sydney`.
- Canonical/live artifacts inspected this run: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `paper_tex/sections/*.tex`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/PAPER_TORS_acmsmall.pdf`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `paper_tex/tables/table2.tex`, `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`,
  `CANONICAL_SUBMISSION.md`, `DOI_DEPOSIT_INSTRUCTIONS.md`,
  `RELEASE_MANIFEST.json`, `_release/bestrec_deposit_v1.0.zip`,
  `_bestrec_run/hstu_results_manifest.json`, `OFFICE_V3_RESULTS.md`, and
  `FIR_BREADTH_RESULTS.md`.
- Working tree before this audit edit: tracked modification only
  `PAPER_REVIEW_AUDIT.md`; untracked files:
  `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.
- Temporary visual renders were created under
  `tmp/pdfs/hourly-strict-paper-audit-20260714-0157/`, inspected, and then
  removed.

### Verdict

**No new numerical failure appeared, but the paper is still not ready for a
top-journal submission.** The strict artifact gate, Office V3 adjudicator, and
FIR-breadth adjudicator all pass freshly. The rejection risk is instead
internal consistency, release packaging, and production polish:

1. Appendix A.0 still tells readers that only Musical_Instruments is confirmed
   and that Office is not counted, while the abstract, Section 5.2, Section
   6.4/6.5, and `CANONICAL_SUBMISSION.md` count Office V3 as a passed second
   per-category comparison.
2. `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` claims the Office inconsistency was
   fixed everywhere and that zero stale occurrences remain. That response is
   contradicted by current `rg`, PDF text extraction, and visual rendering.
3. The deposit instructions and `_release/bestrec_deposit_v1.0.zip` still
   predate Office V3 and FIR-breadth.
4. The TORS PDF still has a visible Table 2 caption/body split across pages 27
   and 28, and `paper_tex/BUILD_NOTES.md` still mixes current statements with
   old 35/36-page and 40/40 claims even though acmsmall is currently 41 pages.

### Commands And Evidence Checked

- `Get-Date -Format "yyyy-MM-dd HH:mm:ss K"`
  - Current run time: `2026-07-14 01:57:32 +10:00`.
- `git status --short`; `git rev-parse --abbrev-ref HEAD`;
  `git rev-parse --short HEAD`; `git log -1 --pretty=%s`
  - Branch/HEAD as above.
  - No tracked source/manuscript changes since the last audit other than the
    existing `PAPER_REVIEW_AUDIT.md` modification.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS.
  - HSTU core-block parity exact.
  - `168` cells recomputed; `0` paper mismatches; `0` untraceable; all `14`
    declared claim families sourced.
  - Release manifest verification OK for `113` declared files.
  - MI V2 gate OK; legacy Office V1 descriptive/VOID check OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 01:57:33`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, 5/5 seeds above
    both `0.0279` and `0.0271`.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 01:57:33`.
  - `Industrial_and_Scientific`: mean paired delta `+0.00240`, 95% CI
    `[+0.00183,+0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: mean paired delta `+0.00566`, 95% CI
    `[+0.00493,+0.00639]`, 5/5 positive.
- `_bestrec_run/hstu_results_manifest.json` structured check
  - Required families include `office_v3` and `fir_breadth`.
  - This confirms the strict internal artifact graph sees the new evidence even
    though the external/deposit bundle is stale.
- `rg "Office stays VOID|outcome is pending|Office is not counted|confirmed per-category claim remains|..."`
  - `PAPER_DRAFT.md` line 8 still says Office stays VOID and V3 is pending.
  - `PAPER_SUBMISSION.md` line 621 and
    `paper_tex/sections/appendix-a0.tex` line 4 still say the confirmed
    per-category claim is Musical_Instruments only and Office is not counted.
  - `PAPER_SUBMISSION.md` line 334 and
    `paper_tex/sections/05-results.tex` line 90 say Office V3 passed and is
    counted under its frozen point-estimate wording.
  - `PAPER_SUBMISSION.md` line 526 and
    `paper_tex/sections/06-discussion.tex` line 81 correctly distinguish V1
    VOID from V3 counted pass.
- PDF text extraction with `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; stale Office phrases occur on page 41;
    `SILLM4Rec` occurs on page 19.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; stale Office phrases occur on page
    36; `SILLM4Rec` occurs on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; stale Office phrases occur
    on page 37; `SILLM4Rec` occurs on page 18.
- Visual PDF rendering with PyMuPDF and manual image inspection
  - `paper_tex/PAPER_TORS.pdf` page 27: Table 2 caption appears alone at the
    bottom of the page.
  - `paper_tex/PAPER_TORS.pdf` page 28: the Table 2 body starts at the top of
    the next page, separated from the caption.
  - `paper_tex/PAPER_TORS.pdf` page 36 and
    `paper_tex/PAPER_TORS_acmsmall.pdf` page 37 visibly contain the stale
    Appendix A.0 Office wording.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: 40 pages; `0` placeholder/forbidden-claim failures; 20 informational
    review hits for SOTA/non-claim wording.
  - This scanner is useful but insufficient: it does not detect the Office
    V1/V3 semantic contradiction or the caption split.
- Deposit zip inspection
  - `_release/bestrec_deposit_v1.0.zip` SHA256:
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`.
  - 48 entries, all under `bestrec_deposit_v1.0/`.
  - Contains old `PAPER_SUBMISSION.md`, old `PAPER_SUBMISSION.pdf`,
    `SOTA_CONFIRM_PREREG_OFFICE.md`, and `SOTA_CONFIRM_OFFICE_RESULTS.md`.
  - Does not contain `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
    `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`, or
    `paper_tex/PAPER_TORS.pdf`.
- `RELEASE_MANIFEST.json` structured check
  - `result_families` are still only `FIR_ablations`, `MI_gate_EXEC2`,
    `MI_gate_EXEC2_rest`, `MI_rebuild`, `OFFICE_gate`, and
    `OFFICE_idonly_floor`.
  - No Office V3 or FIR-breadth family appears in that release-manifest layer,
    even though strict submission gating now uses `_bestrec_run/hstu_results_manifest.json`.
- `paper_tex/BUILD_NOTES.md`
  - Header says review artifact 40 pages and production preview 40 pages, but
    current `PAPER_TORS_acmsmall.pdf` is 41 pages.
  - Later compile-status sections still preserve old 35/36-page blocks and an
    embedded old 35-page hygiene output. Some are labeled historical, but the
    file now mixes historical and current-state claims in a way that will confuse
    a reviewer or release maintainer.

### External Fact-Check / Novelty Notes

- Amazon Reviews 2023 official documentation supports the dataset framing:
  collected by McAuley Lab in 2023, 571.54M reviews, newer interactions through
  September 2023, richer metadata, and standard splitting.
  Source: https://amazon-reviews-2023.github.io/
- HSTU-BLaIR's public repository supports the comparator constants used in the
  manuscript: Video Games HSTU-BLaIR NDCG@10 `0.0760`, Office Products
  `0.0271`, and Musical Instruments `0.0406`, on Amazon Reviews 2023 subsets.
  Source: https://github.com/snapfinger/HSTU-BLaIR
- Latte is a close concurrent pressure point: it evaluates Instruments,
  Scientific, and Games from Amazon Reviews 2023 with leave-one-out splitting;
  Table 1 reports Latte NDCG@10 `0.0331` on Instrument and `0.0515` on Game.
  The manuscript's "point-estimate observation, not a claim" wording remains
  necessary. Source: https://arxiv.org/html/2605.06331v1
- GrIT remains another overlapping AR2023 pressure point: it reports Video Games
  `94,762` users, `25,612` items, `814,586` interactions and Video Games
  NDCG@10 `0.0588`. This supports inclusion in related work, not direct
  superiority. Source: https://arxiv.org/html/2602.19728v1
- ReSID/ChronoSID continue to justify the manuscript's non-interchangeability
  caveat for the SID line. ReSID uses a SID-based generative setup and a
  filtered universe; ChronoSID reports output-level MI NDCG@10 `0.0345` vs
  ReSID `0.0325`. Sources:
  https://arxiv.org/html/2602.02338v1 and
  https://arxiv.org/html/2607.03918v1
- SILLM4Rec evidence now supports the paper's exclusion rationale better than
  earlier audits: the public repo instructs users to create candidate product
  ranking tasks and generate SFT/DPO training data. ACM/search metadata also
  describes it as a re-ranking task. This supports non-interchangeability with
  full-catalog LLOO, but a final submission should either cite this concrete
  basis without vague "pending" language or archive a direct full-paper
  inspection. Sources: https://github.com/MKC-Lab/SILLM4Rec and
  https://dl.acm.org/doi/10.1145/3743093.3771011

### Confirmed Problems

1. **Live source/PDF contradiction:** Appendix A.0 still makes an unscoped
   "Office is not counted" claim while the body counts Office V3.
2. **Stale draft status:** `PAPER_DRAFT.md` line 8 still says Office stays VOID
   and V3 is pending.
3. **Audit-response contradiction:** `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`
   asserts that all stale Office sites were fixed and zero occurrences remain;
   current source and PDFs refute that assertion.
4. **Stale deposit package:** the advertised `v1.0-deposit` zip and DOI
   instructions do not include Office V3 or FIR-breadth documentation.
5. **Release-manifest scope mismatch:** the strict submission manifest includes
   `office_v3` and `fir_breadth`, but `RELEASE_MANIFEST.json` still exposes the
   older release-evidence families.
6. **Visible PDF layout defect:** Table 2 caption and body are split across
   pages 27 and 28 in `paper_tex/PAPER_TORS.pdf`.
7. **Build notes are not reliable as current-state documentation:** acmsmall is
   41 pages, while `BUILD_NOTES.md` still says 40/40 in current-state prose and
   carries older 35/36-page blocks.

### Plausible Risks / Author Verification Needed

- **Deposit policy vs reviewer expectation:** Section 8 says local per-user
  sidecars can be supplied on request and later deposited. That is defensible
  for top-journal review only if the public deposit bundle clearly contains the
  tracked aggregate evidence for every printed claim now being counted.
- **SILLM4Rec final wording:** the current sentence is defensible but awkward:
  it says "pending direct protocol inspection" while also stating the repository
  evidence that supports exclusion. Either inspect the ACM full paper directly
  or make the repo/ACM re-ranking evidence the explicit final rationale.
- **Generated TeX source of truth:** if Appendix A.0 is generated from markdown,
  fixing only TeX or only markdown will recreate the contradiction. Fix the
  canonical source and regenerate all downstream PDFs.

### Confirmed Non-Problems This Run

- No strict artifact-gate failure, empirical-cell mismatch, untraceable printed
  cell, Office V3 adjudicator failure, or FIR-breadth adjudicator failure was
  observed.
- The current main-body Office V3 wording is narrow where it is present:
  point-estimate comparison against published `0.0271` and local regeneration
  `0.0279`, no paired/distributional superiority, and no SOTA claim.
- The FIR-breadth claim remains correctly scoped as an internal paired
  filter-vs-no-filter contrast, not a comparator result.
- The 2026 related-work paragraph remains cautious enough on direct claims,
  provided it keeps the "no comparative claim against concurrent arXiv-only
  work" language.

### Concrete Fixes To Make Next

1. Rewrite Appendix A.0 in `PAPER_SUBMISSION.md`,
   `paper_tex/sections/appendix-a0.tex`, and the generated PDFs so the stale
   sentence is V1-scoped: V1 remains VOID; V3 is separate, passed, and reported
   in Section 5.2.
2. Update or remove `PAPER_DRAFT.md` line 8 so the draft no longer says Office
   V3 is pending.
3. Add a short erratum to `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` acknowledging that
   its "zero stale occurrences" claim was false in the live workspace.
4. Rebuild and rename the deposit bundle after Office V3/FIR-breadth, then
   update `DOI_DEPOSIT_INSTRUCTIONS.md` and `CANONICAL_SUBMISSION.md` to point
   to the new bundle.
5. Decide whether `RELEASE_MANIFEST.json` should include first-class
   `office_v3` and `fir_breadth` families, or explicitly document that
   `_bestrec_run/hstu_results_manifest.json` is the current claim-family source
   of truth.
6. Fix Table 2 so its caption and table body stay together, then rebuild and
   visually inspect at least the affected pages.
7. Refresh `paper_tex/BUILD_NOTES.md` so current page counts and hygiene output
   are current and historical blocks are clearly separated.
8. Finalize the SILLM4Rec exclusion by either inspecting the ACM full paper or
   revising the sentence to rely on the observed re-ranking/SFT-DPO evidence.

### Open Questions

- Should the next archival bundle be `v1.0.1-deposit`, or should the Office V3
  and FIR-breadth integration become a new release series?
- Is `RELEASE_MANIFEST.json` intentionally an older `v0.9-audit-evidence`
  release manifest, or should it track every current counted claim?
- Should `PAPER_DRAFT.md` remain a historical draft, or is it still a live
  deliverable that must be kept internally consistent?
- Does the venue target tolerate the 41-page acmsmall preview if documented, or
  does it need layout compaction?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDFs, result files, release manifest,
      deposit zip, response file, and build notes.
- [x] Re-run strict manuscript/artifact gate.
- [x] Re-run Office V3 adjudicator.
- [x] Re-run FIR-breadth adjudicator.
- [x] Check strict claim-family manifest for `office_v3` and `fir_breadth`.
- [x] Search live manuscript sources for stale Office wording.
- [x] Extract PDF text and page counts from all compiled deliverables.
- [x] Render and visually inspect affected PDF pages.
- [x] Inspect deposit zip contents and release-manifest family scope.
- [x] Fact-check comparator and close-literature boundaries against external
      sources.
- [x] Refresh the current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Scope Appendix A.0 to V1 and regenerate all PDFs.
- [ ] Remove stale `PAPER_DRAFT.md` V3-pending status.
- [ ] Correct or annotate the false response-file closure claim.
- [ ] Rebuild current deposit/release bundle.
- [ ] Fix Table 2 caption/table placement.
- [ ] Refresh `paper_tex/BUILD_NOTES.md`.
- [ ] Finalize SILLM4Rec full-paper inspection or rationale wording.

## Audit Run - 2026-07-14 01:00 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory: `$env:CODEX_HOME` was unset in this shell, so this run read
  the fallback memory path
  `C:\Users\rayxc\.codex\automations\hourly-strict-paper-audit\memory.md`.
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `paper_tex/sections/*.tex`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/PAPER_TORS_acmsmall.pdf`,
  `paper_tex/references.bib`, `CANONICAL_SUBMISSION.md`,
  `DOI_DEPOSIT_INSTRUCTIONS.md`, `RELEASE_MANIFEST.json`,
  `_release/bestrec_deposit_v1.0.zip`, `PREREG_OFFICE_V3.md`,
  `OFFICE_V3_RESULTS.md`, `PREREG_FIR_BREADTH.md`,
  `FIR_BREADTH_RESULTS.md`, and current Office V3 / FIR-breadth result JSONs.
- Working tree state before this audit edit: the only tracked modification was
  `PAPER_REVIEW_AUDIT.md`; untracked files remained
  `_bestrec_run/impact_program.DONE`, `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`. This audit
  also generated temporary visual-QA renders under
  `tmp/pdfs/hourly-strict-paper-audit/`.

### Verdict

**The empirical gates are still green, but the manuscript remains not
submission-ready for top-journal review.** The blocking risk is no longer the
aggregate result computation; it is consistency and presentation. The advertised
deposit bundle predates Office V3 and FIR-breadth, Appendix A.0 and rendered
PDFs still say Office is not counted despite the current Office V3 pass, and a
fresh visual render found a table/caption split that will look sloppy to a
reviewer.

The SILLM4Rec issue improved: accessible ACM/search and repository evidence now
supports treating it as a candidate re-ranking / SFT-DPO workflow rather than a
full-catalog LLOO protocol. However, the paper's "pending direct protocol
inspection" wording should be made more precise or backed by an archived
full-paper inspection.

### Commands And Evidence Checked

- `Get-Date -Format "yyyy-MM-dd HH:mm:ss K"`
  - Current run time: `2026-07-14 01:00:30 +10:00`.
- `git status --short`; `git rev-parse --abbrev-ref HEAD`;
  `git rev-parse --short HEAD`; `git log -1 --pretty=%s`
  - Branch/HEAD unchanged from prior audit.
  - Same tracked/untracked state as above before this audit edit.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS at this run.
  - HSTU core-block parity exact; `168` cells recomputed; `0` paper
    mismatches; `0` untraceable; all `14` declared claim families sourced;
    release manifest verification OK for `113` files; MI V2 gate OK; legacy
    Office V1 descriptive/VOID adjudication OK.
- `uv --project _bestrec_run run python _bestrec_run\update_release_manifest.py --verify`
  - PASS: `113` files verified, `0` release-asset files not local.
  - But structured inspection confirms `result_families` still only lists
    `FIR_ablations`, `MI_gate_EXEC2`, `MI_gate_EXEC2_rest`, `MI_rebuild`,
    `OFFICE_gate`, and `OFFICE_idonly_floor`.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-14 00:56:48`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, 5/5 seeds above
    both `0.0279` and `0.0271`.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-14 00:56:48`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, sd `0.00046`, 95% CI
    `[+0.00183, +0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, sd `0.00059`, 95% CI
    `[+0.00493, +0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: `PAPER_TORS.pdf` has 40 pages, 0 placeholder/forbidden-claim
    failures, and 20 informational SOTA/negated-claim review hits.
- PDF text extraction with `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages; stale phrases `Office is not counted`
    and `confirmed per-category claim remains` occur on page 41; `SILLM4Rec`
    occurs on page 19.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; stale Office phrases occur on page
    36; `SILLM4Rec` occurs on page 18.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; stale Office phrases occur
    on page 37; `SILLM4Rec` occurs on page 18.
- Visual PDF rendering with PyMuPDF
  - Rendered pages 1, 18, 19, 27, 28, 31, and 36 from
    `paper_tex/PAPER_TORS.pdf`.
  - Confirmed page 36 visibly contains the stale Appendix A.0 sentence
    "Office is not counted."
  - Confirmed Table 2 caption starts alone at the bottom of page 27, while the
    table body begins at the top of page 28 without the caption beside it.
  - No clipping or unreadable glyphs observed on the rendered sample pages.
- Deposit zip inspection with `zipfile`
  - `_release/bestrec_deposit_v1.0.zip`: SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`, 48
    entries.
  - Contains `PAPER_SUBMISSION.md` and `PAPER_SUBMISSION.pdf`.
  - Contains no `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
    `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`, or
    `paper_tex/PAPER_TORS.pdf`.
- `rg "Office stays VOID|outcome is pending|Office is not counted|confirmed per-category claim remains" ...`
  - `PAPER_DRAFT.md` line 8 still says "Office stays VOID" and V3 outcome is
    pending.
  - `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
    `paper_tex/sections/appendix-a0.tex` still contain the stale V1-era
    "Office is not counted" sentence.
- `rg "PREREG_OFFICE_V3|OFFICE_V3_RESULTS|PREREG_FIR_BREADTH|FIR_BREADTH_RESULTS|v1.0-deposit|bestrec_deposit|46-file" ...`
  - `CANONICAL_SUBMISSION.md` now names Office V3 and FIR-breadth evidence.
  - `DOI_DEPOSIT_INSTRUCTIONS.md` still advertises the old 46-file
    `v1.0-deposit` bundle and points Zenodo upload instructions to
    `bestrec_deposit_v1.0.zip`.

### External Fact-Check / Novelty Notes

- Amazon Reviews 2023 official documentation supports the dataset framing:
  collected by McAuley Lab in 2023, `571.54M` reviews, newer interactions
  through September 2023, richer metadata, and standard splitting. Source:
  https://amazon-reviews-2023.github.io/
- HSTU-BLaIR's public repository and arXiv page support the comparator constants
  used here: Video Games HSTU-BLaIR NDCG@10 `0.0760`, Office Products `0.0271`,
  and Musical Instruments `0.0406`, on Amazon Reviews 2023 subsets. Sources:
  https://github.com/snapfinger/HSTU-BLaIR and
  https://arxiv.org/html/2504.10545v3
- Latte remains a close concurrent AR2023 5-core LLOO pressure point: it reports
  experiments on Instruments/Scientific/Games and NDCG@10 values including
  Instruments `0.0331` and Games `0.0515`. Source:
  https://arxiv.org/html/2605.06331v1
- GrIT is another AR2023 pressure point on overlapping categories: it uses the
  full item set for evaluation, 5-core filtering, leave-one-out, and reports
  Video Games NDCG@10 `0.0588`. Source:
  https://arxiv.org/html/2602.19728v1
- ReSID and ChronoSID continue to support the manuscript's "SID-line filtered
  universe differs" caveat: ReSID reports Musical Instruments `57,359` users /
  `23,742` items / `490,522` interactions, and ChronoSID reports ReSID-to-
  ChronoSID output-level MI N@10 `0.0325` to `0.0345`. Sources:
  https://arxiv.org/html/2602.02338v1 and
  https://arxiv.org/html/2607.03918v1
- SILLM4Rec is now less ambiguous but still needs citation discipline. The ACM
  DOI/search result identifies the paper as MMAsia 2025 and says it focuses on
  re-ranking tasks where LLMs sort candidate items; DBLP lists it as MMAsia
  2025 paper `65:1-65:8`; the public repository instructs users to create
  candidate product ranking tasks and generate SFT/DPO training data. This is
  evidence for non-interchangeability with full-catalog LLOO, not evidence that
  it is irrelevant. Sources:
  https://dl.acm.org/doi/10.1145/3743093.3771011,
  https://dblp.org/rec/conf/mmasia/WuQL0025, and
  https://github.com/MKC-Lab/SILLM4Rec

### Confirmed Problems

1. **The Appendix A.0 Office contradiction is still live in source and PDFs.**
   The V1 appendix can remain VOID, but its broad sentence must be scoped to the
   V1 campaign because the body now counts Office V3.
2. **`PAPER_DRAFT.md` remains stale at the status-line level.** It says Office
   stays VOID and V3 is pending, contradicting the current Office V3 pass.
3. **The DOI/deposit bundle is stale.** A reviewer following the current DOI
   instructions will not receive the Office V3 or FIR-breadth evidence files.
4. **`paper_tex/BUILD_NOTES.md` is stale.** It says acmsmall is 40 pages and
   current builds are 40/40 while the live acmsmall PDF is 41 pages.
5. **Table 2 has a visible caption/table split.** The caption is stranded at the
   bottom of TORS page 27 and the table body starts on page 28; this is a
   production-readiness defect even if not a scientific error.

### Plausible Risks / Author Verification Needed

- **SILLM4Rec wording:** the current "pending direct protocol inspection" caveat
  is conservative, but now that accessible evidence says re-ranking/SFT-DPO, the
  authors should either cite that concrete basis or archive the inspected ACM
  PDF. Do not leave the exclusion as vague "metadata did not establish
  comparability."
- **Release boundary:** the paper says tracked artifacts are the reproducibility
  contract and local per-user sidecars are supplementary. That is defensible only
  if the deposit/release package is updated or the cover letter explicitly
  explains the tracked-vs-supplementary boundary.
- **Layout polish:** sampled rendered pages are legible, but only selected pages
  were visually inspected this run. A full PDF visual pass should follow the
  caption split fix.

### Confirmed Non-Problems This Run

- No strict artifact-gate failure, table-cell mismatch, untraceable printed
  cell, Office V3 adjudicator failure, FIR-breadth adjudicator failure, or TORS
  hygiene-scan failure was observed.
- The body's Office V3 claim wording remains properly narrow where it is current:
  a per-category point-estimate comparison against published `0.0271` and local
  regeneration `0.0279`, not paired/distributional superiority or SOTA.
- The concurrent-literature paragraph remains cautious enough: it records
  point-estimate observations and non-comparability caveats rather than claiming
  superiority over 2026 arXiv-only work.

### Concrete Fixes To Make Next

1. Scope Appendix A.0's broad sentence to V1: "under the V1 pre-registration, no
   claim counts the V1 campaign; the separate V3 redesign passed and is reported
   in Section 5.2."
2. Update or delete `PAPER_DRAFT.md` line 8 so it no longer says Office V3 is
   pending.
3. Rebuild the DOI/deposit bundle after Office V3 and FIR-breadth; update
   `DOI_DEPOSIT_INSTRUCTIONS.md` and release notes to point to the new bundle.
4. Refresh `paper_tex/BUILD_NOTES.md` with actual TORS/acmsmall page counts and
   current scan output.
5. Fix the Table 2 float/caption placement in the LaTeX build, then re-render
   the full PDF visually.
6. Replace the SILLM4Rec sentence with a concrete re-ranking/SFT-DPO exclusion
   rationale, or archive a direct full-paper protocol inspection.

### Open Questions

- Should the archival DOI package be versioned as `v1.0.1-deposit`, or should
  the release be promoted to a new post-V3/post-FIR major artifact?
- Does the submission target require the 41-page acmsmall preview to be reduced,
  or only documented accurately?
- Should Office V3 and FIR-breadth be first-class `RELEASE_MANIFEST.json`
  `result_families`, or is `_bestrec_run/hstu_results_manifest.json` intended to
  remain the source of truth for those claim families?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Re-run strict manuscript/artifact gate.
- [x] Verify release-manifest status and inspect result-family scope.
- [x] Re-run Office V3 adjudicator dynamically.
- [x] Re-run FIR-breadth adjudicator dynamically.
- [x] Check rendered PDF page counts, stale phrases, and hygiene scan.
- [x] Render selected PDF pages for visual QA.
- [x] Inspect deposit zip contents and DOI instructions.
- [x] Fact-check comparator and nearby-literature boundaries against external
      sources.
- [x] Refresh current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair Appendix A.0 Office wording.
- [ ] Remove stale `PAPER_DRAFT.md` V3-pending status line.
- [ ] Rebuild current deposit/release package.
- [ ] Refresh build-note page-count documentation.
- [ ] Fix Table 2 caption/table placement.
- [ ] Inspect/archive SILLM4Rec full paper or revise the exclusion rationale.

## Audit Run - 2026-07-13 23:57 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Automation memory: no prior memory file was present for this automation at
  run start.
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `paper_tex/sections/*.tex`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `CANONICAL_SUBMISSION.md`,
  `VENUE_PLAN.md`, `RELEASE_MANIFEST.json`, `DOI_DEPOSIT_INSTRUCTIONS.md`,
  `_release/bestrec_deposit_v1.0.zip`, `PREREG_OFFICE_V3.md`,
  `OFFICE_V3_RESULTS.md`, `PREREG_FIR_BREADTH.md`,
  `FIR_BREADTH_RESULTS.md`, and current Office V3 / FIR-breadth result JSONs.
- Working tree state before this audit edit: the only tracked modification was
  `PAPER_REVIEW_AUDIT.md`; untracked files remained
  `_bestrec_run/impact_program.DONE`, `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.

### Verdict

**No new numerical or adjudication failure was found; the rejection risk is still
submission-package consistency.** The strict gate, release-manifest verification,
Office V3 adjudicator, FIR-breadth adjudicator, and TORS hygiene scan all pass
again. The paper remains vulnerable for the same top-journal reasons: Appendix
A.0 and the compiled PDFs still contain the broad V1-era sentence that "Office
is not counted," `PAPER_DRAFT.md` still has a stale V3-pending status line, the
DOI/deposit bundle still predates Office V3 and FIR-breadth, and `BUILD_NOTES.md`
still reports historical/current page counts inconsistently with the 41-page
acmsmall preview.

The core empirical claim set is mechanically stronger than the packaging story.
A reviewer using the repository can re-run the current strict graph and see the
new evidence; a reviewer using the advertised `v1.0-deposit` zip cannot.

### Commands And Evidence Checked

- `Get-Date -Format "yyyy-MM-dd HH:mm:ss K"`
  - Current run time: `2026-07-13 23:57:21 +10:00`.
- `git diff --name-only` / `git status --short`
  - Only tracked diff: `PAPER_REVIEW_AUDIT.md`.
  - Same four untracked local files as the previous audit.
- `rg "Office is not counted|confirmed per-category claim remains|V3 outcome is pending|outcome pending|not part of any counted claim|Office never a passed category|35 pages|36 pages|current builds are 40/40|SILLM4Rec" ...`
  - Confirmed `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, and
    `paper_tex/sections/appendix-a0.tex` still contain the broad Appendix A.0
    sentence: "The confirmed per-category claim remains Musical_Instruments
    only; Office is not counted."
  - Confirmed `PAPER_DRAFT.md` line 8 still says Office stays VOID and V3 is
    pending.
  - Confirmed `paper_tex/BUILD_NOTES.md` still contains 35/36-page historical
    compile lines with "current builds are 40/40", while the live acmsmall PDF
    is 41 pages.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS at `2026-07-13 23:57 Australia/Sydney`.
  - HSTU core-block parity OK; `168` cells recomputed; `0` mismatches; `0`
    untraceable; all `14` claim families sourced; release manifest OK for `113`
    files; MI V2 gate OK; legacy Office V1 descriptive/VOID adjudication OK.
- `uv --project _bestrec_run run python _bestrec_run\update_release_manifest.py --verify`
  - PASS: `113` files verified, `0` release-asset files not local.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-13 23:57 Australia/Sydney`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, 5/5 seeds above
    both `0.0279` and `0.0271`.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-13 23:57 Australia/Sydney`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, sd `0.00046`, 95% CI
    `[+0.00183, +0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, sd `0.00059`, 95% CI
    `[+0.00493, +0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: `PAPER_TORS.pdf` has 40 pages, 0 placeholder/forbidden-claim
    failures, and 20 informational SOTA/negated-claim review hits.
- PDF page-count/text extraction with `pypdf`
  - `PAPER_SUBMISSION.pdf`: 45 pages, contains `Office is not counted` and
    `confirmed per-category claim remains`.
  - `paper_tex/PAPER_TORS.pdf`: 40 pages, contains the same two stale phrases.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages, contains the same two stale
    phrases.
- Deposit zip inspection with `zipfile`
  - `_release/bestrec_deposit_v1.0.zip`: last write
    `2026-07-11T22:11:05.439574`, SHA256
    `8fd3eb58e35e695d910b960b4cacf85c50e23e6ff77ec0a637953655f1d08770`,
    `48` entries under prefix `bestrec_deposit_v1.0/`.
  - Contains the old prefixed `PAPER_SUBMISSION.md` and
    `PAPER_SUBMISSION.pdf`, but contains no `PREREG_OFFICE_V3.md`,
    `OFFICE_V3_RESULTS.md`, `PREREG_FIR_BREADTH.md`,
    `FIR_BREADTH_RESULTS.md`, or `paper_tex/PAPER_TORS.pdf`.
  - `DOI_DEPOSIT_INSTRUCTIONS.md` still advertises a 46-file
    `v1.0-deposit` bundle and points Zenodo upload instructions to
    `bestrec_deposit_v1.0.zip`.

### External Fact-Check / Novelty Notes

- Amazon Reviews 2023's official site supports the high-level dataset framing:
  it reports `571.54M` reviews, `54.51M` users, `48.19M` items, and standard
  splitting; it also lists the relevant categories, including Video_Games,
  Musical_Instruments, Office_Products, Industrial_and_Scientific, and
  CDs_and_Vinyl. Sources:
  https://amazon-reviews-2023.github.io/ and
  https://amazon-reviews-2023.github.io/data_processing/5core.html
- HSTU-BLaIR v3 remains the relevant comparator source for the paper's external
  constants and dataset-statistics family; it evaluates AR2023 5-core Video
  Games, Office Products, and Musical Instruments. Source:
  https://arxiv.org/html/2504.10545v3
- Latte remains a close novelty/priority pressure point but not a direct
  contradiction to the current non-claim wording. It states that it uses AR2023
  Instruments, Scientific, and Games with leave-one-out, and its Table 7 lists
  the same statistics family for Instruments (`57,439` users / `24,587` items /
  `511,836` interactions), Scientific, and Games (`94,762` / `25,612` /
  `814,586`). Source: https://arxiv.org/html/2605.06331v1
- ReSID/ChronoSID support the paper's "SID-line filtered universe differs"
  caveat: ReSID lists Musical Instruments as `57,359` users / `23,742` items /
  `490,522` interactions, and ChronoSID reports output-level MI N@10 `0.0345`
  vs ReSID `0.0325` under that line. Sources:
  https://arxiv.org/html/2602.02338v1 and
  https://arxiv.org/html/2607.03918v1
- SILLM4Rec's public repository supports only a repository-based
  non-interchangeability rationale: it documents image-description generation,
  user preference summaries, candidate product ranking tasks, and SFT/DPO data.
  That does not close full-paper protocol inspection; the ACM paper still needs
  direct inspection or an explicit "pending direct protocol inspection" caveat.
  Sources: https://github.com/MKC-Lab/SILLM4Rec and
  https://dl.acm.org/doi/10.1145/3743093.3771011

### Confirmed Problems

1. **Appendix A.0 still contradicts the live Office V3 claim.** The V1 appendix
   sentence is historically understandable but too broad in the current paper
   and PDFs. It must be scoped to the V1 pre-registration only.
2. **`PAPER_DRAFT.md` still has a stale status line.** It says Office stays VOID
   and V3 is pending, even though the abstract/body now count the V3 pass.
3. **The deposit bundle is stale.** The DOI instructions and `v1.0-deposit` zip
   still point to a pre-Office-V3/pre-FIR-breadth package.
4. **`BUILD_NOTES.md` is stale/internally inconsistent.** The live acmsmall
   preview is 41 pages, while the notes still say current builds are 40/40 in
   the old compile-status block.

### Confirmed Non-Problems

- The strict artifact graph remains green, with all current claim families
  sourced and no mismatched/untraceable printed cells.
- Office V3 remains mechanically green under its frozen redesigned claim
  wording.
- FIR-breadth remains mechanically green for both new categories.
- The TORS review PDF hygiene scan remains PASS; the stale Office phrase is a
  substantive contradiction, not a scanner miss or placeholder failure.

### Concrete Fixes To Make Next

1. Rewrite Appendix A.0's broad sentence to: under the V1 pre-registration, no
   claim counts the V1 campaign; the later V3 redesign is reported separately
   in Section 5.2.
2. Remove or update the `PAPER_DRAFT.md` v3.8 status line so it no longer says
   V3 is pending.
3. Rebuild the DOI/deposit bundle after Office V3 and FIR-breadth, and update
   `DOI_DEPOSIT_INSTRUCTIONS.md` / release notes to point to the new package.
4. Refresh `paper_tex/BUILD_NOTES.md` for actual page counts and current scan
   output, or clearly mark the old 35/36-page block as historical without the
   "current builds are 40/40" phrase.
5. Before submission freeze, inspect the SILLM4Rec ACM full paper directly if
   accessible, or keep the exclusion explicitly repository-evidence-based and
   inspection-pending.

### Open Questions

- Is the stale `v1.0-deposit` bundle still meant for reviewers, or should a
  post-V3/post-FIR package supersede it immediately?
- Should the production preview be compressed back to 40 pages, or should 41
  pages be accepted and documented?
- Should `RELEASE_MANIFEST.json` name Office V3 and FIR-breadth as first-class
  result families, or explicitly delegate current per-claim evidence to
  `_bestrec_run/hstu_results_manifest.json`?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Check workspace diff state.
- [x] Re-run strict manuscript/artifact gate.
- [x] Verify release-manifest status.
- [x] Re-run Office V3 adjudicator dynamically.
- [x] Re-run FIR-breadth adjudicator dynamically.
- [x] Check rendered PDF page counts, stale phrases, and hygiene scan.
- [x] Inspect deposit zip contents and DOI instructions.
- [x] Fact-check current dataset/comparator/related-work boundary against
      external sources.
- [x] Refresh current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Repair Appendix A.0 Office wording.
- [ ] Remove stale `PAPER_DRAFT.md` V3-pending status line.
- [ ] Rebuild current deposit/release package.
- [ ] Refresh build-note page-count documentation.
- [ ] Inspect SILLM4Rec full paper or keep the exclusion explicitly pending.

## Audit Run - 2026-07-13 22:59 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `paper_tex/sections/*.tex`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `RELEASE_MANIFEST.json`,
  `_bestrec_run/hstu_results_manifest.json`, `DOI_DEPOSIT_INSTRUCTIONS.md`,
  `_release/bestrec_deposit_v1.0.zip`, `OFFICE_V3_RESULTS.md`,
  `PREREG_OFFICE_V3.md`, `FIR_BREADTH_RESULTS.md`,
  `PREREG_FIR_BREADTH.md`, and current Office V3 / FIR-breadth result JSONs.
- Working tree state before this audit edit: tracked modification already
  present in `PAPER_REVIEW_AUDIT.md`; untracked
  `_bestrec_run/impact_program.DONE`, `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.

### Verdict

**The numerical gates are green, but the paper is not submission-package ready.**
The current strict rebuild and both fresh adjudicators pass. The highest current
top-journal rejection risks are now consistency and archival reproducibility:
the appendix/PDF still contains a broad "Office is not counted" statement that
conflicts with the counted Office V3 pass, and the DOI/deposit bundle predates
both Office V3 and FIR-breadth.

The release-manifest result is nuanced. `update_release_manifest.py --verify`
passes for the manifest's declared scope, and the generated HSTU manifest sees
Office V3 and FIR-breadth evidence. But the user-facing deposit instructions and
zip do not contain the new prereg/results files. A reviewer trying to reproduce
the submitted claim from the advertised `v1.0-deposit` artifact would not have
the current evidence set.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS at `2026-07-13 22:56 Australia/Sydney`.
  - HSTU parity OK; `168` cells recomputed; `0` mismatches; `0` untraceable;
    all `14` claim families sourced; release manifest OK for `113` declared
    files; MI V2 gate OK; legacy Office V1 descriptive/VOID adjudication OK.
- `uv --project _bestrec_run run python _bestrec_run\update_release_manifest.py --verify`
  - PASS: `113` files verified, `0` release-asset files not local.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-13 22:56 Australia/Sydney`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, 5/5 seeds above
    both `0.0279` and `0.0271`.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-13 22:56 Australia/Sydney`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, sd `0.00046`, 95% CI
    `[+0.00183, +0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, sd `0.00059`, 95% CI
    `[+0.00493, +0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: `PAPER_TORS.pdf` has 40 pages, 0 placeholder/forbidden-claim
    failures, and 20 informational SOTA/negated-claim review hits.
- PDF page-count extraction with `pypdf`
  - `paper_tex/PAPER_TORS.pdf`: 40 pages, 612 x 792 pt.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages, 486 x 720 pt.
  - `PAPER_SUBMISSION.pdf`: 45 pages, 612 x 792 pt.
- PDF text extraction with `pypdf`
  - `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`, and
    `paper_tex/PAPER_TORS_acmsmall.pdf` all contain `Office is not counted` and
    `confirmed per-category claim remains`.
  - No `outcome pending` phrase was found in those PDFs, but `PAPER_DRAFT.md`
    still contains the old pending-status line.
- Deposit/release packaging inspection
  - `_release/bestrec_deposit_v1.0.zip` timestamp: `2026-07-11 22:11`; SHA256
    matches `DOI_DEPOSIT_INSTRUCTIONS.md`.
  - Zip entries: 48. It contains `PAPER_SUBMISSION.md` and
    `PAPER_SUBMISSION.pdf`, but contains no `PAPER_TORS.pdf`, no
    `PREREG_OFFICE_V3.md`, no `OFFICE_V3_RESULTS.md`, no
    `PREREG_FIR_BREADTH.md`, and no `FIR_BREADTH_RESULTS.md`.
  - `RELEASE_MANIFEST.json` `result_families` keys remain:
    `MI_gate_EXEC2`, `MI_gate_EXEC2_rest`, `MI_rebuild`, `OFFICE_gate`,
    `OFFICE_idonly_floor`, `FIR_ablations`; the text does not contain
    `results_OFFICEV3`, `results_FIRB`, `PREREG_OFFICE_V3`, or
    `PREREG_FIR_BREADTH`.
  - `_bestrec_run/hstu_results_manifest.json` does contain Office V3 and
    FIR-breadth evidence strings, so the fail-closed table gate and the public
    archival bundle are currently not aligned.
- FIR-breadth JSON provenance scan over `_bestrec_run/results_FIRB*.json`
  - `20` FIRB JSONs total.
  - `CDs_and_Vinyl`: 10 files, one unique `data_sha256` set, sidecar hash fields
    present in 10/10, 0 missing sidecar references.
  - `Industrial_and_Scientific`: 10 files, one unique `data_sha256` set, sidecar
    hash fields present in 10/10, 0 missing sidecar references.

### External Fact-Check / Novelty Notes

- Official Amazon Reviews 2023 documentation supports the dataset framing:
  McAuley Lab's AR2023 site reports `571.54M` reviews, `54.51M` users,
  `48.19M` items, rich reviews/metadata/links, and standard splitting. Source:
  https://amazon-reviews-2023.github.io/
- Official AR2023 5-core processing remains the right source for category and
  split availability. Source:
  https://amazon-reviews-2023.github.io/data_processing/5core.html
- HSTU-BLaIR v3 supports the comparator constants used by the paper: it reports
  AR2023 5-core Video Games / Office Products / Musical Instruments statistics
  and NDCG@10 values `0.0760`, `0.0271`, and `0.0406` for HSTU-BLaIR. Source:
  https://arxiv.org/html/2504.10545v3
- Latte is closer than a casual related-work paragraph suggests: it uses AR2023
  Instruments / Scientific / Games, LLOO, and the same MI/VG statistics family;
  it reports RQ-KMeans Latte NDCG@10 `0.0331` for Instruments and `0.0515` for
  Games. This supports citation and context, but not direct superiority without
  protocol audit. Source: https://arxiv.org/html/2605.06331v1
- ReSID/ChronoSID use a different SID-line filtered universe. ReSID reports
  Musical Instruments statistics of `57,359` users, `23,742` items, and
  `490,522` interactions; ChronoSID reports output-level MI NDCG@10 `0.0345`
  versus ReSID `0.0325`. This supports the paper's non-interchangeability
  boundary for that line. Sources: https://arxiv.org/html/2602.02338v1 and
  https://arxiv.org/html/2607.03918v1
- WPGRec confirms that wavelet/frequency-domain sequential recommendation is an
  active and broader prior-art line, so the FIR novelty claim must remain
  narrow. Source: https://arxiv.org/html/2604.21305v1
- SILLM4Rec's public repository supports the current exclusion rationale: its
  workflow includes image descriptions, user preference summaries, candidate
  product ranking tasks, and SFT/DPO training data. The ACM DOI page was
  located, but direct full-paper protocol inspection was not completed in this
  run. Sources: https://github.com/MKC-Lab/SILLM4Rec and
  https://dl.acm.org/doi/10.1145/3743093.3771011

### Confirmed Problems

1. **Archival/deposit package is stale.** The advertised DOI-ready bundle does
   not include the new Office V3 or FIR-breadth prereg/results evidence, and
   the instructions still point users to that stale bundle.
2. **Current PDFs contain contradictory Office counting language.** The main
   paper counts Office V3; Appendix A.0 still says the confirmed per-category
   claim remains MI only and Office is not counted. Even if historically
   intended for V1, it is too broad in the current compiled paper.
3. **`PAPER_DRAFT.md` has a stale status sentence.** The opening status line says
   Office stays VOID and V3 is pending, contradicting the live claim set.
4. **`paper_tex/BUILD_NOTES.md` remains stale.** It says acmsmall is 40 pages and
   current builds are 40/40, while actual `PAPER_TORS_acmsmall.pdf` is 41 pages;
   it also embeds an old 35-page hygiene scan block.

### Plausible Risks Requiring Author Verification

1. **Whether `RELEASE_MANIFEST.json` is intended to be complete claim evidence
   or only a legacy release-asset manifest.** If it is advertised as the
   reproducibility manifest, it must include or explicitly delegate Office V3
   and FIR-breadth evidence to `_bestrec_run/hstu_results_manifest.json`.
2. **Whether the deposit should include local-only per-user sidecars at review
   time.** The manuscript says they are provided on reviewer/editor request and
   deposited upon acceptance; some artifact reviewers may expect them in the
   initial package.
3. **SILLM4Rec full-paper protocol inspection.** The repository evidence is
   enough for a cautious exclusion sentence, but a top reviewer may require the
   ACM PDF to be inspected directly.

### Confirmed Non-Problems

- The strict artifact graph, declared release-manifest verification, MI V2 gate,
  and legacy Office V1 descriptive/VOID adjudication all pass.
- Office V3 remains mechanically green under the redesigned
  environment-matched preregistration.
- FIR-breadth remains mechanically green for both categories with 5/5 positive
  paired seeds and CIs excluding zero.
- The two FIR-breadth result categories have consistent `data_sha256` sets and
  sidecar hash fields in tracked run JSONs.

### Concrete Fixes To Make Next

1. Rebuild the DOI/deposit bundle after the Office V3 and FIR-breadth changes;
   include `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
   `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`, relevant result JSONs or
   a manifest that enumerates them, and the current PDFs.
2. Update `DOI_DEPOSIT_INSTRUCTIONS.md`, `CITATION.cff`, and any release notes
   from the July 11 `v1.0-deposit` state to a current July 13 package state.
3. Decide whether `RELEASE_MANIFEST.json` should hash Office V3/FIR-breadth
   source evidence directly or explicitly state that `_bestrec_run/hstu_results_manifest.json`
   is the complete per-claim evidence manifest.
4. Rewrite Appendix A.0's broad Office sentence to be V1-scoped, e.g. "Under
   this V1 pre-registration, no claim counts the V1 campaign; the later V3
   redesign is reported separately in Section 5.2."
5. Remove or update the stale `PAPER_DRAFT.md` opening status line that says V3
   is pending.
6. Refresh `paper_tex/BUILD_NOTES.md` for the actual 40/41 page counts and the
   current 40-page hygiene scan output.
7. Inspect the SILLM4Rec ACM full paper directly or keep the exclusion as
   repository-based evidence only.

### Open Questions

- Is `_release/bestrec_deposit_v1.0.zip` still intended to be offered to
  reviewers, or is a new post-V3/post-FIR package planned?
- Should the acmsmall preview be compressed back to 40 pages, or should the
  notes simply document 41 pages?
- Should Office V3 and FIR-breadth result JSONs become first-class
  `RELEASE_MANIFEST.json` families?
- Can the authors access the ACM SILLM4Rec PDF for direct protocol inspection?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Re-run strict manuscript/artifact gate.
- [x] Verify release-manifest status.
- [x] Re-run Office V3 adjudicator dynamically.
- [x] Re-run FIR-breadth adjudicator dynamically.
- [x] Check rendered PDF page counts and hygiene scan.
- [x] Search markdown, TeX, and PDFs for stale Office wording.
- [x] Inspect deposit zip contents and DOI instructions.
- [x] Compare `RELEASE_MANIFEST.json` scope to `_bestrec_run/hstu_results_manifest.json`.
- [x] Check FIR-breadth result JSON hashes and sidecar references.
- [x] Fact-check AR2023, HSTU-BLaIR, Latte/SID-line, WPGRec, and SILLM4Rec
      claims against external sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Rebuild current deposit/release package.
- [ ] Remove broad Office "not counted" wording from Appendix A.0.
- [ ] Refresh stale build notes and acmsmall page-count documentation.
- [ ] Inspect SILLM4Rec full paper or keep the exclusion explicitly pending.

## Audit Run - 2026-07-13 21:57 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `174b5a74` (`Respond to audit
  run 2026-07-13 20:57 (all fixes executed; open questions answered)`).
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `paper_tex/sections/08-availability.tex`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `RELEASE_MANIFEST.json`,
  `FIR_BREADTH_RESULTS.md`, `CANONICAL_SUBMISSION.md`, `VENUE_PLAN.md`,
  `_bestrec_run/results_FIRB_*.json`, `PREREG_FIR_BREADTH.md`,
  `OFFICE_V3_RESULTS.md`, and current Office V3 result/provenance files.
- Working tree state before this audit edit: no tracked modifications; untracked
  `_bestrec_run/impact_program.DONE`, `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`.

### Verdict

**The paper is numerically and provenance-green in the current tree, but not yet
artifact-polished.** The strict manuscript/artifact rebuild passes after the new
deposit-policy edits and manifest synchronization. Office V3 and FIR-breadth
mechanical evidence both remain green. The highest current rejection/readiness
risk is not a result contradiction; it is presentation/package drift: the
acmsmall production preview is 41 pages while build notes still describe the
current deliverables as 40/40.

The new Section 8 deposit policy is a real improvement. It makes the
tracked-artifact boundary explicit and states that local-only per-user sidecars
are hash-pinned supplementary audit material. A skeptical reviewer may still
ask for the sidecars or exact raw-data acquisition path at review time, so the
deposit policy should be mirrored in the eventual artifact package/release notes,
not only in the manuscript.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - Initial run during this audit: numerical/artifact table build passed, but
    release-manifest verification failed for edited `PAPER_SUBMISSION.md` and
    `PAPER_DRAFT.md`.
  - Final rerun at `2026-07-13 21:57 Australia/Sydney`: PASS. HSTU parity OK;
    `168` cells recomputed; `0` mismatches; `0` untraceable; all `14` claim
    families sourced; release manifest OK for `113` files; MI V2 gate OK;
    legacy Office V1 descriptive/VOID adjudication OK.
- `uv --project _bestrec_run run python _bestrec_run\update_release_manifest.py --verify`
  - PASS: `113` files verified, `0` release-asset files not local.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-13 21:55 Australia/Sydney`.
  - K=16: mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, 5/5 seeds above
    both `0.0279` and `0.0271`.
  - K=8: mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, 5/5 seeds above
    both `0.0279` and `0.0271`.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - PASS at `2026-07-13 21:57 Australia/Sydney`.
  - `Industrial_and_Scientific`: paired mean `+0.00240`, sd `0.00046`, 95% CI
    `[+0.00183, +0.00297]`, 5/5 positive.
  - `CDs_and_Vinyl`: paired mean `+0.00566`, sd `0.00059`, 95% CI
    `[+0.00493, +0.00639]`, 5/5 positive.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: `PAPER_TORS.pdf` has 40 pages, 0 placeholder/forbidden-claim
    failures, and 20 informational SOTA/negated-claim review hits.
- PDF text/page extraction with `pypdf`
  - `paper_tex/PAPER_TORS.pdf`: 40 pages; new deposit-policy wording found.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 41 pages; deposit-policy wording mostly
    found, but long phrases are split by extraction.
  - `PAPER_SUBMISSION.pdf`: 45 pages; new tracked-artifact/reviewer-request
    deposit-policy wording found.
- FIR-breadth provenance scan over `_bestrec_run/results_FIRB_*.json`
  - `Industrial_and_Scientific`: 10 run JSONs, 1 unique `data_sha256` set, 0
    missing sidecars.
  - `CDs_and_Vinyl`: 10 run JSONs, 1 unique `data_sha256` set, 0 missing
    sidecars.
- `rg` over manuscript/build-note sources
  - Section 8 deposit policy is present in `PAPER_SUBMISSION.md`,
    `PAPER_DRAFT.md`, and `paper_tex/sections/08-availability.tex`.
  - `paper_tex/BUILD_NOTES.md` still has historical 35/36-page comments, and
    now incorrectly says current builds are 40/40 despite the acmsmall PDF being
    41 pages.

### External Fact-Check / Novelty Notes

- The official Amazon Reviews 2023 site supports the dataset framing and public
  data boundary: McAuley Lab's AR2023 release includes ratings/reviews,
  metadata, links, standard splits, and the headline corpus scale
  (`571.54M` reviews, `54.51M` users, `48.19M` items). Source:
  https://amazon-reviews-2023.github.io/
- The official AR2023 5-core processing page lists both FIR-breadth categories
  and leave-last-out split downloads. It reports `Industrial_and_Scientific`
  5-core statistics of `51.0K` users, `25.8K` items, `412.9K` ratings, and
  LLOO split rows `311.0K / 51.0K / 51.0K`; it reports `CDs_and_Vinyl`
  `123.9K` users, `89.4K` items, `1.6M` ratings, and LLOO split rows
  `1.3M / 123.9K / 123.9K`. Source:
  https://amazon-reviews-2023.github.io/data_processing/5core.html
- HSTU-BLaIR still supports the comparator constants and protocol family used
  by the paper: the arXiv HTML reports AR2023 5-core Video Games / Office
  Products / Musical Instruments, LLOO-style chronological evaluation, and
  NDCG@10 values `0.0760`, `0.0271`, and `0.0406` for HSTU-BLaIR. Source:
  https://arxiv.org/html/2504.10545v3
- The HSTU-BLaIR GitHub README still supports the environment caveat: it says
  the implementation was tested on Ubuntu 22.04, Python 3.9, CUDA 12.6, and a
  single RTX 4090. Source: https://github.com/snapfinger/HSTU-BLaIR
- SILLM4Rec's public repository supports the paper's non-interchangeability
  rationale: its workflow asks users to generate image descriptions, user
  preference summaries, candidate product ranking tasks, and SFT/DPO training
  data. This is not established as the same full-catalog LLOO setting, but the
  ACM page/PDF should still be inspected directly before final freeze. Sources:
  https://github.com/MKC-Lab/SILLM4Rec and
  https://dl.acm.org/doi/10.1145/3743093.3771011

### Confirmed Problems

1. **Production-preview page-count inconsistency.** `PAPER_TORS_acmsmall.pdf`
   is 41 pages by `pypdf`, but `paper_tex/BUILD_NOTES.md` says the current
   builds are 40/40. Fix either the acmsmall layout or the notes before
   distributing the production preview.
2. **Strict manifest can go red during manuscript/PDF update windows.** This
   run reproduced the failure mode briefly after Section 8 edits. It is green
   now, but the workflow must always end with manifest verification and strict
   rebuild after any rendered-paper change.

### Plausible Risks Requiring Author Verification

1. **Supplementary sidecar deposit timing.** Section 8 says local-only per-user
   sidecars will be provided on editorial/reviewer request and deposited upon
   acceptance. Confirm this is acceptable for the target venue; some artifact
   evaluators prefer all supplementary evidence available at first review.
2. **Raw AR2023 archive instructions.** The untracked raw
   `Industrial_and_Scientific.csv.gz` and `CDs_and_Vinyl.csv.gz` files are
   consistent with a no-redistribution policy, but release docs should give the
   exact official download route and expected hashes.
3. **SILLM4Rec full-paper inspection.** Public repo evidence supports
   exclusion, but direct ACM full-paper protocol inspection remains the cleaner
   top-journal posture.

### Confirmed Non-Problems

- The strict artifact graph, release manifest, MI V2 gate, and Office
  descriptive/VOID adjudication all pass in the final current-tree rerun.
- Office V3 remains green under the redesigned frozen point-estimate wording.
- FIR-breadth remains green for both categories with 5/5 positive paired seeds
  and CIs excluding zero.
- The new deposit-policy text appears in markdown, TeX, `PAPER_TORS.pdf`, and
  `PAPER_SUBMISSION.pdf`.
- The external AR2023 5-core site supports the existence and broad statistics
  of the two added breadth categories.

### Concrete Fixes To Make Next

1. Fix `paper_tex/BUILD_NOTES.md` so the current page-count statements match
   current artifacts, especially `PAPER_TORS_acmsmall.pdf` = 41 pages.
2. Decide whether to compress the acmsmall production preview back to 40 pages
   or accept/document 41 pages.
3. Mirror the Section 8 deposit policy in release notes/artifact packaging:
   exact raw-data download route, expected raw/split hashes, and how reviewers
   can obtain local-only per-user sidecars.
4. Inspect the SILLM4Rec ACM PDF/full paper before freeze, or keep the current
   exclusion explicitly caveated as repository-based only.
5. Keep running `update_release_manifest.py --verify` and
   `rebuild_hstu_submission.py --strict` after every manuscript or rendered-PDF
   change.

### Open Questions

- Is `PAPER_TORS_acmsmall.pdf` intended to be a real submitted production
  preview? If yes, is 41 pages acceptable for the target venue?
- Should local-only Office/FIR-breadth per-user sidecars be deposited before
  review rather than only upon request/acceptance?
- Should the untracked raw FIR-breadth archives be accompanied by a small
  `RAW_DATA_DOWNLOADS.md` with official URLs and SHA256s?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Re-run strict manuscript/artifact gate after the Section 8 deposit-policy
      edits.
- [x] Verify release-manifest status after the transient mismatch.
- [x] Re-run Office V3 adjudicator dynamically.
- [x] Re-run FIR-breadth adjudicator dynamically.
- [x] Check rendered PDFs for deposit-policy text and page counts.
- [x] Check FIR-breadth result JSONs for consistent `data_sha256` and sidecar
      references.
- [x] Fact-check AR2023 5-core category/split claims against the official site.
- [x] Fact-check HSTU-BLaIR comparator constants and environment caveat.
- [x] Re-check SILLM4Rec public repository rationale.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Fix or document the 41-page acmsmall production preview.
- [ ] Mirror the sidecar/raw-data deposit policy in release packaging.
- [ ] Inspect SILLM4Rec full paper or leave exclusion explicitly pending.

## Audit Run - 2026-07-13 20:57 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `1f48b726` (`Regenerate
  RELEASE_MANIFEST at the consistency-sweep boundary`).
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/main.tex`, `paper_tex/paper-shared.tex`,
  `paper_tex/sections/*`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/hygiene_scan_output.txt`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/references.bib`,
  `RELEASE_MANIFEST.json`, `OFFICE_V3_RESULTS.md`, `PREREG_OFFICE_V3.md`,
  `_bestrec_run/hstu_results_manifest.json`, `_bestrec_run/hstu_tables.json`,
  and current Office V3 result/provenance files.
- Working tree state after the final verification run: no tracked
  modifications; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`. This audit
  edits only `PAPER_REVIEW_AUDIT.md`.

### Verdict

**The prior Office status contradiction is fixed and the strict gates are green
again.** The live paper now consistently states the two-track Office story:
Office V1 remains VOID under its original floor-check preregistration, while
Office V3 passed under the redesigned environment-matched preregistration and
counts only as a per-category point-estimate comparison. The compiled TORS PDF
contains the corrected wording and does not contain the stale "no claim counts
Office" / "outcome pending" phrases.

No current reject-level artifact or numerical failure was reproduced after the
workspace settled. During this run, one strict command initially failed
release-manifest verification while manifested manuscript/PDF files were dirty;
a direct manifest-hash check and a subsequent strict rerun showed the hashes
matched and the release-manifest gate passed. Treat this as a resolved
transient state, not a current blocker, but it is exactly the failure mode that
must be avoided before submission or tagging.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - First run during this audit: table/artifact cells passed, but release
    manifest verification failed with 8 dirty/hash problems against
    `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`, `PAPER_DRAFT.md`, and
    `paper_tex/PAPER_TORS.pdf`.
  - Direct SHA256 check immediately afterward: all four files matched the
    current `RELEASE_MANIFEST.json` entries.
  - Final rerun at `2026-07-13 20:57 Australia/Sydney`: PASS. HSTU parity OK;
    `168` cells recomputed; `0` mismatches; `0` untraceable; all `14` claim
    families sourced; release manifest OK for `113` files; MI V2 gate OK;
    legacy Office V1 descriptive/VOID adjudication OK.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-13 20:54 Australia/Sydney`.
  - K=16: seed finals `0.03060`, `0.03053`, `0.03046`, `0.03033`, `0.03041`;
    mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`.
  - K=8: seed finals `0.03025`, `0.03037`, `0.03030`, `0.03030`, `0.03026`;
    mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`.
  - 10/10 seeds exceed both `0.0279` and `0.0271`; comparability conditions OK.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: 40 pages, 0 placeholder/forbidden-claim failures, 20 informational
    SOTA/negated-claim review hits.
- PDF text extraction from `paper_tex/PAPER_TORS.pdf`
  - Found `redesigned V3`, `Office_Products status`, and `no claim counts the
    V1 campaign`.
  - Did not find stale `no claim counts Office`, `outcome pending`, or `Office
    never a passed category`.
- Page-count check with `pypdf`
  - `paper_tex/PAPER_TORS.pdf`: 40 pages.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 40 pages.
  - `PAPER_SUBMISSION.pdf`: 45 pages.
- `rg "outcome pending|no claim counts Office|not part of any counted claim|Office never a passed category|SILLM4Rec|local-only|35 pages|36 pages|45 pages|40 pages" ...`
  - No stale Office-pending/no-count wording remains in the live manuscript
    sources. The remaining "no claim counts" wording is narrowed to "the V1
    campaign."
  - `paper_tex/BUILD_NOTES.md` still contains historical 35/36-page references,
    but they are labeled as round-8/historical in context; low-priority
    documentation tidiness issue only.
- `git status --short`
  - After final verification, only the four unrelated untracked files listed
    above remain.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR still supports the comparator constants used by the paper: the
  arXiv PDF reports AR2023 5-core Video Games / Office Products / Musical
  Instruments and Table 2 gives HSTU-BLaIR NDCG@10 `0.0760`, `0.0271`, and
  `0.0406`. Source: https://arxiv.org/pdf/2504.10545
- The HSTU-BLaIR GitHub README also reports those same three AR2023 categories
  and constants, and states the implementation was tested on Ubuntu 22.04,
  Python 3.9, CUDA 12.6, and an RTX 4090. This supports the paper's
  environment-caveat framing. Source: https://github.com/snapfinger/HSTU-BLaIR
- The official Amazon Reviews 2023 site confirms the 2023 McAuley Lab dataset,
  rich review/metadata/link features, standard splits, 571.54M reviews, 54.51M
  users, 48.19M items, and category-level pages for the paper's categories.
  Source: https://amazon-reviews-2023.github.io/
- GrIT's arXiv HTML supports the paper's cautious mention: it uses AR2023 Video
  Games statistics `94,762` users / `25,612` items / `814,586` interactions,
  says evaluation uses the full item set, and reports Video Games NDCG@10
  `0.0588`. Source: https://arxiv.org/html/2602.19728v1
- Latte/SID-MLP and ChronoSID remain related but non-interchangeable context:
  Latte reports AR2023 Instruments/Scientific/Games under semantic-ID
  generative recommendation; ChronoSID reports MI output-level NDCG@10 `0.0345`
  vs ReSID `0.0325`, while its main table reports ChronoSID MI NDCG@10
  `0.0347`. The paper's "output-level MI table" wording is precise enough.
  Sources: https://arxiv.org/html/2605.06331v1 and
  https://arxiv.org/html/2607.03918v1
- The SILLM4Rec public repository supports the current exclusion rationale: it
  instructs users to generate image descriptions, user preference summaries,
  candidate product ranking tasks, and SFT/DPO training data. This is not
  established as apples-to-apples full-catalog LLOO. The ACM page/search
  metadata still says AR2023 5-core and NDCG@K, so full-paper inspection remains
  advisable. Sources: https://github.com/MKC-Lab/SILLM4Rec and
  https://dl.acm.org/doi/10.1145/3743093.3771011
- FMLP-Rec and BSARec continue to support a narrow novelty boundary only:
  filtering/frequency-domain sequential recommendation and self-attention
  low-pass/oversmoothing motivation are prior art. The paper should keep its
  novelty claim to the leak-free left-causal FIR adaptation in this
  HSTU-style, artifact-gated setting. Sources: https://arxiv.org/abs/2202.13556
  and https://arxiv.org/abs/2312.10325

### Confirmed Problems

1. **No current hard rejection defect reproduced after the final rerun.** The
   previous Office contradiction and the transient manifest failure are both
   superseded by current source/PDF/gate evidence.
2. **Documentation staleness remains minor.** `paper_tex/BUILD_NOTES.md` still
   carries historical 35/36-page references and a 36-page tree comment, even
   though the header and current artifacts are 40/40. This is not in the
   manuscript, but it is sloppy release documentation.

### Plausible Risks Requiring Author Verification

1. **Per-user sidecar release boundary.** The paper's aggregate V3 cells
   recompute from tracked JSONs, but per-user sidecars remain local-only. Decide
   whether those sidecars will be deposited for review or whether the tracked
   aggregate boundary is the intended reproducibility contract.
2. **SILLM4Rec protocol inspection.** Public repo evidence supports exclusion,
   but a reviewer could reasonably ask why the full ACM paper was not inspected
   given its AR2023 5-core/NDCG metadata.
3. **Untracked raw breadth files.** The two untracked raw proper-data archives
   for `cds_vinyl` and `industrial_sci` may be intentional local inputs, but if
   the FIR-breadth result is central to the final artifact package, their
   release/deposit boundary should be explicit.

### Confirmed Non-Problems

- Office V1/V3 wording is now internally consistent in markdown, TeX, and
  compiled PDF extraction.
- The strict artifact gate, release-manifest verification, MI V2 gate, and
  legacy Office V1 descriptive/VOID adjudication all pass on the final rerun.
- Office V3 passes dynamically under its frozen wording and remains limited to
  a per-category point-estimate comparison.
- Current HSTU-BLaIR, GrIT, Latte, ChronoSID, Amazon Reviews 2023, FMLP-Rec,
  BSARec, and SILLM4Rec spot-checks do not force a manuscript retraction or
  numerical correction. They reinforce the current narrow/non-comparability
  framing.

### Concrete Fixes To Make Next

1. Keep `RELEASE_MANIFEST.json` synchronized with any future source/PDF edits;
   run the strict gate after every render and do not submit while tracked
   manifested files are dirty.
2. Clean `paper_tex/BUILD_NOTES.md` historical page-count/tree comments so a
   reviewer or artifact evaluator never sees conflicting current-vs-historical
   deliverable descriptions.
3. Decide the Office V3/FIR-breadth per-user sidecar deposit policy and state it
   once in Section 8/release docs.
4. Inspect the SILLM4Rec ACM full paper before freeze, or keep the current
   exclusion sentence but explicitly mark full protocol inspection as pending.
5. Keep all claims in cover letters, responses, and metadata aligned with the
   current boundaries: no broad SOTA, no paired superiority against HSTU-BLaIR,
   and Office V1 VOID unchanged.

### Open Questions

- Were the transient dirty manifested files part of a concurrent render/manifest
  update that completed during this audit? If yes, no action; if not, audit the
  render script for non-atomic manifest windows.
- Should the local-only sidecars for Office V3 and FIR-breadth be deposited as a
  supplementary artifact before top-journal submission?
- Is `PAPER_SUBMISSION.pdf` still a live deliverable, or should the release
  surface emphasize only the 40-page TORS artifacts?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Verify the prior Office V1/V3 contradiction was fixed in markdown and TeX.
- [x] Search compiled PDF extraction for stale Office/pending phrases.
- [x] Re-run Office V3 adjudicator dynamically.
- [x] Re-run strict manuscript/artifact gate after workspace settled.
- [x] Check release manifest hashes for current submission documents.
- [x] Check compiled PDF page counts and hygiene output.
- [x] Fact-check current comparator and related-literature claims against
      HSTU-BLaIR, AR2023, GrIT, Latte, ChronoSID, SILLM4Rec, FMLP-Rec, and
      BSARec sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Decide and document the Office V3/FIR-breadth sidecar release boundary.
- [ ] Clean stale historical page-count comments in `paper_tex/BUILD_NOTES.md`.
- [ ] Inspect SILLM4Rec full paper or keep exclusion explicitly pending.

## Audit Run - 2026-07-13 19:54 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `1f48b726` (`Regenerate
  RELEASE_MANIFEST at the consistency-sweep boundary`).
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/main.tex`, `paper_tex/paper-shared.tex`,
  `paper_tex/sections/*`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/hygiene_scan_output.txt`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/references.bib`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, `PREREG_OFFICE_V3.md`,
  `OFFICE_V3_RESULTS.md`, `RELEASE_MANIFEST.json`,
  `_bestrec_run/hstu_results_manifest.json`, `_bestrec_run/hstu_tables.json`,
  and current Office V3 result/provenance records.
- Working tree state before this audit edit: no tracked modifications; untracked
  `_bestrec_run/impact_program.DONE`, `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`. This audit
  edits only `PAPER_REVIEW_AUDIT.md`.

### Verdict

**The numerical and packaging gates are green again, but the paper still has a
reject-level Office status contradiction.** The previous red release-manifest
finding is superseded by a fresh strict run: all 168 artifact-gated cells
recompute, all claim families are sourced, and the release manifest verifies.
Office V3 also still passes its own fresh adjudication.

The remaining blocker is therefore not the result; it is a stale limitation
sentence. Section 6.4 says Office V3 passed and is counted as the second
pre-registered per-category comparison, while Section 6.5 says the
second-category pass is VOID and "no claim counts Office." The same stale
sentence is present in the LaTeX twin. A top-journal reviewer would read that as
unresolved claim governance unless fixed before submission.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release-manifest verification OK for `113` files.
  - PASS: MI V2 gate; legacy Office V1 remains descriptive/VOID under its own
    floor-check preregistration.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-13 19:53 Australia/Sydney`.
  - K=16: seed finals `0.03060`, `0.03053`, `0.03046`, `0.03033`, `0.03041`;
    mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`.
  - K=8: seed finals `0.03025`, `0.03037`, `0.03030`, `0.03030`, `0.03026`;
    mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`.
  - 10/10 seeds exceed both `0.0279` and `0.0271`; comparability conditions OK.
- `rg "outcome pending|pending|no claim counts Office|not part of any counted claim|Office never a passed category|SILLM4Rec|local-only|PAPER_TORS_acmsmall|45 pages|40 pages" ...`
  - No `outcome pending`/old Office-pending hit remains in live paper sources.
  - Confirmed stale `no claim counts Office` sentence in
    `PAPER_SUBMISSION.md` line 526 and `paper_tex/sections/06-discussion.tex`
    line 81.
  - Confirmed the SILLM4Rec candidate-ranking/SFT-DPO explanation is now present
    in both markdown and TeX.
  - Confirmed Section 8 now distinguishes tracked Office V3 aggregate evidence
    from local-only per-user sidecars.
- `uv --project _bestrec_run run python -c "<pypdf page-count check>"`
  - `paper_tex/PAPER_TORS.pdf`: 40 pages.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 40 pages.
  - `PAPER_SUBMISSION.pdf`: 45 pages.
- `uv --project _bestrec_run run python paper_tex\scan_pdf.py paper_tex\PAPER_TORS.pdf`
  - PASS: 40 pages, 0 placeholder/forbidden-claim failures, 18 informational
    SOTA/negated-claim review hits.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's arXiv paper reports AR2023 5-core Video Games, Office Products,
  and Musical Instruments with item/user statistics matching this paper's
  comparator family, and Table 2 gives HSTU-BLaIR NDCG@10 values `0.0760`,
  `0.0271`, and `0.0406`. This supports the paper's comparator constants.
  Source: https://arxiv.org/pdf/2504.10545
- The official Amazon Reviews 2023 site confirms the 2023 McAuley Lab dataset,
  user reviews, item metadata, links, and standard splits. This supports the
  high-level dataset framing. Source: https://amazon-reviews-2023.github.io/
- SILLM4Rec is still close enough to require caution: ACM metadata describes
  experiments on three 5-core Amazon Reviews 2023 datasets with NDCG@K metrics,
  while the public repository describes image-to-text descriptions, user
  preference summaries, candidate product ranking tasks, and SFT/DPO training
  data. The paper's current non-interchangeability rationale is plausible, but
  the full protocol should be inspected before freeze. Sources:
  https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec
- ChronoSID's arXiv HTML reports the paper's cited output-level MI comparison
  against ReSID (NDCG@10 `0.0345` vs `0.0325`), supporting inclusion of the SID
  line as related but non-interchangeable protocol context. Source:
  https://arxiv.org/html/2607.03918v1

### Confirmed Problems

1. **Office status contradiction remains despite the response log claiming all
   sites were updated.** `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` says all Office V3
   status sites were fixed, but live Section 6.5 still carries the old V1-only
   limitation sentence. This is a paper-source defect, not just a response-log
   defect.
2. **The stale sentence appears in both canonical markdown and TeX.** Fixing
   only `PAPER_SUBMISSION.md` would leave `paper_tex/sections/06-discussion.tex`
   and the TORS artifact inconsistent until rebuilt.
3. **SILLM4Rec still needs full-protocol inspection before a top-journal
   freeze.** The current repo-based sentence is much better than the earlier
   vague exclusion, but ACM metadata is close enough to the paper's dataset
   family that a reviewer can ask why it was not inspected directly.

### Confirmed Non-Problems

- The prior red strict-release finding is no longer current; strict rebuild and
  release-manifest verification pass.
- Office V3 aggregate adjudication remains green and matches the paper's
  counted per-category point-estimate wording.
- Section 8's tracked-vs-local-only Office V3 boundary is now substantially
  clearer than in the prior audit.
- Current TeX/PDF hygiene is green: no forbidden broad SOTA claim, no placeholder
  failure, and the SOTA mentions are explicit non-claims or review hits.
- HSTU-BLaIR comparator constants and AR2023 high-level dataset framing are
  externally supported by primary/official sources checked this run.

### Concrete Fixes To Make Next

1. Replace the Section 6.5 Office bullet in both markdown and TeX with the same
   two-track statement used elsewhere:
   - Office V1 remains VOID under the original floor-check pre-registration.
   - Office V3 passed under the separate environment-matched preregistration and
     counts only as a per-category point-estimate comparison, not paired
     superiority or SOTA.
2. Rebuild the markdown PDF and TORS PDF after that edit, rerun the PDF hygiene
   scan, rerun `rebuild_hstu_submission.py --strict`, regenerate the release
   manifest if any manifested output changes, and commit the prose/PDF/manifest
   boundary together.
3. Add a short response-log correction acknowledging the missed Section 6.5
   sentence, so future audits do not treat the response log's "all sites fixed"
   line as ground truth.
4. Inspect the SILLM4Rec ACM full paper/PDF before freeze, or state explicitly
   that the exclusion is based only on public repository workflow evidence and
   not direct protocol inspection.
5. Decide whether Office V3 per-user sidecars remain local-only permanently or
   get deposited as ancillary artifacts; keep the release boundary synchronized
   with that decision.

### Open Questions

- Is `paper_tex/sections/06-discussion.tex` generated from markdown, or should
  the Office bullet be edited in both places manually before the next render?
- Are Office V3 per-user sidecars intended to be deposited now that V3 is a
  counted claim, or are tracked aggregate JSONs the declared reproducibility
  boundary?
- Can the authors access the SILLM4Rec ACM PDF/full paper for direct protocol
  inspection before final submission?
- Is `PAPER_SUBMISSION.pdf` still a live deliverable alongside the 40-page TORS
  artifact, or just a reader edition for repository review?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      response, and audit artifacts.
- [x] Search current manuscript/TeX for stale Office pending/no-claim wording.
- [x] Re-run strict manuscript/artifact/release gate.
- [x] Re-run Office V3 adjudicator dynamically.
- [x] Check compiled PDF page counts and TORS hygiene output.
- [x] Fact-check comparator, dataset, SILLM4Rec, and current SID-line claims
      against external primary/official sources where available.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Fix the remaining Office Section 6.5 contradiction in markdown and TeX.
- [ ] Rebuild PDFs and rerun strict/hygiene gates after the prose fix.
- [ ] Inspect SILLM4Rec full protocol before freeze.

## Audit Run - 2026-07-13 06:46 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `f50c7fdd` (`Respond to
  PAPER_REVIEW_AUDIT run 23:39: 4.1 role table + count definitions`).
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/sections/*`, `paper_tex/tables/*`,
  `paper_tex/references.bib`, `PREREG_FIR_BREADTH.md`,
  `FIR_BREADTH_RESULTS.md`, FIR-BREADTH JSON/log artifacts, and the cumulative
  audit.
- Working tree state after this audit's commands: `PAPER_REVIEW_AUDIT.md`
  modified by this audit; `PREREG_OFFICE_V3.md` independently gained an
  uncommitted Erratum E1 at 06:46; `FIR_BREADTH_RESULTS.md`, FIR-BREADTH
  adjudicator/scripts/results, and raw-data directories are untracked. No
  manuscript/TeX source file was edited by this audit.

### Verdict

**The live workspace has outgrown the submitted manuscript.** The printed paper
still passes its strict rebuild and hygiene checks, but the now-complete
FIR-BREADTH campaign makes the current manuscript stale: it says two categories
are pending and unclaimed while the workspace contains a mechanical two-category
confirmation. A top-journal reviewer would treat this as a governance and
scope-boundary failure unless the authors either freeze the submitted package as
pre-breadth, or integrate the campaign cleanly and regenerate every artifact.

The second live rejection risk is unchanged: the causal FIR novelty boundary
still cites frequency filters but not older causal/local convolutional
sequential-recommendation work. The claim can survive only as a narrow
left-causal, zero-init depthwise residual FIR inside this HSTU-style evaluation
apparatus, not as a broad first use of causal/local convolution.

### Commands And Evidence Checked

- `_bestrec_run\.venv\Scripts\python.exe _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - Industrial_and_Scientific: `CONFIRMED`.
  - CDs_and_Vinyl: `CONFIRMED`.
  - Industrial paired deltas: `+0.00243`, `+0.00196`, `+0.00191`, `+0.00287`,
    `+0.00284`; mean `+0.00240`, 95% t-CI `[+0.00183, +0.00297]`, positive
    seeds `5/5`.
  - CDs paired deltas: `+0.00539`, `+0.00638`, `+0.00617`, `+0.00498`,
    `+0.00540`; mean `+0.00566`, 95% t-CI `[+0.00493, +0.00639]`, positive
    seeds `5/5`.
- `FIR_BREADTH_RESULTS.md`
  - Contains the same mechanical adjudication block and frozen claim wording
    for both categories, but the file is currently untracked.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed, 0 mismatches, 0 untraceable; all 12 declared
    claim families sourced.
  - PASS: release manifest verification OK for 113 files.
  - PASS: MI dual gate; Office remains descriptive/VOID under prereg floor
    check.
- `rg "FIR_BREADTH|FIR-BREADTH|Industrial_and_Scientific|CDs_and_Vinyl|outcome pending|pending-campaign"`
  - `PAPER_SUBMISSION.md`, `paper_tex/sections/04-experiments.tex`, and
    `paper_tex/tables/table_datasets41.tex` still label the FIR-BREADTH rows as
    pending and say no result from them is claimed.
  - `PAPER_SUBMISSION.md` / `paper_tex/sections/06-discussion.tex` still say
    other categories are untested.
- Structured JSON parse of completed CDs_and_Vinyl files:
  - Filter NDCG@10 by seed: `0.066173`, `0.066262`, `0.066081`, `0.065990`,
    `0.065889`.
  - No-filter NDCG@10 by seed: `0.060778`, `0.059880`, `0.059913`,
    `0.061013`, `0.060494`.
  - Every inspected result manifest records `git_dirty_tracked=true` at
    `f50c7fdd6eb821a7c4012ea5abcd53662d691424`.
- `paper_tex/hygiene_scan_output.txt`
  - PASS: `PAPER_TORS.pdf`, 39 pages, 0 placeholder/forbidden-claim failures.
- `pdfinfo`
  - Not usable in this shell (`The system cannot find the path specified.`), so
    no fresh external page-count extraction was recorded this run.

### Confirmed Problems

1. **The paper is now stale relative to its own workspace evidence.** Both
   FIR-BREADTH categories are confirmed under the frozen rule, but the
   manuscript still presents the campaign as pending and outside the paper's
   result set.
2. **The campaign cannot yet be cited as top-journal-grade evidence.** The
   adjudication file and underlying scripts/results/raw-data directories are
   untracked, the result manifests record dirty tracked state, and the release
   manifest/artifact gate has not been extended to this campaign.
3. **Office V3's clean-tree rule changed in an uncommitted erratum.** The new
   erratum exempts audit/response logs from the dirty-tree condition. No Office
   V3 run artifacts or live processes were found, so this appears pre-run, but
   it is only defensible if committed before the first V3 run and kept narrow.
4. **The frozen claim wording is narrow and must stay narrow.** The admissible
   wording is only "paired 5-seed improvement on <category>, transplanted with
   zero per-category tuning, positive with a 95% CI excluding zero." It is not a
   comparator claim, not an SOTA claim, and not evidence for all categories.
5. **The causal FIR related-work boundary remains under-cited.** The manuscript
   still needs Caser/NextItNet/cheap causal-convolution SR or equivalent local
   convolutional SR citations before "new left-causal FIR realization" is safe.
6. **SILLM4Rec exclusion is now a paper-readiness risk, not just a TODO.** ACM
   metadata says the paper uses three 5-core Amazon Reviews 2023 datasets and
   reports NDCG@10, so a reviewer may reasonably expect either inspection or a
   more cautious exclusion sentence.

### Confirmed Fixes Since Earlier Runs

- The prior "first to report numbers" / "only published work using AR2023"
  problem no longer appears in the searched manuscript/TeX sources.
- The 2026 AR2023-adjacent paragraph now covers SID-MLP, Latte, GrIT, ReSID,
  ChronoSID, Augment-or-Not, and DiffuReason with explicit comparability
  caveats and no comparative claim against concurrent arXiv work.
- The strict submission rebuild remains green despite the in-progress
  FIR-BREADTH materials being outside the printed-paper artifact graph.

### Plausible Risks Requiring Author Verification

- The authors need a scope decision: submit a pre-FIR-BREADTH snapshot, or make
  FIR-BREADTH a real result section/appendix with committed provenance and a
  regenerated paper/PDF. Leaving the current mixed state is the worst option.
- If FIR-BREADTH is integrated, the main paper must decide whether this is a
  short breadth note in limitations/results or a full result table. The latter
  requires new generated tables and manifest coverage.
- `FIR_BREADTH_RESULTS.md` appeared during/after the final run despite this
  audit using `--no-append`; verify whether the training driver or adjudicator
  created it intentionally before treating it as the official record.
- `PREREG_OFFICE_V3.md` Erratum E1 should be committed before any V3 run starts;
  otherwise the exemption could look like post-hoc relaxation after seeing a
  clean-tree failure.
- SILLM4Rec may still be non-comparable, but "accessible metadata did not
  establish..." is now only partially satisfying because the ACM abstract
  metadata is close enough to the paper's protocol family to invite reviewer
  scrutiny.

### External Fact-Check / Novelty Notes

- GrIT is an arXiv 2026 sequential-recommendation preprint; the manuscript's
  "concurrent arXiv-only" caveat is supported by the arXiv listing as checked in
  this run. Source: https://arxiv.org/abs/2602.19728
- DiffuReason's arXiv listing identifies it as a 2026 sequential-recommendation
  paper; the search/PDF snippet reports the manuscript-cited different
  Video-and-Games universe (`67,658` users, `25,535` items, `654,867`
  interactions), supporting the non-comparability note. Source:
  https://arxiv.org/abs/2602.09744
- Augment-or-Not's arXiv listing confirms it is a 2025 LLM-recommender
  benchmark; the paper's non-interchangeable-protocol citation is directionally
  appropriate. Source: https://arxiv.org/abs/2505.23053
- SILLM4Rec ACM metadata says its experiments use three 5-core Amazon Reviews
  2023 datasets and report NDCG@10, so it should not be dismissed without full
  protocol inspection. Source: https://dl.acm.org/doi/10.1145/3743093.3771011
- The earlier causal-convolution novelty warning still applies: Caser,
  NextItNet, and cheap causal-convolution SR are relevant prior art for any
  broad local/causal convolution phrasing. Sources:
  https://arxiv.org/abs/1809.07426, https://arxiv.org/abs/1808.05163,
  https://arxiv.org/abs/2211.01297

### Concrete Fixes To Make Next

1. Decide the FIR-BREADTH scope boundary before editing prose:
   - **Pre-breadth submission:** remove or archive untracked FIR-BREADTH
     artifacts from the submitted/deposit boundary and keep the paper's pending
     language accurate for the submitted snapshot.
   - **Integrated submission:** commit/adjudicate/manifest the entire campaign,
     regenerate tables/PDFs, and update all pending/untested language.
2. If integrated, add one narrowly worded FIR-BREADTH result paragraph/table:
   Industrial `+0.00240` CI `[+0.00183,+0.00297]`; CDs `+0.00566` CI
   `[+0.00493,+0.00639]`; both 5/5 positive; explicitly "internal paired
   filter-vs-no-filter, zero per-category tuning, no comparator/SOTA claim."
3. Commit or deliberately exclude `FIR_BREADTH_RESULTS.md`,
   `_bestrec_run/adjudicate_fir_breadth.py`, run scripts, prep/encoding
   scripts, raw-data provenance, JSONs, user sidecars if intended, and any
   manifest updates as a single coherent evidence boundary.
4. Commit `PREREG_OFFICE_V3.md` Erratum E1 before any Office V3 execution, or
   remove it and keep the original strict clean-tree rule. Do not run V3 while
   the pre-registration is dirty.
5. Repair causal FIR novelty wording and references by adding convolutional SR
   prior art before FMLP/BSARec, then narrow the claim to this specific
   zero-init left-causal residual FIR in this artifact-gated setting.
6. Obtain/inspect SILLM4Rec full text or soften the exclusion to:
   "SILLM4Rec is adjacent AR2023 5-core work, but we have not yet verified
   full-catalog LLOO comparability; we therefore make no claim against it."

### Open Questions

- Should FIR-BREADTH be incorporated before submission, or treated as future
  work outside the current paper snapshot?
- If incorporated, should Office V3 remain pending in the same paragraph, or
  should the paper separate "confirmed internal breadth" from "Office
  comparator-facing pre-registration still pending/VOID history"?
- Is the Office V3 Erratum E1 author-approved and intentionally pre-run, or was
  it generated by an automated responder that should not define the protocol?
- Is there institutional access to the SILLM4Rec PDF, or should the authors
  contact the authors for protocol details?

### Running Checklist

- [x] Locate canonical manuscript source and PDF.
- [x] Read automation memory and prior cumulative audit.
- [x] Re-run strict submission rebuild.
- [x] Wait for final CDs_and_Vinyl no-filter seed to finish.
- [x] Re-run FIR-BREADTH mechanical adjudicator after all 20 runs completed.
- [x] Check manuscript/TeX for stale pending/untested language.
- [x] Check current related-work coverage for recent AR2023-adjacent papers.
- [x] Inspect unexpected `PREREG_OFFICE_V3.md` tracked diff.
- [x] Update the cumulative audit with current findings.
- [ ] Decide pre-breadth vs integrated-scope submission boundary.
- [ ] Commit/manifest or deliberately exclude FIR-BREADTH artifacts.
- [ ] Commit or remove Office V3 Erratum E1 before any V3 run.
- [ ] Repair causal-convolution prior-art boundary.
- [ ] Inspect SILLM4Rec full protocol or soften exclusion wording.

## Audit Run - 2026-07-13 05:40 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `f50c7fdd` (`Respond to
  PAPER_REVIEW_AUDIT run 23:39: 4.1 role table + count definitions`).
- Tracked working tree before this run: `PAPER_REVIEW_AUDIT.md` modified; no
  tracked manuscript or TeX edits detected after the 02:41 audit.
- Active untracked FIR-BREADTH artifacts changed after 02:41:
  - CDs_and_Vinyl filter seeds `20260713`-`20260717` are now complete.
  - CDs_and_Vinyl no-filter seeds `20260713`-`20260714` are complete.
  - CDs_and_Vinyl no-filter seed `20260715` appears active: `uv`/`python`
    process started 05:19 and `run_FIRB_CDs_and_Vinyl_nofilter_seed20260715.log`
    was at epoch 14 during inspection.
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/sections/*`, `paper_tex/tables/*`,
  `paper_tex/references.bib`, `PREREG_FIR_BREADTH.md`, FIR-BREADTH JSON/log
  artifacts, and the existing cumulative audit.

### Verdict

**The paper itself still builds cleanly, but top-journal readiness is blocked by
two live issues: moving-scope evidence and an incomplete novelty boundary.**
The printed paper can be defended only as a pre-FIR-BREADTH snapshot. If the
new breadth evidence is included, Industrial_and_Scientific must be integrated
with full provenance and CDs_and_Vinyl must remain VOID until all pairs are
complete and mechanically adjudicated. Separately, the causal FIR novelty
boundary needs repair: the manuscript acknowledges bidirectional frequency
filters but not earlier convolutional/causal-convolution sequential
recommenders.

### Commands And Evidence Checked

- `_bestrec_run\.venv\Scripts\python.exe _bestrec_run\adjudicate_fir_breadth.py --no-append`
  - Industrial_and_Scientific: `CONFIRMED`.
  - Paired deltas remain `+0.00243`, `+0.00196`, `+0.00191`, `+0.00287`,
    `+0.00284`; mean `+0.00240`, 95% t-CI `[+0.00183, +0.00297]`, positive
    seeds `5/5`.
  - CDs_and_Vinyl: `VOID(incomplete)` with 7/10 runs present; missing no-filter
    seeds `20260715`-`20260717`.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed, 0 mismatches, 0 untraceable; all 12 declared
    claim families sourced.
  - PASS: release manifest verification OK for 113 files.
  - PASS: MI dual gate; Office remains descriptive/VOID under prereg floor
    check.
- Structured JSON parse of completed CDs_and_Vinyl FIR-BREADTH files:
  - Filter complete: seeds `20260713`-`20260717`, NDCG@10 `0.066173`,
    `0.066262`, `0.066081`, `0.065990`, `0.065889`.
  - No-filter complete: seeds `20260713`-`20260714`, NDCG@10 `0.060778`,
    `0.059880`.
  - Completed paired deltas: seed `20260713` `+0.00539`; seed `20260714`
    `+0.00638`.
  - All completed CDs result manifests inspected here record
    `git_dirty_tracked=true` at commit `f50c7fdd`.
- `rg "FIR_BREADTH|Industrial_and_Scientific|CDs_and_Vinyl|untested|pending"`
  - `PAPER_SUBMISSION.md`, `paper_tex/sections/04-experiments.tex`, and
    `paper_tex/tables/table_datasets41.tex` still label Industrial and CDs as
    pending.
  - `PAPER_SUBMISSION.md` and `paper_tex/sections/06-discussion.tex` still say
    other categories are untested.
- `rg "cheap causal|causal convolution|Caser|NextItNet|2211\.01297|WEARec"`
  - No local citation/prose hit in `PAPER_SUBMISSION.md`, `paper_tex/sections`,
    or `paper_tex/references.bib`.
- `paper_tex/hygiene_scan_output.txt`
  - Latest scan remains PASS: 39 pages, 0 placeholder/forbidden-claim failures.

### Confirmed Problems

1. **CDs_and_Vinyl is still void, despite favorable-looking partials.** The
   frozen rule requires five paired differences. Reporting the two completed
   positive pairs would be selective-peeking, especially because the remaining
   no-filter arm is still running.
2. **The current manuscript is stale relative to the workspace.** Industrial is
   adjudicable and confirmed; CDs is partially run and void. The paper still
   says both are pending and other categories are untested.
3. **The causal FIR novelty paragraph omits convolutional SR prior art.** Caser,
   NextItNet-style holed/dilated convolution, and cheap causal-convolution
   self-attentive SR all weaken a claim that the "left-causal FIR realization"
   is new unless the paper distinguishes its much narrower contribution.
4. **FIR-BREADTH is not yet provenance-clean.** The adjudicator/scripts/results
   remain untracked, no official adjudication record was appended, and all
   completed CDs result manifests inspected in this run have dirty tracked
   state.
5. **The pre-registration's "script committed with the campaign" promise is not
   presently true in the working tree.** `adjudicate_fir_breadth.py` is
   untracked, so the campaign cannot yet support a methodology-first
   submission without repository hygiene work.

### Plausible Risks Requiring Author Verification

- If no-filter seed `20260715` finishes after this audit, the current section
  will immediately become stale. That is fine for an hourly audit, but the paper
  must not be submitted while the evidence boundary is moving.
- The large partial CDs deltas may tempt an early breadth claim. A strict
  reviewer will treat that as cherry-picking unless the official 5-pair
  adjudicator result is recorded and all missing counterparts are accounted for.
- The causal FIR contribution can probably survive if rewritten as "a
  zero-init, depthwise, left-causal residual FIR inserted before an HSTU-style
  stack under all-position full-catalog AR2023 LLOO," but not as a broad first
  use of causal/local convolution for sequential recommendation.
- The methodology-led framing raises the standard for all of the above. A
  normal empirical paper might get away with a late appendix note; this paper's
  stated contribution is that it does not.

### External Fact-Check / Novelty Notes

- `Self-Attentive Sequential Recommendation with Cheap Causal Convolutions`
  (arXiv:2211.01297) explicitly proposes a self-attentive SR model using causal
  convolutions to capture local item context for attention and sequence
  embedding. Source: https://arxiv.org/abs/2211.01297
- Caser (`Personalized Top-N Sequential Recommendation via Convolutional
  Sequence Embedding`, WSDM 2018) uses convolutional filters over recent item
  sequences to learn local sequential patterns. Source:
  https://arxiv.org/abs/1809.07426
- NextItNet (`A Simple Convolutional Generative Network for Next Item
  Recommendation`) uses holed/dilated convolutional layers to model short- and
  long-range item dependencies for next-item recommendation. Source:
  https://arxiv.org/abs/1808.05163
- WEARec (AAAI 2026) lists a broader frequency-SR lineage including FMLP-Rec,
  SLIME4Rec, FEARec, BSARec, and FamouSRec, supporting a broader related-work
  sentence if the manuscript keeps frequency/time-frequency claims prominent.
  Source: https://arxiv.org/html/2511.07028v1
- WPGRec remains a relevant 2026 time-frequency sequential-recommendation
  comparator/context paper and is already cited; it should stay framed as
  related prior art, not an apples-to-apples AR2023 comparator. Source:
  https://arxiv.org/abs/2604.21305

### Concrete Fixes To Make Next

1. Rewrite the FIR novelty boundary everywhere it appears (abstract,
   introduction, Table 0, method, conclusion) to include the convolutional SR
   line. Suggested boundary: "local/causal convolutional sequence modeling and
   frequency filtering are prior art; our contribution is the zero-init gated
   depthwise left-causal FIR residual placed before an HSTU-style stack and
   artifact-gated under AR2023 full-catalog LLOO."
2. Add references and Table 0/prose distinctions for Caser, NextItNet or an
   equivalent dilated-convolution SR source, and cheap causal-convolution SR.
3. Decide the FIR-BREADTH evidence boundary before any submission package:
   either freeze the paper as pre-breadth and exclude these artifacts, or wait
   for all CDs counterparts, run the official adjudicator append, commit/hash
   scripts/results/provenance, and update the manuscript/PDF.
4. Do not mention the two positive CDs pairs in manuscript prose until the
   missing no-filter seeds are complete and the frozen rule returns a category
   verdict.
5. If FIR-BREADTH is integrated, use only the frozen internal-paired wording and
   keep it out of comparator/SOTA claims.

### Open Questions

- Is the current intended submission snapshot pre-FIR-BREADTH, or should the
  paper wait for the active CDs no-filter sequence to finish?
- If FIR-BREADTH is integrated, should dirty-tracked runs be accepted with code
  hashes and disclosure, or rerun from a clean committed boundary?
- Should WEARec/FamouSRec/SLIME4Rec be added only to related work, or also to
  Table 0's novelty-boundary row?

### Running Checklist

- [x] Read automation memory state.
- [x] Locate canonical manuscript source, TeX derivative, PDF, figures/tables,
      preregistration, result files, and cumulative audit.
- [x] Check files modified after the previous audit.
- [x] Re-adjudicate FIR-BREADTH in no-append mode.
- [x] Re-run strict manuscript artifact rebuild.
- [x] Parse completed CDs_and_Vinyl FIR-BREADTH JSONs and paired deltas.
- [x] Confirm manuscript still says Industrial/CDs pending and other categories
      untested.
- [x] Fact-check causal/local-convolution and frequency-SR novelty context
      against primary sources.
- [x] Update this cumulative audit.
- [ ] Add missing causal-convolution/convolutional-SR prior-art citations.
- [ ] Decide whether FIR-BREADTH enters the submission or remains excluded.
- [ ] Complete/officially adjudicate CDs_and_Vinyl before any breadth wording.

## Audit Run - 2026-07-13 02:41 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Tracked working tree: `PAPER_REVIEW_AUDIT.md` modified before this run; no
  manuscript/source edits made by this audit.
- No commits after the previous automation cutoff (`2026-07-12T15:37:31Z`).
- Untracked active files include FIR-BREADTH/Office V3 adjudicators and driver
  scripts, raw-data directories for Industrial/CDs, 10 Industrial FIR-BREADTH
  result JSONs, one CDs filter result, and a smoke result.

### Verdict

**The printed paper still passes its artifact gate, but the workspace has moved
past the paper's stated FIR-BREADTH status.** Industrial_and_Scientific now
mechanically confirms the causal FIR filter under the frozen internal paired
rule. CDs_and_Vinyl is incomplete/void. The top-journal risk is no longer
"partial result contamination"; it is scope and provenance: the paper says
pending/untested while the workspace contains an untracked favorable confirmed
result and an incomplete companion category.

### Commands And Evidence Checked

- `_bestrec_run/.venv/Scripts/python.exe _bestrec_run/adjudicate_fir_breadth.py --no-append`
  - Industrial_and_Scientific: `CONFIRMED`.
  - Per-seed NDCG@10 deltas: `+0.00243`, `+0.00196`, `+0.00191`,
    `+0.00287`, `+0.00284`.
  - Paired mean `+0.00240`, sd `0.00046`, 95% t-CI
    `[+0.00183, +0.00297]`, positive seeds `5/5`.
  - CDs_and_Vinyl: `VOID(incomplete)` with 1/10 runs present.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed; 0 mismatch; 0 untraceable; all 12 claim
    families sourced.
  - PASS: release manifest verification for 113 files.
  - PASS: MI V2 dual gate.
  - PASS/VOID-as-designed: Office descriptive adjudication.
- Source/code inspection:
  - `paper_tex/sections/04-experiments.tex` and `paper_tex/tables/table_datasets41.tex`
    still label Industrial_and_Scientific and CDs_and_Vinyl as pending.
  - `paper_tex/sections/06-discussion.tex` still says other categories are
    untested.
  - `_bestrec_run/run_sasrec_sbert.py` implements the FIR as left-padded
    depthwise Conv1d on right-padded sequences, supporting the leak-free claim.
- `git status --short`
  - Confirms the breadth result files, adjudicator, driver/prep scripts, and raw
    data are untracked.
- `paper_tex/hygiene_scan_output.txt`
  - Latest recorded scan passes: 39 pages, 0 placeholder/forbidden failures.

### Confirmed Problems

1. **Stale paper/workspace status.** The paper's pending/untested language is no
   longer true of the workspace if these new artifacts are part of the
   submitted evidence package.
2. **Incomplete paired campaign.** CDs_and_Vinyl is currently void by the
   campaign's own rule; it cannot be quietly ignored if Industrial is used.
3. **Untracked campaign boundary.** FIR-BREADTH evidence is not yet in the
   repository/release manifest/artifact graph. This undercuts a methodology-led
   paper unless fixed or explicitly excluded.
4. **Adjudication not recorded.** I used `--no-append` to avoid changing
   `FIR_BREADTH_RESULTS.md`; that file still does not exist unless another
   process creates it later. The confirmed Industrial verdict is therefore
   audit-observed, not yet campaign-recorded.

### Plausible Risks Requiring Author Verification

- Some FIR-BREADTH result manifests were generated with `git_dirty_tracked=true`
  because this audit file was dirty. The code hashes may still prove training
  identity, but a reviewer will expect a clean explanation if the result becomes
  confirmatory evidence.
- The positive Industrial result strengthens breadth for the FIR module but
  should not be allowed to inflate the paper into a general cross-category
  recommender claim. It is an internal paired filter-vs-no-filter result, not a
  comparator or SOTA result.
- The paper's "trustworthy-evaluation apparatus" framing raises the bar for
  process hygiene. Untracked favorable artifacts are more damaging under this
  framing than they would be in an ordinary empirical paper.

### External Fact-Check / Novelty Notes

- GrIT is a real 2026 arXiv preprint; its table reports Video Games NDCG@10
  `0.0588` under its listed setup. Source:
  https://arxiv.org/html/2602.19728v1
- WPGRec is a real 2026 time-frequency sequential-recommendation paper and the
  arXiv page says accepted to SIGIR 2026. This supports citing it as later
  frequency/time-frequency prior art, not as an apples-to-apples comparator.
  Source: https://arxiv.org/abs/2604.21305
- DiffuReason uses a different AR2023 "Video & Games" universe; the arXiv text
  lists 67,658 users / 25,535 items / 654,867 interactions, supporting the
  manuscript's non-comparability caveat. Source:
  https://arxiv.org/html/2602.09744
- Augment or Not? uses Amazon'23 Musical Instruments and Industrial and
  Scientific under 5-core leave-one-out, supporting the manuscript's
  "AR2023-adjacent, non-interchangeable" framing. Source:
  https://arxiv.org/html/2505.23053v1
- The Amazon Reviews 2023 project page confirms the dataset is collected in
  2023 and includes reviews, metadata, and links, with 571.54M reviews and
  standard splitting resources. Source: https://amazon-reviews-2023.github.io/

### Concrete Fixes To Make Next

1. Decide whether FIR-BREADTH is inside or outside the current submission. If
   outside, exclude the untracked result files from the evidence bundle and keep
   the paper frozen as pre-breadth.
2. If FIR-BREADTH is inside, create the official adjudication record, commit the
   scripts/results/provenance, add manifest/artifact-gate coverage, and update
   Section 4.1/6.4 to say Industrial confirmed and CDs incomplete/void.
3. Preserve narrow wording: "Industrial_and_Scientific internal paired 5-seed
   filter-vs-no-filter improvement" only. No external comparator language.
4. Add a provenance note for dirty tracked state or rerun under a clean
   committed boundary if pristine confirmation is required.
5. Re-run PDF hygiene after any manuscript integration of FIR-BREADTH.

### Running Checklist

- [x] Read automation memory state.
- [x] Locate canonical TeX/Markdown/PDF sources and artifact files.
- [x] Inspect current audit file and preserve previous uncommitted sections.
- [x] Check working tree and new untracked campaign artifacts.
- [x] Run FIR-BREADTH adjudicator in no-append mode.
- [x] Run strict manuscript artifact rebuild.
- [x] Inspect FIR implementation for left-causal padding.
- [x] Fact-check recent-literature and dataset framing against primary sources.
- [x] Update this cumulative audit.
- [ ] Decide whether FIR-BREADTH enters the paper or remains excluded.
- [ ] Commit/hash campaign artifacts before any FIR-BREADTH claim is submitted.

## Audit Run - 2026-07-13 01:42 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` /
  `f50c7fdd6eb821a7c4012ea5abcd53662d691424`.
- Tracked manuscript/PDF/LaTeX diff since the 00:40 audit: none.
- Tracked working tree: `PAPER_REVIEW_AUDIT.md` modified.
- Untracked active-program files include the FIR-BREADTH and Office V3
  adjudicators, driver/prep scripts, raw-data provenance, 5 filter result JSONs,
  3 no-filter result JSONs, and the smoke result.
- Active process observed: `run_impact_program.sh` had advanced to
  `FIRB Industrial_and_Scientific nofilter seed 20260716`; I did not stop or
  modify it.

### Verdict

**The manuscript still has no new printed contradiction: it says the
FIR-BREADTH campaign is pending, and no breadth result is claimed.** The
rejection risk is now process contamination. Partial outcomes have been observed
before the untracked-tooling and dirty-tree defects were repaired. In a
methodology-first paper, that is central: the campaign can still be reported
honestly, but it should not be sold as a pristine confirmatory extension unless
it is restarted or accompanied by a blunt provenance erratum.

### Commands And Evidence Checked

- `git status --short --untracked-files=all`
  - Confirms only `PAPER_REVIEW_AUDIT.md` is tracked-dirty, while the impact
    driver, adjudicators, raw-data provenance, and FIR-BREADTH results are
    untracked.
- `git diff --name-only -- PAPER_SUBMISSION.md PAPER_DRAFT.md
  PAPER_SUBMISSION.pdf CANONICAL_SUBMISSION.md paper_tex`
  - Empty: the printed paper sources/artifacts have not changed since the 00:40
    strict rebuild/PDF-hygiene check.
- `_bestrec_run/impact_program.log`
  - The program began at `2026-07-13 00:25:03` from a dirty tracked tree
    containing manuscript, PDF, LaTeX, table, and reference changes.
  - Later FIR-BREADTH runs continued with `PAPER_REVIEW_AUDIT.md` dirty.
  - As of this audit, seed 20260716 no-filter was running.
- FIR-BREADTH JSON manifests:
  - Filter seeds 20260713-17 are present; no-filter seeds 20260713-15 are
    present.
  - Full-catalog `n_eval=50,985` for all observed Industrial_and_Scientific
    results checked.
  - Observed paired best-test NDCG@10:
    - seed 20260713: filter `0.033774047`, no-filter `0.031343612`,
      delta `+0.002430`.
    - seed 20260714: filter `0.033409370`, no-filter `0.031453663`,
      delta `+0.001956`.
    - seed 20260715: filter `0.032943585`, no-filter `0.031031976`,
      delta `+0.001912`.
  - Manifest dirtiness: filter 20260713 records `git_dirty_tracked=false`;
    filter 20260714-17 and no-filter 20260713-15 record
    `git_dirty_tracked=true`.
- `FIR_BREADTH_RESULTS.md`
  - Not present at audit time, so no mechanical adjudication block has been
    recorded yet.

### External Fact-Check / Source Notes

- The official AR2023 5-core page lists the relevant rounded category
  statistics: Industrial_and_Scientific 51.0K users / 25.8K items / 412.9K
  ratings; CDs_and_Vinyl 123.9K / 89.4K / split rows 1.3M train plus 123.9K
  validation/test; Musical_Instruments 57.4K / 24.6K / 511.8K; Office_Products
  223.3K / 77.6K / 1.8M; Video_Games 94.8K / 25.6K / 814.6K. Source:
  https://amazon-reviews-2023.github.io/data_processing/5core.html
- The AmazonReviews2023 benchmark README defines `last_out` as leave-last-out:
  latest review for test, second-latest for validation, rest for training, and
  `rating_only` as deduplicated user/item/rating/timestamp records with 0-core
  or 5-core filtering. Source:
  https://github.com/hyp1231/AmazonReviews2023/blob/main/benchmark_scripts/README.md
- HSTU-BLaIR's repository reports the comparator values used in the manuscript:
  Video_Games HSTU-BLaIR NDCG@10 `0.0760`, Office_Products `0.0271`, and
  Musical_Instruments `0.0406`, with a warning that reproduction can vary
  within a small margin. Source: https://github.com/snapfinger/HSTU-BLaIR

### Confirmed Problems

1. **The active FIR-BREADTH campaign is already result-exposed while its
   adjudication/run tooling is outside the committed boundary.** This violates
   the spirit, and likely the literal reviewer reading, of the prereg's
   "adjudication script committed with the campaign" sentence.
2. **The run driver intentionally allows dirty tracked state for FIR-BREADTH.**
   That may have been acceptable engineering convenience before the paper led
   with methodology; it is not strong enough for a top-journal confirmatory
   claim.
3. **Partial positive results are now known.** Even if the final 5-seed rule
   later confirms, the decision to keep, report, or expand the campaign is now
   post-outcome unless the authors explicitly freeze that choice or restart.
4. **The same dirty audit file will likely block Office V3.** The driver uses a
   hard clean-tree check for Office V3; unless the tracked tree is cleaned
   before the FIR-BREADTH segment completes, Office V3 should exit under its
   own condition 3 rather than run.

### Concrete Fixes To Make Next

1. For a pristine confirmatory claim: stop after the current run family,
   classify these Industrial/CDs outputs as contaminated/exploratory, commit
   the driver/adjudicators/prep scripts/provenance, and restart with new seeds.
2. For a less conservative but honest route: write a provenance erratum before
   any paper edit, listing the dirty launch state, the untracked tooling, every
   result manifest's `git_dirty_tracked` flag, code hashes, and the exact point
   at which partial results became visible.
3. Do not update `PAPER_SUBMISSION.md`, release notes, or responses with
   FIR-BREADTH numbers until all 5 paired seeds are complete and the mechanical
   adjudicator has run under a committed version.
4. If Office V3 is intended to proceed in the current driver, clean the tracked
   tree first; otherwise let the hard check stop it and record that stop as
   designed behavior.

### Open Questions

- Will the authors prefer a clean restart over a provenance erratum for
  FIR-BREADTH?
- Should FIR-BREADTH's driver be changed to hard-fail on dirty tracked state,
  matching Office V3, now that process integrity is the lead contribution?
- Should the pre-registration be amended to say "embedded code hashes" are
  sufficient, or is that amendment itself post-outcome and therefore a reason
  to restart?

### Running Checklist

- [x] Read automation memory state.
- [x] Preserve the existing 00:40 audit section.
- [x] Recheck active workspace and untracked artifacts.
- [x] Inspect current FIR-BREADTH result manifests and log.
- [x] Verify no tracked manuscript/PDF/LaTeX diff since the 00:40 artifact
      gate.
- [x] Fact-check AR2023 split/stat claims and HSTU-BLaIR comparator values
      against external sources.
- [ ] Resolve FIR-BREADTH governance before using any breadth result.
- [ ] Re-run strict build/PDF hygiene after the active GPU program is stopped
      or finished.
- [ ] Decide whether Office V3 should be allowed to stop on the clean-tree hard
      check or be relaunched from a clean boundary.

## Audit Run - 2026-07-13 00:40 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `f50c7fdd`
- Supplied last-run cutoff: `2026-07-12T13:35:29.596Z`.
- Commits after cutoff:
  - `a7d6733d` Impact-revision program: pre-registrations committed BEFORE any
    run.
  - `791de36a` Approach (C): methodology-first reframe -- retitled, apparatus
    leads, claims unchanged.
  - `14c3df2b` Regenerate RELEASE_MANIFEST at the reframe boundary.
  - `bbb728fe` Round-15: Section 4.1 rewritten as role-based dataset table;
    count definitions fixed; brittle phrasing.
  - `8ccd04f1` Regenerate RELEASE_MANIFEST at round-15 boundary.
  - `f50c7fdd` Respond to PAPER_REVIEW_AUDIT run 23:39.
- Tracked working tree at audit time: clean.
- Untracked/currently outside git boundary: impact-program scripts, two
  adjudicators, first FIR-BREADTH result, smoke result, and new raw-data
  downloads/provenance files.
- A FIR-BREADTH run was active during this audit:
  `Industrial_and_Scientific filter seed 20260714` (Python process observed at
  00:40, log at epoch 3/20). I did not stop or modify it.

### Verdict

**The previous hard manuscript defect is fixed, and the printed paper still
passes its strict artifact gate.** Section 4.1 now describes the dataset roles
and total counts clearly. The new top-journal rejection risk is not a table
value; it is governance around the newly launched impact/FIR-BREADTH program.
After the methodology-first reframe, process integrity is now part of the
paper's lead claim. The campaign currently has untracked adjudication/run
tooling and a start-of-run dirty-tree ambiguity. Those defects must be resolved
before any breadth result is printed as confirmatory.

### Commands And Evidence Checked

- `git log --oneline --decorate --since='2026-07-12T13:35:29Z'`
  - Shows the impact pre-registrations, methodology reframe, Section 4.1 repair,
    manifest regenerations, and response commit after the supplied cutoff.
- `git status --short --untracked-files=all`
  - Tracked tree clean, but untracked:
    `_bestrec_run/adjudicate_fir_breadth.py`,
    `_bestrec_run/adjudicate_office_v3.py`,
    `_bestrec_run/encode_impact_titles.py`,
    `_bestrec_run/prep_impact_data.py`,
    `_bestrec_run/run_impact_program.sh`,
    `_bestrec_run/results_FIRB_Industrial_and_Scientific_filter_seed20260713.json`,
    `_bestrec_run/smoke_FIRB_IS_seed1.json`, and new raw-data provenance files.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12 claim
    families sourced.
  - PASS: release manifest verification, MI V2 dual gate, Office
    descriptive/VOID adjudication.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py paper_tex/PAPER_TORS.pdf`
  - PASS: 39 pages; 0 placeholder/forbidden-claim failures.
- Source inspection:
  - `paper_tex/sections/04-experiments.tex` now states total 5-core
    interactions and the LLOO count rule.
  - `paper_tex/tables/table_datasets41.tex` includes all active/pending
    categories with roles and total counts.
  - `rg "two AR2023|~830k|5.17M|unreviewed concurrent"` no longer finds the old
    Section 4.1 defects or brittle "unreviewed concurrent" phrasing.
  - `rg "814,585"` still finds the comparator-paper count in Section 5.1; treat
    as a labeling/readability risk, not a reopened Section 4.1 defect.
- Local row-count checks:
  - Industrial_and_Scientific: total 412,947; train 310,977; valid 50,985; test
    50,985.
  - CDs_and_Vinyl: total 1,552,764; train 1,305,012; valid 123,876; test
    123,876.
- Impact-program evidence:
  - `_bestrec_run/impact_program.log` says preconditions passed, then printed a
    dirty tracked tree at `2026-07-13 00:25:03`, warned, and began
    `FIRB Industrial_and_Scientific filter k8 seed 20260713`.
  - `_bestrec_run/results_FIRB_Industrial_and_Scientific_filter_seed20260713.json`
    records `git_commit=f50c7fdd`, `git_dirty_tracked=false`, full-catalog
    `n_eval=50,985`, and best-by-validation test NDCG@10 0.033774. Because the
    run started before the commit boundary but recorded clean status at write
    time, the manifest does not by itself prove clean start-state provenance.
  - `_bestrec_run/adjudicate_fir_breadth.py` implements a sensible mechanical
    paired 5-seed rule, but it is untracked, contradicting
    `PREREG_FIR_BREADTH.md`'s statement that adjudication is committed with the
    campaign.

### Confirmed Fixes Since Prior Audit

1. **Section 4.1 role/scope inconsistency is fixed.**
   - The old "two categories" phrasing is gone.
   - Office is explicitly descriptive/VOID, not confirmatory.
   - Industrial_and_Scientific and CDs_and_Vinyl are explicitly pending, with no
     result claimed in this version.
2. **Dataset counts in the main table are now total counts.**
   - The table's Industrial/CDs counts match official rounded AR2023 statistics
     and the local exact row counts.
   - The LLOO relationship `train = total - 2 * users` is stated in Section 4.1.
3. **Brittle "unreviewed concurrent work" wording is removed.**
   - The paper now uses "concurrent arXiv-only work" and "status as of the
     access date" style phrasing.
4. **Current printed-paper artifact gate remains green.**
   - The methodology reframe and Section 4.1 table did not break the 164-cell
     rebuild or TORS hygiene scan.

### Confirmed Problems

1. **The FIR-BREADTH adjudication and run tooling are not frozen in git even
   though the pre-registration says the adjudication script is committed with
   the campaign.**
   - This undermines the paper's lead process claim if any breadth result is
     later used.
   - Concrete fix: commit/hash the adjudicator, driver, data-prep script,
     encoder script, and raw-data provenance before adjudication; update
     `RELEASE_MANIFEST.json` once any result is printed. If strict confirmatory
     purity is required, void/restart with new seeds under a clean committed
     tooling boundary.
2. **The first FIR-BREADTH campaign run has start-state provenance ambiguity.**
   - Program log: dirty tracked tree at run launch.
   - Result JSON: clean tracked tree at result write.
   - Concrete fix: either treat the existing FIR-BREADTH run family as
     exploratory/contaminated, or add an explicit erratum proving that the dirty
     tracked diffs were documentation-only and that training-code hashes were
     identical from launch through write. A top-journal reviewer will likely
     prefer the former.
3. **Partial results exist while the paper says the campaign outcome is
   pending.**
   - This is currently acceptable because no breadth result is claimed, but the
     paper must not be edited to exploit the observed first seed. Once the
     campaign finishes, report confirmed/null/void symmetrically and manifest
     every printed value.

### Plausible Risks Requiring Author Verification

- **The methodology-first reframe raises the standard for process evidence.**
  It makes the paper more coherent, but also turns any process blemish into a
  central weakness. If the authors want this framing, they should harden the
  new campaign rules rather than allow warn-and-proceed dirty-tree behavior.
- **The 814,585 vs 814,586 interaction-count split may still annoy reviewers.**
  Keep the +/-1 comparator-pipeline caveat, but label Section 5.1's 814,585 as
  the HSTU-BLaIR-reported comparator count.
- **SILLM4Rec remains a direct-inspection item.** The current exclusion sentence
  is narrow enough, but final submission should either inspect the paper or keep
  the exclusion carefully metadata-scoped.
- **The currently running seed may finish while this audit section is being
  read.** Re-run the status checks before making any release/deposit decision.

### External Fact-Check / Novelty Notes

- Official Amazon Reviews 2023 5-core statistics list
  Industrial_and_Scientific at 51.0K users / 25.8K items / 412.9K ratings,
  CDs_and_Vinyl at 123.9K / 89.4K / 1.6M, Musical_Instruments at 57.4K /
  24.6K / 511.8K, Office_Products at 223.3K / 77.6K / 1.8M, and Video_Games at
  94.8K / 25.6K / 814.6K. Source:
  https://amazon-reviews-2023.github.io/data_processing/5core.html
- The AmazonReviews2023 benchmark README defines `rating_only` as user/item/
  rating/timestamp records, removes duplicate user-item reviews, applies
  k-core filtering, and defines `last_out` as leave-last-out with latest review
  for test, second-latest for validation, and the rest for train. Source:
  https://github.com/hyp1231/AmazonReviews2023/blob/main/benchmark_scripts/README.md
- HSTU-BLaIR's repository reports the comparator rows used by the paper:
  Video_Games HSTU-BLaIR NDCG@10 0.0760, Office_Products 0.0271, and
  Musical_Instruments 0.0406; it also warns that reproduction may vary by a
  small margin. Source: https://github.com/snapfinger/HSTU-BLaIR
- Ferrari Dacrema et al. support the paper's evaluation-trust motivation: their
  abstract says only 7 of 18 neural recommender algorithms were reproducible
  with reasonable effort, and 6 of those could often be beaten by simple
  heuristics. Source: https://arxiv.org/abs/1907.06902

### Concrete Fixes To Make Next

1. Decide whether the current FIR-BREADTH campaign is confirmatory or
   exploratory. For a top-journal confirmatory claim, the safest action is
   VOID/restart with a clean committed tool boundary and new seeds.
2. Commit the impact-program tooling and adjudicators before any further
   adjudication or Office V3 run is used as evidence.
3. Add a provenance erratum if any current FIR-BREADTH artifacts are retained:
   exact start/end commit, dirty tracked files at launch, code hashes, and why
   start-dirty did or did not void the claim.
4. Keep all breadth numbers out of the paper until the full paired 5-seed rule
   is adjudicated and the values are added to the artifact gate/manifest.
5. Label the Section 5.1 `814,585` interaction count as comparator-reported, or
   add a short parenthetical: local row total is 814,586; comparator pipeline
   reports 814,585.
6. Add one sentence in the methodology-reframe paragraph that this is an
   auditable case-study discipline, not a claim to have invented
   pre-registration, artifact evaluation, or standardized benchmarking.

### Open Questions

- Are the maintainers willing to void/restart FIR-BREADTH to preserve a clean
  confirmatory story, or should it be downgraded to exploratory evidence?
- Was the dirty tracked tree at FIR-BREADTH launch entirely documentation/PDF
  state, or did any code or generated table script that could affect claims
  differ from the eventual commit?
- Should the run driver enforce clean tracked tree for FIR-BREADTH just as it
  already does for Office V3, given the paper's new methodology-first framing?

### Running Checklist

- [x] Read automation memory.
- [x] Locate canonical manuscript sources and PDFs.
- [x] Check commits and working-tree state after the supplied cutoff.
- [x] Verify strict rebuild/provenance gate.
- [x] Verify TORS PDF hygiene scan.
- [x] Confirm Section 4.1 role table and total-count repair.
- [x] Verify new Industrial/CDs local row counts.
- [x] Fact-check AR2023 count/split claims and HSTU-BLaIR comparator values
      against external sources.
- [x] Inspect new impact pre-registration, driver, adjudicator, logs, and first
      result manifest.
- [ ] Resolve FIR-BREADTH untracked-tooling and start-dirty provenance risk
      before claiming any breadth result.
- [ ] Re-run audit after the active FIR-BREADTH job completes or is stopped.

## Audit Run - 2026-07-12 23:39 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `8d060297`
- Supplied last-run cutoff: `2026-07-12T12:35:58.679Z`.
- `git log --since="2026-07-12T12:35:58Z"` returned no commits. The tracked
  working tree was clean before and after this audit.
- Automation memory at start still described the 21:37 run's top watch items:
  the Section 3.2 HSTU/SASRec contradiction and stale WPGRec metadata.
- Canonical artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/sections/01-introduction.tex`,
  `paper_tex/sections/03-method.tex`,
  `paper_tex/sections/04-experiments.tex`,
  `paper_tex/sections/05-results.tex`,
  `paper_tex/sections/07-conclusion.tex`, `paper_tex/references.bib`,
  `paper_tex/tables/table0_novelty.tex`, local AR2023 5-core CSV splits, and
  the strict rebuild/provenance scripts.

### Verdict

**The two prior top blockers are repaired, and the artifact graph remains
green.** The remaining reviewer-facing problem is Section 4.1: it understates
the experimental scope ("two" categories) and mixes total interaction counts
with train-only counts. A strict reviewer can read this as sloppy protocol
description, even though the downstream results/provenance are internally
traceable.

### Commands And Evidence Checked

- `git status --short --branch`
  - Clean on `codex/bestrec-sota-results`.
- `git log --since="2026-07-12T12:35:58Z" --oneline --decorate --name-status`
  - No commits after the supplied cutoff.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12 declared
    claim families sourced.
  - PASS: release manifest verification, MI V2 dual gate, Office descriptive/
    VOID adjudication.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py paper_tex/PAPER_TORS.pdf`
  - PASS: 36 pages; 0 placeholder/forbidden-claim failures.
  - SOTA/paired-superiority mentions are negated or informational.
- PDF text extraction with `pypdf` through the repo `uv` environment
  - Both PDFs no longer contain "Our base model" or "2-layer Transformer
    encoder".
  - Both PDFs contain the new "Headline encoder" text.
  - Both PDFs contain WPGRec in references with non-stale accepted/SIGIR 2026
    wording, though not always in the exact same extracted string.
  - `PAPER_SUBMISSION.pdf` contains "partially resolves the open mechanism";
    the TORS PDF uses the more scoped "partial causal role" conclusion wording.
- Local CSV counts with `Measure-Object -Line`
  - Video_Games `rating_only`: 814,587 lines including header -> 814,586 rows.
  - Video_Games split rows: 625,062 train + 94,762 valid + 94,762 test =
    814,586.
  - Musical_Instruments `rating_only`: 511,837 lines including header ->
    511,836 rows.
  - Musical_Instruments split rows: 396,958 train + 57,439 valid + 57,439 test
    = 511,836.
  - Beauty_and_Personal_Care `rating_only`: 6,624,442 lines including header ->
    6,624,441 rows.
  - Beauty split rows: 5,165,289 train + 729,576 valid + 729,576 test =
    6,624,441.
  - Office_Products `rating_only`: 1,800,879 lines including header ->
    1,800,878 rows.
  - Office split rows: 1,354,262 train + 223,308 valid + 223,308 test =
    1,800,878.

### Confirmed Fixes Since Prior Audit

1. **Section 3.2 method contradiction is repaired.**
   - Source now describes shared item-feature construction, then the HSTU-style
     headline encoder, then the SASRec-SBERT baseline.
   - Section 4.3 points to the HSTU-style encoder and uses the same 4-layer
     configuration.
   - Rendered PDFs no longer expose the stale SASRec-as-headline wording.
2. **WPGRec metadata is repaired.**
   - `paper_tex/references.bib` now says WPGRec is accepted to SIGIR 2026.
   - `PAPER_SUBMISSION.pdf` renders "SIGIR 2026 (accepted; arXiv:2604.21305)".
   - `paper_tex/PAPER_TORS.pdf` renders "Accepted to SIGIR 2026".
3. **Mechanism rhetoric is materially toned down.**
   - The abstract now says the user-mode titration "partially resolves the open
     mechanism (under the thinning intervention's assumptions)".
   - The conclusion states that collaborative connectivity is "consistent with
     a partial causal role" and repeats that these are controlled interventions,
     not causal identification of the real-world generative process.

### Confirmed Problems

1. **Section 4.1 does not match the paper's current experimental scope.**
   - It says "We evaluate on two AR2023 5-core categories" and lists only
     Video_Games and Beauty_and_Personal_Care.
   - The abstract, Section 5, and conclusion make Musical_Instruments a
     headline cross-category confirmation. Office_Products also appears as a
     descriptive/VOID pre-registration result.
   - Concrete fix: rewrite Section 4.1 as a role-based dataset table with all
     categories used anywhere in the paper, including which are confirmatory,
     exploratory, appendix-only, or VOID/descriptive.
2. **Section 4.1 mixes interaction-count definitions.**
   - Video_Games is listed as "~830k interactions" while later Section 5.1 says
     814,585 and local data give 814,586 rows after header.
   - Beauty is listed as 5.17M interactions, which matches train-only rows, not
     total 5-core rows (6,624,441). A reader will not know whether counts mean
     total rating-only interactions or train interactions after LLOO.
   - Concrete fix: state both totals and split counts, or state only totals in
     Section 4.1 and move train counts to an appendix/protocol table.

### Plausible Risks Requiring Author Verification

- **SILLM4Rec is closer than a metadata-only footnote suggests.** ACM metadata
  says the paper experiments on three AR2023 5-core subdatasets, including
  Video_Games, and the GitHub repo describes generation of candidate product
  ranking tasks. That still does not prove identical full-catalog LLOO
  comparability, but it does make "excluded pending direct protocol inspection"
  the right stance.
- **"Unreviewed concurrent work" is a brittle phrase.** SID-MLP, Latte, and
  GrIT still look like arXiv-only works in the sources checked here, but peer
  review status can change. Prefer "concurrent arXiv works" if the sentence does
  not need a review-status claim.
- **Reader burden remains high.** The abstract is now more defensible, but it
  still carries many p-values, caveats, and mechanism claims. Table 2 remains
  valuable but dense.

### External Fact-Check / Novelty Notes

- WPGRec arXiv confirms the title, wavelet-packet/graph-enhanced framing, and
  "Accepted to SIGIR 2026" comment:
  https://arxiv.org/abs/2604.21305
- The SIGIR 2026 accepted-papers page also lists WPGRec:
  https://sigir2026.org/en-AU/pages/program/accepted-papers
- SID-MLP arXiv page shows only arXiv metadata and no accepted-venue comment in
  the opened page:
  https://arxiv.org/abs/2605.12617
- Latte arXiv page shows only arXiv metadata and no accepted-venue comment in
  the opened page:
  https://arxiv.org/abs/2605.06331
- GrIT search/open metadata remains arXiv-preprint style:
  https://arxiv.org/abs/2602.19728
- SILLM4Rec ACM/GitHub pages confirm MMAsia 2025 publication context and
  AR2023 5-core / candidate-ranking relevance, but not full-catalog LLOO
  equivalence from accessible metadata:
  https://dl.acm.org/doi/10.1145/3743093.3771011
  https://github.com/MKC-Lab/SILLM4Rec
- Official Amazon Reviews 2023 5-core statistics list Video_Games at 94.8K
  users, 25.6K items, 814.6K ratings; Musical_Instruments at 57.4K users,
  24.6K items, 511.8K ratings; Beauty_and_Personal_Care at 729.6K users,
  207.6K items, 6.6M ratings; Office_Products at 223.3K users, 77.6K items,
  1.8M ratings:
  https://amazon-reviews-2023.github.io/data_processing/5core.html
- The AmazonReviews2023 benchmark scripts define 5-core `rating_only` and
  `last_out` leave-last-out splits, with latest interaction as test,
  second-latest as validation, and remaining interactions as train:
  https://github.com/hyp1231/AmazonReviews2023/blob/main/benchmark_scripts/README.md

### Concrete Fixes To Make Next

1. Rewrite Section 4.1 as a dataset/protocol table with category role, total
   rows, train/valid/test rows, users, items, and which paper claims depend on
   the category.
2. Replace Video_Games "~830k" and later "814,585" with one consistent value:
   814,586 local rows, or 814.6K when rounded.
3. Decide whether Beauty's 5.17M should be labeled "train interactions" or
   replaced by total 6.62M in the dataset list.
4. Keep SILLM4Rec excluded only under the narrow protocol-inspection caveat, or
   inspect the ACM full text and add a short non-comparability sentence.
5. Before final submission, recheck whether SID-MLP, Latte, or GrIT acquired
   accepted-venue metadata; otherwise avoid "unreviewed" in favor of
   "concurrent arXiv".

### Open Questions

- Should Office_Products appear in the main dataset table as "VOID/descriptive"
  or be moved entirely to appendix/pre-registration material?
- Should the paper report both total and train-only interaction counts, or only
  totals in the main dataset description?
- Can the authors access the full SILLM4Rec ACM paper to audit candidate-set
  construction, ranking universe, and whether metrics are full-catalog LLOO?

### Running Checklist

- [x] Read automation memory.
- [x] Locate canonical manuscript sources and PDFs.
- [x] Check commits and tracked tree after the supplied last-run cutoff.
- [x] Verify strict rebuild/provenance gate.
- [x] Verify TORS PDF hygiene scan.
- [x] Confirm prior Section 3.2 methods fix in source and PDFs.
- [x] Confirm WPGRec SIGIR 2026 status in source and rendered references.
- [x] Fact-check current concurrent-work and SILLM4Rec status with external
  sources.
- [x] Verify local AR2023 category row counts and identify Section 4.1 scope/
  count inconsistency.

## Audit Run - 2026-07-12 21:37 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `3a346d86`
- Automation memory at start: no prior memory content was present at
  `$CODEX_HOME/automations/hourly-strict-paper-audit/memory.md`.
- Supplied last-run cutoff: `2026-07-12T10:34:56.879Z`.
- `git log --since="2026-07-12T10:34:56Z"` returned no commits; tracked working
  tree was clean before and after the strict rebuild.
- Canonical artifacts inspected: `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/sections/03-method.tex`,
  `paper_tex/sections/04-experiments.tex`, `paper_tex/sections/05-results.tex`,
  `paper_tex/sections/06-discussion.tex`, `paper_tex/sections/appendix-a.tex`,
  `paper_tex/references.bib`, `paper_tex/tables/TABLES_PROVENANCE.json`,
  `paper_tex/tables/table0_novelty.tex`, `_bestrec_run/hstu_results_manifest.json`,
  and representative result JSONs for VG/MI headline runs.

### Verdict

**Artifact/provenance gates are green and the previous MLP-adaptor contradiction
is repaired, but the current manuscript has a new high-salience methods
contradiction.** The paper's numerical story is traceable; the problem is that
Section 3.2 still reads like the headline model is a 2-layer SASRec/Transformer,
while every headline run and the artifact graph say the model is a 4-layer
HSTU-style encoder. A top-journal reviewer can cite this as an unclear or stale
method description even if all results are valid.

### Commands And Evidence Checked

- `git status --short --branch`
  - Clean on `codex/bestrec-sota-results`.
- `git log --since="2026-07-12T10:34:56Z" --oneline --decorate --name-status`
  - No commits after the supplied cutoff.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12 declared
    claim families sourced.
  - PASS: release manifest verification, MI V2 dual gate, Office descriptive/
    VOID adjudication.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py paper_tex/PAPER_TORS.pdf`
  - PASS: 36 pages; 0 placeholder/forbidden-claim failures.
  - SOTA mentions are informational and negated/non-claim contexts.
- PDF text extraction with `pypdf`
  - Both PDFs contain the repaired Section 6.1 language ("text content, not the
    projection layer") and Appendix A.1's "MLP adaptor by itself does NOT help".
  - Both PDFs no longer contain the stale phrase "only consistently-positive
    intervention".
  - Both PDFs still contain WPGRec; neither mentions SIGIR 2026 acceptance.
- Targeted source/result sweeps
  - `paper_tex/sections/03-method.tex`: "Our base model, SASRec-SBERT" and
    "2-layer Transformer encoder".
  - `paper_tex/sections/04-experiments.tex`: headline runs use HSTU-style
    encoder with `d_model 64, 4 layers, 2 heads, dropout 0.5`.
  - Representative result JSONs confirm `encoder: hstu`, `n_layers: 4`,
    `n_heads: 2`, `dropout: 0.5`.

### Confirmed Problems

1. **Method architecture description is internally inconsistent.**
   - Source conflict: Section 3.2 presents the "base model" as SASRec-SBERT
     with a 2-layer Transformer; Section 3.7 says the additions are defined on
     top of HSTU-style; Section 4.3 says all headline results use HSTU-style
     `4 layers`; result JSONs confirm HSTU/4-layer for the headline runs.
   - Why this matters: the paper asks reviewers to trust fine-grained
     architectural deltas. A stale method section undermines reproducibility and
     makes it unclear whether Table 1 is a SASRec or HSTU-style ablation.
   - Concrete fix: rewrite Section 3.2 as "Item-feature construction and
     scoring" plus "Headline HSTU-style encoder"; demote SASRec-SBERT to
     baseline/protocol-parity wording; move the HSTU equation into Section 3.2
     or point Section 4.3 to the exact HSTU subsection; state `4 layers, 2
     heads, d=64, dropout=0.5` once in the method and once in experiments.
2. **WPGRec reference metadata is stale.**
   - `PAPER_SUBMISSION.md` and `paper_tex/references.bib` still put WPGRec under
     an "unreviewed at the time of writing" preprint framing.
   - arXiv metadata for `2604.21305` says WPGRec was accepted to SIGIR 2026.
   - Concrete fix: remove WPGRec from the unreviewed-preprint umbrella or revise
     the note to "accepted to SIGIR 2026; arXiv:2604.21305"; keep it as broader
     frequency/time-frequency prior art, not an apples-to-apples AR2023
     comparator.

### Confirmed Fixes Since Prior Audit

- **Section 6.1 / Appendix A.1 MLP-adaptor contradiction is repaired.** The
  current source and both PDFs now say the Beauty signal is attributable to
  BLaIR/rich text as a bundle, while the clean MiniLM+MLP adaptor ablation is
  negative.
- **SILLM4Rec tooling-language leak remains fixed.** The manuscript no longer
  says a paper was inaccessible to "our tooling"; the current sentence says
  accessible metadata did not establish apples-to-apples protocol comparability.
- **Artifact gates remain green.** Strict rebuild, table provenance, release
  manifest, PDF hygiene scan, and tracked working tree all pass.

### Plausible Risks Requiring Author Verification

- **SILLM4Rec direct protocol inspection is still open.** The public GitHub repo
  instructs users to download Amazon Reviews 2023 5-core files and generate
  candidate ranking tasks, which makes the paper more relevant than a metadata-
  only mention. However, the accessible repo does not establish full-catalog
  LLOO equivalence, so exclusion remains defensible only if narrowly worded.
- **"Resolves the open mechanism" overstates the tail evidence.** The user-mode
  titration supports a partial mechanism under synthetic thinning assumptions;
  it does not fully resolve the real data-generating mechanism. This is a
  rhetoric risk, not a numeric contradiction.
- **Reader burden remains high.** The abstract, Section 5, and Table 2 are
  unusually dense. The honesty is useful, but a reviewer may miss the core
  contribution behind caveats and negative-result detail.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's arXiv HTML confirms the AR2023 5-core statistics and comparator
  constants used by the manuscript: Video Games 25,612 items / 94,762 users /
  814,585 interactions, NDCG@10 0.0760; Musical Instruments NDCG@10 0.0406;
  Office Products NDCG@10 0.0271. Source:
  https://arxiv.org/html/2504.10545v3
- SID-MLP's arXiv HTML confirms same-statistics AR2023 5-core LLOO datasets for
  MI/VG: Musical Instruments 57,439 users / 24,587 items / 511,836
  interactions and Video Games 94,762 users / 25,612 items / 814,586
  interactions. Source: https://arxiv.org/html/2605.12617v1
- WPGRec's arXiv page confirms it is a wavelet-packet, graph-enhanced
  sequential recommendation paper and says "Accepted to SIGIR 2026"; this
  supports the manuscript's broader frequency/time-frequency boundary but
  invalidates the "unreviewed" metadata note. Source:
  https://arxiv.org/abs/2604.21305
- The SILLM4Rec public repo confirms relevance to Amazon Reviews 2023 5-core
  data preparation and generated ranking tasks, but the accessible README does
  not establish full-catalog LLOO comparability. Source:
  https://github.com/MKC-Lab/SILLM4Rec
- The official Amazon Reviews 2023 site remains the correct dataset source and
  documents the 5-core processing caveats and category statistics. Sources:
  https://amazon-reviews-2023.github.io/ and
  https://amazon-reviews-2023.github.io/data_processing/5core.html

### Concrete Fixes To Make Next

1. Repair Section 3.2 / 3.7 / 4.3 architecture wording before any submission:
   make the headline HSTU-style 4-layer encoder the main method and label
   SASRec-SBERT as baseline/protocol-parity only.
2. Rebuild both PDFs and rerun text extraction for the phrases "2-layer
   Transformer encoder" and "4 layers" after the method fix.
3. Update WPGRec metadata to SIGIR 2026 accepted status, and remove it from any
   blanket "unreviewed" preprint sentence.
4. Keep SILLM4Rec excluded unless the full paper is inspected; if mentioned,
   keep the current narrow "not established as apples-to-apples full-catalog
   LLOO" wording.
5. Tone down "resolves the open mechanism" to "partially resolves" or "supports
   a partial mechanism under the thinning intervention."

### Open Questions

- Should the Method section be organized around the headline HSTU-style stack
  only, with SASRec-family details moved to baselines/appendix, or should it
  explicitly describe two model families?
- Can the authors obtain SILLM4Rec's full ACM PDF to inspect its exact
  evaluation protocol?
- Is WPGRec's SIGIR 2026 acceptance enough to move it from a reference note into
  the related-work prose, or is the current one-sentence boundary sufficient?

### Running Checklist

- [x] Read automation memory.
- [x] Locate canonical manuscript sources and PDFs.
- [x] Check commits and tracked tree after the supplied last-run cutoff.
- [x] Verify strict rebuild/provenance gate.
- [x] Verify TORS PDF hygiene scan.
- [x] Verify prior Section 6.1 MLP-adaptor contradiction is absent from PDFs.
- [x] Fact-check selected novelty/comparator claims against external sources.
- [x] Identify new confirmed methods inconsistency.
- [x] Identify stale WPGRec bibliographic metadata.
- [ ] Rewrite Method architecture section for HSTU-style 4-layer headline stack.
- [ ] Update WPGRec SIGIR 2026 metadata and rerender references.
- [ ] Protocol-inspect SILLM4Rec full text if accessible before freeze.

## Audit Run - 2026-07-12 18:37 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `395d472f` (`Respond to
  PAPER_REVIEW_AUDIT run 17:35: tooling-leak removed, artifact roles explicit`)
- Automation memory at start: no prior memory file found at
  `$CODEX_HOME/automations/hourly-strict-paper-audit/memory.md`.
- Working tree before writing this audit: clean.
- Files modified after the supplied cutoff (`2026-07-12T07:32:54.215Z`):
  `PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`,
  `_paper_render.html`, `paper_tex/sections/05-results.tex`,
  `paper_tex/tables/*`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `RELEASE_MANIFEST.json`,
  `_bestrec_run/hstu_tables.json`, and `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`.
- Canonical artifacts inspected: `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/sections/05-results.tex`,
  `paper_tex/sections/06-discussion.tex`, `paper_tex/sections/appendix-a.tex`,
  `paper_tex/tables/table0_novelty.tex`, `paper_tex/tables/table1.tex`,
  `paper_tex/tables/tableV2conf.tex`, `paper_tex/tables/table56_theirs.tex`,
  `paper_tex/references.bib`, `paper_tex/hygiene_scan_output.txt`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, and this audit file.

### Verdict

**Strict artifact/provenance gate remains green, but the manuscript has a
confirmed self-contradiction that a top-journal reviewer can cite directly.**
The contradiction is not numerical: it is the interpretation of the Beauty
cross-pipeline scan. Section 6.1 says the MLP adaptor is the only consistently
positive intervention and hypothesizes why it helps; Appendix A.1 later says the
clean MiniLM-only MLP-adaptor ablation drops performance and that the observed
gain comes from changing the text encoder and content, not the projection layer.

This should be fixed before any submission freeze. It is a high-salience
internal-consistency defect because both statements are in the rendered PDFs.

### Commands And Evidence Checked

- `git status --short --branch`
  - Clean on `codex/bestrec-sota-results` before writing this audit.
- Modified-since-cutoff scan from `2026-07-12T07:32:54.215Z`
  - Confirms the latest substantive changes are the manuscript/PDF/table rebuild
    and response files after the previous audit response.
- `uv --project _bestrec_run run python _bestrec_run/update_release_manifest.py
  --verify`
  - PASS: 113 files verified.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py
  --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12 declared
    claim families sourced.
  - PASS: release manifest verification, MI V2 dual gate, Office
    descriptive/VOID adjudication.
- `pdfinfo` via bundled Poppler direct executable
  - `PAPER_SUBMISSION.pdf`: 41 pages, letter, generated 2026-07-12 18:27.
  - `paper_tex/PAPER_TORS.pdf`: 36 pages, letter, generated 2026-07-12 18:27.
- PDF text extraction with `pypdf` under `uv`
  - `PAPER_SUBMISSION.pdf`: Section 6.1 contradiction on page 30; appendix
    clean-ablation correction on page 39.
  - `paper_tex/PAPER_TORS.pdf`: same contradiction on page 27 and appendix
    correction on page 35.
- Poppler page renders inspected visually
  - `tmp/pdfs/audit_20260712_1830/paper_submission_p-30.png`: Section 6.1
    visibly says "only consistently-positive intervention is the MLP-adaptor."
  - `tmp/pdfs/audit_20260712_1830/paper_tors_27_single.png`: same text visible
    in the TORS PDF.
  - `tmp/pdfs/audit_20260712_1830/paper_tors_p-35.png`: appendix visibly says
    "The MLP adaptor by itself does NOT help on this protocol."
- Targeted `rg` sweeps
  - `not accessible to our tooling` is gone.
  - SILLM4Rec is now excluded using neutral protocol-auditability wording.
  - `\keywords{...}` is present in `paper_tex/paper-shared.tex`.

### Confirmed Problems

1. **Section 6.1 contradicts Appendix A.1 on the MLP adaptor.**
   - Section 6.1: "the only consistently-positive intervention is the
     MLP-adaptor design" and "the 2-layer MLP can also denoise the BLaIR
     features."
   - Appendix A.1: the clean MiniLM + MLP adaptor row is 0.01889, worse than
     the MiniLM + Linear baseline around 0.0190; the text says the MLP adaptor
     by itself does not help and the observed +1.3-2.3% comes from MiniLM ->
     BLaIR plus titles -> rich text, not projection-layer form.
   - Why this matters: the current paper asks reviewers to trust an unusually
     complex artifact/provenance story. A direct internal contradiction in the
     discussion weakens that trust even though the numeric artifact gate passes.

### Plausible Risks Requiring Author Verification

- **The Beauty cross-pipeline scan may not deserve body discussion anymore.**
  The paper already frames it as appendix/supporting material, and the headline
  spine is causal FIR + tail pattern. Consider deleting Sections 6.1-6.2 or
  replacing them with a shorter "superseded supporting scan" paragraph.
- **SILLM4Rec may still need a freeze-time full-paper inspection.** Search/ACM
  metadata confirms the paper exists and says it uses three 5-core AR2023
  subdatasets, but accessible metadata did not establish the exact
  full-catalog-LLOO protocol needed for apples-to-apples comparison.
- **The abstract remains very dense.** Its caveats are mostly correct, but a
  reviewer may still see too many results, p-values, and mechanism claims before
  the method is introduced. This is a readability/reviewer-fatigue risk, not a
  contradiction.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's arXiv HTML confirms the paper uses AR2023 5-core subsets and
  reports the comparator constants the manuscript relies on: Video Games
  HSTU-BLaIR NDCG@10 0.0760, Office Products 0.0271, and Musical Instruments
  0.0406; its dataset statistics match the paper's quoted users/items for the
  HSTU-BLaIR-family protocol. Source:
  https://arxiv.org/html/2504.10545v3
- GrIT (arXiv:2602.19728) reports AR2023 Video Games with 94,762 users, 25,612
  items, 814,586 interactions, 5-core filtering, full-item-set evaluation, and
  NDCG@10 0.0588 for GrIT. The manuscript's "numerically higher but no
  comparative claim" framing is appropriate. Source:
  https://arxiv.org/html/2602.19728v1
- Latte (arXiv:2605.06331) reports Amazon Reviews 2023 Instruments/Scientific/
  Games and includes Latte NDCG@10 values 0.0331 (Instruments) and 0.0515
  (Games) in the RQ-KMeans row, supporting the manuscript's values. Source:
  https://arxiv.org/pdf/2605.06331
- SILLM4Rec metadata confirms a real MMAsia 2025 paper with DOI
  `10.1145/3743093.3771011`; search snippets from ACM state experiments use
  three 5-core Amazon Reviews 2023 subdatasets, but the accessible metadata
  checked here did not establish full-catalog LLOO comparability. Source:
  https://dl.acm.org/doi/10.1145/3743093.3771011

### Concrete Fixes To Make Next

1. Rewrite `PAPER_SUBMISSION.md` Section 6.1 from "MLP adaptor transfer" to
   "BLaIR/rich-text content transfer, with MLP alone negative in the clean
   ablation." Remove the denoising hypothesis unless it is clearly scoped to
   BLaIR-rich-text + MLP as an inseparable bundle.
2. Apply the same correction to `PAPER_DRAFT.md` and the LaTeX twin
   `paper_tex/sections/06-discussion.tex`.
3. Rerender both PDFs and confirm extraction no longer contains the phrase
   "only consistently-positive intervention is the MLP-adaptor."
4. Optional: collapse Sections 6.1-6.2 into one short appendix-pointer paragraph
   to keep the body focused on the headline results.
5. Before freeze, obtain/inspect the SILLM4Rec full text if available; otherwise
   keep the current neutral exclusion sentence.

### Open Questions

- Does the author want to preserve the Beauty scan as interpretive discussion,
  or retain it only as an appendix/provenance record?
- Is SILLM4Rec full text available through institutional access? If yes, it
  should be protocol-inspected, not left as metadata-only.

### Running Checklist

- [x] Locate canonical manuscript source and PDFs.
- [x] Read prior audit and response trail.
- [x] Check files changed after the supplied last-run cutoff.
- [x] Verify release manifest.
- [x] Run strict rebuild/provenance gate.
- [x] Inspect latest PDF page counts and rendered pages.
- [x] Fact-check key comparator/recent-literature claims against primary or
      reliable sources.
- [x] Identify a new confirmed reviewer-facing contradiction.
- [ ] Rewrite Section 6.1 / LaTeX discussion to match Appendix A.1.
- [ ] Rerender PDFs after the prose fix.
- [ ] Protocol-inspect SILLM4Rec full text if accessible before submission
      freeze.

## Audit Run - 2026-07-12 17:35 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `a53a9013` (`Respond to
  PAPER_REVIEW_AUDIT run 16:32: coverage clause (iv), CCS/keywords closed`)
- Working tree before writing this audit: clean.
- Commits since supplied last-run cutoff (`2026-07-12T06:31:53Z`):
  `2fcfb06f` (AR2023-adjacent clause, CCS concepts, keywords, references, PDF
  rebuild), `8fb5c21a` (manifest regeneration), `a53a9013` (response log).
- Canonical artifacts inspected: `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`,
  `CANONICAL_SUBMISSION.md`, `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`,
  `paper_tex/paper-shared.tex`, `paper_tex/sections/05-results.tex`,
  `paper_tex/references.bib`, `paper_tex/tables/tableA1.tex`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/hygiene_scan_output.txt`, and
  `PAPER_REVIEW_AUDIT.md`.

### Verdict

**No numerical, provenance, or claim-boundary rejection defect found.** The
strict rebuild remains green, and the new recent-literature paragraph materially
improves the prior coverage risk. The only new confirmed problem is writing and
submission-polish level: the paper should not tell reviewers that a paper was
excluded because it was inaccessible to "our tooling." Also, the metadata fix is
closed for the TORS LaTeX artifact but not for the markdown-rendered PDF, so the
submission role of `PAPER_SUBMISSION.pdf` should stay explicit.

### Commands And Evidence Checked

- `git status --short --branch`
  - Clean on `codex/bestrec-sota-results`.
- `git log --since="2026-07-12T06:31:53Z" --oneline --decorate --name-status`
  - Confirms the three expected commits after the prior audit cutoff.
- `git diff --stat` and targeted `git diff`
  - No uncommitted manuscript or artifact drift before this audit edit.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py
  --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: 164 cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12 declared
    claim families sourced.
  - PASS: release manifest verification, 113 files verified.
  - PASS: MI V2 dual gate.
  - PASS/VOID: Office remains descriptive and VOID under the preregistered floor
    check.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py
  paper_tex/PAPER_TORS.pdf`
  - PASS: 36 pages; 0 placeholder/forbidden-claim failures.
  - Informational SOTA list remains negated/non-claim contexts.
- PDF text extraction via `pypdf` under the project `uv` runtime
  - `paper_tex/PAPER_TORS.pdf`: 36 pages; contains `CCS Concepts`, DiffuReason,
    SILLM4Rec, "full text was not accessible", and the new AR2023-adjacent
    clause. Extraction did not find the literal string `Keywords`, likely
    because acmart renders the keyword label differently.
  - `PAPER_SUBMISSION.pdf`: 41 pages; contains Augment or Not, DiffuReason,
    SILLM4Rec, "full text was not accessible", and the new AR2023-adjacent
    clause; extraction did not find `CCS Concepts` or `Keywords`.
- Targeted wording sweep
  - `PAPER_SUBMISSION.md` / `paper_tex/sections/05-results.tex` no longer have
    the old first/only AR2023 wording and still keep Video_Games as non-SOTA.
  - `paper_tex/sections/05-results.tex` now contains the audit-requested clause
    `(iv) Other AR2023-adjacent, non-interchangeable protocols`.

### Confirmed Problems

1. **Manuscript leaks audit/tooling process into the SILLM4Rec sentence.**
   Current wording: "A further candidate (SILLM4Rec) is not cited pending direct
   protocol inspection (its full text was not accessible to our tooling at the
   time of writing)." A journal paper can say protocol details were not available
   in the accessible metadata; it should not mention "our tooling." This is a
   small but real reviewer-confidence issue.
2. **The CCS/keyword closure is artifact-specific.** The TORS LaTeX source and
   `PAPER_TORS.pdf` now contain ACM CCS concepts, but `PAPER_SUBMISSION.pdf`
   does not. If the markdown PDF remains a public reader artifact, this is fine;
   if it is treated as a submission artifact, the prior metadata finding is not
   fully closed.

### Plausible Risks Requiring Author Verification

- **SILLM4Rec may be relevant but is not protocol-audited from accessible
  metadata.** Search/ACM/ResearchGate metadata confirms the paper exists
  (`SILLM4Rec: Self-Improving with Chain of Thought Enhanced Preference
  Optimization for Multimodal Recommendation`, MMAsia 2025, DOI
  `10.1145/3743093.3771011`), but the accessible metadata did not provide enough
  protocol detail to decide whether it belongs in the AR2023 5-core paragraph.
  Keep it excluded unless the PDF can be inspected directly; if mentioned, use a
  neutral note such as "excluded pending direct protocol inspection."
- **The response log overstates the metadata verification.**
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` says both PDFs had CCS/keywords verified
  in extraction, but the extraction check here finds that only the TORS artifact
  carries CCS. This is not a paper defect if the response log is historical
  correspondence, but it should not be copied into submission metadata.
- **Table 2 and first-page review-mode text remain standing polish risks.**
  Nothing in this run worsens them.

### External Fact-Check / Novelty Notes

- `Augment or Not?` is correctly AR2023-adjacent but non-interchangeable: it
  uses Amazon'23 Musical Instruments and Industrial and Scientific under 5-core
  leave-one-out, and its table reports LETTER-TIGER Musical Instruments
  NDCG@10 = 0.0282. Source:
  https://arxiv.org/html/2505.23053v1
- `DiffuReason` is correctly non-comparable to this paper's Video_Games result:
  it reports a different AR2023 Video & Games universe (67,658 users / 25,535
  items / 654,867 interactions), full ranking, and HSTU/DiffuReason-H NDCG@10
  0.0945 / 0.1041. Source: https://arxiv.org/html/2602.09744v1
- Amazon Reviews 2023 remains the correct primary dataset source. Source:
  https://amazon-reviews-2023.github.io/
- SILLM4Rec metadata confirms existence and venue/DOI, but not protocol details
  in the accessible pages used here. Sources:
  https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://www.researchgate.net/publication/398412502_SILLM4Rec_Self-Improving_with_Chain_of_Thought_Enhanced_Preference_Optimization_for_Multimodal_Recommendation

### Concrete Fixes To Make Next

1. Replace the SILLM4Rec sentence with neutral wording:
   "A further candidate, SILLM4Rec (MMAsia 2025), is excluded pending direct
   protocol inspection; accessible metadata did not establish an
   apples-to-apples AR2023 5-core full-catalog LLOO setting."
   Or simply delete the sentence until the paper is inspectable.
2. Decide whether `PAPER_SUBMISSION.pdf` should gain a short metadata front
   matter block or be explicitly described as non-venue reader output. Do not
   claim that both PDFs contain CCS/keywords unless extraction verifies it.
3. Keep the current AR2023-adjacent paragraph's non-comparability framing for
   `Augment or Not?` and `DiffuReason`; it is source-supported.
4. Leave Table 2 dense only if completeness is the intended reviewer-facing
   tradeoff; otherwise move most negative-result rows to appendix.
5. Re-run one final literature/protocol sweep at freeze.

### Open Questions

- Is `PAPER_SUBMISSION.pdf` still intended for public/reader consumption after
  TORS submission, and if so should it carry venue metadata for consistency?
- Can the authors obtain SILLM4Rec's full PDF through institutional access or an
  author copy before freeze?

### Running Checklist

- [x] Locate canonical manuscript source and PDF.
- [x] Read prior automation memory and prior cumulative audit.
- [x] Check files/commits after the automation last-run cutoff.
- [x] Verify strict rebuild and release manifest.
- [x] Verify TORS PDF hygiene scan.
- [x] Fact-check new Augment/DiffuReason coverage against external sources.
- [x] Check CCS/keyword presence in generated PDFs.
- [x] Identify reviewer-facing SILLM4Rec tooling-language defect.
- [ ] Rewrite or remove the SILLM4Rec sentence.
- [ ] Clarify metadata expectations for `PAPER_SUBMISSION.pdf`.
- [ ] Final freeze-time literature/protocol sweep.

## Audit Run - 2026-07-12 16:32 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `555f566` (`Respond to
  PAPER_REVIEW_AUDIT run 15:31: header collision fixed (visually verified);
  regenerates-wording aligned`)
- Working tree before writing this audit: clean.
- Commits since the supplied last-run cutoff (`2026-07-12T05:30:22Z`):
  `15b7dbaf` (short running title and regenerates wording), `d7846db4`
  (manifest regen), `555f5669` (response log).
- Canonical artifacts inspected: `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`,
  `CANONICAL_SUBMISSION.md`, `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`,
  `paper_tex/main.tex`, `paper_tex/paper-shared.tex`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/references.bib`,
  `paper_tex/sections/*`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, and `PAPER_REVIEW_AUDIT.md`.
- Visual PDF check: rendered `paper_tex/PAPER_TORS.pdf` pages 1, 17, 18, 22,
  23, 24, 29, and 35 with `pypdfium2` through the project `uv` runtime into
  `tmp/pdfs/hourly_audit_20260712_1632_tors/`.

### Verdict

**No new hard rejection defect found in this run.** The prior two confirmed
defects are closed: the TORS running title no longer collides with page numbers,
and the unpinned comparator language is aligned to "regenerates" rather than
"reproduces." The scientific/provenance gate remains green. The highest current
risks are now submission-readiness and reviewer-perception risks: recent-work
coverage, Table 2 density, CCS/keyword metadata, and one minor first-page
layout-polish check.

### Commands And Evidence Checked

- `git status --short --branch`
  - Clean on `codex/bestrec-sota-results`.
- `git log --since="2026-07-12T05:30:22Z" --oneline --name-status`
  - Confirms the expected three commits after the previous audit response.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py
  --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12 claim
    families sourced.
  - PASS: release manifest verification, 113 files verified.
  - PASS: MI dual gate.
  - PASS/VOID: Office remains descriptive and VOID under the preregistered floor
    check.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py
  paper_tex/PAPER_TORS.pdf`
  - PASS: 35 pages; 0 placeholder/forbidden-claim failures.
  - Informational SOTA list contains only explicit non-claim contexts.
- PDF text/object extraction with `pypdf`
  - `paper_tex/PAPER_TORS.pdf`: 35 pages, 426,626 bytes; contains WPGRec and
    "regenerates"; no `CCS Concepts`.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 36 pages, 433,961 bytes; contains
    WPGRec and "regenerates"; no `CCS Concepts`.
  - `PAPER_SUBMISSION.pdf`: 40 pages, 1,311,606 bytes; contains WPGRec and
    "regenerates"; no `CCS Concepts`.
- Wording sweep
  - `paper_tex/sections/05-results.tex` now has
    `The Musical_Instruments comparator regenerates locally` and
    `Caveats (why these are regenerations, not reproductions)`.
  - Remaining `reproduce*` hits are either negated pinned-reproduction caveats
    or internal "does not reproduce MI's tail win" thinning-language, not an
    official-comparator claim.
- Visual spot check
  - Page 23: short running title and page number are separated; Fig. 3 remains
    readable.
  - Page 24: Table 2 is legible but still dense.
  - Page 29: short running title and page number are separated; ethics/data
    governance section is readable.
  - Page 1: content is readable; note the duplicated-looking acmart
    "Manuscript submitted to ACM" topmatter/footer text as a freeze-time polish
    check.

### Confirmed Fixes Since Prior Audit

1. **Running-header collision fixed.** The optional short title in
   `paper_tex/paper-shared.tex` is present and the previously failing pages
   visually render cleanly.
2. **Comparator wording fixed.** The MI local reference-implementation run is
   now described as an environment-caveated local regeneration, not an official
   or pinned reproduction.
3. **Strict gate remains healthy after those fixes.** The rebuild, manifest
   verification, MI gate, Office VOID adjudication, and PDF hygiene scan all
   pass on the current HEAD.

### Confirmed Problems

- **No new confirmed numerical, provenance, or claim-boundary defect was found.**
- **Confirmed submission metadata still absent:** the active PDFs and TeX source
  do not include ACM CCS concepts or keywords. This is acceptable only if it is
  intentionally deferred until the actual TORS submission form/template pass.

### Plausible Risks Requiring Author Verification

- **Recent AR2023 literature coverage may still look selective.** The manuscript
  currently cites the main same-statistics and SID-family 2026 preprints, but a
  fresh search found additional AR2023-adjacent work not in the bibliography:
  `Augment or Not?` (2025) evaluates AR2023 Musical Instruments / Industrial
  and Scientific under 5-core leave-one-out; `DiffuReason` (2026) evaluates
  AR2023 Video & Games with an HSTU backbone but a different filtered universe;
  and SILLM4Rec has an ACM DOI page claiming three AR2023 5-core datasets. None
  of the inspected results overturn the paper's MI comparator choice or
  no-Video-Games-SOTA boundary, but a reviewer may expect an explicit
  non-comparability note.
- **DiffuReason deserves special handling if cited.** It reports Video & Games
  HSTU NDCG@10 0.0945 and DiffuReason-H 0.1041, far above this manuscript's
  Video_Games number, but its Video & Games universe is 67,658 users / 25,535
  items / 654,867 interactions and it filters positive ratings differently from
  the HSTU-BLaIR-family universe here (94,762 / 25,612 / about 814,586). This
  is not an apples-to-apples defeat, but it is a reason to keep avoiding broad
  Video_Games claims.
- **`Augment or Not?` is relevant but not threatening.** Its AR2023 Musical
  Instruments table reports best listed NDCG@10 0.0282 (LETTER-TIGER), well
  below HSTU-BLaIR's 0.0406 comparator, but it is a modern AR2023 5-core
  LOO LLM-recommender benchmark and should be considered for the final
  recent-work paragraph.
- **SILLM4Rec needs direct inspection before citation.** Search/ACM metadata
  indicate AR2023 5-core experiments, but this audit did not fully inspect the
  paper text because the ACM PDF page was not accessible through the tool.
- **First-page ACM footer/topmatter repetition may be harmless.** Verify against
  final TORS instructions rather than changing acmart blindly.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR still reports the paper's key comparator points: Video Games
  HSTU-BLaIR NDCG@10 0.0760, Office Products 0.0271, Musical Instruments
  0.0406, with AR2023 5-core framing. Sources:
  https://github.com/snapfinger/HSTU-BLaIR and
  https://arxiv.org/html/2504.10545v3
- SID-MLP remains a same-statistics AR2023 5-core LLOO concurrent-preprint
  comparator context for MI/VG dataset statistics. Source:
  https://arxiv.org/html/2605.12617v1
- WPGRec is real and supports the manuscript's statement that later
  time-frequency/wavelet-packet SR work exists; an ACM DOI search result now
  also appears, so bibliography metadata should be checked at freeze. Sources:
  https://arxiv.org/abs/2604.21305 and
  https://dl.acm.org/doi/10.1145/3805712.3809907
- `Augment or Not?` uses Amazon'23 Musical Instruments / Industrial and
  Scientific, 5-core leave-one-out, and reports MI NDCG@10 values up to 0.0282
  in its Table 2. Source: https://arxiv.org/html/2505.23053
- `DiffuReason` uses AR2023 Video & Games only among its Amazon review
  datasets, with 67,658 users / 25,535 items / 654,867 interactions and full
  ranking; its HSTU-backbone result is on a different universe and should not be
  mixed with HSTU-BLaIR-family numbers. Source:
  https://arxiv.org/html/2602.09744
- Amazon Reviews 2023 remains the correct primary dataset source for public
  review, metadata, and link facts. Source: https://amazon-reviews-2023.github.io/

### Concrete Fixes To Make Next

1. Add a compact recent/concurrent-work note covering additional
   AR2023-adjacent but non-interchangeable protocols, or document why they are
   excluded from the main related-work paragraph. Include at least
   `Augment or Not?` and `DiffuReason`; inspect SILLM4Rec directly if adding it.
2. Decide whether to split Table 2 before submission or leave the dense
   complete negative-result map in the main text.
3. Add ACM CCS concepts and keywords before the actual TORS submission freeze.
4. Verify the first-page acmart "Manuscript submitted to ACM" repetition against
   final TORS formatting guidance.
5. Run one more targeted literature sweep at the freeze timestamp, especially
   for AR2023 5-core, HSTU, semantic-ID/generative, LLM/reasoning, and
   frequency/time-frequency sequential-recommendation work.

### Open Questions

- Should the paper cite `Augment or Not?` and `DiffuReason` in the main
  related-work paragraph, or in a short appendix/concurrent-work note?
- Is SILLM4Rec close enough to the paper's protocol to warrant inclusion after
  direct inspection?
- Is the dense Table 2 intended as a deliberate top-journal evidence table, or
  should it be condensed for first-pass review readability?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical source and compiled artifacts.
- [x] Check commits since the supplied last-run cutoff.
- [x] Verify strict numerical/provenance rebuild.
- [x] Run TORS PDF hygiene scan.
- [x] Render and visually inspect the prior failure pages.
- [x] Verify the prior header-collision fix.
- [x] Verify the prior "reproduces" wording fix.
- [x] Run a targeted external literature sweep.
- [x] Update the cumulative audit with current risk priorities.
- [ ] Add/freeze final recent-work coverage.
- [ ] Decide Table 2 split vs dense main-table presentation.
- [ ] Add ACM CCS concepts and keywords before submission.
- [ ] Verify final TORS first-page/footer formatting.

## Audit Run - 2026-07-12 15:31 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `c580f48` (`Respond to
  PAPER_REVIEW_AUDIT run 14:34: manifest boundary healed + dirty-file gate;
  WPGRec; BUILD_NOTES`)
- Working tree before writing this audit: clean.
- Manifest source boundary: `RELEASE_MANIFEST.json` records `git_commit =
  d76ef6436b60e6feab7b28d067172786ab8eaf0c`. `git diff --name-status
  5ce2d91..HEAD` shows only `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, so the
  manifest/source boundary is deliberate rather than new drift.
- Canonical artifacts inspected: `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`,
  `paper_tex/main.tex`, `paper_tex/paper-shared.tex`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/references.bib`, `paper_tex/sections/*`, `paper_tex/tables/*`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/PAPER_TORS_acmsmall.pdf`,
  `RELEASE_MANIFEST.json`, `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, and
  `CANONICAL_SUBMISSION.md`.
- Visual PDF check: rendered `paper_tex/PAPER_TORS.pdf` pages 1, 17, 18, 22,
  23, 24, 29, and 35 with `pypdfium2` into
  `tmp/pdfs/hourly_audit_20260712_1531_tors/`.

### Verdict

**Numerical/provenance package: currently green. Submission formatting: not yet
green.** The prior manifest blocker, stale build-note class paragraph, and
uncited WPGRec/time-frequency related-work issue are closed. The strict rebuild
passes and the TORS PDF hygiene scanner passes. However, the rendered ACM
manuscript has a visible running-header/page-number collision on odd pages, and
the "reproduces" wording around the MI comparator still risks overstating an
unpinned local regeneration.

### Commands And Evidence Checked

- `git status --short --branch`
  - Clean at `c580f48`.
- `git log --oneline --decorate -5`
  - Shows `d76ef64` content commit, `5ce2d91` manifest child, then `c580f48`
    response-log commit.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py
  --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    declared claim families sourced.
  - PASS: release manifest verification, 113 files verified.
  - PASS: MI V2 dual gate.
  - PASS/VOID: Office arithmetic remains descriptive and VOID under the
    preregistered floor-check failure.
- `uv --project _bestrec_run run python _bestrec_run/update_release_manifest.py
  --verify`
  - PASS: 113 files verified, 0 release-asset files not local.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py
  paper_tex/PAPER_TORS.pdf`
  - PASS: 35 pages; 0 placeholder/forbidden-claim failures.
  - Review list contains only explicit SOTA/non-claim contexts.
- PDF object/text inspection with `pypdf`
  - `paper_tex/PAPER_TORS.pdf`: 35 pages, 427,696 bytes, US-letter media box,
    0 image XObjects, 3 vector Form XObjects; contains `ETHICS`, `GrIT`,
    `FEARec`, `WPGRec`, and the pinned-reproduction caveat; no `CCS Concepts`.
  - `PAPER_SUBMISSION.pdf`: 40 pages, 1,311,601 bytes, US-letter media box, 3
    image XObjects; contains `GrIT`, `FEARec`, and `WPGRec`.
- Visual spot check
  - Page 1: title/abstract readable in ACM manuscript review format.
  - Page 23: Fig. 3 page readable, but running title collides with page number.
  - Page 24: Table 2 is legible but crowded.
  - Page 29: ethics/data-governance text readable, but running title again
    collides with page number.

### Confirmed Fixes Since Prior Audit

1. **Manifest/source-boundary blocker fixed.** The previously dirty
   `emit_latex_tables.py` change is committed, the manifest was regenerated at
   a clean boundary, and the strict verify now includes the dirty-file gate.
2. **`BUILD_NOTES.md` class contradiction fixed.** The notes now state that
   `main.tex` is the gated `manuscript,review,anonymous` target and
   `main-acmsmall.tex` is an untracked production preview.
3. **Time-frequency related-work gap mostly fixed.** The novelty-boundary
   paragraph now cites WPGRec with a bibliography entry and no longer leaves the
   broader "subsequent time-frequency" phrase unsupported.
4. **Prior core scientific boundaries still hold.** Figures, ethics/data
   governance, GrIT, FEARec, WPGRec, Office VOID language, and no-Video-Games
   SOTA language remain present in the active artifacts.

### Confirmed Problems

1. **Running header overlaps page number in the TORS review PDF.** This is
   visible in the rendered review artifact, not just an extraction artifact.
   `paper_tex/paper-shared.tex` sets a long `\title{...}` and
   `\renewcommand{\shortauthors}{Anonymized}` but does not provide an optional
   short running title, so acmart uses the full title in the running head.
2. **Comparator wording remains stronger than the paper's own caveat boundary.**
   The section heading "The Musical_Instruments comparator reproduces" and the
   sentence "a local regeneration by the generating code reproduces it" should
   be softened. The evidence supports a local, environment-caveated regeneration
   of the published point estimate, not a faithful pinned reproduction.

### Plausible Risks Requiring Author Verification

- Whether to split Table 2 before initial TORS submission or wait for reviewer
  pressure. It is now technically readable but dense enough to slow review.
- Whether to add ACM CCS concepts and keywords now or only at submission-freeze.
- Whether to cite one more representative 2025 time-frequency SR paper such as
  HyTiFRec/CTF4Rec, or keep WPGRec as the representative recent example. WPGRec
  is enough to support the current sentence, but the literature is moving fast.
- Whether `PAPER_SUBMISSION.pdf` remains a live deliverable or only a markdown
  render. The TORS artifact is cleaner on ethics/formatting and appears to be
  the real submission target.

### External Fact-Check / Novelty Notes

- ACM author guidance and venue examples support the `manuscript,review` /
  `manuscript,review,anonymous` review build direction. Sources:
  https://www.acm.org/publications/authors/submissions and
  https://chi2026.acm.org/chi-publication-formats/
- ACM TORS author guidelines require originality / not-under-review
  declaration in the cover letter; this supports keeping the TORS-specific venue
  plan explicit. Source: https://dl.acm.org/journal/tors/author-guidelines
- WPGRec is a real 2026 arXiv preprint in the time-frequency sequential
  recommendation line and is now a reasonable representative citation for the
  novelty-boundary paragraph. Source: https://arxiv.org/abs/2604.21305
- HyTiFRec is a 2025 hybrid time-frequency sequential-recommendation paper,
  relevant as an optional additional recent citation but not strictly required
  after WPGRec was added. Source:
  https://www.techscience.com/cmc/v83n2/60583
- HSTU-BLaIR remains the stronger external AR2023 5-core comparator family for
  the manuscript's Video_Games / Musical_Instruments / Office framing. Sources:
  https://github.com/snapfinger/HSTU-BLaIR and
  https://arxiv.org/html/2504.10545v3
- Amazon Reviews 2023 is a large public dataset with user reviews, item
  metadata, and links; the paper's ethics section correctly scopes the risk to
  public/pseudonymized review and metadata use rather than human-subject
  intervention. Source: https://amazon-reviews-2023.github.io/

### Concrete Fixes To Make Next

1. Add an optional short title in `paper_tex/paper-shared.tex`, rebuild both
   TeX targets, rerun `paper_tex/scan_pdf.py`, and visually inspect pages with
   running heads.
2. Replace the `paper_tex/sections/05-results.tex` and `PAPER_SUBMISSION.md`
   "comparator reproduces" wording with "regenerates locally under the unpinned
   shimmed research path" language.
3. Decide Table 2 presentation: leave as dense complete main-table evidence, or
   move long rows to appendix and keep a compact main summary.
4. Add ACM CCS concepts and keywords at submission freeze.
5. Run one final literature sweep immediately before TORS submission.

### Open Questions

- Is `PAPER_SUBMISSION.pdf` still intended to be submitted anywhere, or is
  `paper_tex/PAPER_TORS.pdf` now the only review artifact?
- Should the response log remain outside the manifest boundary by policy, or
  should deposits include response/audit correspondence as ancillary files?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical source and compiled artifacts.
- [x] Verify clean git state and manifest boundary.
- [x] Run strict numerical/provenance rebuild.
- [x] Run release-manifest verification.
- [x] Run TORS PDF hygiene scan.
- [x] Render and visually inspect representative PDF pages.
- [x] Fact-check current venue/literature/comparator claims against external
      sources.
- [x] Confirm prior 14:34 blockers are mostly fixed.
- [ ] Fix TORS running-header/page-number collision.
- [ ] Soften "reproduces" wording for unpinned local comparator runs.
- [ ] Decide Table 2 split vs dense main-table presentation.
- [ ] Add ACM CCS concepts and keywords before submission.
- [ ] Final targeted literature sweep at freeze.

## Audit Run - 2026-07-12 14:34 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `6719bb3` (`Close round-8 row 1
  with phase-B landing details`)
- Working tree before writing this audit: dirty only in
  `_bestrec_run/emit_latex_tables.py`.
- Dirty change inspected: one added typography rule,
  `Beauty\_and\_PC -> Beauty\_and\_\allowbreak PC`, at
  `_bestrec_run/emit_latex_tables.py:109`.
- Canonical source/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `CANONICAL_SUBMISSION.md`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, `VENUE_PLAN.md`,
  `RELEASE_MANIFEST.json`, `_bestrec_run/emit_latex_tables.py`,
  `paper_tex/main.tex`, `paper_tex/main-acmsmall.tex`,
  `paper_tex/build.ps1`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/references.bib`, `paper_tex/sections/*`,
  `paper_tex/tables/*`, `paper_tex/PAPER_TORS.pdf`, and
  `paper_tex/PAPER_TORS_acmsmall.pdf`.
- Visual PDF check: rendered `paper_tex/PAPER_TORS.pdf` pages 1, 17, 18, 22,
  23, 24, 29, and 35 with `pypdfium2` into
  `tmp/pdfs/hourly_audit_20260712_1430_tors/`.

### Verdict

**The TORS review-format issue is substantially fixed, but the release boundary
is not yet clean enough for a top-journal artifact package.** The current
review PDF is now a 35-page ACM `manuscript,review,anonymous` build; the hygiene
scanner passes; figures, ethics, GrIT, FEARec, and the no-SOTA wording all remain
present; and the strict numerical gate passes. The serious new blocker is
provenance: the manifest hash for `_bestrec_run/emit_latex_tables.py` matches an
uncommitted working-tree edit, not the committed file at either `HEAD` or the
manifest's recorded source boundary.

### Commands And Evidence Checked

- `git status --short --branch`; `git log --oneline -5`
  - HEAD is `6719bb3`.
  - Only tracked dirty file before this audit was
    `_bestrec_run/emit_latex_tables.py`.
- `git diff -- _bestrec_run/emit_latex_tables.py`
  - One-line typography-only `Beauty_and_PC` allowbreak addition.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    required claim families sourced.
  - PASS: release manifest verification, 113 files verified.
  - PASS: MI V2 dual gate.
  - PASS/VOID: Office arithmetic passes, but Office remains descriptive and
    VOID under the preregistered floor-check failure.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py paper_tex/PAPER_TORS.pdf`
  - PASS: 35 pages; 0 placeholder/forbidden-claim failures.
  - Review list contains only explicit SOTA/non-claim contexts.
- `update_release_manifest.py --verify`
  - PASS in the dirty working tree because the manifest hash matches the dirty
    generator file.
- Manifest/hash cross-check:
  - Working-tree `_bestrec_run/emit_latex_tables.py` SHA256 =
    `1ac6b422b12416a893c8eb9f79e21729801435d9af4202a84b43f8ecd2e60f86`.
  - `RELEASE_MANIFEST.json` entry for that file =
    `1ac6b422b12416a893c8eb9f79e21729801435d9af4202a84b43f8ecd2e60f86`.
  - `HEAD:_bestrec_run/emit_latex_tables.py` SHA256 =
    `2d631b7a785f734704cbc90756a5a2a5c879ff3d5f9cb2d6bdbbbc36196a08d6`.
  - `7a627ef:_bestrec_run/emit_latex_tables.py` SHA256 =
    `2d631b7a785f734704cbc90756a5a2a5c879ff3d5f9cb2d6bdbbbc36196a08d6`.
  - Therefore the manifest does not describe the committed source state it says
    it describes.
- PDF object/text inspection:
  - `PAPER_SUBMISSION.pdf`: 40 pages, 1,310,455 bytes, letter mediabox, 3 image
    XObjects.
  - `paper_tex/PAPER_TORS.pdf`: 35 pages, 427,335 bytes, letter mediabox
    `(612, 792)`, 3 vector Form XObjects.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 36 pages, 433,983 bytes,
    `(486, 720)` mediabox, 3 vector Form XObjects.
  - TORS PDF contains `10 ETHICS`, `GrIT`, and `FEARec`.
- Visual spot check:
  - Figures 1-3 render and remain readable.
  - Table 2 is no longer broken across a bad page transition; page 24 is
    readable, though dense.
  - Ethics/data-governance text is readable on page 29.

### Confirmed Fixes Since Prior Audit

1. **ACM review format was changed to the safer default.** `paper_tex/main.tex`
   now uses `\documentclass[manuscript,review,anonymous]{acmart}` and produces
   the manifest-gated `PAPER_TORS.pdf`. `main-acmsmall.tex` is now a separate
   production-preview target.
2. **Response staleness is reduced.** `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` now
   begins with a historical-log banner and closes the prior "in flight" wording
   with landing commits.
3. **Deposit/source-boundary prose exists.** `RELEASE_MANIFEST.json` now states
   that `paper_tex` source is governed by Git at the recorded `git_commit`, while
   the manifest hashes the rendered TORS PDF.
4. **Bibliography metadata was improved.** `paper_tex/BUILD_NOTES.md` documents
   registry-verified metadata fills and explicitly lists entries left untouched
   because no authoritative record was found.
5. **Prior scientific blockers remain closed.** Figures, ethics/data governance,
   Table 0 parity wording, GrIT, and FEARec remain present in the inspected
   artifacts.

### Confirmed Problems

1. **Manifest/source-boundary inconsistency is now the top blocker.** The working
   tree passes `update_release_manifest.py --verify`, but only because a
   manifest-hashed file is dirty. A clean clone at `HEAD` would have the
   committed generator content, whose hash does not match the committed manifest
   entry. This contradicts the manifest's "hashes describe repository files as
   of git_commit" rule.
2. **`paper_tex/BUILD_NOTES.md` contradicts itself about the document class.**
   Lines 11-29 and the actual `main.tex` say the review build is `manuscript`;
   lines 84-91 still say the document class is
   `acmsmall,screen,review,anonymous`. Fix the stale paragraph to name both
   targets correctly.
3. **Related-work prose has an uncited "subsequent time-frequency architectures"
   phrase.** The paper cites FEARec, but not the later wavelet/time-frequency
   works that make the phrase true. This is a reviewer-polish issue, not a
   result invalidation.

### Plausible Risks Requiring Author Verification

- Whether the dirty `Beauty_and_PC` line is intended. It appears consistent with
  `BUILD_NOTES.md`'s overfull-box claim, but it must be committed or removed.
- Whether the manifest `git_commit` should advance beyond `7a627ef` after the
  response-only commits. If response files remain outside the deposit boundary,
  this can be acceptable, but the boundary should be explicit.
- Whether TORS requires CCS concepts and keywords at initial submission. The
  current build notes defer them as new content.
- Whether to split Table 2 before submission freeze despite the manuscript build
  being visually acceptable.
- Which representative 2025-2026 time-frequency SR works to cite in the
  novelty-boundary paragraph.

### External Fact-Check / Novelty Notes

- ACM's current author workflow says review submissions should be single-column
  and says LaTeX authors should use the `manuscript` option with
  `\documentclass[manuscript]{acmart}`. This supports the new `main.tex`
  review target. Source: https://www.acm.org/publications/authors/submissions
- The current `acmart` documentation says the `review` option is useful when
  combined with `manuscript`, and that `anonymous` obscures author information.
  It also notes ACM submission samples for both manuscript and acmsmall. Source:
  https://mirrors.ctan.org/macros/latex/contrib/acmart/acmart.pdf
- SID-MLP remains a relevant 2026 AR2023 5-core comparator-context paper: it
  reports AR2023 5-core leave-last-out statistics matching the MI/VG universes
  and NDCG@10 values below the manuscript's MI/VG values. Source:
  https://arxiv.org/html/2605.12617v1
- GrIT remains a relevant same-statistics AR2023 Video_Games 5-core related-work
  item: its table reports Video Games NDCG@10 0.0588. Source:
  https://arxiv.org/html/2602.19728v1
- The time-frequency SR line is broader than FEARec. WPGRec (2026) explicitly
  frames frequency/time-frequency modeling as active, cites FEARec and WaveRec,
  and proposes wavelet-packet subband modeling with graph propagation. Source:
  https://arxiv.org/html/2604.21305v1
- HyTiFRec (2025) is another time-frequency sequential-recommendation example,
  proposing a hybrid time-frequency dual-branch transformer and reporting
  experiments on five datasets. Source:
  https://www.sciencedirect.com/org/science/article/pii/S1546221825003388

### Concrete Fixes To Make Next

1. Commit `_bestrec_run/emit_latex_tables.py` if the `Beauty_and_PC` line is
   intended, then regenerate/commit `RELEASE_MANIFEST.json` at the intended
   boundary and verify from a clean working tree. If the line is not intended,
   remove it and regenerate the manifest instead.
2. Fix `paper_tex/BUILD_NOTES.md` lines 84-91 so the document-class section
   describes the default `manuscript` review target and the separate `acmsmall`
   preview target.
3. Add one sentence and 1-3 representative citations for later
   frequency/time-frequency SR work (for example WaveRec/WPGRec and HyTiFRec),
   or remove the phrase "subsequent time-frequency architectures."
4. Decide whether Table 2 should be split for readability before submission
   freeze.
5. Add ACM CCS concepts / keywords if TORS requires them at initial submission.

### Open Questions

- Was the manifest regenerated while `_bestrec_run/emit_latex_tables.py` was
  dirty and then committed without the generator edit?
- Should `RELEASE_MANIFEST.json` describe the latest source commit, or only the
  committed artifact boundary for the TORS PDF?
- Is the current Table 2 density an acceptable TORS tradeoff, or should the
  main paper carry only a summarized negative-result map?

### Running Checklist

- [x] Read automation memory.
- [x] Locate canonical manuscript source and TORS artifacts.
- [x] Check files modified since the previous automation cutoff.
- [x] Inspect current git status and recent commits.
- [x] Verify strict numerical/provenance gate.
- [x] Verify TORS hygiene scan.
- [x] Inspect PDF page count, media box, figures, and ethics section.
- [x] Render visual spot-check pages.
- [x] Fact-check ACM review-format guidance against external sources.
- [x] Run targeted AR2023/generative and time-frequency related-work searches.
- [x] Identify manifest/dirty-source contradiction.
- [ ] Commit or remove dirty generator change and align the manifest boundary.
- [ ] Fix stale `BUILD_NOTES.md` document-class paragraph.
- [ ] Cite or remove uncited later time-frequency architecture wording.
- [ ] Decide whether to split Table 2.

## Audit Run - 2026-07-12 12:34 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `9cb7fcb` (`Regenerate
  RELEASE_MANIFEST: TORS artifacts enter the drift gate`)
- Working tree before writing this audit: clean.
- Canonical source/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `CANONICAL_SUBMISSION.md`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, `VENUE_PLAN.md`,
  `RELEASE_MANIFEST.json`, `paper_tex/main.tex`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `paper_tex/sections/*`, `paper_tex/tables/*`, `paper_tex/references.bib`,
  and the strict rebuild wrapper.
- Visual PDF check: rendered `paper_tex/PAPER_TORS.pdf` pages 1, 18, 22, 24,
  25, 26, 30, 31, and 36 with `pypdfium2` into
  `tmp/pdfs/hourly_audit_20260712_1140_tors/`.

### Verdict

**Material progress since 10:31: the prior top blockers are closed in the
current artifacts, and the numerical/provenance gate still passes.** The paper
is now much closer to a real TORS submission package: figures are embedded,
ethics/data governance exists, the Table 0 HSTU-parity contradiction is fixed,
GrIT/FEARec are cited/scoped, the TORS PDF is built and scanned, and the release
manifest includes the TORS PDF. The main remaining top-journal risks are
format-policy ambiguity, source/deposit boundary clarity, table readability, and
final literature/bibliography polish.

### Commands And Evidence Checked

- `git status --porcelain=v1 -uall`
  - Clean before writing this audit.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    required claim families sourced.
  - PASS: release manifest verification, 113 files verified.
  - PASS: MI V2 dual gate. K=16 CI-LB 0.04096 and K=8 CI-LB 0.04083 both exceed
    the published HSTU-BLaIR 0.0406 point estimate.
  - PASS/VOID: Office arithmetic passes, but Office remains descriptive and
    VOID under the preregistered floor-check failure.
- `uv --project _bestrec_run run python paper_tex/scan_pdf.py paper_tex/PAPER_TORS.pdf`
  - PASS: 36 pages; 0 placeholder/forbidden-claim failures. SOTA/paired/pinned
    mentions are listed as review items and appear in explicit non-claim
    contexts.
- `pypdf` object/text inspection:
  - `PAPER_SUBMISSION.pdf`: 40 pages, 1,310,455 bytes, 3 image XObjects.
  - `paper_tex/PAPER_TORS.pdf`: 36 pages, 430,794 bytes, 3 vector Form XObjects.
  - Both PDFs contain Fig. 1, Fig. 2, Fig. 3, GrIT, and FEARec; neither contains
    the stale phrase `no numerical-parity claim`.
  - The TORS PDF text extraction finds the ethics section as uppercase
    `10 ETHICS AND DATA GOVERNANCE`; its body includes public/pseudonymized
    AR2023 use, no review bodies/images, no raw-data redistribution, no
    re-identification, and IRB/human-subjects non-applicability.
- Visual spot check:
  - Fig. 1, Fig. 2, and Fig. 3 render and are readable.
  - Ethics/data-governance text is visible and readable on page 30.
  - The old Table 2 dangling continuation-cell defect is gone in the TORS PDF;
    the table remains very dense on page 25.
- Manifest/release check:
  - `RELEASE_MANIFEST.json` now records `git_commit =
    7a8607b280173d0ac15de242044f56bac6c5ccbd`, the immediate parent of current
    HEAD `9cb7fcb...`, which matches the manifest's "cannot hash itself"
    boundary rule.
  - `submission_docs` now includes `paper_tex/PAPER_TORS.pdf`; the manifest diff
    also adds `_bestrec_run/emit_latex_tables.py`.

### Confirmed Fixes Since Prior Audit

1. **Figures are embedded.** The Markdown PDF has 3 image XObjects and the TORS
   PDF has 3 vector Form XObjects. The old "filename reference only" blocker is
   closed.
2. **Ethics/data governance exists.** `PAPER_SUBMISSION.md` and the TORS PDF now
   include an ethics/data-governance statement with AR2023 provenance, data-use
   scope, no raw redistribution, no review-body/image processing, no
   re-identification, and IRB/human-subjects non-applicability.
3. **Table 0 HSTU parity contradiction is fixed.** The row now says
   equation-level verification plus bitwise core-block parity, while still
   refusing a pinned end-to-end reproduction claim.
4. **GrIT is cited and scoped.** The paper records GrIT's Video_Games NDCG@10
   0.0588 as a same-statistics AR2023 5-core point estimate and explicitly does
   not make a comparative claim against unreviewed concurrent work.
5. **Frequency/time-frequency related work is broader.** FEARec is cited as a
   representative wider line, and the paper narrows its causal-FIR contribution.
6. **RecSys 2027 timing is no longer overstated.** `VENUE_PLAN.md` now says
   dates are not announced and treats RecSys 2026 only as precedent.
7. **TORS smoke artifacts are triaged.** `paper_tex/` is now tracked as a
   derived ACM/TORS build; `_smoke.*` is gone and `PAPER_TORS.pdf` is manifest
   covered.

### Confirmed Problems

1. **The TORS build may not match ACM's review-submission option.** ACM's
   current general author workflow says LaTeX review submissions should use
   `\documentclass[manuscript]{acmart}` for single-column review, but
   `paper_tex/main.tex` uses `acmsmall,screen,review,anonymous`. This may still
   be acceptable if TORS explicitly wants the journal template at initial
   submission; otherwise switch the review build to `manuscript,review,anonymous`
   and keep `acmsmall` for accepted-production formatting.
2. **Response prose is stale.** `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` still has
   historical rows saying the TORS round-7 deltas are being applied / will be
   committed and older 37/38-page statements. Do not include that file in a
   submission bundle without either updating or clearly labeling it historical.

### Plausible Risks Requiring Author Verification

- Whether TORS initial submission should use ACM `manuscript` review format or
  the current `acmsmall,screen,review,anonymous` build.
- Whether the DOI/deposit archive should hash/package the full `paper_tex`
  source tree, not only the rendered `paper_tex/PAPER_TORS.pdf`.
- Whether Table 2 should be split into a compact main-paper table plus appendix
  detail before TORS submission.
- Whether BibTeX metadata warnings accepted by `BUILD_NOTES.md` should be fixed
  now for production-quality references.
- Whether to do one final targeted literature sweep for 2026 AR2023 5-core and
  frequency/time-frequency SR papers before freezing the TORS reference list.

### External Fact-Check / Novelty Notes

- ACM's current author workflow says review submissions should be single-column
  and, for LaTeX, use the `manuscript` option; the same page says ACM journals
  use `acmsmall` except listed exceptions. This creates the current TORS-format
  ambiguity. Source: https://www.acm.org/publications/authors/submissions
- ACM's simultaneous-submission policy says ACM normally does not permit a
  manuscript under review in an ACM journal/proceeding to be simultaneously
  under review elsewhere, and violation can cause rejection. This supports the
  sequenced TORS -> RecSys plan. Source:
  https://www.acm.org/publications/policies/simultaneous-submissions
- The TORS author-guidelines page indicates authors must submit a cover letter
  declaring originality, unpublished status, and not-currently-under-review
  status. Source: https://dl.acm.org/journal/tors/author-guidelines
- AR2023's official documentation confirms the dataset includes user reviews,
  item metadata including raw image fields, links, newer interactions through
  Sep. 2023, fine-grained timestamps, and standard splits. This supports keeping
  the ethics/data-governance statement. Source:
  https://amazon-reviews-2023.github.io/
- GrIT (arXiv:2602.19728) reports Video Games NDCG@10 0.0588 in its overall
  table; citing/scoping it remains necessary. Source:
  https://arxiv.org/html/2602.19728v1
- FEARec (arXiv:2304.09184 / SIGIR 2023) frames self-attention SR as low-pass
  and proposes a frequency-enhanced hybrid-attention model, so it is an
  appropriate representative of the broader frequency/time-frequency SR line.
  Source: https://arxiv.org/abs/2304.09184

### Concrete Fixes To Make Next

1. Decide and document the TORS initial-submission class option; preferably add a
   `manuscript,review,anonymous` build target if TORS does not override ACM's
   general review guidance.
2. Clarify the deposit boundary: hash/package `paper_tex` sources or explicitly
   state that Git commit `7a8607b...` is the source boundary and the manifest
   hashes only the rendered TORS artifact.
3. Update or quarantine stale `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` prose before
   any public release bundle.
4. Consider splitting Table 2 for readability.
5. Fill missing BibTeX production metadata where available.
6. Run a final targeted literature sweep immediately before TORS submission.

### Running Checklist

- [x] Read automation memory.
- [x] Inspect current HEAD, git status, canonical Markdown, TORS LaTeX, manifest,
      and response files.
- [x] Re-run the strict submission gate.
- [x] Run the TORS PDF hygiene scanner.
- [x] Inspect PDF object counts and key extracted text.
- [x] Render representative TORS pages and visually inspect figures, ethics, and
      Table 2 continuation.
- [x] Fact-check ACM submission format, ACM simultaneous-submission policy,
      TORS cover-letter requirement, AR2023 data fields, GrIT, and FEARec.
- [ ] Resolve ACM/TORS `manuscript` vs `acmsmall` review-format ambiguity.
- [ ] Clarify or expand manifest coverage for the `paper_tex` source package.
- [ ] Update stale response prose or keep it out of public bundles.
- [ ] Improve Table 2 readability.
- [ ] Complete final literature and bibliography metadata sweep.

## Audit Run - 2026-07-12 10:31 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `5df3d37` (`Record venue + DOI
  decisions: TORS primary, RecSys 2027 repro secondary (sequenced); DOI
  deferred`)
- Pre-existing working tree state: `PAPER_REVIEW_AUDIT.md` was already modified
  with the 09:37/09:40 audit content. I preserved it and appended this current
  section plus the risk-list refresh above.
- Canonical source/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `_paper_render.html`, `CANONICAL_SUBMISSION.md`,
  `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`, `RELEASE_MANIFEST.json`,
  `VENUE_PLAN.md`, `DOI_DEPOSIT_INSTRUCTIONS.md`, `figures/*`, and the strict
  rebuild wrapper.
- Visual PDF check: rendered pages 1, 14, 24, 25, 26, 34, and 38 with
  `pypdfium2` into `tmp/pdfs/hourly_audit_20260712_1030_pypdfium/`. The bundled
  Poppler wrappers (`pdfinfo.cmd`, `pdftoppm.cmd`) are discoverable but still
  fail at runtime with "The system cannot find the path specified."

### Verdict

**No numerical regression; the submission blockers are still presentation,
ethics/data governance, and literature/venue hygiene.** The strict result gate
passes. The current HEAD mostly adds venue/DOI planning, not manuscript
substance, so the previously identified top blockers remain open. A fresh
external check adds one sharper related-work risk: GrIT is a same-protocol-family
2026 AR2023 Video_Games sequential-recommendation paper and is not cited.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    required claim families sourced.
  - PASS: release manifest verification, 111 files verified.
  - PASS: MI V2 dual gate. K=16 CI-LB 0.04096 and K=8 CI-LB 0.04083 both exceed
    the published HSTU-BLaIR 0.0406 point estimate.
  - PASS/VOID: Office arithmetic passes, but Office remains descriptive and VOID.
- `pypdf` extraction / PDF metadata:
  - `PAPER_SUBMISSION.pdf` has 38 pages, 830,097 bytes, and 0 embedded image
    objects.
  - Extracted PDF text contains `Fig. 1`, `Fig. 2`, and `Fig. 3`, but does not
    contain `Ethics`, `privacy`, `data-use`, `FEARec`, `MUFFIN`, `WEARec`,
    `WPGRec`, or `GrIT`.
- `_paper_render.html` and `PAPER_SUBMISSION.md` scan:
  - No `<img>` tags or Markdown image inclusions for the three cited figures.
  - The figure files exist on disk under `figures/`.
- Visual rendering:
  - Page 1 is readable and not visibly clipped.
  - Table 2 still has the page-break polish defect: page 26 starts with a
    dangling continuation cell (`dv=dqk=16 spec`) before the next row.
- Git/release metadata:
  - Current HEAD is `5df3d37`; `RELEASE_MANIFEST.json` still records
    `git_commit = 9ed7be3...`; `CANONICAL_SUBMISSION.md` still says 36 pp.
  - Final `git status` also shows untracked `paper_tex/` smoke artifacts
    (`acmart.cls`, `ACM-Reference-Format.bst`, `_smoke.tex`, `_smoke.pdf`)
    timestamped during this run window. I did not treat them as canonical paper
    source; they should be triaged before committing or deleting.

### Confirmed Problems

1. **Fig. 1-3 are absent from the PDF.** This is still the single clearest
   top-journal desk/reviewer-facing defect. Add real figure inclusion syntax or
   convert the figures into the generated LaTeX flow, then verify the compiled
   PDF has image/XObject content and sane placement.
2. **No ethics/privacy/data-use section.** AR2023's own documentation describes
   user review text, timestamps, metadata, images, and user IDs, so the paper
   should explicitly state data provenance, public-dataset status, privacy/PII
   handling, license/terms boundary, and whether human-subjects/IRB review is
   not applicable or was not required.
3. **Table 0 still contradicts the HSTU parity evidence.** Change the row from
   "no numerical-parity claim" to the actual boundary: exact core-block parity
   against the reference research implementation; no pinned end-to-end official
   system reproduction.
4. **GrIT is an uncited same-protocol-family comparator.** GrIT's AR2023
   Video_Games statistics match the paper's 5-core family and it reports
   NDCG@10 0.0588. The manuscript should cite it and explain that the present
   0.0673 multi-seed result is higher, while protocol/training details still
   need careful comparability wording.
5. **Venue planning needs a source boundary.** The TORS-first / RecSys-later
   sequence is consistent with ACM no-dual-submission policy, but RecSys 2027
   deadlines are not yet verifiable. Use RecSys 2026 only as precedent, not as a
   hard 2027 claim.

### Plausible Risks Requiring Author Verification

- Whether `VENUE_PLAN.md` should be amended now to say "RecSys 2027 dates TBD"
  instead of "`deadline ~spring 2027`".
- Whether the deposit/release manifest should be regenerated for HEAD `5df3d37`
  or explicitly scoped to the earlier paper-artifact commit.
- Whether GrIT's reported preprocessing/evaluation is close enough to Table 1b
  to include in a numerical comparator table, or only in related work.
- Whether untracked `paper_tex/` smoke artifacts are intended derived-output
  scaffolding for the TORS conversion or should be removed before packaging.

### External Fact-Check / Novelty Notes

- ACM's current author workflow says review submissions should use the
  single-column `manuscript` option of `acmart`; its ACM template page also says
  ACM journals use `acmsmall` except listed exceptions. Source:
  https://www.acm.org/publications/authors/submissions
- ACM policy says manuscripts under review are generally not allowed to be
  simultaneously under review elsewhere without explicit permission, supporting
  the non-simultaneous venue sequence in `VENUE_PLAN.md`. Source:
  https://www.acm.org/publications/policies/simultaneous-submissions
- RecSys 2026 required reproducibility/resource submissions to provide relevant
  artifacts, source code/data, installation instructions, and hardware
  documentation; it also prohibited dual submissions. This is precedent only;
  RecSys 2027 details are not yet established. Source:
  https://recsys.acm.org/recsys26/call/
- AR2023 documentation confirms user review text, timestamps, metadata, images,
  and user IDs, which supports the ethics/data-use concern. Source:
  https://amazon-reviews-2023.github.io/
- GrIT (arXiv:2602.19728) reports AR2023 Video_Games 5-core statistics matching
  this protocol family (94,762 users, 25,612 items, 814,586 interactions), uses
  full-item-set ranking, and reports NDCG@10 0.0588. Source:
  https://arxiv.org/abs/2602.19728 and
  https://arxiv.org/html/2602.19728v1

### Concrete Fixes To Make Next

1. Embed and visually verify Fig. 1-3.
2. Add an ethics/privacy/data-use statement.
3. Fix Table 0 HSTU parity wording.
4. Cite/scope GrIT and add the broader frequency/time-frequency SR references.
5. Correct stale page-count metadata in `CANONICAL_SUBMISSION.md` and avoid
   reusing older response prose as submission metadata.
6. Amend `VENUE_PLAN.md` to mark RecSys 2027 dates as TBD, or cite the eventual
   official 2027 CFP once available.
7. Resolve whether `RELEASE_MANIFEST.json` should be regenerated for current
   HEAD before any release/deposit bundle.
8. Triage untracked `paper_tex/` smoke artifacts before commit/release.

### Running Checklist

- [x] Read automation memory.
- [x] Preserve existing uncommitted audit content.
- [x] Re-run the strict submission gate.
- [x] Inspect manuscript source, compiled PDF, render HTML, figures, manifest,
      venue plan, and DOI note.
- [x] Render representative PDF pages with `pypdfium2`.
- [x] Fact-check ACM submission/dual-submission policy, RecSys reproducibility
      precedent, AR2023 data fields, and GrIT.
- [ ] Embed and visually verify Fig. 1-3.
- [ ] Add ethics/privacy/data-use statement.
- [ ] Fix Table 0 HSTU parity wording.
- [ ] Cite/scope GrIT and frequency/time-frequency SR papers.
- [ ] Fix stale page-count and manifest-boundary metadata.
- [ ] Move to target TORS/ACM formatting.
- [ ] Triage untracked `paper_tex/` smoke artifacts.

## Audit Run - 2026-07-12 09:40 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `9686cfb` (`Respond to
  PAPER_REVIEW_AUDIT run 08:31: preprint references completed with fetched
  metadata`)
- Note: before this section was written, `PAPER_REVIEW_AUDIT.md` was already
  modified with an uncommitted 09:37 audit section. I preserved that section and
  added only this incremental audit plus the risk-list updates above.
- Canonical source/artifacts inspected: `PAPER_SUBMISSION.md`,
  `CANONICAL_SUBMISSION.md`, `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`,
  `PAPER_SUBMISSION.pdf`, `RELEASE_MANIFEST.json`, `THEIRS_ON_OURS_REPORT.md`,
  `figures/*`, and the strict rebuild wrapper.
- Visual PDF check: rendered selected pages 1, 14, 15, 16, 18, 23, 24, 25, 26,
  28, 34, 35, and 38 with Poppler `pdftoppm.exe` into
  `tmp/pdfs/hourly_audit_20260712_0625/`.

### Verdict

**The numerical/artifact core still passes, but the submission package remains
not top-journal-ready.** The strict gate recomputes all manuscript numbers and
passes. The remaining rejection risks are now mostly presentation, consistency,
and literature-positioning issues: missing embedded figures, no ethics/data-use
statement, a contradicted HSTU-parity sentence in Table 0, and an under-covered
frequency/time-frequency related-work line.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    required claim families sourced.
  - PASS: release manifest verification, 111 files verified.
  - PASS: MI V2 dual gate. K=16 CI-LB 0.04096 and K=8 CI-LB 0.04083 both exceed
    the published HSTU-BLaIR 0.0406 point estimate.
  - PASS/VOID: Office arithmetic passes, but Office remains descriptive and VOID.
- `pypdf` extraction / PDF metadata:
  - `PAPER_SUBMISSION.pdf` has 38 pages and no image objects.
  - Non-ASCII extraction warnings were math/typographic symbols only, not
    mojibake.
- Visual rendering:
  - Tables are readable overall.
  - Table 2 has a polish defect: the page break leaves an isolated continuation
    cell ("dv=dqk=16 spec") at the top of page 26.
  - Fig. 1-3 are still not embedded in the rendered PDF.
- Text/source scan:
  - Confirmed contradiction: `PAPER_SUBMISSION.md` Table 0 says "no
    numerical-parity claim"; Section 3.7 and limitations say the core block is
    exactly parity-tested.
  - Confirmed omission: `PAPER_SUBMISSION.md` does not mention FEARec, MUFFIN,
    WEARec, WPGRec, or equivalent broader frequency/time-frequency SR coverage.

### Confirmed Problems

1. **HSTU fidelity wording contradicts itself.** Fix Table 0's HSTU-base row so
   it no longer says "no numerical-parity claim". Suggested boundary:
   "core-block parity demonstrated against the reference research
   implementation; no pinned end-to-end system reproduction."
2. **Frequency-filter related work is too narrow.** Add a short sentence and
   references around the FMLP/BSARec novelty-boundary paragraph acknowledging
   the broader frequency/time-frequency SR line. The causal FIR contribution can
   still be framed as narrower: left-causal, depthwise FIR, HSTU-style stack,
   all-position next-item objective, full-catalog AR2023 LLOO.
3. **PDF page-count statements are stale in response/canonical files.**
   `CANONICAL_SUBMISSION.md` still says the PDF is 36 pp; the newest PDF is
   38 pp. `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` contains both corrected 38 pp
   language and older 37 pp language in older response sections. This is not a
   scientific problem, but do not use stale response prose as submission-package
   metadata.
4. **Table 2 page break needs polishing.** The isolated continuation cell is not
   data-corrupting, but a reviewer-facing PDF should avoid dangling table cells.

### Plausible Risks Requiring Author Verification

- The 09:37 audit's missing-figures and no-ethics findings remain the dominant
  submission-readiness blockers.
- The broader frequency/time-frequency literature may contain additional
  directly relevant work beyond the four examples checked here. A venue-format
  pass should do one final targeted search before freezing the references.
- The release manifest boundary still depends on whether the next package is
  cut from `9ed7be3` assets or from current HEAD `9686cfb`.

### External Fact-Check / Novelty Notes

- FEARec (SIGIR 2023) explicitly frames self-attention SR as low-pass and
  proposes a frequency-enhanced hybrid attention network. Source:
  https://arxiv.org/abs/2304.09184
- MUFFIN (CIKM 2025) is a user-adaptive frequency-filtering SR model and frames
  itself against limitations of earlier frequency-domain SR models. Source:
  https://arxiv.org/abs/2508.13670
- WEARec (AAAI 2026) proposes dynamic frequency-domain filtering plus wavelet
  feature enhancement for sequential recommendation. Source:
  https://arxiv.org/abs/2511.07028
- WPGRec (2026 preprint) proposes wavelet-packet guided graph-enhanced
  sequential recommendation. Source: https://arxiv.org/abs/2604.21305

### Concrete Fixes To Make Next

1. Embed and visually verify Fig. 1-3.
2. Add the ethics/privacy/data-use statement.
3. Fix the HSTU-base row in Table 0.
4. Add the frequency/time-frequency related-work sentence and references.
5. Fix the Table 2 page break during venue-template formatting.
6. Decide whether to update the release-manifest boundary from `9ed7be3` to
   current HEAD before the next deposit/release bundle.

### Running Checklist

- [x] Read automation memory.
- [x] Re-read the current cumulative audit and preserve existing uncommitted
      audit content.
- [x] Re-run the strict submission gate.
- [x] Inspect canonical source, response, manifest, PDF, and figure assets.
- [x] Render representative PDF pages.
- [x] Fact-check the broader frequency/time-frequency SR line.
- [ ] Embed and visually verify Fig. 1-3.
- [ ] Add ethics/privacy/data-use statement.
- [ ] Fix Table 0 HSTU parity wording.
- [ ] Add frequency/time-frequency related-work coverage.
- [ ] Triage/cite GrIT and any other same-statistics AR2023 5-core papers.
- [ ] Resolve release-manifest boundary if cutting a new release.
- [ ] Move to target venue formatting.

## Audit Run - 2026-07-12 09:37 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `9686cfb` (`Respond to
  PAPER_REVIEW_AUDIT run 08:31: preprint references completed with fetched
  metadata`)
- Tracked working tree after verification and before writing this audit section:
  clean. After this audit update, only `PAPER_REVIEW_AUDIT.md` is modified.
- Canonical source/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `_paper_render.html`,
  `RELEASE_MANIFEST.json`, `_bestrec_run/rebuild_hstu_submission.py`,
  `_bestrec_run/render_paper_pdf.py`, `figures/*`, prior cumulative audit and
  response files.
- Visual PDF check: rendered selected pages 1, 14, 19, 23, 32, and 34 with
  `pypdfium2` into `tmp/pdfs/hourly-strict-paper-audit-visual/`. Poppler wrapper
  commands (`pdfinfo.cmd`, `pdftoppm.cmd`) were present but failed with "The
  system cannot find the path specified", so `pypdfium2` was used instead.

### Verdict

**The prior 2026-reference problem is fixed.** The four recent preprints now
have full bibliographic entries, and the compiled PDF contains SID-MLP, Latte,
ChronoSID, ReSID, and the new author/title metadata. The stale first/only
AR2023 phrases remain absent from the PDF.

**The strict result/artifact gate still passes.** The build recomputes 164 paper
cells, reports 0 mismatches and 0 untraceable cells, verifies 111 manifest files,
passes MI dual-gate arithmetic, and keeps Office descriptive/VOID.

**New top-journal risk: the paper refers to figures that are not actually in the
PDF.** The figure files exist on disk, but `PAPER_SUBMISSION.md` uses prose
references such as `Fig. 1 (figures/fig_tail_law_mechanism)` rather than image
inclusion syntax, `_paper_render.html` has no `<img>` tags for them, and a PDF
page-image scan found no embedded image objects. This is a confirmed
submission-readiness defect, not a scientific-result defect.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    claim families sourced.
  - PASS: release manifest verification, 111 files verified.
  - PASS: MI V2 dual gate. K=16 mean 0.04152, CI-LB 0.04096; K=8 mean 0.04120,
    CI-LB 0.04083; both above the published HSTU-BLaIR 0.0406 point estimate.
  - PASS/VOID: Office arithmetic passes, but Office remains descriptive and VOID.
- PDF text extraction using `pypdf`:
  - 38 pages, 830,097 bytes.
  - `first to report numbers`, `only published work using AR2023`, and `first
    such reported number`: absent.
  - `SID-MLP`, `Latte`, `ChronoSID`, `ReSID`, and the author/title strings for
    Guo/Hou/Huang/Liang entries: present.
- Visual/layout sampling with `pypdfium2`:
  - Selected text/table pages are readable and not visibly clipped.
  - No venue template, page numbers, headers, or journal formatting were added.
  - Confirmed missing embedded figures: source contains no Markdown image
    syntax, `_paper_render.html` has no image tags for Fig. 1-3, and `pypdf`
    found no page images.
- `git status --short`
  - Clean after strict rebuild and audit inspection, before writing this audit
    section.

### Confirmed Fixes Since The 08:31 Audit

1. **Bare 2026 preprint references fixed.** `PAPER_SUBMISSION.md` now gives
   author/title metadata for SID-MLP, Latte, ChronoSID, and ReSID, with an
   explicit unreviewed-concurrent-work fence.
2. **Latte MI/VG numbers rechecked.** Latte's Table 1 reports the values quoted
   by the manuscript: Instruments NDCG@10 0.0331 and Games NDCG@10 0.0515.
3. **PDF/manifest/audit dirty state resolved.** The branch is clean at HEAD
   `9686cfb`; the prior dirty regenerated PDF/manifest state has been committed.

### Confirmed Problems

1. **Figures absent from the compiled paper.** The paper's live scientific story
   relies on Fig. 1-3, but the PDF currently contains only prose references to
   figure filenames. Fix by embedding the PNG/PDF figure assets in the manuscript
   source and rerendering. Then visually inspect pages containing each figure.
2. **No ethics/privacy/data-use section.** The paper uses a large public review
   dataset that includes user review text, timestamps, item metadata/images, and
   pseudonymous user IDs. A submission should include a short ethics/data-use
   statement covering public-data use, privacy/PII handling, license/terms,
   limitations of recommender deployment, and whether IRB/human-subjects review
   was not required.
3. **Current release manifest commit does not equal current HEAD.**
   `RELEASE_MANIFEST.json` records `git_commit = 9ed7be3...`, while the current
   HEAD is `9686cfb...`. Strict verification passes because the response-only
   commit does not affect the release assets, but this distinction should be
   explicit if cutting a release from HEAD.

### Plausible Risks Requiring Author Verification

- **GrIT related-work coverage.** GrIT is not currently cited. It reports on
  Amazon Reviews 2023 Video_Games with the same 94,762 users / 25,612 items /
  814,586 interactions statistics and NDCG@10 0.0588. It is below this paper's
  0.0673 and below HSTU-BLaIR's 0.0760, so it does not invalidate the result,
  but a reviewer could object that a same-statistics 2026 AR2023 sequential
  recommender was missed.
- **RPORec and other 2026 LLM/generative AR2023 papers are non-comparable but
  should be triaged.** RPORec explicitly omits the 5-core filter and uses a
  one-year temporal truncation, so it should not be compared numerically. It may
  still belong in a "recent non-comparable AR2023 protocols" sentence if the
  venue expects very fresh coverage.
- **Mechanism wording remains close to the line.** The paper repeatedly scopes
  "driver" and "partial causal role" to synthetic thinning interventions, which
  is good. Preserve those caveats if the abstract/introduction is shortened.
- **Page design is readable but not journal-ready.** The sampled PDF pages are
  legible, but the document is a Markdown/HTML render without target venue
  layout, headers/footers, figure placement, or formal caption formatting.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR reports AR2023 5-core statistics and comparator values used by the
  manuscript: Video_Games HSTU-BLaIR NDCG@10 0.0760, Office_Products 0.0271,
  Musical_Instruments 0.0406. Source: https://arxiv.org/html/2504.10545v3
- Latte reports Instruments NDCG@10 0.0331 and Games NDCG@10 0.0515 in its
  Table 1. Source: https://arxiv.org/html/2605.06331v1
- SID-MLP reports same-family Instruments/Games numbers, including Sid-Mlp
  Instruments NDCG@10 0.0332 and Games NDCG@10 0.0512. Source:
  https://arxiv.org/html/2605.12617v1
- ReSID reports MI NDCG@10 0.0346 under its own filtered universe. Source:
  https://arxiv.org/html/2602.02338v1
- ChronoSID's output-level MI table reports ReSID 0.0325 vs ChronoSID 0.0345
  NDCG@10 with paired-bootstrap confidence intervals. Source:
  https://arxiv.org/html/2607.03918v1
- GrIT uses Amazon Reviews 2023 Video_Games with 94,762 users, 25,612 items, and
  814,586 interactions, and reports Video_Games NDCG@10 0.0588. Source:
  https://arxiv.org/html/2602.19728v1
- RPORec uses the latest Amazon source but states it omits 5-core filtering and
  uses a one-year temporal truncation, making it non-comparable to the paper's
  fixed 5-core LLOO protocol. Source: https://arxiv.org/html/2605.21967
- Amazon Reviews 2023's official site states the dataset includes user reviews,
  item metadata, and links, with 571.54M reviews and interactions through
  September 2023. Source: https://amazon-reviews-2023.github.io/

### Concrete Fixes To Make Next

1. Embed Fig. 1-3 in `PAPER_SUBMISSION.md` with real captions, rerender
   `PAPER_SUBMISSION.pdf`, and visually inspect every figure page.
2. Add a short ethics/privacy/data-use section before Code and Data Availability
   or inside Limitations.
3. Add GrIT to the 2026 AR2023 related-work paragraph, or explicitly scope it
   out as non-text/non-HSTU but same-statistics Video_Games context.
4. If preparing a release/deposit from current HEAD, regenerate
   `RELEASE_MANIFEST.json` or document why the manifest boundary remains
   `9ed7be3`.
5. Move the manuscript into the target venue template after the figure/ethics
   fixes, then repeat full visual QA.

### Open Questions

- What is the target venue/template? This now blocks final submission readiness.
- Should GrIT be cited in the main text as same-statistics AR2023 Video_Games
  context, or confined to a recent-preprints footnote?
- Are the three figure files intended as main-paper figures or supplementary
  figures? The current text treats them as main-paper figures.

### Running Checklist

- [x] Read automation memory.
- [x] Locate canonical manuscript source and PDF.
- [x] Verify current HEAD and clean working tree.
- [x] Rerun strict submission gate.
- [x] Check compiled PDF text for stale novelty phrases and new references.
- [x] Fact-check the 2026 preprint metadata/numbers against primary sources.
- [x] Perform a fresh AR2023-related-work search.
- [x] Render selected PDF pages for visual inspection.
- [x] Detect missing embedded figures.
- [ ] Embed and visually verify Fig. 1-3 in the compiled PDF.
- [ ] Add ethics/privacy/data-use statement.
- [ ] Triage/cite GrIT and any other same-statistics AR2023 5-core papers.
- [ ] Resolve release-manifest boundary if cutting a new release.
- [ ] Move to target venue formatting.

## Audit Run - 2026-07-12 08:31 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD at final verification: `codex/bestrec-sota-results` /
  `9ed7be3` (`Respond to PAPER_REVIEW_AUDIT run 07:28: literature framing
  fixed (no priority claims), references completed`)
- Note: the branch advanced during this automation run from `a889053` to
  `9ed7be3` via commits at 2026-07-12 08:29-08:30 Australia/Sydney. I treated
  the new HEAD as the current workspace state and did not revert it.
- Current modified tracked files after this audit:
  `PAPER_SUBMISSION.pdf`, `RELEASE_MANIFEST.json`, and this audit file.
- Canonical source/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_DRAFT.md`, `PAPER_SUBMISSION.pdf`, `RELEASE_MANIFEST.json`,
  `_bestrec_run/rebuild_hstu_submission.py`, `_bestrec_run/render_paper_pdf.py`,
  and the cumulative audit.

### Verdict

**The previous literature-framing rejection risk is now fixed in the source and
the regenerated PDF.** The stale "first to report numbers", "only published work
using AR2023", and "first such reported number" phrases are gone. The paper now
separates same-statistics AR2023 5-core LLOO preprints (SID-MLP, Latte), the
ReSID/ChronoSID filtered SID universe, and older Amazon-2014 TIGER/LIGER
protocols.

**Scientific core remains conditionally defensible under the narrowed claim
boundary.** The strict gate still passes; Video_Games is not claimed as SOTA,
Musical_Instruments remains a per-category point-estimate comparison, and Office
remains VOID/descriptive.

**Main remaining top-journal risk is polish, not result invalidation.** Full
metadata for the 2026 arXiv-only references and venue formatting remain open.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact (`max|diff| = 0.000e+00`).
  - PASS: 164 paper cells recomputed; 0 `MISMATCH`; 0 `UNTRACEABLE`; all 12
    claim families sourced.
  - PASS: release manifest verification after regeneration: 111 files verified.
  - PASS: MI V2 gate. K=16 mean 0.04152, CI-LB 0.04096; K=8 mean 0.04120,
    CI-LB 0.04083; both above the published HSTU-BLaIR 0.0406 point estimate.
  - PASS/VOID: Office arithmetic gates pass, but Office remains descriptive and
    VOID because the preregistered floor check failed.
- `uv --project _bestrec_run run python _bestrec_run/render_paper_pdf.py`
  - Regenerated `PAPER_SUBMISSION.pdf`: 827,780 bytes, 38 pages, placeholder
    scan clean.
- PDF text extraction using `pypdf`:
  - `first to report numbers`: absent.
  - `only published work using AR2023`: absent.
  - `where we are the first`: absent.
  - `first such reported number`: absent.
  - `SID-MLP`, `Latte`, and the revised BLaIR/AR2023 historical note: present.
- `uv --project _bestrec_run run python _bestrec_run/update_release_manifest.py --verify`
  - Initially failed only because the regenerated PDF hash differed from the
    manifest.
  - `--regen` refreshed `RELEASE_MANIFEST.json` to `git_commit =
    9ed7be3ee79822fd1bca59fedd29618539aded4b`; final strict verification
    passed.

### Confirmed Fixes Since The 07:28 Audit

1. **Priority/novelty wording fixed.** The manuscript no longer claims to be
   first to report AR2023 5-core LLOO numbers, and Appendix A.3 no longer says
   BLaIR is the only published work using AR2023.
2. **2026 AR2023 coverage expanded.** The related-work/comparability paragraph
   now includes SID-MLP and Latte in addition to ReSID and ChronoSID, and keeps
   the protocol families separate.
3. **Named prior-art references mostly filled.** The References section now has
   entries for TiSASRec, VQ-Rec, ProtoMF, MELT, DropoutNet, and CLCRec, plus
   arXiv-identifier entries for ReSID, ChronoSID, SID-MLP, and Latte.
4. **PDF and manifest refreshed.** The compiled PDF no longer contains the stale
   phrases, and the manifest verifies the regenerated PDF hash.

### Confirmed Problems

1. **Bare references for four recent preprints.** ReSID, ChronoSID, SID-MLP, and
   Latte are currently listed by name + arXiv ID only. That is acceptable for an
   internal audit but weak for a top-journal bibliography.
2. **Working tree is intentionally dirty.** `PAPER_SUBMISSION.pdf` and
   `RELEASE_MANIFEST.json` changed during this run. Keep or commit them with the
   audit; do not mix the regenerated PDF with an older manifest boundary.

### Plausible Risks Requiring Author Verification

- The paper says Latte reports MI NDCG@10 0.0331 and VG 0.0515. I confirmed
  Latte uses the same MI/VG dataset statistics from its arXiv HTML, but the
  exact two NDCG values should be checked once more against the paper's table
  before final submission because the table extraction is brittle.
- The phrase "The Musical_Instruments comparator reproduces" is defensible only
  because the surrounding paragraphs caveat the run as environment-caveated and
  unpinned. If space edits shorten Section 5.6, preserve the caveat.
- The related-work freshness scan was broad, not exhaustive. Triage additional
  2026 AR2023 recommender preprints for relevance before a real submission.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's public repository reports the exact comparator values used by the
  paper: Video_Games HSTU-BLaIR NDCG@10 0.0760, Office_Products 0.0271, and
  Musical_Instruments 0.0406, with expected small run variability. Source:
  https://github.com/snapfinger/HSTU-BLaIR
- SID-MLP (arXiv:2605.12617) uses Amazon Reviews 2023 5-core last-out splits and
  reports the same MI/VG dataset statistics as this paper's HSTU-BLaIR-family
  universe: MI 57,439 / 24,587 / 511,836 and VG 94,762 / 25,612 / 814,586.
  Source: https://arxiv.org/html/2605.12617v1
- Latte (arXiv:2605.06331) uses Amazon Reviews 2023 Instruments/Scientific/Games
  leave-one-out and reports the same statistics for Instruments and Games.
  Source: https://arxiv.org/html/2605.06331v1
- ReSID (arXiv:2602.02338) evaluates Amazon-2023 subsets under its own filtered
  universe: MI 57,359 / 23,742 / 490,522 and VG 94,515 / 24,685 / 772,218.
  Source: https://arxiv.org/html/2602.02338v1
- ChronoSID (arXiv:2607.03918) reports an output-level MI comparison with ReSID
  0.0325 vs ChronoSID 0.0345 NDCG@10 and paired-bootstrap confidence intervals.
  Source: https://arxiv.org/html/2607.03918v1
- Amazon Reviews 2023's official site describes the dataset and standard
  processing resources; it is the correct source for dataset-level facts.
  Source: https://amazon-reviews-2023.github.io/

### Concrete Fixes To Make Next

1. Expand the four 2026 preprint references from bare arXiv IDs to full
   author/title entries.
2. Decide whether to include a short "recent preprints" paragraph for other
   2026 AR2023 recommendation papers found by fresh search, or explicitly scope
   the paper to the HSTU-BLaIR/SID-protocol families.
3. Commit `PAPER_SUBMISSION.pdf`, `RELEASE_MANIFEST.json`, and this audit file
   together if this regenerated artifact state is accepted.
4. Move the manuscript into the target venue template and rerun the PDF visual
   check after formatting.

### Open Questions

- What is the target venue? The current Markdown/Chrome PDF is readable but not
  venue-formatted.
- Does the author want to cite all very recent 2026 arXiv preprints in the main
  paper, or keep only those that directly threaten priority/comparability?

### Running Checklist

- [x] Read automation memory.
- [x] Locate canonical manuscript source and PDF.
- [x] Detect branch advancement and audit the final HEAD.
- [x] Verify stale first/only AR2023 phrases are absent from source.
- [x] Regenerate `PAPER_SUBMISSION.pdf`.
- [x] Verify stale phrases are absent from extracted PDF text.
- [x] Regenerate `RELEASE_MANIFEST.json`.
- [x] Rerun strict submission gate after PDF/manifest refresh.
- [x] Fact-check the key novelty/comparator literature against primary sources.
- [ ] Expand 2026 preprint references to full bibliographic entries.
- [ ] Commit the regenerated PDF, manifest, and audit if this state is kept.
- [ ] Move to target venue formatting.

## Audit Run - 2026-07-12 07:28 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `a889053` (`Respond to PAPER_REVIEW_AUDIT run 1 (cumulative format): all 3 confirmed problems fixed, open questions answered`)
- Tracked working tree after verification: clean.
- Automation last-run cutoff supplied by the runner: `2026-07-11T20:24:42.912Z`
  (= 2026-07-12 06:24:42 Australia/Sydney). Only
  `_bestrec_run/hstu_tables.json` had a newer mtime; strict rebuild rewrote it
  and the tracked tree remained clean.
- Canonical manuscript source/artifact found:
  `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`, `PAPER_DRAFT.md`,
  `CANONICAL_SUBMISSION.md`, `RELEASE_MANIFEST.json`, `_bestrec_run/*`.
- PDF artifact exists (`PAPER_SUBMISSION.pdf`, 813,880 bytes, last written
  2026-07-12 04:26:17). Fresh `pdfinfo` inspection failed on this Windows
  environment with "The system cannot find the path specified"; this run did
  not perform a fresh visual PDF render.

### Verdict

**Scientific core remains conditionally defensible, but the literature framing
needs revision before top-journal submission.** The strict artifact gate passes
and the paper still avoids broad SOTA / paired-superiority claims. However, the
current source contains stale priority/novelty wording that a reviewer can
falsify quickly from current AR2023 generative-recommendation papers.

**Artifact package: improved since the prior audit.** The previous cell-count
and manifest-scope problems are resolved.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU parity OK.
  - PASS: submission table build green, **164 cells**, 0 `MISMATCH`, 0
    `UNTRACEABLE`, all 12 declared claim families sourced.
  - PASS: `RELEASE MANIFEST VERIFY: OK (111 files verified, 0 release-asset
    files not local)`.
  - PASS: MI V2 dual gate.
  - PASS: Office adjudication remains descriptive/VOID.
- `git status --short`
  - Clean before and after strict rebuild.
- `rg`/`Select-String` checks:
  - Confirmed no stale "163 cells" in `CANONICAL_SUBMISSION.md`.
  - Confirmed `RELEASE_MANIFEST.json` has a `reference_runs` section hashing
    local reference-run artifacts, including `office_hstu_blair`.
  - Confirmed `.gitignore` excludes `/_paper_render.html` and `/tmp/` under a
    "never release-swept" scratch comment.
  - Located stale literature wording in `PAPER_SUBMISSION.md:282` and
    `PAPER_SUBMISSION.md:619`.
  - Located missing-reference candidates in body/table mentions:
    TiSASRec, VQ-Rec, ProtoMF, MELT, DropoutNet, CLCRec, ReSID, ChronoSID,
    SASRecText.

### Confirmed Fixes Since Prior Audit

1. **Stale table-cell count fixed in canonical source.** `CANONICAL_SUBMISSION.md`
   now points to strict-build invariants and says the authoritative count is the
   build output; the current strict output is 164 cells.
2. **Office HSTU-BLaIR reference-run artifacts are now manifest-scoped.**
   `RELEASE_MANIFEST.json` contains a `reference_runs` section with hashes for
   the three local reference-implementation runs, including
   `_bestrec_run/theirs_runs/office_hstu_blair/*`; strict verification now
   checks 111 files.
3. **Render scratch is explicitly ignored.** `.gitignore` excludes
   `/_paper_render.html` and `/tmp/`, reducing accidental release-sweep risk.

### Confirmed Problems

1. **Stale "first to report numbers" claim.** `PAPER_SUBMISSION.md:282` says:
   "Among methods evaluated on the AR2023 5-core LLOO protocol (where we are
   the first to report numbers)..." This conflicts with:
   - HSTU-BLaIR, already used as the paper's own AR2023 5-core comparator.
   - SID-MLP (arXiv:2605.12617), which reports AR2023 5-core LLOO statistics
     matching this paper's MI/VG universe (MI 57,439 / 24,587 / 511,836; VG
     94,762 / 25,612 / 814,586).
   - Latte (arXiv:2605.06331), which reports the same MI/VG/Scientific
     statistics and AR2023 LLOO setup.
   Fix: delete the parenthetical or narrow it to the exact model/artifact claim
   being made; do not claim first protocol numbers.
2. **Appendix A.3 contradicts the body and current literature.**
   `PAPER_SUBMISSION.md:619` says "BLaIR ... is the only published work using
   AR2023." The body itself cites HSTU-BLaIR as the relevant AR2023 5-core
   reference, and the 2026 literature now includes additional AR2023 papers.
   Fix: rewrite this appendix note as historical/superseded and say no
   *comparable Beauty_and_Personal_Care 5-core number* was found, rather than
   saying BLaIR is the only AR2023 work.
3. **References section is incomplete relative to named prior art.** Any
   top-journal reviewer checking Table 0 will expect full bibliographic entries
   for every named method. Add full references for all named methods or remove
   names that are not essential.

### Plausible Risks Requiring Author Verification

- The ChronoSID sentence says its output-level MI table is "five-run averages."
  The source table reports paired-bootstrap confidence intervals for the
  ReSID-vs-ChronoSID output-level comparison; verify whether "five-run averages"
  is supported elsewhere or delete that phrase.
- The phrase "A faithful HSTU implementation" in `PAPER_SUBMISSION.md:264`
  could be misread against the later "HSTU-style pure-PyTorch implementation"
  and shimmed reference-regeneration discussion. Consider rephrasing to
  "faithful pinned-environment HSTU-BLaIR reproduction" to keep the boundary
  precise.
- `pdfinfo`/visual PDF check was not completed in this run. If this audit is
  used for final submission readiness, rerender or visually inspect the PDF
  after the literature/reference edits.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's public repository reports the key comparator rows used in the
  manuscript: Video Games HSTU-BLaIR NDCG@10 0.0760, Office Products 0.0271,
  and Musical Instruments 0.0406; it also states expected small reproduction
  variability. Source: https://github.com/snapfinger/HSTU-BLaIR
- ReSID (arXiv:2602.02338) evaluates Amazon Reviews 2023 subsets and reports a
  different MI filtered universe (57,359 users / 23,742 items / 490,522
  interactions) plus MI N@10 0.0346 in its main results table. Source:
  https://arxiv.org/html/2602.02338v1
- ChronoSID (arXiv:2607.03918) uses the same ReSID-style MI/VG universe and
  reports MI N@10 0.0346 in its main table, plus an output-level table with
  ReSID 0.0325 vs ChronoSID 0.0345. Source:
  https://arxiv.org/html/2607.03918v1
- SID-MLP (arXiv:2605.12617) is a relevant 2026 generative-recommendation
  paper using AR2023 5-core leave-one-out; its dataset statistics match the
  HSTU-BLaIR-family MI/VG statistics in this manuscript. Its N@10 numbers are
  lower than this paper's MI/VG results, so it does not overturn the claimed
  empirical margin, but it does invalidate "first report" wording. Source:
  https://arxiv.org/html/2605.12617v1
- Latte (arXiv:2605.06331) also uses AR2023 Instruments/Scientific/Games LLOO
  statistics matching the same MI/VG universe and reports N@10 0.0331
  (Instruments) and 0.0515 (Games). Source:
  https://arxiv.org/html/2605.06331v1

### Concrete Fixes To Make Next

1. Replace `PAPER_SUBMISSION.md:282` with a protocol-scoped statement such as:
   "Among our HSTU-style full-catalog AR2023 5-core LLOO runs, the model is a
   compact, reproducible baseline..." Do not use "first to report numbers."
2. Rewrite Appendix A.3 item 4 to remove "BLaIR is the only published work using
   AR2023"; preserve only the narrower Beauty_and_Personal_Care comparability
   point if still true after a fresh search.
3. Add full reference entries for TiSASRec, VQ-Rec, ProtoMF, MELT, DropoutNet,
   CLCRec, ReSID, ChronoSID, SID-MLP, Latte, and any other named method in
   Table 0/body prose.
4. Expand the 2026 semantic-ID/generative-retrieval paragraph to include
   SID-MLP and Latte, explicitly separating:
   - HSTU-BLaIR-family same-stat AR2023 5-core LLOO comparators.
   - ReSID/ChronoSID filtered-universe SID-line comparators.
   - Older Amazon 2014 TIGER/LIGER results.
5. Rerender and visually inspect `PAPER_SUBMISSION.pdf` after these text edits.

### Open Questions

- Is the Beauty_and_Personal_Care "first such reported number" claim still
  intended? It may be defensible only under a very narrow exact-universe
  definition; otherwise it should be softened to "we did not find a comparable
  public number."
- Should the paper cite very recent arXiv-only 2026 work in the main related
  work, or move it to a "concurrent and recent preprints" paragraph to avoid
  over-weighting unreviewed papers while still being complete?

### Running Checklist

- [x] Locate canonical manuscript source and PDF.
- [x] Read prior automation memory and prior cumulative audit.
- [x] Check files modified after the automation last-run cutoff.
- [x] Verify strict rebuild and release manifest.
- [x] Confirm prior audit's cell-count and manifest findings are resolved.
- [x] Fact-check comparator and novelty claims against current primary sources.
- [x] Identify stale first/only AR2023 wording.
- [x] Identify missing-reference candidates.
- [ ] Remove/soften stale first/only AR2023 claims.
- [ ] Add missing bibliographic references.
- [ ] Rerender and visually inspect the PDF after text edits.

## Audit Run - 2026-07-12 04:28 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch: `codex/bestrec-sota-results`
- HEAD at final verification: `3ca9617` (`Regenerate RELEASE_MANIFEST after Office HSTU-BLaIR integration`)
- Manifest boundary: `RELEASE_MANIFEST.json` records `git_commit =
  815259016ca78c11077e7834040eb25a76f3873a`, which is the parent of current
  HEAD. This matches the manifest's stated "manifest cannot hash itself;
  containing commit is immediate child" rule.
- Tracked working tree after verification: clean.
- Untracked scratch still present: `_paper_render.html`, `tmp/pdfs/...`.

### Verdict

**Narrow scientific core: still conditionally acceptable.** The paper now has a
defensible claim boundary: causal FIR as an incremental, leak-free adaptation;
dataset-conditional text/tail pattern; MI per-category point-estimate
comparison; Office descriptive/VOID; no Video_Games or broad SOTA claim.

**Artifact package: minor revision.** The strict rebuild passes, the manifest
verification passes, and the completed Office HSTU-BLaIR run is disclosed with
the right caveat. The remaining issues are documentation/manifest hygiene rather
than result invalidation.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU parity OK.
  - PASS: submission table build green, **164 cells**, 0 `MISMATCH`, 0
    `UNTRACEABLE`, 12/12 families sourced.
  - PASS: `RELEASE MANIFEST VERIFY: OK (96 files verified)`.
  - PASS: MI V2 dual gate.
  - PASS: Office adjudication remains descriptive/VOID.
- `uv --project _bestrec_run run python _bestrec_run/test_pinned_env_parity.py --mode pinned`
  - Correctly fails closed on Windows without real `fbgemm_gpu` instead of
    silently using shims.
- `uv --project _bestrec_run run python _bestrec_run/update_release_manifest.py --verify`
  - PASS at final state.
- `git ls-files _bestrec_run/theirs_runs/office_hstu_blair ...`
  - Confirms `office_hstu_blair.log`, `metrics.jsonl`, `run_meta.json`, gin
    config, and intended TensorBoard-log pointer are tracked.
- `rg "163 cells|164 cells|cells recomputed" ...`
  - Finds stale `163 cells` text in `CANONICAL_SUBMISSION.md` and
    `RESPONSE_TO_RESUBMISSION_AUDIT_ROUND3_2026-07-12.md`.
- `rg "office_hstu_blair|theirs_runs/office" RELEASE_MANIFEST.json`
  - No explicit top-level manifest entry for the completed Office HSTU-BLaIR
    run artifacts.

### Confirmed Fixes Since Prior Audit

- The active Office HSTU-BLaIR run is no longer hidden local state. It completed
  and is integrated into `PAPER_SUBMISSION.md`, `THEIRS_ON_OURS_REPORT.md`, and
  `_bestrec_run/hstu_results_manifest.json`.
- The completed Office HSTU-BLaIR result is reported cautiously:
  final NDCG@10 0.0275, best full eval 0.0279, vs published 0.0271. The paper
  correctly says this regenerates the published row within a small margin and
  **does not** un-void the preregistered Office result.
- The earlier inference that all published Office rows might be conservative is
  corrected: the local Office SASRec row is conservative relative to its
  published row (+13.9%), but Office HSTU-BLaIR only regenerates at +1.6%.
- The release manifest is current at the committed boundary and the strict
  wrapper now verifies it.
- The pinned-parity script's dangerous fallback is fixed: pinned mode refuses to
  treat shim fallback as publication evidence.

### Confirmed Problems

1. **Stale 163-cell text.** Update both stale locations to 164 cells or remove
   the exact cell count from prose. This is low effort and should be fixed before
   another release/deposit bundle.
2. **Top-level artifact manifest coverage is incomplete for the new local
   Office HSTU-BLaIR run.** This is not caught by `update_release_manifest.py
   --verify` because those run files are not currently in the top-level manifest
   scope. Either add hashes for:
   `_bestrec_run/theirs_runs/office_hstu_blair/metrics.jsonl`,
   `run_meta.json`, `hstu-sampled-softmax-n512-blair.gin`,
   `tb_logdir_intended.txt`, and `office_hstu_blair.log`; or add an explicit
   manifest note that these are git-tracked source artifacts governed by
   `_bestrec_run/hstu_results_manifest.json`, not release-manifest assets.
3. **Untracked render scratch remains.** `_paper_render.html` and `tmp/pdfs/*`
   are acceptable as local scratch, but should not be accidentally swept into a
   release unless intentionally archived.

### Plausible Risks Requiring Author Verification

- `CANONICAL_SUBMISSION.md` line describing the table generator says the
  "current state" is 163 cells. Because strict build now prints 164 cells, this
  could be read as a stale canonical state declaration.
- The paper's Section 5.6 table is now stronger, but the surrounding wording
  must continue to separate three concepts: published comparator point,
  unpinned local regeneration, and faithful pinned reproduction. The current
  caveat is adequate; do not shorten it for space without preserving that
  distinction.
- The DOI/deposit bundle should be checked after any manifest-scope change. The
  strict gate verifies current repo files, but the external release asset
  contents are only as good as the archived bundle.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR is a real 2025 comparator source and reports the key Amazon Reviews
  2023 5-core numbers used by the manuscript: Video_Games HSTU-BLaIR NDCG@10
  0.0760, Office_Products 0.0271, and Musical_Instruments 0.0406 in its results
  table. Source: https://arxiv.org/html/2504.10545v3
- HSTU is the relevant base architecture source and makes strong claims about
  generative recommenders and HSTU efficiency/quality. Source:
  https://arxiv.org/abs/2402.17152
- BLaIR introduced Amazon Reviews 2023 and the recommendation-specialized text
  encoders used by the comparator family. Source:
  https://arxiv.org/abs/2403.03952
- BSARec explicitly frames Transformer self-attention in sequential
  recommendation as low-pass / oversmoothing and uses Fourier-transform
  inductive bias. This supports the paper's claim that the frequency motivation
  is prior work, not novel. Source:
  https://ojs.aaai.org/index.php/AAAI/article/view/28747
- FMLP-Rec already used learnable frequency-domain filters for sequential
  recommendation. This supports the manuscript's narrow novelty boundary for
  the FIR module. Source: https://arxiv.org/abs/2202.13556
- TIGER uses semantic IDs for generative retrieval and reports SOTA claims on
  earlier Amazon review benchmarks, but those are not the same AR2023 5-core
  protocol. Source:
  https://papers.neurips.cc/paper_files/paper/2023/file/20dcab0f14046a5c6b02b61da9f13229-Paper-Conference.pdf
- LIGER is a relevant generative/dense retrieval comparator family, but its
  contribution is a hybrid retrieval method and not an apples-to-apples AR2023
  5-core LLOO comparator for this manuscript's main numbers. Source:
  https://arxiv.org/abs/2411.18814

### Open Questions

- Should `RELEASE_MANIFEST.json` explicitly include all local
  reference-implementation run artifacts, or is git tracking plus
  `_bestrec_run/hstu_results_manifest.json` the intended provenance layer?
- Will the next deposited release include the completed Office HSTU-BLaIR run
  artifacts, or are those repository-only descriptive artifacts?
- What target venue/template is intended? The current PDF is useful for review,
  but the paper is not yet venue-formatted.

### Running Checklist

- [x] Locate canonical manuscript source and PDF.
- [x] Inspect current claim boundary and prior response.
- [x] Verify strict rebuild.
- [x] Verify release manifest gate.
- [x] Verify pinned-mode fail-closed behavior.
- [x] Inspect completed Office HSTU-BLaIR disclosure.
- [x] Spot-check novelty/comparator claims against primary sources.
- [ ] Replace stale `163 cells` prose with `164 cells` or remove exact count.
- [ ] Decide whether to top-level hash-manifest the new Office HSTU-BLaIR run
      artifacts.
- [ ] Remove or intentionally archive render scratch files before release.
- [ ] Move to venue template when target venue is chosen.

## Audit Run - 2026-07-13 07:44 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch: `codex/bestrec-sota-results`
- HEAD: `acbe282f` (`Respond to PAPER_REVIEW_AUDIT run 05:40: breadth completed+integrated, conv prior art cited, provenance committed`)
- Tracked working tree before this audit section: clean.
- Untracked files present:
  - `_bestrec_run/results_OFFICEV3_k16_seed20260728.json`
  - `_bestrec_run/results_OFFICEV3_k16_seed20260728.users.jsonl.gz`
  - `_bestrec_run/results_OFFICEV3_k16_seed20260728.final.users.jsonl.gz`
  - `_bestrec_run/results_OFFICEV3_k16_seed20260728.json.treestate.txt`
  - `_bestrec_run/results_OFFICEV3_k16_seed20260729.json.treestate.txt`
  - `_bestrec_run/smoke_FIRB_IS_seed1.json`
  - `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`
  - `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`
- Current primary manuscript/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/main.tex`, `paper_tex/paper-shared.tex`,
  `paper_tex/PAPER_TORS.pdf`, `paper_tex/sections/*.tex`,
  `paper_tex/tables/*.tex`, `paper_tex/references.bib`,
  `PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`,
  `PREREG_OFFICE_V3.md`, `_bestrec_run/adjudicate_office_v3.py`,
  `paper_tex/BUILD_NOTES.md`, and `paper_tex/hygiene_scan_output.txt`.

### Verdict

**Scientific/result gate: green for the current manuscript.** I independently
reran the strict build and it passed: 166 recomputed cells, 0 mismatches,
0 untraceable values, all 13 declared claim families sourced, release-manifest
verification OK, MI dual gate PASS, and Office remains descriptive/VOID under
the earlier prereg.

**Top-journal readiness: still not clean.** The new hard risk is not the FIR
result; it is the Office V3 provenance/adjudication path. The paper now states
Office V3 is pending, which is acceptable, but the committed V3 adjudicator has
a bug in the dirty-tree exemption path that can make the campaign unverifiable
exactly when the new E1 erratum is needed.

**Live-state update during this audit:** Office V3 started while this audit was
running via `_bestrec_run/run_impact_program.sh`; k16 seed 20260728 completed
and k16 seed 20260729 was active. The completed seed recorded
`git_dirty_tracked=true` at commit `acbe282f` with the treestate sidecar showing
only `PAPER_REVIEW_AUDIT.md` as dirty, exactly the E1 case. Its final-epoch
full-catalog NDCG@10 is 0.03060398 (n_eval 223,308), above the V3 reference
0.0279, but this is 1/10 runs and has no campaign-level status.

### Prioritized Rejection-Risk List

1. **Confirmed blocker for Office V3 evidence, not current FIR claims:
   the Office V3 adjudicator's E1 path is broken.**
   `_bestrec_run/adjudicate_office_v3.py` references `os.path` and `RUN_DIR`
   at lines 203 and 205, but this file never imports `os` and never defines
   `RUN_DIR`. That code path executes when a run manifest has
   `git_dirty_tracked != false`, which is exactly the case E1 was added to
   handle. If the hourly audit/response logs dirty the tree during Office V3,
   the adjudicator will raise `NameError` instead of verifying the treestate
   sidecar. This contradicts the response file's claim that per-run treestate
   sidecars are verified by the adjudicator.
2. **Confirmed live-campaign provenance risk: Office V3 is now writing
   untracked result and treestate artifacts while the audit file is dirty.**
   The completed k16 seed 20260728 result has `git_dirty_tracked=true`; its
   pre/post treestate sidecar shows only `PAPER_REVIEW_AUDIT.md` as dirty, and
   the seed 20260729 pre-run sidecar already exists. This should be admissible
   under E1 if the adjudicator works, but the artifacts are currently untracked
   and the adjudicator's E1 code path is broken. Treat Office V3 as unaudited
   until the tool is fixed and the sidecar/result boundary is explicit.
3. **Confirmed documentation inconsistency: `paper_tex/BUILD_NOTES.md` is
   partially stale after the FIR-BREADTH sync.** The top of the file says
   `PAPER_TORS.pdf` is 39 pages and the current `hygiene_scan_output.txt`
   agrees. Later, the compile-status and directory-inventory sections still say
   35 pages / 36-page preview and claim ACM CCS concepts and keywords are not
   provided. `paper-shared.tex` now contains CCSXML, `\ccsdesc`, and `\keywords`.
   This is low scientific risk but looks careless in an artifact package.
4. **Plausible literature-risk requiring author verification: SILLM4Rec is
   closer than the paper's one-sentence exclusion may suggest.** Public ACM
   metadata says SILLM4Rec experiments use three 5-core Amazon Reviews 2023
   sub-datasets, and the public repo instructs users to download AR2023 5-core
   files. However, the repo workflow appears to generate candidate product
   ranking tasks and image/text preference summaries rather than full-catalog
   LLOO ranking, so the paper's current "excluded pending direct protocol
   inspection" stance remains defensible. Before freeze, inspect the ACM PDF
   directly or cite the repo-level non-comparability reason more explicitly.
5. **Plausible external-benchmark risk: LensKit Codex now has AR2023 5-core
   benchmark pages, but the site itself says it is work-in-progress and should
   not yet be cited or relied upon.** Do not cite it as evidence; keep it on the
   freeze sweep list because a reviewer may know of it or because it may mature
   before submission.

### Confirmed Fixes Since Last Audit

- The stale first/only AR2023 language flagged in earlier audits is not present
  in the current claim wording. The paper now states no protocol-priority claim
  and separates same-statistics AR2023 5-core LLOO, SID-line filtered-universe
  work, older Amazon-2014 TIGER/LIGER, and other AR2023-adjacent protocols.
- The FIR novelty boundary was materially improved. The paper now cites
  frequency/time-frequency prior art beyond FMLP-Rec/BSARec and explicitly
  names convolutional sequential-rec prior art (Caser and NextItNet), narrowing
  the contribution to a left-causal, depthwise FIR regularizer inside an
  HSTU-style stack.
- FIR-BREADTH is no longer a mid-campaign partial. `PREREG_FIR_BREADTH.md` was
  committed at `a7d6733d` before the result/adjudication commit `9619f5d4`, and
  `FIR_BREADTH_RESULTS.md` mechanically reports both new categories as
  CONFIRMED under the frozen rule:
  Industrial_and_Scientific mean paired delta +0.00240, 95% CI
  [+0.00183, +0.00297], 5/5 positive; CDs_and_Vinyl mean paired delta +0.00566,
  95% CI [+0.00493, +0.00639], 5/5 positive.
- The manuscript integrates the FIR-BREADTH result narrowly: four categories in
  total, zero per-category tuning for the breadth categories, no comparator
  claim, no SOTA language.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity OK.
  - PASS: `SUBMISSION BUILD GREEN: 166 cells recomputed from source artifacts; 0 untraceable, 0 paper mismatches, all 13 declared claim families sourced`.
  - PASS: `RELEASE MANIFEST VERIFY: OK (113 files verified, 0 release-asset files not local)`.
  - PASS: MI dual gate.
  - PASS: Office adjudication remains descriptive/VOID.
- `git status --short`
  - Tracked tree clean before the audit append.
  - During the audit, Office V3 started and added the untracked k16 seed
    20260728 result/user sidecars and seed 20260729 treestate sidecar listed above.
- `git log --follow -- PREREG_FIR_BREADTH.md`
  - Confirms prereg commit `a7d6733d` precedes the FIR result integration commit.
- `git log -- _bestrec_run/results_FIRB_... FIR_BREADTH_RESULTS.md`
  - Confirms result JSONs and adjudication record landed in `9619f5d4`.
- Manual source inspection:
  - `_bestrec_run/adjudicate_office_v3.py`: undefined `os` and `RUN_DIR` in the E1 branch.
  - `PREREG_OFFICE_V3.md`: E1 exempts exactly `PAPER_REVIEW_AUDIT.md` and
    `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`.
  - `paper_tex/BUILD_NOTES.md`: page-count/CCS sections stale relative to current output.
  - `paper_tex/hygiene_scan_output.txt`: current scan is PASS, 39 pages, no placeholder/forbidden failures.
- Live Office V3 process/result inspection:
  - `_bestrec_run/run_impact_program.sh` was active, running Office_Products k16
    seed 20260729 under `uv`.
  - Completed seed 20260728: final-epoch full-catalog NDCG@10 0.03060398,
    n_eval 223,308, `git_dirty_tracked=true`, final per-user sidecar recorded.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR (arXiv:2504.10545v3) reports the comparator-family AR2023 5-core
  statistics and numbers used by the paper: Video Games 25,612 items /
  94,762 users / 814,585 interactions and HSTU-BLaIR NDCG@10 0.0760; Office
  Products NDCG@10 0.0271; Musical Instruments NDCG@10 0.0406.
  Source: https://arxiv.org/html/2504.10545v3
- GrIT (arXiv:2602.19728v1) reports AR2023 Video Games full-item-set ranking
  with matching 5-core statistics and Video Games NDCG@10 0.0588. The paper's
  "point-estimate observation, not a claim" language is appropriate because
  training/protocol details have not been fully audited for comparability.
  Source: https://arxiv.org/html/2602.19728v1
- WPGRec appears on the official SIGIR 2026 accepted-papers page, supporting
  the bibliography note that it is accepted rather than merely an unreviewed
  arXiv preprint. Source: https://sigir2026.org/en-AU/pages/program/accepted-papers
- Caser and NextItNet are legitimate convolutional sequential-recommendation
  prior art, so adding them to the FIR novelty boundary was necessary and
  correct. Sources: https://arxiv.org/abs/1809.07426 and
  https://arxiv.org/abs/1808.05163
- Augment or Not? (arXiv:2505.23053) really uses Amazon'23 Musical Instruments
  and Industrial and Scientific under 5-core leave-one-out and reports MI
  NDCG@10 0.0282 for LETTER-TIGER in its table. Source:
  https://arxiv.org/pdf/2505.23053
- DiffuReason (arXiv:2602.09744) uses a different AR2023 "Video & Games"
  universe with 67,658 users / 25,535 items / 654,867 interactions, supporting
  the paper's non-comparability note. Source: https://arxiv.org/pdf/2602.09744
- SILLM4Rec metadata and repo evidence confirm AR2023 5-core relevance but not
  apples-to-apples full-catalog LLOO comparability. Sources:
  https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec
- LensKit Codex has AR2023 5-core pages, but its own header says it should not
  yet be cited or relied upon. Source: https://codex.lenskit.org/amazon/2023-5core/

### Concrete Fixes To Make Next

1. Fix `_bestrec_run/adjudicate_office_v3.py` before any Office V3 result is
   used: import `os` or use `Path`, define the sidecar directory as
   `_bestrec_run`, and add a small test/smoke path that exercises the E1 branch
   with a fake dirty manifest and treestate sidecar.
2. Decide and document the Office V3 treestate-sidecar boundary. If sidecars
   are evidence for E1, commit them with the corresponding result JSONs and
   include them in the adjudication/provenance story; if they are scratch, add
   an ignore rule and have the adjudicator read only committed sidecars or
   explicitly recorded run manifests.
3. Update `paper_tex/BUILD_NOTES.md` to remove stale page counts and the stale
   "CCS concepts / keywords not provided" warning. Make page counts refer to
   `hygiene_scan_output.txt` where possible.
4. Before submission freeze, inspect the SILLM4Rec ACM PDF directly. If it uses
   candidate ranking, say that explicitly in the paper rather than "pending
   direct protocol inspection"; if it is full-catalog LLOO, add it to the
   non-comparable or comparable-preprint paragraph as appropriate.
5. Keep the current SOTA/non-SOTA wording discipline. The strict scan's SOTA
   hits are all explicit non-claims; do not shorten these caveats for space.

### Open Questions

- Office V3 is already continuing while this audit has dirtied the tracked tree.
  The E1 adjudicator path must be fixed before any V3 result can be treated as
  auditable campaign evidence.
- Should `data_raw_proper/*/*.csv.gz` raw category archives be committed,
  ignored, or excluded by policy? The current provenance JSONs are tracked, but
  the raw gz files are not.
- Is `smoke_FIRB_IS_seed1.json` intentionally retained as scratch? It predates
  the FIR-BREADTH final results and should not be confused with claim evidence.
- Does the final TORS submission package include `BUILD_NOTES.md`? If yes, its
  stale compile-status section is a visible artifact-quality defect.

### Running Checklist

- [x] Locate canonical manuscript source and compiled artifacts.
- [x] Read prior cumulative audit tail and response log.
- [x] Check git status, commit history since the last run, and untracked files.
- [x] Rerun strict manuscript/artifact gate.
- [x] Verify FIR-BREADTH prereg/result commit ordering.
- [x] Verify FIR-BREADTH printed deltas against adjudication record.
- [x] Spot-check new novelty/prior-art claims against external sources.
- [x] Spot-check recent AR2023-adjacent comparator coverage.
- [x] Identify Office V3 adjudicator bug.
- [x] Detect live Office V3 run and inspect first completed seed metadata.
- [ ] Fix and smoke-test Office V3 adjudicator E1 path.
- [ ] Decide Office V3 treestate-sidecar artifact boundary.
- [ ] Update stale `paper_tex/BUILD_NOTES.md` sections.
- [ ] Inspect SILLM4Rec full paper before submission freeze.
- [ ] Re-run strict gate after any fixes.

## Audit Run - 2026-07-13 09:45 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch: `codex/bestrec-sota-results`
- HEAD: `acbe282f` (`Respond to PAPER_REVIEW_AUDIT run 05:40: breadth completed+integrated, conv prior art cited, provenance committed`)
- Tracked working tree entering this run: already dirty only because the prior
  `PAPER_REVIEW_AUDIT.md` section was uncommitted. The strict build did not add
  any further tracked dirty files.
- Current source/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/sections/*.tex`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/hygiene_scan_output.txt`, `PREREG_OFFICE_V3.md`,
  `_bestrec_run/adjudicate_office_v3.py`,
  `_bestrec_run/results_OFFICEV3_k16_seed20260728.json`,
  `_bestrec_run/results_OFFICEV3_k16_seed20260729.json`,
  `_bestrec_run/results_OFFICEV3_k16_seed20260730.json`, and their treestate /
  per-user sidecars where present.
- Live run state: `uv` + Python process still active from 2026-07-13 09:13:20,
  consistent with k16 seed 20260731 running. At inspection time there was only
  `results_OFFICEV3_k16_seed20260731.json.treestate.txt`, no completed seed
  20260731 result JSON yet.

### Verdict

**Current manuscript remains gate-green, but not submission-clean.** The
paper's own claimed results still pass the strict artifact gate: HSTU core-block
parity OK; 166 cells recomputed; 0 mismatches; 0 untraceable values; all 13
declared claim families sourced; release manifest verified 113 files; MI dual
gate PASS; legacy Office remains descriptive/VOID.

**Confirmed hard blocker for future Office V3 evidence:** the V3 adjudicator
does not merely look suspicious statically; it crashes in no-append mode on the
current results with `NameError: name 'os' is not defined` at the E1 treestate
path. Therefore any Office V3 campaign result is currently unauditable, even
though the three completed k16 seeds are numerically above the frozen gate
reference.

**No current paper overclaim detected for Office V3.** The manuscript still says
the redesigned V3 preregistration is committed with "outcome pending" and
explicitly says no V3 result is claimed in this version. That boundary is
correct while the campaign is live and the adjudicator is broken.

### Prioritized Rejection-Risk List

1. **Confirmed blocker: Office V3 adjudicator E1 path crashes at runtime.**
   Command run:
   `uv --project _bestrec_run run python _bestrec_run/adjudicate_office_v3.py --no-append`.
   It exits 1 with `NameError: name 'os' is not defined` at line 203. This is
   triggered by the actual completed V3 result manifests, all of which have
   `git_dirty_tracked=true`. Until this is fixed and smoke-tested, Office V3
   cannot be used as claim evidence.
2. **Confirmed live-campaign provenance gap: three completed k16 V3 runs are
   above the reference but all depend on the broken E1 path.** Current final
   full-catalog NDCG@10 values: seed 20260728 = 0.03060398, seed 20260729 =
   0.03052536, seed 20260730 = 0.03045678, all with n_eval 223,308 and all
   above 0.0279. All three are from commit `acbe282f` with
   `git_dirty_tracked=true`; treestate sidecars show only
   `PAPER_REVIEW_AUDIT.md` dirty, which should be E1-admissible if the tool
   worked.
3. **Confirmed artifact-boundary risk if Office V3 becomes counted later.**
   The paper currently says Office and FIR-breadth per-user sidecars are
   local-only, untracked, hash-embedded, and not part of any counted claim. That
   is fine for the current manuscript because V3 is pending. If V3 is promoted
   into a counted claim, this availability/provenance sentence and release
   manifest boundary must be updated before submission.
4. **Confirmed documentation defect: `paper_tex/BUILD_NOTES.md` remains stale.**
   The top section now says `PAPER_TORS.pdf` is 39 pages and the current hygiene
   scan agrees. Later sections still say 35 review pages / 36 preview pages and
   still state that ACM CCS concepts and keywords are not provided, even though
   `paper-shared.tex` now contains CCSXML, `\ccsdesc`, and `\keywords`. This is
   not a result defect, but it undermines artifact polish.
5. **Plausible novelty/freshness risk: SILLM4Rec remains under-inspected.**
   ACM/search metadata says it uses three 5-core Amazon Reviews 2023
   sub-datasets, and the public repository explicitly downloads AR2023 5-core
   files. The repository workflow, however, creates candidate product ranking
   tasks and preference-optimization data, not an obvious full-catalog LLOO
   benchmark. The current exclusion sentence is defensible only as a temporary
   freeze-time placeholder.

### Confirmed Fixes / Non-Problems Since The Prior Section

- No new Office V3 overclaim was introduced in the manuscript. The result remains
  "outcome pending" in the introduction, dataset table, conclusion, and TeX twin.
- The strict artifact gate still passes after the current workspace inspection.
- Seed 20260729's missing `*.final.users.jsonl.gz` file is not by itself a
  defect: its best epoch is 20, matching the final epoch, and the manifest
  records `user_records_path` with 223,308 rows and a SHA256. The adjudicator
  comment explicitly treats the best-by-val sidecar as the final sidecar when
  best epoch equals final epoch.
- The current FIR-BREADTH manuscript language remains narrow: paired internal
  filter-vs-no-filter improvements on two additional categories, no comparator
  claim, no SOTA claim.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: exact HSTU core-block parity.
  - PASS: `SUBMISSION BUILD GREEN: 166 cells recomputed from source artifacts;
    0 untraceable, 0 paper mismatches, all 13 declared claim families sourced`.
  - PASS: `RELEASE MANIFEST VERIFY: OK (113 files verified, 0 release-asset
    files not local)`.
  - PASS: MI V2 gate.
  - PASS: legacy Office adjudication remains descriptive/VOID.
- `uv --project _bestrec_run run python _bestrec_run/adjudicate_office_v3.py --no-append`
  - FAIL: `NameError: name 'os' is not defined` at the E1 sidecar lookup.
  - `--no-append` prevented creation of `OFFICE_V3_RESULTS.md`.
- `git status --short`
  - Tracked: `PAPER_REVIEW_AUDIT.md` only.
  - Untracked result/control artifacts: k16 seed 20260728, 20260729, 20260730
    result JSONs and treestate files; seed 20260731 treestate file; old
    `_bestrec_run/smoke_FIRB_IS_seed1.json`; raw category gz files for CDs and
    Industrial.
  - Ignored local per-user sidecars exist for seeds 20260728, 20260729, and
    20260730.
- Office V3 result spot-check:
  - k16 seed 20260728: final NDCG@10 0.03060398, best 0.03061777, n_eval
    223,308, final sidecar present.
  - k16 seed 20260729: final NDCG@10 0.03052536, best 0.03056013, n_eval
    223,308, best epoch 20, `user_records_path` present.
  - k16 seed 20260730: final NDCG@10 0.03045678, best 0.03050437, n_eval
    223,308, final sidecar present.
- `paper_tex/hygiene_scan_output.txt`
  - PASS: 39 pages, 0 placeholder/forbidden failures.
  - SOTA mentions are all review-list informational / negated claim wording.

### External Fact-Check / Novelty Notes

- Official Amazon Reviews'23 documentation describes the dataset as public
  AR2023 with 571.54M reviews, 48.19M items, 33 domains, rich metadata, and
  standard splits. Source: https://amazon-reviews-2023.github.io/
- The official AR2023 benchmark scripts define 5-core processing and
  leave-last-out splits where each user's latest review is test and second
  latest is validation. This supports the paper's use of the term LLOO, but
  also reinforces why timestamp-split LensKit pages are not directly comparable.
  Source: https://github.com/hyp1231/AmazonReviews2023/blob/main/benchmark_scripts/README.md
- HSTU-BLaIR's arXiv page states that its Table 2 covers Video Games, Office
  Products, Musical Instruments, and Steam, and emphasizes Office Products as a
  sparse dataset where BLaIR improves over SASRec/HSTU. Source:
  https://arxiv.org/html/2504.10545v3
- SILLM4Rec remains close enough to require freeze inspection. ACM metadata says
  the experiments use three 5-core AR2023 sub-datasets; the public repo says to
  download AR2023 5-core files and then generate image descriptions, user
  preference summaries, candidate product ranking tasks, and SFT/DPO data.
  Sources: https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec
- LensKit Codex now has Amazon 2023 5-core pages, but the site header says the
  Codex is work-in-progress and should not yet be cited or relied upon. Its
  listed AR2023 page uses absolute-timestamp 5-core benchmark files, so it is
  also not the same LLOO protocol as this paper. Source:
  https://codex.lenskit.org/amazon/2023-5core/

### Concrete Fixes To Make Next

1. Patch `_bestrec_run/adjudicate_office_v3.py`: replace the `os.path` /
   undefined `RUN_DIR` use with `HERE / f"results_OFFICEV3_k{arm}_seed{s}.json.treestate.txt"`
   or define/import the needed names; add a smoke test that exercises E1 with a
   fake dirty manifest and treestate sidecar.
2. After fixing, rerun `adjudicate_office_v3.py --no-append` on the current
   partial campaign and verify it reports missing runs rather than crashing.
3. Decide the Office V3 per-user sidecar and treestate boundary before any V3
   claim is integrated: either track/hash the needed sidecars or explicitly
   keep V3 outside counted claims.
4. Update `paper_tex/BUILD_NOTES.md` stale page-count and CCS/keyword sections.
5. Inspect the SILLM4Rec ACM PDF directly before freeze, or revise the paper to
   cite the repo-level candidate-ranking non-comparability reason instead of a
   generic "pending direct protocol inspection" statement.

### Open Questions

- Will the current k16 Office V3 run finish all five seeds before the next audit,
  and will the k8 arm start under the same dirty-tree pattern?
- Should the running automation dirtying `PAPER_REVIEW_AUDIT.md` be paused during
  confirmatory campaigns, or is E1 the intended permanent solution?
- Should ignored Office V3 user sidecars be promoted to tracked/release evidence
  if V3 becomes a counted claim?
- Is `BUILD_NOTES.md` included in the final TORS/deposit artifact package? If
  yes, the stale sections are visible submission defects.

### Running Checklist

- [x] Read automation memory and prior audit tail.
- [x] Locate canonical manuscript source, TeX twin, PDFs, result files, and
      preregistration files.
- [x] Rerun strict manuscript/artifact gate.
- [x] Confirm Office V3 adjudicator failure dynamically.
- [x] Inspect current Office V3 result JSONs and treestate sidecars.
- [x] Verify current paper does not claim Office V3 results.
- [x] Re-check TeX hygiene scan and stale build notes.
- [x] Spot-check SILLM4Rec, LensKit Codex, AR2023 docs, and HSTU-BLaIR sources.
- [ ] Fix and smoke-test Office V3 adjudicator E1 path.
- [ ] Re-adjudicate Office V3 partial campaign after the fix.
- [ ] Decide Office V3 evidence/sidecar release boundary.
- [ ] Update stale `paper_tex/BUILD_NOTES.md`.
- [ ] Inspect SILLM4Rec full paper before submission freeze.

## Audit Run - 2026-07-13 10:43 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch: `codex/bestrec-sota-results`
- HEAD: `acbe282f` (`Respond to PAPER_REVIEW_AUDIT run 05:40: breadth completed+integrated, conv prior art cited, provenance committed`)
- Tracked working tree entering this run: already dirty only because
  `PAPER_REVIEW_AUDIT.md` contains uncommitted prior audit sections. The strict
  rebuild did not leave `_bestrec_run/hstu_tables.json` dirty.
- Current manuscript/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/sections/*.tex`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `PREREG_OFFICE_V3.md`, `_bestrec_run/adjudicate_office_v3.py`, and current
  `_bestrec_run/results_OFFICEV3_k16_seed20260728..31.json` result/treestate
  artifacts.
- Live run state: `uv` + Python processes from 2026-07-13 10:06:28 remain
  active. `results_OFFICEV3_k16_seed20260732.json.treestate.txt` exists, but
  `results_OFFICEV3_k16_seed20260732.json` does not yet exist. No k8 V3 result
  files are present.

### Verdict

**Current manuscript claims still pass the artifact gate, but Office V3 remains
unusable as evidence.** The strict rebuild passed in this run: HSTU core-block
parity OK; 166 empirical cells recomputed; 0 mismatches; 0 untraceable values;
all 13 declared claim families sourced; release manifest verified 113 files; MI
dual gate PASS; legacy Office remains descriptive/VOID.

**New since the 09:45 audit:** k16 seed 20260731 completed. Four k16 V3 seeds
are now numerically above the frozen 0.0279 environment-matched reference, but
the campaign still has fewer than 5 valid k16 runs, no k8 runs, and a crashing
adjudicator. Under `PREREG_OFFICE_V3.md`, any arm with fewer than 5 valid runs
is not claimable, and the full second-category confirmation requires both k16
and k8 arms to pass.

**No current paper overclaim detected.** The manuscript still frames Office V3
as outcome-pending and keeps Office outside counted claims. That boundary is
correct and must not be relaxed until the adjudicator is fixed, seed 20260732
and the k8 arm complete, and the release/sidecar boundary is decided.

### Prioritized Rejection-Risk List

1. **Confirmed blocker: Office V3 adjudicator still crashes dynamically.**
   `uv --project _bestrec_run run python _bestrec_run/adjudicate_office_v3.py --no-append`
   exits 1 with `NameError: name 'os' is not defined` at line 203, in the E1
   treestate-sidecar path. The source imports `argparse` at line 35 but does not
   import `os`, and the path expression also relies on undefined `RUN_DIR`.
   Until this is fixed and smoke-tested, V3 evidence is not auditable.
2. **Confirmed incomplete campaign: k16 has 4/5 completed seeds and k8 has 0/5.**
   Final-epoch full-catalog NDCG@10 values for completed k16 runs:
   20260728 = 0.03060398, 20260729 = 0.03052536, 20260730 = 0.03045678,
   20260731 = 0.03032775. Four-seed descriptive mean = 0.03047847, sd =
   0.00011710, t-approx CI lower bound = 0.03029214. This is numerically
   encouraging, but it is still not the preregistered 5-seed arm test.
3. **Confirmed provenance/availability boundary risk if V3 is promoted later.**
   All four completed k16 result JSONs show `git_dirty_tracked=true` at commit
   `acbe282f`; treestate sidecars show only `PAPER_REVIEW_AUDIT.md` dirty,
   which should be E1-admissible after the tool fix. The current paper says
   Office/FIR-breadth per-user sidecars are local-only and not part of counted
   claims. If V3 becomes counted, that sentence and the release manifest must be
   updated or reviewers will see an evidence-boundary mismatch.
4. **Confirmed documentation defect: `paper_tex/BUILD_NOTES.md` remains stale.**
   Current `hygiene_scan_output.txt` says `PAPER_TORS.pdf` has 39 pages.
   `pypdf` confirms `PAPER_TORS.pdf` has 39 letter pages and
   `PAPER_TORS_acmsmall.pdf` has 41 pages, while later `BUILD_NOTES.md`
   sections still say 35 review pages / 36 preview pages and still claim CCS
   concepts/keywords are absent despite `paper-shared.tex` containing CCSXML
   and `\keywords`.
5. **Plausible freshness/novelty risk requiring author verification:
   SILLM4Rec remains under-inspected.** ACM/search metadata and the public repo
   establish AR2023 5-core relevance; the repo workflow appears to build
   candidate-ranking and SFT/DPO data rather than full-catalog LLOO. The current
   paper can keep it out of comparable-results claims only if this
   non-comparability is made explicit or the full ACM PDF is inspected before
   freeze.

### Confirmed Fixes / Non-Problems Since The Prior Section

- Seed 20260731 now exists as a completed k16 V3 JSON with n_eval 223,308,
  commit `acbe282f`, `git_dirty_tracked=true`, `best_test_epoch=20`, and
  final-epoch NDCG@10 0.03032775.
- Seed 20260732 is still running or incomplete: only its 54-byte pre-run
  treestate marker exists.
- The strict gate did not create any new tracked diff outside this audit file.
- PDF rendering with the bundled Poppler wrappers could not be performed in
  this Windows run because both `pdfinfo.cmd` and `pdftoppm.cmd` fail with "The
  system cannot find the path specified." Text/page geometry checks were
  performed with `pypdf`, and the manuscript hygiene scan remains PASS.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: exact HSTU core-block parity.
  - PASS: `SUBMISSION BUILD GREEN: 166 cells recomputed from source artifacts;
    0 untraceable, 0 paper mismatches, all 13 declared claim families sourced`.
  - PASS: `RELEASE MANIFEST VERIFY: OK (113 files verified, 0 release-asset
    files not local)`.
  - PASS: MI V2 gate.
  - PASS: legacy Office adjudication remains descriptive/VOID.
- `uv --project _bestrec_run run python _bestrec_run/adjudicate_office_v3.py --no-append`
  - FAIL: `NameError: name 'os' is not defined` at line 203.
  - `--no-append` prevented creation of `OFFICE_V3_RESULTS.md`.
- Office V3 k16 result extraction:
  - seed 20260728: final 0.03060398, best 0.03060573, n_eval 223,308.
  - seed 20260729: final 0.03052536, best 0.03052536, n_eval 223,308.
  - seed 20260730: final 0.03045678, best 0.03047156, n_eval 223,308.
  - seed 20260731: final 0.03032775, best 0.03032775, n_eval 223,308.
- `git status --short`
  - Tracked: `PAPER_REVIEW_AUDIT.md`.
  - Untracked: k16 V3 result/treestate files for seeds 20260728..31,
    seed 20260732 treestate only, `_bestrec_run/smoke_FIRB_IS_seed1.json`, and
    raw `data_raw_proper` category gz files.
- PDF checks:
  - `pypdf`: `paper_tex/PAPER_TORS.pdf` = 39 pages, 612 x 792 pt.
  - `pypdf`: `paper_tex/PAPER_TORS_acmsmall.pdf` = 41 pages, 486 x 720 pt.
  - `pypdf`: `PAPER_SUBMISSION.pdf` = 44 pages, 612 x 792 pt.
  - `pdftoppm.cmd`: failed before rendering, so no PNG visual inspection was
    completed this run.

### External Fact-Check / Novelty Notes

- Official AR2023 5-core documentation defines leave-last-out splitting as
  first N-2 interactions for training, N-1 for validation, and N for testing,
  while separately documenting absolute-timestamp splitting. This supports the
  paper's LLOO terminology and its caution against comparing to timestamp-split
  pages. Source: https://amazon-reviews-2023.github.io/data_processing/5core.html
- HSTU-BLaIR reports the same AR2023 benchmark family and key comparator
  numbers: Video Games HSTU-BLaIR NDCG@10 0.0760, Office Products 0.0271, and
  Musical Instruments 0.0406; it also lists Office Products as 77,551 items,
  223,308 users, and 1,800,877 interactions. Source:
  https://arxiv.org/html/2504.10545v3
- The HSTU-BLaIR public repo says results should reproduce "within a small
  margin of variability" and documents the released configs/hardware context.
  This supports treating local comparator regenerations as informative but
  environment-caveated. Source: https://github.com/snapfinger/HSTU-BLaIR
- LensKit Codex's AR2023 5-core page uses UCSD absolute-timestamp benchmark
  files, not this paper's LLOO protocol. It remains a watch item, not an
  apples-to-apples comparator. Source: https://codex.lenskit.org/amazon/2023-5core/
- SILLM4Rec's public repo says to download AR2023 5-core files, then generate
  image descriptions, user preference summaries, candidate product ranking
  tasks, and SFT/DPO data. That is close enough for a related-work check but
  not yet evidence of full-catalog LLOO comparability. Source:
  https://github.com/MKC-Lab/SILLM4Rec

### Concrete Fixes To Make Next

1. Fix `_bestrec_run/adjudicate_office_v3.py` E1 path (`os` import or `Path`
   rewrite; remove/define `RUN_DIR`), then run `--no-append` and confirm it
   reports missing/partial campaign status instead of crashing.
2. Let k16 seed 20260732 finish, then run the fixed V3 adjudicator before
   starting or trusting any k8 evidence.
3. Decide whether V3 per-user and treestate sidecars become tracked/release
   evidence if V3 is integrated into the paper.
4. Clean `paper_tex/BUILD_NOTES.md`: update 39/41-page counts and remove the
   stale CCS/keyword warning.
5. Inspect the SILLM4Rec ACM PDF or revise related work to state the observed
   candidate-ranking/SFT-DPO non-comparability from the public repo.

### Open Questions

- Is the active 10:06 process seed 20260732 still healthy, and will it emit a
  result JSON before the next audit?
- Should hourly audit writes be exempted permanently via E1, or should
  confirmatory campaigns run with the audit paused to keep manifests clean?
- Are `data_raw_proper/*/*.csv.gz` intended release assets, ignored local raw
  caches, or accidental untracked files?
- Is `BUILD_NOTES.md` included in the final artifact package? If yes, the stale
  page-count/CCS sections are visible submission defects.

### Running Checklist

- [x] Read automation memory.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, and audit
      artifacts.
- [x] Rerun strict manuscript/artifact gate.
- [x] Confirm Office V3 adjudicator failure dynamically.
- [x] Inspect completed Office V3 k16 seeds 20260728..31.
- [x] Confirm seed 20260732 is still incomplete and k8 has not started.
- [x] Verify current paper still keeps Office V3 outcome-pending.
- [x] Check PDF page counts and note Poppler wrapper failure.
- [x] Spot-check AR2023, HSTU-BLaIR, LensKit Codex, and SILLM4Rec sources.
- [ ] Fix and smoke-test Office V3 adjudicator E1 path.
- [ ] Re-adjudicate V3 partial campaign after the fix.
- [ ] Decide V3 sidecar/release boundary.
- [ ] Update stale `paper_tex/BUILD_NOTES.md`.
- [ ] Inspect SILLM4Rec full paper before submission freeze.

## Audit Run - 2026-07-13 14:52 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `a437f14c` (`Regenerate
  RELEASE_MANIFEST at the Office V3 boundary`).
- HEAD parent: `045d6a6f`; `RELEASE_MANIFEST.json` says its own commit is the
  immediate child of the state it describes, so the parent-pointer pattern is
  intentional rather than automatically defective.
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/main.tex`, `paper_tex/paper-shared.tex`,
  `paper_tex/sections/*.tex`, `paper_tex/tables/TABLES_PROVENANCE.json`,
  `paper_tex/BUILD_NOTES.md`, `paper_tex/hygiene_scan_output.txt`,
  `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`, `RELEASE_MANIFEST.json`,
  `_bestrec_run/hstu_results_manifest.json`, `_bestrec_run/hstu_tables.json`,
  Office V3 result JSONs/treestate sidecars, and the existing cumulative audit.
- Working tree before this audit edit had only untracked
  `_bestrec_run/impact_program.DONE`, `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  and two raw `data_raw_proper/*/*.csv.gz` files. After this audit,
  `PAPER_REVIEW_AUDIT.md` is modified by this audit. No manuscript, TeX,
  result, preregistration, or source-code file was edited by this audit.

### Verdict

**The evidence layer has improved materially, but the manuscript is not
submission-ready because the prose did not converge after Office V3 passed.**
The Office V3 campaign is now mechanically adjudicated as PASS, and the strict
artifact gate is green. The top rejection risk is no longer "Office V3 is
unusable"; it is "the paper simultaneously says Office V3 passed, is pending,
and counts in no claim."

A reviewer would likely trust the artifact gate more than in prior rounds, but
would also view the inconsistent Office wording as a serious control failure in
a paper whose lead contribution is evaluation governance.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/adjudicate_office_v3.py --no-append`
  - PASS: both arms pass the frozen V3 gate.
  - K=16: seed finals `0.03060`, `0.03053`, `0.03046`, `0.03033`, `0.03041`;
    mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, 5/5 above `0.0279`
    and `0.0271`.
  - K=8: seed finals `0.03025`, `0.03037`, `0.03030`, `0.03030`, `0.03026`;
    mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, 5/5 above `0.0279`
    and `0.0271`.
  - Comparability conditions OK: dataset identity within the declared +/-1
    interaction tolerance; reference artifacts hash-match; E1 audit-log
    dirty-tree exemption accepted from treestate sidecars; embedded code/data
    hashes identical across all 10 runs.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release manifest verification OK for `113` files.
  - PASS: MI V2 gate; legacy Office V1 adjudication remains descriptive/VOID.
- `rg "outcome pending|no claim counts Office|not part of any counted claim|Office never a passed category|35 pages|36 pages|40 pages"`
  - Finds stale pending/no-claim wording in `PAPER_SUBMISSION.md`,
    `paper_tex/sections/01-introduction.tex`, `02-related.tex`,
    `07-conclusion.tex`, `08-availability.tex`, and `06-discussion.tex`.
  - Finds stale build-note page counts and the old "Office never a passed
    category" hygiene summary in `paper_tex/BUILD_NOTES.md`.
- `pypdf` page-count check:
  - `paper_tex/PAPER_TORS.pdf`: 40 pages, 612 x 792 pt.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 40 pages, 486 x 720 pt.
  - `PAPER_SUBMISSION.pdf`: 45 pages, 612 x 792 pt.
- `paper_tex/hygiene_scan_output.txt`
  - PASS: 40 pages, 0 placeholder/forbidden failures, 18 informational
    SOTA/negated-claim review hits.
- `git ls-files "_bestrec_run/results_OFFICEV3_*" "OFFICE_V3_RESULTS.md" "PREREG_OFFICE_V3.md"`
  - Confirms the V3 result JSONs, treestate files, preregistration, and result
    file are tracked.
- `git ls-files "_bestrec_run/results_OFFICEV3_*users.jsonl.gz"`
  - Confirms Office V3 per-user sidecars are not tracked.

### Confirmed Problems

1. **Office V3 status contradiction is now the leading rejection risk.**
   Current state:
   - PASS/counting wording: abstract, `PAPER_SUBMISSION.md` dataset table row,
     Section 5.2 V3 paragraph, and Section 6.4 category-scope bullet.
   - Stale pending wording: introduction, related-work evaluation-practice
     paragraph, and conclusion still say the redesigned Office pre-registration
     is committed with "outcome pending at the time of writing."
   - Stale no-claim wording: Section 6.5 still says the Office second-category
     pass is VOID and "no claim counts Office," which now contradicts the V3
     pass paragraph.
2. **Availability is stale for a counted V3 claim.** Section 8 says "Office
   descriptive summary JSONs are manifest-backed" and that Office per-user
   sidecars are local-only and "not part of any counted claim." That was correct
   for Office V1, but not for a manuscript that now counts Office V3 as the
   second pre-registered per-category point-estimate comparison. At minimum,
   distinguish tracked V3 JSON/treestate evidence from local-only per-user
   sidecars and state whether sidecars are required for claim recomputation.
3. **The abstract misstates the comparator execution boundary.** It says the
   comparator's "reference implementation cannot execute on our hardware," while
   Section 5.6 says the unmodified reference implementation's research path does
   execute locally under shims. The safe wording is that the pinned official
   CUDA/Triton environment cannot execute locally; the unpinned shimmed research
   path can, as environment-caveated single-run regeneration.
4. **`paper_tex/BUILD_NOTES.md` is visibly stale despite a current top sync
   block.** It now opens with 40/40 page counts, but later still says 35/36
   pages, still lists absent CCS/keywords as an accepted warning despite
   `paper-shared.tex` containing CCSXML and keywords, and still embeds an old
   hygiene block ending with "Office never a passed category." This is not a
   result defect, but it weakens submission polish and artifact credibility.
5. **The generated strict-build table family still exposes a legacy Office V1
   table named `office_confirmation`.** This is acceptable if clearly labeled as
   Appendix A.0 V1 VOID evidence, but it increases confusion now that `office_v3`
   is also a counted family. Ensure prose never lets `office_confirmation` imply
   the current Office V3 result is void.

### Confirmed Fixes / Non-Problems Since The Prior Section

- The Office V3 adjudicator E1 path no longer crashes. The prior `NameError:
  os is not defined` / undefined `RUN_DIR` blocker is gone in the current
  workspace.
- All five K=16 and all five K=8 Office V3 seeds exist and adjudicate under the
  frozen final-epoch full-catalog rule.
- The strict rebuild includes `office_v3` in `required_families`, sources both
  V3 cells from tracked JSONs, and reports no paper mismatches.
- The causal-convolution prior-art boundary is improved: the current related
  work now cites Caser and NextItNet and explicitly narrows the FIR claim to a
  depthwise, linear, zero-init FIR tap bank rather than convolutional sequence
  encoding.
- The compiled TORS hygiene scan is current and clean; the stale hygiene block
  is confined to `BUILD_NOTES.md`.

### Plausible Risks Requiring Author Verification

- Decide whether Office V3 per-user sidecars must be shipped/tracked now that
  V3 is counted. If they are not needed to recompute printed table cells, say
  that; if they are part of auditability, include them in the release boundary
  or an external artifact bundle.
- Decide whether `RELEASE_MANIFEST.json` should name Office V3 result families
  directly, or whether the tracked `hstu_results_manifest.json` plus strict gate
  is the intended evidence layer. The current release manifest verifies, but it
  does not list `OFFICEV3` under `result_families`.
- Decide whether the conclusion should count both MI and Office as
  pre-registered point-estimate comparisons, while keeping Office V1 VOID as a
  separate demonstration of self-voiding governance.
- Confirm that no prose outside `PAPER_SUBMISSION.md` and `paper_tex/sections`
  is used as a submission/deposit artifact with old "Office pending" or "Office
  never passed" wording.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR's arXiv PDF reports AR2023 5-core statistics matching the paper's
  comparator family: Video Games `25,612` items / `94,762` users / `814,585`
  interactions; Office Products `77,551` / `223,308` / `1,800,877`; Musical
  Instruments `24,587` / `57,439` / `511,835`. It reports NDCG@10 `0.0760`
  for Video Games HSTU-BLaIR, `0.0271` for Office HSTU-BLaIR, and `0.0406` for
  Musical Instruments HSTU-BLaIR. Source: https://arxiv.org/pdf/2504.10545
- The official AR2023 site describes the dataset as collected in 2023, with
  `571.54M` reviews, `48.19M` items, 33 domains, and standard splits. This
  supports the paper's AR2023 framing but not any cross-protocol comparison by
  itself. Source: https://amazon-reviews-2023.github.io/
- SID-MLP evaluates on AR2023 Musical Instruments, Industrial & Scientific, and
  Video Games, and its appendix statistics for MI/VG match the HSTU-BLaIR-family
  counts up to the known +/-1 interaction issue. Source:
  https://arxiv.org/html/2605.12617v1
- Latte reports RQ-KMeans NDCG@10 values of `0.0331` on Instruments and `0.0515`
  on Games in its NDCG table, supporting the paper's statement that these
  concurrent preprint point estimates do not alter the HSTU-BLaIR comparator
  choice. Source: https://arxiv.org/pdf/2605.06331
- ChronoSID uses a different SID-line filtered universe (`57,359` MI users,
  `23,742` MI items, `490,522` MI interactions; `94,515` VG users, `24,685` VG
  items, `772,218` VG interactions) and reports MI output-level N@10 `0.0345`
  vs ReSID `0.0325`. This supports the paper's non-interchangeability caveat.
  Source: https://arxiv.org/pdf/2607.03918
- LensKit Codex's AR2023 5-core page explicitly says the codex is a
  work-in-progress and should not yet be cited or relied upon, and it uses
  absolute-timestamp 5-core benchmark files. It remains a watch item, not an
  apples-to-apples comparator. Source: https://codex.lenskit.org/amazon/2023-5core/
- SILLM4Rec remains a close related-work risk: ACM metadata says its experiments
  use three 5-core AR2023 sub-datasets, and the public repo instructs users to
  download AR2023 5-core files before creating image descriptions, user
  preference summaries, candidate product ranking tasks, and SFT/DPO data.
  Sources: https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec

### Concrete Fixes To Make Next

1. Replace every stale Office V3 pending/no-claim sentence with a consistent
   two-track statement:
   - Office V1 remains VOID under its original floor-check preregistration.
   - Office V3 passed under a separate environment-matched pre-registration and
     is counted only as a per-category point-estimate comparison, not paired
     superiority or SOTA.
2. Update Section 8 availability for V3:
   - tracked: `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`, V3 JSONs,
     treestate sidecars, `hstu_results_manifest.json`;
   - local-only: per-user `*.users.jsonl.gz` and `*.final.users.jsonl.gz`
     sidecars, hash-embedded in run manifests;
   - explicitly state whether local-only sidecars are outside printed-cell
     recomputation or are available through a release artifact.
3. Repair the abstract comparator sentence to "the pinned official environment
   cannot execute on our hardware; the reference research path runs locally only
   as an unpinned, shimmed, environment-caveated single-run regeneration."
4. Refresh `paper_tex/BUILD_NOTES.md`: remove old 35/36 page-count sections,
   remove stale CCS/keyword warning, replace the old hygiene block with the
   current 40-page / 18-review-hit PASS block, and delete "Office never a passed
   category."
5. Inspect the SILLM4Rec ACM PDF directly before freeze, or revise the related
   work sentence to cite the public repo's candidate-ranking/SFT-DPO workflow as
   the concrete non-comparability reason.
6. Optionally rename or annotate the generated `office_confirmation` table
   family in prose as "legacy Office V1 VOID table" wherever it appears, so it
   cannot be confused with the counted V3 result.

### Open Questions

- Are Office V3 per-user sidecars intended to remain local-only, or should they
  be deposited as an external artifact now that V3 is counted?
- Should `RELEASE_MANIFEST.json` list Office V3 result JSONs directly, or is the
  strict `hstu_results_manifest.json` evidence layer the intended source of
  truth for counted result families?
- Is `PAPER_SUBMISSION.pdf` still a current deliverable, given it is 45 pages
  while the TORS artifact is 40 pages?
- Is the SILLM4Rec ACM PDF accessible through institutional access, or should
  the authors avoid the "excluded pending direct protocol inspection" phrasing
  and state only the public repo-level non-comparability?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Re-run Office V3 adjudicator dynamically.
- [x] Re-run strict manuscript/artifact gate.
- [x] Check tracked/untracked status of Office V3 JSONs, treestate files, and
      per-user sidecars.
- [x] Search manuscript and TeX for stale Office V3 pending/no-claim wording.
- [x] Check compiled PDF page counts and hygiene output.
- [x] Fact-check current related-literature claims against HSTU-BLaIR, AR2023,
      SID-MLP, Latte, ChronoSID, LensKit Codex, and SILLM4Rec sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Make Office V3 status consistent in abstract/introduction/related work/
      results/discussion/conclusion/availability.
- [ ] Decide and document the Office V3 sidecar/release boundary.
- [ ] Refresh stale `paper_tex/BUILD_NOTES.md`.
- [ ] Inspect SILLM4Rec full paper or soften/restate the exclusion rationale.

### Post-Audit Addendum - 2026-07-13 17:57 Australia/Sydney

Additional manuscript/source edits landed while this audit was being verified.
They partially address the findings above, but they also introduce a new strict
release-gate failure.

Confirmed updates after the section above was written:

- `PREREG_OFFICE_V3.md` now has Erratum E2 explaining the three missing
  `user_records_final_path` cases: when best-by-validation and final epoch
  coincide, the regular `*.users.jsonl.gz` sidecar is the final-epoch per-user
  record.
- `OFFICE_V3_RESULTS.md` now has a per-run sidecar inventory for all ten Office
  V3 runs.
- `PAPER_SUBMISSION.md` now fixes several stale Office V3 pending statements,
  repairs the pinned-environment vs shimmed-research-path comparator wording in
  the abstract/result paragraph, revises Section 8 to identify tracked V3
  aggregate JSONs/treestate sidecars, and gives a concrete SILLM4Rec
  non-comparability reason from the public repo workflow.
- `paper_tex/BUILD_NOTES.md` now marks the CCS/keyword warning resolved and
  updates the Office V1/V3 hygiene wording, but still carries old 35/36-page
  historical compile-status text.

Current residual blockers after those edits:

1. `rebuild_hstu_submission.py --strict` now **fails** at release-manifest
   verification: `PAPER_SUBMISSION.md`, `PAPER_SUBMISSION.pdf`, and
   `PAPER_DRAFT.md` have hash mismatches against `RELEASE_MANIFEST.json` and
   are dirty manifested files. The table/artifact graph itself remains green
   (`168` cells, `0` mismatches, `0` untraceable, all `14` claim families
   sourced). Next required action: regenerate the release manifest for the
   changed package and commit it with the changed manuscript/PDF files.
2. `PAPER_SUBMISSION.md` still has a Section 6.5 Office limitation sentence
   saying the Office second-category pass is VOID and "no claim counts Office";
   this now conflicts with Office V3 being counted in Section 5.2/6.4.
3. The TeX derivative is now mostly synced relative to the canonical markdown.
   The remaining stale TeX prose found by search is the Office "no claim counts
   Office" limitation sentence in `paper_tex/sections/06-discussion.tex`.
4. Fresh `adjudicate_office_v3.py --no-append` at 17:57 still PASSes with the
   same K=16/K=8 CI lower bounds and comparability checks.

Updated checklist:

- [x] Re-run Office V3 adjudicator after the post-audit edits.
- [x] Re-run strict submission rebuild after the post-audit edits.
- [x] Record new release-manifest failure.
- [ ] Regenerate `RELEASE_MANIFEST.json` for the modified manuscript/PDF package.
- [ ] Regenerate/sync TeX from `PAPER_SUBMISSION.md` and rebuild the TORS PDFs.
- [ ] Repair remaining Section 6.5 Office V1/V3 wording in the canonical
      markdown.

## Audit Run - 2026-07-13 17:50 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `a437f14c` (`Regenerate
  RELEASE_MANIFEST at the Office V3 boundary`).
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/main.tex`, `paper_tex/paper-shared.tex`,
  `paper_tex/sections/*`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/hygiene_scan_output.txt`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/references.bib`,
  `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
  `RELEASE_MANIFEST.json`, `_bestrec_run/hstu_results_manifest.json`,
  `_bestrec_run/hstu_tables.json`, and Office V3 result JSON/sidecar files.
- Working tree state observed: `PAPER_REVIEW_AUDIT.md` already modified;
  untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`. This audit
  edited only `PAPER_REVIEW_AUDIT.md`.

### Verdict

**No new numerical gate failure was found, but the same reject-level prose and
release-boundary blockers remain.** Office V3 still passes a fresh no-append
adjudication, and the strict artifact rebuild still recomputes every printed
cell. The paper is not yet submission-clean because the manuscript still says
Office V3 is pending/non-counted in several places while Section 5.2 and
Section 6.4 count it.

The sharpest reviewer-facing problem is now governance, not performance:
counted Office V3 aggregate evidence is tracked and gate-green, but the release
text still says Office sidecars are local-only and not part of counted claims.
That is survivable only if the paper explicitly defines which artifacts support
the counted aggregate cells and what per-user sidecars are, or are not, part of
the public reproducibility boundary.

### Commands And Evidence Checked

- `rg "outcome pending|no claim counts Office|not part of any counted claim|Office never a passed category|35 pages|36 pages|CCS|keyword|SILLM4Rec|cannot execute|reference implementation" ...`
  - Still finds stale Office V3 pending/no-claim wording in
    `PAPER_SUBMISSION.md`, `paper_tex/sections/01-introduction.tex`,
    `02-related.tex`, `06-discussion.tex`, `07-conclusion.tex`, and
    `08-availability.tex`.
  - Still finds stale 35/36 page counts, a stale CCS/keyword warning, and the
    old "Office never a passed category" hygiene summary in
    `paper_tex/BUILD_NOTES.md`.
- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-13 17:50 Australia/Sydney`.
  - K=16: seed finals `0.03060`, `0.03053`, `0.03046`, `0.03033`, `0.03041`;
    mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds above
    both `0.0279` and `0.0271`.
  - K=8: seed finals `0.03025`, `0.03037`, `0.03030`, `0.03030`, `0.03026`;
    mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds above
    both `0.0279` and `0.0271`.
  - Comparability conditions OK: dataset identity within the declared +/-1
    interaction tolerance; reference artifacts hash-match; E1 dirty-tree
    exemption accepted through treestate sidecars; embedded code/data hashes
    identical across all 10 runs.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` `MISMATCH`; `0` `UNTRACEABLE`; all `14`
    declared claim families sourced.
  - PASS: release manifest verification OK for `113` files.
  - PASS: MI V2 gate; legacy Office V1 remains descriptive/VOID.
- `git ls-files PREREG_OFFICE_V3.md OFFICE_V3_RESULTS.md RELEASE_MANIFEST.json _bestrec_run/hstu_results_manifest.json _bestrec_run/hstu_tables.json _bestrec_run/results_OFFICEV3_*`
  - Tracks `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`, all 10 Office V3
    aggregate JSONs, all 10 treestate sidecars, and both strict-build manifests.
  - Does not track Office V3 per-user `*.users.jsonl.gz` sidecars.
- Office V3 sidecar parse:
  - Local Office V3 sidecar archives matching `results_OFFICEV3_*users*.jsonl.gz`:
    `17` files, total `80,688,616` bytes.
  - All 10 JSONs have `provenance.user_records_path` and existing regular
    sidecars.
  - `results_OFFICEV3_k16_seed20260729.json`,
    `results_OFFICEV3_k16_seed20260731.json`, and
    `results_OFFICEV3_k8_seed20260731.json` have no
    `provenance.user_records_final_path`.
  - All 10 runs have 20 history entries and final epoch 20; for the three null
    final-sidecar fields, the regular sidecar may therefore be the final-epoch
    sidecar, but this is author-verification territory because
    `PREREG_OFFICE_V3.md` promised explicit `*.final.users.jsonl.gz` sidecars.
- Fresh page/hygiene checks:
  - `paper_tex/PAPER_TORS.pdf`: 40 pages.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 40 pages.
  - `PAPER_SUBMISSION.pdf`: 45 pages.
  - `paper_tex/hygiene_scan_output.txt`: PASS, 40 pages, 0 placeholder/
    forbidden-claim failures, 18 informational SOTA/negated-claim review hits.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR v3 supports the comparator constants used in the paper: AR2023
  5-core statistics match Video Games, Office Products, and Musical Instruments,
  and Table 2 reports HSTU-BLaIR NDCG@10 `0.0760`, `0.0271`, and `0.0406`.
  Source: https://arxiv.org/html/2504.10545v3
- The official Amazon Reviews 2023 site supports the dataset framing: a 2023
  McAuley Lab release with reviews, metadata, links, standard splits, 571.54M
  reviews, 54.51M users, and 48.19M items. Source:
  https://amazon-reviews-2023.github.io/
- The causal FIR novelty boundary is now appropriately narrow if kept as written:
  FMLP-Rec introduces learnable frequency filters for sequential recommendation;
  BSARec uses Fourier transform to add an inductive bias; Caser and NextItNet
  establish older convolutional sequence modeling prior art. Sources:
  https://arxiv.org/abs/2202.13556,
  https://arxiv.org/html/2312.10325v1,
  https://arxiv.org/abs/1809.07426,
  https://arxiv.org/abs/1808.05163
- Recent AR2023-adjacent checks mostly support the paper's cautious
  non-comparison posture. SID-MLP reports AR2023 5-core LLOO with the same
  MI/VG-family statistics; Latte reports the same dataset statistics in its
  appendix; GrIT reports Video Games `94,762` users / `25,612` items /
  `814,586` interactions and full-item-set ranking with GrIT NDCG@10 `0.0588`;
  ChronoSID reports a SID/generative pipeline and output-level MI NDCG@10
  `0.0345`, which is not a direct HSTU-BLaIR-family comparator. Sources:
  https://arxiv.org/html/2605.12617v1,
  https://arxiv.org/html/2605.06331,
  https://arxiv.org/html/2602.19728,
  https://arxiv.org/html/2607.03918v1
- SILLM4Rec remains the most under-inspected recent-work item. ACM metadata says
  its experiments use three AR2023 5-core sub-datasets and report NDCG@1/5/10,
  but the public GitHub workflow documents image-to-text conversion, user
  preference summaries, candidate product ranking tasks, and SFT/DPO training
  data. That is a concrete non-comparability signal, but the current manuscript
  sentence is still too vague unless the ACM PDF is directly inspected. Sources:
  https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec

### Confirmed Problems

1. **Office V3 prose is contradictory.** Section 5.2 and Section 6.4 count V3;
   the introduction, related-work reproducibility paragraph, conclusion, Section
   6.5, and availability text still describe the redesigned Office campaign as
   pending/non-counted or say no Office claim counts.
2. **Section 8 is stale for a counted claim.** It says Office sidecars are
   local-only and not part of any counted claim. This is no longer accurate for
   the printed Office V3 aggregate claim-family cells, even if the per-user
   sidecars remain outside the public release.
3. **Office V3 sidecar metadata needs an erratum or release-boundary note.**
   Three V3 JSONs lack explicit final-sidecar paths despite the pre-registration
   promising final sidecars. The aggregate gate passes, but a reviewer could
   reasonably ask why the promised final per-user artifacts are missing.
4. **The abstract/reference-execution distinction remains over-compressed.**
   The paper must distinguish "pinned official environment cannot execute" from
   "shimmed unpinned research path executes locally."
5. **`paper_tex/BUILD_NOTES.md` remains stale.** It still embeds old page counts,
   old warnings, and the old Office non-pass hygiene summary.
6. **SILLM4Rec exclusion is still under-supported.** The exclusion may be
   defensible, but the sentence should cite a concrete reason or be softened
   until the full paper is inspected.

### Confirmed Non-Problems

- Office V3 aggregate adjudication is still green on a fresh run.
- The strict manuscript/artifact graph still passes and sources all 14 claim
  families.
- The HSTU-BLaIR comparator constants are externally supported by the cited
  arXiv v3 paper.
- The current compiled TORS hygiene scan is PASS; the stale hygiene text is in
  `BUILD_NOTES.md`, not the current hygiene output.
- The causal FIR novelty boundary now cites enough prior art to survive if the
  authors keep the claim incremental and do not broaden it.

### Concrete Fixes To Make Next

1. Make every Office sentence use the same two-track wording:
   - V1: VOID under the original floor-check pre-registration; descriptive only.
   - V3: passed under the separate environment-matched pre-registration; counts
     only as a per-category point-estimate comparison, not paired superiority,
     not SOTA.
2. Repair Section 8 and release docs:
   - tracked: `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`, V3 aggregate
     JSONs, treestate sidecars, `hstu_results_manifest.json`, and
     `hstu_tables.json`;
   - local-only: Office V3 per-user sidecars, hash-embedded in result JSONs;
   - explicit public recomputation boundary for the counted Office V3 aggregate
     cells.
3. Add an Office V3 sidecar erratum/manifest. For the three null
   `user_records_final_path` cases, state whether `user_records_path` is the
   final-epoch sidecar because the run ended at epoch 20, or generate/deposit
   explicit final sidecars.
4. Repair the abstract comparator sentence so it says the pinned official
   CUDA/Triton environment cannot execute locally, while the unpinned shimmed
   research path can execute only as an environment-caveated regeneration.
5. Refresh `paper_tex/BUILD_NOTES.md` to match current build output: 40/40 page
   TORS PDFs, 45-page `PAPER_SUBMISSION.pdf`, current 18-hit hygiene scan, and
   no stale CCS/keyword warning if metadata now exists.
6. Replace the SILLM4Rec sentence with a concrete, cited non-comparability
   reason or inspect the ACM PDF before final submission.

### Open Questions

- Are Office V3 per-user sidecars intended for public deposit now that V3 is
  counted, or are aggregate JSONs the declared public evidence boundary?
- For the three Office V3 result JSONs with no final-sidecar path, is the
  regular sidecar explicitly the final-epoch sidecar because training ended at
  epoch 20?
- Should the release manifest list Office V3 result files directly, or is
  `hstu_results_manifest.json` the intended public source of truth for those
  claim-family rows?
- Should the generated `office_confirmation` table remain V1-only in Appendix
  A.0, or should V3 get a generated table as well to reduce reader confusion?
- Is `PAPER_SUBMISSION.pdf` still a live deliverable despite being 45 pages
  while both TORS PDFs are 40 pages?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Search manuscript and TeX for stale Office V3 pending/no-claim wording.
- [x] Re-run Office V3 adjudicator dynamically.
- [x] Re-run strict manuscript/artifact gate.
- [x] Check tracked/untracked status of Office V3 aggregate JSONs, treestate
      sidecars, and per-user sidecars.
- [x] Check Office V3 sidecar metadata for missing final-sidecar fields.
- [x] Check compiled PDF page counts and hygiene output.
- [x] Fact-check comparator, novelty, and recent-literature claims against
      primary/official sources where available.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Make Office V3 status consistent in abstract/introduction/related work/
      results/discussion/conclusion/availability.
- [ ] Decide and document the Office V3 sidecar/release boundary.
- [ ] Refresh stale `paper_tex/BUILD_NOTES.md`.
- [ ] Inspect SILLM4Rec full paper or soften/restate the exclusion rationale.

## Audit Run - 2026-07-13 15:50 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `a437f14c` (`Regenerate
  RELEASE_MANIFEST at the Office V3 boundary`).
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/main.tex`, `paper_tex/paper-shared.tex`,
  `paper_tex/sections/*`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/hygiene_scan_output.txt`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/references.bib`,
  `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`, `RELEASE_MANIFEST.json`,
  `_bestrec_run/hstu_results_manifest.json`, `_bestrec_run/hstu_tables.json`,
  and `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`.
- Working tree state observed before this audit's write: `PAPER_REVIEW_AUDIT.md`
  already modified; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`. This audit
  edited only `PAPER_REVIEW_AUDIT.md`.

### Verdict

**No new numerical or artifact-gate failure was found, but the same manuscript
consistency defect remains a hard submission blocker.** Office V3 is supported
by the current artifacts and by a fresh dynamic adjudication, yet the paper still
contains older prose saying the redesigned Office pre-registration is pending or
that no Office claim counts. For a paper whose main contribution is evaluation
governance, this is likely reject-level if submitted as-is.

The recent-literature paragraph is mostly defensible because it avoids direct
comparative claims against concurrent or non-interchangeable work. The remaining
literature risk is SILLM4Rec: it is close enough to require either direct ACM
PDF inspection or a concrete non-comparability sentence grounded in the public
repo's candidate-ranking/SFT-DPO workflow.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run/adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-13 15:48:52`.
  - K=16: seed finals `0.03060`, `0.03053`, `0.03046`, `0.03033`, `0.03041`;
    mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` above both
    `0.0279` and `0.0271`.
  - K=8: seed finals `0.03025`, `0.03037`, `0.03030`, `0.03030`, `0.03026`;
    mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` above both
    `0.0279` and `0.0271`.
  - Comparability conditions OK: dataset identity within the declared +/-1
    interaction tolerance; reference artifacts hash-match; E1 dirty-tree
    exemption accepted via treestate sidecars; embedded code/data hashes
    identical across all 10 runs.
- `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release manifest verification OK for `113` files.
  - PASS: MI V2 gate; legacy Office V1 remains descriptive/VOID.
- `rg "outcome pending|no claim counts Office|not part of any counted claim|Office never a passed category|35 pages|36 pages|CCS|keyword"`
  - Still finds stale Office V3 pending/no-claim wording in
    `PAPER_SUBMISSION.md`, `paper_tex/sections/01-introduction.tex`,
    `02-related.tex`, `06-discussion.tex`, `07-conclusion.tex`, and
    `08-availability.tex`.
  - Still finds stale 35/36 page counts, CCS/keyword warning, and "Office never
    a passed category" in `paper_tex/BUILD_NOTES.md`.
- `pypdf` page-count check:
  - `paper_tex/PAPER_TORS.pdf`: 40 pages, 612 x 792 pt.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 40 pages, 486 x 720 pt.
  - `PAPER_SUBMISSION.pdf`: 45 pages, 612 x 792 pt.
- `git ls-files "_bestrec_run/results_OFFICEV3_*" "OFFICE_V3_RESULTS.md" "PREREG_OFFICE_V3.md" "_bestrec_run/results_OFFICEV3_*users.jsonl.gz"`
  - Tracks `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`, all 10 V3 JSONs,
    and all 10 V3 treestate files.
  - Does not track any Office V3 per-user sidecar matching the `users.jsonl.gz`
    pattern.

### Confirmed Problems

1. **Office V3 prose remains internally contradictory.** The abstract and
   Section 5.2 now say Office V3 passed and is counted; Section 6.4 also says
   V3 passed and is the second counted pre-registered per-category comparison.
   But the introduction, related-work evaluation-practice paragraph, conclusion,
   and Section 6.5 still say the redesigned Office pre-registration is pending
   or that no Office claim counts.
2. **Section 8 availability is still stale for a counted V3 claim.** The strict
   artifact graph sources `office_v3`, and tracked V3 JSON/treestate files are
   present. Section 8 still says Office sidecars are local-only and not part of
   any counted claim. The paper must distinguish tracked V3 printed-cell
   evidence from local-only per-user sidecars, and say whether those sidecars
   are needed for independent recomputation.
3. **The abstract still over-compresses the comparator execution boundary.**
   It says the comparator reference implementation cannot execute on this
   hardware, while Section 5.6 says the reference research path does execute
   locally under shims. The precise claim is about the pinned official
   CUDA/Triton environment, not the entire reference implementation.
4. **`paper_tex/BUILD_NOTES.md` remains stale.** The top now reports 40/40
   pages, but later sections still report 35/36 pages, still carry a stale
   CCS/keyword warning despite current CCS/keywords in `paper-shared.tex`, and
   still embed an old hygiene block ending with "Office never a passed
   category."

### Confirmed Fixes / Non-Problems Since The Prior Section

- Office V3 adjudication remains mechanically green on a fresh run; no
  adjudicator crash, missing run, or comparator-hash defect recurred.
- The strict artifact gate remains green after the Office V3 integration:
  `office_v3` is in `required_families`, both Office V3 table cells source to
  tracked JSONs, and the strict build reports no mismatches.
- The recent GrIT / Augment-or-Not / DiffuReason paragraph is cautious enough
  on the checked facts: it uses point-estimate language and non-comparability
  caveats rather than claiming superiority.
- The compiled TORS hygiene scan remains PASS; the stale hygiene text is in
  `BUILD_NOTES.md`, not in `hygiene_scan_output.txt`.

### External Fact-Check / Novelty Notes

- GrIT reports Amazon Video Games with `94,762` users, `25,612` items, and
  `814,586` interactions, uses a standard leave-one-out split, states that
  testing uses the full item set, and reports Video Games NDCG@10 `0.0588`.
  This supports the paper's "matching statistics / point-estimate observation"
  wording, but not a direct comparability or superiority claim because the
  implementation/protocol details were not audited. Source:
  https://arxiv.org/html/2602.19728v1
- Augment-or-Not uses Amazon'23 Musical Instruments and Industrial & Scientific,
  5-core filtering, leave-one-out with second-to-last validation and last test,
  and reports LETTER-TIGER Musical Instruments NDCG@10 `0.0282`. This supports
  citing it as AR2023-adjacent LLM-recommender context rather than as a stronger
  HSTU-BLaIR-family comparator. Source:
  https://arxiv.org/html/2505.23053v1
- DiffuReason reports a different "Video & Games" universe (`67,658` users,
  `25,535` items, `654,867` interactions), says Video & Games is sourced from
  Amazon Reviews 2023, applies rating `> 3` positives, truncates/pads histories
  to length 20, and reports HSTU-backbone N@10 values under that setup. This
  supports the paper's non-interchangeability caveat. Source:
  https://arxiv.org/pdf/2602.09744
- SILLM4Rec remains close and under-inspected. ACM metadata/search snippets say
  the experiments use three 5-core Amazon Reviews 2023 sub-datasets including
  `Baby_Products`, `Video_Games`, and `CDs_and_Vinyl`; the public repo tells
  users to download AR2023 5-core files, then generate image descriptions, user
  preference summaries, candidate product ranking tasks, and SFT/DPO training
  data. This supports treating it as not yet established as full-catalog LLOO,
  but the paper should cite the concrete workflow or inspect the ACM PDF.
  Sources: https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec

### Concrete Fixes To Make Next

1. Replace every stale Office V3 pending/no-claim sentence with one consistent
   two-track statement:
   - Office V1 remains VOID under its original floor-check pre-registration.
   - Office V3 passed under the separate environment-matched pre-registration
     and counts only as a per-category point-estimate comparison, not paired
     superiority or SOTA.
2. Update Section 8 availability for V3:
   - tracked: `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`, V3 JSONs,
     treestate sidecars, and `hstu_results_manifest.json`;
   - local-only: per-user `*.users.jsonl.gz` / `*.final.users.jsonl.gz`
     sidecars, hash-embedded in run manifests;
   - explicit statement on whether local-only sidecars are outside printed-cell
     recomputation or available through a release artifact.
3. Repair the abstract comparator sentence so it says the pinned official
   environment cannot execute locally, while the unpinned shimmed research path
   can run only as an environment-caveated single-run regeneration.
4. Refresh `paper_tex/BUILD_NOTES.md`: remove old 35/36 page-count sections,
   remove the stale CCS/keyword warning, replace the embedded old hygiene block
   with the current 40-page / 18-review-hit PASS block, and delete "Office never
   a passed category."
5. Inspect the SILLM4Rec ACM PDF directly before freeze, or revise the paper's
   SILLM4Rec sentence to cite the public repo's candidate-ranking/SFT-DPO
   workflow as the concrete non-comparability reason.

### Open Questions

- Are Office V3 per-user sidecars intentionally local-only, or should they be
  released/deposited now that V3 is counted?
- Should `RELEASE_MANIFEST.json` list Office V3 result files directly under
  `result_families`, or is the strict `hstu_results_manifest.json` evidence
  layer the intended source of truth?
- Is `PAPER_SUBMISSION.pdf` still a live deliverable now that it is 45 pages
  while the TORS artifact is 40 pages?
- Can the authors access the SILLM4Rec ACM PDF, or should the paper use the
  public repo workflow as the explicit basis for exclusion?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Search manuscript and TeX for stale Office V3 pending/no-claim wording.
- [x] Re-run Office V3 adjudicator dynamically.
- [x] Re-run strict manuscript/artifact gate.
- [x] Check tracked/untracked status of Office V3 JSONs, treestate files, and
      per-user sidecars.
- [x] Check compiled PDF page counts and hygiene output.
- [x] Fact-check current related-literature claims against GrIT,
      Augment-or-Not, DiffuReason, and SILLM4Rec sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Make Office V3 status consistent in abstract/introduction/related work/
      results/discussion/conclusion/availability.
- [ ] Decide and document the Office V3 sidecar/release boundary.
- [ ] Refresh stale `paper_tex/BUILD_NOTES.md`.
- [ ] Inspect SILLM4Rec full paper or soften/restate the exclusion rationale.

## Audit Run - 2026-07-13 16:49 Australia/Sydney

### Audited State

- Workspace: `C:\Users\rayxc\Documents\R`
- Branch/HEAD: `codex/bestrec-sota-results` / `a437f14c` (`Regenerate
  RELEASE_MANIFEST at the Office V3 boundary`).
- Canonical sources/artifacts inspected: `PAPER_SUBMISSION.md`,
  `PAPER_SUBMISSION.pdf`, `paper_tex/main.tex`, `paper_tex/paper-shared.tex`,
  `paper_tex/sections/*`, `paper_tex/BUILD_NOTES.md`,
  `paper_tex/hygiene_scan_output.txt`, `paper_tex/PAPER_TORS.pdf`,
  `paper_tex/PAPER_TORS_acmsmall.pdf`, `paper_tex/references.bib`,
  `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`,
  `RELEASE_MANIFEST.json`, `_bestrec_run/hstu_results_manifest.json`,
  `_bestrec_run/hstu_tables.json`, and Office V3 result JSON/sidecar files.
- Working tree state observed during this audit: `PAPER_REVIEW_AUDIT.md`
  already modified; untracked `_bestrec_run/impact_program.DONE`,
  `_bestrec_run/smoke_FIRB_IS_seed1.json`,
  `data_raw_proper/cds_vinyl/CDs_and_Vinyl.csv.gz`, and
  `data_raw_proper/industrial_sci/Industrial_and_Scientific.csv.gz`. This audit
  edited only `PAPER_REVIEW_AUDIT.md`.

### Verdict

**No new aggregate numerical or strict-gate failure was found, but the manuscript
still has a reject-level consistency problem.** Office V3 remains mechanically
supported: the adjudicator passes, the strict artifact build recomputes the
Office V3 cells, and the external HSTU-BLaIR constants still match the cited
paper. The live rejection risk is that multiple sections still say Office is
pending or non-counted while other sections count the V3 pass.

This run also sharpens the availability issue: Office V3 per-user sidecars are
local-only and untracked, and three Office V3 result JSONs have
`user_records_final_path = null`. Those three runs have `best_test_epoch = 20`
over 20 epochs, so the regular `user_records_path` may be the final-epoch
sidecar, but the pre-registration explicitly says final-epoch sidecars are
emitted. A reviewer can accept the aggregate gate only if the paper/release
states this boundary precisely.

### Commands And Evidence Checked

- `uv --project _bestrec_run run python _bestrec_run\adjudicate_office_v3.py --no-append`
  - PASS at `2026-07-13 16:49 Australia/Sydney`.
  - K=16: seed finals `0.03060`, `0.03053`, `0.03046`, `0.03033`, `0.03041`;
    mean `0.03047`, sd `0.00011`, 95% CI-LB `0.03033`, `5/5` seeds above
    both `0.0279` and `0.0271`.
  - K=8: seed finals `0.03025`, `0.03037`, `0.03030`, `0.03030`, `0.03026`;
    mean `0.03029`, sd `0.00005`, 95% CI-LB `0.03024`, `5/5` seeds above
    both `0.0279` and `0.0271`.
  - Comparability conditions OK: dataset identity within the declared +/-1
    interaction tolerance; reference artifacts hash-match; E1 dirty-tree
    exemption accepted through treestate sidecars; embedded code/data hashes
    identical across all 10 runs.
- `uv --project _bestrec_run run python _bestrec_run\rebuild_hstu_submission.py --strict`
  - PASS: HSTU core-block parity exact.
  - PASS: `168` cells recomputed; `0` untraceable; `0` paper mismatches; all
    `14` declared claim families sourced.
  - PASS: release manifest verification OK for `113` files.
  - PASS: MI V2 gate; legacy Office V1 remains descriptive/VOID.
- `rg "outcome pending|no claim counts Office|not part of any counted claim|Office never a passed category|35 pages|36 pages|CCS|keyword|SILLM4Rec"`
  - Still finds stale Office V3 pending/no-claim wording in
    `PAPER_SUBMISSION.md`, `paper_tex/sections/01-introduction.tex`,
    `02-related.tex`, `06-discussion.tex`, `07-conclusion.tex`, and
    `08-availability.tex`.
  - Still finds stale 35/36 page counts, the old CCS/keyword warning, and the
    old "Office never a passed category" hygiene summary in
    `paper_tex/BUILD_NOTES.md`.
- `uv --project _bestrec_run run python -c "<pypdf page-count check>"`
  - `paper_tex/PAPER_TORS.pdf`: 40 pages.
  - `paper_tex/PAPER_TORS_acmsmall.pdf`: 40 pages.
  - `PAPER_SUBMISSION.pdf`: 45 pages.
- `paper_tex/hygiene_scan_output.txt`
  - PASS: `PAPER_TORS.pdf`, 40 pages, 0 placeholder/forbidden-claim failures,
    18 informational SOTA/negated-claim review hits.
- `git ls-files "_bestrec_run/results_OFFICEV3_*" ...`
  - Tracks `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`, all 10 Office V3
    result JSONs, and all 10 treestate sidecars.
  - Does not track Office V3 per-user sidecars.
- Structured Office V3 sidecar parse:
  - Local Office V3 sidecar archives matching `results_OFFICEV3_*users*.jsonl.gz`:
    `17` files, total `80,688,616` bytes.
  - All 10 JSONs have `user_records_path` and existing regular sidecars.
  - `results_OFFICEV3_k16_seed20260729.json`,
    `results_OFFICEV3_k16_seed20260731.json`, and
    `results_OFFICEV3_k8_seed20260731.json` have no
    `provenance.user_records_final_path`; each has `best_test_epoch = 20` and
    `history_count = 20`.

### External Fact-Check / Novelty Notes

- HSTU-BLaIR v3 reports AR2023 5-core Video Games, Office Products, and
  Musical Instruments with the same item/user statistics used here, and Table 2
  reports HSTU-BLaIR NDCG@10 `0.0760`, `0.0271`, and `0.0406` respectively.
  This supports the paper's comparator constants. Source:
  https://arxiv.org/html/2504.10545v3
- SILLM4Rec is not safe to dismiss with only "metadata did not establish
  comparability." ACM/search metadata indicates an MMAsia 2025 paper using
  Amazon Reviews 2023 5-core sub-datasets and reporting NDCG, while the public
  repo's workflow says to create image descriptions, user preference summaries,
  candidate product ranking tasks, and SFT/DPO training data. That supports a
  non-comparability rationale, but the paper should cite the concrete workflow
  or inspect the ACM PDF directly. Sources:
  https://dl.acm.org/doi/10.1145/3743093.3771011 and
  https://github.com/MKC-Lab/SILLM4Rec
- The Amazon Reviews 2023 official site confirms the dataset is a 2023 McAuley
  Lab release with user reviews, item metadata, links, and standard splits,
  supporting the paper's high-level dataset framing. Source:
  https://amazon-reviews-2023.github.io/

### Confirmed Problems

1. **Office V3 prose is still contradictory.** The abstract and Section 5.2
   say Office V3 passed and is counted; Section 6.4 also says V3 is counted.
   But the introduction, related-work paragraph, conclusion, and Section 6.5
   still say the redesigned Office pre-registration is pending or that no
   Office claim counts.
2. **Section 8 is stale for a counted claim.** It says Office sidecars are
   local-only and not part of any counted claim. The printed Office V3 cells are
   counted and source to tracked JSONs, so Section 8 must distinguish printed
   aggregate-cell evidence from per-user sidecars.
3. **Office V3 sidecar metadata needs an erratum or release manifest.** Three
   Office V3 JSONs lack `user_records_final_path` even though the prereg says
   final-epoch sidecars are emitted. Because those runs' best epoch is final
   epoch, the regular sidecar may be enough, but this needs to be made explicit.
4. **The abstract still over-compresses the execution boundary.** It says the
   comparator reference implementation cannot execute on this hardware, while
   Section 5.6 says the unmodified reference research path executes locally
   under shims. The accurate distinction is pinned CUDA/Triton environment
   versus unpinned shimmed research path.
5. **`paper_tex/BUILD_NOTES.md` is still stale.** The top reports the new 40/40
   page state, but later sections still report 35/36 pages, the old CCS/keyword
   warning, and an old hygiene block ending with "Office never a passed
   category."
6. **SILLM4Rec remains an under-cited exclusion.** The current sentence is
   directionally defensible but too vague for a top-journal related-work
   section. It should either cite the ACM paper/repo and state "candidate
   reranking/SFT-DPO, not established as full-catalog LLOO," or inspect the
   PDF and update the comparison.

### Confirmed Non-Problems

- The Office V3 aggregate gate remains green on a fresh run; no adjudicator
  crash, missing run, reference hash defect, or comparator threshold drift was
  observed.
- The strict artifact graph remains green and includes `office_v3` in required
  claim families; the Office V3 printed cells source to tracked JSONs.
- The current HSTU-BLaIR comparator constants are externally supported by the
  cited arXiv v3 paper.
- The current compiled TORS hygiene scan is PASS; the stale hygiene text is in
  `BUILD_NOTES.md`, not `paper_tex/hygiene_scan_output.txt`.

### Concrete Fixes To Make Next

1. Replace every stale Office V3 pending/no-claim sentence with one consistent
   two-track statement:
   - Office V1 remains VOID under its original floor-check pre-registration.
   - Office V3 passed under the separate environment-matched pre-registration
     and counts only as a per-category point-estimate comparison, not paired
     superiority or SOTA.
2. Update Section 8 and/or release docs for V3:
   - tracked: `PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`, V3 JSONs,
     treestate sidecars, and `hstu_results_manifest.json`;
   - local-only: Office V3 per-user `*.users.jsonl.gz` / `*.final.users.jsonl.gz`
     sidecars, hash-embedded in result JSONs;
   - explicit statement on whether aggregate printed-cell recomputation is
     sufficient without per-user sidecars, or where the sidecars will be
     deposited.
3. Add an Office V3 sidecar erratum/manifest explaining the three null
   `user_records_final_path` cases, preferably noting that `best_test_epoch =
   final epoch` if the regular sidecar is the intended final sidecar.
4. Repair the abstract comparator sentence: the pinned official CUDA/Triton
   environment cannot execute locally; the unpinned shimmed research path can
   run only as an environment-caveated single-run regeneration.
5. Refresh `paper_tex/BUILD_NOTES.md`: remove old 35/36 page-count sections,
   remove the stale CCS/keyword warning, replace the embedded old hygiene block
   with the current 40-page / 18-review-hit PASS block, and delete "Office never
   a passed category."
6. Revise the SILLM4Rec sentence with a concrete citation/reason, or inspect
   the ACM PDF directly before freeze.

### Open Questions

- Are Office V3 per-user sidecars intended for public release/deposit now that
  V3 is counted, or are aggregate result JSONs the declared reproducibility
  boundary?
- For the three Office V3 runs with `user_records_final_path = null`, is
  `user_records_path` explicitly the final-epoch sidecar because the best epoch
  is epoch 20, or should separate final sidecars be generated?
- Should `RELEASE_MANIFEST.json` list Office V3 result files directly under
  `result_families`, or is `hstu_results_manifest.json` the intended source of
  truth for Office V3?
- Is `PAPER_SUBMISSION.pdf` still a live deliverable now that it is 45 pages
  while both TORS PDFs are 40 pages?

### Running Checklist

- [x] Read automation memory and prior cumulative audit.
- [x] Locate canonical manuscript, TeX, PDF, result, preregistration, release,
      and audit artifacts.
- [x] Search manuscript and TeX for stale Office V3 pending/no-claim wording.
- [x] Re-run Office V3 adjudicator dynamically.
- [x] Re-run strict manuscript/artifact gate.
- [x] Check tracked/untracked status of Office V3 JSONs, treestate files, and
      per-user sidecars.
- [x] Check Office V3 sidecar metadata for null final-sidecar fields.
- [x] Check compiled PDF page counts and hygiene output.
- [x] Fact-check current comparator and related-literature claims against
      HSTU-BLaIR, SILLM4Rec, and AR2023 sources.
- [x] Update current prioritized rejection-risk list.
- [x] Append this timestamped audit section.
- [ ] Make Office V3 status consistent in abstract/introduction/related work/
      results/discussion/conclusion/availability.
- [ ] Decide and document the Office V3 sidecar/release boundary.
- [ ] Refresh stale `paper_tex/BUILD_NOTES.md`.
- [ ] Inspect SILLM4Rec full paper or soften/restate the exclusion rationale.
