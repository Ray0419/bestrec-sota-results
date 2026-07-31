# Phase 0a — does dataset sequentiality predict FIR benefit?

**Result: NO. The hypothesis it was built to test was REFUTED by these scripts.**
See [`CLAUDE_PHASE0A_RESULT_2026-08-01.md`](../../CLAUDE_PHASE0A_RESULT_2026-08-01.md).

Kept because the refutation is the useful output, and because the length-confound finding about the
published TORS diagnostic stands on its own.

## What it computes

The training-free half of the sequentiality diagnostic of Klimashevskaia et al., *An Analysis of
Sequential Patterns in Datasets for Evaluation of Sequential Recommendations*, ACM TORS 2025
(`10.1145/3787969`; arXiv 2408.12008): count n-grams surviving a support threshold before vs after
shuffling each user's sequence. Their reading: relative change above −90% ⇒ weak structure.

- `ngram_diag.py` — the metric on any split CSV.
- `phase0a.py` — native splits + a length-matched variant.
- `phase0a_matched.py` — **the one that matters**: matches users *and* sequence length across
  corpora, bootstraps over 20 user draws, and rank-correlates the diagnostic against the measured
  FIR effect.

## Why matching is not optional

n-gram survival under shuffling is mechanically length-dependent, and support-thresholded counts
also scale with corpus size. ML-1M sequences average 131 items; Amazon 5-core average 6–10.

| corpus | native 3-gram | matched 2-gram (1000 users × 10 items) | FIR effect |
|---|---:|---:|---:|
| MovieLens1M_R4 | **−98.77%** | **−56.70%** | +0.0000002 |
| Industrial_and_Scientific | −94.42% | −59.63% | +0.002110 |
| CDs_and_Vinyl | −91.96% | −68.81% | +0.006150 |
| Musical_Instruments | −86.60% | −59.66% | +0.002116 |

Native, ML-1M looks like the *most* sequential corpus and Spearman vs the FIR effect is **−0.80**
— an apparent dissociation. Matched, ML-1M is the *least* sequential and Spearman is **+1.000**.
The sign flip is the length confound, and the apparent dissociation was the artifact.

(Even the matched +1.000 is soft: Welch contrasts show MI (t=1.01) and IS (t=1.17) are *not*
distinguishable from ML-1M; only CDs is (t=3.81). Two of the three orderings driving it are noise.)

## Run it

```bash
# 1. rebuild ML-1M from the repository's own frozen acquisition script
python _bestrec_run/acquire_movielens_fir_efficiency_v1.py --acquire

# 2. fetch the AR2023 5-core rating CSVs (small; ~7-21 MB each)
mkdir -p experiments/phase0a_sequentiality/amzn
cd experiments/phase0a_sequentiality/amzn
for C in Musical_Instruments Industrial_and_Scientific CDs_and_Vinyl; do
  curl -fLO "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/benchmark/5core/rating_only/$C.csv.gz"
done
cd -

# 3. run
python experiments/phase0a_sequentiality/phase0a.py
python experiments/phase0a_sequentiality/phase0a_matched.py
```

Paths are overridable via `BESTREC_REPO`, `ML1M_TRAIN`, `AMZN_DIR`.

**Integrity checks worth repeating:** the rebuilt ML-1M train split must hash to
`a1e0858393a720693e8b7dbaf167b252a2fcb5c2627d07f6ce3ccee0c47f6128` (matches
`fir_efficiency_ml1m_v1_adjudication.json:673`), and `Industrial_and_Scientific.csv.gz` to
`37dc32e707c6a89d2f8c4cf259fdec4e0ac1e2c7bd99c5886ee2c74c0ca99060` (matches
`data_raw_proper/industrial_sci/provenance_Industrial_and_Scientific.json`). Both were verified.

## Limits

Training-free metric only — the model-based half (SASRec/GRU4Rec degradation, Jaccard@10) was not
run, and the memo argues against running it post-hoc without pre-declaration. n=4 corpora. Amazon
LLOO vs ML-1M global time-cutoff is an uncontrolled protocol difference.
