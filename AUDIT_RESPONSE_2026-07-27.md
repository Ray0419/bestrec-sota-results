# Response to `PAPER_REVIEW_AUDIT.md` — 2026-07-27

This response addresses the 18-item list timestamped 2026-07-27 22:00. It does
not edit or supersede the independent audit. “Closed” means the manuscript or
artifact now matches the evidence; it does not retroactively improve study
independence, custody, or construct validity.

| Audit item | Current disposition | Response and evidence |
|---:|---|---|
| 1 | **OPEN — author action required** | Author, affiliation, country, contact, and running-header fields remain placeholders. Builds pass only with a logged `DRAFT_WAIVER=1`; no identity was invented. A release build must be rerun without the waiver after real metadata are supplied. |
| 2 | **Mechanical result CLOSED; evidence class OPEN pending author attestation** | `Digital_Music` V1 remains `DM-V1-FEASIBILITY-VOID`, and Software V2 remains permanent `SW-V2-INTEGRITY-FAIL`; neither contributes an endpoint. Software V3 was frozen and pushed before launch at tag `fir-prospective-sw-v3-freeze` / commit `9c8f1a16`, permitted a transductive all-split catalog while suppressing TEST scoring, used exclusive-created hash-linked local seals, and invoked the protocol-designated adjudicator after all 16 sealed endpoints existed. The exact verdict is `SW-V3-PRACTICAL-POS`: learned−identity **+0.005062, ordinary paired 95% CI [+0.004591,+0.005533]**, paired-difference SD 0.000563779, paired t(7)=25.39, p=3.75×10⁻⁸, 8/8 positive; the post-hoc two-sided exact sign sensitivity is p=.0078125, and learned/identity means were 0.120200/0.115138. The graph now gates every registered paired difference, the SD, and the sign sensitivity, and the paper includes the requested paired-seed figure. The CI lower bound exceeds the frozen +0.000500 reporting threshold. Tracked evidence cannot establish whether earlier V2 validation output was observed before the V3 freeze, and local logs cannot prove first human/tool access. Unless the authors supply a signed, dated visibility/custody statement, the paper now classifies V3 as outcome-known/exploratory same-team robustness. It is not independent confirmation or cross-domain replication. |
| 3 | **CLOSED for discrimination from the named compound placebo; temporal isolation remains open** | `PREREG_FIR_POINTWISE_V1.md`, its frozen source hashes, structural test, runner, sealed evaluator, and mechanical adjudicator were committed and pushed before launch. All 24 training runs suppressed TEST scoring and recorded no TEST metrics, but used the pre-existing transductive all-split catalog and executed from a tracked-dirty tree; all 24 selected checkpoints then received one sealed final evaluation. The protocol-designated adjudicator returned `POINTWISE-FIR-DISCRIMINATED`: learned−identity +0.001872 [+0.001737,+0.002007], pointwise−identity −0.000069 [−0.000200,+0.000061], learned−pointwise +0.001941 [+0.001788,+0.002095], with the first and third contrasts rejecting in one frozen three-test Holm family. Local process ordering does not establish first human/tool access. The placebo and FIR each have exactly 1,024 trainable parameters and matched backbone hashes, but the compound DCT/GELU placebo also differs in basis/rank, activation, and channel mixing. The study discriminates learned FIR from that tested non-temporal residual on outcome-known MI; it does not isolate temporal access, establish per-channel necessity, or supply independent confirmation/generalization. The causality suite covers 18/18 paths. |
| 4 | **Current artifact replay CLOSED; frozen V3 training replay defect disclosed** | `bootstrap_public_clone.py` hydrates and raw-hash-verifies every release section. All 48 Software V3 assets were uploaded, and a fresh HTTPS clone directly downloaded and verified the complete **407-asset / 9,489,409,339-byte** public boundary with zero local reuse. A subsequent pristine clone at pushed commit `9cfe5c1f` re-verified all 407 bytesets, installed the frozen 91-package environment, recomputed 196/196 active cells across 20 families with zero mismatch/untraceable cells, verified the 1,009-file manifest, passed every governed adjudicator, rendered the 47-page reader PDF with `scan: CLEAN`, and passed both ACM targets under the draft waiver. This artifact replay did not rerun V3 training. The audit correctly found that the frozen common module expects the CRLF SHA-256 `a230d17c…` for one MI lineage-reference JSON while a normal tagged checkout produces LF SHA-256 `37c78ef…`; direct clean-tag execution fails that raw input assertion until the historical CRLF representation is restored. `FIR_PROSPECTIVE_SW_V3_REPLAY_ERRATUM.md` records both hashes and the descendant preserves the exact CRLF bytes. The reference was not read for runtime configuration, so endpoint arithmetic is unchanged, but frozen-tag portability is not claimed. |
| 5 | **CLOSED** | E-A is labeled the frozen independent-arm Welch/Satterthwaite analysis: ordinary 95% Welch CI, df=13.939; its paired-by-seed result is descriptive only. Hybrid intervals are ordinary paired 95% CIs; Holm adjusts p-values/decisions, not intervals. A new health gate forbids the stale labels. |
| 6 | **OPEN human verification; disclosure closed** | Dirty-tree execution across five commits, absent independent sidecar custody, and the limited local start marker are retained in the main text and erratum. The study remains outcome-known exploratory evidence. Only the maintainer can verify pre-adjudication human/tool visibility. |
| 7 | **Current frequency and clean text+ID comparator coverage CLOSED narrowly** | FreqRec and WEARec are cited in Table 0, Related Work, Method, and the bibliography; BSARec is correctly scoped to Theorem 1 on repeated softmax attention, not the HSTU-style operator. The prospectively frozen official-code WEARec campaign returned `WEAREC-BELOW-EXISTING-REFERENCE`: WEARec NDCG@10 0.059184 [0.058674,0.059693] versus the existing 0.067337 [0.067063,0.067611] reference; descriptive unpaired delta −0.008154 [−0.008689,−0.007618]. The outcome-visible V2 AlphaFuse port remains permanently `NONCOUNTABLE`/`manuscript_allowed=false`. The separately frozen E-E V3 campaign completed 16/16 training bundles, then 16/16 sealed TEST evaluations, before the unchanged committed adjudicator became the first authorized endpoint reader. Exact verdict: `EEV3-REPORTABLE-OUTCOME-KNOWN`. AlphaFuse-style MiniLM NDCG@10 is 0.048273 [0.048129,0.048416] versus repository SASRec-ID 0.039024 [0.038106,0.039941]; descriptive independent-arm Welch delta +0.009249 [0.008329,0.010169]. The package remains −0.019065 [−0.019347,−0.018783] below the existing reference. This closes comparator execution, not the independence gap: it is prospectively frozen only for its fresh optimizer seeds on an outcome-known split by the same investigators. MiniLM replaces the published AlphaFuse text vectors; text availability, initialization, trainable capacity, parameter allocation, and architectures differ. The result is a whole-package contrast, not a published-table reproduction, null-space-fusion isolation, equal-tuning evidence, independent confirmation, or SOTA. |
| 8 | **PARTLY CLOSED by prospective construct/time sensitivity** | The Amazon estimand remains next recorded review event, not preference/purchase/deployment engagement. The prospectively frozen MovieLens study now supplies a rating≥4 primary estimand, an all-rating construct sensitivity, and a global 90% time boundary with a training-observed catalog. Its negative verdict is reported. Verified-purchase, keep-latest, real implicit-event, and query-time-catalog sensitivities remain unrun. |
| 9 | **Numerical graph, claim-map, and Table 0 quantitative provenance CLOSED; mutation depth remains open** | The graph has 199 active cells across 23 required families with zero mismatch/untraceable cells. The MovieLens cell verifies frozen code hashes and recomputes released aggregate seed-vector, paired-interval, Holm/NI, sensitivity, and resource arithmetic. The WEARec cell verifies official-code provenance, six reference artifacts, eight private endpoint hashes, and released NDCG/Welch arithmetic. The E-E V3 cell recomputes all released NDCG/HR/MRR summaries and both Welch contrasts, verifies the same six reference artifacts, validates fixed-dataset sensitivity/resource metadata and all 16 endpoint/sidecar hashes, and records `private_endpoint_replay=0` and `private_bootstrap_replay=0`. No cell claims replay of private endpoint extraction. `build_claim_artifact_map.py` asserts that every active cell is mapped exactly once. `build_table0_claim_ledger.py` generates Table 0’s quantitative fields from active graph cells, and the strict wrapper fails if its marked region drifts. Literature attribution remains citation-checked authored prose. Full mutation/fault-injection depth remains future assurance work. |
| 10 | **Primary paper type CLOSED; validation depth OPEN** | Title, abstract, Introduction, Table 0, Related Work, Discussion, and Conclusion consistently define the paper as an **incremental modular FIR contribution**. The audit/rebuild apparatus is a supporting contribution, not the lead. Current-baseline execution, cross-repository validation, fault injection, and reviewer-usability evidence would strengthen but do not redefine the paper type. |
| 11 | **CLOSED** | “Transfers,” “cross-category confirmation/transfer,” “FIR-specific interpretation,” and “supports temporal mixing” were removed from the canonical and rendered manuscripts. Shared/nonlinear controls are described as statistically unseparated, never equivalent. The health gate now fails on the stale attribution phrases. |
| 12 | **CLOSED** | The manuscript names the separately frozen five-test family A and four-test family B, reports all nine Holm-adjusted p-values, labels every CI ordinary paired, and states that neither one global nine-test family nor simultaneous-CI coverage is implied. |
| 13 | **PARTLY CLOSED; population inference remains open** | The prospective MovieLens phase adds one non-Amazon global-time split, eight matched seed blocks, an all-rating sensitivity, and fixed-dataset user/item cluster bootstrap sensitivities. All six cluster intervals for parsimonious-minus-learned contrasts include zero. Inference still does not sample datasets or repeated cutoffs; the bootstrap intervals are sensitivities, not new independent samples, and no retained null is called equivalence. |
| 14 | **CLOSED experimentally; primary outcome negative** | A pre-acquisition frozen six-arm MovieLens 1M study tested identity, shared (16 parameters), grouped (128), rank≤8 tangent-factorized (320), learned per-channel (1,024), and equal-parameter pointwise (1,024) over eight exact matched-initialization blocks. It reports the pre-declared 0.000500 noninferiority family and parameter/FLOP/latency/inference-memory/training-memory/time curves. Shared, grouped, and low-rank met the margin versus learned FIR, but learned FIR failed replication versus identity and pointwise; therefore the parsimony result is explicitly conditional and does not establish useful compression or FIR value. Exact verdict: `ML1M-NO-FIR-REPLICATION`. |
| 15 | **OPEN experimental/engineering work** | Cache/item-map binding, metadata-missingness controls, repeated thinning draws, tie-safe sensitivity, and item-macro/hierarchical inference remain incomplete. Claims were narrowed rather than treating these omissions as repaired. |
| 16 | **OPEN release/deposit item** | The public evidence assets are complete, remotely size/digest checked, and clean-clone replayed, but the mutable `v0.9-audit-evidence` and stale deposit tag are not represented as a final immutable archival deposit. A new versioned release/tag and DOI deposit must be cut only after final author/legal metadata and a final clean-clone replay. |
| 17 | **Partly CLOSED** | Related Work was condensed; Table 0 is now a less cramped three-column generated claim ledger; the appendix and supplement overflows were repaired; and targeted visual inspection found no clipping. The Software section now has a two-panel matched-seed/difference figure with zero and +0.000500 reference lines, exact plotted-data CSV, detailed ACM `\Description`, and explicit exploratory/not-independent labeling. Figure S1 has larger labels, descriptive alt text, and embedded Type-0/TrueType fonts rather than Type-3 glyph fonts. Reader bookmarks/tagging, venue PDF tagging, accessibility review of the remaining document, and further body-length reduction remain editorial/accessibility work. |
| 18 | **OPEN — author/legal action required** | Outcome visibility, exact dirty patches, author order/identity, portal mode and length, ethics/privacy review, funding/conflicts, licenses, and derivative-redistribution permission require maintainer verification. |

## Net claim after the audit

This is a modular contribution paper, not a brand-new algorithm or architecture
paper. The defensible result is narrower: under fixed outcome-visible settings,
tested trainable left-causal residual arms improved a frozen-identity control.
Learned per-channel FIR taps are one successful realization, but the present
controls do not establish learned-tap superiority. The matched pointwise-placebo
study discriminates learned FIR from one equal-parameter compound non-temporal
arm on outcome-known MI, but does not isolate temporal access. A separately frozen
Software attempt mechanically cleared its thresholded rule. Earlier V2 validation-output
non-visibility is not independently established, so it is classified outcome-known
same-team robustness; its same investigator, code lineage, Amazon family, and local
same-user custody also preclude independent confirmation.
The artifact apparatus makes that boundary, the nulls, and the deviations
reproducible; it does not turn them into independent confirmation.
The frozen E-E V3 current-comparator study adds a positive AlphaFuse-style
whole-package-versus-repository-ID contrast (+0.009249 [0.008329,0.010169])
while also recording that package's negative contrast to the stronger existing
reference (−0.019065 [−0.019347,−0.018783]). This strengthens comparator
coverage for a modular paper, but does not isolate null-space fusion or equalize
architecture, capacity, initialization, text availability, or tuning.
The prospectively frozen MovieLens 1M study further narrows the boundary: learned FIR
did not replicate versus identity or pointwise on the non-Amazon primary split. Smaller
FIR arms met the registered noninferiority margin only relative to that non-replicating
learned arm, so the paper treats parsimony as conditional numerical compression rather
than a positive efficiency claim.

## Reproduction evidence

The current boundary was replayed from a fresh HTTPS clone. The public downloader
installed and raw-hash-verified all 407 release assets (9,489,409,339 bytes), including
the 48 Software V3 assets, with zero local reuse. The final pristine clone at pushed
commit `9cfe5c1f` then re-verified those bytes, installed the frozen runtime and pinned
submodules, obtained bitwise core-block parity, recomputed 196/196 active cells across
20 claim families, verified the 1,009-file manifest, passed every governed adjudicator,
retained Office V1 as VOID, rendered the reader PDF with `scan: CLEAN`, passed both ACM
targets under the explicit author-placeholder draft waiver, and ended
`SUBMISSION REBUILD: PASS`. A final archival tag/DOI deposit should repeat the full
fresh-clone check after author/legal metadata are finalized.

## 2026-07-28 completion addendum

The continuation audit made four further changes without editing the independent
audit log:

1. It found a real machine-readable taxonomy defect: TFV2 cells were still
   labeled `confirmatory` in the generated evidence graph although the paper
   correctly calls that campaign outcome-visible/non-confirmatory. The graph now
   labels TFV2 exploratory, and `build_claim_artifact_map.py` asserts the expected
   evidence class so the error cannot silently recur.
2. `CLAIM_ARTIFACT_MAP.md` now maps ten manuscript claim groups to exact cell IDs,
   source artifacts, evidence classes, and both reviewer reconstruction paths.
   Its deterministic verifier is part of the strict rebuild.
3. The final literature/venue sweep added SISA-Rec (arXiv:2607.11168) and ASER
   (arXiv:2603.02709) as concurrent modular-content work, recorded their Amazon
   Reviews 2014 protocol mismatch, closed the SILLM4Rec inspection item with an
   explicit access limitation, and verified the current acmart v2.19 build.
4. `PHASE_COMPLETION_AUDIT_2026-07-28.md` reconciles all ten repair phases and
   every Claude handoff item. The deposit builder now derives its Git-backed
   evidence inventory from the release manifest and active cell graph. The
   deterministic 899-entry `v1.2.0` candidate contains the active Git-backed
   graph sources plus the current pointwise protocol/adjudication chain; normal
   publish mode still refuses to proceed with creator placeholders. No tag,
   archival release, or DOI is claimed to exist.

The residual audit blockers are therefore substantive or human-controlled, not
unfinished local editing: independent temporal/non-Amazon confirmation, repeated
cutoffs, and current equal-protocol system baselines require new preregistered
experiments; author, conflict, legal, and DOI fields require maintainer authority.

## 2026-07-28 pointwise-placebo and parity addendum

The later 00:28 audit correctly observed that the pointwise study was then only an
uncommitted protocol. That status has changed through a clean temporal sequence:
pre-outcome commit and push (`93e73a5c`), 24 TEST-sequestered training runs, 24 sealed
one-shot final evaluations, then the committed adjudicator's first read. The result is
now integrated symmetrically into Markdown and TeX, including the null pointwise−identity
contrast and all Holm-adjusted p-values. The TORS-only phrases “transfers to a second
category” and “does not learn as reliably” were removed, closing the prose-parity defect
identified by the audit. The evidence remains explicitly outcome-known.

## 2026-07-28 final audit-response addendum

The latest audit's V3 evidence-class and replay findings are accepted. Markdown,
TeX, the artifact graph, claim map, README, citation metadata, and deposit template
now use the same narrowed boundary: V3 is an outcome-known/exploratory same-team
robustness result unless the authors later supply a signed visibility/custody statement;
the local seals are exclusive-created and hash-linked rather than immutable; and the
adjudicator is protocol-designated rather than provably the first human/tool reader.
The exact `SW-V3-PRACTICAL-POS` arithmetic is retained without upgrading its evidence
class. The CRLF/LF frozen-reference defect is separately recorded in
`FIR_PROSPECTIVE_SW_V3_REPLAY_ERRATUM.md`.

The audit's stale-landing-metadata finding is also closed for the mutable current
boundary: README reports the public asset boundary and the current candidate count;
CFF/Zenodo metadata report 199 cells across 23 families and no longer claim
that the compound placebo isolates temporal access; the public release manifest was
uploaded last. The final immutable tag, verified creators/legal fields, and DOI remain
open human-controlled work.

## 2026-07-28 statistical-visibility and generated-ledger addendum

The latest statistical and presentation requests are now implemented without changing
the frozen Software decision rule. The manuscript reports the paired-difference SD, all
eight registered differences, and a clearly post-hoc two-sided exact sign sensitivity.
A new two-panel figure shows every matched identity/learned endpoint and every paired
difference against zero and the +0.000500 reporting threshold. Its data CSV is checked
row-by-row by the Software graph rule; all quantitative values remain exploratory
same-team robustness evidence rather than independent confirmation.

Table 0 is now a three-column generated claim ledger. Ten quantitative FIR fields are
formatted from active `OK` graph cells, and both the strict rebuild and TeX emitter fail
if its marked region drifts. The archival candidate gate now derives the live cell,
family, release-asset, and byte counts and checks README/CFF/Zenodo against them; it also
rejects the withdrawn temporal-isolation wording and invokes the Table 0 verifier. The
current candidate has 899 entries. Literature attribution remains authored,
citation-checked prose rather than a machine-derived novelty claim.

## 2026-07-28 non-Amazon parsimony phase (design-stage response)

Audit items 8, 13, and 14 have advanced from an unspecified future experiment to
a concrete prospective protocol, but they are **not yet closed**.  The draft
`PREREG_FIR_EFFICIENCY_ML1M_V1.md` freezes a MovieLens 1M rating≥4 primary
estimand, a global 90% time boundary, a fixed-point training-observed catalog,
an all-rating construct sensitivity, and six matched arms: identity, shared,
grouped, rank≤8 tangent-factorized, per-channel, and equal-parameter pointwise.
The three parsimonious arms use 16, 128, and 320 trainable filter parameters
versus 1,024 per-channel parameters.  A 0.000500 NDCG@10 noninferiority margin,
family-wise inference, user- and item-cluster bootstrap sensitivities, and
parameter/FLOP/latency/memory/training-time reporting are specified before data
access.

A pre-freeze static audit found and repaired a recurrence of the earlier TEST
visibility weakness: with sequestration enabled, the trainer now constructs its
maps from TRAIN+VALID and neither opens nor hashes TEST bytes.  The deterministic
split closes user/item eligibility to a fixed point so every sealed target is
already training-observed; the final evaluator's strict checkpoint load verifies
that invariant.  Structural tests pass for exact identity at initialization,
nonzero gradients, parameter counts, no future-token leakage, frozen-evaluator
reconstruction, and resource instrumentation.

No MovieLens archive, rating record, transformed split, per-user endpoint, or
experimental outcome has been acquired or inspected.  The official ML-1M README
prohibits redistribution without separate permission, so the protocol keeps all
record-level artifacts private and permits only aggregate provenance, hashes,
statistics, code, and adjudication in the public graph.  The phase may be called
prospective same-investigator non-Amazon robustness/efficiency evidence after a
valid outcome; it cannot be called independent confirmation or population-wide
generalization.

## 2026-07-28 non-Amazon parsimony phase (outcome integration)

The design-stage phase completed without the campaign process opening any endpoint
before all 96 TEST-sequestered training runs and 96 sealed evaluations existed. The
protocol-designated adjudicator was then invoked in the recorded process sequence;
local evidence does not establish first human/tool access. Its exact verdict is
`ML1M-NO-FIR-REPLICATION`.

On the rating≥4 primary global-time split, mean NDCG@10 was 0.052151 learned,
0.052151 identity, and 0.052116 pointwise. Learned−identity was +0.000000 with
ordinary paired 95% CI [−0.000074,+0.000075] and Holm-adjusted p=.995;
learned−pointwise was +0.000035 [−0.000057,+0.000127], p_Holm=.796. Neither
replication gate passed. The all-rating sensitivity agreed: +0.000012
[−0.000107,+0.000131] and +0.000043 [−0.000082,+0.000168].

Shared, grouped, and rank≤8 low-rank FIR used 16, 128, and 320 trainable filter
parameters versus 1,024 for learned per-channel FIR. Their candidate−learned
differences were +0.000060, −0.000027, and +0.000060, with simultaneous lower
bounds −0.000068, −0.000128, and −0.000033. All passed the frozen −0.000500
noninferiority boundary after Holm adjustment. This result is reported only as
conditional numerical compression: the learned-FIR effect prerequisite failed,
so NI-PASS does not imply FIR utility, superiority, or equivalence to identity.
Parameter/FLOP/latency/memory/time measurements are plotted and labeled as
descriptive readings from one GPU.

The public evidence graph binds the aggregate adjudication, recomputes all released
seed-vector statistics and Holm decisions, verifies the frozen text-file hashes, and
cross-checks every resource-figure row. The ML-1M README prevents redistribution of
record-level data; checkpoints, endpoint files, and per-user sidecars therefore remain
private. The public graph expressly does not claim independent replay of private
endpoint extraction. Audit items 8 and 13 are only partly closed; item 14 is closed
experimentally with a negative primary result.

## 2026-07-28 current-baseline and presentation response

Audit item 4 requested at least one feasible current equal-evaluation baseline.
`PREREG_WEAREC_BASELINE_V1.md` froze the official AAAI 2026 WEARec code at
commit `2087335339b1ead87da6e066ce14e2d33880a95e`, two validation-only presets,
and eight assessment seeds under the paper's split, full catalog, complete-history
mask, cutoff, and strict-greater tie rule. The campaign completed all 2 tuning runs,
8 TEST-sequestered assessment trainings, and 8 sealed one-shot evaluations without
recorded errors. Only after the status reached complete was the committed adjudicator
run as the protocol-designated first authorized endpoint reader.

The exact verdict is **`WEAREC-BELOW-EXISTING-REFERENCE`**. WEARec mean NDCG@10
is **0.059184, 95% CI [0.058674, 0.059693]**; the existing six-seed full-model
reference is **0.067337 [0.067063, 0.067611]**. The descriptive outcome-known
unpaired Welch contrast is **−0.008154 [−0.008689, −0.007618], p=1.16×10⁻¹¹**.
The graph recomputes both released NDCG vectors, both t intervals, the Welch arithmetic,
the verdict, resource metadata, reference hashes, and the private endpoint-hash ledger.
It does not replay private endpoint extraction or HR/MRR raw-vector arithmetic.

This WEARec result closes the current frequency-baseline half of audit item 7 as a narrow
official-model/equal-evaluation feasibility run. The clean AlphaFuse-style text+ID half
has now also completed under `PREREG_EE_V3.md`: 16/16 fresh-seed training bundles were
ready before 16/16 sealed TEST evaluations, and the unchanged committed adjudicator was
the first authorized endpoint reader. Its exact verdict is
**`EEV3-REPORTABLE-OUTCOME-KNOWN`**. AlphaFuse-style MiniLM NDCG@10 is
**0.048273 [0.048129,0.048416]** versus repository SASRec-ID
**0.039024 [0.038106,0.039941]**; the descriptive independent-arm Welch difference is
**+0.009249 [0.008329,+0.010169], p=3.48×10⁻⁸**. Against the existing six-seed
reference, the package is **−0.019065 [−0.019347,−0.018783]**. User and target-item-
cluster bootstrap intervals remain fixed-split sensitivities, not optimizer/population
inference. V3 is prospectively frozen only with respect to its fresh optimizer seeds:
the split and earlier paper/reference outcomes were already known to the same
investigators. MiniLM replaces the published AlphaFuse text vectors, and the arms differ
in text availability, initialization, trainable capacity, parameter allocation, and
architecture. The result is countable whole-package current-comparator evidence, not a
published-table reproduction, paired experiment, null-space-fusion isolation, equal-
tuning evidence, independent confirmation, or SOTA.

The audit's Table 0 readability and abstract-length concerns were also rechecked.
Table 0 now uses generator-controlled ragged-right columns, additional padding, and
increased row leading; both ACM targets compile, the hygiene scan passes, and a
rendered-page inspection found no clipping or overlap across the repeated-header
page break. The canonical Markdown abstract is 220 words under the repository's
Unicode-aware count, down from the audit's earlier approximately 275-word snapshot.
