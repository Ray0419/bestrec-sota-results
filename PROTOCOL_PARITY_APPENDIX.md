# Protocol-Parity Appendix (Codex audit fix #7)

Evidence that our reproduced AR2023 Musical_Instruments protocol matches the comparator paper
(HSTU-BLaIR; Liu 2025, arXiv:2504.10545), and why a comparator rerun is infeasible here.

## 1. Dataset identity

| statistic | HSTU-BLaIR paper (MI) | ours (from run manifests) |
|---|---:|---:|
| users | 57,439 | 57,439 (n_eval = all users, every run) |
| items | 24,587 | 24,587 |
| interactions | 511,835 | 511,836 = train 396,958 + valid 57,439 + test 57,439 |

(User/item counts match exactly; the interaction total differs by exactly one. Investigated
2026-07-08 — our 511,836 rows contain zero duplicate rows and zero duplicate (user,item) pairs,
so the ±1 originates on the comparator paper's side of the counting; immaterial to LLOO since
both pipelines evaluate exactly one target per user for the identical 57,439 users. Full
statement: `SOTA_CONFIRM_PREREG_V2_ERRATA.md` E1.) Source: Amazon Reviews 2023 (Hou et al.
2024), official category dump.

## 2. Preprocessing / split

- 5-core filtering via `preprocess_5core_standard.py`, which mirrors the official
  `hyp1231/AmazonReviews2023` kcore script (iterative user+item 5-core, timestamp-ordered).
- Leave-last-out: last interaction per user = test, second-last = valid, rest = train;
  (user,item) dedup keep-earliest before splitting.
- Frozen split hashes (embedded in every V2 run manifest and pre-registered in
  `SOTA_CONFIRM_PREREG_V2.md`):
  train `1f56c4ab…f9dba`, valid `f1240768…d76bc`, test `19f3ed96…da36a`,
  text cache `40697924…ed90b`.

## 3. Evaluation parity

Full-catalog masked ranking: score all 24,587 items, mask the user's full seen history
(train+val), rank the held-out test item; NDCG@10 = 1/log2(rank+2), 0-indexed rank; HR@10.
This matches the comparator repo's eval (`generative_recommenders/research/data/eval.py` —
full-catalog brute-force top-k with seen-item filtering; verified at source level 2026-06-13).
All 57,439 users evaluated (no sampling, no stratification) in every gated run.

## 4. Cross-checks that our split is not easier

- Our plain ID-only SASRec on this MI split: NDCG@10 **0.0264** — well BELOW the paper's
  published MI SASRec (0.0356). An easier split would inflate, not deflate, a weak baseline.
- On Video_Games (same pipeline), our SASRec reproduces their published SASRec within 4%
  (0.0551 vs 0.0573), and our best model (0.0673) remains 11% BELOW their published
  HSTU-BLaIR (0.0760) — the pipeline does not systematically inflate.

## 5. Why the comparator cannot be rerun here (stated limitation, Codex fix #6)

The official HSTU-BLaIR implementation pins `torch==2.2.2+cu121`, `fbgemm_gpu==0.6.0`,
`torchrec==1.1.0` + Triton HSTU kernels. On this machine's Blackwell GPU (sm_120) that stack
fails with "CUDA error: no kernel image is available for execution on the device" — reproduced
inside WSL Ubuntu with their pinned environment (SOTA_VERDICT.md §5, 2026-06-14). Therefore no
comparator seed-distribution or paired user-level test is possible on this hardware, and every
claim is capped at "exceeds the published point estimate" (wording frozen in the prereg).

## 6. 2026 literature positioning (Codex fix #9)

- **ReSID** (arXiv:2602.02338): semantic-ID generative retrieval; reports MI NDCG@10 = 0.0346
  under its own filtering/statistics — different setup, lower number; not directly comparable.
- **ChronoSID** (arXiv:2607.03918, 2026-07-04): improves over ReSID on MI within the SID
  protocol (NDCG@10 0.0346, five-run average); again a different filtered universe.
- **TIGER / LIGER**: evaluate on Amazon 2014, not AR2023 (verified in CITATION_AUDIT.md); not
  comparable.
- Positioning: our claim is confined to the **HSTU-BLaIR protocol family** (AR2023 5-core LLOO
  full-catalog), where 0.0406 is the strongest published MI number we know of; SID-family
  results under different filtering are cited and discussed, not claimed against.

## 7. Obtaining the ignored data/cache artifacts (clean-clone reproduction, audit R5)

`data_5core/` and `cache_5core/` are git-ignored (size). A fresh clone regenerates them:

1. **Raw data:** download the `Musical_Instruments` reviews + metadata from the official Amazon
   Reviews 2023 release (Hou et al. 2024, `hyp1231/AmazonReviews2023` / McAuley Lab HF datasets).
2. **Splits:** run `preprocess_5core_standard.py Musical_Instruments` (mirrors the official kcore
   script) → the three CSVs; verify against the frozen SHA256s in `SOTA_CONFIRM_PREREG_V2.md`
   (train `1f56c4ab…`, valid `f1240768…`, test `19f3ed96…`) — hash equality guarantees the
   identical split.
3. **Text cache:** run `_bestrec_run/run_5core_benchmark.py --encode-titles` (MiniLM/SBERT
   `all-MiniLM-L6-v2`) → `cache_5core/sbert_titles_Musical_Instruments.npy`; verify SHA256
   `40697924…`.
4. **Rebuild:** `OUTDIR=_bestrec_run/rebuild_v2 bash _bestrec_run/run_sota_confirm_v2.sh`
   regenerates all 10 runs from scratch (no skip shortcut) and adjudicates them.
