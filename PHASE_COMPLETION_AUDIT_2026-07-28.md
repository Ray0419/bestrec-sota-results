# Phase-completion audit (2026-07-28)

This ledger reconciles `HANDOFF_CODEX.md`,
`PAPER_ACCEPTANCE_REPAIR_PLAN_2026-07-11.md`, and `EXPERIMENT_PROGRAM.md` against
the current paper and executable evidence graph. It distinguishes work that is
complete from work that is impossible to finish truthfully without a new
pre-declaration, new outcome-bearing runs, author decisions, or authenticated
deposit access.

## Executive verdict

- **Locally executable manuscript, mechanism, artifact, and review work:** complete,
  subject to the final clean-clone gate recorded below.
- **Submission metadata:** blocked on maintainer-supplied real author,
  affiliation, conflict, reviewer, preprint, and legal/licensing decisions. The
  manuscript intentionally retains explicit placeholders rather than invented
  identities.
- **New experiments:** the explicitly authorized parameter-matched pointwise-placebo
  phase was preregistered, committed, pushed, run with TEST sequestered during all 24
  training jobs, sealed-evaluated once, and mechanically adjudicated. Other interventions
  (local order and E-B/E-C/E-C2/E-D) remain new outcome-bearing work requiring their own
  frozen pre-declarations.
- **Final DOI/release publication:** blocked on the same metadata/legal decisions
  and authenticated archive access. A deterministic, explicitly unpublished
  candidate bundle can be built locally; no tag, GitHub release, or DOI is
  represented as existing before it actually exists.

## Ten-phase repair plan

| phase | status | current evidence |
|---|---|---|
| 1. Fail-closed artifact gate | **COMPLETE** | `rebuild_hstu_submission.py --strict` calls the strict table graph, manifest verification, governed adjudicators, HSTU parity, FIR causality, and the generated claim-to-artifact map. The graph currently recomputes 198 active paper cells across 22 families with zero mismatch/untraceable cells, including aggregate-only MovieLens negative-replication and WEARec current-baseline families. |
| 2. Remove or rerun old Table 1a | **COMPLETE (safe-removal path)** | Unretained v1 SASRec rows are excluded from the paper claim set and retained only as explicitly `RETIRED` provenance. No claim depends on them. |
| 3. Re-adjudicate Office honestly | **COMPLETE** | Office V1 remains permanently `VOID`. The separately pre-declared V3 campaign passes only the narrow environment-caveated, per-category point-estimate rule; it is not promoted to paired, distributional, or SOTA evidence. |
| 4. Bind Office to the artifact graph | **COMPLETE** | Office V1 and V3 cells, verdicts, external constants, and manuscript wording are graph-backed and drift-gated. |
| 5. Full-user Office sidecars | **COMPLETE** | Office V3 result arms have compressed per-user sidecars, including final-evaluation sidecars for the retained final rows; hashes/counts are release-manifested. |
| 6. Manuscript contradiction cleanup | **COMPLETE** | Category scope, core-block-only parity, comparator caveats, fixed-split inference, and the absence of any broad SOTA claim are aligned across abstract, results, limitations, conclusion, cover letter, and audit response. |
| 7. Lock permitted claims | **COMPLETE** | `CANONICAL_SUBMISSION.md`, `AUDIT_RESPONSE_2026-07-27.md`, and `CLAIM_ARTIFACT_MAP.md` define the same narrow claim boundary. Forbidden-wording and numeral-hygiene scans run during every build. |
| 8. Statistical cleanup | **COMPLETE** | Evidence timing/custody, randomized unit, interval/test method, multiplicity, fixed-split scope, outcome visibility, and null/deviated/VOID status are explicit. The 2026-07-28 audit also corrected TFV2's machine label from confirmatory to exploratory/outcome-visible and added a regression assertion. |
| 9. Reproducibility/release | **COMPLETE for public reconstruction; FINAL DEPOSIT BLOCKED** | The repository exposes two routes: hydrated-checkout strict rebuild and from-zero public-clone bootstrap followed by strict rebuild. `RELEASE_MANIFEST.json` pins public assets and repository files. A current candidate deposit is deterministic, but publishing/tagging/DOI minting awaits verified metadata and archive login. |
| 10. Presentation/PDF polish | **COMPLETE except author block** | The current TORS PDF uses `acmart` v2.19, has generated tables/figures, passes hygiene scans, and has been page-rendered and visually inspected. Real author metadata is intentionally unresolved. |

## Claude handoff phases

| handoff item | status | disposition |
|---|---|---|
| Canonical nonsingular FIR | **COMPLETE** | Canonical implementation, matched initialization, preregistration, and MI result are integrated. |
| Canonical breadth transfer | **COMPLETE** | Industrial_and_Scientific and CDs_and_Vinyl breadth results and adjudication are integrated with outcome-visible wording. |
| Active controls | **COMPLETE** | Fixed, shared, and parameter-matched nonlinear causal controls are integrated. A later equal-parameter current-position-only placebo is also complete: learned FIR beats it while its identity contrast spans zero (`POINTWISE-FIR-DISCRIMINATED`). This discriminates learned FIR from that compound placebo but does not isolate temporal access; the competitive shared causal filter still prevents per-channel-tap attribution. |
| Manuscript rewrite | **COMPLETE** | The paper is organized as a modular-contribution study with the audit apparatus and negative results preserved; the journal-format length is deliberate rather than a conference-short target. |
| Causality unit test | **COMPLETE** | `test_fir_causality.py` is in the strict chain and checks 18/18 future-perturbation cases, including the pointwise path and FIR positive control. |
| Tap/frequency-response diagnostic | **COMPLETE** | Deterministic learned-tap and magnitude-response data/figure are generated from bound checkpoints and included as descriptive mechanism evidence. |
| Local-order intervention retrain | **NOT RUN — SEPARATE NEW EXPERIMENT** | The parameter-matched pointwise placebo now addresses temporal versus non-temporal access on outcome-known MI. A local-order intervention would test a different mechanism and still requires a new frozen protocol and fresh seeds; it is not needed to represent the completed placebo result. |
| Two reproduction paths | **COMPLETE** | Both paths are written in `CLAIM_ARTIFACT_MAP.md`; the public-clone route is automated by `bootstrap_public_clone.py`. |
| Claim-to-artifact map | **COMPLETE** | `CLAIM_ARTIFACT_MAP.md` is deterministically generated and verified by the strict rebuild. Its verifier now requires every active cell to appear exactly once, closing the prior six-cell omission. |
| Manuscript-matched deposit | **CANDIDATE COMPLETE; PUBLICATION BLOCKED** | Candidate metadata and bundle are current, deterministic, and marked unpublished. A final immutable tag/asset/DOI cannot be truthfully created before author/legal verification. |
| Mock review and cover letter | **COMPLETE as drafts** | Current files reflect the narrowed claims and remaining metadata fields. Maintainer fields remain visibly bracketed. |

## Optional experiment program

The unchecked E-B (text permutation/random features), E-C (training-target
multiplicity parity), E-C2 (thinning-draw replication), and E-D
(frequency-conditioned text gate) tasks are scientifically useful but optional
acceptance-upside experiments. They must not be backfilled post hoc into the
current evidence class. E-E V2's outcome-visible AlphaFuse package comparison
remains quarantined. A separate E-E V3 protocol is now frozen before any of its
fresh seeds or endpoints exist; it uses complete-history-masked selection and
evaluation, sealed first-reader adjudication, and a whole representation-package
framing. Its eventual result remains outcome-known, same-investigator exploratory
evidence rather than independent confirmation.

## Remaining human-controlled submission gate

Before submission, the maintainer must supply and verify:

1. legal author names, order, affiliations, emails, and ORCIDs;
2. conflicts, suggested/opposed reviewers, and preprint/related-submission status;
3. license/redistribution approval for the archival bundle;
4. the target submission date and TORS portal-required fields; and
5. if desired, authenticated GitHub/Zenodo publication of the already checked
   candidate followed by insertion of the real DOI.

None of these fields is inferred from a username.
