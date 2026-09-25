# Human-only steps between the current state and a submitted manuscript (2026-09-08)

State at `08401302` on `codex/cleanresearchwithskill`: `rebuild_hstu_submission.py --strict` PASS;
release manifest verified (1,081 files); hygiene scan PASS; `paper_tex/PAPER_TORS.pdf` 33 pages,
`PAPER_TORS_acmsmall.pdf` and `PAPER_TORS_SUPPLEMENT.pdf` built. Nothing below can be done by an
agent without inventing identities, accepting legal terms, or publishing on your behalf.

## A. ACM TORS (primary, rolling submission)

1. **Author metadata.** Replace every `[Maintainer: ...]` field in `paper_tex/paper-shared.tex`
   (title block), `COVER_LETTER_TORS.md`, `CITATION.cff`, `.zenodo.json`. TORS is single-blind, so
   real names/affiliations are required.
2. **AI-use statement.** Finalize the short form in `AUTHORSHIP_AI_STATEMENT.md` (worktree
   `brave-rhodes-0a7d09`; copy to main) and resolve its two `[HAS/HAS NOT]` boxes truthfully. Check
   the current ACM authorship policy wording at submission time (the policy page returned 403 to
   automated fetch on 2026-09-08).
3. **Tier-A decision (gate A0).** Name the ranking authority and edition your institution uses and
   verify TORS (ISSN 2770-6699) against it, per `TIER_A_PUBLICATION_ROADMAP.md` §2. If TORS does
   not qualify, the fallback shortlist is in the same section.
4. **Gate-A0 ranking spot-check + human re-verification** of the counted numbers
   (`CANONICAL_SUBMISSION.md` items 1–3) against `_bestrec_run/hstu_tables.json`.
5. **Rebuild after edits, in this order:** `paper_tex/build.ps1` → `python
   _bestrec_run/update_release_manifest.py --regen` → `python
   _bestrec_run/build_claim_artifact_map.py --write` → `--regen` again → commit everything →
   `python _bestrec_run/rebuild_hstu_submission.py --strict` must print SUBMISSION REBUILD: PASS.
6. **Deposit.** Tag `v1.2.0-deposit` (the manifest's `intended_deposit_tag`), run the no-waiver
   clean-clone replay (`_bestrec_run/clean_clone_replay.py`; see `DOI_DEPOSIT_INSTRUCTIONS.md`),
   upload to Zenodo, and put the DOI in the availability section.
7. **Submit** via the TORS portal with `COVER_LETTER_TORS.md`. Optional cover-letter sentence
   licensed by `COMPARATOR_LANDSCAPE_2026-09-08.md`: "as of 2026-09-08 we located no published
   NDCG@10 above the HSTU-BLaIR values on either counted category under this protocol."

Known scientific exposure a reviewer may raise (roadmap Phases B/C, not closable without new GPU
campaigns you must authorize): baseline tuning fairness and the absence of an externally custodied
non-Amazon replication. Both are disclosed in the manuscript's limitations.

## B. RecSys 2027 short paper (ρ(k)/π*), next window ≈ April 2027

1. Complete the placeholder bib entries in `paper_tex_rhok/refs.bib` (worktree) from the arXiv
   records; re-run `tectonic main.tex` and confirm it still fits 4 pages + references.
2. Create the anonymous repository (pre-registration `PREREG_RHO_K_V1.md`, analyzer
   `poc_rho_k_analyze.py`, `RHO_K_analysis.json`) and add its link.
3. Write the GenAI disclosure in Acknowledgments (required by the RecSys CFP).
4. Check the RecSys 2027 CFP when it appears; 2026 rules assumed: 4 double-column pages, references
   extra, mutually anonymous review, abstract ~1 week before the paper deadline.

## C. What does not exist and should not be claimed

No general state-of-the-art result. The counted results are per-category point-estimate wins
(Musical_Instruments, Office_Products V3) over a single-seed published comparator. Video_Games is
0.0673 vs 0.0760 and is explicitly not claimed.
