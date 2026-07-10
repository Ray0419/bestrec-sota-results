# Strict Full Method and Paper Audit

Date: 2026-07-10

Scope: This audit covers publication readiness beyond novelty and originality: experimental protocol, fairness, statistical validity, reproducibility, artifact provenance, manuscript consistency, claim hygiene, data/code release, and presentation. It treats the package as if submitted to a selective systems/ML/recommender venue by a skeptical reviewer looking for any reason to reject.

## Verdict

Reject the current paper/package as publication-ready.

The main reason is not one isolated bug. The problem is that the repository currently contains multiple overlapping publication candidates, stale generated artifacts, hand-written paper tables, protocol deviations, and claim-scope ambiguity. Some individual result artifacts are numerically traceable, and the isolated LC2C SOTA lab package is much closer to defensible for a narrow cold-item full-catalog claim. But the current submission package, as a whole, is not yet clean, canonical, or audit-proof enough for a top venue.

I would not approve broad SOTA claims. I would only consider a narrow claim after the fixes below are completed and re-audited.

## What Passed

1. The full-catalog ranking implementation in `_bestrec_run/run_sasrec_sbert.py` appears directionally correct for the checked path. Test ranking scores the target against the full item catalog, masks user training history, and also masks the validation item when evaluating the test target.

2. The V2 Musical_Instruments gated result values were locally recomputed from JSON artifacts:

   - k16 fresh EXEC2 NDCG@10 values: 0.0412647461, 0.0410805520, 0.0414740849, 0.0415161932, 0.0422605757
   - k16 mean: 0.04151923
   - k16 95 percent t lower bound: 0.04096097
   - k8 mean: 0.04120308
   - k8 95 percent t lower bound: 0.04083214
   - `n_eval`: 57439 users

   This supports that the reported narrow V2 point estimate is not an obvious arithmetic fabrication.

3. The sidecar manifest for the V2 run was checked locally. Sidecar row counts match `n_eval=57439`, and no hash/size/row-count errors were observed in the manifest audit.

4. The LC2C SOTA lab artifacts are closer to a publication-grade package than the root paper. Its public gate records a narrow approval for cold-item full-catalog ranking, with positive margins against listed baselines on Beauty, Fashion, Instruments, and Books.

These passes do not make the whole submission acceptable. They only identify parts that are salvageable.

## Blocking Findings

### 1. No Single Canonical Submission Exists

The repository currently contains at least four different publication tracks:

1. `PAPER_DRAFT.md`: HSTU/FIR/tail-law manuscript.
2. `_bestrec_sota_lab/paper_draft/lc2c_retrieval_ltr_paper.md`: LC2C Retrieval LTR cold-item manuscript.
3. `_paper_gen/build_paper_full.py` and `BEST_Rec_v4_Full_Paper.pdf`: old BEST-Rec v4 / LC2C / EASE paper.
4. `_bestrec_run/tables.json` and `_bestrec_run/results_manifest.json`: old LC2C-era generated artifacts, including `sota_claim_allowed: false`.

A reviewer cannot tell which paper is the actual submission. This is a fatal packaging and provenance problem. A top venue submission must have one canonical manuscript, one artifact graph, one result manifest, and one set of claims.

Required fix: choose exactly one canonical paper and move all other papers into clearly labeled archive or appendix folders. The build script, manifest, tables, figures, PDF, and claim checklist must all point to that one paper only.

### 2. Paper Tables Are Not Fully Generated From Current Manifested Artifacts

The root `PAPER_DRAFT.md` contains hand-written Markdown tables and prose values. The active `_paper_gen/build_paper_full.py` is still an older BEST-Rec v4 generator and does not build the current HSTU/FIR/tail-law manuscript from current HSTU artifacts.

This fails the publication audit because there is no enforceable link from result files to paper cells. A typo, stale number, or cherry-picked value could enter the paper without detection.

Required fix: create current-paper artifacts such as:

- `hstu_results_manifest.json`
- `hstu_results_final.json`
- `hstu_significance.json`
- `hstu_tables.json`
- `hstu_figures_manifest.json`

The paper build must fail if any empirical value is absent from these files.

### 3. The Root Manuscript Contains Internal Contradictions

The root draft says the evaluation covers two Amazon Reviews 2023 categories, Video_Games and Beauty_and_Personal_Care, but later sections rely on Musical_Instruments as a central result and tail-law evidence.

The manuscript also contains stale drafting notes, including active notes that rungs are being filled concurrently and optional seed instructions. A submitted paper cannot contain this mixture of final claims and live lab notes.

Required fix: remove all draft notes, changelog material, TBD author placeholders, and obsolete text. Then perform a line-by-line consistency pass on dataset names, seed counts, metrics, claims, and limitations.

### 4. HSTU Fidelity Is Not Proven

The implementation contains an unresolved specification conflict:

- The HSTU docstring describes attention using a `1/sqrt(dh)` scale and row-count normalization.
- Later implementation comments say faithful HSTU uses no `1/sqrt(d)` and no row normalization.
- The code still divides by sequence length in the attention path.

This is not a harmless comment mismatch if the paper compares against or claims a specific HSTU architecture. It creates uncertainty about whether the implemented model is faithful HSTU, a modified HSTU, or an accidental hybrid.

Required fix: add an equation-level implementation appendix and unit tests that verify the exact attention formula. If the implementation differs from canonical HSTU, rename it honestly and stop calling it faithful HSTU.

### 5. External Comparator Limitation Is Too Central

The current root package says the direct HSTU-BLaIR comparator could not be run because of environment incompatibilities. That is a serious limitation because the paper's central comparison depends on whether the new method beats or explains a strong contemporary comparator.

A top reviewer may accept an environment limitation only if the paper narrows its claim accordingly. It is not enough to say "we could not run it" while still implying SOTA-level comparison.

Required fix: either run the comparator in a compatible environment, obtain author-provided results on the exact split, or remove any claim that depends on outperforming that comparator.

### 6. Statistical Evidence Is Uneven Across Claims

Some claims use five fresh seeds and clear lower bounds. Other parts of the paper, including negative maps, titration claims, and tail-law claims, appear to rely on fewer seeds, single-seed evidence, or exploratory evidence.

A reviewer will not accept a strong causal or mechanistic story if the evidence base changes quietly between claims.

Required fix:

- Label each result as confirmatory or exploratory.
- Report sample unit for every p-value.
- Apply correction families explicitly.
- Provide per-user paired tests where appropriate.
- Provide clustered bootstrap intervals for primary deltas.
- Do not use single-seed negative maps as decisive systematic evidence.

### 7. The Negative-Result Map Is Underpowered

The draft explicitly suggests that single-seed evidence is sufficient for the negative map. That is not publication-grade for claims about which components do or do not work.

Required fix: either downgrade the negative map to anecdotal/exploratory evidence or rerun the major negative findings with enough seeds and confidence intervals to support the claim.

### 8. Reproducibility Is Not Yet Bulletproof

The V2 run script hardcodes a Windows virtualenv path and uses `set -u` rather than a stricter shell failure mode. It also skips existing outputs by default. The gated V2 JSONs were generated before embedded `user_records_sha256` and `code_sha256` fields were added, so the primary result files are not self-contained.

The errata discloses these problems, which is good. But disclosure is not the same as a clean reproducibility package.

Required fix:

- Use portable commands such as `uv --project _bestrec_run run python ...`.
- Use strict failure handling in shell scripts.
- Add a `--resume` flag if skipping outputs is desired; otherwise default to clean regeneration.
- Regenerate final confirmatory outputs with embedded code hash, data hash, sidecar hash, command, timestamp, environment, and git commit.
- Add a clean rebuild test from raw/cache inputs to PDF.

### 9. Data and Artifact Release Is Incomplete For Submission

The paper mentions code/data availability but does not yet provide a clean archival release path for all current claims. The root draft mentions precomputed text caches only for Video_Games and Beauty_and_Personal_Care, while current claims also use Musical_Instruments.

Required fix: create a release manifest with exact dataset preprocessing scripts, split files, text caches, result JSONL files, checksums, and license notes. For large records, use a stable DOI-backed archive such as Zenodo or OSF, not only local paths or branch artifacts.

### 10. LC2C SOTA Lab Claim Has A Fairness Caveat

The LC2C Retrieval LTR package is the closest to a defensible narrow publication claim, but the method uses DropoutNet-derived evidence as a feature/fallback while also comparing against DropoutNet. This is not automatically invalid: learned fusion systems often compare against their component models. But it changes the claim.

The correct claim is not "we independently beat DropoutNet." The correct claim is closer to:

> A validation-trained full-catalog cold-item fusion/reranking system, using DropoutNet and text/content evidence as inputs, improves over its component baselines under the stated protocol.

Required fix: put this caveat in the abstract/intro/limitations. Add a no-DropoutNet ablation and a fair learned-ensemble baseline with similar feature access.

### 11. Broad SOTA Is Not Supported

The current artifacts can at most support narrow claims:

- HSTU/FIR track: narrow Musical_Instruments or specific-tail-effect claims, if artifact provenance and comparator limitations are fixed.
- LC2C SOTA lab track: narrow cold-item full-catalog ranking claims, if framed as DropoutNet-assisted learned fusion.

They do not support broad recommender-system SOTA, broad warm-start SOTA, broad cold-start SOTA across all realistic settings, or top-level claims about replacing modern sequential recommenders.

Required fix: remove broad SOTA language unless every required comparator, setting, and statistical gate is satisfied.

### 12. Presentation Is Not Submission-Clean

The root draft includes TBD authors, changelog/status text, drafting notes, and possible encoding artifacts in terminal rendering. Even if some encoding issues are only PowerShell display artifacts, the PDF must be rendered and inspected.

Required fix: render the final PDF from the canonical source and visually inspect it. Verify typography, table alignment, references, equations, figure labels, author block, and absence of draft notes.

### 13. Threats To Validity Are Too Mild

The paper needs a sharper limitations section. It should plainly state:

- Which results are confirmatory.
- Which results are exploratory.
- Which baselines could not be run.
- Which claims depend on one dataset or one product category.
- Whether the method uses any baseline model as an input feature.
- Whether preprocessing differs by even one interaction from the external comparator.

Required fix: rewrite limitations as an audit-quality section, not a soft disclaimer.

## Required Repair Path

### Path A: If The Canonical Paper Is The HSTU/FIR Manuscript

1. Move all LC2C and BEST-Rec v4 paper artifacts out of the canonical submission path.
2. Create a current HSTU/FIR artifact graph and manifest.
3. Regenerate all tables and figures from that manifest.
4. Resolve HSTU formula fidelity with code tests and appendix equations.
5. Fix all dataset-count contradictions.
6. Remove all stale draft notes.
7. Run or remove the central external comparator claim.
8. Separate confirmatory and exploratory results.
9. Add correction-aware statistics for all primary claims.
10. Render and inspect the final PDF.

Until this is done, I would reject the HSTU/FIR paper.

### Path B: If The Canonical Paper Is The LC2C Retrieval LTR Cold-Item Paper

1. Move the LC2C SOTA lab paper into the canonical submission path.
2. Frame the contribution as a narrow full-catalog cold-item learned-fusion/reranking method.
3. State prominently that DropoutNet evidence is used as an input/fallback.
4. Add no-DropoutNet and equal-access ensemble ablations.
5. Keep warm-start, broad SOTA, and general recommender claims out of the abstract and conclusion.
6. Archive raw per-user records and manifests with stable checksums.
7. Re-run the public gate from a clean checkout immediately before submission.

This path is closer to approval, but I would still require the fairness caveat and ablations before acceptance.

## Submission Decision Matrix

| Candidate | Current Decision | Reason |
|---|---:|---|
| Root HSTU/FIR `PAPER_DRAFT.md` | Reject | Noncanonical artifact graph, stale notes, contradictions, unresolved HSTU fidelity, comparator limitation |
| LC2C Retrieval LTR lab paper | Major revision | Narrow result appears stronger, but claim must be reframed as DropoutNet-assisted fusion and ablated fairly |
| Old BEST-Rec v4 paper | Reject | Existing manifest says SOTA claim not allowed and modern baseline suite was incomplete |
| Broad SOTA claim | Reject | Not supported by current artifacts |
| Narrow V2 MI numeric claim | Conditionally usable | Arithmetic and sidecars are traceable, but packaging and provenance need cleanup |

## Final Reviewer Position

I would still reject the current resubmission.

The strongest salvage path is not to keep patching every manuscript at once. Pick one canonical paper. If the goal is fastest honest publication, the LC2C Retrieval LTR cold-item paper is the more defensible track, but only with narrow framing and fair ablations. If the goal is the HSTU/FIR paper, it needs a full artifact rebuild and a stricter comparator/statistics package before it can survive a top-tier review.
