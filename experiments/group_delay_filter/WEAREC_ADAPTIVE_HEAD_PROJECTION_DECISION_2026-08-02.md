# WEARec adaptive-head projection decision - 2026-08-02

## Decision

**Feasibility support; surviving research lead, not authorized for large-scale
training.**

The frozen gate selected the final adaptive frequency-generator output in the
official LastFM and Sports_and_Outdoors checkpoints and abstained on Beauty and
ML-1M. Both eligible validation deltas were positive, so the preregistered
support rule passed.

| dataset | validation NDCG@10 delta | paired bootstrap 95% interval | sign |
|---|---:|---:|---:|
| LastFM | +0.001578 | [-0.001067, +0.004380] | positive |
| Sports_and_Outdoors | +0.000715 | [+0.000307, +0.001113] | positive |

The unweighted mean delta is `+0.001147`. Beauty and ML-1M were not projected
because their final adaptive output-weight energies (`0.871416`, `0.804424`)
failed the unchanged `0.905` gate. No projected test outcome was accessed.

## Candidate algorithm

**Depth-Gated Adaptive Head Collapse (DAHC)** trains WEARec's dynamic frequency
generator with independent per-head outputs. After model selection, it treats
the final output weight and bias as row-by-head matrices. If both have rank-1
retained energy at least `0.905` and dominant-head/uniform cosine at least
`0.97`, DAHC replaces their head columns by the mean and deploys one output map
broadcast across heads. Otherwise it leaves the checkpoint unchanged.

This keeps the input-dependent frequency response. It shares the generator
that produces that response, not the full filter or the wavelet path.

## Realized compactness

A compact implementation computes the shared final output once and broadcasts
it as a stride-based view. Against the expanded projected checkpoint, the
LastFM smoke test has exact encoder parity (`max_abs=0`). It removes 3,380
parameters on two-head LastFM and 10,140 on four-head Sports, reducing the
selected output layer by 50% and 75%. Whole-model reductions are only 1.03%
and 0.79%, respectively. An idle-device benchmark is still required; no
latency claim follows from the contended smoke run.

## Novelty boundary

The exact adaptive-frequency/sequential-recommendation endpoint was not found
in the targeted search, but broad novelty is not available. Head-wise
DirectShare and PostShare already select and share pretrained attention-head
weights, and FilterNet already shows universal channel-shared frequency
filters outperforming individual filters in forecasting. DAHC's potentially
novel claim is therefore narrow: label-free depth-gated collapse of a learned
input-dependent frequency generator in sequential recommendation, with
abstention and a full-training/compact-deployment distinction.

Current novelty/value confidence is approximately 70-80%, not 95%. Before
scale-up it needs: exact closest-paper comparison, an idle compact benchmark,
fresh optimizer-seed replication on both eligible datasets, a fair compact
from-scratch control, and one prospectively untouched current-model dataset.

## Provenance

- Preregistration SHA-256:
  `404b585a19e324e2e7885adac838da449774a3494a12d0097c90d26aa050967d`.
- LastFM validation artifact SHA-256:
  `760fa7e8b5740d8da2424567683a86b819d639b45bafcc120cf57469596935cf`.
- Sports validation artifact SHA-256:
  `691db459dde6b39165f54fc2fa0b730285b8716f182127a9ace5d54c58ac70f7`.
- Official WEARec revision:
  `2087335339b1ead87da6e066ce14e2d33880a95e`.
