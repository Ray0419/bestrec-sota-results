# Revision Plan

**Audit time:** 2026-06-08 12:31:01 +10:00

## Submission Decision

Current status: **reject as a final SOTA paper; revise as a narrow,
protocol-qualified workshop paper**.

The results are useful, but the manuscript cannot pass a strict review until
the remaining attribution, protocol, and statistical gates are closed.

## Required Fixes Before Any Submission

1. **Regenerate the old BEST-Rec PDF or retire it.**
   - The current PDF does not cite the modern components used in the current
     experiments.
   - Editable source was not found, so the safe path is to create a new
     manuscript source and generated PDF.

2. **Lock external comparator protocols.**
   - For TIGER, BLaIR, and LIGER, record exact paper table, dataset variant,
     preprocessing, candidate scope, split, and metric definition.
   - If those do not match the repository's 5-core full-catalog protocol, use
     "strong internal baseline" or "target-range comparison", not "beats".

3. **Add per-user statistical records.**
   - Aggregate JSON files are insufficient for final Wilcoxon/bootstrap claims.
   - Future runs must write per-user records with `user_id`, `target_item_id`,
     `seed`, `method`, `candidate_scope`, `ndcg10`, `hr10`, and `rr`.

4. **Complete matched multi-seed Beauty confirmation or keep it negative.**
   - The Beauty BLaIR-rich-text/MLP improvement is small.
   - It cannot be presented as significant without matched baseline seeds and
     per-user paired tests.

5. **Make all component attribution explicit.**
   - Keep `_bestrec_run/CITATIONS.md`.
   - Keep attribution paragraphs in code, reports, and paper drafts.
   - Do not call the Hou et al. SASRecText adaptor a new local method.

6. **Archive exact commands and environment.**
   - Every publishable result must include command, seed, git commit, Python/
     CUDA/PyTorch versions, GPU model, input data hashes, and output hashes.

7. **Run final manuscript QA.**
   - Verify all tables are generated from JSON artifacts.
   - Verify no stale notebook/cache results are used.
   - Run external plagiarism/similarity checking on the final PDF.

## Feasible Next Experiment Plan

If the goal remains a stronger paper rather than a guarded short paper:

1. Re-run Video_Games with five fresh seeds, complete per-user JSONL records,
   and a manifest.
2. Re-run exact, faithful TIGER/BLaIR/LIGER comparators or reproduce their
   preprocessing/evaluation from public code.
3. For Beauty, either:
   - keep the negative result as evidence of a scaling limit, or
   - run a multi-week semantic-ID / generative retrieval reproduction instead
     of further small SASRec tweaks.

## Acceptance Gate

A strict approval requires:

- No unattributed borrowed component.
- No approximate leaderboard number used as final evidence.
- No missing seed/command/environment metadata for claimed results.
- No aggregate-only statistical claim.
- No Beauty significance claim without matched per-user tests.
- No broad SOTA claim unless the full comparator suite is apples-to-apples.
