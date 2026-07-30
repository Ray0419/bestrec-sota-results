# CANONICAL SUBMISSION — single source of truth (full-method audit F1; updated for round-2 audit F1, 2026-07-11)

**The one canonical authored source:** `PAPER_SUBMISSION.md`. Its reader rendering is
`PAPER_SUBMISSION.pdf`; the ACM/TORS source under `paper_tex/` is the venue mirror, with
generated quantitative tables and strict source/PDF claim checks. `PAPER_DRAFT.md` is a
historical, noncanonical working record retained for provenance; it is not a submission
source and need not match the live claim set. Everything else is archived (see
`archive_noncanonical/README.md`) or marked non-canonical
(`_bestrec_sota_lab/paper_draft/NONCANONICAL.md`).

## The canonical claim set (nothing broader is claimed anywhere)

1. **MI point-estimate result (externally approved; the first of the two counted
   per-category point-estimate comparisons — see item 3 for Office V3):** fresh 5-seed CI lower bounds exceed the published HSTU-BLaIR Musical_Instruments
   point estimate (0.0406) for both kernels (K=16 CI-LB 0.04096, K=8 CI-LB 0.04083, 10/10 fresh
   seeds above) — per-category point-estimate comparison, not paired superiority, not general
   SOTA. The comparator has additionally been **locally regenerated** by running the reference
   implementation itself (best full-eval epoch NDCG@10 = 0.0406 exactly; environment-caveated
   single run, §5.6 / `THEIRS_ON_OURS_REPORT.md`) — regeneration, never "official reproduction".
   Evidence: `SOTA_CONFIRM_PREREG_V2.md` → `SOTA_CONFIRM_V2_RESULTS.md` (+ errata).
2. **FIR treatment package (filter + initialization + optimizer path):** multi-seed package-arm estimates positive on **four categories** (Video_Games +
   Musical_Instruments in development; Industrial_and_Scientific + CDs_and_Vinyl under the
   pre-declared breadth campaign `PREREG_FIR_BREADTH.md` / `FIR_BREADTH_RESULTS.md` —
   both categories fired the frozen decision rule ("CONFIRMED" per its mechanical
   adjudication), with the rule's *paired interpretation withdrawn* 2026-07-19 (same-seed
   arms are not initialization-paired; manuscript §5.3): the primary supported analysis is
   the post-hoc independent-arm Welch (the earlier 'conservative' characterization is retracted), both 95% CIs excluding zero; the
   treatment is the FIR-plus-initialization/optimizer package). Comparator ablations **complete** (5-seed × 2 arms, manuscript §5.2):
   the fixed moving-average arm keeps ~59% of the gain — an observation confounded by the shared singular start (§3): no learned-shape attribution is claimed; the zero-init gate comparison is confounded by the singular-initialization bootstrap. Artifacts: `results_FIRABL_*` (manifest family `tableV2conf`/FIR
   cells).
3. **Office_Products — V1 VOID stands; V3 PASSED (the second counted per-category
   point-estimate comparison).**
   The V1 pre-declaration is **VOID under its floor check** and stays VOID — descriptive
   only, counted in no claim; the floor anomaly is mechanistically explained (their own
   SASRec run locally lands +13.9% above its published row; their Office HSTU-BLaIR row
   regenerates locally at +1.6%) and no post-hoc result restores a voided pre-declaration
   (`SOTA_CONFIRM_PREREG_OFFICE.md`, `SOTA_CONFIRM_OFFICE_RESULTS.md`, Appendix A.0,
   `THEIRS_ON_OURS_REPORT.md`). The **redesigned V3 pre-declaration PASSED**
   (`PREREG_OFFICE_V3.md` + ERRATUM E1; `OFFICE_V3_RESULTS.md`): fresh never-inspected
   seeds 20260728–32, gate vs the environment-matched local regeneration (0.0279 > published
   0.0271) — K=16 CI-LB **0.03033**, K=8 CI-LB **0.03024**, 10/10 seeds above both
   references. Claim capped at the frozen wording: per-category point-estimate comparison;
   no paired superiority; not SOTA of any kind.
   Also under this item: the **MI frequency-5 tail case** +
   thinning-intervention evidence (intervention-scoped wording) is unchanged.
4. TAPE as a modest secondary component; negative results labeled exploratory unless multi-seed.
5. Reproducibility: provenance manifests, per-user sidecars (MI tracked; Office/FIR-breadth
   per-user sidecars local-only/untracked, not part of any counted claim), clean-rebuild
   demonstration, and the fail-closed artifact gate below. **Sidecar deposit policy:** the
   tracked/released-artifact boundary is the reproducibility contract: the 196 declared
   empirical cells recompute from graph-bound artifacts, while literature/interpretive prose
   is outside that numerical graph. Graph coverage and release-manifest coverage are distinct;
   we do not claim every transitive graph source is explicitly listed in the release manifest.
   Local-only per-user sidecars are supplementary
   audit material, hash-pinned in tracked run manifests, provided on editorial/reviewer
   request and deposited as supplementary material upon acceptance (paper §8).

## Canonical artifact graph

- Prereg chain: `SOTA_CONFIRM_PREREG_V2.md` (+ `_ERRATA`), `SOTA_CONFIRM_PREREG_OFFICE.md`,
  `PREREG_OFFICE_V3.md` (+ ERRATA E1/E2; results `OFFICE_V3_RESULTS.md`),
  `PREREG_FIR_BREADTH.md` (results `FIR_BREADTH_RESULTS.md`), and
  `PREREG_FIR_CANONICAL_BREADTH.md` (mechanical verdict
  `_bestrec_run/fir_canonical_breadth_adjudication.json`), plus
  `PREREG_FIR_EFFICIENCY_ML1M_V1.md` (prospective non-Amazon verdict
  `_bestrec_run/fir_efficiency_ml1m_v1_adjudication.json`),
  `PREREG_WEAREC_BASELINE_V1.md`, and `PREREG_EE_V3.md` (outcome-known
  current-comparator verdicts `_bestrec_run/wearec_baseline_v1_adjudication.json`
  and `_bestrec_run/ee_v3_adjudication.json`)
- Results of record: `_bestrec_run/results_SOTACONF_V2_*.json` (+ tracked sidecars +
  `SOTACONF_V2_sidecar_manifest.json`), `_bestrec_run/rebuild_v2/`, `results_OFFICE_*`
  (present; descriptive/VOID), `results_FIRABL_*` (present), `results_OFFICEV3_k{16,8}_seed*.json` (+ per-run tree-state sidecars), `_bestrec_run/results_FIRB_*` (20 tracked breadth runs), the reference-implementation run
  artifacts `_bestrec_run/results_*_FIRCANON_*.json` (32 matched-initialization canonical-breadth runs), `_bestrec_run/results_Musical_Instruments_FIRPOINTV1_*` (24 matched-initialization pointwise-placebo runs plus sealed evaluations), `_bestrec_run/theirs_runs/*/metrics.jsonl` (+ `run_meta.json`, preprocess
  provenance), `_bestrec_run/results_Software_FIRPROSPV3_*` (16 protocol-frozen
  matched-initialization training records plus sealed evaluations), and the per-table
  source families enumerated in `_bestrec_run/hstu_results_manifest.json`. MovieLens
  record-level data, checkpoints, endpoints, and per-user sidecars remain private under
  the ML-1M README; only aggregate adjudication/provenance is public. E-E V3
  likewise releases only the compact aggregate adjudication; its 16 TEST endpoints,
  rank sidecars, and checkpoints remain private and are represented by a recorded hash ledger.
- Table generation (fail-closed): `_bestrec_run/build_hstu_tables.py` regenerates every
  empirical table from the manifest; **`--submission` exits nonzero** on any UNTRACEABLE cell,
  any printed-numeral MISMATCH, or any required claim family without sourced cells
  (invariants: 0 mismatch / 0 untraceable / every required family sourced; the
  authoritative family/cell counts are the strict build's own output)
- Canonical one-command verification: `python _bestrec_run/rebuild_hstu_submission.py --strict`
  (parity test → strict `--submission` build → release-manifest verification → MI V2
  adjudicator → **Office V3 adjudicator (counted; build fails unless CAMPAIGN VERDICT:
  PASS)** → **TFV2 repaired-estimand adjudicator (counted integrity gate; Git-declared frozen rules; outcome-visible — not confirmatory, §5.3 disclosure (vii); ALL PASS required)** → **FIR-breadth frozen-rule adjudicator (artifact-integrity; paired interpretation withdrawn)** → **E-A canonical FIR adjudicator** → **canonical FIR breadth adjudicator (`CANON-BREADTH-POS` artifact verdict required; manuscript evidence-class outcome-known/test-exposed)** → **FIR active-control adjudicator (`CTRL-ACTIVE-CONTROL-SUPPORTED` artifact verdict required; outcome-known exploratory mechanism study)** → **FIR pointwise-placebo adjudicator (`POINTWISE-FIR-DISCRIMINATED` required; outcome-known exploratory mechanism study)** → **Software V3 recorded protocol verdict (`SW-V3-PRACTICAL-POS` required; graph independently recomputes all sealed endpoints and the practical rule; outcome-known/exploratory same-team robustness, not independent confirmation)** → **MovieLens aggregate verdict (`ML1M-NO-FIR-REPLICATION` required; graph recomputes public aggregate seed vectors, Holm/NI arithmetic, and resource rows but cannot replay private record-level endpoints)** → **WEARec aggregate verdict (`WEAREC-BELOW-EXISTING-REFERENCE` required; outcome-known official-code/equal-evaluation feasibility evidence)** → **E-E V3 aggregate verdict (`EEV3-REPORTABLE-OUTCOME-KNOWN` required; graph recomputes released summaries/contrasts and checks private endpoint/sidecar ledger shape, hash-string syntax, and uniqueness without reading the private files; whole-package same-investigator evidence, not independent confirmation or SOTA)** →
  Office V1 adjudicator (descriptive/VOID, non-gating)) — passes end-to-end at the
  submitted commit; `update_release_manifest.py --verify-git <intended_deposit_tag>`
  additionally checks the manifest against the git blobs at the deposit tag
- Parity: `_bestrec_run/test_hstu_parity.py` + `HSTU_PARITY_REPORT.md` (bitwise-exact core
  block) and the reference-implementation shim harness `_bestrec_run/fbgemm_shims.py` +
  `theirs_*.py` (`THEIRS_ON_OURS_REPORT.md`)
- Adjudicators: `summarize_sota_confirm_v2.py`, `office_prereg_tools.py` (idempotent appends;
  output carries the VOID banner)
- Release/provenance: `RELEASE_MANIFEST.json` — split/cache/protocol/result AND
  submission-doc/PDF/parity-artifact hashes, kept in sync **mechanically**: the strict
  wrapper runs `update_release_manifest.py --verify` and fails the gate on any drift;
  regenerate with `--regen` (+ commit together) whenever a manifested file changes.
  GitHub release `v0.9-audit-evidence` supplies data/result/parity assets. The next
  manuscript-matched deposit is the **unpublished intended candidate**
  `v1.2.0-deposit`; it is not a tag or release until verified creator/legal metadata is
  supplied. Historical `v1.1.11-deposit` is stale relative to this manuscript and remains
  provenance only. The tracked `_bestrec_run/build_deposit_bundle.py --candidate` prepares
  the current bundle without claiming publication (`DOI_DEPOSIT_INSTRUCTIONS.md`).
- Audits + responses: `CLAUDE_SOTA_*AUDIT*.md`, `STRICT_*AUDIT*.md` (incl.
  `STRICT_RESUBMISSION_AUDIT_ROUND2_2026-07-11.md`), `RESPONSE_TO_*.md`

Old-track artifacts (`archive_noncanonical/`, `_bestrec_sota_lab/paper_draft/`) feed nothing here.

## Noncanonical root-level PDFs (disambiguation note, 2026-07-19)

Three legacy PDFs at the repository root are **not** part of this submission and must not be mistaken for submission artifacts: `BERT-Embedded Self-attention Transformer Recommender (BEST-Rec)_ Tackling Sparsity and Cold-Starts.pdf`, `BEST_Rec_v4_Sections_3-8.pdf`, and `BEST_Rec_v4_Sections_3-8_Elaborated.pdf` — they are the maintainer's separate earlier manuscript line (noncanonical, unmanifested, never cited by the canonical papers; disposition is the maintainer's call). The only canonical root PDF is `PAPER_SUBMISSION.pdf` (reader rendering); the venue artifact is `paper_tex/PAPER_TORS.pdf`.

## Pre-declared post-v1.1.11 additions (2026-07-22/23)

Registered here so the claim ledger stays canonical; each entered ONLY through its frozen pre-declaration committed before launch, and each may only narrow further. The FORBIDDEN wordings above remain in force unchanged.

1. **E-A (PREREG_FIR_V3, verdict W-POS; outcome-visible exploratory evidence):** learned FIR taps vs identity control, +0.002265 [+0.001928, +0.002602] NDCG@10 (MI, frozen V2 config, 8 seed blocks, per-seed init-state hash equality verified). The A2−A1 weight-decay sensitivity is +0.000010 [−0.000339, +0.000360], p=.95: no difference detected, not equivalence and not a pathway exclusion. The reused split and documented provenance deviations preclude fresh-confirmation status. Artifacts: results_MI_FIRV3_*, fir_v3_adjudication.json.
2. **E-F (PREREG_HYBRID_V1, verdicts W-H-POS on MI/IS/VG):** late z-score fusion with train-only EASE changed test NDCG@10 by +0.00244 [+0.00219, +0.00268] (MI), +0.00261 [+0.00211, +0.00310] (IS), +0.00317 [+0.00286, +0.00348] (VG); five fresh seeds each; significance attaches to fused-vs-sequential only. Pre-declared point-estimate rows: MI fused five-seed mean 0.04399 exceeds the published single-run 0.0406; VG 0.07031 remains below 0.0760; MI ensemble5 0.04557 (ensemble frame). Artifacts: results_*_HYBRIDV1_*, hybrid_v1_adjudication.json.
3. **E-G (PREREG_COLDFUSE_V1) — OUTCOME-VISIBLE, PROTOCOL-DEVIATED; NO confirmatory status; descriptive estimates only (reclassified per audit 2026-07-23 15:59).** The no-interim clause was violated (mid-campaign endpoint commits/reports); the LITERAL frozen Gate 5 FAILS MI and VG and governs; the amended gate/adjudicator postdate 24/25 outcome visibility (sensitivity only; v1/v2/v3 all preserved with hashes). Descriptive tail-bin estimates: +0.00217 (MI), +0.00243 (IS), +0.00337 (VG), +0.00114 (Office), +0.00481 (CDs); near-threshold sparse-warm redistribution (frequency-0 never moved; mid/head means negative); intervals are optimizer-seed intervals on one exposed split. NOTHING here is counted. E-G2 (the intended clean replication) is ALSO now EXPOSED/protocol-deviated — a git add -A on commit df5afc9f swept 54 COLDFUSE2 artifacts (incl. 28 confirmation artifacts = 14 JSON/NPZ pairs) to the public branch; completion later remained descriptive and UNADJUDICATED (no E-G2 adjudication ever occurred) (audit 2026-07-23 22:00) — so it cannot be counted either; the sole remaining path is a future repository-sequestered E-G3. Artifacts: results_*_COLDFUSE_*, coldfuse_v1_adjudication.json (+ preserved v1/v2 outputs), GATE5_CONFORMANCE_DECISION.md.
4. **FIR active controls (PREREG_FIR_CONTROLS; verdict CTRL-ACTIVE-CONTROL-SUPPORTED; outcome-known exploratory evidence):** all temporally active arms beat identity after Holm adjustment. Learned taps beat the fixed MA/HP arms, which are algebraically redundant scalar/sign parameterizations, but did not separate from channel-shared or parameter-matched nonlinear causal controls. This campaign alone did not isolate temporal access. The sealed final evaluator does not repair dirty-tree execution or the sidecar-custody suffix error; author verification of any pre-adjudication human visibility remains required. Artifacts: results_Musical_Instruments_FIRCTRL_*, fir_controls_adjudication.json.
5. **FIR pointwise placebo (PREREG_FIR_POINTWISE_V1; verdict POINTWISE-FIR-DISCRIMINATED; outcome-known exploratory evidence):** an identity-initialized, gradient-active, current-position-only DCT/GELU/linear residual has the same 1,024 trainable parameters as the K=16 depthwise FIR. Pointwise−identity is −0.000069 [−0.000200,+0.000061], while learned FIR−pointwise is +0.001941 [+0.001788,+0.002095] and rejects after Holm adjustment. This discriminates learned FIR from that tested compound placebo; because basis/rank, activation, channel mixing, and temporal access change together, it does not isolate temporal access or establish per-channel-tap necessity. It is not independent confirmation or cross-domain replication. Artifacts: results_Musical_Instruments_FIRPOINTV1_*, fir_pointwise_v1_adjudication.json.
6. **Frozen Software robustness result (PREREG_FIR_PROSPECTIVE_SW_V3; verdict SW-V3-PRACTICAL-POS):** learned−identity is +0.005062, ordinary paired 95% CI [+0.004591,+0.005533], paired-difference SD 0.000563779, paired t(7)=25.39, p=3.75×10⁻⁸, with 8/8 positive differences; a post-hoc two-sided exact sign sensitivity gives p=.0078125. The CI lower bound exceeds the frozen +0.000500 reporting threshold. Training used validation-only checkpoint selection and no TEST scoring, followed by one sealed TEST evaluation per checkpoint and protocol-designated adjudication. Because tracked evidence cannot establish non-visibility of earlier V2 validation output, the manuscript classifies V3 outcome-known/exploratory. Its local exclusive-created, hash-linked seals are not external custody, and the frozen tag has a disclosed raw-line-ending reference-hash replay defect. Scope remains same-investigator, same-code-lineage, same-Amazon-family evidence, not independent confirmation or cross-domain replication. Artifacts: results_Software_FIRPROSPV3_*, fir_prospective_sw_v3_{attempt,ready,endpoints_complete,status,adjudication}.json, FIR_PROSPECTIVE_SW_V3_REPLAY_ERRATUM.md, figures/fig_software_v3_pairs_{data.csv,pdf}.
7. **Prospective MovieLens parsimony/efficiency result (PREREG_FIR_EFFICIENCY_ML1M_V1; verdict ML1M-NO-FIR-REPLICATION):** on the rating≥4 global-time primary view, learned−identity is +0.000000 [-0.000074,+0.000075], p_Holm=.995, and learned−pointwise is +0.000035 [-0.000057,+0.000127], p_Holm=.796. Neither effect gate passes. Shared/grouped/low-rank arms use 16/128/320 filter parameters versus 1,024 learned and pass the frozen −0.000500 noninferiority boundary, but only as conditional numerical compression relative to a learned arm whose effect did not replicate. This is prospectively frozen same-investigator non-Amazon evidence, not independent confirmation, generalization, equivalence to identity, or deployment utility. Public artifacts: protocol/code, aggregate adjudication, and aggregate resource figure/CSV. Private under the ML-1M README: record rows, transformed splits, checkpoints, endpoints, and per-user sidecars.
8. **Current-comparator campaigns (outcome-known same-investigator evidence):** official-code WEARec returned `WEAREC-BELOW-EXISTING-REFERENCE`, 0.059184 [0.058674,0.059693] versus the existing 0.067337 reference. Separately frozen E-E V3 returned `EEV3-REPORTABLE-OUTCOME-KNOWN`: the AlphaFuse-style MiniLM package scored 0.048273 [0.048129,0.048416] versus a zero-initialized upstream-class SASRec-ID control at 0.039024 [0.038106,0.039941], delta +0.009249 [0.008329,0.010169], but remained −0.019065 [−0.019347,−0.018783] below the existing reference. The E-E V3 result is a whole representation-package contrast under shared data/evaluation and a frozen configuration. MiniLM replaces the published AlphaFuse text vectors; architecture, text availability, initialization, trainable capacity, parameter allocation, and tuning history are not equalized. It is not a comparison with upstream-default normal initialization; that sensitivity and an equal-budget factorial remain open. Prelaunch preparation opened the outcome-known combined TRAIN/VALID/TEST export but retained only TRAIN histories and VALID targets in the training input; fitting and selection did not load, hash, or score TEST, and sealed assessment waited for the 16-checkpoint READY record. Neither campaign supplies independent confirmation or SOTA evidence, and E-E V3 does not isolate null-space fusion. Public artifacts: frozen protocols/code and compact adjudications; the graph checks only the private endpoint/sidecar ledger structure and hash-string syntax/uniqueness, while the local adjudicator checked the actual private files.
