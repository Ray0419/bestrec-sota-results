# Impact-revision program (maintainer-approved, 2026-07-12)

Goal: raise the submission's significance/impact while keeping every discipline that survived
14 audit rounds. Three approaches, all authorized to run to completion:

**(A) Office second-category confirmation, redesigned (`PREREG_OFFICE_V3.md`).** The original
Office pre-registration was VOIDed by its own floor check — correctly, because it assumed
cross-environment comparability with a published number. The redesign gates against the
**environment-matched local regeneration of the comparator** (their unmodified code on its own
pipeline, run on this machine: Office HSTU-BLaIR best full-eval NDCG@10 0.0279, final 0.0275),
eliminating by construction the comparability failure mode that killed round one. New
never-inspected seeds; the old VOID campaign stays VOID and is not merged.

**(B) FIR-lever breadth (`PREREG_FIR_BREADTH.md`).** The causal FIR filter is currently
multi-seed-confirmed on two categories. Add two new categories (Industrial_and_Scientific,
CDs_and_Vinyl; fallback Toys_and_Games if CDs is infeasible on 16 GB) with a paired
filter-vs-no-filter 5-seed contrast under the frozen V2 configuration — an *internal* contrast,
so no comparator assumptions at all. Null results are reported with the same prominence as wins.

**(C) Methodology reframe (writing only; no claim changes).** Reorder the paper so the
**trustworthy-evaluation methodology** — pre-registration protocol, fail-closed artifact gate
recomputing every printed number, comparator regeneration harness, self-VOIDing adjudication —
is the lead contribution, with the FIR/MI/tail results as its demonstrations. Constraints:
no caveat may be weakened, no claim broadened, all forbidden wordings remain forbidden; this is
an emphasis reordering, not a claims change. New related-work coverage of RecSys
reproducibility/evaluation practice.

## Standing rules for this program

- **Prereg-before-run**: both pre-registrations are committed before their first GPU run; fresh
  seeds are never-inspected (breadth: 20260713–17; Office V3: 20260728–32 — disjoint from every
  previously used seed family).
- One GPU job at a time; breadth runs first (short), Office V3 after (long).
- `results_*.json` are append-only artifacts (rename-preserve, never overwrite).
- Every landed result enters the artifact manifest (fail-closed `--submission` gate) before the
  paper prints it; the strict wrapper must pass at every commit.
- Honest reporting is symmetric: pre-registered nulls and fails are published with the same
  prominence as passes (as the Office V1 VOID was).
