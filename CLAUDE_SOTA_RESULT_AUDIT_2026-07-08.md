# Strict Audit Of Claude's SOTA Claim

Audit time: 2026-07-08 10:31:00 +10:00  
Auditor stance: hostile reviewer / publication gatekeeper  
Claim under audit: `SOTA_ACHIEVED.md` says a scoped SOTA result is achieved on Amazon Reviews 2023 `Musical_Instruments` 5-core leave-last-out full-catalog masked NDCG@10.

## Decision

**Reject as a publication-grade SOTA claim in its current form.**

The local arithmetic supports a much narrower statement:

> On this local reproduced `Musical_Instruments` split, five fresh `SOTACONF_k16` seeds produce mean NDCG@10 = 0.04151 with a seed-level 95% t-interval [0.04111, 0.04191], above the published HSTU-BLaIR point estimate 0.0406.

That is promising and probably real as a local experimental result. It is **not yet enough** for a top-conference or top-journal SOTA claim because the result lacks an auditable preregistration/source/data manifest, compares against a single-seed external point estimate rather than a rerun comparator distribution, and has a very thin margin.

## Audited Claim

`SOTA_ACHIEVED.md` claims:

- Dataset/protocol: Amazon Reviews 2023 `Musical_Instruments`, 5-core, leave-last-out, full-catalog masked evaluation.
- Comparator: HSTU-BLaIR, NDCG@10 = 0.0406, from Liu 2025 / arXiv:2504.10545.
- Our method: HSTU encoder + frozen SBERT features + TAPE-512 + time/text-sim/positional biases + causal spectral FIR filter K=16 + label smoothing.
- Result: NDCG@10 = 0.04151 +/- 0.00033 over five fresh seeds 20260613-20260617, 95% CI [0.04111, 0.04191].
- Caveats already admitted: one category only, comparator single seed, K16 not statistically better than K8, thin margin.

## What I Verified Locally

I recomputed the headline seed aggregation from:

- `_bestrec_run/results_SOTACONF_k16_MI_seed20260613.json`
- `_bestrec_run/results_SOTACONF_k16_MI_seed20260614.json`
- `_bestrec_run/results_SOTACONF_k16_MI_seed20260615.json`
- `_bestrec_run/results_SOTACONF_k16_MI_seed20260616.json`
- `_bestrec_run/results_SOTACONF_k16_MI_seed20260617.json`

| Seed | n_eval | NDCG@10 | HR@10 | Best-val epoch |
|---:|---:|---:|---:|---:|
| 20260613 | 57,439 | 0.0411129595 | 0.0742875050 | 10 |
| 20260614 | 57,439 | 0.0418372857 | 0.0754191403 | 18 |
| 20260615 | 57,439 | 0.0417695304 | 0.0742352757 | 16 |
| 20260616 | 57,439 | 0.0416054300 | 0.0752102230 | 15 |
| 20260617 | 57,439 | 0.0412222277 | 0.0744267832 | 12 |

Recomputed aggregate:

- Mean NDCG@10: **0.0415094867**
- Sample SD: **0.0003255885**
- 95% t-interval with df=4: **[0.0411052151, 0.0419137582]**
- Minimum seed: **0.0411129595**
- All five seeds exceed 0.0406: **yes**

I also verified that each saved `best_test` value corresponds to the epoch with the best validation NDCG in the JSON history. I did **not** find a test-checkpoint-selection bug in these five files.

## External Comparator Check

The cited HSTU-BLaIR comparator is real. The HSTU-BLaIR arXiv v3 paper reports Amazon Reviews 2023 `Musical Instruments` statistics of 24,587 items, 57,439 users, and 511,835 interactions, matching the local result files on users/items. The same paper reports `Musical Instruments` NDCG@10 values: SASRec 0.0356, HSTU 0.0392, HSTU-OpenAI 0.0393, and HSTU-BLaIR 0.0406. Source: [HSTU-BLaIR arXiv v3](https://arxiv.org/html/2504.10545v3).

However, current 2026 literature includes newer semantic-ID / generative retrieval methods that must be positioned carefully. ReSID reports MI NDCG@10 = 0.0346 under a different filtered setup and dataset statistics, not directly overturning the 0.0415 claim but clearly belonging in the SOTA discussion. Source: [ReSID arXiv](https://arxiv.org/html/2602.02338v1). ChronoSID, posted 2026-07-04, reports improvements over ReSID on MI with output-level NDCG@10 0.0345 under its own SID protocol. Source: [ChronoSID arXiv](https://arxiv.org/html/2607.03918v1).

## Evaluation-Code Check

The headline evaluation path in `_bestrec_run/run_sasrec_sbert.py` appears broadly correct for full-catalog next-item ranking:

- It scores the target against all item candidates.
- It appends validation history for test evaluation.
- It masks the user's full input history before ranking.
- It computes `rank0 = number of candidates with score > target_score`.
- It computes NDCG@10 as `1 / log2(rank0 + 2)` if `rank0 < 10`.
- The five result files have `eval_subsample = 0` and `eval_stratify_head = 0.0`, so the headline uses all 57,439 users.

I did not rerun the five training jobs from scratch during this audit. I only audited the saved artifacts and code.

## Blocking Findings

### F1. Preregistration is not auditable

`SOTA_CONFIRM_PREREG.md` says it was written on 2026-07-06 before the confirmation runs, but the local filesystem reports:

- `SOTA_CONFIRM_PREREG.md` creation/write time: 2026-07-08 10:21:54
- `SOTA_ACHIEVED.md` creation/write time: 2026-07-08 10:22:04
- result files: 2026-07-06 11:07:39 through 11:43:08

Both claim files are untracked by git. `git ls-files --stage` returns no tracked entry for them or the five result JSONs. A reviewer cannot distinguish true preregistration from after-the-fact reconstruction. This is a hard reject for any "pre-registered, selection-free" wording.

### F2. Result artifacts lack provenance

The result JSONs do not include the fields a publication-grade artifact needs:

- no `created_at`
- no command line
- no git commit or source hash
- no data/split hash
- no environment/machine manifest
- no raw interaction count in the JSON
- no immutable link between the result and the code state that produced it

The worktree is also dirty, with many modified and untracked files, including the training script. The result may be real, but the exact source state is not reconstructible.

### F3. Comparator statistics are insufficient for significance

The HSTU-BLaIR comparator is a published single-seed point estimate. Our five-seed CI above a fixed 0.0406 point is weaker than a statistical test against a comparator distribution. It does not establish paired user-level superiority over HSTU-BLaIR.

Acceptable wording is limited to:

> Our five-seed mean and seed-level confidence interval exceed the published HSTU-BLaIR point estimate.

It is not yet acceptable to say:

> Statistically significantly better than HSTU-BLaIR.

### F4. Margin is too small to survive protocol ambiguity

The lower CI margin over 0.0406 is about +0.000505 absolute. That is roughly a 1.2% relative margin over the comparator. A small split mismatch, preprocessing difference, tie-handling difference, train/eval epoch mismatch, or comparator rerun variance could erase it.

This is not fatal by itself, but it demands unusually strong reproducibility evidence. The current artifact trail does not provide that evidence.

### F5. SOTA scope is too broad in file naming and some phrasing

`SOTA_ACHIEVED.md` is too strong as a headline artifact. The actual support is:

- one Amazon Reviews 2023 category only,
- one metric only,
- against one published point estimate,
- not Video Games,
- not all Amazon Reviews 2023,
- not cold-start,
- not a broad recommender-systems SOTA claim.

The paper must call this **a per-category point-estimate comparison**, not a general SOTA result.

### F6. Current literature positioning is incomplete

The claim file cites HSTU-BLaIR but does not sufficiently position 2026 SID/generative retrieval work such as ReSID and ChronoSID. These papers appear to use different filtering and evaluation setups, so they do not directly refute the MI claim. But omitting them creates a reviewer opening: "not compared to current generative retrieval SOTA."

### F7. No clean rebuild evidence

There is no evidence that a clean checkout plus one documented command regenerates the five JSONs, the summary, and the claim file. A top venue will expect at least a scriptable manifest and ideally a clean rebuild log.

## Non-Blocking Positive Findings

- The five headline numbers recompute exactly from disk.
- Each headline file evaluates all 57,439 users.
- Users/items match the HSTU-BLaIR `Musical Instruments` table.
- The evaluation masking and NDCG formula look correct for single-target full-catalog ranking.
- K8 robustness reportedly also clears 0.0406 on seeds 20260613-20260617, reducing the concern that K16 alone was a knife-edge.

## Required Fixes Before I Would Approve

1. **Retire the current "pre-registered" claim.** Treat seeds 20260613-20260617 as consumed exploratory/confirmation evidence, not as audit-proof preregistration.

2. **Create a real immutable preregistration.** Commit or externally timestamp a new preregistration before any new run. It must include frozen code commit, exact command, seeds, dataset hash, decision rule, and no-edit rule.

3. **Run a fresh confirmatory sweep from a clean commit.** Use new seeds that have never been inspected. Do not reuse 20260613-20260617 as the decisive approval run.

4. **Generate a manifest for every run.** Required fields: command, start/end timestamp, git commit, dirty-state flag, full config, environment, GPU/CPU notes, package lock, raw data hashes, split hashes, result hash, n_users, n_items, n_interactions, and output path.

5. **Save per-user records.** At minimum: `dataset, seed, user_id, target_item_id, rank0, ndcg10, hr10, rr`. Without this, bootstrap audits and tie/rank diagnostics are crippled.

6. **Rerun or obtain the HSTU-BLaIR comparator distribution if possible.** A single external point estimate is not enough for a strong "significant improvement" claim. If the official implementation cannot run locally, run it on compatible hardware or state the limitation explicitly.

7. **Add a protocol-parity appendix.** Include preprocessing script hash, Amazon Reviews 2023 source version, 5-core procedure, split generation, item metadata filtering, and a table comparing users/items/interactions with HSTU-BLaIR.

8. **Update the claim language.** Use "exceeds the published HSTU-BLaIR point estimate on AR2023 Musical Instruments under our reproduced protocol" unless comparator reruns and paired statistics are completed.

9. **Discuss ReSID, ChronoSID, TIGER/LIGER-style methods.** Explain which are directly comparable and which differ in filtering/protocol. Do not imply they do not exist.

10. **Run a clean rebuild test.** From a clean clone, execute one documented script that regenerates results, summary tables, and the paper artifact.

## Approval Boundary

I would approve a narrow, honest claim after the fixes if the fresh clean-confirmatory run still clears the HSTU-BLaIR point estimate and the paper states the comparator limitation plainly.

I would not approve the current phrase "SOTA ACHIEVED - scoped, pre-registered, selection-free" because the preregistration and artifact provenance are not currently audit-proof.

## Final Verdict

**Reject for now.**

The numbers are encouraging. The paper should not claim publication-grade SOTA until the experiment is rerun from an immutable preregistration with a manifest, clean source state, per-user records, and a defensible comparator story.
