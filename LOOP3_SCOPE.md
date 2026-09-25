# Loop 3 scope — global-time protocol
### 2026-08-07 · scoping only, nothing built yet · gates the three verified results in [VERIFIED_RESULTS.md](VERIFIED_RESULTS.md)

---

## 1. Why this is worth more than planned

Loop 3 was scheduled as a *validity* step: re-run promoted claims under a temporally valid protocol so they license deployment claims. The feasibility measurement below shows it is more than that.

**Under leave-one-out, cold prevalence had to be imposed. Under the global-time protocol it is observed.** The whole exchange-rate framework — break-even p\* = |c|/(g+|c|) — answers "is imputation worth it?" only when compared against an actual cold prevalence π_t. LOO gave us no such number (VG's natural cold pool was 85 items, 0.36% of catalog, an artifact of the 5-core LLOO construction). The temporal protocol yields π_t directly, and the answer is nothing like what I assumed:

| dataset | cutoff | train | evaluable events | cold items | **natural π_t** | distinct cold items hit |
|---|---|---:|---:|---:|---:|---:|
| MI | q=0.60 | 60% | 114,840 | 5,304 (21.6%) | **28.0%** | 5,174 |
| MI | **q=0.75** | 75% | 85,485 | 2,884 (11.7%) | **20.6%** | 2,840 |
| MI | q=0.85 | 85% | 55,686 | 1,674 (6.8%) | **17.4%** | 1,646 |
| VG | q=0.60 | 60% | 158,223 | 9,483 (37.0%) | **60.6%** | 9,148 |
| VG | **q=0.75** | 75% | 117,274 | 6,389 (24.9%) | **52.4%** | 6,248 |
| VG | q=0.85 | 85% | 79,696 | 4,065 (15.9%) | **47.1%** | 4,012 |

*(`poc_temporal_feasibility.py`, read-only, no GPU. Cold = first observed interaction after the cutoff; evaluable = post-cutoff event whose user has pre-cutoff history.)*

Real cold prevalence is **17–61%**, not the sub-1% the LOO protocol implied. Set against our measured break-even (p\* = 6.8% at N=243 rising to 42.3% at N=2,153), MI at q=0.75 lands at π_t = 20.6% with N_cold = 2,884 — **close enough to the break-even that the answer is genuinely undetermined**, which is exactly what makes it worth running. VG at π_t = 52.4% with N_cold = 6,389 sits in a different regime entirely.

This turns "re-verify under a better protocol" into **the decision-relevant experiment the framework was built for**.

## 2. Feasibility: green

- Sample sizes ample (85k evaluable events, 17.6k cold targets on MI at q=0.75) — far more than the ~3k that resolved effects in Loops 1–2.
- 2,840 distinct cold items hit at MI q=0.75 ≈ our largest LOO pool (3,121), so **the AUC and efficiency-ratio instruments transfer at comparable N** with no recalibration.
- 75% of interactions retained for training — model quality should remain sane.
- Timestamps span 2003–2023 with median 2018.6 (MI) / 2016.4 (VG); no pathological clustering.

## 3. Coordination — the reuse boundary (needs your call)

The parallel session **specified this protocol and implemented it** in `_bestrec_run/run_poc_temporal_lc2c_v1.py` (418 lines, All_Beauty, 356 items). Their protocol primitives are directly reusable:

| their primitive | reuse |
|---|---|
| `quantile_cutoff(events, q)` — pooled interaction-time quantile | **port as-is** |
| `first_times()` — first observed interaction as catalog-arrival proxy | **port as-is** (adopt their declared limitation too) |
| `warm = first <= cutoff`, `cold = first > cutoff` | **port as-is** |
| `available_cold_mask = first[cold] <= event.timestamp` — first-availability | **port the semantics** (needs a different implementation at our scale, §5) |
| two-stage inner/outer cutoffs (0.60 dev / 0.75 outer) | **adopt** — gives leak-free selection |
| EASE/LC2C model, PZC score alignment, bootstrap | **not reusable** — their model is item-item linear on 356 items; ours is sequential on 24k |

**Proposal:** we port their protocol semantics into our sequential pipeline and cite them as its origin; they keep ownership of the protocol contribution. No duplicated work, no competing implementations. **This needs their agreement before I write code** — it is their design, and two divergent implementations of the same protocol in one repo would be worse than either.

## 4. Design decisions (my recommendations)

1. **Cutoffs:** two-stage, q=0.60 (selection) and q=0.75 (reporting), matching their PoC. MI primary, VG secondary — VG's π_t = 52% is a genuinely different regime and worth having, but it is 4× the GPU cost.
2. **Cold definition:** natural arrival (first interaction > cutoff). **No artificial capping** — the k-dial is not needed for the cold slice here, which sidesteps the pre-empted-technique problem entirely. The dose machinery stays available for the *degree* question, which is separate.
3. **The 5-core break (declare, don't hide):** the 5-core property was established globally; under a time cut, some items/users fall below 5 pre-cutoff interactions. Their PoC applied cutoffs to the existing 5-core files and declared it. **Recommend the same** — re-coring inside the window would change the item population and break comparability with every prior run. This must be a stated limitation, not a silent choice.
4. **Availability constraint:** enforce it. Scoring against items that did not yet exist is the single largest validity threat, and it is what makes the protocol "global-time" rather than just "time-split".
5. **Endpoints:** the three verified results, re-measured — within-pool AUC gain, offset-matched efficiency ratio, and p\* — **plus the new one only this protocol enables: π_t vs p\* on the same data**, i.e. does imputation actually pay at realistic prevalence?

## 5. Engineering plan and the one real risk

**Main risk: per-event candidate availability.** A naive implementation recomputes an availability mask per event (85k events × 24.5k items) and is prohibitive. Mitigation: availability is **monotone in time** — an item, once available, stays available. So bucket evaluation events by time (e.g. 50 buckets), precompute one boolean mask per bucket via `np.searchsorted` on sorted `first_times`, and score each bucket as a batch. Cost becomes O(buckets × n_items) instead of O(events × n_items) — negligible, and it composes with the existing batched scorer. This is the piece I would prototype first.

**Build list:**
- `run_sasrec_sbert_temporal.py` (trainer copy): time-cut `train_inters`; user sequences from pre-cutoff interactions only; eval set = post-cutoff events with pre-cutoff history.
- Bucketed availability mask in the eval path.
- Extend `poc_offset_decomp.py` to consume the temporal eval (the instruments themselves are unchanged — both are already pool-size invariant and offset-invariant).
- `PREREG_TEMPORAL_V1.md` with endpoints, decision rules, and kill criteria frozen before the first run.

**Explicitly out of scope:** re-verifying the dose-response/threshold (pre-empted, low value), EB-NeRD, and any new algorithmic component.

## 6. Budget and gates

| stage | cost |
|---|---|
| Coordination + prereg | ~0 |
| Build + availability prototype | ~0.5–1 day code, no GPU |
| Smoke test (1 seed, MI, q=0.75) | ~10 min GPU |
| MI main: text + ID arms × 5 seeds | ~1.5 GPU-h |
| Decompositions (5 seeds) | ~0.5 GPU-h |
| VG secondary (optional, 3 seeds) | ~2.5 GPU-h |
| **total** | **~1 day code + 2–5 GPU-h** |

**Gates.** (a) Smoke test must reproduce sane absolute metrics before the campaign — a temporally split model scoring near zero means the pipeline is wrong, not that cold start is hard. (b) Each verified result exits labeled **temporally-valid** or **LOO-only**. (c) Pre-declared: if effects shrink or vanish under temporal validity, **that is the result** and gets reported as such — this protocol is more honest than LOO, so a shrinkage finding is a contribution, not a failure.

## 7. Decisions I need from you

1. **Coordination:** may I port their protocol into our sequential pipeline (crediting them), or should this wait for them to build it?
2. **VG or MI-only?** VG's π_t = 52% is a second regime and strengthens generality, at ~2.5 extra GPU-h.
3. **Scope discipline:** I recommend re-verifying only the three verified results and the new π_t-vs-p\* question — not reopening the dose-response.
