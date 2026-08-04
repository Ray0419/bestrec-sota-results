# Publishable Claim

**Audit time:** 2026-06-08 12:31:01 +10:00

**Update 2026-06-08:** same-run `sasrec_blair` and `sasrec_no_sbert`
comparators were added to the fresh confirmatory package. The internal ablation
claim strengthened, but the broad SOTA claim was blocked by a stronger external
HSTU-BLaIR report. The 2026-06-09 update below supersedes the "unreproduced"
status from that audit pass.

**Update 2026-06-09:** the HSTU-BLaIR WSL reproduction lane completed in the
SM120 compatibility environment. Final full-eval NDCG@10 is `0.0738224`; best
full-eval NDCG@10 is `0.0740335`; best epoch/partial NDCG@10 is `0.0777197`.
This is stronger than the SASRec-SBERT confirmatory mean `0.0550927`, so the
broad Video_Games SOTA claim is blocked. The HSTU run is not yet
publication-grade canonical evidence because it is a CUDA 12.8 compatibility
port and the log contains fbgemm autograd-kernel warnings.

## Strict Claim That Can Be Drafted Now

### Confirmatory rerun result

The fresh five-seed rerun in
`_bestrec_confirmatory_sasrec/video_games_sasrec_confirmatory_20260608_5seed/`
is now the strongest internal evidence:

| Seed | NDCG@10 | HR@10 | MRR |
|---:|---:|---:|---:|
| 20260608 | 0.0546930 | 0.0985100 | 0.0493902 |
| 20260609 | 0.0551649 | 0.1009687 | 0.0493300 |
| 20260610 | 0.0553428 | 0.1002723 | 0.0498045 |
| 20260611 | 0.0547804 | 0.0992064 | 0.0493729 |
| 20260612 | 0.0554822 | 0.0999979 | 0.0501063 |

Mean NDCG@10 is `0.0550927` with sample standard deviation `0.0003452`.
The run wrote `473,810` per-user full-catalog records and a hash-checked
manifest.

Same-run comparators:

| Method | Mean NDCG@10 | Std | Holm-significant vs `sasrec_sbert` |
|---|---:|---:|---|
| `sasrec_blair` | 0.0545244 | 0.0007472 | yes, Holm p = 0.0311053 |
| `sasrec_no_sbert` | 0.0509659 | 0.0006818 | yes, Holm p = 1.05610e-31 |

### Historical exploratory result

SASRec-SBERT is a small SASRec-style sequential recommender that adds frozen
SBERT/MiniLM item-text features to learned item embeddings. On this repository's
Amazon Reviews 2023 Video_Games 5-core leave-last-out full-catalog protocol, the
saved three-run result is:

| Run file | NDCG@10 | HR@10 | MRR |
|---|---:|---:|---:|
| `results_sasrec_sbert_Video_Games_v3.json` | 0.0543478 | 0.0983517 | 0.0489073 |
| `results_sasrec_sbert_Video_Games_seed20260522.json` | 0.0497873 | 0.0898672 | 0.0451127 |
| `results_sasrec_sbert_Video_Games_seed20260523.json` | 0.0500020 | 0.0906798 | 0.0452239 |

The honest publishable wording is:

> Under our 5-core full-catalog Video_Games protocol, adding frozen SBERT/MiniLM
> text features to a compact SASRec-style model produces a strong and
> internally reproducible sequential recommendation baseline. In a fresh
> five-seed confirmatory rerun, it achieves `0.05509 +/- 0.00035` NDCG@10 and
> significantly beats same-run BLaIR-encoder and no-text SASRec ablations.

**Comparator audit update (2026-05-30, verified by fetching arXiv PDFs):**
After verifying the actual published comparator papers:
- TIGER (Rajput et al. 2023, NeurIPS, arXiv:2305.05065) evaluates on Amazon **2014** Beauty/Sports/Toys, NOT AR2023. Reports NDCG@10 = 0.0384 on Beauty 2014.
- LIGER (Yang et al. 2024, arXiv:2411.18814) also Amazon **2014**. Reports NDCG@10 = 0.04020 ± 0.00044 (K=20, Beauty 2014).
- BLaIR (Hou et al. 2024, arXiv:2403.03952) evaluates on AR2023 but with **by-timestamp 8:1:1 split with no k-core filter** and **UniSRec downstream**, not SASRec. Their best Video_Games NDCG@10 (across LLM encoders, in their Table 8) is 0.0138.

**Updated conclusion:** the earlier session's "SOTA-competitive against
TIGER/BLaIR/LIGER" framing must be retracted as apples-to-oranges. HSTU-BLaIR is
now the relevant stronger external Video_Games reference in both the upstream
README and our completed compatibility-port run. Our 0.05509 ± 0.00035 remains
a reference number and same-run ablation result, not a SOTA result.

## Claims That Must Not Be Made Yet

- Do not claim a new Transformer architecture.
- Do not claim invention of SBERT, BLaIR, Amazon Reviews 2023, or the Hou et al.
  SASRecText MLP adaptor.
- Do not claim broad recommender SOTA.
- Do not claim Video_Games SOTA. HSTU-BLaIR's upstream README reports
  NDCG@10 = 0.0760, and our completed SM120 compatibility-port run is still
  substantially stronger than SASRec-SBERT.
- Do not claim Beauty_and_Personal_Care SOTA.
- Do not claim statistical significance for the Beauty BLaIR-rich-text/MLP gain
  without matched multi-seed baseline runs and per-user records.
- Do not claim final superiority over TIGER/BLaIR/LIGER unless exact split,
  preprocessing, candidate scope, metric, and table values are locked.

## Beauty Negative Result To Preserve

The strongest Beauty_and_Personal_Care saved result remains far below the
published LIGER target range:

| Result file | NDCG@10 | HR@10 | MRR |
|---|---:|---:|---:|
| `results_sasrec_chunkedfull_Beauty.json` | 0.0191144 | 0.0346393 | 0.0177866 |
| `results_sasrec_blair_richtext_mlp_Beauty.json` | 0.0193575 | 0.0348038 | 0.0180004 |
| `results_sasrec_blair_richtext_mlp_seed43_Beauty.json` | 0.0195452 | 0.0351396 | 0.0181366 |

This supports a negative-result section: simple SASRec-style models with frozen
text features do not close the Beauty_and_Personal_Care gap under this
repository's full-catalog 5-core protocol.

## Current Approval Decision

As a strict reviewer, I would not approve a final SOTA paper yet. I would
approve continued drafting of a narrow workshop-style paper if it uses the
guarded claim above, retains the Beauty negative result, cites the external
comparator blockers, and completes the revision plan in `REVISION_PLAN.md`.
