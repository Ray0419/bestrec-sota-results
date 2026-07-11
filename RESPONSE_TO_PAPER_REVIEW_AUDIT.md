# Response to PAPER_REVIEW_AUDIT (cumulative)

This response file is cumulative, mirroring `PAPER_REVIEW_AUDIT.md`: each audit run gets a
timestamped response section below. The newest section always addresses the audit's newest
"Audit Run" section and its updated risk list.

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
