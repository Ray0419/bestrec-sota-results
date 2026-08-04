# PREREG_EE — closest-comparator benchmark: AlphaFuse (SIGIR 2025) on our split

> **READ ERRATUM E2 (bottom) FIRST.** The current VG launch is QUARANTINED as a
> protocol-deviated, NON-COUNTABLE engineering pilot (`adjudicate_ee.py` returns
> `PILOT_NONCOUNTABLE`). The estimand-equality claims in the body below —
> "identical estimand", "same full-catalog LLOO", "apples-to-apples", "contrast
> is the fusion architecture", "dimension-agnostic" — are **RETRACTED** (the two
> arms use different evaluators: AlphaFuse does not mask seen items, ours does).
> E-E V2 requirements are in E2. Body retained verbatim for the audit trail.

**Status: FROZEN before any real E-E run exists (committed-before-existence,
§5.3 disclosure ii).** Smoke test (2-epoch dev probe, 2026-07-24) confirmed the
port runs; NO real run has been executed or read at freeze time. This file fixes
the protocol, config, seeds, metric, decision rule, and the exact admissible
claim wording BEFORE launch. The mechanical adjudicator `adjudicate_ee.py` and
the result-capture runner `run_ee.py` are committed in the same commit.

## What E-E is (and is NOT)
E-E is a **descriptive closest-comparator positioning** experiment: run a recent
strong text/ID method (AlphaFuse) under OUR exact full-catalog leave-last-out
protocol and report where our stack sits relative to it. It is:
- NOT a confirmatory hypothesis test (no pass/fail on a null).
- NOT a superiority claim in either direction, NOT SOTA, NOT "beats". Reporting
  is point-estimate only; the FORBIDDEN list (CANONICAL_SUBMISSION.md) applies
  verbatim to every E-E sentence and to the adjudicator's own output.
- NOT part of the two counted comparisons (MI V2, Office V3). Running AlphaFuse
  on Office is a NEW, separate comparison (AlphaFuse-vs-ours) and does not touch
  the frozen Office V3 (ours-vs-published) claim.

## Arms (both on the SAME AR2023 5-core LLOO split, SAME MiniLM-384 text)
- **A — AlphaFuse** (Hugo-Chinn/AlphaFuse, SIGIR 2025), SASRec backbone,
  `model_type=AlphaFuse`, the authors' recommended config (their README):
  `hidden_dim=128, null_dim=64, loss_type=infoNCE, neg_ratio=64, lr=1e-3,
  ID_embs_init_type=zeros, language_embs_scale=40, temperature=0.07,
  batch_size=256, num_blocks=2, num_heads=1, dropout_rate=0.1, epoch=500,
  patience=50` (train.py defaults for the unlisted knobs). Data via our adapter
  (`build_alphafuse_dataset.py`): left-pad L=50, pad=item_num, per-prefix train
  expansion, `minilm_emb.pickle` = our frozen MiniLM-384 title vectors
  re-indexed to export item ids.
- **B — our stack** (SASRec-SBERT), the recorded per-category run, SAME MiniLM
  title embeddings, SAME split. Comparator number read mechanically from the
  pinned provenance file (below) — not hand-copied.

## Categories
- **Video_Games** (primary; adapter built + smoke-passed). Comparator provenance:
  `_bestrec_run/results_BEST_VG_seed2026061{0,1,2,9}.json` best_test NDCG@10
  (mean of the 4 recorded seeds).
- **Office_Products** (secondary; counted category — the AlphaFuse-vs-ours
  comparison is NEW and separate from Office V3). Comparator provenance: the
  canonical Office base NDCG@10 recorded in the manifest/results (pinned by the
  adjudicator at read time; VOID-floor Office V3 wording untouched).

## Seeds
- Arm A (AlphaFuse): `{22, 23, 24}` (22 = authors' default; 23,24 fresh). 3 seeds.
- Arm B (ours): its already-recorded seeds (frozen; not re-run).

## Metric
- **Primary: NDCG@10**, full-catalog LLOO (identical estimand to ours).
- Reported family (AlphaFuse emits natively): HR/NDCG/MRR @ {5,10,20,50}.

## Disclosed deviations (every E-E sentence must carry them)
1. **Embeddings**: our frozen MiniLM-384 substituted for the paper's OpenAI
   text-embedding-3 (no API key; both frozen language embeddings; AlphaFuse's
   null-space construction is dimension-agnostic). NOTE this makes A and B use
   the SAME text signal, so the contrast is the fusion architecture.
2. **Split**: our AR2023 5-core LLOO split — we NEVER compare to AlphaFuse's
   paper numbers (their ATV/ATG/ASO datasets).
3. **Training loss**: each method trains as designed — ours chunked full softmax,
   AlphaFuse sampled-negative infoNCE (neg_ratio 64). Inherent, not imposed.
4. **Train-row expansion**: per-prefix is our adapter's disclosed choice (their
   offline data-prep is not in their repo; on OUR data the choice is ours).
5. **Single environment**: one machine/GPU; point estimates, no cross-environment
   variance modeled — same "environment-caveated" class as our other runs.

## Decision rule (REPORTING gate, not a hypothesis test)
`adjudicate_ee.py` is a mechanical integrity+reporting gate. It MUST:
1. Load all present `results_EE_<cat>_alphafuse_seed*.json`; require ≥3 seeds
   for a category to be reportable (else mark that category INCOMPLETE).
2. Compute AlphaFuse mean±sd of the full metric family; assert all finite.
3. Read arm B's NDCG@10 from the pinned provenance and record its source path.
4. Emit the comparison table + the signed point-estimate difference
   (A_mean − B) labelled **descriptive, non-inferential** — no significance
   test, no "superior/better/beats/SOTA" tokens (the adjudicator scans its own
   output for those tokens and FAILS if any appear).
5. Record all five disclosed deviations verbatim in `ee_adjudication.json`.
6. Verdict vocabulary is limited to: `REPORTABLE` (≥3 seeds, integrity OK) or
   `INCOMPLETE`. There is no PASS/FAIL and no superiority verdict.

## Frozen artifacts
- Per-seed results: `_bestrec_run/results_EE_<cat>_alphafuse_seed<seed>.json`
  (written by `run_ee.py`; append-only; never overwrite `results_*.json`).
- Adjudication: `_bestrec_run/ee_adjudication.json` (verbatim, committed).
- Admissible manuscript sentence (template): "Under our full-catalog LLOO
  protocol on <cat> and the same MiniLM-384 title embeddings, AlphaFuse (its
  authors' recommended SASRec-backbone config, our split) attains NDCG@10 = A
  (mean of 3 seeds); our stack attains B. We report this as an
  environment-caveated point-estimate comparison under the five disclosed
  deviations and make no claim of statistical superiority in either direction
  and no SOTA claim."

## ERRATUM E1 (2026-07-24, at first adjudication run) — self-check string only
The frozen `adjudicate_ee.py` ran correctly on the 3 VG seeds and returned
`REPORTABLE`, but its forbidden-token self-check (a naive substring scan meant to
catch any accidental superiority/SOTA wording in its OWN output) FALSE-POSITIVED
on the adjudicator's own NEGATED disclaimer strings ("NOT SOTA", "NOT a
superiority claim"). Fix: those two disclaimer strings were reworded to
"descriptive only; no best-system or ranking claim is asserted" — semantically
identical (still asserts no superiority/SOTA). **Unchanged:** the verdict rule
(>=3 seeds, finite -> REPORTABLE), the metric aggregation, the point-estimate
computation, the comparator provenance, the disclosed deviations, and the
forbidden-token list itself. The edit cannot change the verdict or any number
(it only affects whether the substring tripwire trips on the adjudicator's own
disclaimer text); verify via `git diff` that only the two strings changed. The
VG numbers in `ee_adjudication.json` were produced by the pre-erratum
adjudicator's identical computation.

## ERRATUM E2 (2026-07-24 16:00 audit, ACCEPTED) — RETRACTION + PILOT QUARANTINE
The audit correctly showed the current VG launch is **not a countable
closest-comparator result**. VERIFIED: the two arms use DIFFERENT evaluators, so
NOT the same estimand — AlphaFuse's `utils.evaluate` ranks the catalogue WITHOUT
masking the user's consumed items; our paper evaluator masks the full train+val
history before ranking (`run_sasrec_sbert.py:1626-1630`, `final[k, items]=-inf`).
Masking removes distractors and inflates our arm, confounding the gap.

**RETRACTED for this launch:** "identical estimand", "same full-catalog LLOO",
"apples-to-apples", "the contrast is the fusion architecture", and
"dimension-agnostic". The MiniLM-384 substitution also changes the text geometry
AlphaFuse's null-space SVD is built on, so this is a controlled **AlphaFuse-style
MiniLM port, not a faithful reproduction**, and the whole systems (not just
fusion) differ (model family, dims, loss, optimiser, tuning, biases).

**QUARANTINE:** the current 3-seed VG run is a **protocol-deviated engineering
PILOT** (`adjudicate_ee.py` now returns `PILOT_NONCOUNTABLE`). Its values and
wording are NOT integrated into any paper.

**E-E V2 (required before any countable comparison):**
1. ONE shared exact-rank evaluator used UNCHANGED by both arms; freeze seen-item
   masking, catalogue eligibility, dedup, tie policy, cutoffs, val selection;
   synthetic unit tests for seen-item + tie cases.
2. Primary test = matched-backbone factorial (AlphaFuse fusion on/off) under that
   evaluator with EQUAL validation-only tuning budgets; two full systems kept
   only as a SECONDARY descriptive comparison; report params/FLOPs/mem/latency.
3. Exact provenance: register filenames, seeds, sizes, SHA-256; require exactly
   the registered files (no extras); Arm B mandatory per category; missing →
   INCOMPLETE with nonzero exit. (Also corrects the E1 comparator note: our VG
   fourth recorded seed is 09, not 19.)
4. Immutable attempt dirs + append-only hash-chained ledger + atomic writes;
   per-user rank sidecars (so HR/NDCG + clustered CIs + tail strata reconstruct).
5. Pin upstream AlphaFuse full SHA + licence + lockfile/container + clean state +
   hardware; endpoints sealed OUTSIDE the repo; register per-prefix/preprocessing
   parity (or a sensitivity) before launch; add `results_EE_*` to seal patterns.
