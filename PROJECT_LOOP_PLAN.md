# Project loop plan — cold-start measurement paper
### 2026-08-06 · operating cycle + phased iterations · companion to [NOVELTY_AUDIT.md](NOVELTY_AUDIT.md), [MERGED_COLDSTART_AGENDA.md](MERGED_COLDSTART_AGENDA.md), [RESULTS_DOSE_RESPONSE_V1.md](RESULTS_DOSE_RESPONSE_V1.md)

---

## 0. What we are building (fixed identity, decided)

**One evaluation/measurement paper**, merged with the parallel session's theory half:

> Cold-start evaluation rewards a nuisance pool offset (their theorem, our confirmation); the community's metrics cannot separate that offset from genuine cold relevance (our instruments: offset-matched efficiency ratio, within-pool AUC); the underlying representation geometry that makes the offset so effective is known representation degeneration, bridged here to evaluation (cited, not claimed); and controlled interventions show text contributes nothing below an activation threshold in item degree (our k-dial/dose machinery).

Every algorithmic idea we tested died; the paper's identity is measurement. Their RQ2 (selective FIR) remains a separate future paper and is out of scope for this loop.

---

## 1. The operating loop (applies to every claim, every iteration)

```
VERIFY → PREREG → RUN → ANALYZE → RECONCILE → DECIDE
```

1. **VERIFY (novelty + prior art), before any GPU.** Dedicated search per claim; write the 3 closest works and the surviving delta into NOVELTY_AUDIT.md. A claim without this step cannot enter a prereg.
2. **PREREG.** Frozen endpoints, statistics, decision rules, *and kill criteria* in a `PREREG_*.md` before the first run. Deviations are logged as deviations.
3. **RUN.** Foreground only (detached processes get reaped here); GPU probe before every launch (respects the other session's serialization lock); skip-if-exists resume; per-invocation run caps; sidecars + capsets always written; seeds ≥ 5 for any confirmatory claim; initialization-paired arms.
4. **ANALYZE.** Pre-registered statistics only, house conventions (across-seed t-intervals, sign counts, within-run contrasts where the design allows). Scale-free metrics (within-pool AUC/MRR) wherever pool sizes differ.
5. **RECONCILE.** Update the results docs; log corrections explicitly (never silently edit); sync a short memo of anything affecting the parallel session's half; update memory.
6. **DECIDE.** Each claim exits as PROMOTED (paper-bound), ITERATE (needs the next loop), or KILLED (recorded with the evidence). Interim readouts are never reported as findings — two claims died this session between 3 and 5 seeds.

**Standing budget rule:** ≤ 4 GPU-hours per loop iteration without an explicit decision to exceed; every loop ends with a written go/no-go for the next.

---

## 2. The iterations

### Loop 0 — verification pass (NOW; zero GPU; ~half a day)
The audit found we generated faster than we verified. Nothing else runs until this closes.

- Dedicated novelty searches for the 5 surviving claims: k-dial/multi-dose design; activation threshold; efficiency ratio; coarse-vs-fine result; within-pool metric correction. Also: break-even p\* and √N law (before Loop 2 spends GPU on them).
- Rewrite the mechanism sections of POC_RESULTS_COLDSTART.md and MERGED_COLDSTART_AGENDA.md to cite representation degeneration + popularity-direction prior art; reframe as bridge + replication.
- Write the sync memo for the parallel session (their theorem is unaffected; their write-up should cite the degeneration literature; the metric-degeneracy correction affects their protocol §4).
- **Exit gate:** every live claim has a verified-novelty entry with named closest work. Any claim pre-empted here is killed now, cheaply.

### Loop 1 — complete the dose curve (≈ 1 GPU-h)
The curve is unsampled where it is most interesting (control = 3.8× the k=16 gap).

- PREREG_DOSE_RESPONSE_V2: extend `--item-cap-multi` to {16, 24, 32, 48, 64} + control, same 5 seeds, same design. Pre-registered question: is the rise above threshold saturating, linear, or step-like? Endpoint: curve shape class by pre-declared criteria (fits compared by AIC across seed-level curves).
- **Kill criterion:** if k=16 fails to replicate (CI includes 0), the threshold claim is withdrawn, not re-tuned.
- **Exit gate:** threshold claim either PROMOTED with a characterized upper limb, or killed.

### Loop 2 — confirm or kill the √N break-even law (≈ 2–3 GPU-h)
Currently 3 points, 1 seed — the most likely next casualty, and it must not reach the paper unconfirmed.

- Design: N_cold sweep via `--item-cap-frac` ∈ {0.02, 0.05, 0.10, 0.25} at k=0, 3 seeds, MI; efficiency ratio and break-even computed with the scale-free AUC alongside NDCG. Fit exponent per seed; claim requires CI on the exponent excluding 0 and covering ~0.5 consistently.
- **Kill criterion:** exponent sign-inconsistent across seeds → the law is demoted to "cost grows with N_cold" (qualitative) and the √N figure is withdrawn.
- **Exit gate:** law PROMOTED / demoted / killed — in writing.

### Loop 3 — global-time protocol (the big build; ≈ 1 day code + 3–4 GPU-h; coordinate first)
Everything so far is leave-one-out; no deployment-time claim is licensed. This is the binding validity gap and the deliberate merge point with the parallel session.

- **Coordinate before building** — they specified the protocol (global-time cutoffs, first-availability, mixed warm/cold targets) and may have code; duplicate nothing. Decide who builds the split pipeline.
- Build: temporal splits for MI + one more category; first-availability constraints; natural cold = items first appearing after the training cutoff; mixed-target eval.
- Re-run only the PROMOTED claims from Loops 1–2 under the new protocol (threshold; efficiency ratio; decomposition). Prereg the replication with the pre-declared possibility that effects shrink or vanish under temporal validity — that outcome is a *result*, not a failure.
- **Exit gate:** each promoted claim is labeled LOO-only or temporally-valid.

### Loop 4 — generality (≈ 3–4 GPU-h)
- Replicate the temporally-valid claims on one more dataset (Office_Products ≈ MI-cost, or VG at 4×; MiniLM caches exist for both). 3–5 seeds.
- Sampled-negatives arm for the *evaluation* claims (we only checked the geometry there, not the decomposition).
- **Exit gate:** every paper-bound claim carries ≥ 2 datasets or an explicit single-dataset scope statement.

### Loop 5 — the field-wide audit (≈ 4 GPU-h; the paper's punchline)
- Their intervention audit + our instrument, unified: reproduce 3–5 published cold-start baselines from the classic list (DropoutNet-style, content-init, score-fusion variants — selected by what runs in this harness), and report each one's **efficiency ratio and offset-decomposition** under the global-time protocol.
- Pre-registered claim: some published gains are ≤ a pure offset (ratio ≈ 1.0). If none are, that is also publishable ("the field's methods do carry genuine signal; the metrics still can't show it").
- **Exit gate:** the audit table exists with pre-registered interpretation either way.

### Loop 6 — assembly (no new experiments)
- Merge with the theory half: their theorem + OCE/CVaR certificate + protocol; our instruments + interventions + audit. One paper.
- House pipeline: claim–artifact map for every number; adjudicator scripts; manifest hashes; retraction/correction log included (we already have three corrections — that trail is part of the paper's credibility, in this repo's style).
- Venue: RecSys/SIGIR full paper or TORS (fits the repo's venue plan); decide with the maintainer.

---

## 3. Standing rules distilled from this session's failures

| rule | incident that created it |
|---|---|
| Novelty search *before* GPU, for emergent claims too | suppression-axis mechanism found pre-empted after being reported |
| 5 seeds before any claim leaves the worktree | "text actively hurts at k=4" died between 3 and 5 seeds |
| Pre-registered tests, but *shape* honesty over test-passing | H1 "passed" while the data showed a threshold, not the tested ramp |
| Scale-free metrics across unequal pools | 658% "genuine share" from within-pool NDCG@10 |
| Multi-dose within-run designs over per-rung runs | 6× cost reduction + removed the density confound |
| Foreground runs, GPU probe, resumable drivers | detached processes silently reaped; crash mid-campaign |
| Corrections logged, never silently edited | three corrections so far — all traceable |
| Reconcile with the parallel session at every loop boundary | independent convergence found by accident, mid-session |

## 4. Decision points reserved for you

1. **Loop 3 ordering** — protocol-first (validity before more findings) vs Loops 1–2 first (cheap, machinery hot). Plan assumes 0 → 1 → 2 → 3; flipping 1–2 and 3 is defensible.
2. **Dataset budget in Loop 4** (Office vs VG vs both).
3. **Venue + authorship/merge mechanics** with the parallel session's output.
4. **The stop rule:** if after Loop 2 the surviving set is only {metric correction, efficiency ratio} without the threshold or the law, the right move may be a short evaluation-note paper rather than a full study — flag rather than push on.
