# PAPER_SPINE — the rewrite blueprint (28.4k dossier -> ~20–35pp acmsmall)

Started 2026-07-24. This is the target structure the manuscript is rewritten
INTO: a tight **rigor / reproducibility methods paper**, not a novelty flagship
(that framing fits the evidence and the achievable venue, per the acceptance
calibration). Every claim stays inside CANONICAL_SUBMISSION.md; nothing here
broadens a claim. Forensics/chronology move to a labelled supplement.

## Thesis (one sentence)
Under a fixed, pre-registered, honestly-reported leave-last-out protocol on
Amazon Reviews 2023, we report what actually holds for text-augmented sequential
recommendation — two environment-caveated point-estimate matches to published
numbers, a set of component ablations, and an honest negative/boundary result —
with pre-registration and test sequestration as the method's backbone.

## Main body spine (target ~9–13k words; each section: budget · source · cut)

1. **Introduction** (~900w) — the reproducibility question + why honest scoping.
   Source: current intro, stripped of any SOTA/novelty framing. Cut: hype.
2. **Protocol** (~1200w) — 5-core LLOO split; the SASRec-SBERT stack; the ONE
   evaluator (full-catalogue, seen-item masked, strict-greater ties); the
   pre-registration + sequestration discipline. Source: §3 conventions + methods.
3. **Primary results** (~1500w) — the TWO counted point-estimate comparisons:
   Musical_Instruments (vs 0.0406) and Office_Products V3 (vs 0.0271 / regen
   0.0279), NDCG@10 + the HR/NDCG/MRR@{5,10,20,50} family, full caveats. Source:
   §5 results tables. Cut: any paired/superiority phrasing.
4. **Component ablations** (~1800w) — FIR (E-A), EASE late-fusion (E-F), and the
   closest-comparator **fusion factorial** (E-E V2: AlphaFuse fusion on/off under
   the shared evaluator). Reported as effects with equal prominence to nulls.
5. **Honest negatives & boundary** (~1500w) — cold-start reclassified as
   sparse-warm redistribution (not cold-start); Office V1 VOID (floor-check
   failure, mechanistically explained); the "SOTA not achievable in this
   environment" boundary (reference kernels can't run on sm_120). Told as the
   paper's integrity centrepiece.
6. **Limitations & reproducibility** (~900w) — environment caveats, the explicit
   forbidden-claim list as honest scoping, artifact/manifest availability.
7. **Related work** (~800w) — AlphaFuse + LLM2Emb positioned honestly (closest
   comparators; fair benchmark or executable exclusion). Cut: padding.

## Supplement (labelled; not the main narrative)
Correction ledger; campaign chronology; full per-seed tables; the E-E V1
quarantine + erratum trail; TFV2 outcome-visibility disclosure; forensic detail.

## Submission-readiness fixes (blocking; do during the rewrite)
- [ ] Real author/affiliation/contact metadata (replace maintainer placeholder). *(human decision — flag to maintainer)*
- [ ] Remove `PAPER_DRAFT.md` "delete before submission" block (or exclude PAPER_DRAFT from the deposit).
- [ ] Replace "null / refuted / refutation" with "estimate crosses zero / no evidence of a trend / non-reproduced" everywhere (md + tex + captions).
- [ ] Abstract: fix "every / all public" scope overclaims to the bounded truth.
- [ ] Figures: replace the overloaded 3-panel composite with one forest/stratum plot (per-seed dots + CIs) + one compact ablation table.
- [ ] Near-empty final reader page; reference-density/overfull pass.
- [ ] Semantic parity check across md / tex / extracted PDF text before each rebuild; strict gate exit 0.

## Execution order (section at a time, each its own commit + strict gate)
Protocol -> Primary results -> Ablations (after E-E V2 factorial adjudicates) ->
Negatives/boundary -> Intro/abstract -> Related work -> Limitations -> figures ->
move forensics to supplement -> full render + tex mirror + H1–H9 + strict.

## Guardrails (unchanged)
Counted set = MI V2 + Office V3 only; FORBIDDEN list applies verbatim; every
paper edit runs the full ritual (render "scan: CLEAN", tex build H1–H9, strict
exit 0). The rewrite REORGANISES and TIGHTENS; it does not invent results.
