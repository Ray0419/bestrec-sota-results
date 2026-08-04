# Paper Acceptance Repair Plan

Date: 2026-07-11

Goal: produce a submission that can pass a strict reviewer by narrowing claims, eliminating untraceable results, making the artifact graph fail closed, and aligning every paper statement with reproducible evidence.

## Executive Decision

Do not try to save every claim.

The fastest credible path is a narrower paper:

> A careful empirical and reproducibility paper showing that a strictly causal FIR temporal filter is a small but real incremental lever for an HSTU-style sequential recommender under AR2023 5-core full-catalog LLOO, with clean evidence on Video_Games and Musical_Instruments.

The paper should not currently claim broad SOTA, general AR2023 SOTA, or a clean Office_Products confirmation.

## Current Claim Status

| Claim | Status | Action |
|---|---:|---|
| Core HSTU block parity | Keep | Exact parity test passes; scope it to the core block |
| Video_Games competitive result | Keep | Must say "not SOTA" |
| Musical_Instruments point-estimate win | Keep conditionally | Narrow point-estimate comparison only |
| Office_Products second-category pass | Remove or mark VOID | Failed preregistered floor check; not manifest-backed |
| Dataset-conditional tail pattern | Keep with major caution | AR2023-limited empirical pattern, not a law |
| TAPE | Keep as minor ablation | Not a headline contribution |
| Negative-result map | Keep as exploratory/supporting | Single-seed rows must not carry confirmatory weight |
| Broad SOTA | Remove | Not supported |

## Phase 1: Make The Artifact Gate Fail Closed

### Problem

`_bestrec_run/build_hstu_tables.py` currently exits successfully even when it reports:

- 4 `UNTRACEABLE` empirical rows.
- 6 manuscript `MISMATCH` cells.

This is unacceptable for a publication build.

### Required Work

1. Add a strict submission mode:

   ```powershell
   uv --project _bestrec_run run python _bestrec_run/build_hstu_tables.py --strict-submission
   ```

2. In strict mode, the script must exit nonzero if any of the following exist:

   - `UNTRACEABLE` cells.
   - `MISMATCH` cells.
   - empirical cells missing from `_bestrec_run/hstu_results_manifest.json`.
   - Office or other newly added claims absent from the manifest.

3. The paper/PDF build must call strict mode first.

4. The build must print a short failure report listing exact table, row, value, source file, and required fix.

### Acceptance Criteria

- `UNTRACEABLE = 0`
- `MISMATCH = 0`
- all paper empirical values are manifest-backed
- table generation exits nonzero on any future drift

## Phase 2: Remove Or Rerun Table 1a

### Problem

Table 1a contains three untraceable 5-seed rows:

- SASRec no-text 5-seed.
- SASRec-SBERT MiniLM 5-seed.
- SASRec-BLaIR 5-seed.

The paper says these rows carry no claim weight, but then immediately uses them to discuss text gains, MiniLM vs BLaIR, and tight seed variance.

### Option A: Fastest Safe Fix

Remove Table 1a from the main paper or replace it with a short prose note:

> Earlier SASRec-family protocol-parity scans were not retained with sufficient artifact provenance and are therefore excluded from the submission claims.

Then remove all observations derived from those rows.

### Option B: Stronger Fix

Rerun Table 1a cleanly:

1. Run SASRec no-text, SASRec-SBERT MiniLM, and SASRec-BLaIR for 5 seeds.
2. Save per-seed JSONs.
3. Save per-user sidecars if the row is used for statistical claims.
4. Add every row to `_bestrec_run/hstu_results_manifest.json`.
5. Regenerate `_bestrec_run/hstu_tables.json`.
6. Verify strict build passes.

### Acceptance Criteria

- No untraceable Table 1a values remain.
- No paper paragraph cites a row that is not traceable.

## Phase 3: Re-Adjudicate Office_Products Honestly

### Problem

The Office_Products result numerically exceeds the published HSTU-BLaIR point estimate, but it violates its own preregistered floor check.

The preregistration says the SASRec floor must be at or below the published SASRec 0.0153 neighborhood. The observed local floor is 0.02208, about 44.3 percent higher.

That means the Office comparison may be using an easier or otherwise non-comparable local baseline configuration/protocol.

### Immediate Required Fix

In the current paper:

1. Remove Office from the abstract headline.
2. Remove "two of the three AR2023 categories" from the abstract, results, and conclusion.
3. Mark Office as `VOID / descriptive` because the preregistered floor check failed.
4. Keep Office only as appendix or future-work evidence unless repaired.

Suggested wording:

> Office_Products numerically exceeded the published HSTU-BLaIR point estimate under the frozen MI configuration, but the preregistered SASRec floor check failed because our local SASRec floor was substantially above the published SASRec reference. We therefore treat Office as descriptive evidence, not as a passed confirmatory category.

### Repair Path If Office Is Needed

1. Run a matched SASRec baseline that mirrors the comparator paper as closely as possible.
2. If possible, run HSTU and HSTU-BLaIR in a compatible environment or obtain author-provided split-matched results.
3. Explain the 0.02208 vs 0.0153 floor discrepancy with evidence.
4. Add Office to the manifest-backed table build.
5. Generate full-user final-epoch sidecars for K=16, K=8, and ID-only arms.
6. Re-adjudicate Office only after the comparability issue is resolved.

### Acceptance Criteria

Office can be restored only if:

- the floor-check failure is resolved by evidence, or
- a new preregistered comparator-valid protocol is run, or
- the paper frames Office as descriptive only.

## Phase 4: Add Office To The Artifact Graph Or Remove It

### Problem

Office values appear in `PAPER_SUBMISSION.md`, but not in:

- `_bestrec_run/hstu_results_manifest.json`
- `_bestrec_run/hstu_tables.json`
- `_bestrec_run/build_hstu_tables.py`

This reintroduces hand-written empirical claims.

### Required Work

If Office stays anywhere outside an appendix note:

1. Add Office source JSONs to the manifest.
2. Add recomputation rules for:

   - K=16 mean.
   - K=16 sample standard deviation.
   - K=16 95 percent lower bound.
   - K=8 mean.
   - K=8 sample standard deviation.
   - K=8 95 percent lower bound.
   - seed count above comparator.
   - full-user `n_eval`.
   - SASRec floor comparison.

3. Generate an Office table from the manifest.
4. Make the strict build fail if Office text values drift.

### Acceptance Criteria

- No Office number appears in the paper unless it is generated from the manifest.

## Phase 5: Generate Full-User Office Sidecars

### Problem

The Office JSONs contain full-user final metrics in `history[-1].test` with `n_eval = 223308`, but the embedded sidecars correspond to best-by-validation 30k-user subsample metrics:

- sidecar `user_records_n = 30000`
- best-test `n_eval = 30000`
- final headline `n_eval = 223308`

### Required Work

1. Add an eval-only replay mode that loads each final checkpoint or saved model state and writes full-user records.
2. If final checkpoints were not saved, rerun Office only if the claim is being restored.
3. Write full-user JSONL or compressed JSONL sidecars for:

   - Office K=16 seeds 20260623-20260627.
   - Office K=8 seeds 20260623-20260627.
   - Office ID-only seeds 20260623-20260627.
   - Office SASRec floor if used.

4. Embed sidecar hashes and row counts in each result JSON.

### Acceptance Criteria

- headline Office result has per-user records with `n = 223308`
- hashes are recorded
- strict manifest validates sidecar existence and row count

## Phase 6: Clean The Manuscript Contradictions

### Required Edits In `PAPER_SUBMISSION.md`

1. Fix the category-scope contradiction.

   Current stale idea:

   > We test only Video_Games and Beauty_and_PC.

   Correct scope:

   > The headline causal-FIR evidence uses Video_Games and Musical_Instruments; Beauty_and_PC supports the tail-pattern null; Office_Products is descriptive unless repaired.

2. Fix HSTU parity language.

   Correct wording:

   > The core HSTU block is numerically parity-tested against the reference research implementation. We do not claim full end-to-end HSTU-BLaIR system parity because the official CUDA/Triton stack is not executable on our hardware.

3. Fix all `+17.6%` instances to `+17.5%`.

4. Fix code/data availability.

   It must mention every category and artifact needed for the current claims:

   - Video_Games
   - Musical_Instruments
   - Beauty_and_PC if kept
   - Office_Products only if kept
   - split hashes
   - text-cache hashes
   - result JSONs
   - sidecars
   - table manifests

5. Remove or soften any claim that the HSTU-BLaIR gap is "localized to CUDA/Triton numerics."

   Safer wording:

   > The official HSTU-BLaIR stack cannot be executed on our hardware, so we cannot isolate the residual gap. The gap may reflect kernel behavior, training recipe, feature path, checkpointing, or implementation constants.

### Acceptance Criteria

- no stale category claims
- no contradictory HSTU parity scope
- all percentages match generated tables
- no unsupported causal explanation for the HSTU-BLaIR gap

## Phase 7: Lock The Permitted Claim Set

### Allowed Main Claims

1. A strictly causal FIR temporal filter is an incremental causal adaptation of prior filtering ideas.
2. It improves the HSTU-style stack on Video_Games in multi-seed ablations.
3. It transfers to Musical_Instruments and carries most of the MI improvement over the no-filter stack.
4. The MI result exceeds the published HSTU-BLaIR point estimate under explicit caveats.
5. Text benefits are dataset-conditional and tail effects are small in absolute terms.
6. TAPE is a minor, sub-additive text-prototype ablation.

### Forbidden Claims

1. Broad SOTA.
2. General AR2023 SOTA.
3. SOTA over HSTU-BLaIR on Video_Games.
4. Office as passed confirmatory evidence until repaired.
5. Causal identification of the real-world data-generating process.
6. Kernel numerics as the proven cause of the HSTU-BLaIR gap.
7. Any conclusion derived from untraceable Table 1a rows.

### Acceptance Criteria

- abstract, introduction, results, limitations, and conclusion all obey the same claim set

## Phase 8: Statistical Cleanup

### Required Work

For every primary result, report:

- evidence class: confirmatory, exploratory, or external
- seed count
- metric
- sample unit
- confidence interval method
- whether p-values are corrected
- whether comparator is paired or unpaired

### Tail Pattern

Keep:

- MI tail win
- VG powered null
- Beauty null if clearly exploratory or lower-powered

Do not overuse:

- Office tail result, because P1 was VOID
- synthetic thinning as real-world causal identification

### Negative Result Map

1. Label single-seed rows as exploratory.
2. Do not use them as proof that a mechanism generally fails.
3. Let only multi-seed, predeclared negatives carry confirmatory weight.

### Acceptance Criteria

- every p-value and CI has a named sample unit
- no uncorrected multi-claim family is presented as final proof
- exploratory results are visually and textually separated from confirmatory results

## Phase 9: Reproducibility And Release

### Required Work

1. Create one canonical rebuild command, for example:

   ```powershell
   uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict
   ```

2. Replace hardcoded virtualenv paths with portable `uv --project`.

3. Make skip/resume behavior explicit:

   - default: clean regeneration or fail if outputs exist
   - `--resume`: reuse existing outputs

4. Use strict shell behavior where shell scripts remain:

   ```bash
   set -euo pipefail
   ```

5. Produce a release manifest containing:

   - git commit
   - command lines
   - Python and package versions
   - GPU/CPU notes
   - raw data identifiers
   - split hashes
   - text-cache hashes
   - result JSON hashes
   - sidecar hashes
   - generated table hashes
   - paper/PDF hash

6. Archive large artifacts with a stable DOI-backed service if possible.

### Acceptance Criteria

- a reviewer can rebuild paper-facing tables from artifacts
- no result relies on a local-only untracked file
- raw large records have a documented release path

## Phase 10: Presentation And PDF Polish

### Required Work

1. Replace placeholder references, including the incomplete HSTU-BLaIR citation.
2. Remove "Format: short style."
3. Rewrite appendix lab language such as "killed" into formal wording.
4. Remove all draft/changelog/audit prose from the submission copy.
5. Render the PDF.
6. Visually inspect:

   - title and author block
   - section numbering
   - table alignment
   - figure labels
   - equations
   - citation formatting
   - line wrapping
   - appendix readability

### Acceptance Criteria

- no draft notes
- no placeholders
- no broken citations
- no lab-notebook language
- PDF is visually clean

## Final Acceptance Gate

The paper is ready to submit only when all of these are true:

1. `build_hstu_tables.py --strict-submission` passes with zero warnings.
2. `UNTRACEABLE = 0`.
3. `MISMATCH = 0`.
4. Office is either removed from headline claims or fully repaired.
5. Every empirical value in the paper is manifest-backed.
6. Full-user sidecars exist for every headline result that needs per-user validation.
7. No stale category or parity contradictions remain.
8. No broad SOTA language remains.
9. The PDF is rendered and visually inspected.
10. The release manifest covers code, commands, data, caches, results, sidecars, tables, and paper.

## Recommended Minimum Submission Version

If time is limited, submit the narrower version:

- Main result: causal FIR filter on Video_Games and Musical_Instruments.
- MI point-estimate comparison: retained with caveats.
- Tail pattern: retained as small, AR2023-limited empirical evidence.
- Office: moved to appendix as descriptive/void.
- Table 1a: removed unless rerun.
- Strict artifact gate: required.

This version is not a broad SOTA paper. It is a careful empirical paper with a defensible incremental method and unusually transparent reproducibility evidence. That is the version most likely to survive strict review.
