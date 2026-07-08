# PRE-REGISTRATION V2 — immutable, audit-proof confirmation (Musical_Instruments)

**Rule zero: this file is NEVER edited after the git commit that introduces it.** Results are
recorded in a separate file (`SOTA_CONFIRM_V2_RESULTS.md`). The provenance chain is: this file is
part of commit `<the commit introducing this file — see git log>`; every V2 result JSON embeds a
`provenance` manifest whose `git_commit` must equal that commit and whose `git_dirty_tracked`
must be `false`. Any mismatch voids the run.

Written in response to `CLAUDE_SOTA_RESULT_AUDIT_2026-07-08.md` (Codex), which rejected the V1
claim for non-auditable preregistration (F1), missing artifact provenance (F2), and overstated
wording (F3/F5). Seeds 20260608–17 are hereby classed as consumed exploratory evidence and are
NOT part of this confirmation.

## Frozen protocol

- **Dataset:** Amazon Reviews 2023 `Musical_Instruments`, 5-core, leave-last-out, full-catalog
  masked evaluation, NDCG@10, all 57,439 users (`eval_subsample=0`, no stratification).
  Data files are frozen by SHA256 (verified in every run's manifest):
  - `Musical_Instruments.train.csv` = `1f56c4abf0515e59090d728174db6b35ffa97f06929a0f955f2be924560f9dba`
  - `Musical_Instruments.valid.csv` = `f1240768bd813fe84620fdff9d91c1055f560f51be42cf8ae9de45d7ee8d76bc`
  - `Musical_Instruments.test.csv`  = `19f3ed965a5adafec9f55575cdbe113556ae5ee156e41591da364cfb89cda36a`
  - `sbert_titles_Musical_Instruments.npy` = `406979249f4f89cb14d520bf9ca33994763e9caffd215280bb5f5ee7a49ed90b`
  - n_users=57,439 · n_items=24,587 · interactions: train 396,958 / valid 57,439 / test 57,439
    (matches the comparator paper's reported 511,835 total and its users/items table).
- **Comparator:** published HSTU-BLaIR point estimate NDCG@10 = **0.0406** on the same
  category/protocol (Liu 2025, arXiv:2504.10545, single seed). Its reference implementation
  cannot execute on this GPU (sm_120; "no kernel image" — proven via WSL, see SOTA_VERDICT.md §5),
  so no comparator rerun/distribution is possible; the claim is therefore capped at
  "exceeds the published point estimate" (wording frozen below).
- **Model config (both arms, identical except kernel):** epochs 20, batch 256, d_model 64,
  n_layers 4, n_heads 2, dropout 0.5, lr 1e-3 warmup_cosine, encoder hstu,
  chunked-full-softmax (item-chunk 32768), time-bias, text-sim-bias, text-prototypes 512,
  pos-rab, label-smoothing 0.2, causal-filter, eval-every 1.
- **Fresh seeds (never inspected in any prior run/decision):** **20260618, 20260619, 20260620,
  20260621, 20260622** — the next consecutive integers after the consumed range; no seed shopping
  is possible by construction.
- **Exact command (arm ∈ {16, 8}; seed ∈ the five above):**
  ```
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Musical_Instruments \
    --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
    --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu \
    --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 \
    --causal-filter --filter-kernel <ARM> --eval-every 1 --seed <SEED> \
    --out _bestrec_run/results_SOTACONF_V2_k<ARM>_MI_seed<SEED>.json
  ```
  Driver: `_bestrec_run/run_sota_confirm_v2.sh` (committed alongside this file).
- **Artifacts per run:** the result JSON (with the embedded provenance manifest: created_at,
  argv, git commit+branch+dirty flag, python/torch/GPU, data SHA256s, interaction counts,
  best-val epoch) and the per-user record sidecar
  `results_SOTACONF_V2_k<ARM>_MI_seed<SEED>.users.jsonl.gz`
  (dataset, seed, user_id, target_item_id, rank0, ndcg10, hr10, rr, pop_bucket; retained on disk,
  SHA256s recorded in the results file).

## Pre-registered decision rule (frozen before any V2 run)

- **PRIMARY (DUAL) GATE:** BOTH arms must pass independently —
  k16 fresh 5-seed mean − 2.776·sd/√5 > 0.0406 **AND** k8 fresh 5-seed mean − 2.776·sd/√5 > 0.0406
  (two-sided 95% t-interval lower bound, df=4). Dual so the claim is kernel-choice-free.
- **SECONDARY:** ≥ 4/5 seeds individually > 0.0406 in each arm.
- **Analysis is fixed:** best-by-val (overall val NDCG@10) per run, as in every prior run; no
  alternative checkpoint/metric/subset may be substituted after seeing results.
- **If the gate PASSES:** the ONLY claim made is the frozen wording below.
- **If the gate FAILS (either arm):** the claim is permanently retired to "statistical near-tie
  with the published single-seed point estimate"; no further confirmation attempts on this
  category (seeds are then consumed; the program ends with the negative recorded).

## Frozen claim wording (verbatim; nothing stronger may be published)

> Our five-seed mean and seed-level 95% confidence interval exceed the published HSTU-BLaIR
> point estimate (NDCG@10 = 0.0406; Liu 2025, arXiv:2504.10545) on Amazon Reviews 2023
> Musical_Instruments under our reproduced 5-core leave-last-out full-catalog protocol, for both
> filter kernels K=8 and K=16. The comparator is a single-seed published number whose reference
> implementation cannot execute on our hardware; no paired or distributional comparison is
> possible, and this is a per-category point-estimate comparison, not a general SOTA claim.
> Newer 2026 semantic-ID methods (ReSID, ChronoSID) report under different filtering/protocols
> and are discussed, not claimed against.

## Committed context

- Codebase state: the commit introducing this file (manifests must match it, dirty=false).
- Protocol parity + comparator-infeasibility evidence: `PROTOCOL_PARITY_APPENDIX.md`.
- Literature positioning (ReSID, ChronoSID, TIGER/LIGER): `PAPER_DRAFT.md` related-work update.
- Clean-rebuild script: `_bestrec_run/run_sota_confirm_v2.sh` (idempotent; regenerates all 10
  runs + summary from a clean checkout with data present).
