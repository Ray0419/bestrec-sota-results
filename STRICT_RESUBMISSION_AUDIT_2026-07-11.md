# Strict Resubmission Audit

Date: 2026-07-11

Submission audited: `PAPER_SUBMISSION.md` as the declared canonical HSTU/FIR manuscript, plus the associated HSTU parity report, Office confirmation report, generated table artifacts, and result JSONs.

Reviewer stance: hostile but fair. I reran the local table builder and HSTU parity test, inspected the Office result JSONs, checked the manifest/table graph, and spot-checked current external comparator claims online.

## Verdict

Reject / major revision.

This resubmission is materially stronger than the prior package. It has a canonical manuscript, the HSTU core-block parity test now passes exactly, the novelty language is substantially narrower, and the Musical_Instruments point-estimate result remains numerically traceable. However, I still would not approve the paper as submitted.

The current blockers are now sharper:

1. The table build still exits green with 4 untraceable empirical rows and 6 manuscript mismatches.
2. The new Office_Products confirmation violates its own preregistered floor check.
3. The Office headline is not integrated into the manifest-backed generated tables.
4. Office full-user headline metrics have no full-user sidecar records; the embedded sidecars are only the 30k subsample.
5. `PAPER_SUBMISSION.md` still contains stale contradictions and claim hygiene problems.

The narrow Musical_Instruments per-category point-estimate comparison can remain conditionally usable. The new Office "second category passed" claim is not approved under the preregistration as written.

## Checks I Ran

### HSTU parity

Command:

```powershell
uv --project _bestrec_run run python _bestrec_run/test_hstu_parity.py
```

Result: PASS. The test reports max absolute difference 0.0 end-to-end and at every checked stage when the LayerNorm epsilon is aligned. This is a genuine fix to the earlier HSTU fidelity blocker, scoped to the core research HSTU block.

### HSTU table builder

Command:

```powershell
uv --project _bestrec_run run python _bestrec_run/build_hstu_tables.py
```

Result: exit code 0, but the output is not publication-clean:

- 148 cells recomputed OK.
- Paper check summary: 124 exact, 18 within rounding, 6 MISMATCH, 4 UNTRACEABLE.
- The script still prints "BUILD GREEN" despite the warnings.

For a publication gate, this must be a failure.

### Office result inspection

I inspected `_bestrec_run/results_OFFICE_k{16,8}_seed*.json` and `_bestrec_run/results_OFFICE_idonly_seed*.json`.

The final-epoch Office headline values are present in each JSON under `history[-1].test` with `n_eval = 223308`. The best-by-validation summaries and sidecars are only `n_eval = 30000`.

This means the Office summary numbers are traceable at aggregate level, but full-user per-record evidence for the headline is missing.

### External comparator spot-checks

I checked public sources for the current comparator context:

- HSTU-BLaIR arXiv table reports Video_Games NDCG@10 0.0760, Office_Products 0.0271, and Musical_Instruments 0.0406: https://arxiv.org/html/2504.10545v3
- ReSID reports Amazon Reviews 2023 subsets and Musical_Instruments N@10 0.0346 in its table: https://arxiv.org/html/2602.02338v1
- ChronoSID is a newer semantic-ID temporal method and reports improvements over ReSID; its MI output-level table distinguishes ReSID 0.0325 from ChronoSID 0.0345: https://arxiv.org/html/2607.03918v1

The paper's broad external-comparator caution is correct, but the ReSID/ChronoSID paragraph needs more precise wording.

## What Improved

### P1. Canonical path now exists

`CANONICAL_SUBMISSION.md` declares `PAPER_SUBMISSION.md` as the submission copy. The old BEST-Rec v4 generator and LC2C-era artifacts have been archived or marked noncanonical. This resolves the previous "no single paper" failure in structure, though not yet in execution.

### P2. HSTU core-block parity is now demonstrated

`HSTU_PARITY_REPORT.md` and `_bestrec_run/test_hstu_parity.py` are substantive. The old docstring/code/spec conflict is no longer a rejection-level problem for the core HSTU block.

Important scope: this validates the block math against the reference research implementation at the tied configuration. It does not validate the whole HSTU-BLaIR training system, data pipeline, hyperparameters, kernel behavior, or end-to-end reproduction.

### P3. Novelty language is much safer

The manuscript now states that the causal FIR filter is an incremental causal adaptation of prior FMLP-Rec/BSARec-style filtering ideas, that TAPE is modest, and that the paper is not claiming a wholly new architecture. This is much closer to defensible framing.

### P4. Musical_Instruments result remains conditionally usable

The MI V2 evidence chain is still the cleanest part of the package:

- Fresh seeds.
- Dual-kernel gate.
- Rebuild evidence.
- Sidecar manifest.
- Published HSTU-BLaIR point estimate exceeded by seed-level confidence intervals.
- Caveat stated: point-estimate comparison only, not paired superiority and not general SOTA.

I would allow this narrow claim if the paper removes table mismatches and stale contradictions.

## Blocking Findings

### F1. The generated table gate still allows untraceable paper values

`_bestrec_run/build_hstu_tables.py` exits successfully while reporting:

- 4 UNTRACEABLE rows.
- 6 MISMATCH cells.

The untraceable rows include:

- `PAPER_SUBMISSION.md:236`: SASRec no-text 5-seed row.
- `PAPER_SUBMISSION.md:237`: SASRec-SBERT MiniLM 5-seed row.
- `PAPER_SUBMISSION.md:238`: SASRec-BLaIR 5-seed row.
- `PAPER_SUBMISSION.md:259`: HSTU-BLaIR local port best-epoch value, excluded in the text but still tracked as an unretained value by the artifact graph.

The manuscript tries to quarantine Table 1a at `PAPER_SUBMISSION.md:240`, but then immediately uses the untraceable rows at `PAPER_SUBMISSION.md:242-247` to make empirical observations about text gain, MiniLM vs BLaIR, and seed reproducibility. That is not acceptable.

Required fix: the table builder must fail on any `UNTRACEABLE` or `MISMATCH` in submission mode. Either rerun and retain the Table 1a artifacts, or remove those rows and all observations derived from them.

### F2. Office_Products violates its own preregistered floor check

`SOTA_CONFIRM_PREREG_OFFICE.md:46-48` states that the plain ID-only SASRec run "must be at or below" the published SASRec 0.0153 neighborhood, because an easier split would inflate it.

The actual result in `SOTA_CONFIRM_OFFICE_RESULTS.md:72` is:

- Observed floor SASRec NDCG@10: 0.02208
- Published SASRec NDCG@10: 0.0153
- Relative inflation: +44.3 percent

The report still declares `P2 DUAL GATE: PASS` at `SOTA_CONFIRM_OFFICE_RESULTS.md:74`.

As a strict reviewer, I reject this adjudication. The preregistered gate had a floor-check condition, and that condition failed. The paper may disclose the failure, but it cannot count Office as a clean second-category pass unless it resolves the floor-check failure with a matched comparator-baseline rerun or a preregistered amendment made before looking at results.

Required fix: mark the Office P2 result as VOID or "not comparable under prereg floor check" until a matched SASRec/HSTU-BLaIR-family baseline explains the 44 percent floor inflation.

### F3. Office headline is not manifest-backed

`PAPER_SUBMISSION.md:314` adds a major new Office result:

- K=16 final NDCG@10 0.03042 +/- 0.00008
- K=8 final NDCG@10 0.03033 +/- 0.00018
- all 10 seeds above 0.0271
- "two of the three AR2023 categories"

But `rg` finds no Office entries in `_bestrec_run/hstu_results_manifest.json`, `_bestrec_run/hstu_tables.json`, or `_bestrec_run/build_hstu_tables.py`. The new Office claim is hand-written text, not part of the manifest-backed paper table system.

This reintroduces the exact artifact-provenance problem the resubmission claimed to fix.

Required fix: add Office to the manifest, generated tables, and paper build. The build must fail if the Office cells drift or are absent.

### F4. Office full-user sidecars are missing

The Office JSONs contain final full-user metrics in `history[-1].test` with `n_eval = 223308`. However, their embedded `user_records_path`, `user_records_n`, and `user_records_sha256` refer to the best-by-val 30k-user subsample:

- best-test `n_eval`: 30000
- sidecar `user_records_n`: 30000
- final-epoch headline `n_eval`: 223308

So the headline result has no full-user per-record sidecar hash. This blocks independent per-user statistical checks and record-level reproducibility for the Office headline.

Required fix: regenerate or eval-only replay the final-epoch Office models and write full `n=223308` per-user sidecars for K=16, K=8, and ID-only arms, then hash and manifest them.

### F5. The manuscript still contains stale contradictions

`PAPER_SUBMISSION.md:455-460` says:

- "Generalization to all AR2023 categories: we test only Video_Games and Beauty_and_PC. Books was deferred."

But the paper's central claims now rely on Musical_Instruments and Office_Products. This is stale text and directly contradicts the abstract, section 5.2, and the new Office paragraph.

`PAPER_SUBMISSION.md:467` says the HSTU-style implementation is "verified equation-by-equation only" and "we do not claim numerical parity," while the repository now has a numerical core-block parity report showing exact equality. This is inconsistent. The correct limitation is narrower: no executable official end-to-end HSTU-BLaIR kernel/system reproduction, but core research-block parity is demonstrated.

`PAPER_SUBMISSION.md:478` says +17.6 percent over SASRec. The recomputed value is +17.5 percent, and the abstract already uses +17.5 percent.

`PAPER_SUBMISSION.md:488` says only Video_Games and Beauty text caches are released. The current paper needs Musical_Instruments and Office_Products artifacts too.

Required fix: run a manuscript consistency pass after generated tables are finalized. No stale "what we do not claim" bullets, no contradictory HSTU-parity wording, no unreconciled percentages.

### F6. The residual-gap explanation is overclaimed

The abstract and conclusion repeatedly say the gap to HSTU-BLaIR Video_Games is localized to custom CUDA/Triton kernel numerics. That is too strong.

What is actually proven:

- The official custom kernels cannot run on the local sm_120 setup.
- The local HSTU core block can be made numerically identical to the reference research block in a controlled CPU test.
- The submitted model does not match HSTU-BLaIR Video_Games.

What is not proven:

- That the residual gap is caused by CUDA/Triton numerics.
- That training recipe, full stack differences, optimizer schedule, feature path, sequence preprocessing, checkpoint choice, or implementation constants are not responsible.

Required fix: replace "localize the residual gap to kernel numerics" with "we could not isolate the residual gap because the official end-to-end stack is not executable on our hardware; kernel incompatibility blocks a faithful reproduction."

### F7. Office P1 prediction is void, but the paper still uses it as pattern support

The Office preregistered tail prediction was scored VOID because the connectivity statistic landed in the ambiguous zone and the stats tool had an internal U-definition inconsistency. The paper correctly discloses this at `PAPER_SUBMISSION.md:314`, but then uses the descriptive Office tail hit counts as support for the connectivity gradient.

This is allowed only as descriptive post hoc pattern evidence. It must not be used as a pre-registered confirmation of the tail rule.

Required fix: make the Office tail paragraph explicitly non-confirmatory and remove "out-of-sample prediction" language from any claim summary unless the VOID status is adjacent.

### F8. Current semantic-ID comparison needs precision

`PAPER_SUBMISSION.md:286` says ReSID and ChronoSID both report Musical_Instruments NDCG@10 around 0.0346, while also noting different filtered universes. Public tables show ReSID reports MI N@10 0.0346 in its own setup, and ChronoSID reports MI values under its own setup with ReSID and ChronoSID separated.

The paper should not compress this into a simple "both report 0.0346" sentence. It is not fatal, because the paper does not claim against them, but a strict reviewer will see it as imprecise comparator positioning.

Required fix: cite each result separately, with exact metric, dataset statistics, and whether it is main-table ranking or output-level analysis.

### F9. Presentation and reference hygiene remain below submission standard

Examples:

- `PAPER_SUBMISSION.md:496` still says "Format: short style."
- `PAPER_SUBMISSION.md:507` has a placeholder reference: "Liu, X. (et al.), 2025. HSTU-BLaIR: ..."
- Appendix A retains old scan language such as "killed" runs and superseded material. It may be useful internally, but it reads like a lab notebook, not a polished appendix.
- There is no rendered PDF visual audit in the current evidence chain.

Required fix: produce a clean conference-style PDF with complete references, no placeholders, and appendix material rewritten in formal language.

### F10. Reproducibility scripts are still not release-grade

`_bestrec_run/run_office_program.sh` hardcodes `_bestrec_run/.venv/Scripts/python`, skips existing outputs by default, and depends on an external driver log before proceeding. The prereg promises precise execution, but the driver is not robust enough for a fresh external reviewer.

Required fix: use portable `uv --project _bestrec_run run python ...`, strict shell failure handling, explicit `--resume` semantics, and one documented clean rebuild command for the canonical HSTU/FIR paper.

## Claim Decisions

| Claim | Decision | Reason |
|---|---:|---|
| Core HSTU block parity | Accept with scope | Exact parity test passes for the core research block |
| MI per-category point-estimate over HSTU-BLaIR 0.0406 | Conditionally accept | Numerically traceable, but paper/package must remove stale contradictions and table mismatches |
| Office second-category pass over HSTU-BLaIR 0.0271 | Reject for now | Preregistered floor check failed by +44.3 percent; Office not manifest-backed; full-user sidecars missing |
| Video_Games SOTA | Reject | Paper correctly says no, HSTU-BLaIR 0.0760 remains stronger |
| Broad AR2023 or recommender SOTA | Reject | Not claimed cleanly, not supported |
| Dataset-conditional tail pattern | Major revision | MI/VG evidence is useful; Office is VOID/descriptive; claims need tighter statistical framing |
| TAPE as a contribution | Accept only as minor ablation | Gain is small and sub-additive |
| Negative-result map | Accept as exploratory/supporting | Most rows are single-seed, not confirmatory |

## Required Repair Plan

1. Change `build_hstu_tables.py` so submission mode fails on any `UNTRACEABLE`, `MISMATCH`, or hand-written Office claim absent from the manifest.
2. Remove or rerun Table 1a. If kept, regenerate all SASRec/SBERT/BLaIR 5-seed rows and retain per-seed artifacts.
3. Re-adjudicate Office under the preregistration honestly. Either mark Office VOID/failure because the floor check failed, or run a matched comparator-baseline protocol that explains the 0.02208 vs 0.0153 gap before using Office as a pass.
4. Add Office to `hstu_results_manifest.json`, `hstu_tables.json`, and the generated paper table path.
5. Generate full-user final-epoch Office sidecars for every Office headline arm. The 30k sidecars are not enough.
6. Fix all stale manuscript contradictions: tested categories, HSTU parity scope, +17.5 percent, code/data availability, and Office VOID language.
7. Soften the HSTU-BLaIR residual-gap explanation. Do not claim kernel numerics caused the gap unless directly proven.
8. Clean references and appendix language, then render and visually inspect the PDF.
9. Create a DOI-backed artifact release or, at minimum, a complete local release manifest listing all split hashes, text-cache hashes, result JSONs, sidecars, and code hashes.

## Final Reviewer Position

I still reject the resubmission.

This is no longer a "throw it out" package. It is a serious empirical/reproducibility paper trying to become acceptable. But it is not there yet. The HSTU parity fix is real. The MI narrow point-estimate result is still the cleanest publishable claim. The new Office result is promising numerically but currently fails its own preregistered comparability floor and is not integrated into the manifest-backed artifact graph.

The fastest path to acceptance is to remove Office from the headline until repaired, make the table build fail closed, delete every untraceable Table 1a claim, and submit a narrower paper around the causal FIR lever plus the MI confirmation and carefully scoped tail-pattern evidence.
