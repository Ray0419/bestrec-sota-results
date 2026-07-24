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
- 2026-07-25 00:1x — 9 rewrite commits: abstract, front matter, §3.7, §5.5, §6.1,
  §6.5 tightened; Supplement boundary S.1–S.3 established. 28,411 -> ~28,115 words,
  61 -> 60 pp. (Relocation step 1 structural; word drop comes with the table moves.)
