# H6 Phase-A Implementation Lock

Status: frozen before confirmatory execution

Date locked: 2026-08-07

- Runner: `code/run_h6_phase_a_coverage.ps1`
- Runner SHA-256:
  `D1CA7A0E1F59CCD31D1C74B71B4DB8EB3D9E676AF0CDFDCC4CA5932BA3AC5B7E`
- Protocol SHA-256:
  `53EAE6D5D19982DD5E6926F563A6D327A5A1AF47DFC5CF58DA4D54D1D61DB0A4`
- Runtime: Windows PowerShell 5.1, one process, no Python, BLAS, workers, or
  network access.
- Parser: clean.
- Synthetic self-test: `H6_PHASE_A_SELFTEST_OK`.

The runner records its runtime hash and the protocol hash in `result.json` and
rehashes every immutable data input immediately before publication. A result
is accepted only after an external second full replay produces the identical
cohort-manifest hash. This replay requirement is intentionally not asserted by
the runner itself.

The streamed cohort manifest is a local Phase-B input and is excluded from Git
because it may be large. Its exact byte hash and schema remain in the committed
result and artifact manifest.
