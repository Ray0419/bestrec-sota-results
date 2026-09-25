# PREREG: Steam generality chapter (V1)

**Frozen 2026-08-12, before any Steam run.** Governs the generality chapter of the merged TOIS-target paper, per the grilled shared understanding (confirmed by the maintainer 2026-08-12): venue order TOIS → IP&M → TORS; measurement contribution with prescriptive framing; Steam chapter is load-bearing for the TOIS breadth burden.

## 1. Purpose and pre-declared null

Every verified result to date is Amazon-only (MI, VG). This chapter tests whether the instruments and the decision framework transfer to a non-Amazon, text-bearing domain. **The transfer-null is pre-declared as a reportable outcome:** the repo's own precedent (`PREREG_FIR_EFFICIENCY_ML1M_V1` → `ML1M-NO-FIR-REPLICATION`) shows Amazon-derived effects can fail to transfer entirely. If the instruments do not transfer to Steam, that is the chapter, honestly reported — not a discarded experiment.

## 2. Dataset

Steam reviews + games metadata (McAuley/Kang 2017 crawl, the SASRec-lineage standard): ~2.57M users, ~32k games, ~7.8M reviews; game metadata carries title, genres, tags, publisher — the text side the instruments require (MovieLens was disqualified for having none). Preprocessing: 5-core, through an adapter into the existing `preprocess_5core_standard.py` conventions (same split format as the Amazon categories) so the entire downstream pipeline — trainer, temporal split, per-event eval, decomposition — runs unmodified. Text embeddings: MiniLM over title+genres+tags, same encoder as the Amazon caches.

**Sanity anchor (gate):** our backbone trained on Steam under standard LLOO must land within a defensible band of published SASRec-family Steam numbers (SASRec/BERT4Rec/GRU4Rec/FMLP-Rec are all reported on this dataset). A pipeline that can't reproduce the ballpark invalidates everything downstream; the campaign does not start until this gate passes.

## 3. Design

1. **Temporal protocol** (ported, credited to the parallel session's design): pooled-quantile cutoffs q=0.60/0.75, first-appearance arrival proxy, natural cold, first-availability mask. Measure observed π_t.
2. **Arms:** text backbone, 3 seeds (20260736–38); 5 if effects are near a decision boundary (rule: any primary CI whose exclusion verdict would flip within ±1 SD).
3. **Instruments over the post-hoc family** (per Q12): text-kNN imputation, ridge imputation, pure offset sweep, and score-level fusion — every method scored by all four endpoints below, so the efficiency ratio discriminates *between* methods.
4. **Popular-framework/SOTA comparison, "if applicable" clause interpreted concretely:** (a) published-number anchors for SASRec-family methods (always applicable); (b) an HSTU-BLaIR Steam run using the configs already in `external/HSTU-BLaIR` **iff** the documented sm_120 compatibility caveats permit — reported with those caveats verbatim, as the repo's prior HSTU-BLaIR port was. If infeasible, that infeasibility is stated, not silently dropped.

## 4. Endpoints (identical to PREREG_TEMPORAL_V1 §3, unchanged)

E1 within-pool AUC gain (confirmed iff all seeds > 0, CI excludes 0) · E2 offset-matched efficiency ratio (confirmed iff CI excludes 1.0) · E3 break-even p\* with CI · E4 primary: aggregate effect at observed π_t, with the E3/E4 sign-agreement consistency requirement.

**Decision rules.** Instruments transfer iff E1 and E2 confirm on Steam. Framework transfers iff E3/E4 agreement holds. Partial transfer (E1 yes, E2 no, etc.) is reported as measured — no re-slicing, no metric substitution, no seed additions beyond the pre-stated 3→5 rule.

## 5. Budget & risks

Post-5-core Steam ≈ 334k users / 13k items (SASRec paper's figures): largest training runs of the program, est. 30–60 min/run ⇒ campaign ≈ 3–6 GPU-h. Adapter + encoding ≈ half a day. Risks: raw-format drift in the 2017 crawl (adapter work), embedding cache size (13k items — small), and the known possibility the 16 GB card forces batch reduction at 334k users (fallback: user subsampling with the subsample machinery, declared if used).

## 6. Out of scope

Trained cold-start baselines (DropoutNet-style) — deferred until a reviewer asks; runtime/serving (walled off in `adaptive-recsys-ara`); any algorithmic headline claim.
