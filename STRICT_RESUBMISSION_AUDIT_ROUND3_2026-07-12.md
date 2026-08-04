# Strict Resubmission Audit Round 3 - 2026-07-12

## Audited State

- Branch: `codex/bestrec-sota-results`
- HEAD: `15ea70b8873b44213999a6f8624ceb21ae3a875b`
- Tracked working tree: clean.
- Untracked local artifacts present during audit:
  - `_bestrec_run/theirs_runs/office_hstu_blair.log`
  - `_bestrec_run/theirs_runs/office_hstu_blair/`
  - `_paper_render.html`
  - `tmp/`
- Audit scope: current paper package, artifact graph, PDF, manifest consistency, pinned-environment parity evidence, and a spot check against current primary-source comparator literature. I did not rerun the full multi-seed training campaign.

## Verdict

**Scientific core: approve the narrowed claim set.**

The current manuscript no longer tries to sell the old broad SOTA story. It frames Video_Games as competitive but not SOTA, Musical_Instruments as a per-category point-estimate comparison against HSTU-BLaIR, Office as VOID/descriptive, and the reference-implementation runs as environment-caveated regenerations rather than official pinned reproductions. Under that narrow framing, I do not find a remaining scientific-core reason to reject.

**Final publication package: conditional minor-to-moderate revision, not unconditional accept yet.**

The empirical gates now pass, the PDF is readable, and the new pinned CPU parity evidence is strong. However, the release/provenance package is not yet perfectly self-consistent at HEAD, and there is one reproducibility footgun in the new parity script. I would not sign a camera-ready artifact bundle until the findings below are fixed.

**Broad SOTA claim: reject.**

The paper still must not claim broad SOTA over HSTU-BLaIR, TIGER, LIGER, BLaIR, or the broader recommender literature. The manuscript currently avoids that claim, which is correct.

## Commands Rerun

All commands below were run from `C:\Users\rayxc\Documents\R`.

| Check | Result |
|---|---|
| `uv --project _bestrec_run run python _bestrec_run/build_hstu_tables.py --submission` | PASS: 163 cells recomputed, 0 `MISMATCH`, 0 `UNTRACEABLE`, 12/12 declared claim families sourced |
| `uv --project _bestrec_run run python _bestrec_run/test_hstu_parity.py` | PASS: HSTU core block parity exact within the asserted `1e-5` gate |
| `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict` | PASS: parity, strict table build, MI adjudication, Office VOID/descriptive adjudication all completed |
| WSL pinned leg: `wsl.exe -e /home/ray/pinned_parity_env/bin/python ... test_pinned_env_parity.py --mode pinned` | PASS against real `fbgemm-gpu-cpu==0.6.0`, torch `2.2.2+cpu`, CPU only |
| WSL shim replay: `... --mode shimmed` | PASS: same-stack shim replay bit-exact, block gate exact `0.0` |
| Windows paper-stack shim replay: `uv --project _bestrec_run run python ... --mode shimmed` | PASS: op/grad replay exact `0.0`; block drift within `1e-5`, observed max `4.768e-07` |
| `uv --project _bestrec_run run python _bestrec_run/fbgemm_shims.py` | PASS: shim self-test on CPU and CUDA |
| `uv --project _bestrec_run run python _bestrec_run/theirs_runs/tmp/pinned_parity/negative_control.py` | PASS: exact gate detects padding, length, and one-ulp perturbations |
| PDF inspection with `pdfinfo`, `pypdf`, and rendered pages 2, 27, 28, 30, 31 | PASS for readability; no stale placeholder strings found; explicit non-claims list renders correctly |

## What Is Now Strong

1. **The artifact graph is materially stronger than in prior rounds.** `_bestrec_run/hstu_tables.json` reports submission mode, no untraceable cells, no paper mismatches, no unsourced printed table values, and all declared claim families present.

2. **The paper's claim boundaries are now reviewer-safe.** `PAPER_SUBMISSION.md:441`, `PAPER_SUBMISSION.md:486`, and `PAPER_SUBMISSION.md:494` explicitly preserve the key caveats: comparator runs are regenerations not reproductions, Office is VOID, and broad SOTA is not claimed.

3. **The pinned CPU parity objection is mostly closed.** The intended three-leg parity sequence works:
   - real pinned CPU fbgemm under WSL passes,
   - same-stack shim replay is bit-exact,
   - Windows paper-stack replay has only tiny fp32 CPU kernel drift.

4. **The PDF is no longer visibly broken.** The previous "Explicit non-claims" inline-list defect is fixed. The rendered pages I inspected are readable and not misleading.

5. **The Office claim is no longer being smuggled back in.** The paper says Office gate arithmetic passed but the preregistered floor check voids it. That is the right decision.

## Remaining Findings

### F1. Release manifest is stale relative to the submitted HEAD

Severity: **Major artifact-packaging issue.**

Evidence:

- `RELEASE_MANIFEST.json:8` records `git_commit = 31ca137dc5c7e11b4336c0d9df43d3f206505e3c`.
- Current HEAD is `15ea70b8873b44213999a6f8624ceb21ae3a875b`.
- `RELEASE_MANIFEST.json:169` says the manifest describes the working tree at `git_commit` and that the containing commit is the immediate child of that commit. That was true for the round-2 fix, but it is no longer true after the later pinned-parity commit.
- The new paper now cites `PINNED_ENV_PARITY_REPORT.md`, and HEAD adds `_bestrec_run/test_pinned_env_parity.py`, but those are not covered by the release manifest.

Impact:

The empirical results are not invalidated, but a strict reproducibility reviewer can say the submitted package and its top-level release manifest no longer describe the same commit. This is exactly the kind of small inconsistency that undermines an otherwise strong artifact story.

Required fix:

Regenerate or supplement the manifest at `15ea70b...`. It should include hashes for at least:

- `PAPER_SUBMISSION.md`
- `PAPER_SUBMISSION.pdf`
- `PINNED_ENV_PARITY_REPORT.md`
- `_bestrec_run/test_pinned_env_parity.py`
- `_bestrec_run/fbgemm_shims.py`
- `THEIRS_ON_OURS_REPORT.md`
- the pinned-parity logs/JSON outputs if they remain cited as artifacts

Then update `CANONICAL_SUBMISSION.md` and DOI/deposit instructions to point to the new manifest boundary.

### F2. `test_pinned_env_parity.py --mode pinned` can silently pass without real fbgemm

Severity: **Major reproducibility footgun, but not a result invalidation.**

Evidence:

- `_bestrec_run/test_pinned_env_parity.py:498` catches `fbgemm_gpu` import failure and installs the shim fallback.
- `_bestrec_run/test_pinned_env_parity.py:600` still reports the pinned-mode gate.
- I accidentally ran `uv --project _bestrec_run run python _bestrec_run/test_pinned_env_parity.py --mode pinned` in Windows first. It printed `SHIM-FALLBACK` and still exited PASS.
- The intended WSL pinned command later did run real `fbgemm-gpu-cpu==0.6.0` and passed, so the evidence itself is real. The problem is that the CLI can create a false PASS if a reviewer runs the wrong command.

Impact:

A reviewer could reproduce the wrong "pinned" leg and believe they tested real fbgemm when they did not. This is preventable and should be fixed before submission.

Required fix:

Make `--mode pinned` fail closed unless real `fbgemm_gpu` imports. If a dev fallback is useful, require an explicit flag such as `--allow-shim-fallback-for-dev` and print a non-publication warning. The publication command must never let `SHIM-FALLBACK` count as pinned evidence.

### F3. Pinned-parity output artifacts are not manifest-backed

Severity: **Moderate artifact issue.**

Evidence:

- `PINNED_ENV_PARITY_REPORT.md:198-202` lists scratch artifacts in `_bestrec_run/theirs_runs/tmp/pinned_parity/`.
- `git ls-files` shows the report and test script are tracked, but the parity output files themselves are not tracked.
- The current scratch directory contains `pinned_ops.pt`, `pinned_block.pt`, `inenv_results.json`, replay JSONs, setup logs, and negative-control logs, but these are not included in `RELEASE_MANIFEST.json`.

Impact:

The test is rerunnable, and I reran it successfully, so this is not fatal. But if the report cites these outputs as artifacts, they need either archived hashes or a clear statement that they are generated scratch products whose source of truth is the script plus commands.

Required fix:

Either archive and hash the parity outputs in the release/deposit bundle, or change the report to say the scratch files are reproducible intermediates and add a strict regeneration command to the artifact gate.

### F4. An Office HSTU-BLaIR comparator run is active but not part of the tracked submission

Severity: **Moderate disclosure risk.**

Evidence:

- Untracked files exist at `_bestrec_run/theirs_runs/office_hstu_blair/` and `_bestrec_run/theirs_runs/office_hstu_blair.log`.
- A Python training process was active during the audit.
- The partial metrics file had 42 rows and was only around epoch 24; it is not a completed official result.
- `THEIRS_ON_OURS_REPORT.md:291` and `THEIRS_ON_OURS_REPORT.md:365` still describe Office HSTU-BLaIR as not run / staged.

Impact:

Because Office is VOID and not counted, this does not invalidate the submitted claim set. But once the authors know an Office HSTU-BLaIR run is underway, final submission should not leave it as invisible local state if it completes before submission. Otherwise a reviewer can object that a relevant comparator result was suppressed or ignored.

Required fix:

Let the run finish or explicitly cancel it. If it finishes before submission, integrate it as descriptive/non-confirmatory Office evidence with the same VOID caveat, or archive it outside the submitted artifact bundle and state that it postdates the frozen submission. Do not silently leave a completed comparator run unreported.

### F5. Source manifest still contains stale historical notes

Severity: **Minor-to-moderate audit hygiene issue.**

Evidence:

- `_bestrec_run/hstu_results_manifest.json:10176` still says `PAPER WORDING MISMATCH` for a sampled-softmax row.
- `_bestrec_run/hstu_results_manifest.json:11299` still says `PAPER WORDING MISMATCH` for a CF1 row.
- `_bestrec_run/hstu_results_manifest.json:12218` still says the matched comparator-baseline rerun is "in progress".
- The current paper and generated tables appear to have fixed these issues, and the cells are marked `OK`, but the notes remain stale.

Impact:

This does not break the numbers, but it weakens the "source of truth" story. A reviewer reading the manifest directly will see contradictions.

Required fix:

Update the stale notes to describe the current state, rerun `build_hstu_tables.py --submission`, and confirm the strict gate still passes.

### F6. Final venue formatting is not done

Severity: **Minor unless the target venue requires a template now.**

Evidence:

- `PAPER_SUBMISSION.pdf` is 37 pages, generated by HeadlessChrome/Skia from `_paper_render.html`.
- The PDF is readable, but it is not in a standard conference/journal LaTeX template.

Impact:

Not a scientific blocker. It is a submission-readiness blocker once a target venue is chosen.

Required fix:

Move to the chosen venue template before actual submission. Keep the artifact table values generated from JSON, not retyped into LaTeX by hand.

## External Novelty/SOTA Spot Check

Primary-source spot check:

- HSTU remains a strong modern sequential-transduction comparator: [Actions Speak Louder than Words: Trillion-Parameter Sequential Transducers for Generative Recommendations](https://arxiv.org/abs/2402.17152).
- BLaIR is the relevant AR2023 text/retrieval source: [Bridging Language and Items for Retrieval and Recommendation](https://arxiv.org/abs/2403.03952).
- TIGER and LIGER remain relevant generative-retrieval comparators, but they are not evaluated under the same AR2023 5-core LLOO protocol used here: [TIGER NeurIPS 2023](https://papers.neurips.cc/paper_files/paper/2023/file/20dcab0f14046a5c6b02b61da9f13229-Paper-Conference.pdf), [LIGER](https://arxiv.org/abs/2411.18814).

Conclusion from the spot check: the paper's explicit non-claim over TIGER/LIGER/BLaIR/HSTU-BLaIR is necessary and correct. The novelty should be sold as a careful HSTU-style pure-PyTorch empirical study with a causal FIR temporal filter, a dataset-conditional text/tail pattern, and unusually strong artifact auditing, not as a general SOTA recommender.

## Claims I Would Allow

- A leak-free, strictly causal FIR temporal filter improves the local HSTU-style stack on the tested AR2023 5-core LLOO setting.
- The FIR effect transfers to Musical_Instruments in the reported ablations.
- The text/tail benefit is dataset-conditional, not universal.
- Musical_Instruments has a pre-registered per-category point-estimate comparison against the published HSTU-BLaIR number, with caveats about the comparator being a published single point and not a paired test.
- The reference implementation was locally regenerated for selected runs under an unpinned but increasingly well-audited shimmed environment.
- Office is descriptive and VOID under the preregistered floor check.

## Claims I Would Not Allow

- Broad SOTA.
- SOTA over TIGER, LIGER, BLaIR, or HSTU-BLaIR.
- Video_Games SOTA.
- Office as a confirmed second-category pass.
- Paired superiority over HSTU-BLaIR.
- Full pinned-GPU reproduction.
- Training-level equivalence between torch 2.2.2/fbgemm pinned CUDA and torch 2.11/shimmed Windows.

## Required Fixes Before I Would Sign Off

1. Regenerate or supplement `RELEASE_MANIFEST.json` at HEAD `15ea70b...`, including the new pinned-parity evidence and paper/PDF hashes.
2. Make `test_pinned_env_parity.py --mode pinned` fail if real fbgemm is unavailable.
3. Decide the fate of the active untracked Office HSTU-BLaIR run: complete and disclose, or exclude with a clear date/freeze boundary.
4. Clean stale notes in `_bestrec_run/hstu_results_manifest.json`.
5. Rerun the strict build after those changes and re-render the PDF.

## Final Decision

If this were a journal/conference review today, I would return:

**Minor revision for the narrowed paper; reject any broad-SOTA framing.**

The hard scientific objections from earlier rounds are now largely addressed. The remaining issues are not "your result is fake" issues; they are "your final artifact bundle must be as clean as your audit standard claims" issues. Fixing the manifest boundary, the pinned-mode fail-closed behavior, the untracked Office-run disclosure, and the stale manifest notes would move my decision to approval of the narrow submission.

