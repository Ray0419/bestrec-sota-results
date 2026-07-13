# Response to PAPER_REVIEW_AUDIT (cumulative)

This response file is cumulative, mirroring `PAPER_REVIEW_AUDIT.md`: each audit run gets a
timestamped response section below. The newest section always addresses the audit's newest
"Audit Run" section and its updated risk list.

> **Historical log.** Each section records the state at its own timestamp; page counts,
> cell counts, and "in flight" phrases in older sections are point-in-time statements that
> later sections supersede. This file is an audit-trail document, **not** submission-package
> metadata (`CANONICAL_SUBMISSION.md` governs), and is not included in deposit bundles.

## Response — to Audit Run 2026-07-13 20:57 (responded 2026-07-13, same day)

**Verdict acknowledged:** no reject-level defect reproduced — the §6.5 fix verified in source
and compiled-PDF extraction; strict gate, manifest, MI V2, Office V1 descriptive, and Office V3
adjudication all green on the auditor's own re-runs. Every remaining item is documentation or
policy; all are now closed except the one explicitly deferred to the freeze.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1 | No hard rejection defect | Acknowledged; nothing to fix. |
| CP-2 | `BUILD_NOTES.md` stale 35/36-page references | **Fixed.** The file-tree comment (a current-state diagram, not a log entry) now reads 40 pp / 40 pp; the acmsmall "36 pages" compile-status line carries the same *(round-8 count; current builds are 40/40 — see header)* marker the manuscript line already had. Line 84's "35 pages" already says "at the round-8 build" — explicitly historical, left as log. |
| Fix-1 | Manifest sync discipline | Acknowledged + open question answered below: the transient dirty state the audit observed **was** the concurrent 19:54-response ritual completing (see timeline). No non-atomic script window exists: `--regen` and the commit are steps 4–5 of the same ritual, and `--verify` (run inside every strict build) fails on any dirty manifested file, so the repo cannot *settle* in that state. |
| Fix-2 | BUILD_NOTES cleanup | Done (CP-2). |
| Fix-3 | Sidecar deposit policy | **Decided and stated once, in §8 (md + TeX) and mirrored in `CANONICAL_SUBMISSION.md`:** the tracked-artifact boundary is the intended reproducibility contract (every printed claim recomputes from tracked, hash-manifested artifacts; no dependence on any local-only file); local-only per-user sidecars are supplementary audit material, pre-committed by hash in tracked run manifests, **provided on editorial/reviewer request and deposited as supplementary material upon acceptance** — any later deposit byte-verifiable against the already-tracked hashes. |
| Fix-4 | SILLM4Rec | **Explicitly marked pending, structurally:** `VENUE_PLAN.md` now has a pre-submission freeze checklist whose item 1 is "SILLM4Rec full-paper inspection — PENDING", with the repo-evidence rationale and the disclosure path if the ACM full text stays inaccessible. The paper's exclusion sentence is unchanged (it rests on repo evidence, which the audit itself confirms). |
| Fix-5 | Claim-boundary alignment | Standing discipline. Bonus catch while executing this: `VENUE_PLAN.md`'s hygiene-sweep description still carried the **pre-V3** wording "Office never a passed category" — rescoped to "Office **V1** never presented as passed (VOID permanent); Office **V3** only within its frozen wording". Also refreshed `CANONICAL_SUBMISSION.md` stale counts (12→14 families, 164→168 cells) and added the V3/FIR-breadth results-of-record entries. |
| PR-1 | Sidecar release boundary | Closed by Fix-3. |
| PR-2 | SILLM4Rec inspection | Closed as explicitly-pending by Fix-4 (freeze-gated, maintainer go-signal required). |
| PR-3 | Untracked raw breadth archives | **Boundary made explicit** in `FIR_BREADTH_RESULTS.md` ("Data boundary" section): the two `.csv.gz` are intentional local downloads of the public AR2023 release (raw data is never redistributed, same as the four original categories); the derived splits are untracked but pinned — all 20 tracked run JSONs embed split SHA256s under `provenance.data_sha256`, and the preprocessing code is tracked, so every printed breadth cell's dataset identity is byte-verifiable. §8 states the same in one sentence. |

### Open questions answered

- **Transient dirty manifested files:** yes — concurrent work, not a script defect. The audit
  recorded HEAD `1f48b726`, which predates the two 19:54-response commits; its first strict run
  landed inside that response's render→commit window (renders done, commit not yet landed), and
  by the audit's own SHA256 recheck the commits had landed and everything matched. The ritual
  always ends commit-then-strict, and `--verify` fails on dirty manifested files, so this state
  cannot persist silently.
- **Sidecar deposit:** policy now stated once in §8/release docs (Fix-3).
- **Is `PAPER_SUBMISSION.pdf` live?** Yes, with distinct roles: `PAPER_SUBMISSION.md`/`.pdf` is
  the canonical reader edition (governs content, per `CANONICAL_SUBMISSION.md`);
  `paper_tex/PAPER_TORS.pdf` (+ untracked acmsmall preview) is the venue manuscript generated
  from it. Both stay manifested; neither supersedes the other.

**Ritual:** `render_paper_pdf.py` → 45 pp, scan **CLEAN**; `paper_tex/build.sh` → hygiene
**PASS**, 40 pp; `update_release_manifest.py --regen`; committed together;
`rebuild_hstu_submission.py --strict` → exit 0 (**168 cells, 0 mismatch, 0 untraceable, 14/14
families, 113-file manifest OK**); manifest + refreshed PDFs re-uploaded to both releases.

## Response — to Audit Run 2026-07-13 19:54 (responded 2026-07-13, same day)

**Verdict acknowledged:** both gates green on the auditor's own fresh re-runs (strict rebuild:
168 cells / 0 mismatch / 0 untraceable / 14 families / 113-file manifest OK; Office V3
adjudication PASS with the exact per-seed finals reproduced). The single confirmed blocker —
the §6.5 Office prose contradiction — is fixed.

### Confirmed problem 1 (risk #1): §6.5 still said "the second-category pass is VOID … and no claim counts Office"

**Fixed — the bullet is now scoped precisely to V1 and states the V3 pass.** The old bullet
predated the V3 campaign and was never updated when §5.2/§6.4 were; it read as an unscoped
"Office" status and therefore contradicted the counted V3 pass. Rewritten in all three live
sources (`PAPER_SUBMISSION.md` §6.5, `PAPER_DRAFT.md` §6.5,
`paper_tex/sections/06-discussion.tex` line 81) as **"Office_Products status (V1 vs V3,
stated precisely)"**:

- the **V1** floor check failed (+44%) → the V1 second-category pass is **VOID** and the V1
  campaign counts in no claim (unchanged, forever);
- the **redesigned V3** (environment-matched reference, fresh seeds) **passed and is counted**
  (§5.2) — strictly under its frozen wording: per-category point-estimate comparison, no
  paired/distributional superiority, not SOTA of any kind;
- the limitation that genuinely remains is stated in the claim's place: both counted
  comparisons (MI, Office V3) gate against single-seed published values and a single-run
  local regeneration, so distributional comparator uncertainty is unquantified.

No caveat was weakened: the bullet still opens with the V1 VOID, and the residual
single-seed-comparator limitation is now *more* explicit than before. `grep` confirms zero
occurrences of "no claim counts Office" remain in any live paper source; the phrase survives
only in audit-history documents quoting the old text.

**Ritual:** `render_paper_pdf.py` → 45 pp, scan **CLEAN**; `paper_tex/build.sh` → hygiene
verdict **PASS**, both PDFs rebuilt (40 pp); `update_release_manifest.py --regen` (three
re-rendered artifacts re-hashed); committed together; `rebuild_hstu_submission.py --strict`
→ exit 0 (**168 cells, 0 mismatch, 0 untraceable, 14/14 families, manifest 113 files OK**);
refreshed PDFs + manifest re-uploaded to the release.

### Non-blocker risk items (positions restated, no action needed)

- **#4 sidecar boundary / #7 FIR novelty wording / #9 claim boundary:** standing discipline;
  the fixed §6.5 bullet itself now models the required precision. No live text drifted.
- **#5 SILLM4Rec:** full-protocol inspection of the ACM PDF remains on the pre-submission
  freeze checklist (maintainer-gated), as recorded previously. The current repo-evidence-based
  exclusion rationale stands in both sources.
- **#6 BUILD_NOTES:** the audit itself notes the historical labels are in place and current
  page counts (40/40/45) are correctly recorded; left as the append-only build log it is.
- **#8 methodology-first fit:** framing kept narrow (apparatus demonstrated on concrete
  empirical claims); no broadening.

## Response — to the 2026-07-13 risk-list refresh (incl. back-filled runs 00:40 / 01:42 / 02:41 and the 16:49 re-adjudication)

The audit process back-filled three overnight run sections and refreshed the prioritized risk
list against the post-V3 workspace. The three overnight runs' findings were consolidated into
the 05:40/06:46 runs already answered (breadth staleness, provenance tracking, erratum
ordering, Caser/NextItNet — all resolved at commits `9619f5d`…`045d6a6`). The refreshed list's
three confirmed blockers were V3-integration stragglers; all fixed:

| # | Finding | Resolution |
|---|---|---|
| 1 | Office V3 status internally inconsistent (intro, related-work, conclusion, a limitation still said "outcome pending") | **All sites updated** in both papers and the LaTeX twin: each now states the pass with the V1-VOID-stands pairing; the conclusion carries the full arc ("the apparatus caught its own comparability flaw, the redesign removed it by construction, and the fixed protocol passed"). Verified: **zero occurrences of "outcome pending" remain** in the md, tex, or either compiled PDF. |
| 2 | Availability boundary stale for a *counted* V3 claim | §8 rewritten to state the boundary exactly: the ten V3 result JSONs and per-run tree-state provenance sidecars are **tracked** (every printed V3 claim recomputes from these via the fail-closed gate); per-user sidecars for Office V1/V3 and FIR-breadth are local-only with SHA256s embedded in each run's tracked manifest, inventoried in `OFFICE_V3_RESULTS.md`. |
| 3 | Three V3 runs have `user_records_final_path = null` vs the prereg's final-sidecar promise | **ERRATUM E2** (dated, post-campaign, disclosure-only): the writer emits a separate `*.final` sidecar only when best-epoch ≠ final-epoch; for the three coinciding runs the regular sidecar *is* the final-epoch record (hash-embedded). A 10-row per-run sidecar inventory is appended to `OFFICE_V3_RESULTS.md`. No data missing; no gate, seed, or wording change. |
| 6 | Abstract "reference implementation cannot execute" contradicts §5.6 | Fixed to the precise distinction: the **pinned official environment** cannot execute locally; the research path runs only as unpinned, shimmed, environment-caveated regenerations (§5.6). |
| 7 | BUILD_NOTES staleness (page counts, resolved CCS warning, old hygiene wording) | Fixed: round-8 counts marked historical, CCS warning marked RESOLVED with pointer, and the hygiene description updated to the current claim boundary (V1-as-passed forbidden; V3 citable only per its frozen wording). |
| 9 | SILLM4Rec exclusion should cite observed evidence | Upgraded in both papers using the audit's own repo findings: "generated candidate-ranking tasks with SFT/DPO workflows rather than full-catalog LLOO ranking, so the accessible evidence indicates a non-interchangeable protocol." |
| 8 / 10 / 11 | FIR novelty stays narrow; methodology framing stays narrow; scientific boundary | Affirmed — no wording touched beyond the fixes above; the FIR claim remains the leak-free zero-init depthwise FIR regularizer in this artifact-gated setting; the apparatus is framed as an auditable per-paper discipline demonstrated on concrete claims; the boundary list is enforced by the responder's standing rules. |

**Verification:** md 45 pp / 3 images / scan CLEAN; TORS 40 pp scan PASS (review list steady at
18, all explicit non-claims); numeral fidelity zero-missing; manifest regenerated; strict chain
PASS (168 cells 0/0, 14/14 families; 113 files verified) → pushed. Items 4–5 of the refreshed
list are the audit's own fresh-green re-runs of both gates, concurring.

## Response — to Audit Run 2026-07-13 06:46 (responded 2026-07-13, same day)

This run audited the two-minute window between the FIR-BREADTH campaign completing (06:44) and
its integration landing. Every confirmed problem was resolved by the intervening milestone
commits (`9619f5d` … `acbe282`) and the Office V3 completion that followed; itemized:

| # | Finding | Resolution |
|---|---|---|
| 1 | Paper stale vs workspace (breadth confirmed but presented as pending) | Integrated same morning under the frozen wording (commit `9619f5d`): §5.2 breadth paragraph, abstract, Table 0, §4.1 roles — four-category claim, nothing broader. |
| 2 | Campaign not citable (untracked scripts/results; gate not extended) | All committed at `9619f5d`: 20 result JSONs, driver, adjudicators, prep scripts, data provenance, adjudication record; the `fir_breadth` manifest family gates every printed breadth numeral (now 168 cells, 14/14 families GREEN). |
| 3 | Office V3 erratum uncommitted; only defensible if committed before the first V3 run and kept narrow | **Both conditions provable from git**: ERRATUM E1 is in commit `9619f5d`; every one of the 10 V3 run manifests records commit `acbe282f` — a descendant — so the erratum predates every run. It is narrow by construction (exactly the two external audit-log files; all protocol code still bound; per-run treestate sidecars verify exempt-only dirt — the adjudicator checked all 10). |
| 4 | Breadth claim wording must stay narrow | It did — the paper quotes the frozen wording verbatim; no comparator or SOTA language anywhere in the breadth material. |
| 5 | Caser/NextItNet convolutional prior art missing | Cited at `9619f5d` (§2.3 + Table 0, Crossref-verified DOIs) with the explicit FIR-tap-bank-vs-conv-encoder distinction. |
| 6 | SILLM4Rec exclusion needs caution | The current sentence is already the cautious form this audit line previously endorsed ("excluded pending direct protocol inspection; accessible metadata did not establish an apples-to-apples AR2023 5-core full-catalog LLOO setting"); full-text inspection remains on the freeze checklist. |

**Since this audit ran, the Office V3 campaign completed and PASSED** (both arms: K=16 CI-LB
0.03033, K=8 CI-LB 0.03024, 10/10 seeds above both the local regeneration 0.0279 and the
published 0.0271; mechanical adjudication `OFFICE_V3_RESULTS.md`, all comparability conditions
verified incl. the E1 treestate evidence). It is integrated in both paper formats under the
frozen claim wording; the V1 VOID stands unchanged. Claim boundary now: **two counted
pre-registered per-category point-estimate comparisons (MI, Office V3)** — nothing broader.

**Verification:** SUBMISSION BUILD GREEN (168 cells, 0/0, 14/14 families incl. `office_v3`);
both PDFs rebuilt (md 45 pp / 3 images / CLEAN; TORS 40 pp scan PASS, zero missing numerals);
manifest regenerated; strict chain PASS; pushed.

## Response — to Audit Run 2026-07-13 05:40 (responded 2026-07-13, same day)

Verdict received: paper builds cleanly; blockers were moving-scope evidence (mid-campaign
snapshot) and the FIR novelty boundary's missing convolutional prior art. The audit ran while
the FIR-BREADTH campaign was mid-flight; all findings are now resolved by completion +
integration.

| # | Finding | Resolution |
|---|---|---|
| 1 | CDs_and_Vinyl "void, despite favorable-looking partials" — selective peeking risk | **Resolved by the process working as designed**: no partial was ever reported anywhere; the mechanical adjudicator ran only after all 20 pairs completed (06:44), per the frozen rule. Final verdicts: **both categories CONFIRMED** (IS +0.0024, CI [+0.0018, +0.0030]; CDs +0.0057, CI [+0.0049, +0.0064]; 5/5 seeds positive each), recorded in `FIR_BREADTH_RESULTS.md`. |
| 2 | Manuscript stale vs workspace | **Integrated under the frozen claim wording**: §5.2 breadth paragraph, abstract clause, contribution bullet, Table 0 evidence column, §4.1 role rows (pending → CONFIRMED) — in both papers and the LaTeX twin; the filter is now stated as confirmed on **four categories**, nothing broader. |
| 3 | FIR novelty paragraph omits convolutional SR prior art | **Repaired**: Caser (Tang & Wang 2018) and NextItNet (Yuan et al. 2019 — dilated *causal* convolutions) are cited in §2.3 and Table 0's prior-art column, with the explicit distinction: our filter is a single **depthwise, linear FIR tap bank** (no nonlinearity, no channel mixing, zero-init no-op) acting as a frequency-filter *regularizer* inside an attention stack — not a convolutional sequence encoder. Crossref-verified DOIs in the bibliography. |
| 4+5 | FIR-BREADTH not provenance-clean (scripts/results untracked; no adjudication record; dirty manifests) | **All committed now**: the 20 result JSONs, driver, both adjudicators, prep/encode scripts, data provenance JSONs, and the official adjudication record; the new `fir_breadth` manifest family gates the printed numbers (**SUBMISSION BUILD GREEN: 166 cells, 0/0, 13/13 families**). The dirty-manifest observation was the hourly audit's own file appends — addressed structurally by **PREREG_OFFICE_V3.md ERRATUM E1** (dated, pre-campaign): the two external audit-log files are exempt from condition 3, with per-run treestate sidecars captured by the driver and verified by the adjudicator so any dirty state is *provably* exempt-only. The FIR-BREADTH prereg never required a clean tree (code identity via embedded hashes, as disclosed at design time). |

**Verification:** both PDFs rebuilt (md 44 pp / 3 images / CLEAN; TORS 39 pp scan PASS,
numeral-fidelity zero-missing) → manifest regenerated → strict chain **PASS** (166 cells 0/0,
13/13 families; 113 files verified) → pushed. The Office V3 campaign relaunches on this clean
boundary.

## Response — to Audit Run 2026-07-12 23:39 (responded 2026-07-13)

Verdict received: prior blockers repaired, gates green; remaining problem is §4.1 scope/count
description. Both confirmed problems fixed; note that this response also lands alongside the
approach-(C) methodology reframe and the committed impact-program pre-registrations
(IMPACT_REVISION_PLAN.md), which the next audit run will see.

| # | Finding | Resolution |
|---|---|---|
| 1 | §4.1 says "two categories" (VG + Beauty) — contradicts the paper's actual scope | Rewritten as the audit's suggested **role-based dataset table** covering every category used anywhere: VG (headline + tail null), MI (FIR confirmation + pre-registered comparator confirmation), Office (VOID/descriptive + V3 prereg pending), Beauty (tail null + appendix scan), plus the two **pending FIR-breadth campaign categories** (Industrial_and_Scientific, CDs_and_Vinyl) listed for scope completeness with an explicit "no result from them is claimed" sentence. The LaTeX version is **emitter-generated** (new registry entry), not hand-retyped — and the emitter's fail-closed table-count check caught the addition before the registry was updated, exactly as designed. |
| 2 | §4.1 mixes total vs train-only interaction counts | Fixed with the audit's own verified numbers: the table states **total 5-core interactions** (VG 814,586; MI 511,836; Office 1,800,878; Beauty 6,624,441) with the LLOO rule stated inline (train = total − 2 × users), replacing the ambiguous "~830k"/"5.17M" figures. |
| R-phrasing | "Unreviewed concurrent work" is brittle | Adopted: "concurrent arXiv-only work" in §5.1 and "status as of the access date" in the reference notes — no review-status claim remains where none is needed. |
| R-SILLM4Rec | Closer than a footnote suggests | Agreed with the audit's own conclusion: "excluded pending direct protocol inspection" is the right stance and is exactly what the paper says. |

**Verification:** both PDFs rebuilt (md 44 pp / 3 images / CLEAN; TORS scan PASS) → manifest
regenerated → strict chain **PASS** (164 cells 0/0, 12/12 families; 113 files verified) → pushed.

## Response — to Audit Run 2026-07-12 21:37 (responded 2026-07-12, same day)

Verdict received: gates green, prior contradiction repaired; one new confirmed methods
contradiction (§3.2) and one stale reference status (WPGRec). Both fixed, plus the flagged
rhetoric item.

| # | Finding | Resolution |
|---|---|---|
| 1 | §3.2 describes a 2-layer SASRec as "our base model" while every headline run is the 4-layer HSTU-style encoder (result JSONs confirm `encoder: hstu`, `n_layers: 4`) | **Restructured exactly as the audit prescribes, in both papers and the LaTeX twin**: §3.2 now presents (a) the shared item-feature construction, (b) the **headline HSTU-style encoder** — every §5 result; pointwise `silu(QKᵀ+rab)V`, bitwise core-block parity; config stated once in method and once in experiments (**4 layers, 2 heads, d=64, dropout 0.5**) — and (c) SASRec-SBERT demoted to the parity/floor + Appendix-A.1 baseline with an explicit "**no headline number uses this encoder**" sentence. §4.3's "(§3.2)" cross-reference is now correct by construction. Verified in both rebuilt PDFs: the stale phrase is gone, the headline description present. |
| 2 | WPGRec labeled "unreviewed" but arXiv says accepted to SIGIR 2026 | Reference moved out of the unreviewed-preprint block into the main list as "SIGIR 2026 (accepted; arXiv:2604.21305)" in both papers; bib note updated; "SIGIR 2026" verified present in both PDF extractions. Its role is unchanged: broader frequency/time-frequency prior art, not an AR2023 comparator. |
| R-rhetoric | "resolves the open mechanism" too strong | Softened in the abstract (md + tex) to "**partially resolves** the open mechanism **(under the thinning intervention's assumptions)**" — matching the §5.4.2 claim language exactly; a claim-narrowing edit. |
| R-SILLM4Rec / R-density | Full-text inspection; abstract/Table-2 density | Unchanged freeze-time items; the SILLM4Rec repo finding (5-core AR2023 handling but no full-catalog-LLOO evidence) supports keeping the current narrow exclusion sentence. |

**Verification:** both PDFs rebuilt (md 41 pp / 3 images / CLEAN; TORS scan PASS); all four edits
verified in both extractions → manifest regenerated at the clean boundary → strict chain
**PASS** (164 cells 0/0, 12/12 families; 113 files verified) → pushed.

## Response — to Audit Run 2026-07-12 18:37 (responded 2026-07-12, same day)

Verdict received: gate green; one confirmed manuscript self-contradiction (§6.1 vs Appendix A.1
on the MLP adaptor). Fixed in full.

| # | Finding | Resolution |
|---|---|---|
| 1 | §6.1 says the MLP adaptor is "the only consistently-positive intervention" + a denoising hypothesis, contradicting A.1's clean ablation (adaptor-alone negative: 0.01889 vs ≈0.0190) | **Rewritten exactly along the audit's line, in both papers and the LaTeX twin**: the transfer signal is attributed to *text content* (BLaIR + rich item text, with the adaptor present only as part of that bundle); the adaptor's parametric form alone is stated as negative in the clean ablation; the denoising hypothesis is **explicitly retracted as not supported**, with any residual account scoped to the inseparable bundle. Verified in both rebuilt PDFs: the contradiction phrase is absent, the corrected attribution present. This is a claim-narrowing correction — the discussion now matches the appendix evidence instead of overselling a component. |
| R-collapse | Collapse §6.1–6.2 to an appendix pointer? | **Declined for now, with rationale**: with the contradiction fixed, §6.1–6.2 carry the honest cross-pipeline-transfer interpretation that supports the negative-result contribution; they are already framed as appendix-supporting material. Revisit at freeze alongside the Table-2 presentation decision. |
| R-SILLM4Rec | Freeze-time full-text inspection | On the freeze checklist (unchanged); the current neutral exclusion sentence stays accurate either way. |
| R-abstract | Abstract density / mechanism language | Noted as a freeze-time readability pass candidate — with the standing constraint that caveats are never shortened for space; if anything moves, mechanism detail moves out of the abstract into §5.4, not the other way. |

**Verification:** both PDFs rebuilt (md 41 pp / 3 images / CLEAN; TORS scan PASS); contradiction
phrase verified absent from both extractions → manifest regenerated at the clean boundary →
strict chain **PASS** (164 cells 0/0, 12/12 families; 113 files verified) → pushed.

## Response — to Audit Run 2026-07-12 17:35 (responded 2026-07-12, same day)

Verdict received: **no numerical, provenance, or claim-boundary rejection defect** — the two
confirmed items are writing/metadata polish. Both fixed.

| # | Finding | Resolution |
|---|---|---|
| 1 | "not accessible to our tooling" leaks audit process into journal prose | Replaced with the audit's suggested neutral wording in both papers **and** the LaTeX twin: *"A further candidate, SILLM4Rec (MMAsia 2025), is excluded pending direct protocol inspection; accessible metadata did not establish an apples-to-apples AR2023 5-core full-catalog LLOO setting."* Verified absent from both rebuilt PDFs' extractions. |
| 2 | CCS/keywords closure is TORS-artifact-specific; the markdown PDF's role must be explicit | Made explicit **on the artifact itself**: `PAPER_SUBMISSION.pdf` now carries a front-matter line declaring it the *reader edition rendered from the canonical markdown*, pointing to `paper_tex/PAPER_TORS.pdf` as the ACM review artifact that carries venue metadata. **Clarification of the prior response's wording**: the round-11 "verified in extraction" statement referred to the TORS artifact only (content-level check: CCS block + keyword terms) — the markdown PDF never carried and is not intended to carry ACM metadata; this response supersedes any broader reading, per the historical-log banner. |
| R-SILLM4Rec | Obtain the full PDF before freeze? | Noted for the freeze checklist: if institutional/author access materializes, SILLM4Rec gets protocol-inspected and either enters clause (iv) with a non-comparability note or stays excluded; the paper's current sentence is accurate either way. |
| R-table2 / R-p1 / R-lit | Standing freeze-time items | Unchanged: Table 2 dense-by-design pending freeze/reviewer preference; first-page acmart review-mode text verified against TORS workflow at freeze; final sweep at the maintainer's go signal. |

**Verification:** both PDFs rebuilt (md 41 pp / 3 images / CLEAN, reader-edition note renders;
TORS 36 pp scan PASS, leak absent) → manifest regenerated at the clean boundary → strict chain
**PASS** (164 cells 0/0, 12/12 families; 113 files verified) → pushed.

## Response — to Audit Run 2026-07-12 16:32 (responded 2026-07-12, same day)

Verdict received: **"No new hard rejection defect found in this run"** — both prior confirmed
defects verified fixed; remaining items are submission-readiness and reviewer-perception risks.
All actioned.

| # | Finding | Resolution |
|---|---|---|
| 1 | Recent AR2023-adjacent coverage may look selective (Augment-or-Not?, DiffuReason, SILLM4Rec) | §5.1 gains **clause (iv) — "Other AR2023-adjacent, non-interchangeable protocols"** in both papers and the LaTeX twin: *Augment or Not?* (Huang et al., 2025, arXiv:2505.23053 — MI/Industrial_and_Scientific 5-core LOO, best listed MI 0.0282) and **DiffuReason** (Jiang et al., 2026, arXiv:2602.09744 — different "Video & Games" universe 67,658/25,535/654,867, cited *precisely to flag non-comparability*, which reinforces the no-Video_Games-claims boundary exactly as the audit reasoned); **SILLM4Rec's exclusion is documented in the paper text** (full text inaccessible pending direct inspection — the audit's own condition). Metadata fetched from arXiv listings; two References entries added under the concurrent-preprint fence. |
| 2 | CCS concepts / keywords absent | **Closed now instead of deferred again**: `egin{CCSXML}` block (Information systems~Recommender systems [500], Personalization [300]) + `\ccsdesc` + `\keywords` added to `paper-shared.tex`; verified present in the compiled PDF's extraction. The maintainer can adjust the taxonomy lines at freeze, but the recurring "metadata absent" finding is gone. |
| R-p1 | First-page "Manuscript submitted to ACM" repetition | Kept as-is per the audit's own caution ("verify against the exact TORS workflow before freeze, don't change acmart blindly") — this is standard acmart review-mode topmatter+footer output; logged as a freeze-time verification item in VENUE_PLAN's typesetting rules. |
| R-table2 / R-lit | Table 2 density; freeze sweep | Standing positions unchanged: dense-by-design until freeze or reviewer request; final sweep at the maintainer's go signal. This round's two additions came from the audit's sweep — the process is doing exactly what the freeze sweep will do, continuously. |

**Verification:** both PDFs rebuilt (md 41 pp / 3 images / CLEAN; TORS 36 pp, scan PASS, CCS +
keywords + both new citations verified in extraction) → manifest regenerated at the clean
boundary → strict chain **PASS** (164 cells 0/0, 12/12 families; 113 files verified) → pushed.

## Response — to Audit Run 2026-07-12 15:31 (responded 2026-07-12, same day)

Verdict received: numerical/provenance package green; submission formatting not yet green (header
collision + one wording overstatement). Both confirmed problems fixed and visually verified.

| # | Finding | Resolution |
|---|---|---|
| 1 | Running title collides with page numbers (pp. 23/29 of the TORS review build) | Fixed with the audit's suggested mechanism: `	itle[Causal FIR Filtering in an HSTU-Style Recommender]{…full title…}` in `paper-shared.tex`; both TeX targets rebuilt, hygiene scan PASS, and the previously-affected pages **re-rendered and visually inspected** — the short running head now sits clear of the page number on both. |
| 2 | "The Musical_Instruments comparator reproduces" overstates an unpinned run | Softened to the caveat boundary in both markdown papers **and** the LaTeX twin: the §5.6 heading now reads "regenerates locally", the in-paragraph sentence reads "a local run of the generating code regenerates it under the unpinned shimmed research path", and §5.2 says "regenerates the published value". The titration-internal "reproduces the MI-subcritical anchor" (our runs vs our own anchor, no comparator involved) is deliberately unchanged. |
| Q1 | Is `PAPER_SUBMISSION.pdf` still a live deliverable? | Yes, with distinct roles: `PAPER_SUBMISSION.pdf` is the **canonical-markdown render** — the human-readable output of the artifact-gated source that repository readers and these audits consume; `paper_tex/PAPER_TORS.pdf` is the **venue review artifact**. Both are manifest-gated; neither supersedes the other until submission, when TORS receives the LaTeX build. |
| Q2 | Should the response log enter the manifest/deposit boundary? | By policy, no (historical-log banner): it is audit-trail correspondence, not package metadata. If a venue's artifact track wants the correspondence, it ships as clearly-labeled ancillary material outside the hash boundary — the boundary statement in `manifest_scope` covers this. |
| R-table2 / R-CCS / R-lit / R-HyTiFRec | Standing items | Positions unchanged and restated: Table 2 stays complete-by-design until freeze or reviewer request; CCS concepts + keywords are drafted at submission freeze; the final literature sweep runs at the maintainer's go signal; WPGRec suffices as the representative time-frequency citation per the audit's own note ("not strictly required after WPGRec"). |

**Verification:** both PDFs rebuilt (md 40 pp / 3 images / CLEAN; TORS manuscript scan PASS with
header fix visually confirmed) → manifest regenerated at the clean boundary → strict chain
**PASS** (164 cells 0/0, 12/12 families; 113 files verified incl. the dirty-file gate) → pushed.

## Response — to Audit Run 2026-07-12 14:34 (responded 2026-07-12, same day)

Verdict received: review format substantially fixed; the new top blocker is the manifest hashing
an uncommitted generator edit. All three confirmed problems fixed, with the blocker class closed
structurally.

| # | Finding | Resolution |
|---|---|---|
| 1 | Manifest hashed a git-dirty `emit_latex_tables.py` (clean clone would not verify) | **Healed and made un-leakable.** The dirty `llowbreak` line was the typesetting agent's intended overfull fix that the orchestrator's phase-B `git add` list missed — it is now committed, and the manifest regenerated at the clean boundary. Structural fix so this class cannot recur: `--verify` (which the strict wrapper runs) now **fails on any git-dirty manifested file**, and `--regen` prints a commit-together checklist of dirty manifested files. The audit's own scenario — verify passing only because the dirty file matches — is now impossible: dirty ⇒ gate failure. |
| 2 | `BUILD_NOTES.md` stale document-class paragraph | Rewritten to describe both targets: `manuscript,review,anonymous` review default → `PAPER_TORS.pdf`; `acmsmall` production preview (untracked); shared `paper-shared.tex` carries the journal metadata. |
| 3 | Uncited "subsequent time-frequency architectures" | Phrase replaced with a **cited representative**: WPGRec (Liu, Ji, Yan, 2026 — "Wavelet Packet Guided Graph Enhanced Sequential Recommendation", arXiv:2604.21305, metadata fetched from the arXiv listing) in §2.3 of both papers and the LaTeX twin; reference entries added under the concurrent-preprint fence. |
| R-boundary | Should the manifest `git_commit` advance past response-only commits? | Boundary already explicit in `manifest_scope` (manifest describes the recorded commit; its own commit is the child); response files are outside the deposit boundary per the historical-log banner. With the new dirty-file gate, any *content* commit that touches manifested files now forces a regen, so the boundary tracks content changes mechanically and ignores response-only commits by construction. |
| R-CCS / R-table2 / R-lit | CCS concepts/keywords, Table 2 split, literature freeze | Unchanged positions, restated: CCS concepts + keywords are drafted at submission time (TORS requires them in the workflow, not in the audit build); Table 2 split deferred to freeze or reviewer request with the completeness rationale; the final literature sweep runs at the maintainer's TORS go signal — this round's WPGRec addition came from the audit's own sweep, which is the process working. |

**Verification:** both PDFs rebuilt (md: 40 pp / 3 images / scan CLEAN; TORS manuscript: 35 pp /
scan PASS + acmsmall preview) → manifest regenerated at the clean boundary → strict chain
**PASS** (164 cells 0/0, 12/12 families; **manifest verify OK incl. the new dirty-file gate**)
→ pushed.

## Response — to Audit Run 2026-07-12 12:34 (responded 2026-07-12, same day)

Verdict received: material progress, prior top blockers closed, gate passes; remaining risks are
format policy, deposit boundary, table readability, and bibliography polish.

| # | Finding | Resolution |
|---|---|---|
| 1 | TORS review build uses `acmsmall`, ACM's general workflow wants `manuscript` for review | **Adopted the audit's preferred resolution**: the build is being restructured so the default review target compiles `[manuscript,review,anonymous]` → `PAPER_TORS.pdf` (the manifest-gated artifact), with `acmsmall` retained only as an untracked production-preview target; `VENUE_PLAN.md` documents the policy with ACM's own guidance cited. **Landed same day** (commits `7a627ef` + `074f122`): two-target build — default review target `[manuscript,review,anonymous]` → `PAPER_TORS.pdf` (35 pp US-Letter, 0 errors, hygiene scan PASS, numeral fidelity intact), `acmsmall` kept as an untracked production preview; format verified by page geometry (612×792 vs 486×720). Note: acmart's `manuscript` and `acmsmall` are both single-column, so pages barely move — the compliance point is the class option, now exactly ACM's review instruction. Same pass: **21 bibliography entries gained registry-verified metadata** (Crossref / ACL Anthology / PMLR; DOIs render; unverifiable fields left empty with documented reasons — nothing invented). |
| 2 | Response prose stale ("in flight", old page counts) | Structural fix: the response file now opens with a **Historical-log banner** (sections are point-in-time records, superseded by later sections; the file is audit-trail, not package metadata, and is excluded from deposit bundles), and the two specific in-flight clauses are closed with their landing commits. |
| R-deposit | Should the deposit hash/package the paper_tex source tree? | **Boundary stated in the manifest itself** (`generated_artifacts_note`): the LaTeX *source* tree is governed by git at the recorded `git_commit`; the manifest hashes only the rendered `PAPER_TORS.pdf`; deposit bundles requiring source ship the git archive of that commit. |
| R-table2 | Split Table 2 for readability? | **Deferred with rationale**: the negative-result map's completeness is itself the finding, TORS journal format carries no page pressure, and splitting is a content-organization change we will take up at submission freeze or on direct reviewer request — not silently now. |
| R-bib | Fill BibTeX production metadata | Dispatched with the class-option task: fields filled **only where verifiable** from authoritative listings (never invented); arXiv-only entries stay arXiv-only. Committed on landing. |
| R-lit | Final literature sweep before freeze | Agreed and scheduled **at submission freeze** (the maintainer's TORS go signal), covering 2026 AR2023 5-core, semantic-ID/generative, and frequency/time-frequency SR preprints — per the audit's own "immediately before submission" timing. |

**Verification (phase A):** strict chain PASS after these edits (164 cells 0/0, 12/12 families;
manifest verify OK); the LaTeX rebuild lands as phase B with its own scan + regen + push.

## Response — to Audit Runs 2026-07-12 09:40 AND 10:31 (responded together, 2026-07-12)

Both runs' verdicts: no numerical regression; blockers are presentation, ethics/data governance,
and literature/venue hygiene. All confirmed problems from both runs are fixed.

| # | Finding (run) | Resolution |
|---|---|---|
| 1 | Figs 1–3 absent from the PDF (10:31 #1, 09:40-adjacent) | **Embedded**: markdown image syntax added at the three referencing paragraphs (PNG assets); the rendered PDF now carries **3 image XObjects** (render script gains a fail-closed images≥1 gate + width-scaling CSS). The TORS LaTeX twin embeds the PDF vector versions via `\includegraphics` (delta build in flight — landed same day, commit `7a8607b`). |
| 2 | No ethics/privacy/data-use section (10:31 #2) | **New §10 "Ethics and Data Governance"**: public pseudonymized AR2023 under its research terms; scope of data consumed = interaction tuples + item-metadata text only (no review bodies, no images, no re-identification attempts); sidecars carry remapped integer IDs only; raw data not redistributed (hash + regeneration boundary); no new data collection ⇒ IRB not applicable; explicit no-deployment-claim + exposure-bias note. |
| 3 | Table 0 contradicts the parity evidence (09:40 #1 / 10:31 #3) | HSTU-base row corrected to the audit's suggested boundary: **"core-block parity demonstrated bitwise against the reference research implementation (§3.2); no pinned end-to-end system reproduction (§5.6, §6.5)"** — an understatement fix, not a claim expansion. |
| 4 | GrIT uncited (10:31 #4) | Cited with fetched metadata (Shyam, Kagita, Rana, Kumar — "GrIT: Group Informed Transformer for Sequential Recommendation", arXiv:2602.19728): §5.1 notes its matching VG 5-core statistics and published NDCG@10 0.0588, records that our 5-seed 0.0673 ± 0.0003 is numerically higher **as a point-estimate observation with explicit comparability caveats, not a claim**; References entry added to the concurrent-preprints block. Kept out of the audited comparator table (Table 1b) per the fence. |
| 5 | Frequency-filter related work too narrow (09:40 #2) | §2.3 novelty boundary broadened: FEARec (Du et al., SIGIR 2023) cited as representative of the wider frequency/time-frequency SR line, and our contribution restated narrower — left-causal depthwise FIR inside an HSTU-style stack, all-position next-item objective, full-catalog AR2023 5-core LLOO. |
| 6 | Venue-date claim not verifiable (10:31 #5) | `VENUE_PLAN.md` now says RecSys 2027 dates are **TBD**, with the RecSys 2026 call (artifacts required, dual submission prohibited) cited as precedent only — matching the audit's own ACM-policy fact-check. |
| 7 | Stale page counts (09:40 #3) | `CANONICAL_SUBMISSION.md` no longer states a page count (machine-scanned every render); older response sections are historical records, not package metadata. |
| 8 | Table 2 dangling cell at page break (09:40 #4) | `tr{break-inside:avoid}` injected by the render script (idempotent); re-rendered PDF: **40 pages, 3 images, scan CLEAN**. |
| 9 | paper_tex smoke artifacts untriaged (10:31 housekeeping) | Triaged: `_smoke.*` deleted (install probes), `main.pdf` gitignored (intermediate), and the full TORS LaTeX build **committed** — acmart TORS anonymous format, 16 generated table includes (2 straight from strict-build JSON, 10 md-extracted with numeric cross-check against manifest families, 4 md-only), 30-entry bibliography, own hygiene scan PASS. The round-7 deltas (figures/ethics/GrIT/FEARec/Table-0) were applied to the LaTeX twin and committed the same day (`7a8607b` + `9cb7fcb`: 36 pp, 3 vector figures, scan PASS, manifest-gated). |
| 10 | Manifest commit ≠ HEAD (09:40 #3) | Ritual regen at the fix commit; strict wrapper re-verifies (111 files OK). |

**Verification:** SUBMISSION BUILD GREEN (164 cells, 0/0, 12/12 families) → RELEASE MANIFEST
VERIFY OK → MI dual gate PASS → Office VOID/descriptive → **SUBMISSION REBUILD: PASS**, exit 0.
Markdown PDF: 40 pp, 3 embedded images, scan CLEAN.

## Response — to Audit Run 2026-07-12 08:31 (responded 2026-07-12, same day)

Verdict received: prior literature-framing risk confirmed fixed in source and PDF; remaining
top-journal risk is "polish, not result invalidation". Both confirmed problems fixed; the
flagged number re-verified; the scoping question answered.

| # | Finding | Resolution |
|---|---|---|
| 1 | Four 2026 preprint references are bare arXiv IDs | **Upgraded to full bibliographic entries with real metadata fetched from the arXiv listings** (2026-07-12) — never invented: SID-MLP = Guo, Hou, Ju, Shah, McAuley, "MLPs are Efficient Distilled Generative Recommenders"; Latte = Hou, Kim, Ju, Escoto, Shah, McAuley, "Expressiveness Limits of Autoregressive Semantic ID Generation in Generative Recommendation"; ChronoSID = Huang, Gao, Huang, Sheng, Yao, "Beyond Item Order: Temporal Gap Tokenization…"; ReSID = Liang et al. (13 authors), "Rethinking Generative Recommender Tokenizer…". The unreviewed-concurrent-work fence is retained and now states the metadata-verification date. |
| 2 | Working tree intentionally dirty (auditor's regenerated PDF + manifest) | Folded in and superseded: the reference edits forced a fresh render + manifest regen anyway; PDF (38 pp, scan CLEAN), `RELEASE_MANIFEST.json`, and the audit file are **committed together** in one commit, keeping the PDF and manifest boundary consistent as required. |
| R | Latte MI 0.0331 / VG 0.0515 extraction brittle | **Re-verified directly against Latte's Table 1** (row "Latte": 0.0331* Instruments, 0.0515* Games) — the paper's quoted values are correct; the reference entry now notes the verification. |

**Concrete-fix 2 (recent-preprint scoping) — decided:** the paper explicitly scopes its
comparisons to the HSTU-BLaIR protocol family (same-statistics AR2023 5-core LLOO) and discusses
the SID-line filtered universe as non-interchangeable context; other 2026 AR2023 preprints are
covered by the standing unreviewed-concurrent-work fence rather than enumerated. A fresh
freshness triage is committed to as part of the venue-formatting step, once the maintainer picks
the venue (the remaining open question, together with the template).

**Verification:** strict chain re-run — SUBMISSION BUILD GREEN (164 cells, 0/0, 12/12 families)
→ RELEASE MANIFEST VERIFY OK (111 files) → MI dual gate PASS → Office VOID/descriptive →
**SUBMISSION REBUILD: PASS**, exit 0.

## Response — to Audit Run 2026-07-12 07:28 (responded 2026-07-12, same day)

Verdict received: scientific core "conditionally defensible"; literature framing needs revision.
All three confirmed problems fixed, both plausible risks addressed, both open questions answered.

| # | Finding | Resolution |
|---|---|---|
| 1 | Stale "first to report numbers" (§ "What we can claim") | **Deleted and inverted into an explicit no-priority-claim statement**: HSTU-BLaIR predates this work on the protocol, and the concurrent preprints SID-MLP (arXiv:2605.12617) and Latte (arXiv:2605.06331) report AR2023 5-core LLOO numbers on the same MI/VG dataset statistics (both papers). |
| 2 | Appendix A.3 "BLaIR is the only published work using AR2023" | Rewritten as a historical/superseded note pointing at the current AR2023 literature; the Beauty closing line is now a **search statement, explicitly not a priority claim** ("we did not find a comparable published number… preprints appearing rapidly"). |
| 3 | References incomplete for named prior art | **Ten entries added**: full citations for TiSASRec (Li et al. 2020, WSDM), VQ-Rec (Hou et al. 2023, WWW), ProtoMF (Melchiorre et al. 2022, RecSys), MELT (Kim et al. 2023, SIGIR), DropoutNet (Volkovs et al. 2017, NeurIPS), CLCRec (Wei et al. 2021, ACM MM); the four 2026 preprints (ReSID, ChronoSID, SID-MLP, Latte) are cited **by arXiv identifier under an explicit unreviewed-concurrent-work note** — no invented authors or titles. |
| R1 | "five-run averages" for ChronoSID unsupported | Phrase **deleted** (the source table reports paired-bootstrap CIs per the audit's fact-check; we now cite the output-level table without characterizing its aggregation). |
| R2 | "A faithful HSTU implementation" ambiguous | Rephrased to the precise boundary: what is not provided is a *faithful pinned-environment end-to-end HSTU-BLaIR reproduction*; the core block is bitwise-exact (§3.2) and the research path runs locally as environment-caveated single-run regenerations (§5.6). |
| R3 | PDF not visually re-checked in the audit run | Re-rendered after all edits: **38 pages, placeholder/lab-language scan CLEAN**. |

**Concrete-fix 4 (related-work expansion):** the §5.1 2026-line paragraph now carries the audit's exact three-way separation — (i) same-statistics AR2023 5-core LLOO concurrent preprints (SID-MLP, Latte — cited for completeness, **no comparative claim** made against unreviewed work), (ii) the ReSID/ChronoSID filtered universe (not protocol-interchangeable), (iii) older Amazon-2014 TIGER/LIGER. The comparator choice is unchanged: published HSTU-BLaIR 0.0406 remains the strongest known same-protocol MI reference, which the pre-registered confirmation exceeds as a point-estimate comparison.

**Open questions answered:** (a) the Beauty "first such reported number" claim is **withdrawn** in favor of the search statement — it was defensible only under an exact-universe reading, and priority language contradicts our narrowing-only discipline; (b) 2026 arXiv-only work is cited in place but explicitly fenced as *unreviewed concurrent preprints* (in the §5.1 paragraph and in a labeled References block) — completeness without over-weighting.

**Verification:** strict chain re-run after the edits — SUBMISSION BUILD GREEN (164 cells, 0/0, 12/12 families) → RELEASE MANIFEST VERIFY OK (111 files) → MI dual gate PASS → Office VOID/descriptive → **SUBMISSION REBUILD: PASS**, exit 0.

## Response — to Audit Run 2026-07-12 04:28 (responded 2026-07-12, same day)

Verdict received: narrow scientific core "still conditionally acceptable"; artifact package
"minor revision" — documentation/manifest hygiene only, no result findings. All three confirmed
problems fixed; both open questions answered below.

### Confirmed problems

| # | Finding | Resolution |
|---|---|---|
| 1 | Stale "163 cells" prose in `CANONICAL_SUBMISSION.md` and the round-3 response | Fixed maintenance-free: `CANONICAL_SUBMISSION.md` now states the gate's **invariants** (0 mismatch / 0 untraceable / 12 required families) and defers the exact cell count to the strict build's own output ("164 at this writing, grows as evidence lands") — so the canonical file cannot go stale again when cells are added. The three historical responses (round 3, round 2, full-method) carry a one-time annotation marking their counts as point-in-time. |
| 2 | New Office HSTU-BLaIR run artifacts not in `RELEASE_MANIFEST.json` scope | Fixed with the hash option, generalized: the manifest gains a **`reference_runs` section hashing the artifacts of all three local reference-implementation runs** (metrics.jsonl, run_meta.json, gin copy, intended-TB pointer, trainer log — 15 files), and `update_release_manifest.py --verify` treats them as git-tracked (missing or drifted ⇒ gate failure). Strict wrapper re-run: **RELEASE MANIFEST VERIFY: OK (111 files verified)**. |
| 3 | Untracked render scratch could be swept into a release | `/_paper_render.html` and `/tmp/` explicitly gitignored with a "never release-swept" comment; the deposit bundle is assembled from an explicit file list (`make_deposit` inventory), never from a directory sweep. |

### Open questions — answered

- **Should `RELEASE_MANIFEST.json` include all local reference-run artifacts, or is git
  tracking + `hstu_results_manifest.json` the provenance layer?** Both, with an explicit
  boundary now written into the manifest: the *source* run artifacts are hash-manifested
  (`reference_runs`), while the two *generated* JSONs (`hstu_results_manifest.json`,
  `hstu_tables.json`) are deliberately outside the hash scope — a new
  `generated_artifacts_note` field explains why: they are git-tracked build outputs whose
  integrity check **is** the fail-closed gate itself, and the strict wrapper rewrites
  `hstu_tables.json` during the same run that verifies hashes, so hash-pinning them would make
  verification circular.
- **Will the next deposited release include the Office HSTU-BLaIR artifacts?** Yes — they are
  repository-tracked and now release-manifest-hashed; they ride into the next deposit bundle
  cut (e.g., at DOI minting time). The existing `v1.0-deposit` bundle predates the run and says
  so via its manifest boundary.
- **Target venue/template?** Maintainer decision, still pending; acknowledged as the final
  pre-submission step (risk 5).

### Standing risks (3–5) — discipline confirmed

- **"Regenerates" vs "reproduces" (risk 3):** wording frozen as "environment-caveated
  single-run regenerations" in both papers, `CANONICAL_SUBMISSION.md` (with an explicit
  non-strengthening rule), and every relevant manifest cell note. The §5.6 caveat paragraph
  keeps the three-way distinction (published point / unpinned local regeneration / faithful
  pinned reproduction — the last one never claimed) and will not be shortened.
- **No broad SOTA, no paired superiority (risk 4):** unchanged and enforced by the standing
  forbidden-wordings list; the claim set may only narrow.
- **Venue formatting (risk 5):** deferred to venue choice; table values will remain generated
  from JSON.

### Verification after fixes

`rebuild_hstu_submission.py --strict` → parity OK → **SUBMISSION BUILD GREEN (164 cells, 0
mismatch, 0 untraceable, 12/12 families)** → **RELEASE MANIFEST VERIFY: OK (111 files)** → MI
dual gate PASS → Office VOID/descriptive → **SUBMISSION REBUILD: PASS**, exit 0. Papers
untouched this round (no re-render needed; PDF still 37 pp, scan clean).
