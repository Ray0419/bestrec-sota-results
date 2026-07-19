# Response to PAPER_REVIEW_AUDIT (cumulative)

This response file is cumulative, mirroring `PAPER_REVIEW_AUDIT.md`: each audit run gets a
timestamped response section below. The newest section always addresses the audit's newest
"Audit Run" section and its updated risk list.

> **Historical log.** Each section records the state at its own timestamp; page counts,
> cell counts, and "in flight" phrases in older sections are point-in-time statements that
> later sections supersede. This file is an audit-trail document, **not** submission-package
> metadata (`CANONICAL_SUBMISSION.md` governs), and is not included in deposit bundles.

## Response — to Audit Run 2026-07-19 13:47 (round 1: the fail-open counted gate; retractions sequenced next)

**Verdict acknowledged.** This audit lands two findings of the highest class: a counted gate
that could never fail (CP-2) and a scientific analysis whose printed interpretation is not
what the code computes (CP-1). Round 1 executes CP-2 completely; the retraction rounds are
declared below with their exact targets, because rushing surgery on load-bearing scientific
prose in one tick is how new errors get made.

### Executed this round

| # | Audit item | Action |
|---|---|---|
| CP-2 | Counted MI gate fail-open (`return 0` unconditionally; wrapper checks exit code only) | **Fixed both layers:** the adjudicator returns 2 whenever `overall_pass` is false, and the strict wrapper now requires **exit 0 AND the exact `DUAL GATE VERDICT: PASS` token** — the same pattern the Office V3 / FIR-breadth gates already use. Verified live: the strict chain prints "MI V2 gate adjudication (counted; must PASS): OK" and passes end-to-end with true exit 0. The audit's fuller failure-branch test battery joins the fault-corpus work item. |

### Declared next rounds (in order; targets quoted so nothing can be silently dropped)

1. **CP-1 retraction (next tick):** withdraw from both papers + TeX: the "spectrally
   irreducible / no representation-side lever can rescue the tail" conclusions (line ~422
   region), the BBP/MP figure (`make_fig_bbp_irreducibility`), and Table 1e's `d_eff=23`
   normalization (no artifact reports 23; the 24 was enforced by the GD1 intervention, not
   measured) — replaced by a dated retraction note in the retirement pattern; the gated
   Table-1e cells retire via `build_hstu_tables` + `--write-manifest`, and the narrowed
   universal's cell count becomes count-agnostic (build-output-authoritative).
2. **CP-5 (same round):** remove "double dissociation" (7 occurrences), "connectivity
   alone," and "closes the mechanism" — the supported statement is a conditional pattern
   under two bundled thinning interventions with fixed user-removal draws.
3. **CP-6 (same round):** six rungs not seven (and the ×7 multiplicity line), the false
   "climbs monotonically"/"monotone on both metrics" claims, the TAPE-vs-negative-map
   contradiction, and the paired-seed convention breach note.
4. **CP-7 + 12:57 CP-5 (citations round):** C3SASR, HyenaRec, TASTE, AlterRec + the
   methodological set (Jannach & Chen, Pineau, Nosek, TOP, badging, PROV, Beaulieu-Jones);
   "rare/cold" → warm-item long-tail terminology; md-vs-TeX bibliography sync (Nieuwenhuis,
   Tilman cited properly).
5. **CP-3/CP-4 + 12:57 items:** public-asset truth-up with fail-not-skip; Table A1
   coverage-or-retirement (incl. the 22-vs-20 row-count contradiction) and the datasets
   table; then TORS mode (`manuscript,screen`, single-blind) + acmart; governance v1.1.10.

### Flagged to the maintainer (unchanged from 12:57, now with 13:47 additions)

Front-end rewrite; apparatus fault-corpus evaluation or demotion; tuned modern baselines or
sharper narrowing; independent prereg timestamps; **plus 13:47's:** whether a corrected,
prospectively-specified embedding-spectrum analysis is worth running at all, and a matched
causal-convolution baseline for the FIR novelty test.

## Response — to Audit Run 2026-07-19 12:57 (round 1 of a sequenced execution; responded 2026-07-19)

**This is the deepest audit of the campaign — a full top-journal review simulation with 11
confirmed problems and an 11-item fix order — and its two central findings are both real.**
One tick cannot honestly execute all of it; this response executes the correctness/honesty
core now and commits a sequenced schedule for the rest, with the authorial-scope items
flagged to the maintainer.

### Executed this round

| # | Audit item | Action |
|---|---|---|
| CP-2 | `MI_rebuild` manifest entries aliased to the wrong files (false PASS via basename any-match) | **Fixed at the class level:** every result-family entry is re-keyed to its **exact repo-relative path** with the digest of that path; `--verify`, `--verify-git`, and regen resolve `/`-qualified keys exactly and **reject ambiguous non-qualified basenames**. The migration confirmed the audit precisely: **10 wrong digests in MI_rebuild, 0 in every other family** — all corrected to the true `rebuild_v2/` hashes. Verify + verify-git pass 128/128 at the new HEAD. |
| CP-1 (step 1) | "Every empirical table cell" is a false universal (Table A1, dataset table at `checked: 0`) | **The audit's own first instruction executed — stop claiming until true:** all six universals in both papers are narrowed to the accurate statement ("every cell of the artifact-gated result tables — 168 cells across 14 families; two expository tables, §4.1 datasets and Appendix A.1, are converted from the canonical markdown outside this graph and labeled as such"). Full coverage-or-retirement is scheduled (below), and "every" does not return until it is true. |
| SILLM4Rec | The auditor's full-text inspection **settles it** | **Upgraded from "pending" to a confirmed protocol distinction** in both papers + TeX: 500 sampled test users, 20-item history cap, 1-positive-vs-9-random-negatives (§4.1.3–4.1.4), so its VG NDCG@10 0.6073 is a ten-candidate sampled-ranking number — not comparable to any full-catalog value here. Thanks are due: this closes a freeze item the responder could not (403s on both sides). |
| Prereg timing | Private repo, unsigned commits → "immutable" overstates | **Narrowed everywhere:** "immutable pre-registration" → "version-controlled pre-declared protocol," with the no-independent-external-timestamp limitation stated at first use in the abstract. This is a strict claim-narrowing; external timestamping (OSF/Zenodo/signed tags) for any future confirmation is flagged to the maintainer alongside the deferred DOI decision. |
| CP-11 (wording) | V1 heading readable as contradicting V3; "10 fresh seeds" imprecise | §5.2's attempt heading is now "**Office_Products V1** … superseded by the counted V3 campaign below"; seed phrasing is "five pre-specified never-inspected seeds per kernel; ten arm-runs" at both sites. Reader-PDF orphan page stays a recorded freeze cosmetic. |

Both PDFs rebuilt (46 pp scan CLEAN; 40 pp hygiene PASS); compiled-text checks confirm the old
phrases gone and new ones present; strict gate true-exit 0; manifest regenerated.

### Sequenced next (loop-executable, next ticks in order)

1. **CP-1 completion:** wire `table_datasets41` into the artifact graph (counts recomputable
   from tracked split/provenance artifacts); evaluate Table A1's per-run artifacts — if not
   retained to gate standard, **retire the table** per the audit's rule (precedent: the
   v1-era rows); then make empirical `checked: 0` a build failure and add the
   altered-value regression test.
2. **CP-9:** apply the verified TORS mode (`[manuscript,screen]`, no line numbers,
   single-blind) + correct `VENUE_PLAN`'s double-anonymous error; acmart refresh via an
   official distribution; full rebuild + hygiene + page inspection.
3. **CP-3:** make the v0.9 release-asset story truthful (upload the 1.09 GB split/cache
   assets or re-describe as regenerable-local with fail-not-skip semantics).
4. **CP-10:** builder into `submission_docs`; "51 result JSONs" inventory corrected (81 + 10
   tree-state); one date convention; REBUILD-mode fail when a tagged version's content
   would differ; then a coherent v1.1.10 cut.
5. **CP-5 (citations):** add the named methodological literature (Jannach & Chen TORS 2026,
   Pineau et al., Nosek et al., TOP, ACM badging, PROV, Beaulieu-Jones & Greene) with the
   narrowed integration-claim sentence.
6. **CP-7 (labels/stats):** split evidence classes (preregistered-confirmatory vs multi-seed
   exploratory vs single-seed vs external constant) in the manifest and prose; paired-delta
   reporting for same-seed arms.

### Flagged to the maintainer (authorial scope — not loop-executable)

- **CP-6:** front-end rewrite (200–300-word abstract, ≤3 contributions, RQ/title alignment,
  moving negative probes to supplementary) — this is a voice-and-structure decision.
- **CP-4:** apparatus fault-corpus evaluation + independent rerun, or demotion to
  "case-study workflow" — a research task changing the paper's positioning.
- **CP-8:** tuned multi-seed modern baselines under the identical protocol (GPU campaigns),
  or the sharper methodology-case-study narrowing.
- Independent prereg timestamping going forward (OSF/signed tags).

## Response — to Audit Run 2026-07-19 09:34 (responded 2026-07-19, same tick)

**Verdict acknowledged.** The 08:32 blocker is confirmed closed by the auditor's own checks
(v1.1.9 verified, linter present, v1.1.8 marked not-final-DOI); the three residual items are
small DOI-facing metadata drift, each now fixed **with a structural fence** so the class dies:

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1 | "65 entries" vs the zip's 66 | **Corrected to 66** (README_DEPOSIT + SHA256SUMS + 64 payloads), and the **consistency gate now verifies** the documented count equals `len(FILES) + 2` — a future inventory change with a stale count refuses to build. |
| CP-2 | DATE="2026-07-18" vs the 2026-07-19 release | **Single-sourced:** the builder no longer hardcodes a date; the bundle README's date is derived from the manifest's regen date with the basis printed explicitly ("local, Australia/Sydney"). The v1.1.9 discrepancy was exactly the hazard named (a hardcoded date crossing a local-midnight boundary); it cannot recur. |
| CP-3 | Untracked raw-data/byproducts unignored | **`.gitignore` extended:** `data_raw_proper/` (raw AR2023 downloads are never redistributed), `_bestrec_run/*.DONE`, `_bestrec_run/smoke_*.json` — a broad manual `git add`/packaging sweep can no longer pick them up. |
| PR (cover letter) | Artifact sentence readable as "zip contains the live chain" | **Rewritten to make the attribution unambiguous:** the *repository* carries the full adversarial audit chain in every tagged tree; the *bundle* contains core historical audit documents, live chain repository-tracked rather than re-bundled. |
| PR (TORS policy 403) | Venue line-number/anonymity policy unverifiable via fetch | Noted for the freeze checklist — the audit's own conclusion (verify in the submission portal at upload) is already the recorded plan in `VENUE_PLAN.md` item 5. |
| PR (SILLM4Rec) | Institutional access before freeze | Standing, recorded with the dated 403 attempts. |

No new cut: the corrected count/date/wording live in source and the builder template; the
published v1.1.9 bundle remains accurate for its own state except the internal "65 entries"
echo and the one-day date basis — both called out here for the record and both fixed in the
template the next cut will print. Strict gate true-exit 0 at the new HEAD; manifest
regenerated (builder is manifested) and refreshed on v0.9.

## Response — to Audit Run 2026-07-19 08:32 (responded 2026-07-19, same tick)

**Verdict acknowledged.** The empirical gates are green; the artifact-readiness finding is
right: the published v1.1.8 zip's internal README predated both the audit-chain wording
precision and the counted-adjudicator chain description, and the builder template would have
repeated it. Fixed at the template, fenced with a content linter, and archived in a fresh
verified cut — per the audit's own recommendation not to use v1.1.8 as the DOI artifact.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-3 / Fix-1 | Builder README template under-describes the gate | **Template's verification-chain text now states the full eight-step chain in the audit's exact order** (parity → strict table build → manifest verification → MI V2 → COUNTED Office V3 must-PASS → COUNTED FIR-breadth both-CONFIRMED → Office V1 descriptive/VOID). |
| Fix-2 | Bundle-content linter | **Installed in the consistency gate:** the build refuses if the README template omits the counted gate steps, lacks the core-historical-audit-documents wording, or uses bare "audit chain" phrasing outside a historical scope — CP-1/CP-2's recurrence is now structurally impossible. Bonus proof it works: mid-round the gate refused my own partially-patched state (intended-tag v1.1.9 vs VERSION v1.1.8) exactly as designed. |
| CP-1/CP-2 | Published v1.1.8 zip carries the stale internal wording | **[`v1.1.9-deposit`](https://github.com/Ray0419/bestrec-sota-results/releases/tag/v1.1.9-deposit) cut** under the full topology recipe; **v1.1.8 marked superseded with an explicit "do not use as the final DOI artifact" note** (the audit's alternative for the published tag). Round-trip verifies the bundled README **content**: counted-chain present, historical-audit wording present, zero bare "audit chain" occurrences. |
| CP-4 | HEAD drift understated (support-doc/builder changes past the tag) | Closed by the cut: tag == release commit == the state carrying all wording/builder fixes; post-tag drift is again response-only. |
| CP-5/CP-6 | SILLM4Rec full text; acmart/cover-letter/line-numbers | Freeze-gated as recorded (403 attempts documented in `VENUE_PLAN.md` last tick; institutional route at freeze). |

### Round-trip at `v1.1.9-deposit`

Assets hash-match local; tag blob == manifest asset == bundled manifest; `--verify-git
v1.1.9-deposit` OK 128/128; bundled README passes all three content checks; inner
`SHA256SUMS.txt` 0 mismatches; **post-tag rebuild byte-identical**; tag == release commit.
**FULL ROUND-TRIP: PASS.** Strict gate true-exit 0 before the cut.

## Response — to Audit Run 2026-07-19 06:27 (responded 2026-07-19, same tick)

**Verdict acknowledged.** Gates green at HEAD on the auditor's re-runs; the executable finding
was the deposit-scoped "audit chain" wording promising more than the v1.1.8 bundle carries.
Fixed via the audit's **option (b)** — precise wording — with the rationale below; the
SILLM4Rec access attempts are now on the record.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1 | Deposit "audit chain" wording broader than the bundle | **Option (b) chosen and executed:** the DOI bundle row, the bundle README template, and the cover letter now say the bundle carries **core historical audit documents**, while the **live hourly adversarial pair** (`PAPER_REVIEW_AUDIT.md` / `RESPONSE_TO_PAPER_REVIEW_AUDIT.md`) is *deliberately* not re-bundled per cut — it is git-tracked and present **in full in every tagged tree**, so a reviewer at any deposit tag has the complete chain in the repository itself. Rationale for (b) over (a): the response file's own long-standing banner declares it audit-trail documentation excluded from deposit bundles, and re-bundling a live, hourly-growing log would create a perpetually-stale snapshot inside each cut — the exact staleness class this audit series keeps catching. The cover letter's "review package includes the complete adversarial audit trail" is corrected to "the **repository** includes…". README's own lines were already accurate (its intro and table row describe the repository, which does hold the full chain). |
| CP-2 | SILLM4Rec full text not inspected (ACM 403 to the auditor too) | **The audit's fallback executed:** `VENUE_PLAN.md`'s freeze item now records the dated access attempts (auditor's direct ACM fetch → 403 on 2026-07-19; responder-side non-interactive access unavailable) and names the institutional route as the remaining path. The manuscript's wording is unchanged — this audit itself confirms it is "appropriately caveated" and the problem is the missing inspection, not overstatement. |
| CP-3 | acmart v2.03 vs v2.19 | Freeze-gated (`VENUE_PLAN.md` item 5, portal-vs-CTAN decision + rebuild + hygiene). |
| CP-4 | Cover-letter brackets | Maintainer-only at freeze, by design. |
| CP-5 | Review-line-number policy | Part of the same freeze item: the `review` option is correct for a review manuscript; whether to disable at upload is checked against the venue's instructions at freeze. |

No new deposit cut: the changes are wording-precision in support docs plus the builder's README
template (all picked up at the next cut); the v1.1.8 bundle remains claim-accurate, and
`--verify-git v1.1.8-deposit` continues to pass for the tag's own state. Strict gate true-exit
0 at the new HEAD; manifest regenerated (builder + docs are manifested) and refreshed on v0.9.

## Response — to Audit Run 2026-07-19 04:31 (responded 2026-07-19, same tick)

**Verdict acknowledged — and this run's own top risk list already records the resolution.**
The Confirmed Problems section reflects the pre-cut state its checks began from; the same
run's refreshed risk list (items 6–7) then verifies the `v1.1.8-deposit` cut end-to-end
("HEAD is tagged v1.1.8-deposit; --verify-git passes; local zip matches its sidecar and the
GitHub asset digest") — that cut and the DOI safety wording landed in the previous tick's
response to the 03:30 run, mid-flight of this audit.

### Point-by-point

| # | Audit item | Status |
|---|---|---|
| CP-1 (`--verify-git v1.1.7-deposit` mismatch) | **Closed by the v1.1.8 cut** — the current literal reviewer target is `v1.1.8-deposit` (`intended_deposit_tag` in the manifest), and this run's own item 7 verifies it. Current HEAD sits one response-only commit past the tag, exactly the acceptable branch-vs-tag state item 7 describes. |
| CP-2 (dangerous `_release/` local-upload path) | **Closed last tick:** Option B now names the v1.1.8 asset and states the safety rule — a local `_release/` copy is usable ONLY if its SHA256 matches the release sidecar for the named tag; otherwise use the downloaded asset. Verified present in the current file; no v1.1.7-from-`_release` instruction remains. |
| CP-3 (no tag archives the builder/doc state) | **Closed by [`v1.1.8-deposit`](https://github.com/Ray0419/bestrec-sota-results/releases/tag/v1.1.8-deposit)** — archives the two-mode builder boundary, deterministic container (byte-identical rebuild proven in the 03:30 round trip), and the CANONICAL chain sync. |
| CP-4 (acmart v2.03 vs v2.19; line numbers) | Freeze-gated (`VENUE_PLAN.md` item 5: portal-vs-CTAN decision + rebuild + hygiene at freeze; line numbers are the `review` option and an explicit upload-time decision). |
| CP-5 (cover-letter brackets) | Maintainer-only at freeze, by design (tracked draft `COVER_LETTER_TORS.md`). |
| CP-6 (SILLM4Rec full text) | Freeze-gated; the paper's exclusion is already explicitly repo-evidence-based and inspection-pending, which is the fallback this audit itself endorses. |

No repository changes were needed this tick beyond this response: the two executable fixes
were already in place and are verified by this very audit's refreshed risk list; the
remaining items are maintainer-gated freeze work, tracked in `VENUE_PLAN.md`.

## Response — to Audit Run 2026-07-19 03:30 (rechecked 04:25; responded 2026-07-19, same tick)

**Verdict acknowledged, and the riding decision is reversed as the audit directed.** Last
response chose to ride the builder/doc fixes until the next cut; this audit correctly ruled
that the branch was no longer deposit-clean (`--verify-git v1.1.7-deposit` failing on the
post-tag `CANONICAL_SUBMISSION.md`) and prescribed the v1.1.8 recipe. Executed verbatim —
and the new cut carries the first **byte-identical rebuild proof**.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1/CP-3 / Fix-1 | Branch not deposit-clean; no tag archives the fixes | **[`v1.1.8-deposit`](https://github.com/Ray0419/bestrec-sota-results/releases/tag/v1.1.8-deposit) cut by the audit's recipe**: regen `--deposit-tag v1.1.8-deposit` → gated build (CUT mode) → one commit → tag at that commit → assets uploaded → `--verify-git v1.1.8-deposit` **OK 128/128**. Archives the builder two-mode boundary, deterministic container, and CANONICAL chain sync. v1.1.7 marked superseded. |
| Fix-2 | Bump VERSION before building (sidecar collision) | Done exactly — v1.1.8 was bumped first, so the published v1.1.7 sidecar was never overwritten locally; v1.1.7's release notes now also warn that post-tag local rebuilds of that bundle differ from its sidecar. |
| CP-2 / Fix-3 | `_release/` local-copy hazard in DOI instructions | **Safety rule installed:** a local `_release/` copy is usable ONLY if its SHA256 matches the release sidecar for the named tag; otherwise use the downloaded asset. |
| Determinism | (from the 00:35 upgrade) | **First byte-identical rebuild proof executed in the round trip:** after tagging, the builder ran in REBUILD mode and reproduced the released zip **byte-for-byte** (digest `95a85d3e80af4937…`) — the reproducibility semantics promised last round are now demonstrated, not just claimed. |
| CP-4–7 / Fix-4–6 | acmart v2.03, red line numbers, SILLM4Rec full text, cover-letter brackets, reader-PDF last page | Freeze-gated as recorded (`VENUE_PLAN.md` checklist; reader-page accepted-cosmetic decision stands; the paper's SILLM4Rec exclusion is already explicitly repo-evidence-based and inspection-pending). |

### Round-trip at `v1.1.8-deposit` (full battery + the new proof)

Assets hash-match local; tag blob == manifest asset == bundled manifest; `--verify-git
v1.1.8-deposit` OK 128/128; bundled `intended_deposit_tag: v1.1.8-deposit`; inner
`SHA256SUMS.txt` 0 mismatches; tag == release commit == HEAD at cut; **post-tag rebuild in
REBUILD mode byte-identical to the released asset**. **FULL ROUND-TRIP: PASS.** Strict gate
true-exit 0 (all eight steps incl. both counted adjudicators) before the cut.

## Response — to Audit Run 2026-07-19 00:35 (responded 2026-07-19, same tick)

**Verdict acknowledged.** v1.1.7 verified end-to-end on the auditor's own checks; the two
executable problems were tooling/doc lag behind the new manifest semantics. Both fixed, with
the reviewer's rebuild path now proven to work.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1 | Builder false-fails at the released tag (still demanded `git_commit == HEAD`; even `--help` ran the gate) | **Gate now implements the documented two-mode invariant** ("the manifest describes THIS tree"): **CUT mode** — `git_commit == HEAD` after a fresh regen — or **REBUILD mode** — `--verify-git HEAD` passes at the tag/descendant. Both modes proven live this tick: check-only printed CUT mode pre-commit and REBUILD mode post-commit. **argparse added**: `--help` prints usage without running anything; `--check-only` runs the gate without building. |
| Fix-2 / open question 2 | Reproducibility semantics | **Answered and upgraded:** the zip container now uses fixed `ZipInfo` metadata, so rebuilds are **byte-identical from the next cut (v1.1.8) onward**; for v1.1.7 and earlier, reproducibility = verified payload equivalence (payload bytes + `SHA256SUMS.txt` identical; container timestamps differ), stated here for the record. The released v1.1.7 assets are untouched. |
| CP-2 / Fix-3 | `CANONICAL_SUBMISSION.md` chain prose stale | **Synced to the live gate:** parity → strict table build → release-manifest verification → MI V2 → **counted Office V3 (must PASS)** → **counted FIR-breadth (both CONFIRMED)** → descriptive Office V1 — plus the `--verify-git <intended_deposit_tag>` pointer. |
| Fix-4 | Hash rule adjacent to the verify command | **Added to README's verification section**: digests verify against the tag blob / release asset / bundle payload, never raw Windows worktree bytes (with the DOI-instructions cross-reference). |
| CP-3–6 / Fix-5 | acmart/line numbers, SILLM4Rec, cover letter, reader-PDF last page | Freeze-gated as recorded (reader-PDF page: accepted-cosmetic decision stands from the 23:28 response). |
| Open question 1 | Repair in v1.1.8 now, or ride? | **Ride until the next cut**, per the boundary policy the audit's own risk #3 endorses for response-class commits — with the honest caveat that this round also touched two manifested docs (`CANONICAL_SUBMISSION.md`, builder), so the v1.1.7 bundle now trails HEAD on those; the claims are untouched, `--verify-git v1.1.7-deposit` still passes for the tag's own state, and the next cut (v1.1.8, first byte-identical container) archives everything. If the auditor prefers an immediate v1.1.8, next tick executes it. |

**Ritual:** builder + docs patches → `--regen --deposit-tag v1.1.7-deposit` → `--check-only`
CUT-mode OK → one commit → `--check-only` REBUILD-mode OK (the reviewer's path, previously the
false-failure) → strict true-exit 0 (all eight steps) → this response → push → v0.9 manifest
refreshed (LF).

## Response — to Audit Run 2026-07-18 23:28 (responded 2026-07-19, next tick)

**Verdict acknowledged.** The live support chain was confirmed fixed by the auditor's own
re-runs (V3 PASS, strict gates both counted campaigns); the top blocker was that the public
deposit predated those fixes — and the builder itself was already refusing to build at HEAD,
which is the consistency gate working as designed. Both confirmed problems executed; the
deposit is re-cut; the field-semantics question is answered with a literal in-manifest target.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1/CP-2 | Fixed state not deposited; builder blocks at HEAD | **[`v1.1.7-deposit`](https://github.com/Ray0419/bestrec-sota-results/releases/tag/v1.1.7-deposit) cut by the full recipe the audit prescribed:** regen (now with `--deposit-tag`) → gated build (the block the audit saw cleared exactly as designed once the manifest was regenerated at the intended state) → one commit → tag at that commit → verifications. The bundle archives the E3 comparator fix and the counted-adjudicator strict gate (round-trip confirms the bundled `rebuild_hstu_submission.py` carries the V3/FIR-breadth gating steps). v1.1.6 marked superseded with the reason. |
| CP-3 / Fix-2 | `git_commit` still reviewer-fragile | **Implemented the audit's suggested pair:** `--regen --deposit-tag <tag>` stamps **`intended_deposit_tag`** — the literal, runnable reviewer target (`--verify-git v1.1.7-deposit`) — alongside `hash_parent_commit` (alias of `git_commit`) and updated `git_commit_semantics`; the `--verify-git` failure hint now names the tag literally. The deposit builder's gate refuses to build unless `intended_deposit_tag` matches its VERSION, so the field can never point at a stale tag. |
| CP-4 / Fix-3 | acmart v2.03 + red line numbers | Freeze-gated (recorded in `VENUE_PLAN.md`); the line numbers are the acmart `review` option working as intended for a review manuscript — whether to disable at upload is part of the freeze template decision. |
| CP-5 / Fix-4 | SILLM4Rec full text | Pending at freeze; the manuscript's exclusion is already explicitly repo-evidence-based and inspection-pending. |
| CP-6 / Fix-5 | Cover-letter brackets | Maintainer-only, at freeze, by design. |
| Fix-6 | Reader PDF's nearly blank last page | **Decision recorded: accepted cosmetic.** `paper_tex/PAPER_TORS.pdf` is the submission artifact; the reader edition is the canonical-markdown rendering whose trailing page carries no content obligations. Not worth render-pipeline churn before freeze. |
| Open question | Cut the deposit now? | Yes — done this tick (above), per the audit's own recipe. |

### Round-trip at `v1.1.7-deposit` (full battery)

Assets hash-match local; **tag blob == manifest asset == bundled manifest** (digest
`3e9ff7dbbb22dfac…`); **`--verify-git v1.1.7-deposit`: OK 128/128**; bundled manifest carries
`intended_deposit_tag: v1.1.7-deposit`; **the bundled strict gate contains the
counted-adjudicator steps** (the exact protection v1.1.6 lacked); inner `SHA256SUMS.txt` 0
mismatches; bundled CITATION/zenodo say 1.1.7; tag == release commit == HEAD at cut. **FULL
ROUND-TRIP: PASS.** Strict gate before the cut: true exit 0, all eight steps OK.

## Response — to Audit Run 2026-07-18 21:30 (responded 2026-07-18, same tick)

**Verdict acknowledged — this was the most important catch of the campaign.** My LF-hashing
migration (previous round) left the Office V3 adjudicator's condition-2 comparator on raw
bytes, so the live adjudicator spuriously VOIDed the counted campaign against the migrated
manifest — and the strict gate didn't notice because it never ran the V3 adjudicator. A
fail-closed apparatus whose counted claim can silently lose its live adjudicator is exactly
what this project must not be. All confirmed problems executed; both open questions answered
with the stricter option.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1/CP-2 | V3 adjudicator VOIDs on hash-policy mismatch | **Comparator aligned to the manifest policy** (LF-normalized text, binary raw). **Prereg question answered via ERRATUM E3** (appended to `PREREG_OFFICE_V3.md`): condition 2's "hash-manifested" protects reference-artifact **content identity**; the migration proved content identity under the legacy rule before rewriting, and the comparator now tests exactly what was frozen, byte-encoding-independently. The spurious-VOID window is disclosed symmetrically in E3 and in `OFFICE_V3_RESULTS.md`. **Decisive evidence:** re-adjudication under the updated comparator reproduced the original PASS block `196799e7c46d` **bit-identically** (the script's dedup declined to append a duplicate) — no verdict content changed at all. |
| CP-3 | Strict gate doesn't protect the counted V3 claim | **Both counted live adjudicators now gate `--strict`** with verdict *parsing* (discovered en route: both adjudicators exit 0 even on VOID, so exit codes alone cannot gate): Office V3 must print `CAMPAIGN VERDICT: PASS`, FIR-breadth must print `CONFIRMED` for both categories; otherwise the build fails. Verified live: the gate chain now shows both steps OK and the full rebuild PASSES with true exit 0. Answered open question 2: yes — all counted campaigns' adjudicators now gate. |
| CP-4 | `git_commit` semantically risky | **`git_commit_semantics` field added** to the manifest (parent-commit convention stated where reviewers look: verify at the introducing commit, any unchanged descendant, or the deposit tag — not at the parent itself when manifested files changed), and `--verify-git` prints that hint when run against the recorded parent. Answered open question 3 with this documented-semantics route: a literal introducing-commit field is unknowable at regen time (the manifest cannot know its own commit), so the deposit tag — always a verifying commit, always in the release — is the reviewer-facing literal target, per `DOI_DEPOSIT_INSTRUCTIONS.md`. |
| CP-5 | acmart refresh pending | Freeze-gated, unchanged (`VENUE_PLAN.md` records portal-v2.16 vs CTAN-v2.19; the review PDF's line numbers are the `review` option working as intended for the manuscript format). |
| Risk 5 | Sidecar language precision | Unchanged and already precise (§8 + bundle README boundary relations). |

### Process disclosures (same standard applied to myself)

- The spurious VOID was **my own migration's collateral** — the audit caught it within hours.
- My tick reports' `STRICT=$?` lines have been measuring the exit code of `tail` (the last
  command in a pipe), not the strict script — the script's own exit propagation was always
  correct (`return 0 if ok else 2` → `sys.exit`), and every strict run was verified by its
  printed PASS line, but the echoed number was meaningless. This round's run captures the true
  exit code without a pipe: **STRICT_EXIT=0** with all eight steps OK, including the two new
  adjudicator gates. Future runs use the unpiped form.

**Ritual:** comparator + gate + manifest patches → E3 + results note → re-adjudication
(bit-identical PASS block) → `--regen` → one commit → strict exit 0 (true capture; 168 cells,
0/0, 14/14 families, 153 files, V3 PASS gate, FIRB CONFIRMED gate) → `--verify-git HEAD` OK
128/128 → this response → push → v0.9 manifest refreshed (LF). Deposit boundary remains
`v1.1.6-deposit`; the next cut archives these gate hardenings.

## Response — to Audit Run 2026-07-18 20:20 (the risk-list refresh with 20:24 check timestamps; manifest hashing was checkout-dependent)

**This was the deepest finding of the campaign, and the audit is fully right.** The manifest's
digests were raw worktree bytes — CRLF on this checkout — so they matched neither the git
blobs at the manifest's own recorded commit (25 mismatches) nor the LF-normalized deposit
payloads (15 mismatches), and `--verify` couldn't see it because it re-hashed the same
worktree. A Linux clone would have failed the strict gate outright. Fixed systemically, with
the auditor's own checks now running in-repo and passing at the new tag.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1 | Manifest inconsistent with its recorded commit's blobs and with the bundle payloads | **Hashing made platform-independent:** git-backed sections (`protocol_code`, `submission_docs`, `result_families`, `reference_runs`) now digest **LF-normalized bytes** for text files — equal to the git-blob hashes and the bundle-payload hashes *by construction*. Release-asset sections (`splits`, `text_caches`, `pinned_parity_artifacts`) keep raw-byte hashing because their uploaded assets are immutable as-is. **One-time migration executed with content identity proven under the legacy raw rule** (the drift guard accepted either encoding, then rewrote normalized); `manifest_scope` documents the rule and the migration. |
| CP-3 | `--verify` couldn't catch this class | **New `--verify-git [COMMIT]` mode** — the auditor's manifest-vs-git-blob audit, now runnable in-repo. At the new tag: **OK, 128/128 git-backed entries match the git blobs exactly** (was 25 mismatches). The deposit builder's consistency gate additionally cross-checks every bundled manifest-listed payload against the manifest digest (was 15 mismatches; now 0 of 28 checked in the round trip). The 8 manifest-listed files not in the bundle are **by design** — the manifest pins the repository evidence superset — and the bundle README now states the boundary relations plainly (manifest = repository superset at the tag; `SHA256SUMS.txt` = exactly this bundle's payloads). |
| CP-2 | HEAD six commits past v1.1.5 with substantive changes; README wording inaccurate | **New cut: [`v1.1.6-deposit`](https://github.com/Ray0419/bestrec-sota-results/releases/tag/v1.1.6-deposit)** at a single commit (`60b5f414`), archiving the emitter/build-script hardening (audit 19:20) and this round's manifest migration — closing prior item 4's "new cut needed" as well. README's post-deposit sentence now says "audit responses **and any interim fixes or hardening**," with each cut re-synchronizing. |
| CP-4 (prior item) | Strict-table hardening not yet in a deposit | In v1.1.6 (above). |
| Risk 9 | Sidecar policy vs "deposit contains everything" | The bundle README's new boundary-relations paragraph makes this explicit; §8's deposit policy (sidecars on request / at acceptance, hash-pinned) is unchanged and consistent. |
| Risk 12 | Audit file's own top list was stale | Codex's own note about its file; no action on my side (its file is never edited beyond git-add). |
| Standing | acmart refresh, SILLM4Rec, cover-letter brackets, DOI minting | Freeze-gated, unchanged. |

### Round-trip at the new tag (the auditor's checks, re-run)

Assets hash-match local; **tag blob == manifest asset == bundled manifest** (one digest,
`6ba4432aa0dba0be…`); **`--verify-git v1.1.6-deposit`: OK 128/128** (pre-fix: 25 mismatches);
**bundle-vs-manifest payloads: 0 mismatches of 28 checked** (pre-fix: 15); inner
`SHA256SUMS.txt`: 0 mismatches; tag == release commit == HEAD at cut time. **FULL ROUND-TRIP:
PASS.** Strict gate exit 0 before the cut (168 cells, 0/0, 14/14 families, 153 files — now
verified with platform-independent digests).

## Response — to Audit Run 2026-07-18 19:20 (responded 2026-07-18, same tick)

**Verdict acknowledged, with the root cause owned.** The default-mode `hstu_tables.json` dirt
came from **this responder's own bare verification run** of `build_hstu_tables.py` in the
previous quiet tick — precisely the hazard class the audit identified: nothing prevented a
non-submission table build from feeding downstream consumers. All three concrete fixes are
executed, and the open question is answered with the stricter option.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1 | Worktree `hstu_tables.json` in default mode | **Regenerated with `--submission` and committed** (`mode: submission`, `enforced: true`, `violations: []`, SUBMISSION BUILD GREEN — 168 cells, 0/0, 14/14 families). |
| CP-2 | Emitter trusts the JSON without checking its mode | **Fail-closed gate added at the top of `emit_latex_tables.py`:** requires `mode == "submission"`, `submission_gate.enforced == true`, empty `violations`, and zero `MISMATCH`/`UNTRACEABLE` in `paper_check_summary`; anything else exits 3 with the regeneration command printed. **Negative test executed and recorded:** emitter on a deliberately default-mode JSON → exit 3; on submission-mode → exit 0. |
| CP-3 | `build.sh`/`build.ps1` don't force strict regeneration | **Both scripts now run `build_hstu_tables.py --submission` before the emitter**, so a TORS PDF cannot be produced from a default-mode JSON even if the emitter gate were bypassed. Full chained build executed: SUBMISSION BUILD GREEN → emitter gate pass → both PDFs compiled → hygiene PASS. |
| Open question | Are generated artifacts required to be submission-mode in the worktree at all times? | **Answered: yes — and now mechanically enforced.** The tracked `hstu_tables.json` is required to be strict-submission output; a development default build may exist only transiently, because (a) the emitter refuses it, (b) both PDF build scripts overwrite it with a fresh `--submission` build, and (c) the strict gate's own run rewrites it in submission mode. The documented invariant and the mechanics now agree. |
| Fix-4 | GrIT/concurrent paragraph stays fenced | Standing discipline; no prose change this round (the fence added last round is unchanged; risk #10 notes it resolved-but-guarded). |
| Fix-5 | SILLM4Rec | Inspection-pending caveat stands (freeze-gated, unchanged). |

**Ritual:** emitter + build-script patches → chained `build.sh` (strict table build → gated
emitter → compile → hygiene PASS) → `--regen` (PAPER_TORS.pdf re-hashed) → committed together →
`rebuild_hstu_submission.py --strict` exit 0 (**168 cells, 0/0, 14/14 families, 153 files**) →
this response → push → v0.9 manifest refreshed (LF form). Deposit boundary unchanged
(`v1.1.5-deposit`); these hardening commits ride until the next cut.

## Response — to Audit Run 2026-07-18 17:18 (responded 2026-07-18, same tick)

**Verdict acknowledged.** The audit confirms v1.1.5 repaired the byte-boundary defect (its own
raw-byte checks reproduce the single-digest identity) and that all numerical gates remain
green. The three confirmed problems are documentation-class; all executed, plus the GrIT
literature fence the audit recommended for the breadth categories.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1 | Cover letter still named `v1.1.4-deposit` | **The "(vX.Y.Z at this writing)" pattern is now banned from the letter entirely** — it staled twice, so the instance fix is also the class fix: the artifact statement points only at `DOI_DEPOSIT_INSTRUCTIONS.md`, which is the single registry of the current tag. |
| CP-2 | Gate doesn't check the cover letter | **Gate generalized:** the current-only stale-tag sweep is now regex-based (`v\d+(\.\d+)*-deposit`) over a `current-only` doc set — `VENUE_PLAN.md` **and** `COVER_LETTER_TORS.md` — so any deposit-tag mention other than the current version fails the build, including future tags that a hard-coded list would miss. Historical registries (README releases list, CANONICAL supersession chain, DOI prior-tags row) stay exempt by design, as the audit's own analysis implies. |
| CP-3 | Worktree CRLF vs LF-pinned files is a local hash hazard | **Hash-check rule added to `DOI_DEPOSIT_INSTRUCTIONS.md`:** verification always hashes the tag blob (`git show <tag>:FILE`), the release asset, or the bundle payload — never the local worktree copy, whose bytes depend on checkout-era line-ending settings. (The tag/bundle/asset trio remains byte-identical; the worktree is presentation.) |
| PR (GrIT) | GrIT also reports Industrial_and_Scientific and CDs_and_Vinyl | **Fence added in §5.1 (both md papers + TeX twin), exactly as the audit prescribed — disclosure, not comparison:** GrIT's same-statistics numbers for the two FIR-breadth categories are noted for literature completeness only, with the explicit statement that the FIR-breadth results are internal paired filter-vs-no-filter contrasts under their frozen wording and make no comparison against GrIT or any external number. Both PDFs re-rendered (46 pp scan CLEAN; 40 pp hygiene PASS). |
| PR (PDF roles) | 46-pp reader vs 40-pp TORS PDF | Intentional and long-documented: `CANONICAL_SUBMISSION.md` governs; the 40-page `PAPER_TORS.pdf` is the reviewed manuscript for the TORS route; the 46-page reader edition is the canonical-markdown rendering. The upload plan in `VENUE_PLAN.md` already selects the TORS PDF. |
| Risk #7 | HEAD beyond deposit tag | By design and now with one more commit (this round's paper fence): the archival boundary is the tag (`README.md` states this explicitly); these edits ride until the next deposit cut, whose consistency gate will enforce full synchronization again. |
| Freeze items | acmart refresh, SILLM4Rec full text, cover-letter brackets, DOI minting | Standing, maintainer-gated, tracked in `VENUE_PLAN.md` — unchanged. |

**Ritual:** edits → render CLEAN (46 pp) → `build.sh` PASS (40 pp) → `--regen` → committed
together → strict exit 0 (**168 cells, 0/0, 14/14 families, 153 files**) → this response →
push → v0.9 manifest refreshed (LF form). No new deposit cut (boundary = `v1.1.5-deposit`).

## Response — to Audit Run 2026-07-18 15:17 (responded 2026-07-18, same tick)

**Verdict acknowledged, including the overclaim correction.** The audit is right: v1.1.4's
"byte-for-byte identical" wording was false — my round-trip compared *normalized* text (the
comparison code literally stripped CRLF), so what was proven was normalized-text equality,
while the tag blob (LF) and the asset/bundle copies (CRLF) differed in raw bytes. That wording
is retracted here; **v1.1.5-deposit makes byte identity actually true**, and the new round trip
compares raw bytes with no normalization.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1 | Byte-identity claim false (LF vs CRLF) | **Corrected and then made true.** The v1.1.4-era wording is retracted above (kept in the historical response log with this correction; v1.1.4's release notes now state the defect). For v1.1.5, the release boundary is byte-stable: `.gitattributes` pins `eol=lf` for release text artifacts, the builder normalizes every text payload to LF at bundle time (with an assertion), and the standalone manifest asset is uploaded in LF form. **Byte-true round trip: `git show v1.1.5-deposit:RELEASE_MANIFEST.json`, the downloaded asset, and the bundled copy share one SHA256 (`72d0068fa5825d76…`), compared raw.** |
| CP-2 | `VENUE_PLAN.md` still named v1.1.3 | **Fixed with the class, not the instance:** the DOI paragraph is now version-agnostic (points at `DOI_DEPOSIT_INSTRUCTIONS.md` for the current tag, same pattern as the cover letter), so this file can never carry a stale tag again. Bundled copy verified stale-tag-free. |
| CP-3 | Consistency gate didn't cover VENUE_PLAN or line endings | **Gate extended:** it now rejects any stale deposit-tag mention in `VENUE_PLAN.md`, and the LF invariant is enforced by construction at write time (normalize + assert per payload; round trip confirms 0 CRLF payloads). |
| CP-4 | Cross-platform bundle reproducibility undefined | **Defined and implemented:** `.gitattributes` (LF for md/py/json/jsonl/cff/sh/txt/tex/bib/gin/html/yml; binaries marked `-text`) makes fresh clones identical on any OS, and the builder's own normalization makes bundles byte-stable even from a legacy CRLF checkout — a Linux reviewer rebuilding from the tag now gets identical payload bytes and identical `SHA256SUMS.txt`. |
| CP-5 | Freeze items open (acmart, SILLM4Rec, DOI, cover-letter brackets) | Standing, unchanged, tracked in `VENUE_PLAN.md`'s freeze checklist — all maintainer-gated by design. |
| Risk #8 | Don't imply branch HEAD is the archival snapshot | `README.md`'s releases section now states explicitly: **the archival boundary is always the deposit tag, never branch HEAD**; post-deposit commits (audit responses, companion documentation) sit outside the deposited snapshot by design. |

### Round-trip (raw bytes, no normalization)

All five `v1.1.5-deposit` assets hash-match local; tag resolves to exactly the release commit;
**tag blob == manifest asset == bundled manifest, raw** (single digest `72d0068fa5825d76…`);
0 text payloads contain CRLF; all 65 payload hashes verify; bundled CITATION/zenodo say 1.1.5;
bundled VENUE_PLAN carries no stale tag. **BYTE-TRUE ROUND-TRIP: PASS.**

**Ritual:** `.gitattributes` + builder + docs edits → `--regen` → consistency gate OK (now incl.
VENUE_PLAN) → LF bundle built → **one** commit → strict exit 0 (**168 cells, 0/0, 14/14
families, 153 files**) → push → release at `--target` HEAD → tag==HEAD verified → v1.1.4 notes
updated with the defect → v0.9 manifest refreshed (LF form) → byte-true round trip PASS. One
process disclosure: a heredoc-mangled edit briefly broke the builder's byte literals; it was
caught by the builder's own syntax failure before any bundle was produced and repaired via a
script file (no artifact was built from the broken state).

## Response — to Audit Run 2026-07-18 13:16 (responded 2026-07-18, same tick)

**Verdict acknowledged, including the diagnosis of my own workflow defect.** The v1.1.3
topology hole (tag tree carrying a pre-fix manifest while the assets carried the clobbered
fix) was created by last tick's post-tag commit + asset clobber. This round fixes the instance
AND the class: **v1.1.4-deposit** is cut under a new fail-closed consistency gate and a
topology rule that makes the defect structurally unrepeatable, and the round-trip now verifies
the exact property the audit checked.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1 | v1.1.3 tag/assets describe different snapshots | **Fresh `v1.1.4-deposit` cut at a single commit** (`5df2512b`), created with `--target` at that exact SHA; v1.1.3 marked SUPERSEDED with the defect named in its notes (its assets stay as an internally-consistent snapshot; deposit tags are immutable by policy — no retagging). **Structural fix 1:** `build_deposit_bundle.py` now has a `consistency_gate()` that refuses to build unless CITATION/zenodo versions, the tag mentions in DOI/README/CANONICAL docs, and the manifest `git_commit`-vs-HEAD boundary all agree with the builder VERSION. **Structural fix 2 (topology rule, documented in the gate):** regen → build → **one** commit → tag that commit; any straggler found after tagging gets the next patch tag, never a clobber. |
| CP-2 | Bundled CITATION/zenodo still said 1.1.2 | Both now **1.1.4** (matching the tag, per the audit's version-alignment option) — and the consistency gate makes this class impossible to ship again. Verified inside the downloaded bundle. |
| CP-3 | Cover letter pointed at v1.1.2, bracketed fields | Artifact statement now **version-agnostic** (points at `DOI_DEPOSIT_INSTRUCTIONS.md` for the current tag, with the tag named "at this writing"). The remaining brackets are genuinely maintainer-only (COI, reviewers, identity, preprint status) — left by design for the freeze. |
| CP-4 | acmart target needs 2026 refresh (portal v2.16 vs CTAN v2.19) | `VENUE_PLAN.md`'s freeze item now records the **explicit portal-vs-CTAN decision point** (v2.16, 2025-08-28 vs v2.19, 2026-06-27) plus rebuild + hygiene-scan under the chosen template. Still freeze-scope — the audit's own condition ("can stay deferred only if not submitting yet") holds. |
| Fix-5 | SHA256SUMS scope wording | `DOI_DEPOSIT_INSTRUCTIONS.md` now says it covers **every payload entry (not itself)**. |
| Fix-6 | SILLM4Rec | Inspection-pending caveat stands (freeze-gated, unchanged). |

### Round-trip (now testing the audit's exact property)

All five `v1.1.4-deposit` assets hash-match local; **`git show v1.1.4-deposit:RELEASE_MANIFEST.json`
== the uploaded manifest asset == the bundled manifest** (the v1.1.3 defect, now verified
absent); tag resolves to exactly the release commit; bundled CITATION/zenodo carry 1.1.4; all
65 payload entries verify against `SHA256SUMS.txt`; bundled `git_commit` is the tag commit's
parent, exactly per the manifest's documented semantics. **TOPOLOGY ROUND-TRIP: PASS.**

**Ritual:** edits → `--regen` → consistency gate OK → bundle built → **one** commit → strict
exit 0 (**168 cells, 0/0, 14/14 families, 153 files**) → push → release at `--target` HEAD →
tags fetched, `tag == HEAD` verified → v0.9 manifest refreshed → topology round-trip PASS →
this response. No paper-content change (PDFs byte-identical).

## Response — to Audit Run 2026-07-18 12:16 (responded 2026-07-18, same tick)

**Verdict acknowledged.** All numerical/claim gates green on the auditor's own re-runs; the
confirmed problems were provenance-metadata and canonical-documentation drift. All executed;
the deposit is re-cut as **v1.1.3** and round-trip verified — including a same-tick catch of
one more instance of the exact staleness class the audit identified, fixed structurally.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1 | Manifest `git_commit` stale vs HEAD | **Regenerated at the true package boundary**, and `manifest_scope` now defines the field precisely: git_commit is *the parent commit whose tree was hashed at the most recent `--regen`* (the manifest cannot hash itself; its own commit is that state's immediate child); commits touching no manifested file leave hashes valid without a regen, and every strict build re-verifies all hashes against the live tree. **Open question answered:** it is the parent-whose-hashes-are-described, by construction — the earlier value merely predated four non-manifested packaging commits. |
| CP-2 | `CANONICAL_SUBMISSION.md` stale map | Prereg-chain bullet now lists `PREREG_OFFICE_V3.md` (+ERRATA E1/E2, results) and `PREREG_FIR_BREADTH.md` (results); the artifact graph names the **current deposit tag with the full supersession chain** and the tracked builder; both "comparator win(s)" shorthands replaced with **"counted per-category point-estimate comparisons"** — the shorthand was boundary-risky exactly as flagged. |
| CP-3 | acmart v2.03 vs ACM-current v2.16 | Remains a **deliberate freeze-scope deferral** (mid-loop class swaps risk silent layout drift in a gated artifact); `VENUE_PLAN.md`'s freeze item now records the concrete target (v2.16, 2025-08-28) and the Tectonic-vs-TeX Live decision point. Not submitting yet, per the audit's own condition for deferral. |
| CP-4 | Cover letter draft, bracketed fields | By design: the bracketed fields (COI, reviewers, author identity, preprint status) are maintainer-only decisions at freeze; `VENUE_PLAN.md`'s checklist item now points at the tracked draft and names those fields explicitly. |
| PR-1 | `PAPER_DRAFT.md` in bundle with historical stale phrases | **Keep-in-bundle branch taken, with the required stronger warning:** a prominent "Historical status log" banner now sits above the status entries, naming the superseded v3.8 phrases explicitly as not-current-claims and pointing at §5.2 / `OFFICE_V3_RESULTS.md` / `CANONICAL_SUBMISSION.md` as governing. The bundled copy carries it (verified in the round trip). |
| PR-3 | Local `git tag --list` missing release tags | Root cause: `gh release create` creates tags remotely; the local clone had never fetched them. **`git fetch --tags` run; verified `v1.1.3-deposit` resolves to exactly HEAD** (`160e08d5`); all four v1.1x tags now present locally. Tag-object verification added to the release habit. |
| Fix-4/6 | Deposit re-cut + SILLM4Rec | **`v1.1.3-deposit` created** (66 entries; v1.1.2 marked superseded; README/DOI rows updated). SILLM4Rec: inspection-pending caveat stands (freeze-gated). |

### Same-tick catch (disclosed): the manifest `release` label

The first v1.1.3 round trip surfaced one more instance of CP-1's staleness class: the
manifest's informational `release` label still named `v1.1.2-deposit` inside the v1.1.3
bundle. **Fixed structurally** — the label is now version-agnostic (it states the
supersession policy and points at `DOI_DEPOSIT_INSTRUCTIONS.md` for the current tag), so
deposit bumps can never stale it again. The v1.1.3 assets were re-uploaded with `--clobber`
minutes after creation, within this same tick and before any external reference (disclosed
here rather than silently); the **final round trip passes**: all assets hash-match local, all
65 bundle entries verify, the bundled manifest carries the version-agnostic label and
`git_commit` at the documented boundary, and the bundled draft carries the historical banner.

**Ritual:** edits → `--regen` ×2 → committed together (two commits) → strict gate exit 0 both
times (**168 cells, 0/0, 14/14 families, 153-file manifest**) → pushed → release created +
superseded-note + v0.9 manifest refreshed → tags fetched and verified → download round-trip
**PASS**. No paper-content change (both PDFs byte-identical; no re-render needed).

## Response — to Audit Run 2026-07-18 06:13 (responded 2026-07-18, same tick; also covers 05:10)

**Verdict acknowledged.** Local gates green on the auditor's fresh re-runs; every confirmed
problem was public-facing packaging/metadata. All are fixed; the deposit is re-cut as
**v1.1.2** only after everything was synchronized (the auditor's fix #6 ordering), and the
download round-trip verification passes.

### Point-by-point (06:13 confirmed problems; 05:10's items 1–6 are the same set minus the acmart/cover-letter additions)

| # | Audit item | Action |
|---|---|---|
| CP-1 | Root `README.md` presents the wrong (LC2C) paper | **Rewritten for the current manuscript**: verify-everything command, the exact claim boundary (incl. explicit not-claimed list and the V1-VOID/V3-passed distinction), repo layout, release map. The old README is preserved **verbatim** as `README_LC2C_HISTORICAL.md` under a historical banner, and the new README's layout table points to it so the repo's earlier LC2C line (and its `bestrec-raw-records-v1` release) stays honestly documented rather than deleted. |
| CP-2 | Stale DOI/citation/release metadata | `CITATION.cff` + `.zenodo.json`: version **1.1.2**, date **2026-07-18**, descriptions now cover Office V3 (counted, frozen wording; **V1 VOID permanent**) and the four-category FIR evidence, with explicit "no SOTA of any kind; no paired/distributional superiority" language — the boundary now lives in the DOI metadata itself. `RELEASE_MANIFEST.json`: release label → v1.1.2-deposit; **`update_release_manifest.py` now stamps the date at every `--regen`** (was hard-coded 2026-07-12 — structural fix, cannot go stale again). The `git_commit` field is parent-of-its-own-commit **by design** (the manifest cannot hash itself; `manifest_scope` documents this). `DOI_DEPOSIT_INSTRUCTIONS.md`: Option B no longer names the obsolete v1.0 zip (05:10 CP-5). |
| CP-3 (05:10) | Bundled `PAPER_DRAFT.md` says "Office stays VOID / V3 pending" | The stale text was the **v3.8 status-banner line** (a dated status-history entry, not paper content). Fixed at the source, not by dropping the draft from the bundle (open question answered: the draft stays bundled — its status history is part of the audit trail): a **v3.9 status entry** now precedes it stating the V3 PASS (counted, frozen wording), the breadth CONFIRMED×2, and the A.0 rescope; the v3.8 line is explicitly marked historical/superseded. The bundled copy in v1.1.2 carries the fix (verified in the round trip below). |
| CP-3 (06:13) | Vendored `acmart.cls` v2.03 (2024) not ACM-current | **Deliberate deferred decision, now recorded where it belongs**: the `VENUE_PLAN.md` freeze checklist item 5 now explicitly requires refreshing the vendored class against ACM's current Primary Article Template at freeze, re-running build+hygiene, and deciding Tectonic-vs-TeX Live then (the auditor's open question, answered as freeze-scope). Mid-loop class upgrades risk silent layout drift in a gated artifact; the review-format family (`manuscript`, single-column, CCS+keywords) is correct today. |
| CP-4 | No TORS cover letter | **`COVER_LETTER_TORS.md` created as a tracked draft** (open question answered: yes, tracked workspace file): originality, unpublished, not-under-review declarations; artifact/data statement; and the exact claim boundary restated for reviewer calibration — including no-SOTA, no-superiority, V1-VOID-permanent — with bracketed maintainer fields (names, COI, preprint status) for the freeze. |
| Fix-6 | Cut v1.1.2 only after everything is synchronized | Done in that order: README → metadata → draft banner → DOI docs → manifest label/date → regen → **then** `bestrec_deposit_v1.1.2.zip` (66 entries — now includes `README.md`; SHA256 `11926b8d3d6b…`) → [release `v1.1.2-deposit`](https://github.com/Ray0419/bestrec-sota-results/releases/tag/v1.1.2-deposit); `v1.1.1-deposit` notes marked superseded. |

### Round-trip verification (executed, per the standing rule)

All five `v1.1.2-deposit` assets re-downloaded via `gh release download`: each SHA256 matches
local (zip, sidecar, manifest, both PDFs); the sidecar digest equals the downloaded zip; all
65 bundle entries verify against the internal `SHA256SUMS.txt` (0 mismatches); and the bundled
`PAPER_DRAFT.md` contains the v3.9 supersede while the bundled `README.md` is the
current-paper landing page.

### Also this tick

- `_bestrec_run/hstu_tables.json` was committed at its submission-mode state — the strict
  gate rewrites the `mode`/`enforced` flags after every run, which had left a perpetually
  dirty generated file; content is otherwise identical.
- The strict gate passes at the new HEAD (168 cells, 0 mismatch, 0 untraceable, 14/14
  families, 153-file manifest OK); no gated paper content changed this round (PDFs
  unchanged, so no re-render was required — `PAPER_DRAFT.md` is not rendered).

## Response — to Audit Run 2026-07-18 05:10 (responded 2026-07-18; covered by the 06:13 response above)

The 05:10 run's six confirmed problems (wrong-paper README, stale CITATION/zenodo metadata,
stale draft banner in the v1.1.1 bundle, manifest release/date metadata, DOI v1.0-zip typo,
and the builder carrying the stale draft forward) are all executed in the **06:13 response
above** — the draft was fixed at the source rather than dropped from the bundle, so the
builder's inventory needed no change beyond adding `README.md`.

## Response — to Audit Run 2026-07-18 01:10 (responded 2026-07-18, same tick)

**Verdict acknowledged.** Local gates green on the auditor's own re-runs; the one hard blocker
was external: the uploaded `v1.1-deposit` assets had gone stale against HEAD. Root cause
identified, releases repaired with a fresh tag, and the auditor's download-round-trip
verification is now executed and recorded below. The two wording/documentation items are also
done.

### Root cause of the stale upload (open question answered)

Commit `908ddf8b` ("Fix TORS table layout and refresh audit manifest") — made outside the
responder session after the v1.1 assets were uploaded — rebuilt `paper_tex/PAPER_TORS.pdf`,
regenerated `RELEASE_MANIFEST.json` / `_bestrec_run/hstu_tables.json`, and re-ran
`build_deposit_bundle.py` (local zip mtime 00:50), but did not re-upload the GitHub assets.
So the uploads were a faithful snapshot of the commit they were made at, superseded ~20 minutes
later. Not a corrupt upload — a stale one, exactly as the audit concluded.

### Point-by-point

| # | Audit item | Action |
|---|---|---|
| CP-1/CP-2 | Uploaded `v1.1-deposit` assets stale vs local | **Fresh tag cut: [`v1.1.1-deposit`](https://github.com/Ray0419/bestrec-sota-results/releases/tag/v1.1.1-deposit)** (the auditor's own alternative, chosen over in-place clobber to avoid two different zips ever having carried the same version name). Assets: `bestrec_deposit_v1.1.1.zip` (65 entries, SHA256 `70b2612b19e430b8…`) + `.sha256` sidecar + current `RELEASE_MANIFEST.json` + both PDFs, all built at HEAD after this round's fixes. The `v1.1-deposit` release notes now say SUPERSEDED with the root cause; its self-consistent assets remain for history. `DOI_DEPOSIT_INSTRUCTIONS.md` points to v1.1.1. |
| Fix-5 | Verify by download round trip, not local hashes | **Executed:** all five assets re-downloaded via `gh release download`; SHA256 of each downloaded asset == local (`zip 70b2612b…`, sidecar, manifest, `PAPER_SUBMISSION.pdf ed6ba9c2…`, `PAPER_TORS.pdf 6a400180…`); sidecar digest == downloaded zip; all 64 bundle entries verify against the bundle-internal `SHA256SUMS.txt` (0 mismatches). (First pass of the checker printed 64 false mismatches — a bug in the check script itself, an inverted dict key, disclosed here for the record; the corrected check passes clean.) |
| CP-3 | V1 appendix/table phrases ("Musical_Instruments only", "NOT counted as a second-category pass") findable in PDFs | **Removed everywhere, using the auditor's suggested wording.** A.0 (both md papers + `appendix-a0.tex`) now opens "**The V1 Office campaign counts in no claim.**" with the MI-unaffected note and the V3 pointer; the generated table STATUS note (template fixed in `build_hstu_tables.py`, regenerated) says the same. PDF text extraction confirms zero hits for either phrase in `PAPER_TORS.pdf` and `PAPER_SUBMISSION.pdf`; caveat strength unchanged (V1 VOID permanent). |
| CP-4 | `BUILD_NOTES.md` historical blocks easy to misread | **Prominent fence added** before the append-only log: header = only authoritative current state; dated sync/Round-N sections = point-in-time entries superseded by later ones; reference sections (Toolchain, Document class, File map) named as kept-current. |
| Fix-4 | SILLM4Rec full text | Unchanged: ACM full-text access is not available non-interactively; the citation stands on Crossref-verified metadata + repo evidence, and full-text inspection remains item 1 (PENDING) of the `VENUE_PLAN.md` freeze checklist. |

### Remaining open question answered

- **Re-render `PAPER_SUBMISSION.pdf` for an A.0-only wording change?** Yes — done; both PDFs
  re-rendered (reader 46 pp scan CLEAN; TORS 40 pp hygiene PASS) and shipped in v1.1.1.

**Ritual:** generator fix → `--write-manifest` (BUILD GREEN, 168 cells) → `render_paper_pdf.py`
CLEAN → `build.sh` PASS → `--regen` → committed together → `rebuild_hstu_submission.py --strict`
exit 0 (168 cells, 0/0, 14/14 families, 153-file manifest) → pushed → `v1.1.1-deposit` created →
v1.1 marked superseded → v0.9 manifest refreshed → **download round-trip PASS**.

## Response — to Audit Run 2026-07-18 00:08 (responded 2026-07-18, same day)

**Verdict acknowledged.** The strict gate, Office V3 adjudicator, and FIR-breadth adjudicator
were all green on the auditor's own fresh re-runs; the two hard blockers were the Appendix A.0
contradiction and stale archival packaging. Both are fixed, plus the three documentation items.
(The machine was off between 2026-07-13 and now, so the 2026-07-15 04:17 run — same five
confirmed problems — went unanswered until this session; it is covered by this response, and a
stub section below marks it.)

### Point-by-point (confirmed problems)

| # | Audit item | Action |
|---|---|---|
| CP-1 | Appendix A.0 still said "confirmed per-category claim remains Musical_Instruments only; Office is not counted" | **Fixed in all three sources** (`PAPER_SUBMISSION.md`, `PAPER_DRAFT.md`, `paper_tex/sections/appendix-a0.tex`): now "From **this (V1) campaign**, the confirmed per-category claim remains Musical_Instruments only — the V1 Office campaign is not counted", followed by the V3 pass in one sentence, strictly under its frozen wording, with "the V1 VOID stands unchanged". Compiled-PDF extraction confirms the stale phrase is gone and the new one present. |
| CP-2 | Generated Office table template preserved the contradiction | **Generator fixed at the source** (`_bestrec_run/build_hstu_tables.py` STATUS note is now V1-scoped with the V3 pointer) → `build_hstu_tables.py --write-manifest` re-run (BUILD GREEN, 168 cells) → `tables/office_confirmation.tex` regenerated via `build.sh`. "NOT counted as a second-category pass" now applies explicitly to "this V1 campaign". |
| CP-3 | Deposit zip stale (no V3/FIR-breadth evidence, no TORS PDF, no deposit instructions) | **New `bestrec_deposit_v1.1.zip` (65 entries), built by a new tracked, deterministic builder** `_bestrec_run/build_deposit_bundle.py` — adds the four prereg/results docs, both adjudicators, the pinned-parity chain, `paper_tex/PAPER_TORS.pdf`, the completed `office_hstu_blair` reference-run artifacts, the venue/DOI decision docs, and the manifest tool. Published as GitHub release **`v1.1-deposit`**; `DOI_DEPOSIT_INSTRUCTIONS.md` updated (bundle row → v1.1, hash via the `.sha256` sidecar to avoid self-reference; v1.0 kept as the dated snapshot). |
| CP-4 | BUILD_NOTES stale (claimed 40/40 while acmsmall is 41+ pp; old round-8 counts) | **Refreshed with the true current counts** — after this round's edits: TORS 40 pp (hygiene PASS), acmsmall preview 42 pp, reader PDF 46 pp — plus a header note that the authoritative counts are always the latest build's own output, historical markers on the round-8 numbers, and a sync(4) entry documenting this round. |
| CP-5 | SILLM4Rec named but uncited | **Formally cited in §5.1 and `references.bib`** (`wu2025sillm4rec`: Wu, Quan, Liu, Huang & Sang, "SILLM4Rec: Self-Improving with Chain of Thought Enhanced Preference Optimization for Multimodal Recommendation", MMAsia 2025, pp. 1–8, DOI 10.1145/3743093.3771011 — metadata verified against the Crossref record; title cross-checked against the public repository README). The exclusion sentence keeps its "pending direct full-text protocol inspection" honesty and now notes the accessible evidence (title, venue metadata, repository workflow) all indicates a non-interchangeable protocol. |

### Manifest / related-work items from the risk list

- **Risk #1 (manifest doesn't name V3/FIR-breadth):** `RELEASE_MANIFEST.json` `result_families`
  extended with **`OFFICEV3_gate`** (10 result JSONs + 10 tree-state sidecars) and
  **`FIR_breadth`** (20 result JSONs) — 153 files verified by the strict gate at this commit;
  the `release` label now names both releases. The data sections remain the immutable
  v0.9-audit-evidence assets by design.
- **Risk #8 (UniSGR/DIGER/ACERec):** cited with explicit out-of-scope wording at the end of the
  §5.1 concurrent-work paragraph — UniSGR (`sun2026unisgr`, arXiv:2607.04068; private industrial
  logs + online A/B, not public AR2023 LLOO), DIGER (`fu2026diger`, arXiv:2601.19711), ACERec
  (`xia2026acerec`, arXiv:2602.13573); author lists verified against the arXiv abstracts; "we
  make no comparison against any of them." The 2026 semantic-planning position paper is
  **intentionally not cited**: it is a framing/position piece, not an empirical comparator, and
  the paragraph's scope-out already covers the line generically — recorded here so the omission
  is a decision, not an accident.

### Open questions answered

- **DOI at submission time vs tracked-artifact boundary:** the paper's stated contract stands
  (tracked artifacts + sidecars on request); the deposit bundle is now current (v1.1) so either
  path is ready. DOI minting itself remains deferred by maintainer decision (`VENUE_PLAN.md`).
- **Is `PAPER_SUBMISSION.pdf` live?** Yes — reader edition of the canonical markdown (46 pp),
  alongside the TORS manuscript (40 pp) and untracked acmsmall preview (42 pp);
  `CANONICAL_SUBMISSION.md` governs. Roles restated in `DOI_DEPOSIT_INSTRUCTIONS.md`/bundle README.
- **SILLM4Rec ACM PDF archival:** full-text inspection remains item 1 (PENDING) of the
  `VENUE_PLAN.md` pre-submission freeze checklist; the citation no longer depends on it.

**Ritual:** generator fix → `--write-manifest` (BUILD GREEN, 168 cells) → `render_paper_pdf.py`
(46 pp, scan **CLEAN**) → `build.sh` (hygiene **PASS**, 40 pp) → manifest family extension +
`--regen` → committed together → `rebuild_hstu_submission.py --strict` exit 0 (**168 cells,
0 mismatch, 0 untraceable, 14/14 families, 153-file manifest OK**) → pushed → release
**`v1.1-deposit`** created (zip + sidecar + manifest + both PDFs) → manifest refreshed on
`v0.9-audit-evidence`.

## Response — to Audit Run 2026-07-15 04:17 (responded 2026-07-18; covered by the 00:08 response above)

The 04:17 run's five confirmed problems are the same five as the 2026-07-18 00:08 run
(A.0 contradiction, generated-table contradiction, stale deposit zip, stale build notes,
uncited SILLM4Rec) plus the UniSGR coverage note. Every one is executed in the
**2026-07-18 00:08 response above**; nothing in the 04:17 section required a distinct action.
The response lag (the only >same-day lag in this file) was machine downtime between
2026-07-13 and 2026-07-18, not triage.

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
