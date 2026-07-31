# Filter-parameterisation ladder for FMLP-Rec

Tests whether the **per-channel** parameterisation of FMLP-Rec's learnable frequency filter — the
model's defining component (WWW'22) — is necessary.

Full reasoning, novelty sweep, pre-declared margin and kill conditions:
[`CLAUDE_RQ_FILTER_OVERPARAM_2026-08-01.md`](../../CLAUDE_RQ_FILTER_OVERPARAM_2026-08-01.md).
**Read that before interpreting any number produced here.**

## The arms

Published FMLP-Rec filter (`FMLP-Rec/modules.py:106`, and `model/fmlprec.py` in BSARec):

```python
self.complex_weight = nn.Parameter(
    torch.randn(1, max_seq_length//2 + 1, hidden_size, 2) * 0.02)   # [1, L/2+1, d, 2]
```

per-frequency **×** per-channel. All four arms are **nested**, so any loss is attributable to the
constraint alone:

| arm | parameterisation | filter params (L=50, d=64, 2 layers) | reduction |
|---|---|---:|---:|
| `full` | published: per-freq × per-channel | 6,656 | 1× |
| `rank1` | separable: freq profile ⊗ channel gain | 360 | 18× |
| `shared` | per-frequency, channel-tied | 104 | **64×** |
| `none` | filter layer removed (identity anchor) | 0 | — |

`none` is the floor control, mirroring the `identity` anchor in the repository's own `FIRCTRL`
campaign. Without it the comparison is uninterpretable — see the validity gate below.

## Run it

```bash
cd experiments/filter_overparam
PYBIN=/path/to/python ./setup.sh          # clones + pins BSARec, applies patch, verifies param counts
./run_all.sh 6 LastFM:5 Beauty:5 Toys_and_Games:5 ML-1M:5
```

`setup.sh` fails loudly if the arm parameter counts are not exactly 6656/360/104/0, so a silently
mis-applied patch cannot produce numbers.

**Sizing.** 80 runs (4 datasets × 4 arms × 5 seeds), CPU. Set `n_parallel × 2 ≤ physical cores` —
oversubscription does not merely slow things down, it thrashes badly (32 workers on 14 cores turned
a 7-second epoch into 15 minutes). On 14 cores at 6 concurrent, expect **many hours**; LastFM
finishes first, CDs-scale datasets last. Re-running skips completed runs, so it is safe to
interrupt and resume.

Requires `torch`, `numpy`, `scipy`, `pandas`, `tqdm`. The upstream `bsarec_env.yaml` pins CUDA; on
CPU/Apple Silicon a plain `pip install torch numpy scipy pandas tqdm` is sufficient (`--no_cuda` is
already passed).

## Analyse

```bash
python analyze.py results LastFM Beauty Toys_and_Games ML-1M   # paired stats vs `full`
python analyze.py filters Beauty                               # SVD redundancy of trained filters
```

`results` reports, per dataset and arm, the mean/sd of test NDCG@10 and HR@10, and — paired by seed
against `full` — the mean difference, t, 95% CI, and the count of seeds favouring the arm.

`filters` is the mechanism probe: SVD of each trained `full` filter `[L/2+1, d]`, reporting top-1
singular-energy share, participation-ratio effective rank, and mean inter-channel cosine of the
magnitude responses. **Near-rank-1 ⇒ the per-channel parameterisation is redundant structurally,
not merely behaviourally** — which is what FMLP-Rec's own "the filter converges to a low-pass
shape" analysis predicts.

## Decision rules — declared 2026-08-01 with 0/80 runs complete

**Noninferiority margin**, scale-free because raw NDCG is not comparable across datasets:

> **Δ = 0.10 × (full − none)** per dataset. `shared` is noninferior iff the **upper** bound of the
> two-sided 95% paired CI of `(full − shared)` on NDCG@10 lies below Δ.

**Validity gate:** if `full − none` does not exceed zero with a 95% CI on a dataset, that dataset is
**VOID for this endpoint** and reported as a reproduction failure — not as evidence either way.

**Reproduction anchors.** `full` must land near published FMLP-Rec values or the comparison is void:

| reference | Beauty HR@10 | Beauty NDCG@10 | source |
|---|---:|---:|---|
| FMLP-Rec | 0.0618 | — | DWTRec (arXiv 2503.23436) baseline table |
| BSARec | 0.1008 | 0.0611 | `src/output/BSARec_Beauty_best.log` (ships with upstream) |

**Kill conditions:** `shared` loses beyond the noise floor on a majority of datasets → strong claim
dies. `none ≈ full` → filter does nothing here, report as reproduction failure. Filter SVD
high-rank but `shared` still matches → drop the mechanism claim, do not retrofit a new one.
Everything within seed noise → report as underpowered with the detectable effect size.

## Second model (implemented, not yet queued)

BSARec's `sqrt_beta` is `[1, 1, d]` — also per-channel. The same patch ties it to a scalar:
**128 → 2 parameters**, the same 64× cut on a different filter form. Run with
`--model_type BSARec --filter_mode shared` plus BSARec's own hyperparameters
(`--alpha 0.7 --c 5 --num_attention_heads 1` for Beauty).

## Attribution

The harness is the official BSARec suite (`yehjin-shin/BSARec`), pinned at `c80bdc0`. It is cloned,
not vendored; only `patches/filter_mode.patch` (85 lines) is committed here. FMLP-Rec is Zhou et
al., WWW 2022. Datasets ship with the upstream repository.
