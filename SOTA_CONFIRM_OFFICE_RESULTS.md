> **ERRATUM (2026-07-20).** The pooled two-proportion z statistics recorded below are
> **retracted as inference** (2026-07-19, audit 22:08): the same 36,610 tail users are
> evaluated under every seed and both arms, so the seed-summed rows are clustered repeated
> observations, not independent trials. The counts stand as descriptive record; the valid
> model-seed-level analysis is in the manuscript (independent-arm Welch; graph cells
> `office.tailwelch.*`). This record is preserved unmodified below.



> **FINAL STATUS: OFFICE IS VOID UNDER THE PRE-REGISTERED FLOOR CHECK.** Any
> `P2 DUAL GATE: PASS` lines below are arithmetic-only historical append blocks
> (both CI lower bounds > 0.0271) and are **not claim approvals**. The floor check
> failed (+44% above the published SASRec 0.0153); the anomaly is mechanistically
> explained (`THEIRS_ON_OURS_REPORT.md` §4.1, paper Appendix A.0) and the VOID is
> deliberately retained. Nothing in this file counts Office as a confirmatory pass.

## STATS + P1 PREDICTION (recorded BEFORE any training run)

- splits sha256: train `95d3db37ab29157c...` valid `a0bd9331846c56e0...` test `92a9a602dd6fa73c...`
- full hashes: train 95d3db37ab29157c4e6922270a282f72c43c3c4ccd01cd95385aa852d1469c58 / valid a0bd9331846c56e005d13911f785fcf79938284bb81d04dd72a1b9bb75ca8876 / test 92a9a602dd6fa73c3271ed69d37da5c7e8c63ecb1a928ab59c5085af4188c1ed
- text cache sha256: MISSING
- n interactions: train 1,354,262 / valid 223,308 / test 223,308 (total 1,800,878); n_users(test rows) = 223,308; n_items(train) = 77,225
- **U = mean distinct users/item (TRAIN) = 17.537**
- **P1 mechanical application: PREDICT tail Delta ~ 0 / null (VG/Beauty-like regime)** (rule frozen in SOTA_CONFIRM_PREREG_OFFICE.md; reference points MI 2.34 / VG 3.70 / Beauty 3.51)

### CORRECTION 2026-07-11 — U-definition inconsistency in the stats tool (disclosed, not papered over)

The prereg's P1 text defines U as "mean distinct-users-per-item," and the stats tool computed
exactly that from train interactions (U = 17.537). However, the prereg's own REFERENCE POINTS
(MI 2.34 / VG 3.70 / Beauty 3.51) are unambiguously **n_users/n_items ratios** — the campaign's
original connectivity metric — making the rule internally inconsistent as written. Under the
reference-consistent formula, Office = 223,308 / 77,225 = **2.89**, which falls in the
pre-declared **VOID zone [2.5, 3.0)**. Both readings agree on the operative point (NO tail win
is predicted for Office); the discrepancy changes only whether P1 is scored as "predicted null"
(tool's literal formula) or "VOID/unscored" (reference-consistent formula). Per the
strictest-interpretation principle, **P1 for Office is scored as VOID** — the out-of-sample
prediction test remains decided by the MI/VG/Beauty triple plus any future category falling
OUTSIDE the ambiguous zone. The tail contrast is still run and reported descriptively.
Also recorded: the text-encode step initially failed (missing Office metadata mapping in
`run_5core_benchmark.py`; fixed and re-run), so the k16/k8 gate arms execute after the ID-only
arm rather than before it — arm ORDER carries no significance (config and seeds unchanged).

## ADJUDICATION
- ARM k16 seed 20260623: MISSING
- ARM k16 seed 20260624: MISSING
- ARM k16 seed 20260625: MISSING
- ARM k16 seed 20260626: MISSING
- ARM k16 seed 20260627: MISSING
- ARM k8 seed 20260623: MISSING
- ARM k8 seed 20260624: MISSING
- ARM k8 seed 20260625: MISSING
- ARM k8 seed 20260626: MISSING
- ARM k8 seed 20260627: MISSING
- floor SASRec NDCG@10 = 0.02208 (published SASRec 0.0153; must not be far ABOVE it)

**P2 DUAL GATE: FAIL**

## STATS + P1 PREDICTION (recorded BEFORE any training run)

- splits sha256: train `95d3db37ab29157c...` valid `a0bd9331846c56e0...` test `92a9a602dd6fa73c...`
- full hashes: train 95d3db37ab29157c4e6922270a282f72c43c3c4ccd01cd95385aa852d1469c58 / valid a0bd9331846c56e005d13911f785fcf79938284bb81d04dd72a1b9bb75ca8876 / test 92a9a602dd6fa73c3271ed69d37da5c7e8c63ecb1a928ab59c5085af4188c1ed
- text cache sha256: 48d2b660f7fec56d37c6d418297db6bb9a308d2f664b1ceb5a8f0bb2f5c157e4
- n interactions: train 1,354,262 / valid 223,308 / test 223,308 (total 1,800,878); n_users(test rows) = 223,308; n_items(train) = 77,225
- **U = mean distinct users/item (TRAIN) = 17.537**
- **P1 mechanical application: PREDICT tail Delta ~ 0 / null (VG/Beauty-like regime)** (rule frozen in SOTA_CONFIRM_PREREG_OFFICE.md; reference points MI 2.34 / VG 3.70 / Beauty 3.51)

## ADJUDICATION
- **ARM k16**: ['0.03104', '0.03169', '0.03193', '0.03152', '0.03148'] mean 0.03153 sd 0.00033 CI-LB 0.03113 (5/5 > 0.0271) -> PASS
- **ARM k8**: ['0.03169', '0.03166', '0.03163', '0.03175', '0.03151'] mean 0.03165 sd 0.00009 CI-LB 0.03154 (5/5 > 0.0271) -> PASS
- **P1 tail contrast (pooled hits text vs id)**: @10: 37 vs 35 (z=0.24, p=0.8135)  @20: 64 vs 53 (z=1.02, p=0.3086)  @50: 154 vs 89 (z=4.18, p=0.0000)  @100: 263 vs 174 (z=4.28, p=0.0000)  
- floor SASRec NDCG@10 = 0.02208 (published SASRec 0.0153; must not be far ABOVE it)

**P2 DUAL GATE: PASS**

## ADJUDICATION
- **ARM k16**: ['0.03104', '0.03169', '0.03193', '0.03152', '0.03148'] mean 0.03153 sd 0.00033 CI-LB 0.03113 (5/5 > 0.0271) -> PASS
- **ARM k8**: ['0.03169', '0.03166', '0.03163', '0.03175', '0.03151'] mean 0.03165 sd 0.00009 CI-LB 0.03154 (5/5 > 0.0271) -> PASS
- **P1 tail contrast (pooled hits text vs id)**: @10: 37 vs 35 (z=0.24, p=0.8135)  @20: 64 vs 53 (z=1.02, p=0.3086)  @50: 154 vs 89 (z=4.18, p=0.0000)  @100: 263 vs 174 (z=4.28, p=0.0000)  
- floor SASRec NDCG@10 = 0.02208 (published SASRec 0.0153; must not be far ABOVE it)

**P2 DUAL GATE: PASS**

## FINAL ADJUDICATION — prereg-compliant headline (final-epoch FULL-catalog eval; supersedes the earlier best_test-based sections above)
- **ARM k16**: ['0.03041', '0.03055', '0.03042', '0.03031', '0.03043'] mean 0.03042 sd 0.00008 CI-LB 0.03032 (5/5 > 0.0271) -> PASS
- **ARM k8**: ['0.03035', '0.03036', '0.03048', '0.03043', '0.03002'] mean 0.03033 sd 0.00018 CI-LB 0.03010 (5/5 > 0.0271) -> PASS
- **P1 tail contrast (pooled hits text vs id)**: @10: 364 vs 268 (z=3.82, p=0.0001)  @20: 586 vs 414 (z=5.45, p=0.0000)  @50: 1170 vs 739 (z=9.89, p=0.0000)  @100: 1983 vs 1247 (z=13.01, p=0.0000)  
- floor SASRec NDCG@10 = 0.02208 (published SASRec 0.0153; must not be far ABOVE it)

**P2 DUAL GATE: PASS**

## FINAL ADJUDICATION — prereg-compliant headline (final-epoch FULL-catalog eval; supersedes the earlier best_test-based sections above)
- **ARM k16**: ['0.03041', '0.03055', '0.03042', '0.03031', '0.03043'] mean 0.03042 sd 0.00008 CI-LB 0.03032 (5/5 > 0.0271) -> PASS
- **ARM k8**: ['0.03035', '0.03036', '0.03048', '0.03043', '0.03002'] mean 0.03033 sd 0.00018 CI-LB 0.03010 (5/5 > 0.0271) -> PASS
- **P1 tail contrast (pooled hits text vs id)**: @10: 364 vs 268 (z=3.82, p=0.0001)  @20: 586 vs 414 (z=5.45, p=0.0000)  @50: 1170 vs 739 (z=9.89, p=0.0000)  @100: 1983 vs 1247 (z=13.01, p=0.0000)  
- floor SASRec NDCG@10 = 0.02208 (published SASRec 0.0153; must not be far ABOVE it)

**P2 DUAL GATE: PASS**

## CONTEXT NOTE for the two FINAL ADJUDICATION blocks above (2026-07-11)

The two identical blocks above were appended by successive `office_prereg_tools.py adjudicate`
runs (the tool appended unconditionally; it is now idempotent and its output now carries a VOID
banner). Read them with the overall verdict in view: **"P2 DUAL GATE: PASS" is the gate
arithmetic only** (both CI-LBs > 0.0271). The pre-registration as a whole is **VOID** — the floor
line printed inside each block is the reason (0.02208 sits +44% ABOVE the published 0.0153,
violating the comparability condition). The floor anomaly has since been resolved mechanistically:
the reference implementation's own Office SASRec, run locally end-to-end on its own pipeline,
lands **+13.9% above its published row** (final-epoch NDCG@10 0.0174 vs 0.0153), decomposing the
+44% into published-row conservatism (+13.9%) x baseline-strength protocol differences (+16.9%) —
`THEIRS_ON_OURS_REPORT.md` §4.1 and the paper's Appendix A.0. Because that implies the published
HSTU-BLaIR Office row (0.0271) is plausibly conservative here as well, **the VOID is deliberately
retained**: the gate values remain provisional/descriptive, never a confirmatory pass.

## FINAL ADJUDICATION — prereg-compliant headline (final-epoch FULL-catalog eval; supersedes the earlier best_test-based sections above)
> NOTE: 'P2 DUAL GATE' below reports the gate ARITHMETIC only (CI-LBs vs 0.0271). The pre-registration as a whole is VOID — the floor check failed (+44% above the published SASRec; anomaly explained and VOID deliberately retained, see THEIRS_ON_OURS_REPORT.md S4.1 and the paper's Appendix A.0). Gate values are provisional/descriptive, never a confirmatory pass.
- **ARM k16**: ['0.03041', '0.03055', '0.03042', '0.03031', '0.03043'] mean 0.03042 sd 0.00008 CI-LB 0.03032 (5/5 > 0.0271) -> PASS
- **ARM k8**: ['0.03035', '0.03036', '0.03048', '0.03043', '0.03002'] mean 0.03033 sd 0.00018 CI-LB 0.03010 (5/5 > 0.0271) -> PASS
- **P1 tail contrast (pooled hits text vs id)**: @10: 364 vs 268 (z=3.82, p=0.0001)  @20: 586 vs 414 (z=5.45, p=0.0000)  @50: 1170 vs 739 (z=9.89, p=0.0000)  @100: 1983 vs 1247 (z=13.01, p=0.0000)  
- floor SASRec NDCG@10 = 0.02208 (published SASRec 0.0153; must not be far ABOVE it)

**P2 DUAL GATE: PASS**
