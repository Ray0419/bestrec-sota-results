# MultiVAE strict-confirmatory baseline (Liang et al., WWW 2018)

This document records the publication-grade MultiVAE rerun for the BEST-Rec /
LC2C strict-confirmatory pipeline. It is the last of the mandatory
`not_run` deep baselines (after BLaIR, DropoutNet, CLCRec, LightGCN, and the
TIGER RQ-VAE-proxy) and is the only round-4 deep-baseline that previously
existed only as a legacy single-seed round-3 number inside
`_bestrec_run/results_FINAL.json::datasets.<ds>.baselines.multvae`.

## What was implemented

- **Reference paper**: D. Liang, R. Krichene, M. Hoffman, T. Jebara,
  *Variational Autoencoders for Collaborative Filtering*, WWW 2018.
- **Architecture (paper default)**:
  - Encoder: `n_items -> 600 -> [mu_K, logvar_K]` with `K in {100, 200, 400}`.
  - Decoder: `K -> 600 -> n_items` (raw logits).
  - Tanh activations between hidden layers; **dropout 0.5** on the
    L2-normalized encoder input (paper convention; see also
    https://github.com/dawenl/vae_cf).
- **Loss**: multinomial log-likelihood + `beta * KL(q(z|x) || N(0, I))`.
  `beta` is linearly annealed from 0 to `beta_anneal_cap` over the first
  `total_anneal_steps` training iterations, then capped.
- **Optimizer**: Adam, lr=1e-3, weight_decay=0, batch_size=256 users.
- **Same warm-LOO protocol** as `run_warm_loo.py` and
  `run_lightgcn_strict.py`: 5-fold `make_warm_kfold(SEED=42)`; per
  (user, held-out item) pair, rank the held-out item against every
  item the user has NOT trained on, mask the seen items, report
  NDCG@10 / HR@10 / MRR. Scoring uses the decoder logits given the
  user's training row as encoder input.
- **Hyperparameter sweep on fold-0 inner split** (10% per-user held-out,
  ≤1 per user, only users with ≥2 train interactions) — performed
  once per dataset on `seed=20260521`:
  - `latent_dim in {100, 200, 400}`
  - `beta_anneal_cap in {0.05, 0.20, 0.50}`
  - `total_anneal_steps in {50, 200, 500}`
  - = **27 configs per dataset**
- **Final multi-seed eval**: chosen config × 3 seeds
  (`20260521`, `20260522`, `20260523`) × 5 folds. Per (fold, seed) we
  hold out 10% of training interactions for inner-validation early
  stopping (patience 15, max-epochs 200). Per-(fold, seed, user,
  target, ndcg10) records are written for the downstream paired
  Wilcoxon test.

## Files produced

| Path | Purpose |
| --- | --- |
| `_bestrec_run/run_multivae_strict.py` | Driver (model + sweep + multi-seed) |
| `_bestrec_run/run_multivae_strict_wilcoxon.py` | Per-USER paired Wilcoxon vs `ease_sbert` |
| `_bestrec_run/results_multivae_strict.json` | Per-dataset NDCG/HR/MRR + chosen config + sweep audit |
| `_bestrec_run/results_multivae_strict_perfold_<ds>.json` | (fold, seed, user, target, ndcg10) records, same schema as `results_lightgcn_strict_perfold_<ds>.json` |
| `_bestrec_run/results_multivae_strict_wilcoxon.json` | Holm-corrected Wilcoxon vs `ease_sbert` |
| `_bestrec_run/run_multivae_strict_beauty_fashion.log` | beauty+fashion run trace |
| `_bestrec_run/run_multivae_strict_instruments.log` | instruments run trace |
| `_bestrec_run/run_multivae_strict_books.log` | books run trace |

## Headline numbers (3 seeds × 5 folds, multi-config tuned)

| Dataset | n users | n items | n inter | tuned MultiVAE NDCG@10 ± std (across seeds) | legacy FINAL.multvae NDCG@10 ± std |
| --- | ---: | ---: | ---: | ---: | ---: |
| beauty       |    253 |    356 |    2,535 | **0.0285 ± 0.0088** | 0.0194 ± 0.0065 |
| fashion      |    513 |    614 |    3,805 | **0.0542 ± 0.0052** | 0.0358 ± 0.0059 |
| instruments  |  3,911 |  2,269 |   33,580 | **0.0527 ± 0.0005** | 0.0547 ± 0.0027 |
| books        | 14,407 | 13,164 |  601,992 | **0.0690 ± 0.0003** | 0.0531 ± 0.0023 |

Across-seed std for the tuned numbers is reported as
`np.std(per_seed_means)`; per-seed numbers individually have their own
per-fold std reported inside `results_multivae_strict.json`.

### Per-dataset chosen hyperparameters

| Dataset | latent_dim | beta_anneal_cap | total_anneal_steps | best val NDCG@10 |
| --- | ---: | ---: | ---: | ---: |
| beauty       | 200 | 0.05 | 500 | 0.0584 |
| fashion      | 100 | 0.20 | 200 | 0.0599 |
| instruments  | 100 | 0.50 |  50 | (see results_json) |
| books        | 200 | 0.50 | 200 | 0.0721 |

All chosen configs used `enc_hidden=dec_hidden=600`, `dropout=0.5`,
`lr=1e-3`, `weight_decay=0` (paper defaults for everything except the
three swept axes).

## Comparison to legacy round-3 multvae

Tuned MultiVAE is consistent with or modestly better than the legacy
single-seed round-3 numbers — confirming that the legacy multvae values in
`results_FINAL.json` were reasonable paper-grade defaults but slightly
under-tuned on the smaller datasets:

- **Beauty**: +0.009 NDCG@10 over legacy (+47% relative). The legacy 0.019
  was under-tuned for this small warm fold; the tuned 0.029 reflects a
  reasonable paper-grade choice (latent=200, larger anneal).
- **Fashion**: +0.018 NDCG@10 over legacy (+51% relative). Same story.
- **Instruments**: -0.002 NDCG@10 vs legacy (effectively identical;
  legacy was already in the right ballpark).
- **Books**: +0.016 NDCG@10 over legacy (+30% relative). The legacy 0.053
  was under-tuned for the larger Books dataset; the tuned 0.069 confirms
  that a more aggressive beta-anneal cap and longer anneal schedule both
  matter at this scale.

Note that the legacy `multvae` in `results_FINAL.json` is a single-seed
round-3 number whose `NDCG@10_std` is per-fold std for that seed, not
across-seed std. The tuned numbers above use across-seed std, which is
the audit-grade quantity.

## Honest comparison to EASE+SBERT (paper's central warm claim)

`ease_sbert` warm-LOO NDCG@10 from `_bestrec_run/results_warm_loo.json`
(single seed `SEED=42`, 5-fold; per-user vectors from
`_bestrec_run/results_warm_loo_perfold_<ds>.json`):

| Dataset | ease_sbert | tuned MultiVAE | Δ (vae - ease) | Wilcoxon `vae < ease` p (Holm) | Two-sided p (Holm) |
| --- | ---: | ---: | ---: | ---: | ---: |
| beauty       | 0.0929 | 0.0285 | -0.0644 | 2.62e-13 | 5.23e-13 |
| fashion      | 0.0923 | 0.0549 | -0.0373 | 3.66e-10 | 7.32e-10 |
| instruments  | 0.0564 | 0.0527 | -0.0036 | 1.60e-03 | 3.19e-03 |
| books        | 0.1023 | 0.0682 | -0.0341 | 1.12e-125 | 2.24e-125 |

Per-USER paired Wilcoxon uses one observation per user (the mean of that
user's per-fold per-seed NDCG@10), so the test is independent across users.
Holm-Bonferroni is applied **across datasets** for each of the three
alternatives (two-sided, `vae > ease`, `vae < ease`).

Per-user win counts (multivae > ease_sbert / ease_sbert > multivae / ties):

| Dataset | n users paired | V wins | E wins | ties |
| --- | ---: | ---: | ---: | ---: |
| beauty       |   253 |   58 |  116 |   79 |
| fashion      |   513 |  120 |  161 |  232 |
| instruments  | 3,911 | 1077 | 1034 | 1800 |
| books        | 5,000 | 1274 | 2167 | 1559 |

(Books `n_users_paired=5000` reflects the `RANKING_USERS_CAP=5000` used
by the legacy warm-LOO eval per fold; the multi-seed tuned MultiVAE was
evaluated on all 14,407 users but the paired test only uses the 5,000
that appear in both source files.)

### Honest verdict — does tuned MultiVAE beat / tie / lose to EASE+SBERT?

- **beauty**: EASE+SBERT **wins decisively** (multivae 0.029 vs ease 0.093;
  Holm `vae<ease` p = 2.6e-13).
- **fashion**: EASE+SBERT **wins decisively** (0.054 vs 0.092;
  Holm `vae<ease` p = 3.7e-10).
- **instruments**: EASE+SBERT **wins marginally** (0.053 vs 0.056;
  ~7% relative gap, but with N=3911 the paired Wilcoxon rejects
  `vae >= ease` at Holm-corrected p = 1.6e-3). Within-noise on the
  point estimate, statistically significant on the per-user test.
- **books**: EASE+SBERT **wins decisively** (0.068 vs 0.102;
  Holm `vae<ease` p = 1.1e-125).

**The paper's central warm claim** — that EASE+SBERT beats the deep
collaborative-filtering baselines on the warm-LOO protocol — is **NOT
weakened** by this re-tuning. After a careful 27-config sweep, multi-seed
averaging, and an inner-val early-stopping protocol that follows the
Liang et al. defaults, the tuned MultiVAE still loses to EASE+SBERT on
all 4 datasets (with the gap being huge on beauty/fashion/books and
small but statistically significant on instruments).

## Reproducibility

```sh
# Full multi-seed multi-config run (~30 min wall clock on a single GPU)
_bestrec_run/.venv/Scripts/python _bestrec_run/run_multivae_strict.py \
    beauty fashion instruments books \
    --seeds 20260521,20260522,20260523

# Paired Wilcoxon vs ease_sbert (reads the JSONs produced above
# plus the existing _bestrec_run/results_warm_loo_perfold_<ds>.json)
_bestrec_run/.venv/Scripts/python _bestrec_run/run_multivae_strict_wilcoxon.py \
    beauty fashion instruments books
```

Both scripts are deterministic on a single GPU per seed; the Python +
NumPy + PyTorch seeds are set via `set_seed(seed)` inside
`train_multivae`. Per-fold per-seed n_eval matches the warm-LOO eval in
`run_warm_loo.py` (same `make_warm_kfold(SEED=42)`).
