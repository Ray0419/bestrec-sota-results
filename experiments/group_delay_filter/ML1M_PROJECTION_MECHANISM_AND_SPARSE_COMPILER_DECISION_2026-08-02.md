# ML-1M projection mechanism and sparse-FIR compiler decision - 2026-08-02

## Decision

**A clear, useful research gap has emerged; authorize bounded confirmation and
implementation work, but not a large training campaign yet.**

The strongest candidate is a dual-domain post-training compiler for learned
temporal filters:

1. train the expressive frequency-by-channel filter normally;
2. intervene only on a collapsed late layer;
3. replace its channel responses by their consensus response;
4. inverse-transform that response, retain its largest FIR taps, and deploy the
   final next-item mixer as a direct sparse dot product.

The current working label is **Consensus-Sparse FIR Compilation (CSFC)**. The
name is provisional; the evidence matters more than the acronym.

## Frozen control decisions

### Channel-deviation path: ordered toward sharing

Mean validation NDCG@10 is strictly ordered as the channel-specific deviation
is restored:

| retained deviation alpha | mean NDCG@10 |
|---:|---:|
| 0.00 | 0.1258977884 |
| 0.25 | 0.1240524792 |
| 0.50 | 0.1225632586 |
| 0.75 | 0.1208178222 |
| 1.00 | 0.1186238833 |

All five individual seeds are monotone and all five are best at `alpha=0`.
This passes the frozen **ordered toward sharing** rule and rejects an isolated
endpoint explanation.

### Norm-matched control: structure-specific support

Channel sharing exceeds a scalar-rescaled original filter with exactly the
same Frobenius norm by `+0.0062911762` mean NDCG@10, positive in 5/5 seeds.
This passes the frozen `+0.002`, 4/5 structure-specific rule. Global amplitude
shrinkage explains only a small part of the ordinary sharing gain.

### Power-preserving consensus: energy-independent support

The consensus filter that preserves the original energy separately at every
frequency improves the full model by `+0.0059629810`, positive in 5/5 seeds.
It therefore passes the frozen energy-independent consensus rule. Ordinary
channel-mean sharing remains better by about `0.001311`, so some shrinkage is
helpful, but neither global nor frequency-wise energy reduction is necessary
for the main effect.

Together with the fair from-scratch control (`0.117160` late-shared versus
`0.122428` full and `0.131139` full-then-share), these results support a real
optimization/deployment asymmetry: channel specialization helps optimization,
while retaining it in the selected late filter harms deployment ranking.

## Sparse-FIR result

Both preregistered tap budgets pass, and K=8 is unexpectedly strongest.

| compiled late filter | retained impulse energy | delta vs shared | delta vs original full | positive vs shared |
|---|---:|---:|---:|---:|
| top-8 taps | 95.77% | +0.0027393280 | +0.0100132330 | 5/5 |
| top-16 taps | 98.85% | +0.0005972472 | +0.0078711523 | 3/5 |

For K=8, four of five paired-user bootstrap intervals are strictly positive;
the fifth includes zero. Every seed improves. K=8 therefore passes all frozen
compiler bounds and is the sole primary implementation candidate. K=16 also
passes its noninferiority bounds but is weaker.

The ordering matters scientifically: retaining more impulse energy does not
produce better ranking. The removed weak mid-lag response appears harmful,
while the surviving taps consistently concentrate at the recent boundary and,
in four seeds, a small number of oldest-history boundary positions. This is a
regularizing compilation effect, not merely a high-fidelity approximation.

## Novelty boundary

The exact train-full, collapse-channels, inverse-transform, sparse-tap, direct
next-item deployment pipeline was not found in the targeted recommendation or
sequence-model search. The prior full-text/citation audit also found no
post-training filter-collapse analysis among the closest recommendation
papers. Confidence that the exact sequential-recommendation phenomenon and
pipeline are unoccupied is now approximately **90-95%**.

That is not yet 95% confidence in a Tier-A contribution. Broad components are
occupied by truncated-SVD compression, DirectShare/PostShare, generic magnitude
pruning, frequency-domain CNN compression, Flash Inference, and AIRE-Prune.
The local WEARec ISGP experiment also shows that impulse-energy pruning can
fail in long sparse sequences. Current confidence that CSFC is sufficiently
non-obvious, general, and valuable for a Tier-A journal is approximately
**75-85%**. The ML-1M result is large and repeatable, but still one dataset and
has no measured wall-clock benefit yet.

## Authorized next work

1. Run a frozen validation ablation separating sparse temporal support from
   channel consensus and comparing adaptive top-8 support with fixed recent
   and boundary support.
2. Freeze K=8 and evaluate its still-untouched ML-1M test result only after that
   ablation is locked.
3. Implement the direct final-output sparse FIR and require numerical parity
   with the compiled spectral checkpoint before idle-device timing.
4. Audit exact nearest work beyond title/abstract level, especially impulse-
   response pruning, long-convolution inference, and dual-domain compression.
5. Seek a prospective real dataset or a second learned-filter family that
   activates the frozen collapse gate. No broad training campaign starts until
   one such replication and a meaningful latency result raise value confidence
   toward 95%.

## Provenance

The compact artifact of record is `ml1m_projection_controls_summary.json`.
Preregistration SHA-256 values:

- channel-deviation path:
  `1672aa186bef7ac3aa9ae93cb8dfe7bfc89f76be778fb5292c03cc276e685957`;
- norm control:
  `d5ed6bf88361bc0ae5f9baf1e7c4643f63b101f8a8c98e6ed164bb03369b6109`;
- power-preserving consensus:
  `716a262988162671f37175b1908ed1f134560aa6eee5eb21e3839b6e9f573837`;
- sparse-FIR compiler:
  `88a1e94864e6bd0b8cdd6378c2a7176e1044eb3750a8020fe867fb54a2d7560a`.

All outcomes in this memo are full-catalog validation results. Test was not
accessed for any new control or compiled checkpoint.
