# PREREG: Item-degree dose-response and scale-free offset decomposition (V1)

**Frozen 2026-08-05, before any run of this design.** Written in worktree `claude/brave-rhodes-0a7d09`. Endpoints, statistics, and decision rules below are fixed prior to seeing any result. Deviations must be recorded as deviations, not edits.

## 1. Question

Does an item's training degree *causally* determine the text-vs-ID advantage, and what is the shape of that dose-response? Secondarily: once the offset-invariant metric is made scale-free, what fraction of a content-based imputation's measured cold-start benefit is genuine within-pool relevance rather than a nuisance pool offset?

## 2. Design — simultaneous multi-dose knockdown

Prior runs used one training run per dose level. That is 6× more expensive **and** confounded: capping a large item set changes global training density, so each rung's *other* items differ, and the uncapped control drifted (+0.00355 → +0.00591 across rungs, 5/5 seeds).

This design caps **disjoint item groups to different degrees inside a single run**:

- Eligible items: full train degree ≥ `--item-cap-min-deg` (so a cap of 16 binds).
- A random sample of eligible items is partitioned into 6 **disjoint** groups G₀, G₁, G₂, G₄, G₈, G₁₆, equal in size, assigned by one RNG seeded by `--item-cap-seed` (identical across every run, so groups are the same items everywhere).
- Group G_k keeps only its **k most recent** training occurrences (k = 0 removes the item from training entirely).
- A matched **uncapped control group** G_ctrl is drawn from the same eligibility pool and left untouched.
- Eval histories, eval targets, and popularity terciles stay frozen at full density (identical contract to the existing titration flags).

Every dose level therefore sits inside the same model, under the same global density, competing in the same softmax. Cross-dose comparison becomes within-run as well as within-seed and within-item-pool.

**Arms:** text (`--text-sim-bias --text-prototypes 512`) and ID-only (`--no-sbert`), initialization-paired (same seed, same config, same group assignment; only the text channel differs).

**Seeds:** 5 (20260736–20260740). **Dataset:** Musical_Instruments. **Runs:** 2 arms × 5 seeds = **10**.

## 3. Primary endpoint and decision rule

For seed *s* and dose *k*: `gap(s,k) = NDCG@10_text − NDCG@10_id`, averaged over eval targets landing on group G_k.

- **H1 — monotone dose-response (primary).** Spearman ρ between k and gap(s,·) over the 6 doses, computed per seed. **Confirmed iff** mean ρ > 0 with **5/5 seeds positive**.
- **H2 — abolition at zero degree.** gap(s,0): 95% CI across seeds **includes 0**, and gap at k=16 has a CI **excluding 0**.
- **H3 — causal contrast.** dd(s) = gap(s,16) − gap(s,0). **Confirmed iff** 5/5 seeds positive and the 95% CI excludes 0.

All CIs are across-seed t-intervals (n=5, t*=2.776) on per-seed means, reported with the sign count, per house convention. Bootstrap CIs on per-user deltas are reported as secondary.

**Pre-declared kill criteria.** If H1 fails (ρ not consistently positive), the "degree causes the text advantage" claim is withdrawn — no re-slicing of doses, no dropping of seeds, no switching to a different metric to rescue it. If H3 fails while H1 passes, the claim is downgraded to "ordinal trend only."

## 4. Secondary endpoint — scale-free offset decomposition

The current offset-invariant diagnostic (within-cold NDCG@10) **degenerates on small pools**: ranking top-10 of an 85-item pool is ~free, which produced a nonsensical 658% "genuine share". Replaced here by two scale-free statistics computed from the within-pool rank r (0-indexed) among a pool of size N:

- **within-pool AUC** = 1 − r/(N−1) — the probability the target outranks a random pool member. No cutoff, no pool-size dependence.
- **within-pool MRR** = 1/(r+1) — reported as a secondary, cutoff-free but top-weighted.

Both are exactly invariant to any constant cross-pool offset, so both isolate genuine within-pool relevance.

- **genuine share** = (AUC gain of the method) / (AUC gain achievable), reported alongside the full-catalog cold gain.
- **offset-matched efficiency ratio** = (warm cost per unit cold gain of a pure offset) / (same for the method). Exactly 1.0 for a disguised offset; > 1.0 only for genuine relevance.

Prediction on record: with the scale-free metric, the genuine share should become **comparable across cold-pool sizes**, where the NDCG@10 version read 6.6% / 70% / 658% at N = 3121 / 649 / 85.

## 5. Complexity budget

**Runtime.** 10 training runs replace 60 (6× reduction) — the entire dose-response comes from one run per (arm, seed). MI ≈ 4 min/run ⇒ ≈ 40 min total. Analysis reuses the per-user sidecars each run already writes, so dose slicing costs zero additional GPU. The decomposition scores every variant and every offset inside **one encode pass** per checkpoint (score = h·Eᵀ recomputed per table; the transformer forward, which dominates, runs once).

**Space.** Checkpoints (~95 MB) are written for the **text arm only** (5 files ≈ 475 MB), since the decomposition needs no ID-arm table. Per-user sidecars are gzipped JSONL (~1 MB/run). Group assignments are stored once per run as a small capset JSON. No dense score matrices are ever persisted; ranks are reduced to scalars in-loop, so analysis memory is O(n_eval) not O(n_eval × n_items).

**GPU citizenship.** A parallel session's `PAUSE_EXPERIMENTS` lock is present and is not removed; the driver probes `nvidia-smi` before every run and refuses to launch above 6 GB in use.

## 6. What this does NOT establish

- **Temporal validity.** This remains leave-one-out, not a global-time protocol with first-availability constraints. The parallel session's protocol is the correct one and is not adopted here. No claim about deployment-time cold start may rest on this experiment alone.
- **Cross-dataset generality.** MI only. VG is 4× costlier per run and is deferred.
- **The √N break-even law** is untouched here; it remains 3 points at 1 seed and is explicitly *not* confirmed by this design.
