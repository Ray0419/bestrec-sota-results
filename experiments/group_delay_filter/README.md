# Spectral-factorization and EGSP probes

This feasibility probe tests a compact spectral-filter family motivated by the
failure of ordinary shared and complex rank-1 FMLP-Rec filters to retain the
full filter's accuracy.

For frequency bin `f` and channel `c`, the proposed factorization is

```text
H[f,c] = B[f] * G[c] * exp(-i * 2*pi*f*tau[c]/L)
```

`B` is one shared complex spectrum, `G` is a complex channel gain, and `tau`
is a learned channel delay. Ordinary complex rank-1 is the special case
`tau[c] = 0`; it cannot represent a channel-specific linear phase slope. The
parameter count per layer is `2F + 3D`, versus `2FD` for the full filter.

The first gate is deliberately training-free. `fit_group_delay.py` projects
released or local full-filter checkpoints onto both the best rank-1 manifold
and the group-delay manifold. It can write projected checkpoints for direct
evaluation with the original model code. A direction survives only if group
delay materially reduces reconstruction error and projected checkpoints retain
ranking quality better than rank-1.

This exact parameterization was not found in the sequential-recommendation
literature searched on 2026-08-02. Closest general prior art includes
fractional-delay filters and learnable delay spacing; those concepts must be
cited, and absence from this search is not a final novelty proof.

## Outcome and surviving direction

Group-delay factorization did not beat the simpler rank-1 projection gate and
is not being scaled. The useful finding from this probe family is instead
Energy-Gated Spectral Projection (EGSP): train the full temporal filter, measure
its retained rank-1 energy, and project only layers above a frozen threshold.

On ML-1M, projecting the collapsed late FMLP-Rec layer improved test NDCG@10 by
`0.006959` on average across five seeds; the causal-FIR replication improved by
`0.005176` across four finalized seeds. Training rank-1 from scratch was worse,
which exposes an optimization/deployment rank gap. The same gate abstains on
Beauty, Toys, LastFM, released BEST-Rec checkpoints, and the incomplete Sports
pilot. A preregistered, completed ML-100K run also abstained without test access:
its two canonical layer energies were only `0.8371` and `0.8328`, despite greater matrix
density than ML-1M. Forced BEST-Rec projection was negative, and the tested
exact factorized CPU implementation was slower despite reducing selected filter
storage by 92.2%.

A label-free final-layer singular-value-thresholding branch was also rejected.
It improved ML-1M seed 42 less than EGSP and harmed LastFM by `0.001449`
validation NDCG@10. See `SVHT_FEASIBILITY_DECISION_2026-08-02.md`.

A hash-selected nested-user study found first-layer collapse at 943 users, no
selected layer at 2,000, and late-layer collapse at 4,000. Projection was
slightly negative for the early collapse but improved 4,000-user validation
NDCG@10 by `0.002265` for the late collapse. The surviving rule is therefore
depth-conditioned: only collapsed late filters are deployment candidates. See
`EGSP_SCALE_PHASE_DECISION_2026-08-02.md` and
`LAYER_MIGRATION_FEASIBILITY_DECISION_2026-08-02.md`.

This is a clear research gap, not a validated cross-domain algorithm. See
`EGSP_RESEARCH_DECISION_2026-08-02.md` for the evidence, novelty boundary, and
scale-up gates, `ML100K_PROSPECTIVE_DECISION_2026-08-02.md` for the completed
abstention, and `egsp_evidence_summary.json` for the compact result table.

```bash
python fit_group_delay.py \
  --checkpoint-glob '/path/to/output/LADDER_ML-1M_full_s*.pt' \
  --sequence-length 50 --output-dir projected --summary summary.json
```
