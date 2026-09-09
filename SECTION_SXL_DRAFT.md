# SECTION DRAFT — SCALE×LOSS (SXL) campaign

**For folding into `PAPER_COLDSTART_MEASUREMENT_DRAFT.md` as §6.8, immediately after §6.6.1 (renumber current §6.7 "Scope of validity" to §6.9). Prereg: `PREREG_SCALE_LOSS_V1.md` incl. amendments 8a/8b/8c; artifacts in `_bestrec_run/poc_out/` (`SXL_analysis.json` holds the last analysis pass only — per-LR provenance in the program log).**

---

### 6.8 Does the tail benefit of model scaling survive loss calibration?

§6.6.1 established, at a single model size, that gBCE's calibration exponent β starves the degree tail while preserving the head. Two literatures each speak to half of what happens next, and each holds fixed exactly the axis the other varies. The scaling literature — Zhang et al. (RecSys 2024, arXiv:2311.11351) — slices by popularity group and finds the large-versus-small gap *grows* as popularity falls: the tail benefits more from scale. But it does so at one loss. The calibration literature — gSASRec (Petrov & Macdonald, arXiv:2308.07192; ACM TORS, 10.1145/3699521) — establishes β-calibrated sampled objectives at one scale. The crossing matters because sampled, calibrated objectives are precisely what scaling requires: full softmax over a large catalog is what scaling makes infeasible. If the interaction is negative, the published tail-scaling promise was measured in a regime that production scaling cannot occupy. We pre-registered that crossing (`PREREG_SCALE_LOSS_V1.md`, frozen 2026-08-17) and report here what survived it — which is less than we expected, in an instructive way.

**Design.** Three losses (full-CE with chunked softmax; sampled-CE, 256 negatives; gBCE, t=0.75, K=256 ⇒ β=0.2578) × d_model ∈ {32, 64, 128, 256} × 5 seeds (20260736–40; n=3 screen, n=5 inference per the stage gate), Musical Instruments under the temporal protocol of §5, degree-sliced NDCG@10, `--eval-every 5` best-validation checkpointing at every cell. Because α = K/(n_items−1) depends only on the fixed catalog, β = 0.2578 at every rung: the loss is literally identical across the ladder. Pre-registered endpoints: H1, a replication gate on Zhang et al.'s differential (relative slopes); H2, the primary interaction, S_gBCE(TAIL k1–50) − S_fCE(TAIL) < 0 on absolute OLS slopes over log₂(d), paired by seed, Holm-corrected with H3/H4; H3, a pre-registered *null* (sampled-CE tracks full-CE, licensing the β attribution); H4, aggregate-blindness amplification >5× at every rung.

**Results at lr = 1e-3 (n = 5).** H1 passed: +0.3865 ± 0.1337, 5/5 seeds. H2 was supported: −0.000777, CI [−0.001427, −0.000127] at Holm α = 0.0167, 0/5 seeds positive; the mean absolute tail slope under gBCE is 22% of full-CE's (0.000216 vs 0.000993). H3's null held (−0.000024, CI [−0.000260, +0.000213] spans 0). H4 failed as pre-registered: the worst rung (d=256) gave 6.05× with the CI on (amplification − 5) spanning zero, and the estimator itself misbehaved (§6.8.4). Table 6 gives the per-rung values behind these slopes.

**Table 6. Per-rung NDCG@10 at lr = 1e-3, MI (seed means).** k11–20 is the band where §6.6.1's damage concentrated; HEAD is k>200; warm is the aggregate a leaderboard would report.

| band | loss | d=32 | d=64 | d=128 | d=256 |
|---|---|---:|---:|---:|---:|
| k11–20 | full-CE | 0.002085 | 0.002659 | 0.005582 | 0.005436 |
| k11–20 | sampled-CE | 0.001914 | 0.002325 | 0.004989 | 0.005123 |
| k11–20 | gBCE | 0.000157 | 0.000846 | 0.001024 | 0.000599 |
| HEAD (k>200) | full-CE | 0.120163 | 0.112325 | 0.089005 | 0.099766 |
| HEAD (k>200) | sampled-CE | 0.120638 | 0.117439 | 0.094645 | 0.097583 |
| HEAD (k>200) | gBCE | 0.140509 | 0.123200 | 0.120522 | 0.118007 |
| warm (agg) | full-CE | 0.019673 | 0.019574 | 0.018733 | 0.019187 |
| warm (agg) | sampled-CE | 0.019455 | 0.019184 | 0.018821 | 0.019140 |
| warm (agg) | gBCE | 0.017806 | 0.018176 | 0.017783 | 0.016636 |

*All values are n=5 seed means from the stage-2 `*.degree_eval.json` sidecars (seeds 20260736–40).* Full-CE's k11–20 rises ~2.6× across the ladder while gBCE's stays pinned near zero and non-monotonic (its k1–2 band is exactly 0.000000 at d=32, 128, and 256). gBCE's HEAD exceeds full-CE's at every rung. All three warm aggregates sit within ~8% of each other — the aggregate-blindness point of §6.6, again.

#### 6.8.1 The claim is bounded to lr = 1e-3

**This is the section's most important sentence, so it goes here and not in a limitations footnote: the pre-registered interaction — "capacity does not rescue gBCE's tail" — holds at lr = 1e-3 and does not hold at lr = 5e-4, and every use of it below is bounded accordingly.**

The pre-registered R1 sensitivity check (d=256, lr 5e-4, n=3) showed that lowering LR moves full-CE's head +0.009996 (CI excl. 0, 3/3; 0.1010 → 0.1110) and its tail −0.002301 (CI excl. 0, 0/3), while gBCE is LR-insensitive in every band; the d=256 tail gap attenuated ~2.5× (−0.004647 → −0.001851, n=3 CI [−0.004660, +0.000959]). We then re-ran the full ladder at lr = 5e-4 as amendment A2 — **declared post-hoc in origin in the prereg itself**, with its prediction and decision rule frozen before the 54 new cells ran. The frozen prediction (H2 attenuates but stays negative) was too optimistic: H2 at lr = 5e-4 is −0.000036, CI [−0.000541, +0.000469], 2/5 seeds positive — not supported, and not even sign-consistent. Per the frozen rule, the claim is bounded to lr = 1e-3, stated here and in the abstract, and both LRs are reported side by side (Table 7).

The mechanism is visible in the raw ratios: at lr = 5e-4 gBCE's tail *catches up* with scale (gBCE/fCE tail ratio 6.3% → 17.3% → 39.5% → 49.1% across d=32→256, monotone) while at lr = 1e-3 there is no trend (18.0% / 46.4% / 29.9% / 22.2%). Whether capacity rescues gBCE's tail is itself LR-dependent — the interaction has its own interaction.

**Table 7. The two-LR contrast (MI, n = 5 per LR, paired by seed).**

| endpoint | lr = 1e-3 | lr = 5e-4 | verdict |
|---|---|---|---|
| H1 gate (fCE relative tail − head slope) | +0.3865 ± 0.1337, 5/5 | +0.4816 ± 0.1637, 5/5 | passes both (partial replication; §6.8.4) |
| H2: S_gBCE(TAIL) − S_fCE(TAIL) | **−0.000777**, CI [−0.001427, −0.000127], 0/5 pos. | −0.000036, CI [−0.000541, +0.000469], 2/5 pos. | **supported at 1e-3 only; claim bounded** |
| H3: S_sCE(TAIL) − S_fCE(TAIL) | −0.000024, CI [−0.000260, +0.000213] | −0.000027, CI spans 0 | null holds at both LRs on MI — then fails on Steam (§6.8.2) |
| gBCE/fCE tail ratio by rung | 18.0 / 46.4 / 29.9 / 22.2% (no trend) | 6.3 / 17.3 / 39.5 / 49.1% (monotone catch-up) | capacity rescue is LR-dependent |
| H4 amplification, worst rung | 6.05× (d=256), CI on amp−5 spans 0 → failed | d128 estimate 69.69× (denominator → 0) | estimator unusable as specified (§6.8.4) |

#### 6.8.2 Steam external replication: the β-attribution claim is withdrawn

Steam (3 losses × d ∈ {64, 256} × 3 seeds) was launched to replicate what had survived A2. Three outcomes:

1. **The level effect transfers.** gBCE's tail is 78.7% of full-CE's at d=64 and 42.8% at d=256 (diffs −0.000340, CI [−0.000472, −0.000209] and −0.003493, CI [−0.005606, −0.001380]; 0/3 seeds positive at both rungs). Weaker than MI's 6–49%, but the direction holds off Amazon.
2. **H3 is refuted, decisively and in the opposite direction.** sCE − fCE on the tail is +0.004979 at d=64 and +0.003820 at d=256, both CIs excluding zero, 3/3 seeds positive at both rungs: on Steam, cutting negatives ~12k → 256 makes the tail roughly 4× *better* (fCE 0.001601 vs sCE 0.006580 at d=64). The MI null that licensed "the damage is β, not negative count" does not travel, so **the β-attribution claim of §6.6.1, as a general claim, is withdrawn**; it stands only as an MI result. (One caution flag: fCE's Steam tail jumps 3.8× from d=64 to d=256, 0.001601 → 0.006110, which merits an undertraining check before the d=64 fCE cell is leaned on.)
3. **Aggregate-blindness selectivity is MI-specific.** On Steam gBCE's aggregate warm is 0.1118 vs fCE's 0.1495 at d=64 — a −25% hit that no aggregate metric would miss — and the amplification factors are 0.8× (d=64) and 4.7× (d=256), both below the 5× bar. On MI, gBCE was *selectively* worse on the tail under a flat aggregate; on Steam it is simply worse everywhere. The deployable-instrument version of H4 is therefore not portable.

#### 6.8.3 Reinterpreting our own H3: bounding, not refuting, sampled-softmax theory

Wu et al. (TOIS, arXiv:2201.02327) argue theoretically that sampled softmax *mitigates* popularity bias and benefits the long tail, because frequent items are drawn as negatives more often and are penalized accordingly. Our Steam result is that prediction, realized at 4×. Under that reading, MI's H3 was never a clean attribution control: it was a dataset on which the theoretically predicted tail benefit of sampling *failed to appear*. The honest statement of the whole sampled-CE arm is therefore: we reproduce Wu et al.'s prediction on Steam and fail to reproduce it on MI, which bounds their claim rather than refuting it — and we did not design for that question. A candidate mechanism, stated but not tested here: the sampling rate α = K/(n_items−1) differs 2× between the ladders (MI 256/24,586 = 0.0104; Steam 256/~12k ≈ 0.0213), and β with it (0.2578 vs ≈0.266) — β is constant within each ladder but not across them. This dataset-conditionality also connects to Ferrari et al. (arXiv:2410.17276), who report that whether negative sampling balances popularity bands is dataset-dependent; our contribution here is only the sampled-vs-*full* contrast and the observed sign reversal, logged as a boundary condition, not opened as a campaign.

#### 6.8.4 Limitations and corrections (appended to the §8 log as entries 9–11)

**(9) Estimand inconsistency inside our own prereg.** H1 was pre-registered on relative slopes, H2 on absolute — an inconsistency we introduced and must own. On *relative* slopes the H2 contrast is +0.070, CI [−0.270, +0.410], 3/5 positive: gBCE's mean relative tail slope (0.3862) is if anything above full-CE's (0.3161). The defensible bounded claim is: **gBCE's tail does scale proportionally, but from a base so suppressed that it never converts into absolute rankability within this ladder.** The claim "gBCE's tail does not scale" is not supported and is not made. **(10) The β-attribution withdrawal** of §6.8.2. **(11) H4's estimator is broken by construction:** a ratio whose denominator (the aggregate gBCE−fCE gap) approaches zero blows up — d128 returned 38.93× at lr=1e-3 and 69.69× at lr=5e-4. It failed as specified at lr=1e-3, "passed" meaninglessly at lr=5e-4, and needs a redesign (difference-in-log-ratios or a bootstrap) before reuse. Finally, the head slope is *negative* for all three losses (fCE head 0.1202 at d=32 → 0.0998 at d=256), so H1 passes partly because the head declines: we replicate Zhang et al.'s differential but not their uniform-improvement claim, and R1 shows the head/tail split moves with LR — the partial replication is entangled with tuning, exactly the failure mode arXiv:2606.05257 documents at far larger scale, where the val-loss↔recall correlation flips sign with compute.

#### 6.8.5 What survives, and what the wreckage is worth

One result survives every configuration tested: **the level effect.** gBCE's tail band sits at 6–79% of full-CE's in every cell — all 8 MI cells (4 rungs × 2 LRs; 0/5 seeds positive in each, 40/40 seed-runs) and both Steam rungs (0/3 each) — with the difference CI excluding zero in 7 of 8 MI cells and both Steam cells. That is consistent with §6.6.1's mechanism at the level of *levels*, and with arXiv:2607.21101's independent finding that cold reachability is bounded by training token support in a third architecture family; it is also, on Steam, not selective, which reduces there to "gBCE is worse than full-CE" — a comparison gSASRec's own paper never makes (their baseline is sampled BCE) and which therefore contests nothing they claim.

Everything else — the scale×loss interaction, the β attribution, the amplification instrument, the clean replication of tail-favoring scaling — died under a second learning rate or a second dataset. We report that not as an apology but as the section's second finding: **three of four headline claims were regime-dependent, and each was invisible at the configuration where it was first measured.** A single-LR, single-dataset, aggregate-metric evaluation would have shipped all four. That is this paper's thesis, applied to ourselves.

---

*Word count (prose, excluding tables and header): ~1,290.*
