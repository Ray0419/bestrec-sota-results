# FIR-encoder probe — exploratory, deployable on any CUDA VM

**Status: EXPLORATORY, not pre-registered.** Answers screen `wjslq4lbw` open question #4 — does a strictly causal FIR-only encoder hold accuracy when it *replaces* attention — before any prereg is frozen. Clean minimal reimplementation, deliberately independent of the canonical `_bestrec_run` FIR code.

## What it runs

Two encoders, identical skeleton (pre-LN, 2 blocks, d=64, tied item embeddings, full-catalog cross-entropy), differing only in the token mixer:

| arm | mixer | complexity |
|---|---|---|
| `sasrec` | causal SDPA attention (`F.scaled_dot_product_attention` → flash / mem-efficient kernels on CUDA — the honest optimized baseline) | O(L²) |
| `fir` | strictly causal depthwise FIR conv, 64 taps, identity-init | O(L·K) |

- **Accuracy:** ML-1M, chronological leave-one-out, full-catalog ranking with history masking (no sampled negatives), NDCG@10 / HR@10, max length 200, 3 seeds per arm, early stopping on valid NDCG (patience 20).
- **Cost:** forward latency (median of 30, 10 warmup; CUDA events) and peak memory at lengths {200, 400, 600, 800, 1000}, batch 256, both arms.

## Deploy on a VM

```bash
scp -r experiments/fir_encoder_probe user@vm:~/
ssh user@vm 'cd fir_encoder_probe && bash deploy.sh'
# later:
scp user@vm:~/fir_encoder_probe/results/probe_results.json .
```

`deploy.sh` is idempotent: venv → torch (cu124 wheel if `nvidia-smi` present, else default) → ML-1M from the official GroupLens archive → smoke (~2 min) → full run. Expected full-run wall time: well under an hour on any modern GPU (A10/4090-class); several hours on CPU/MPS.

## Reading the result (probe-grade, no confirmatory claims)

- `fir` mean test NDCG@10 within ~3% relative of `sasrec` → encoder-replacement viability supported → draft prereg for the full noninferiority + efficiency study (mandatory baselines per screen: flash-attn SASRec, FMLP-Rec, Mamba4Rec, LRURec, NextItNet; a genuinely long dataset (XLong-class / KuaiRand / LastFM-1K) in addition to ML-1M).
- `fir` clearly below → the improvement branch dies cheaply; the audit-only formulation remains.
- Latency table is directional on any single GPU; the paper-grade table needs the pre-registered protocol.

Caveats logged up front: single dataset; d=64 small-model regime; FIR taps=64 untested at other budgets; MPS/CPU latency numbers are not comparable to CUDA.
