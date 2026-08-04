# Gate-5 Conformance Decision — PREREG_COLDFUSE_V1 (dated, versioned, integrity-only)

**Date:** 2026-07-23 (before any full-set adjudication of PREREG_COLDFUSE_V1;
the 25th confirm file is still being produced at commit time).
**Trigger:** audit 2026-07-23 09:01, "Integrity gates, runner and provenance"
— CONFIRMED contradiction: the prereg's Gate 5 prose ("base config echo
equals the reference config on every key except seed/out/save_ckpt/fir_v3*")
read literally over the KEY UNION fails MI and VG (36/38 extra keys in the
new configs), while the committed adjudicator implemented only a
seed/category check. IS passes literally. The audit's remedy is adopted
verbatim: decide conformance BEFORE final adjudication, outcome-independently,
and preserve BOTH gate outputs.

## Decision (normalization rule, outcome-independent)

Gate 5 is evaluated in TWO forms, both recorded in the adjudication JSON:

1. **Literal:** dict equality over the key union minus the exempt set.
   Expected and accepted outcome: MI FAIL-literal, VG FAIL-literal, IS PASS
   (recorded as such; nothing is hidden).
2. **Normalized (governing form):**
   a. For every key PRESENT IN THE REFERENCE config (minus exempt), the run
      config value must equal the reference value — the original mechanical
      test, now actually implemented.
   b. Every EXTRA key (present only in the run config, minus exempt) must be
      **provably untouched by the driver**: the adjudicator reconstructs the
      exact command line the driver builds (a deterministic function of the
      reference config alone) and asserts the extra key's flag NEVER appears
      on it. An extra key that was never passed received its argparse
      default, i.e. the feature's disabled state — the same behavior the
      reference-era code had by not having the feature at all.

## Why this is outcome-independent

Both checks consume only: the frozen reference JSONs, the run config echoes,
and the driver's deterministic command constructor. No metric, score, seed
outcome, or NPZ is read. The rule was fixed by this document BEFORE the
full-set adjudicator was ever executed; the MI/IS/VG outcome visibility that
already existed cannot steer a rule that never touches outcomes. Supporting
evidence that extras are era-artifacts, not interventions: IS (whose
reference was recorded 2026-07-22, same parser era) matches literally;
MI/VG references predate the fir_v3/save_ckpt/cold-synth/zfusion flag
additions.

## Scope and preservation

- Applies to PREREG_COLDFUSE_V1 adjudication only; future preregs must write
  Gate 5 in the normalized form explicitly.
- The adjudication JSON records, per category: literal verdict, normalized
  verdict, the exact extra-key list, and the pointer to this document.
- Claims may only narrow; if the normalized gate fails for any run, the
  adjudication refuses (exit 2) exactly as a literal failure would.
- Independent verification: `adjudicate_coldfuse_v1.py --gate5-report` prints
  the full per-category key diff without running any statistics.
