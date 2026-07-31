# Exploratory experiments (Claude, 2026-08-01)

**STATUS: EXPLORATORY. NOT PREREGISTERED. NOTHING HERE IS A COUNTABLE CLAIM.**

These are scratch experiments supporting research-direction memos. They are *outside* the
artifact-gated evidence graph: nothing here is consumed by `rebuild_hstu_submission.py`, nothing
here is in `RELEASE_MANIFEST.json`, and no result here may enter the manuscript without a frozen
preregistration and a fresh run under the repository's gate.

| directory | memo | question | status |
|---|---|---|---|
| `phase0a_sequentiality/` | [`CLAUDE_PHASE0A_RESULT_2026-08-01.md`](../CLAUDE_PHASE0A_RESULT_2026-08-01.md) | Does shuffle-based dataset sequentiality predict FIR benefit? | **complete — hypothesis REFUTED** |
| `filter_overparam/` | [`CLAUDE_RQ_FILTER_OVERPARAM_2026-08-01.md`](../CLAUDE_RQ_FILTER_OVERPARAM_2026-08-01.md) | Does FMLP-Rec's learnable filter need its per-channel parameterisation? | **in flight** |

Read the memos first — they carry the reasoning, the pre-declared kill conditions, and the limits.
These directories carry only the code needed to reproduce the numbers.

## Provenance of inputs (verified, not assumed)

- **ML-1M (r≥4)** is rebuilt by the repository's own frozen
  `_bestrec_run/acquire_movielens_fir_efficiency_v1.py --acquire`. The rebuilt train split hashes
  to `a1e0858393a720693e8b7dbaf167b252a2fcb5c2627d07f6ce3ccee0c47f6128`, **bit-identical** to the
  split recorded in `_bestrec_run/fir_efficiency_ml1m_v1_adjudication.json:673`. Record-level
  artifacts stay under the gitignored private root; ML-1M may not be redistributed.
- **Amazon Reviews 2023 5-core** is downloaded from the McAuley Lab benchmark endpoint.
  `Industrial_and_Scientific.csv.gz` hashes to `37dc32e7…9060`, an **exact match** to
  `data_raw_proper/industrial_sci/provenance_Industrial_and_Scientific.json`. Not redistributed here.
- **BSARec benchmark suite** (third party, `yehjin-shin/BSARec`) is cloned by `setup.sh`, not
  vendored. Only an 85-line patch is committed.
