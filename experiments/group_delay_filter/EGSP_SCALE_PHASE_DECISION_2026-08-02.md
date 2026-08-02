# EGSP nested-user scale mechanism decision — 2026-08-02

## Preregistered outcome

**Inconclusive under the primary scale rule. No cohort test metric was accessed.**

| nested users | interactions | first-layer energy | late-layer energy | selected layer |
|---:|---:|---:|---:|---|
| 943 | 157,245 | 0.905805 | 0.882431 | first |
| 2,000 | 325,133 | 0.868334 | 0.890199 | none |
| 4,000 | 652,238 | 0.853181 | 0.909011 | late |

The late-layer increase from 943 to 4,000 users is `0.026580`. It is monotonic
and reaches the activation threshold, but does not meet the frozen `0.04`
increase required for a support verdict. It also does not meet the falsification
rule. The predeclared 2,000-user interpolation point was therefore run and is
included above.

## Emergent secondary finding

The location of rank collapse changes with cohort size. At 943 users only the
first filter crosses `0.905`; at 2,000 neither does; at 4,000 only the late
filter crosses. The five full-ML-1M discovery seeds likewise select the late
filter. This is consistent with **depth migration of filter compression**, but
one seed per nested cohort cannot distinguish a scale law from seed and
checkpoint-selection variability.

This secondary result was not the primary preregistered criterion and must not
be presented as confirmed. It authorizes a separately frozen validation-only
test of whether the same layer-local energy rule improves ranking at both
selected endpoints.

## Integrity record

All runs used seed 47, validation NDCG@20 checkpoint selection, canonical filter
spectra, and the no-test runner. Their selected checkpoint SHA-256 hashes are:

- 943 users: `08ce3ba1040fc21a7f0d0f6f4d512150448258d6c4dbd2dd59e3811bb0c8a744`
- 2,000 users: `82ffd24925402454b47bdab7e11027edc248f1519b273359fa95bb35a4ba86f1`
- 4,000 users: `59aa14c6eda31ce37a14d2ecef8e911a375d803da65b1dbd93d50e3c0483bde4`

The nested-data manifest is `ml1m_nested_users_manifest.json`; complete
validation, source, log, script, and singular-value records are in the three
`prospective_scale/*.no_test.json` artifacts.
