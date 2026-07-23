# SYNTHESIS_PLAN_DRAFT — restructuring PAPER_SUBMISSION.md into a 20–35pp acmsmall journal synthesis

**Status:** DRAFT plan only (2026-07-23). No paper content has been changed by this file. Executor: follow the sequence in §6.
**Inputs read:** `PAPER_SUBMISSION.md` (current: 27,895 words total; ~23.2k words of §1–§10 body excluding references and appendices; renders ~60pp reader / ~51pp TORS acmsmall), `CANONICAL_SUBMISSION.md`, `README.md`, `EXPERIMENT_PROGRAM.md`, `VENUE_PLAN.md`, `paper_tex/BUILD_NOTES.md`, and the standing audit demands in `PAPER_REVIEW_AUDIT.md` (notably: "choose one central thesis — evaluation apparatus or recommender method — and move campaign chronology to a supplement"; "Target a 10–14k-word journal synthesis plus a separate provenance/forensic supplement"; "Give E-F/E-G coherent method and related-work placement or remove them from the main contribution"; the 20–35-page acmsmall length target).
**Hard constraints honored throughout:** no frozen wording changes meaning; claims may only narrow; no SOTA language anywhere except inside the existing explicit non-claims; every printed number stays inside the fail-closed artifact-gate scan scope (the 175-cell graph relocates with its cells — nothing leaves the gate).

---

## 1. THESIS DECISION

**Recommendation: (a) — the governed-evaluation apparatus, demonstrated end-to-end on a text-augmented sequential recommender, with the empirical campaigns as the evidence that the apparatus produces trustworthy (and honestly refused) findings.**

Rationale (2 sentences): Every external audit round converges on the same verdict — the apparatus is the distinctive contribution while the method additions are graded incremental in a crowded neighborhood by the paper's own Table 0 and Closest-systems I–III, so thesis (b) would headline the paper's weakest flank and would additionally require experiments that are still open (E-B permutation control, E-E AlphaFuse benchmark-or-exclusion, per `EXPERIMENT_PROGRAM.md`) before a method story could stand. Thesis (a) requires **zero claim changes**: the two counted per-category comparisons, the FIR package with its E-A isolation, the MI frequency-5 tail case, E-F, and the E-G refusal already function as the apparatus's demonstration corpus, and all frozen wordings carry over verbatim — the restructure is purely a re-hanging of existing, gated content on the apparatus spine.

Notes binding the decision:
- The **title already matches thesis (a)** ("Artifact-Gated Evaluation of Text-Augmented Sequential Recommendation: …"). Do NOT retitle: `COVER_LETTER_TORS.md` submits the exact canonical title verbatim, and a retitle would ripple through cover/README/CANONICAL for no thesis gain.
- The apparatus claim itself must stay **narrow**, exactly as §2.3(v) already words it: the claim is the *exact combined enforcement mechanism demonstrated on one submission* — "positioned against, not above" Elliot/DaisyRec/Bellogín & Said/Petrov & Macdonald. The audits have flagged that one self-audited case cannot establish general apparatus effectiveness; the synthesis must not silently upgrade the apparatus into a validated general framework. Keep the existing scoping sentences.
- Method results are **retained as findings, demoted from co-headline**: the abstract and §1 lead with the apparatus; the FIR/tail/hybrid results are presented as what the apparatus certified, the VOID/retractions/E-G as what it refused to certify. This is a framing move only; no result is weakened or strengthened.

---

## 2. TARGET STRUCTURE

Target: **≈12,200 words of body text** (hard band 9,000–13,000; abstract included, references/appendices excluded), which at acmsmall density with the retained tables/figures/references lands ≈28–33 pages — inside the 20–35pp demand with headroom. Word budgets below are ceilings; if the first acmsmall build exceeds 35pp, the pre-authorized contingency cuts are (in order): Closest-systems condensation 350→250, §5.1 550→450, Table 0 relocated to supplement with its two boundary sentences kept in §2.2.

| New § | Title | Budget (words) | Built from (current §) |
|---|---|---:|---|
| — | Title + author line | — | keep verbatim (title unchanged; author fields remain the maintainer placeholder) |
| Abstract | Abstract | 200 | rewrite of current Abstract (212) per the audit template: problem → apparatus (a)–(d) in one sentence → the two counted comparisons + FIR package + tail case with uncertainty → one refusal (VOID / E-G descriptive-only) → principal limitation (single-run comparators; fixed-split scope). All numbers already in the current abstract; narrowing only. |
| §1 | Introduction | 900 | condense current §1 (1,307). Keep: evaluation-trust problem framing; the apparatus items (a)–(d) as a one-paragraph overview (mechanics move to new §3); the two research questions; a restructured contribution list — 1. apparatus (lead), 2. FIR package (per §5 wording), 3. MI frequency-5 tail case, 4. E-F hybrid, with E-G named only as a descriptive study; the "our claimed additions are deliberately small" paragraph. Delete-as-redundant: the in-§1 restatement of the Office V0/V3 episode detail (keep 1 sentence + pointer to §5.2/S§1). |
| §2 | Related work and attribution | 1,250 | §2 + §2.1 + §2.3, condensed. §2.1 (350): evaluation practice/reproducibility line (Ferrari Dacrema ×2, Sun 2020, Elliot, DaisyRec, Bellogín & Said, Petrov & Macdonald) + the per-paper-vs-field-level positioning paragraph — this is the thesis's related work, so it moves FORWARD in prominence. §2.2 (900): method context (SASRec→BLaIR→TIGER/LIGER paragraphs condensed to ~350), the attribution table (§2.1, verbatim), Table 0 (kept; typographic tightening only), the §2.3 novelty-boundary paragraph condensed, Closest-systems I/II/III condensed to ~350 (every named system keeps ≥1 clause; the narrowed-boundary sentences — "our defensible distinction is only …", "we make no cold-start-method comparison", the §2.3(v) apparatus positioning — kept in substance verbatim; full three-block text → S§8), PLUS the two audit-demanded additions: one EASE/late-fusion sentence (Steck 2019; Collins et al. 2025) anchoring E-F, and the §5.8 "Positioning" sentence list condensed to ~60 words anchoring E-G. |
| §3 | The governed-evaluation apparatus | 1,500 | NEW section, promoted from §1(a)–(d), §2's enforcement description, §5 conventions, and §5.6 mechanics. §3.1 (400) pre-declaration + the selection-timing taxonomy (confirmatory / outcome-visible / exploratory — moved here from the §5 conventions paragraph; the "selection timing, not seed count" criterion verbatim in substance). §3.2 (350) fail-closed artifact gate: manifest, 175 cells, per-cell recomputation, retire-don't-grandfather (cite the Table-1a v1-era retirement as the worked example). §3.3 (400) comparator-regeneration harness: the three data-movement shims, "regeneration, never reproduction", environment caveats (mechanics from §5.6; its results table stays in §5.2). §3.4 (350) symmetric self-VOIDing adjudication + the Office V1→V3 episode as the apparatus's demonstration (2–3 sentences + pointers §5.2/S§1; VOID-stands wording intact). |
| §4 | Testbed: protocol, models, and interventions | 1,700 | condensed §3 + §4. §4.1 (350) data + 5-core LLOO protocol + dataset table (§4.1 table kept; role column re-pointed) + 2-sentence dedup/tie disclosure (forensics → S§6) + eval protocol (§3.6). §4.2 (400) architectures: item-feature construction, HSTU-style encoder + parity scope note, SASRec baseline, Φ, 1-sentence NaN-trap + 1-sentence chunked softmax (details → S§6, Cut-CE citation kept). §4.3 (500) added components: TAPE (180) and the causal FIR filter (300) with the **initialization disclosure travelling verbatim** (it is load-bearing for every FIR claim). §4.4 (200) fusion-stage scorers: E-F fused = z(seq)+w·z(EASE) definition, train-only fit, val-only frozen-grid selection; E-G history-centroid text scorer formula — this is the audit-demanded "method placement" for §5.7/§5.8. §4.5 (250) experimental design + statistical conventions: seeds/epochs/hardware, the **fixed-split inference-scope sentence verbatim**, the **randomization disclosure ("Same-numbered seeds do not make the two arms a matched pair…") stated once here as the canonical instance** — everywhere else cross-references it (kills the audit's "repeats caveats" complaint without weakening anything). |
| §5 | Findings under the apparatus | 4,350 | restructured by claim, not chronology (details per subsection below). |
| §5.1 | Development reference numbers (Video_Games; NOT SOTA) | 550 | Table 1 + condensed attribution prose + condensed Table 1b (published HSTU-BLaIR family rows + local port row) + the "+17.5% is architectural, text adds +2.7%" finding + popularity floor line (Table 1a shrinks to that line + manifest pointer). Older-protocols table and the 2026 protocol survey leave (→ §2.2 condensation + S§8). "Not SOTA" sentences kept. |
| §5.2 | Counted per-category comparisons and comparator regeneration | 700 | the MI V2 confirmation (frozen claim wording verbatim; tripwire/deviation compressed to 1 sentence + S§7 pointer), Office V3 (frozen wording verbatim), the §5.6 regeneration results table (5 rows, condensed) + 1-paragraph caveat, Office V1 VOID in 2 sentences (full record S§1; "counts in no claim"/"the VOID stands" intact). |
| §5.3 | The FIR package | 750 | Table 1c + package share prose (condensed), **E-A verbatim result wording**, breadth campaign condensed with the **narrowed frozen wording verbatim** + independent-arm Welch CIs, TFV2 FIR endpoints (IS +0.002131, CDs +0.005770, Holm), comparator ablations in 2 sentences with the §4.3 confound cross-ref. |
| §5.4 | The MI frequency-5 tail case | 700 | TFV2 as the primary evidence: **E1 verbatim**, outcome-visible-not-confirmatory label + a 2-sentence chronology conclusion (full disclosures (i)–(ix) → S§3), the frequency-5-heavy characterization incl. exclude-boundary p = 0.52, the **zero-exposure sentences verbatim** ("zero hits through rank 100…", "no cold-start capability is claimed anywhere in this paper"), cross-dataset non-replication (p = 0.13, descriptive), 2-sentence historical note that the original Table-1d analysis is superseded and archived (→ S§3), Fig. 1 kept. |
| §5.5 | Mechanism probes: thinning titrations | 650 | condensed §5.4 + §5.4.1 + §5.4.2: the double result (head tracks thinning, tail trend-free), Table 1e kept, the §5.4.2 4-row regime table kept, dd = +0.000326 / p = 0.058 suggestive-only downgrade sentences kept, "non-reproduction result, not a confirming one" framing kept, Fig. 2 kept; full ratio-table prose, honesty bounds, floor-artifact resolution, and the spectral retraction note → S§3/S§7 (main keeps a one-line dated retraction pointer). |
| §5.6 | Pre-declared hybrid (E-F) | 450 | current §5.7 lightly condensed: provenance (100), **result frozen wording verbatim**, **published-comparator rows verbatim (all three sentences incl. the VG below-0.0760 row and the ensemble-frame row)**, attribution/scope condensed (80) with the dense-EASE infeasibility scope exclusion kept. |
| §5.7 | Sparse-warm text-fusion study (E-G) — descriptive only | 350 | the **classification paragraph verbatim, first**, then one sentence with the five tail-bin estimates, the "near-threshold sparse-warm redistribution, not cold start" naming + "frequency-0 never moved" + mid/head costs named at equal prominence (one sentence), and the E-G2 registered-path sentence. Everything else (system prose, gate-correction forensics, adjudicator v1/v2/v3 history) → S§5. |
| §5.8 | What the apparatus refused to certify | 400 | NEW synthesis subsection — the thesis payoff: Office V1 VOID (2 sentences, wording intact), TFV2's own outcome-visible demotion, the 2026-07-19 retraction set as a dated list (paired-inference withdrawal, VG equivalence, pooled-z, spectral figure — one line each, full records S§7), and the screening-log summary (asymmetric finding + conn-gate as the five-seed illustrative case incl. its cadence caveat; Table 2 → S§4). |
| §6 | Discussion | 650 | merged §6.1–§6.4: what transfers/what doesn't in ~150 (full Beauty discussion → S§2), engineering takeaways ~60, the non-claims block ~250 (every §6.4 + §7 "Explicit non-claims" sentence kept in substance, deduplicated to one canonical list), open experiments ~150 (E-B/E-C/E-E/E-G2 from EXPERIMENT_PROGRAM, stated as disclosed open work). |
| §7 | Limitations | 700 | current §6.5 condensed: one synthesized list, each bullet kept with its dated correction where present, duplicates of the §4.5 canonical disclosures replaced by cross-references; ADD the E-F/E-G limitation bullets (two-scorer vs single-scorer comparators; EASE infeasibility scope; E-G protocol-deviated, optimizer-seed intervals on one exposed split). |
| §8 | Conclusion | 300 | current §7 condensed; apparatus-first ordering already present; keep the certifies-and-refuses sentence; keep explicit non-claims via pointer to §6 (do not re-list). |
| §9 | Code and data availability | 250 | current §8 condensed to the reproducibility contract + one-command verification + supplement/deposit policy sentence; public-access/deposit chronology → S§7. Update the standing "v1.1.12 follows the synthesis" sentence to remain true at each commit. |
| §10 | Ethics and data governance | 350 | current §10 mildly condensed; the redistribution-basis and sidecar-identifier-surface statements keep their exact meaning (they are audit-negotiated wordings — condense connective tissue only). |
| §11 | Acknowledgments | 30 | keep. |
| — | References | — | unchanged entries; citation-location split handled in §6 step 9 (H9 scope). |
| **Total** | | **≈12,180** | |

**Supplement (new file `PAPER_SUPPLEMENT.md` — see §6 for naming/build):**

| Supp § | Title | Content (verbatim moves unless noted) |
|---|---|---|
| S§0 | Concordance and citation guide | old§→new§→supplement map (mandatory: frozen docs — preregs, adjudicator outputs, audit responses, CANONICAL ledger — cite old § numbers and are never edited; this table is the resolution mechanism) |
| S§1 | Office_Products V1 campaign record (VOID) | current Appendix A.0, verbatim, VOID banner intact |
| S§2 | Superseded Beauty_and_PC material | current Appendix A.1–A.3 + §6.1/§6.2 discussion |
| S§3 | Tail-case and titration forensic record | Table 1d + its three bounding points, cohort-defect paragraph, TFV2 process disclosures (i)–(ix), §5.4.1 + §5.4.2 full text incl. honesty bounds and floor-artifact resolution, the retracted spectral-analysis record |
| S§4 | Screening log | Table 2 + full per-probe prose + power paragraphs |
| S§5 | E-G sparse-warm full record | §5.8 system/provenance, integrity-gate correction, adjudicator v1/v2/v3 history, "what this is and is not" full text — **the classification paragraph appears verbatim here too** |
| S§6 | Preprocessing and environment forensics | pre-core dedup counts, timestamp-tie policies, NaN-trap detail, chunked-softmax pseudocode, pinned-environment parity detail (from §5.6 caveats) |
| S§7 | Correction ledger and campaign chronology | all dated retraction/correction/erratum notes collected (paired-inference withdrawal, VG equivalence, pooled-z, spectral, 2-seed trough, Table-1a retirement, prereg deviation E3), tripwire/re-execution narrative, public-access + deposit chronology from §8 |
| S§8 | Extended comparability survey | older-protocols table + comparability caveat, the §5.1 "2026 semantic-ID / generative retrieval line" survey (incl. SILLM4Rec exclusion), Closest-systems I–III full text |

The supplement is canonical-markdown, artifact-gated exactly like the main file (see §6 step 1), and is submitted to TORS as supplementary material; expected size ≈11–13k words (unconstrained).

---

## 3. RELOCATION MAP

Destinations: `main §X` (new numbering above) / `S§Y` / `cut` (delete-as-redundant — meaning preserved elsewhere). "condense" = shorten without meaning change; frozen wordings never condensed.

| # | Current block (heading or first words) | Destination |
|---|---|---|
| 1 | Title + Authors + reader-edition note | keep (front matter; reader-edition note updated to name the supplement) |
| 2 | Abstract | main Abstract (rewrite ≤200w, narrowing only) |
| 3 | §1 paras 1–2 ("Sequential recommendation models predict…", "Recent benchmarks consolidate…") | main §1 (condense to ~120w) |
| 4 | §1 para 3 ("This paper's lead contribution, however, is methodological…" incl. (a)–(d)) | split: overview → main §1; mechanics → main §3.1–§3.4 |
| 5 | §1 research questions + contributions 1–3 | main §1 (condense; contribution list reordered apparatus-first) |
| 6 | §1 closing ("Our claimed additions are deliberately small…") | main §1 (keep, ~60w) |
| 7 | §2 per-system paragraphs (SASRec…BERT4Rec…SBERT…UniSRec/ZESRec/RecFormer…BLaIR…TIGER…LIGER…AR2023) | main §2.2 (condense to ~350w) |
| 8 | §2 "Evaluation practice and reproducibility…" paragraph | main §2.1 (condense to ~300w; prominence raised) |
| 9 | §2.1 Attribution table | main §2.2 (keep verbatim) |
| 10 | §2.2 "Our additions" bullet list | cut as list (each bullet's content survives in §1 contributions, §3.2 retirement example, §4.2 engineering lines, §5 findings) |
| 11 | §2.3 boundary paragraph + **Initialization disclosure (2026-07-19)** | boundary → main §2.2 (condense); initialization disclosure → main §4.3 **verbatim** |
| 12 | Table 0 (novelty boundary) | main §2.2 (keep; contingency: S§8 if >35pp, boundary sentences stay) |
| 13 | Closest systems I / II / III paragraphs | main §2.2 (condense to ~350w total, every system named) + S§8 (full text) |
| 14 | §3.1 preprocessing steps 1–5 + protocol-match para | main §4.1 (condense ~150w) |
| 15 | §3.1 "Pre-core deduplication" + "Timestamp-tie policies" paragraphs | S§6 (main §4.1 keeps 2-sentence disclosure) |
| 16 | §3.2 model architecture (item features, HSTU-style headline, SASRec baseline) | main §4.2 (condense ~250w; parity scope note kept) |
| 17 | §3.3 projection Φ | main §4.2 (~60w) |
| 18 | §3.4 right-padding/NaN trap | main §4.2 one sentence; detail → S§6 |
| 19 | §3.5 chunked-full-softmax + pseudocode | main §4.2 ~80w prose (Cut-CE citation kept); pseudocode → S§6 |
| 20 | §3.6 evaluation protocol | main §4.1 (~100w) |
| 21 | §3.7 TAPE definition | main §4.3 (condense ~180w) |
| 22 | §3.7 causal FIR definition + leak-free construction + narrow-boundary sentences | main §4.3 (condense ~300w; boundary sentences kept in substance) |
| 23 | §4.1 dataset table + role column + trailing prose | main §4.1 (keep table; roles re-pointed to new §s) |
| 24 | §4.2 baselines list | main §4.2 (keep) |
| 25 | §4.3 experimental design incl. **fixed-split inference-scope sentence** | main §4.5 (condense; scope sentence **verbatim**) |
| 26 | §4.4 training details/hardware | main §4.5 (~60w) |
| 27 | §5 "Statistical reporting conventions" paragraph | split: selection-timing taxonomy → main §3.1; remainder → main §4.5 (condense ~120w) |
| 28 | §5.1 Table 1 + component-attribution prose (incl. DECOMP/DECOMP5 parenthetical) | main §5.1 (Table 1 kept; prose condensed ~300w; DECOMP cross-check compressed to 2 sentences) |
| 29 | Table 1a + v1-era retirement note | main §5.1 popularity-floor line + §3.2 retirement example; full note → S§7 |
| 30 | Table 1b + surrounding comparator prose + "provides/does NOT provide" lists | main §5.1 (condense; lists → 2 sentences) |
| 31 | "Older published baselines on different protocols" table + comparability caveat | S§8 (main §5.1 keeps 1 sentence) |
| 32 | "2026 semantic-ID / generative retrieval line" paragraph (i)–(iv) + SILLM4Rec + UniSGR/DIGER/ACERec | main §2.2 (~150w summary, no comparative claims) + S§8 (full) |
| 33 | "What we *can* claim" bullets | main §5.1 (merge, ~60w) |
| 34 | §5.2 opening + Table 1c + package-share prose | main §5.3 (condense ~300w; Table 1c kept) |
| 35 | §5.2 "Pre-declared matched-arm FIR replication (E-A)" paragraph | main §5.3 (**result wording verbatim**; setup condensed) |
| 36 | §5.2 "Pre-declared breadth" paragraph | main §5.3 (condense; **narrowed frozen wording verbatim**; paired-interpretation-withdrawn correction kept) |
| 37 | §5.2 "TFV2 independent-arm replication" (FIR endpoints) | main §5.3 (~80w) |
| 38 | §5.2 "Comparator ablations (audit-requested)" | main §5.3 (2 sentences; confound caveat kept via §4.3 cross-ref) |
| 39 | §5.2 "Pre-declared confirmation vs the published per-category reference" | main §5.2 (**supported-claim wording verbatim**; tripwire/deviation → 1 sentence + S§7) |
| 40 | §5.2 Office V1 paragraph ("descriptive only; superseded…") | main §5.2 (2 sentences) + S§1 |
| 41 | §5.2 Office V3 paragraph ("PASSED") | main §5.2 (**frozen wording verbatim**; mechanics condensed) |
| 42 | §5.3 intro + **randomization disclosure** | disclosure → main §4.5 **canonical instance**; intro → main §5.4 (condense) |
| 43 | Table 1d + bounding points 1–3 | S§3 (main §5.4 keeps 2-sentence historical note) |
| 44 | §5.3 "Cohort-definition defects" paragraph | main §5.4 ~80w summary; full → S§3 |
| 45 | §5.3 "Pre-declared repaired-estimand campaign (TFV2)" paragraph | main §5.4 (**E1 verbatim**, labels + zero-exposure sentences + frequency-5-heavy characterization kept; condense the rest) |
| 46 | §5.3 "TFV2 campaign-process disclosures (i)–(ix)" | S§3 (main §5.4 keeps the (vii) conclusion in 2 sentences: earliest Bitcoin attestation postdates first result ⇒ outcome-visible, not confirmatory) |
| 47 | Fig. 1 (+ dual caption lines) | main §5.4 (keep; caption §-refs renumbered only) |
| 48 | §5.4 titration prose + Table 1e + "Methodological honesty" framing | main §5.5 (condense ~350w; Table 1e kept; "non-reproduction result" framing kept) |
| 49 | §5.4.1 ratio table + prose + candidate-explanation paragraph | main §5.5 (~120w + keep 3-row ratio table optional) ; full prose → S§3 |
| 50 | §5.4.2 user-mode titration + 4-row table + honesty bounds + **Refined verdict + spectral retraction** | main §5.5 (~200w + 4-row table; dd/p=0.058 downgrade kept); bounds + retraction → S§3/S§7 (main keeps one-line dated retraction pointer) |
| 51 | Fig. 2 | main §5.5 (keep) |
| 52 | §5.4.2 "Provenance/honesty" blockquote | S§3 (main inherits via §4.5 cross-ref) |
| 53 | §5.5 screening-log prose + power paragraphs + Table 2 + conn-gate discussion | main §5.8 summary (~250w incl. conn-gate + cadence caveat); Table 2 + full prose → S§4 |
| 54 | §5.6 harness description ("Late in this work we succeeded…") | main §3.3 (mechanics, condensed) |
| 55 | §5.6 results table (5 rows) + "regenerates locally" + Office-floor-resolution paragraphs | main §5.2 (condensed table + ~120w) |
| 56 | §5.6 "Caveats (why these are regenerations, not reproductions)" | main §5.2 ~60w + §3.3; pinned-parity detail → S§6 |
| 57 | §5.7 E-F entire section | main §5.6 (see §4 below; frozen wordings verbatim) |
| 58 | §5.8 E-G entire section | main §5.7 (classification verbatim + summary; rest → S§5; see §4 below) |
| 59 | §6.1 + §6.2 (cross-pipeline transfer discussion) | S§2 (main §6 keeps ~2 sentences) |
| 60 | §6.3 engineering takeaways | main §6 (~60w) |
| 61 | §6.4 "What we don't claim" | main §6 non-claims block (all sentences' meaning kept, deduplicated) |
| 62 | §6.5 Limitations (14 bullets) | main §7 (condense ~700w; add E-F/E-G bullets; §4.5-duplicates become cross-refs) |
| 63 | §7 Conclusion + "Explicit non-claims" | main §8 (condense ~300w; non-claims pointer to §6) |
| 64 | §8 Code and Data Availability (contract + deposit policy) | main §9 (condense ~250w) |
| 65 | §8 "Public-access status…" chronology paragraph | S§7 (main §9 keeps repo URL + one-command verify + current-tag sentence) |
| 66 | §9 Acknowledgments | main §11 (keep) |
| 67 | §10 Ethics and Data Governance | main §10 (condense ~350w; negotiated wordings' meaning intact) |
| 68 | References (75+ entries) | keep; per-document citation scope resolved in build (see §6 step 9) |
| 69 | Appendix A.0 (Office V1 record incl. floor-anomaly resolution + HSTU-BLaIR check) | S§1 verbatim |
| 70 | Appendix A intro + A.1 (20-variant scan) + A.2 + A.3 | S§2 verbatim |

---

## 4. E-F / E-G PLACEMENT

**E-F (counted; W-H-POS on MI/IS/VG) — stays in main, with full method/related-work/limitations placement (the audit's condition for keeping it):**
- **Method:** new §4.4 defines the fusion stage (per-user fused = z(seq) + w·z(EASE); EASE fit on train split only; (l2, w) selected on validation only from frozen grids; test evaluated once at the selected pair). ~120 words, lifted from current §5.7 "Provenance and system".
- **Related work:** §2.2 gains one sentence: EASE (Steck 2019) as the closed-form item-item scorer and ID/text-complementarity ensembling (Collins et al. 2025) as the adjacent line; contribution stated as measured complementarity under the governed protocol, not architecture.
- **Results:** main §5.6, ~450 words. The frozen result sentence and all three published-comparator sentences appear **verbatim** (see §5 below), including the unfavorable VG row (0.07031 < 0.0760) and the ensemble-frame row (0.04557, "comparable only to other ensembles"). The disclosed monitoring/no-no-interim-clause sentence is kept in condensed form (it bounds the evidence class).
- **Limitations (§7):** two bullets added — (i) the hybrid is a two-scorer system compared against single-scorer single-run published values (point-estimate comparisons only, per the frozen wording); (ii) dense EASE is infeasible at Office/CDs/Beauty catalog sizes (pre-declared scope exclusion).

**E-G (outcome-visible, protocol-deviated, descriptive-only) — short descriptive block in main; full record in supplement; the classification paragraph travels with EVERY mention:**
- **Main §5.7 (~350 words), in this order:** (1) the **classification paragraph verbatim** (the whole "Classification (audit 2026-07-23 15:59, accepted). The campaign completed 25/25 runs, but it is classified **outcome-visible and protocol-deviated** …" paragraph, including (a)/(b)/(c) and the E-G2 sentence); (2) one sentence of descriptive tail-bin estimates (+0.00217 MI / +0.00243 IS / +0.00337 VG / +0.00114 Office / +0.00481 CDs, optimizer-seed intervals on one exposed split); (3) the naming sentence — "near-threshold sparse-warm redistribution", frequency-0 never moved, mid/head means negative in every category (equal prominence, one sentence); (4) pointer to S§5 and to E-G2 as the sole path to counted status.
- **Method:** §4.4 gains the one-formula description of the history-centroid text scorer (fused = z(seq) + w_e·z(EASE) + w_t(bin)·z(text); w_t per TRAIN-frequency bin, monotone nonincreasing; ~60 words).
- **Related work:** §2.2 gains the condensed §5.8 "Positioning" sentence (evaluation-time content fusion for sparse items is a crowded neighborhood — Wang 2024, Collins 2025, TedRec, SimRec, Lichtenberg 2025, Wang 2025, Liu 2023 — no architectural novelty claimed).
- **Limitations (§7):** one bullet — E-G is protocol-deviated and outcome-visible; its intervals are optimizer-seed intervals conditional on one fixed, repeatedly exposed split; nothing counted; replication path is E-G2.
- **Supplement S§5:** everything else from current §5.8 (system/provenance, integrity-gate correction, adjudicator v1/v2/v3 hashes, "what this is and is not" full text) — **with the classification paragraph repeated verbatim at the top of S§5**, so no reader of either document can meet E-G numbers without the classification. Rule for the executor: any future mention of an E-G estimate in any document must sit within one paragraph of the classification or an explicit "(descriptive only; protocol-deviated — §5.7/S§5)" tag.
- Abstract/§1: E-G appears at most as "a five-category descriptive study whose own pre-declaration was violated and which is counted in no claim" — never with bare numbers.

**Rejected alternative (recorded):** moving E-F to the supplement too. Rejected because E-F is a *counted* pre-declared campaign in the canonical claim ledger (CANONICAL_SUBMISSION item 2 of the post-v1.1.11 additions; README claim list) — burying a counted claim in a supplement would misrepresent the claim set; the audit's complaint was placement, not existence.

---

## 5. CLAIM-BOUNDARY CHECK — wordings the restructure must NOT alter in meaning

The executor locates each by its opening words (grep-able in `PAPER_SUBMISSION.md` today); each must survive verbatim (modulo §-number cross-references inside them, which may be re-pointed, and the E-F terminology note already disclosed in §5.7). Claims may only narrow; none of these may be condensed.

**Mandated set:**
1. **Counted comparison 1 (MI V2, §5.2):** "fresh multi-seed means and seed-level confidence intervals exceed the published…" (the italicized supported-claim sentence, through "…ruling out an easier split").
2. **Counted comparison 2 (Office V3, §5.2):** "a per-category point-estimate comparison against the published 0.0271 and its…" (through "…not a general-SOTA claim of any kind." — the V1-VOID-stands sentence follows it and also survives).
3. **E-A W-POS (§5.2):** "in the nonsingular matched-arm replication (E-A, 8 seeds/arm, shared verified…" (through "…at the frozen V2 configuration."), plus its two scope sentences "This supports a FIR-specific component…" / "…does not retroactively decompose the historical package estimate".
4. **E-F W-H-POS result (§5.7):** "Under the pre-declared fresh-seed replication (PREREG_HYBRID_V1, 5 seeds), late z-score fusion…" (through "…never to any published comparator).").
5. **E-F published-comparator rows (§5.7), three sentences:** "The fused system's five-fresh-seed mean test NDCG@10 on Musical_Instruments, 0.04399, exceeds…"; "On Video_Games the fused five-fresh-seed mean, 0.07031, remains below the published…"; "A five-checkpoint ensemble of the same frozen stack, fused with EASE…" (ensemble frame clause included).
6. **E-G classification (§5.8):** "The campaign completed 25/25 runs, but it is classified **outcome-visible and protocol-deviated**…" (the full paragraph through "…(EXPERIMENT_PROGRAM E-G2).").

**Additional guarded wordings (frozen or audit-negotiated; treat identically):**
7. **FIR-breadth narrowed frozen wording (§5.2):** "the causal-FIR-filter arm's 5-seed improvement over the no-filter arm on that category…" (the italic clause + "an internal same-seed contrast of the FIR-plus-initialization/optimizer package; nothing broader, no SOTA language, no comparator statement").
8. **TFV2 primary endpoint (§5.3):** "E1 — MI positive-frequency-tail NDCG@10, text − ID: +0.000420, t = 3.79…" through "PASS under Holm", and its label "outcome-visible, not confirmatory" wherever TFV2 is invoked.
9. **Office V1 VOID statements (§5.2 / A.0):** "The V1 Office campaign counts in no claim." and "the VOID stands" / "The VOID therefore stands, deliberately".
10. **Zero-exposure / cold-start non-claim (§5.3):** "zero-exposure bin is degenerate at exactly 0.0 in both arms…" incl. "zero hits through rank 100" (occurs twice — §5.3 and Closest-systems III; both survive) and "no cold-start capability is claimed anywhere in this paper".
11. **Randomization disclosure (§5.3):** "Same-numbered seeds do not make the two arms a matched pair." (canonical instance moves to §4.5; meaning intact).
12. **Fixed-split inference scope (§4.3):** "the training seed is the only randomized unit; every interval in this paper quantifies…".
13. **E-G naming sentences (§5.8):** "The finding's correct name is a near-threshold sparse-warm redistribution…" and "not one frequency-0 target changed in any of the 25 runs".
14. **Initialization disclosure (§2.3):** "with the delta-kernel and gate g=0 initialization, both task gradients are exactly zero…" (travels to §4.3).
15. **Every "not SOTA" non-claim sentence** (§5.1, §5.2 Office V3 wording, §7 non-claims, README-mirrored): SOTA tokens may exist **only** inside these negation contexts — the `paper_tex/scan_pdf.py` hygiene rule already enforces this; the restructure adds no new SOTA token anywhere (this plan itself uses the token only inside non-claim descriptions).

Mechanical enforcement (added in step 1 below): a `frozen_wordings.txt` list containing the anchor strings above + a checker that fails the build if any anchor is absent from the doc-set (main + supplement) or if E-G estimate tokens appear in a paragraph without a classification tag.

---

## 6. EXECUTION SEQUENCE (one commit per step; strict gate green at every commit)

Standing rules for every step: never edit frozen files (`PREREG_*`, `*_RESULTS.md`, adjudicator outputs, audits/responses, results JSONs); md is canonical and the tex mirror is regenerated, never hand-divergent (`VENUE_PLAN.md`); each commit ends with `python _bestrec_run/rebuild_hstu_submission.py --strict` exit 0 + `paper_tex/build.sh` PASS (H1–H10 + hygiene scan) + reader render; moves are verbatim-first — condensation happens only in the commit that owns that block, never silently in passing.

1. **Commit 1 — supplement scaffold + gate scope + frozen-wording tripwire.** Create `PAPER_SUPPLEMENT.md` (title, S§0 concordance stub, empty S§1–S§8 with headings). Extend the gated doc-set to [`PAPER_SUBMISSION.md`, `PAPER_SUPPLEMENT.md`] in `_bestrec_run/build_hstu_tables.py` (cell location may be either doc; total-cell invariant unchanged at 175+), `render_paper_pdf.py` (renders `PAPER_SUPPLEMENT.pdf`), `rebuild_hstu_submission.py --strict`, and the numeral-fidelity multiset check (union of both docs vs both PDFs). Add `_bestrec_run/frozen_wordings.txt` + `check_frozen_wordings.py` (fails on any missing anchor from §5 above; fails on E-G numerals outside a classified paragraph) and wire it into the strict wrapper. Register the supplement in `CANONICAL_SUBMISSION.md` (canonical doc-set), `README.md` layout table, `VENUE_PLAN.md` typesetting rules. Gate must pass with the supplement still empty.
2. **Commit 2 — move the appendices.** Appendix A.0 → S§1; Appendix A/A.1–A.3 → S§2; §6.1–§6.2 → S§2 tail. Leave forward pointers at the old positions ("moved to supplement S§1/S§2"); keep old main-section numbering untouched this commit. Update the tex mirror: `sections/appendix-a0.tex` / `appendix-a.tex` content moves into a new `paper_tex/supplement-shared.tex` + driver `supplement.tex` → `PAPER_TORS_SUPPLEMENT.pdf`; `emit_latex_tables.py` rendered-at map updated for `office_confirmation.tex` and `tableA1.tex`.
3. **Commit 3 — move the screening log.** Table 2 + §5.5 full prose → S§4; write the ~250-word main summary in place (asymmetry finding + conn-gate five-seed case + cadence caveat pointer). Emitter: `table2.tex` renders in the supplement.
4. **Commit 4 — move tail-case forensics.** Table 1d + bounding points + cohort-defect paragraph + TFV2 process disclosures (i)–(ix) → S§3; rewrite §5.3 in place around TFV2 (E1 verbatim; outcome-visible label + 2-sentence (vii) conclusion; zero-exposure sentences verbatim). Emitter: `table1d.tex` → supplement.
5. **Commit 5 — move titration detail.** §5.4.1 + §5.4.2 full prose, honesty bounds, provenance blockquote, spectral-retraction record → S§3/S§7; condensed mechanism subsection written in place (Table 1e + 4-row regime table + dd/p=0.058 downgrade kept in main). Emitter: `table541.tex` (if its prose home moves, keep the 3-row ratio table in main OR move it — decide by page pressure; default keep in main), `table542.tex` stays in main.
6. **Commit 6 — move E-G detail.** Current §5.8 system/gate-correction/adjudicator-history prose → S§5 (classification paragraph duplicated verbatim at S§5 top); main block reduced to the 350-word §4-specified form. `check_frozen_wordings.py` proves the classification anchor exists in both docs.
7. **Commit 7 — move remaining forensics/chronology.** §3.1 dedup + tie-policy paragraphs, §3.4/§3.5 details + pseudocode, §5.1 older-protocols table + 2026 protocol survey, Table 1a retirement note, §5.6 pinned-parity caveat detail, §8 public-access chronology, and the collected dated correction notes → S§6/S§7/S§8 (with one-line dated pointers left in main). Emitter: `table_older_baselines.tex` → supplement.
8. **Commit 8 — restructure and renumber the main body.** Build the new skeleton of §2: §1 Introduction (condense), §2 Related work (merge §2/§2.1/§2.3 + the E-F/E-G related-work sentences), §3 Apparatus (new, from §1(a)–(d) + §5-conventions taxonomy + §5.6 mechanics), §4 Testbed (from §3/§4 + new §4.4 fusion scorers + §4.5 canonical disclosures), §5 Findings reordered (§5.1 VG, §5.2 counted+regeneration, §5.3 FIR, §5.4 tail, §5.5 titrations, §5.6 E-F, §5.7 E-G, §5.8 refusals), §6 Discussion (merge §6.1–§6.4 remnants), §7 Limitations (from §6.5 + new E-F/E-G bullets), §8 Conclusion, §9 Availability, §10 Ethics, §11 Acknowledgments; rewrite the Abstract (≤200w). Re-point every §-cross-reference in both docs; fill S§0 concordance (old§ → new§/S§). Run the frozen-wording checker; run a word-count report (target band 9,000–13,000 body words) and commit it as `_bestrec_run/wordcount_report.txt`.
9. **Commit 9 — regenerate the tex mirror end-to-end.** Re-run the documented pandoc splitter over the restructured md → new `sections/*.tex` set; update the BUILD_NOTES file map; `emit_latex_tables.py` rendered-at map finalized for both drivers; **H9 citation gate scope = main + supplement union** with per-doc bibliographies (both drivers share `references.bib`; entries cited only in supplement text — e.g., the retraction-record refs Baik/Marchenko–Pastur/Gavish, He 2016, MELT/DropoutNet/CLCRec, and any survey-only 2026 entries — must be cited by real commands in `supplement.tex`, and H9 must fail on any entry cited in neither doc and on any `\nocite{*}`). Compile both targets + supplement; hygiene-scan **all three PDFs** (main manuscript, acmsmall preview, supplement); record the acmsmall page count and verify 20–35pp (apply §2 contingency cuts if not).
10. **Commit 10 — cross-file consistency sweep + full ritual.** Update section pointers and supplement references in `README.md`, `CANONICAL_SUBMISSION.md`, `COVER_LETTER_TORS.md` (declare the supplement as submitted supplementary material; title unchanged verbatim), `PLAIN_LANGUAGE_COMPANION.md`, `EXPERIMENT_PROGRAM.md` (manuscript-§ pointers only; frozen preregs/audits untouched — S§0 concordance covers them). Full ritual: render CLEAN, `build.sh` PASS, manifest `--regen` + commit together, strict exit 0, frozen-wording checker PASS.
11. **Post-synthesis (maintainer step, outside this plan):** cut deposit `v1.1.12` at the stabilized content boundary per the §8/README deposit policy (the deposition gate already refuses stale rebuilds), with the from-zero public-clone verification at the new tag.

Risk notes for the executor: (i) the emitter locates tables by **header fingerprint** — if a table caption's bold lead-in is condensed, update the fingerprint in the same commit or the build fails closed (that is the designed behavior; do not weaken the check); (ii) the 175-cell count is the strict build's own output and may legitimately grow with new evidence — the invariant is 0 MISMATCH / 0 UNTRACEABLE / all families sourced across the doc-set, not the literal 175; (iii) figure files are untouched — only caption §-references change (commit 8); (iv) do not touch `retracted_archive/`, OTS files, or anything hash-pinned in `RELEASE_MANIFEST.json` except via `--regen` for the two canonical md/PDF entries that legitimately change.

---

*End of plan. Executor questions that require maintainer judgment: contingency cut activation (§2), Table-541 main-vs-supplement default (step 5), and the deposit timing (step 11). Everything else is specified.*
