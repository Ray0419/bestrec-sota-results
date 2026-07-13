# Pre-registration: Office_Products second-category confirmation, V3 (environment-matched reference)

**Committed BEFORE any run of this campaign.** Frozen at the git commit introducing this file;
runs execute at this commit or a documentation-only descendant (code identity via per-run
embedded code hashes, as in `SOTA_CONFIRM_PREREG_V2_ERRATA.md` E3).

## Why V3 exists (and what happened to V1)

The first Office pre-registration was **VOIDed by its own floor check** and stays VOID: its
comparability condition assumed our local SASRec floor should sit near the *published* SASRec
number, a cross-environment assumption that failed (+44%) and was later mechanistically explained
(`THEIRS_ON_OURS_REPORT.md` §4.1: the published Office SASRec row is ~+13.9% below what the
reference pipeline regenerates in this environment). V3 **removes that failure mode by
construction**: the gate reference is the **environment-matched local regeneration of the
comparator itself** — the unmodified reference implementation (their preprocessing → their gin →
their trainer → their eval) executed on this machine, on a corpus its own dataset-size assertions
verify (77,551 items / 223,308 users), yielding Office HSTU-BLaIR **best full-eval NDCG@10
0.0279** (final-epoch 0.0275), alongside the published **0.0271**. No cross-environment
comparability assumption remains. The old campaign's seeds/results are not merged or reused.

## Frozen configuration and commands

The MI-frozen V2 configuration transplanted **unchanged (zero category-specific tuning)**, both
kernels; per arm `<ARM> ∈ {16, 8}`, seed `<SEED>`:

```
_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Office_Products \
  --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
  --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu \
  --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 \
  --causal-filter --filter-kernel <ARM> --eval-every 1 --seed <SEED> \
  --out _bestrec_run/results_OFFICEV3_k<ARM>_seed<SEED>.json
```

- **Fresh seeds (never inspected in any prior run or decision): 20260728, 20260729, 20260730,
  20260731, 20260732.** Disjoint from every previously used family (incl. Office V1's
  20260623–27 and V2's 20260618–22).
- 2 arms × 5 seeds = 10 runs, sequential, queued AFTER the FIR-BREADTH campaign.
- **Headline rule (identical to the corrected V1 adjudication): the final-epoch FULL-catalog
  eval** — `history[-1].test` with `n_eval == 223,308` asserted — NOT `best_test` (whose
  checkpoint eval subsamples 30k users). Per-user final-epoch sidecars
  (`*.final.users.jsonl.gz`) are emitted and hash-embedded automatically.

## Gate (frozen)

For **each** kernel arm, over its 5 fresh seeds:

- **PASS** iff the two-sided 95% Student-t CI **lower bound** of final-epoch full-catalog
  NDCG@10 exceeds **0.0279** (the environment-matched local regeneration's best full-eval
  reading — the stricter of the two references, and > the published 0.0271 by construction)
  **and** ≥4/5 seeds individually exceed 0.0279.
- The campaign is a **second-category confirmation only if BOTH kernel arms pass.**
- One-sided failures, nulls, and voids are published with identical prominence.

## Comparability conditions (redesigned; all three must hold)

1. **Dataset identity**: our split's users/items must equal the comparator pipeline's own
   assertion-verified corpus (223,308 / 77,551; interactions within ±1 per the known CSV-header
   quirk) — re-recorded in every run manifest.
2. **Environment-matched reference**: the gate reference (0.0279) comes from the comparator's
   unmodified code executed on this same machine and corpus (`theirs_runs/office_hstu_blair/`,
   hash-manifested). If those artifacts change or are found defective, the campaign is VOID.
3. **Provenance**: per-run manifests must show a clean tracked tree (modulo the driver's own
   declared results-append pattern), embedded code hashes, and data SHA256s identical across all
   10 runs.

## Claim wording (frozen — nothing broader may be claimed)

If both arms pass: *"Under a pre-registered protocol with never-inspected seeds, both kernel
arms' fresh 5-seed 95% CI lower bounds on Office_Products exceed both the published HSTU-BLaIR
point estimate (0.0271) and its environment-matched single-run local regeneration (best
full-eval 0.0279) — a per-category point-estimate comparison. The comparator regeneration is a
single run, so no paired or distributional superiority is claimed; this is not SOTA on
Office_Products, not SOTA on Amazon Reviews 2023, and not a general-SOTA claim of any kind."*

## VOID conditions

Any arm with <5 valid runs; any headline value not from the final-epoch full-catalog rule;
missing/failed dataset-identity assertion; reference-artifact drift (condition 2); dirty-tree
provenance beyond the declared pattern; seed substitution; results overwritten rather than
appended; any post-hoc change to this document after the first run starts (append-only errata
with dates are permitted and must be disclosed).

---

## ERRATUM E1 (2026-07-13, appended BEFORE the first V3 run; campaign not yet started)

The FIR-BREADTH segment's clean-tree checkpoint (exit 43, 2026-07-13 06:44) revealed that the
**external hourly audit process appends to `PAPER_REVIEW_AUDIT.md` on its own cadence**, and the
responder appends to `RESPONSE_TO_PAPER_REVIEW_AUDIT.md` — both are documentation logs outside
this campaign's control, and either could dirty the tracked tree mid-run through no action of
the experiment pipeline (the exact failure mode that voided the V2 EXEC1 campaign via a
concurrent documentation edit). **Clarification, effective before any V3 run:** condition 3's
clean-tree requirement exempts exactly these two audit-log files (`PAPER_REVIEW_AUDIT.md`,
`RESPONSE_TO_PAPER_REVIEW_AUDIT.md`) in per-run manifests; it continues to bind every other
tracked file — in particular all protocol code, whose identity remains proven by the embedded
per-run code hashes regardless. No other condition, gate value, seed, or wording changes.

## ERRATUM E2 (2026-07-13, appended after campaign completion; disclosure, no gate change)

The prereg stated that final-epoch per-user sidecars (`*.final.users.jsonl.gz`) "are emitted
and hash-embedded automatically." The run writer emits that separate file **only when the
best-by-validation epoch differs from the final epoch**; when they coincide, the single regular
sidecar (`*.users.jsonl.gz`, embedded as `user_records_{path,n,sha256}`) **is** the final-epoch
per-user record. Three of the ten V3 runs (k16 seeds 20260729/20260731, k8 seed 20260731) hit
this coincidence: their `user_records_final_path` is null and their regular sidecar is the
final-epoch record. No per-user data is missing; all ten runs' final-epoch per-user records
exist and are hash-embedded in the tracked result JSONs. A per-run sidecar inventory is
appended to `OFFICE_V3_RESULTS.md`. Gate values, seeds, conditions, and claim wording are
unchanged; this erratum documents emission mechanics only.
