# WEARec static-base projection decision - 2026-08-02

## Decision

**Compression-only support; reject as a generalization result or scale-up
candidate.**

The frozen final-block projection stayed within the `-0.0005` NDCG@10 margin
on all four official WEARec checkpoints, but only ML-1M was nonnegative. The
unweighted mean validation delta was `-0.00000910`, so the stronger support
rule failed.

| dataset | validation NDCG@10 delta | paired bootstrap 95% interval | unchanged users |
|---|---:|---:|---:|
| Beauty | -0.0000487 | [-0.0002607, +0.0001612] | 98.79% |
| LastFM | -0.0000183 | [-0.0002408, +0.0001972] | 99.08% |
| ML-1M | +0.0000866 | [-0.0005980, +0.0007725] | 95.93% |
| Sports_and_Outdoors | -0.0000560 | [-0.0002335, +0.0001220] | 98.83% |

No projected checkpoint was evaluated on test.

## Interpretation

WEARec's final static FFT scale and bias are nearly shared across heads, and
their head-mean projection is behavior-preserving at the frozen margin. The
selected static tensors shrink by 50% with two heads, 75% with four heads, and
87.5% with eight heads.

This is not practically important whole-model compression. The saved scalars
are only 0.012% to 0.040% of the official models. It also does not reproduce
FMLP-Rec's positive post-training effect.

The WEARec source supplies a simpler explanation. With its adaptive MLP active,

```text
effective_filter = base_filter * (1 + adaptive_scale)
effective_bias = base_bias + adaptive_bias
```

the static affine terms can be folded into the adaptive MLP's final linear
map. They are non-identifiable with that map, so their cross-head collapse is
not clean evidence for an optimization/deployment rank law. An exact folding
implementation could remove them without retraining, but its parameter and
operation savings are too small to justify a Tier-A algorithm claim by itself.

## Provenance

- Preregistration SHA-256:
  `766ba30fd30df1a02ef9595dc61a8b2b0806407db0bd22b3cb4ca760e254f295`.
- Beauty artifact SHA-256:
  `036c20bb3586c287aa4123f9d727c4c5548dd70fa3b0fe5f7f38e7de74d62f0f`.
- LastFM artifact SHA-256:
  `da0e13f47eda0aac6422e3130cda493f0a596fc4448e22f38c1945c446cf50e4`.
- ML-1M artifact SHA-256:
  `532fd7fee76ea4a8cb89c4ac91d0f2130923ef7e2f8a26247096f7202e3010ac`.
- Sports artifact SHA-256:
  `e2934c60cbf4c784a4bccb57cac734616592df8db8e5e56843b88e3fd58bcd06`.

The official WEARec source revision was
`2087335339b1ead87da6e066ce14e2d33880a95e`. The four checkpoint and data
hashes are frozen in the preregistration and verified by the evaluator before
each run.
