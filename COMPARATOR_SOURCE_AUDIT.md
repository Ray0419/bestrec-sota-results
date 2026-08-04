# Comparator Source Audit

**Audit time:** 2026-06-08 12:31:01 +10:00

## Sources Checked

| Component | Source checked | Audit note |
|---|---|---|
| SASRec | https://arxiv.org/abs/1808.09781 | Original SASRec paper by Kang and McAuley; accepted at ICDM 2018. |
| SBERT | https://arxiv.org/abs/1908.10084 | Sentence-BERT by Reimers and Gurevych; source for the sentence-embedding family used by MiniLM caches. |
| BLaIR / Amazon Reviews 2023 | https://arxiv.org/abs/2403.03952 | Current arXiv page lists a 2026 revision and ACL 2026; abstract says BLaIR introduces Amazon Reviews 2023 with more than 570M reviews and 48M items. |
| TIGER | https://arxiv.org/abs/2305.05065 | Generative retrieval recommender using semantic item identifiers; comparator target, not faithfully reproduced by the local minimal prototype. |
| LIGER | https://arxiv.org/abs/2411.18814 | Hybrid generative/dense retrieval comparator; source-locked protocol still required before final leaderboard wording. |
| BERT4Rec | https://arxiv.org/abs/1904.06690 | Bidirectional sequential recommendation baseline; local Beauty run is a negative baseline. |

## Strict Findings

- The repository's historical TIGER/BLaIR/LIGER numeric targets are not yet
  source-locked to exact paper tables.
- The current BLaIR arXiv record is revised in 2026, so old session-memory
  numbers must be rechecked against the version that will be cited.
- Local `run_tiger_minimal.py` is a prototype/negative control, not official
  TIGER.
- Local BLaIR use is an encoder/cache experiment, not a full reproduction of
  the BLaIR paper's benchmark.
- LIGER was not successfully reproduced in the historical session and must not
  be treated as a completed local baseline.

## Required Citation Wording

Use language like:

> We compare against approximate published TIGER/BLaIR/LIGER target ranges as
> context, while final SOTA claims require exact protocol-matched reproduction.

Avoid language like:

> We beat TIGER and BLaIR on the same dataset and protocol.

That stronger sentence is only allowed after the exact external split,
preprocessing, candidate scope, metric, and table values are verified.

