# Handoff — canonical-FIR restructuring program (2026-07-25)

**State:** branch `codex/bestrec-sota-results`, HEAD `e055f9d0`, tree clean, all pushed. GPU **idle**.
Rollback point if needed: tag `pre-fir-restructure-20260725`.

## What just happened

Executing the maintainer's 10-phase plan to refocus the paper on ONE primary claim: the
canonical causal FIR module (see `PAPER_DEADLINE_PLAN.md` progress log for the running record).

1. **Phase 1 DONE (`eb538476` md, `34e78c53` tex):** the CANONICAL FIR — nonsingular,
   gradient-active, identity-initialized (`x' = x + DWConv_Δ(pad_left(x))`, Δ=0, no absorbing
   gate) — is now the *proposed method* in title + §3(b) + intro, in both papers. The historical
   zero-gated form is renamed **legacy zero-gated FIR package** and kept package-level only.
2. **Phase 2 DONE (`e055f9d0`): verdict `CANON-BREADTH-POS`, 2/2 categories PASS.**
   Prereg + adjudicator + driver were frozen and committed BEFORE launch (`a6775c6a`).

   | category | canonical FIR − identity | 95% CI | seeds | |
   |---|---|---|---|---|
   | Industrial_and_Scientific | +0.002110 | [+0.001820, +0.002399] | 8/8 | Holm-SIG |
   | CDs_and_Vinyl | +0.006150 | [+0.005849, +0.006450] | 8/8 | Holm-SIG |

   32/32 runs, matched per-seed init (`init_state_sha256` equality enforced), identity-control
   taps verified L2=0, one frozen config, **zero per-category tuning**. Canonical FIR isolation
   now holds on **three** categories (MI via E-A/`PREREG_FIR_V3`, + these two).
   Artifacts: `PREREG_FIR_CANONICAL_BREADTH.md`, `_bestrec_run/run_fir_canonical_breadth.py`,
   `_bestrec_run/adjudicate_fir_canonical_breadth.py`,
   `_bestrec_run/fir_canonical_breadth_adjudication.json` (verbatim verdict, committed).

## Next actions, in priority order

1. **Integrate the breadth verdict — NOT yet in the manuscript.** The numbers must become
   gate-bound cells in `_bestrec_run/build_hstu_tables.py` traceable to
   `fir_canonical_breadth_adjudication.json` (otherwise the strict gate flags them
   UNTRACEABLE), then prose in intro / §3(b) / §5.2 of **both** md and tex. Run the full RITUAL.
2. **Phase 3 controls — the other half of the acceptance gate; GPU is idle.** Needs new trainer
   arms (fixed causal moving-average, fixed causal high-pass, channel-shared FIR,
   parameter-matched causal-conv comparator), all identity-at-init + gradient-active + shared
   backbone init + equal tuning budget. **Freeze a new prereg + adjudicator BEFORE launch.**
3. **Phase 6 rewrite (CPU, parallel with GPU):** cut 55pp → ~25pp; relocate EASE / sparse-warm
   fusion + Office VOID chronology + titrations to the supplement; demote TAPE to a supporting
   ablation; replace the self-assigned "novelty grade" column with **claim boundary**; align
   conclusion + results headings to the canonical method; strip audit-log prose; state
   "no general SOTA claim" ONCE.
4. **Phase 4 mechanism:** causality unit test (CPU, cheap — do it early); learned-tap /
   frequency-response plots; local-order intervention retrain (GPU).
5. **Phase 7–9:** two reproduction paths + claim-to-artifact map; manuscript-matched deposit tag;
   mock reviews; cover letter.

## Non-negotiables (do not relax)

- **HARD RULES:** never delete/overwrite `results_*.json` (rename-preserve only); never modify
  `external/HSTU-BLaIR`; never edit audit files beyond `git add`; **one GPU job at a time**;
  claims may only NARROW — new claims enter ONLY via a new frozen pre-registration committed
  BEFORE launch, with its mechanical adjudicator.
- **CLAIM BOUNDARY** (`CANONICAL_SUBMISSION.md` governs): two counted comparisons only —
  Musical_Instruments (vs published 0.0406) and Office_Products **V3** (vs 0.0271 published AND
  0.0279 environment-matched regeneration). Office **V1 is VOID/descriptive forever**; TFV2 is
  outcome-visible, **not** confirmatory.
- **The breadth result is an INTERNAL matched-init filter-vs-identity contrast.** Not SOTA, not a
  comparator claim, not paired/distributional superiority. Do not upgrade its wording.
- **FORBIDDEN anywhere:** SOTA of any kind, "significantly better than HSTU-BLaIR",
  "official/pinned reproduction", training-level equivalence, Office V1 as passed, Office V3
  beyond frozen wording, TFV2 as confirmatory. Reference-implementation runs stay
  "environment-caveated single-run regenerations". Never weaken a caveat to close a finding.
- **RITUAL after edits:** `build_hstu_tables.py --write-manifest` (if cells changed) →
  `render_paper_pdf.py` must print `scan: CLEAN` → mirror to `paper_tex/` and
  `bash paper_tex/build.sh` must PASS (H1–H9) → `update_release_manifest.py --regen` (if a
  manifested file changed) → commit → `rebuild_hstu_submission.py --strict` **exit 0** →
  push → `gh release upload v0.9-audit-evidence RELEASE_MANIFEST.json --clobber`.

## Known blockers

- **Author byline is a placeholder** (`paper_tex/paper-shared.tex:37`) — HUMAN TODO. The paper is
  ~0% submittable until filled; `build.sh` H10 fails strict and currently needs `--draft`.
- Deposit (v1.1.12) should be cut only **after** byline + manuscript stabilization; DOI minting
  needs the maintainer's account.
- Negative/failed outcomes are reported with the same prominence as wins. If Phase 3 shows fixed
  averaging matches learned FIR, the claim narrows to "simple causal local filtering suffices" —
  narrow it immediately rather than adding seeds until a threshold is crossed.
