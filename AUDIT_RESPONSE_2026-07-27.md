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
| 7 | **Current frequency and clean text+ID comparator coverage CLOSED narrowly** | FreqRec and WEARec are cited in Table 0, Related Work, Method, and the bibliography; BSARec is correctly scoped to Theorem 1 on repeated softmax attention, not the HSTU-style operator. The prospectively frozen official-code WEARec campaign returned `WEAREC-BELOW-EXISTING-REFERENCE`: WEARec NDCG@10 0.059184 [0.058674,0.059693] versus the existing 0.067337 [0.067063,0.067611] reference; descriptive unpaired delta −0.008154 [−0.008689,−0.007618]. The outcome-visible V2 AlphaFuse port remains permanently `NONCOUNTABLE`/`manuscript_allowed=false`. The separately frozen E-E V3 campaign completed 16/16 training bundles, then 16/16 sealed TEST evaluations, before the unchanged committed adjudicator read the endpoints under the protocol. Exact verdict: `EEV3-REPORTABLE-OUTCOME-KNOWN`. AlphaFuse-style MiniLM NDCG@10 is 0.048273 [0.048129,0.048416] versus a zero-initialized upstream-class SASRec-ID control at 0.039024 [0.038106,0.039941]; descriptive independent-arm Welch delta +0.009249 [0.008329,0.010169]. The package remains −0.019065 [−0.019347,−0.018783] below the existing reference. Prelaunch preparation opened the outcome-known combined TRAIN/VALID/TEST export but retained only TRAIN histories and VALID targets for training; fitting/selection did not load, hash, or score TEST and sealed assessment waited for READY. This closes comparator execution, not the independence gap: it is prospectively frozen only for its fresh optimizer seeds on an outcome-known split by the same investigators. MiniLM replaces the published AlphaFuse text vectors; text availability, initialization, trainable capacity, parameter allocation, and architectures differ. E-E V4 separately completed eight parser-default `Normal(0,1)` SASRec-ID runs and eight sealed evaluations; verdict `EEV4-ALPHAFUSE-ABOVE-NORMAL-SASREC`. Normal-init SASRec-ID scored 0.043065 [0.042645,0.043486], leaving the package above it by +0.005207 [+0.004779,+0.005635]; normal initialization improved SASRec-ID over the V3 zero-init arm by +0.004042 [+0.003089,+0.004995]. Official recipes may override initialization by dataset, so the parser setting is not a universal upstream default. V4 is outcome-known, same-investigator, and cross-campaign; phase/date and initialization are confounded, and capacity/architecture remain unequal. The combined result is a whole-package contrast, not a published-table reproduction, null-space-fusion isolation, equal-tuning evidence, independent confirmation, or SOTA. |
| 8 | **PARTLY CLOSED by prospective construct/time sensitivity** | The Amazon estimand remains next recorded review event, not preference/purchase/deployment engagement. The prospectively frozen MovieLens study now supplies a rating≥4 primary estimand, an all-rating construct sensitivity, and a global 90% time boundary with a training-observed catalog. Its negative verdict is reported. Verified-purchase, keep-latest, real implicit-event, and query-time-catalog sensitivities remain unrun. |
| 9 | **Numerical graph, claim-map, and Table 0 quantitative provenance CLOSED; mutation depth remains open** | The graph has 201 active cells across 25 required families with zero mismatch/untraceable cells. The added evidence-map cell binds all eight plotted rows to six released adjudications without pooling them. The MovieLens cell verifies frozen code hashes and recomputes released aggregate seed-vector, paired-interval, Holm/NI, sensitivity, and resource arithmetic. The WEARec cell verifies official-code provenance, six reference artifacts, and released NDCG/Welch arithmetic while checking the recorded private-endpoint hash ledger. The E-E V3 cell recomputes all released NDCG/HR/MRR summaries and both Welch contrasts, verifies the same six reference artifacts, validates fixed-dataset sensitivity/resource metadata, and checks the 16-row private endpoint/sidecar ledger's schema, 64-hex syntax, and uniqueness. It records `private_endpoint_replay=0` and `private_bootstrap_replay=0`; it does not read or hash the private files. The E-E V4 cell verifies the V3 adjudication hash, recomputes the eight-seed normal-init summary and three cross-campaign Welch contrasts, validates resource medians, and checks the eight-row private ledger without reading endpoints. The local adjudicators checked the actual private files. `build_claim_artifact_map.py` asserts that every active cell is mapped exactly once. `build_table0_claim_ledger.py` generates Table 0’s quantitative fields from active graph cells, and the strict wrapper fails if its marked region drifts. Literature attribution remains citation-checked authored prose. Full mutation/fault-injection depth remains future assurance work. |
| 10 | **Primary paper type CLOSED; validation depth OPEN** | Title, abstract, Introduction, Table 0, Related Work, Discussion, and Conclusion consistently define the paper as an **incremental modular FIR contribution**. The audit/rebuild apparatus is a supporting contribution, not the lead. Current-baseline execution, cross-repository validation, fault injection, and reviewer-usability evidence would strengthen but do not redefine the paper type. |
| 11 | **CLOSED** | “Transfers,” “cross-category confirmation/transfer,” “FIR-specific interpretation,” and “supports temporal mixing” were removed from the canonical and rendered manuscripts. Shared/nonlinear controls are described as statistically unseparated, never equivalent. The health gate now fails on the stale attribution phrases. |
| 12 | **CLOSED** | The manuscript names the separately frozen five-test family A and four-test family B, reports all nine Holm-adjusted p-values, labels every CI ordinary paired, and states that neither one global nine-test family nor simultaneous-CI coverage is implied. |
| 13 | **PARTLY CLOSED; population inference remains open** | The prospective MovieLens phase adds one non-Amazon global-time split, eight matched seed blocks, an all-rating sensitivity, and fixed-dataset user/item cluster bootstrap sensitivities. All six cluster intervals for parsimonious-minus-learned contrasts include zero. Inference still does not sample datasets or repeated cutoffs; the bootstrap intervals are sensitivities, not new independent samples, and no retained null is called equivalence. |
| 14 | **CLOSED experimentally; primary outcome negative** | A pre-acquisition frozen six-arm MovieLens 1M study tested identity, shared (16 parameters), grouped (128), rank≤8 tangent-factorized (320), learned per-channel (1,024), and equal-parameter pointwise (1,024) over eight exact matched-initialization blocks. It reports the pre-declared 0.000500 noninferiority family and parameter/FLOP/latency/inference-memory/training-memory/time curves. Shared, grouped, and low-rank met the margin versus learned FIR, but learned FIR failed replication versus identity and pointwise; therefore the parsimony result is explicitly conditional and does not establish useful compression or FIR value. Exact verdict: `ML1M-NO-FIR-REPLICATION`. |
| 15 | **OPEN experimental/engineering work** | Cache/item-map binding, metadata-missingness controls, repeated thinning draws, tie-safe sensitivity, and item-macro/hierarchical inference remain incomplete. Claims were narrowed rather than treating these omissions as repaired. |
| 16 | **OPEN release/deposit item** | The public evidence assets are complete, remotely size/digest checked, and clean-clone replayed, but the mutable `v0.9-audit-evidence` and stale deposit tag are not represented as a final immutable archival deposit. A new versioned release/tag and DOI deposit must be cut only after final author/legal metadata and a final clean-clone replay. |
| 17 | **Partly CLOSED** | Related Work was condensed; Table 0 is now a less cramped three-column generated claim ledger; the appendix and supplement overflows were repaired; and targeted visual inspection found no clipping. The main Results section now has a compact evidence-map forest plot that places positive Amazon contrasts beside the shared-filter and MovieLens boundary conditions. The detailed Software matched-seed/difference panel is retained as Fig. S1 with zero and +0.000500 reference lines, exact plotted-data CSV, detailed ACM `\Description`, and explicit exploratory/not-independent labeling; the fitted-operator diagnostic is Fig. S2. Reader bookmarks/tagging, venue PDF tagging, accessibility review of the remaining document, and further body-length reduction remain editorial/accessibility work. |
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
CFF/Zenodo metadata report 200 cells across 24 families and no longer claim
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

## 2026-07-30 manuscript-parity, governance, and novelty response

The later July 30 audit identified several manuscript defects that were independent of
the governed result arithmetic. They are accepted and repaired without editing the
audit itself:

1. **Amazon protocol attribution:** Markdown and TeX no longer say that our AR2023
   pipeline “matches” TIGER/LIGER. They now distinguish our iterative user-and-item
   5-core pipeline from TIGER's stated user filtering, LIGER's stated user-and-item
   filtering, both papers' Amazon Reviews 2014 source, and Hou et al.'s AR2023 0-core
   repository path. LIGER's first author and full author list are corrected to Liu
   Yang et al.
2. **MovieLens chronology and governance:** the paper now states that acquisition read
   the official ratings file, constructed and hash-bound TEST, and used TEST targets
   for the frozen target-in-training-catalog cohort. The narrower valid claim is that
   fitting and validation selection consumed TRAIN+VALID only, emitted no TEST scores,
   and preceded sealed one-shot TEST evaluation. Ethics now covers both Amazon Reviews
   2023 and MovieLens 1M, states that only `ratings.dat` was parsed, and records the
   MovieLens non-redistribution/non-commercial boundary plus the remaining institutional
   legal, retention, deletion, and access-control review.
3. **Modern novelty boundary:** Related Work, Table 0, TeX, and the bibliography now
   include mechanism-level positioning against TimeWeaver, TV-Rec, HyenaRec, ConvRec,
   and Mamba4Rec, in addition to FreqRec and WEARec. These citations explicitly rule out
   broad filtering, convolution, temporal-specificity, linear-time, or efficiency
   novelty. No protocol-mismatched published number is presented as a matched baseline.
4. **Statistical wording:** Table 1 and the historical moving-average paragraph now
   define `±` as sample standard deviation, describe arithmetic mean contrasts as
   descriptive, and reject visual “band non-overlap” as an inferential rule. The
   retained pointwise-minus-identity result remains nonequivalence evidence only.
5. **Compression wording:** the MovieLens noninferiority result is now called
   conditional **coefficient-count** compression, not a computational optimization.
   The paper states that no bypass implementation was tested and that measured
   end-to-end latency and memory did not materially improve.
6. **Rendered parity:** figure numbering is synchronized between Markdown and TeX;
   the acmsmall dataset table now provides break opportunities for long category names
   and no longer has column collisions. The fail-closed graph now has 201 active
   cells across 25 required families with zero mismatch and zero untraceable claims.

These repairs close contradictions and presentation defects; they do not close the
substantive external-validity gaps. The current WEARec comparison still differs in
architecture, loss, schedule, and tuning budget; the AlphaFuse-style result remains a
whole-package port using substituted MiniLM features; the prospective non-Amazon FIR
test is negative; and none of the positive FIR evidence is independent confirmation.
Author identity/affiliation/contact fields, conflicts/funding, venue mode and length,
final legal review, immutable archival release, and DOI remain author-controlled open
items. A literal submission build is therefore still blocked until real byline metadata
are supplied and the draft waiver is removed.

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
ready before 16/16 sealed TEST evaluations, after which the unchanged committed
adjudicator read the endpoints under the frozen protocol. Its exact verdict is
**`EEV3-REPORTABLE-OUTCOME-KNOWN`**. AlphaFuse-style MiniLM NDCG@10 is
**0.048273 [0.048129,0.048416]** versus a zero-initialized upstream-class SASRec-ID control
**0.039024 [0.038106,0.039941]**; the descriptive independent-arm Welch difference is
**+0.009249 [0.008329,+0.010169], p=3.48×10⁻⁸**. Against the existing six-seed
reference, the package is **−0.019065 [−0.019347,−0.018783]**. User and target-item-
cluster bootstrap intervals remain fixed-split sensitivities, not optimizer/population
inference. V3 is prospectively frozen only with respect to its fresh optimizer seeds:
the split and earlier paper/reference outcomes were already known to the same
investigators. Prelaunch preparation opened the outcome-known combined export but
retained only TRAIN/VALID fields for training; fitting and selection did not load, hash,
or score TEST. MiniLM replaces the published AlphaFuse text vectors, and the arms differ
in text availability, initialization, trainable capacity, parameter allocation, and
  architecture. The separately frozen E-E V4 sensitivity tests parser-default normal
  initialization; its result is pending and is not backfilled into this V3 result. The result is
countable whole-package current-comparator evidence, not a
published-table reproduction, paired experiment, null-space-fusion isolation, equal-
tuning evidence, independent confirmation, or SOTA.

The audit's Table 0 readability and abstract-length concerns were also rechecked.
Table 0 now uses generator-controlled ragged-right columns, additional padding, and
increased row leading; both ACM targets compile, the hygiene scan passes, and a
rendered-page inspection found no clipping or overlap across the repeated-header
page break. The canonical Markdown abstract is 220 words under the repository's
Unicode-aware count, down from the audit's earlier approximately 275-word snapshot.

## 2026-07-30 claim-accuracy and canonical-source addendum

The later independent audit correctly identified six residual factual/governance
defects. They are now corrected without changing any experimental value or verdict:

1. E-E V3 chronology now states that prelaunch preparation opened the pre-existing
   combined TRAIN/VALID/TEST export and retained only user IDs, TRAIN histories, and
   VALID targets. Model fitting and validation selection did not load, hash, or score
   TEST; sealed assessment waited for the 16-checkpoint READY record. The broader
   claim that no TEST-bearing export had been read is withdrawn.
2. The public graph is now described exactly: it recomputes released aggregates and
   checks private-file ledger shape, 64-hex syntax, and uniqueness. It does not read or
   hash private endpoint/sidecar bytes. The local adjudicator performed the byte-level
   digest checks.
3. The E-E V3 control is labeled a **zero-initialized upstream-class SASRec-ID
   control**, not parser-default-normal SASRec. A normal-initialization sensitivity and an
   equal-budget factorial remain open; the whole-package boundary is retained.
4. `PAPER_SUBMISSION.md` is the sole canonical authored source. `PAPER_DRAFT.md` now
   carries a do-not-submit historical/noncanonical banner, and a health gate enforces
   that status plus the corrected claim phrases in source and rendered PDFs.
5. Ethics/data-governance prose separates public pseudonymized Amazon product-review
   data and released Amazon sidecars from privately held MovieLens ratings data and
   unreleased MovieLens sidecars.
6. AlphaFuse proceedings metadata now includes the verified 1614--1623 page range and
   DOI `10.1145/3726302.3729894`. TIGER preprocessing remains described as a paper-level
   statement rather than proof of the unreleased preprocessing geometry.

## 2026-07-30 parser-default-normal-init sensitivity addendum

Audit item 4 correctly identifies the zero-initialized E-E V3 SASRec control as a
comparator-fairness limitation. `PREREG_EE_V4.md` and its fail-closed source now
predeclare eight fresh runs of the official AlphaFuse-repository `SASRec` class with
the upstream CLI default `ID_embs_init_type="normal"` (`Normal(0,1)`). Training loss,
schedule, VALID selection, data, and full-catalog evaluator match V3; the V4 driver
uses four frozen two-process waves, creates READY only after all eight TEST-unread
terminal bundles exist, seals each one-shot TEST evaluation, and invokes the committed
adjudicator as the first authorized endpoint reader. The primary frozen contrast is
V3 AlphaFuse-style MiniLM minus V4 normal-init SASRec-ID using independent-arm Welch.

This phase is explicitly outcome-known, same-investigator, and cross-campaign. Phase/
date and initialization are confounded, architecture/capacity remain unequal, and the
V3 aggregate was visible before V4 design. Accordingly it can test whether the reported
whole-package contrast survives the CLI-default normal initialization choice, but it
cannot isolate initialization, supply an equal-capacity factorial, establish SOTA, or
provide independent confirmation. This is not described as a universal AlphaFuse recipe:
the official README commands vary by dataset, using both zero and normal ID initialization.
All eight trainings and eight sealed evaluations completed with zero ledger errors before
the committed adjudicator's first endpoint read. Exact verdict:
`EEV4-ALPHAFUSE-ABOVE-NORMAL-SASREC`. Parser-default-normal SASRec-ID NDCG@10 is
0.043065 [0.042645,0.043486]; the V3 AlphaFuse-style package remains above it by
+0.005207 [+0.004779,+0.005635], while normal-init SASRec-ID exceeds the earlier
zero-init arm by +0.004042 [+0.003089,+0.004995]. The normal-init arm remains below
the existing reference by −0.024272 [−0.024728,−0.023816]. This is countable only as
prospectively frozen, outcome-known, same-investigator cross-campaign sensitivity.
Phase/date and initialization are confounded; architecture, capacity, and allocation
remain unequal. It is not independent confirmation, initialization isolation, an
equal-budget factorial, or SOTA.

## 2026-07-30 23:27 audit-response staging addendum

The latest independent audit found two further factual/assurance defects that do not
depend on the pending V4 outcome. They are repaired in a separate post-freeze worktree so
the commit-bound campaign remains untouched:

1. The HSTU-BLaIR geometry is no longer called identical to ours. Markdown and TeX now
   state the exact relationship: the same 25,612 items and 94,762 users, but 814,585
   reported interactions, one fewer than our 814,586. The health gate bans the false
   `identical dataset stats to ours` phrase.
2. The embedded graph generator and tracked `hstu_results_manifest.json` had diverged in
   exactly three E-E V3 semantic fields: TEST chronology, the zero-initialized control
   label, and the public/private hash-verification boundary. The manifest is regenerated,
   and submission mode now independently regenerates it to a temporary file and requires
   byte identity before verifying any recorded cell. A stale self-consistent manifest can
   therefore no longer pass the strict gate.
3. README now states that only tables are mechanically generated from canonical Markdown/
    the artifact graph; TeX prose is a separately maintained mirror under semantic gates.
    The health gate now requires that separately-maintained-TeX disclosure in README,
    `CANONICAL_SUBMISSION.md`, and `VENUE_PLAN.md`, and rejects a renewed claim that the
    TORS/venue/ACM PDF or TeX prose is wholly generated from canonical Markdown.
    The Introduction also replaces the ambiguous `package-versus-repository-ID` label with
   the exact zero-initialized upstream-class SASRec-ID control. The V4 audit response now
   distinguishes the upstream CLI parser default from the dataset-varying official README
   recipes, which use both zero and normal ID initialization.
4. The PowerShell TeX wrapper now matches the shell wrapper's fail-closed release-manifest
   epoch assertion: it parses `RELEASE_MANIFEST.json`, requires a nonempty `git_commit`,
   and permits `ALLOW_HEAD_EPOCH=1` only as an explicit development override. The
   executable closure ledger now passes this formerly failing assertion.
5. The archival builder no longer treats an unresolved intended tag as if it matched
   `HEAD`. Normal/rebuild mode now checks `git rev-parse --verify`'s return code and emits
   an explicit missing-tag failure; candidate mode remains the only pre-tag preparation
   path. This repairs the misleading boundary diagnostic without creating or publishing
   any tag.
6. The E-E V3 Results text now discloses that upstream offline preprocessing was
   unavailable and both official classes consumed rows from the paper's frozen
   per-prefix adapter. It therefore describes upstream-class/training-code transfer, not
   an upstream-pipeline reproduction. The TeX health gate requires this boundary in both
   canonical Markdown and its separately maintained TeX mirror.
7. A new fail-closed clean-clone replay runner records a self-contained JSON transcript
   binding the subject commit/tree, exact commands and complete normalized captured output, output
   hashes, toolchain, graph cell/family summary, release-manifest digest, and all four PDF
   digests. Its verifier rejects transcript tampering, failed/missing stages, subject-tree
   drift, artifact drift, and post-attestation changes outside the record itself. An
   explicit metadata-waiver mode is classified `release_ready=false`; strict mode accepts
   no waiver. Absolute repository/home/source paths and remote credentials are redacted
   deterministically before hashing so a public record does not leak workstation identity.
   The actual outcome-complete attestation remains pending the final V4 merge and clean-clone replay.
8. Archive landing metadata now states the current 200-cell/24-family graph and the
   mechanically computed candidate inventory; it explicitly marks the existing
   908-entry ZIP stale. The deposit gate now parses the semantic graph-count sentences in
   README, CFF, and Zenodo metadata and requires exact equality, rather than accepting the
   live integers anywhere in each file. It also requires README's exact live bundle count.
   The ZIP-internal `README_DEPOSIT.txt` no longer hard-codes the obsolete 196/20 graph;
   its generator reads the active manifest and emits the live values. The main/supplement
   split adds another governed PDF, and V4 integration must update the externally authored,
   mechanically checked values again for the final governed cells and deposit payloads.
9. The acmsmall production preview is now declared in both the release-manifest and
   archival-bundle inventories. The clean-clone verifier requires every artifact,
   including that preview, to be a subject-commit blob before it may emit or accept
   `release_ready=true`; draft replay may record a worktree-only preview but verifies its
   current bytes and labels that weaker binding explicitly. The final merge must rebuild,
   visually inspect, and track the preview before strict attestation.
10. Rendered-page inspection confirmed the reader edition's visible figure sequence
   jumped from Fig. 1 to Fig. 4 because image alt text was not a printed caption and the
   tail composite duplicated a manual caption with the wrong number. Canonical Markdown
   now retains detailed accessibility alt text while providing one concise printed caption
   for each main figure in sequence; the long tail caption is shortened to avoid a page
   spill. The same inspection confirmed Table 1b's bottom rule crossing the acmsmall
   footer. Its governed generator now emits the table through the existing page-breakable
   `longtable` path with fixed ragged columns, instead of one unbreakable `tabularx`.
   Visual QA also found that the detailed fitted-operator diagnostic caption alone forced a nearly blank final
   reader page. Its printed caption is now concise while the detailed accessibility alt text
   remains intact; the reader renderer applies a targeted 75% maximum width to that diagnostic
   so the caption remains with it, without changing global figure typography. Rebuilt-page
   visual verification remains part of the final post-V4 PDF ritual.
11. The reader renderer now derives a deterministic outline from every canonical level-2
   Markdown heading, requires each target to resolve to exactly one rendered page, and verifies
   the final outline count. It also requests visible page folios through Chromium paged-media
   margin boxes. Final visual QA must confirm the active Edge engine renders those folios; the
   venue PDFs remain governed separately by acmart.
12. The abstract is rewritten from a verdict ledger into one question-evidence-boundary spine.
   It retains the primary Amazon effect, matched-control boundary, prospective MovieLens
   failure, comparator scope, and fail-closed record, while removing secondary campaign
   chronology, verdict codes, and redundant estimates. The canonical and TeX abstracts carry
   the same under-190-word scientific content; the exact V4 sensitivity will be added only after its
   frozen adjudication, if it materially changes the comparator boundary.
13. The main Results section now opens its FIR evidence synthesis with one compact
   evidence-map figure rather than the narrower Software-only panel. Four positive
   outcome-known internal Amazon contrasts are shown beside the two matched MI control
   boundaries and both prospectively frozen same-investigator MovieLens transfer
   contrasts. The shared-filter and MovieLens intervals visibly cross zero. The caption
   states that source estimators and evidence classes remain separate and that the rows
   are neither pooled nor one common multiplicity family. The detailed Software paired-
   seed panel moves to Fig. S1 and the fitted-operator diagnostic becomes Fig. S2. A new
   fail-closed graph cell binds all eight plotted rows, labels, source keys, estimates,
   and intervals to six released adjudications; after V4 integration the graph is
   201 active cells across 25 families with zero mismatch or untraceable cells.
14. Section 4 now includes a compact comparator-design matrix that separates aligned
   dimensions from known mismatches for the Amazon identity, MI pointwise, MI shared,
   MovieLens six-arm, WEARec, AlphaFuse-style, and published/local HSTU-BLaIR
   comparisons. It makes architecture, parameter-count, temporal-access, initialization,
   endpoint-custody, and tuning-budget differences visible in one place. In particular,
   sharing a split/evaluator is no longer visually confusable with an equal-model or
   equal-budget experiment, and each row carries its exact supported scope.
15. Section 4 also adds an adjudication-derived MovieLens cohort-flow diagram. It shows
   the official 1,000,209-rating/6,040-user source, the rating-at-least-4 primary and
   all-ratings sensitivity branches, global 90% time eligibility, fixed-point user and
   training-catalog filtering, and exact final TRAIN/VALID/TEST counts. The caption makes
   the primary estimand's conditioning explicit: 1,102 candidate users become 1,033
   retained users over a 2,359-item training-observed catalog, so the cohort is not a
   random sample of all MovieLens users or movies. The existing aggregate MovieLens graph
   cell now verifies every plotted row against `data_provenance.views`; this adds no new
   estimand or evidence class.
16. Table 1 is no longer presented as the headline result. Section 5.1 and the table
   caption now call it descriptive system context and state why it cannot support the
   modular inference: the ladder mixes n=1, five-seed, and six-seed arms, lacks one
   pre-declared contrast family, and summarizes non-initialization-paired arms separately.
   The paper now points readers to the named matched-control and transfer studies in
   Section 5.2 as the FIR claim's evidential basis.
17. The venue-length and readability issue is now resolved as a main/supplement split
    against the official TORS guidance checked on 2026-07-31. The prior production-layout
    preview was 52 pages, outside the journal's usual 20--35 `acmsmall`-page range. The
    focused main article now compiles to 32 review-manuscript pages and 33 `acmsmall` pages.
    It retains the method, comparator-design matrix, primary Amazon evidence, matched
    controls, prospective MovieLens failure, current-comparator results, discussion, and
    limitations. Extended secondary-study narratives, superseded/VOID histories, probe and
    titration ledgers, and appendix tables compile into a separate 18-page reviewer
    supplement. No evidence, negative result, verdict, or claim boundary was deleted. Both
    main renderings and the supplement are now required build outputs; the health gate checks
    compiler completion, cross-references, content markers, forbidden claims, and the main
    paper's page range. All 33 main pages and all 18 supplement pages were rendered and
    visually inspected without clipping, overlap, blank-content loss, or table/figure loss.

18. The focused-package staging commit `6b3a2382` passed the full strict local rebuild before
    the V4 outcome was available. After V4 integration, commit `4bda1169` passed the full
    strict local rebuild again: generator/artifact equality checks passed, all 201 active
    cells across 25 required families recomputed with zero mismatch or untraceable cells,
    the claim map and generated Table 0 verified, every governed adjudicator passed, and
    the release manifest verified 1,073 files with zero missing release assets. The 57-page
    reader, both 33-page main-paper layouts, and 18-page supplement rebuilt successfully;
    every page containing new V4 text or Table 1b was rendered and visually inspected
    without clipping, overlap, or missing content. This is artifact-integrity evidence,
    not scientific confirmation or acceptance evidence. The separately hydrated
    clean-clone replay, final release/upload verification, and human author/contact/legal
    metadata review remain open at this checkpoint.

19. The separately hydrated pristine replay at `ecccfb6e` closed the machine-side
    clean-clone check. It installed and raw-hash-verified all 407 release-only assets,
    reran the 201-cell/25-family strict graph and every governed adjudicator, rebuilt the
    57-page reader, both 33-page main-paper PDFs, and 18-page supplement byte-stably,
    verified all 1,073 manifest files and 666 Git-backed entries, and ended with a clean
    tracked tree. The replay also exposed and repaired three portability defects before
    passing: platform-default newlines in generated evidence/TeX artifacts, a TeX wrapper
    fallback to a clone-local virtualenv, and an attestation validator that accepted only
    SHA-256 Git object IDs in this SHA-1 repository. None changed data, estimates,
    intervals, verdicts, or claim classes. The resulting record remains deliberately
    `clean_clone_draft_metadata_replay` with `release_ready=false`; mechanical replay does
    not supply missing author identity, legal review, independent custody, or acceptance
    evidence.

### Disposition against the 2026-07-30 23:27 prioritized rejection-risk list

This is a status ledger, not an acceptance uplift. `CLOSED IN STAGING` means the named
source/build defect has direct local evidence; it does not mean the paper is submission-ready.

| Audit risk | Current disposition | Evidence boundary / remaining work |
|---:|---|---|
| 1 | **OPEN — HUMAN** | Real author/affiliation/contact/running-header/declaration/release-creator metadata and legal/COI/funding review remain mandatory; no placeholder was invented. |
| 2 | **CLOSED IN STAGING** | Markdown and TeX now say the HSTU-BLaIR comparison has the same users/items but one fewer reported interaction; the health gate rejects the false identity wording. |
| 3 | **CLOSED IN STAGING** | The tracked result manifest was regenerated and strict submission mode independently regenerates it and requires byte equality before accepting its cells. |
| 4 | **OPEN SCIENTIFIC; FRAMING REPAIRED** | The negative, selected-cohort MovieLens result remains central and blocks general FIR/cross-domain claims; the module is optional and the paper is framed as bounded evaluation/falsification. |
| 5 | **PARTIAL — NORMAL-INIT SENSITIVITY COMPLETE** | V3 is labeled as a zero-initialized upstream-class control. V4 completed eight parser-default `Normal(0,1)` SASRec-ID runs and returned `EEV4-ALPHAFUSE-ABOVE-NORMAL-SASREC`; the package remained above this control by +0.005207 [+0.004779,+0.005635]. V4 is cross-campaign and does not supply the requested equal-budget 2x2 factorial, capacity match, text-only/ID-only decomposition, or permuted-text control. |
| 6 | **OPEN SCIENTIFIC** | The closest current systems are positioned accurately, but protocol-matched TV-Rec and a state-space/long-convolution baseline remain unrun. |
| 7 | **PARTIAL** | Table 1 is explicitly descriptive and no longer carries FIR inference; governed contrasts have exact vectors/estimators. A single valid inferential family for the heterogeneous historical ladder is neither claimed nor retrofitted. |
| 8 | **PARTIAL** | The new MovieLens cohort-flow figure exposes the 1,033/6,040 primary cohort and training-catalog conditioning. Rolling cutoffs, out-of-catalog-as-miss coverage, subgroup uncertainty, and another non-Amazon domain remain open. |
| 9 | **PARTIAL — HUMAN/ARCHIVAL RELEASE BLOCKED** | Graph/V4 counts and candidate-bundle inventory are mechanically aligned and the stale 908-entry ZIP is rejected. The pristine replay passes, but final creators, legal metadata, immutable tag/bundle, upload, and download/hash verification remain open. |
| 10 | **CLOSED MECHANICALLY; NOT RELEASE-READY** | Public guidance says tables are generated while TeX prose is separately maintained, and the health gate enforces that boundary. The outcome-complete clean-clone replay passes and its machine-readable record is committed as the designed attestation-only child. The record remains `release_ready=false` because human metadata are absent. |
| 11 | **PARTIAL — POST-V4 PDF CHECK CLOSED** | The paper is split into 33-page TORS and `acmsmall` mains plus an 18-page supplement. Post-V4 builds passed, the reader scan was clean, and all pages containing V4 text or Table 1b were visually checked. Real submission metadata and final accessibility/legal review remain open. |
| 12 | **OPEN HISTORICAL LIMIT** | V3 custody/resume history cannot be repaired retrospectively and external custody was not present. V4 must be reported only under its own frozen lifecycle; it is not independent custody. |
| 13 | **OPEN — AUTHOR/LEGAL** | Aggregate public arithmetic is replayable; lawful release or independent escrow of private endpoints/sidecars and institutional retention/licensing decisions remain open. |
| 14 | **OPEN SCIENTIFIC** | WEARec remains an equal-evaluation feasibility run with unequal architecture/training/search history, not an equal-budget matched comparison. |
| 15 | **OPEN SCIENTIFIC/ENGINEERING** | No true bypass, optimized structured kernel, or counterbalanced latency/memory/energy distribution supports a practical-efficiency claim. |
| 16 | **CLOSED IN STAGING (EDITORIAL SCOPE)** | The abstract follows one question--evidence--boundary spine; the main includes the FIR evidence map, cohort flow, and comparator-design matrix; chronology/VOID/probe ledgers moved to the supplement. Scientific risks above remain unchanged. |

The V4 verdict, post-V4 rebuilt-PDF verification, and separately hydrated clean-clone
replay are now integrated. The immutable archival candidate and human metadata/legal items
remain open and will not be marked closed by these machine-side repairs.
