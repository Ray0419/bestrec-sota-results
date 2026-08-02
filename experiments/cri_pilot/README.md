# CRI Pilot V1 — cross-relation influence disagreement (feasibility)

**Prereg:** [`PREREG_CRI_PILOT_V1.md`](../../PREREG_CRI_PILOT_V1.md) (frozen 2026-08-01, before first full run).
**Novelty verdict behind the RQ:** [`CLAUDE_RQ_CRI_NOVELTY_VERDICT_2026-08-01.md`](../../CLAUDE_RQ_CRI_NOVELTY_VERDICT_2026-08-01.md).

## Contents
- `run_pilot.py` — full pilot (6 configs: {uniform, popularity} noise × seeds {13, 42, 2026}); `--smoke` for the 2-epoch pipeline check.
- `adjudicate.py` — mechanical G1–G4 gate evaluation from `results/`; refuses to adjudicate on incomplete runs.
- `data/` — Taobao 3-behavior train/test txt (copied from the MB-CGCN official release, github.com/SS-00-SS/MBCGCN @ shallow clone 2026-08-01; upstream `Data/README` labels it "Tmall" while the literature calls this release "Taobao").
- `results/` — per-run JSON (AUCs, wall time) + npz (per-edge scores & noise masks), `pilot.log`.
- `.venv/` — uv venv, python 3.12, torch 2.13 (MPS). Not committed.

## Reproduce

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python torch numpy
.venv/bin/python run_pilot.py --smoke   # ~3 min pipeline check
.venv/bin/python run_pilot.py           # full pilot
.venv/bin/python adjudicate.py          # gates
```

## Honest-scope note
Injected-noise detection AUC is a **feasibility signal only** (see prereg out-of-scope list). The representation-space gradient approximation and TracIn-style accumulation are pilot-grade simplifications, declared in the prereg; PBRF-grade influence (Heo et al., NeurIPS 2025) is reserved for the full program if gates pass.
