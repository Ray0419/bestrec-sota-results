# PAPER DEADLINE PLAN — submission-shaped by 08:00 Sydney 2026-07-25

Maintainer deadline (2026-07-25 ~00:40 Sydney): get the paper **submission-shaped**
by **08:00 Sydney**. Cron ticks + continued turns EXECUTE this until then; the
rewrite (WS4) is the TOP priority over other worklist items until the deadline.

## Definition of "done" (honest)
Submission-SHAPED, not accepted, not metadata-complete:
- [x/in-progress] Rewrite to the moderate target (main body ≈ 28pp; keep caveats,
  relocate exhaustive tables + superseded material to `## Supplementary Material`).
- Language pass: "refuted/refutation/flat tail null" -> "non-reproduced / estimate
  crosses zero" (meaning-preserving; legitimate "null hypothesis" usage kept).
- `paper_tex` reconciled to the rewritten md; `bash paper_tex/build.sh` PASS (H1–H9);
  render "scan: CLEAN"; `rebuild_hstu_submission.py --strict` exit 0.
- Fresh deposit tag cut at the clean boundary; manifest regen + from-zero verify.
- **NOT done (human/uncontrollable):** author/affiliation metadata (TODO marker
  stays); acceptance (odds unchanged); E-E V2 factorial adjudication (OFF arm still
  training in background — a caveated closest-comparator, not a manuscript blocker).

## Milestones (Sydney)
- **02:30 — Relocation.** Move §5.4 titration ladder (Table 1e) + §5.5 screening
  log (Table 2) into the Supplement with one-line summaries left in the main text;
  superseded appendices already relabelled S.1–S.3. Cells stay present -> gate green.
- **04:30 — Tightening + language.** Trim intro contribution paras, §2 related
  work, §6 discussion, §7 conclusion; the language pass; abstract already scoped.
- **06:00 — TeX reconcile.** Mirror the md prose changes into `paper_tex/sections/*`,
  rebuild, H1–H9 pass. (Canonical md leads; tex is the derivative.)
- **07:15 — Deposit.** Cut `vX-deposit` at the clean boundary; regen manifest;
  from-zero clone verify at the tag; upload manifest.
- **08:00 — Final.** Full ritual green, push, report status + the remaining human TODO.

## Method (proven this session)
Anchor-span Python edits (typography-safe, count-verified); every increment:
render CLEAN + paper-check 0 mismatch + strict exit 0 + commit. Results-section
prose NUMBERS are gate integrity-anchors — never removed, only relocated. Claim
boundary (MI V2, Office V3; FORBIDDEN list) applies verbatim; the rewrite
reorganises/tightens and invents no results.

## Progress log
- 2026-07-25 00:1x — 9 commits: abstract, front matter, §3.7, §5.5, §6.1, §6.5
  tightened; Supplement boundary S.1–S.3 established.
- 2026-07-25 00:55 — **M1 relocation DONE + M2 language DONE (ahead of schedule):**
  §5.5 screening-log table -> Supplement Table S1 (§S.4); §5.4 titration ladder ->
  Supplement Table S2 (§S.5); language pass (assertive "refuted/flat-null" ->
  "non-reproduced/near-zero/no detected trend", disclaimers + numbers kept). 12
  rewrite commits; every one render-CLEAN + paper-check 0 mismatch + strict exit 0.
  Main body is now structurally submission-shaped (exhaustive tables + superseded
  material live in the Supplement).
- REMAINING to 08:00: (a) optional further tightening of intro/related/conclusion
  (plateaus under keep-caveats); (b) **M3 paper_tex reconcile** — mirror the md
  prose + the new Supplement S.4/S.5 structure into paper_tex/sections, rebuild
  (H1–H9); this is the heavy, less-automatable piece; (c) **M4 deposit** tag +
  from-zero verify. Author metadata stays a TODO.
- 2026-07-25 ~03:30 (tick) — audit 21:59 answered + rewrite advanced: E-E V2 relabeled (representation-package/outcome-visible/NOT countable); abstract 'pass'->'met a predeclared threshold under environment caveats'; §2.2 8-item inventory subordinated to the 3 headline claims; 'Every retraction' universal claim removed. All gate-green. Heavy remaining (stretch, ~4.5h to deadline): cut Results §5.3-§5.4 (number-dense; move forensics to Supplement), figures (Fig1->forest plot; page-61 list), **M3 paper_tex reconcile** (still stale + placeholders), **M4 deposit**. Author metadata = human TODO; acceptance unchanged.
- 2026-07-25 ~05:xx (tick) — **M3 paper_tex reconcile, first substantive pass (build un-blocked):** the actual TORS package `paper_tex/build.sh` had been RED — a table-order-drift FATAL in `emit_latex_tables.py` (the md rewrite relocated Table 1e→S2 and Table 2→S1 into the Supplement, changing pipe-table order; the emitter REGISTRY still expected the old sequence). Fixed by reordering REGISTRY to the current md order (pure byte-permutation; verified 15/15 fp-order match against the live md). Also reconciled `paper_tex/sections/abstract.tex` to the softened canonical md (removed the stale stronger 'pass against published' + universal 'Every retraction' wording that the audit's #1 finding flagged as still living in the submission PDF). Rebuilt: emit passes, both tectonic targets compile, tables regenerate now captioned **Table S1/S2** (md captions flow through the emitter), numeric cross-check 54/54 exact, `check_tex_health.py` **H1–H9 PASS**, hygiene scan PASS. The ONLY remaining build gate is **H10 = the `[Maintainer:` byline placeholder** (author metadata, the standing human TODO; waived-and-logged via `build.sh --draft`, exit 0). PAPER_TORS.pdf refreshed (no longer stale/stronger-claim); manifest regen'd. **Residual M3 (placement, not a blocker):** the S1/S2 tables are captioned correctly but their `\input` still sits in the §5.4/§5.5 body, not yet inside a tex Supplement section mirroring the md's `## Supplementary Material` (S.1–S.5) — a placement/structure fix (add a Supplement section to main.tex, move the two `\input`s, leave body pointers). M4 deposit + figures + author byline still open; acceptance unchanged.
- 2026-07-25 ~06:xx (tick) — **M3 reconcile, second pass (text-correctness unit) + a canonical-source bug caught:** (1) **md regression fixed** — the deadline rewrite's global "Table 2"→"Table S1" rename had corrupted the Liu 2025 citation locator: md said "0.0406; Liu 2025, Table S1)" but 0.0406 is FROM Liu's *published* Table 2 (the hand-maintained tex correctly cites `\citealp[Table 2]{liu2025hstublair}`), NOT our screening-log Supplement table — restored to "Table 2". (2) **tex screening-table refs synced** — 3 refs in 05-results + 1 in 06-discussion updated "Table 2"→"Table S1" to match the emitter's S1 caption (the Liu-citation locator at 05-results:88 correctly left as "Table 2"). (3) **tex title synced** — paper-shared.tex still had the old 167-char title; set to the md's shortened "Artifact-Gated Evaluation of Text-Augmented Sequential Recommenders". Render md scan CLEAN 61pp; tex build.sh --draft PASS (H1–H9 + hygiene; only byline H10 waived); strict exit 0. **Residual M3 unchanged (deferred, still not a blocker):** the structural table relocation (S1/S2 `\input` still in §5.4/§5.5 body, not a tex Supplement section) — riskier prose-reflow, kept out of this atomic unit. Byline/deposit/figures still open; acceptance unchanged.
