# H6 Phase-A Coverage Result: Run 002

Date: 2026-08-07

Classification: confirmatory, label-blind feasibility gate

Verdict: `PASS_COVERAGE_AND_OPEN_LABELS`

## Integrity

- Primary child PID `25340`, exact-replay and verifier children all exited
  zero under launcher PID `9864`.
- Every child stderr and asynchronous-error ledger is zero bytes.
- Primary and replay cohort manifests are byte-identical, SHA-256
  `522D246FBA9769F7EE3C11C95E2710F0FD956B933B4D83E7D0371FA1FE42BEB5`.
- Primary and replay metric payloads are identical, SHA-256
  `4ED3C09D7709E35EE15C2544E32543174EDA3BD0ADBDEA7B347CB040E0B54C7A`.
- Deep verification passed; its SHA-256 is
  `414C3F6E171CF291302A55E4F2C25EC254B2DD3A6807ADADAE9CFFC2EF2EAB18`.
- The completion marker was written last and has SHA-256
  `AF751E729B427453CDBC5E00BBA22E40E21CA858BD91A0C497843C07FFAEFC06`.
- No candidate suffix was present in the manifest. Candidate labels were not
  parsed, counted, or aggregated in Phase A.

The invoking process observed 122.4 seconds of wall time for the primary,
exact replay, deep verifier, and final publication together.

## Locked-gate result

The fixed cohort contains 64,443 eligible impressions, 43,374 distinct users,
and 2,422,258 candidates. It therefore exceeds the 5,000-impression and
2,000-user gates by large margins.

For the primary frozen MIND relation vocabulary:

| Measure | Observed | Locked gate |
| --- | ---: | ---: |
| score vector changed | 87.5720% | at least 20% |
| total order changed | 55.0021% | at least 5%, or Top-10 at least 2% |
| Top-10 set changed | 21.5524% | at least 2%, or order at least 5% |
| Top-1 changed | 9.9313% | descriptive |
| historical candidate score nonzero | 19.4328% | descriptive |
| current candidate score nonzero | 20.4293% | descriptive |

The median per-impression maximum absolute score change is `0.04223`; its
90th percentile is `0.08119`. This is not a numerical-tolerance artifact.

Both predeclared sensitivity views preserve the result:

| View | score changed | order changed | Top-10 set changed |
| --- | ---: | ---: | ---: |
| metadata/navigation blocklist | 84.9122% | 47.6856% | 15.4384% |
| remove `Q30` and `Q22686` | 85.4833% | 55.6088% | 22.1777% |

## Interpretation

H6 Phase A establishes a strong ranking consequence: substituting a current
Wikidata snapshot for the graph observable at the MIND cutoff changes most
structural score vectors and more than half of complete candidate orders under
a held-fixed parameter-free KG scorer. It does not yet establish that the
historical snapshot improves recommendation utility, nor does it make the
shared-fact scorer an algorithm contribution.

The exact committed manifest is now the sole Phase-B cohort. The separately
locked held-fixed outcome test may open candidate suffixes only after this
Phase-A result commit. H7 remains contingent on Phase B showing a practically
and statistically nontrivial recommendation effect beyond matched null graphs.
