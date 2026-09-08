# Comparator landscape check — 2026-09-08

Purpose: answer, for the two counted per-category comparisons, whether any *published* number on the
same benchmark now exceeds the manuscript's fresh multi-seed values. This is a same-team literature
check, not new evidence, and it changes no claim wording: the manuscript's forbidden-vocabulary rule
(no "SOTA", no paired superiority) stands. What it can license is a dated sentence of the form
"the highest reported NDCG@10 we could locate under this protocol", with the caveats below.

## Musical_Instruments (AR2023, iterative user+item 5-core, LLOO, full-catalog)

| source | NDCG@10 | protocol notes |
|---|---:|---|
| **This work, fresh 5-seed K=16** (`SOTA_CONFIRM_V2_RESULTS.md`) | **0.04152 ± 0.00045** (CI-LB 0.04096) | never-inspected seeds 20260618–22; K=8 arm 0.04120 (CI-LB 0.04083) |
| HSTU-BLaIR, published (arXiv:2504.10545 v3, Table 2) | 0.0406 | single seed; locally regenerated at 0.0406 best-epoch / 0.0391 final (§5.6) |
| Latte (arXiv:2605.06331, Table 1, "Instruments") | 0.0331 | LLOO, full ranking; 5-core filtering not stated in main text; baseline PSID 0.0325 |
| SID-MLP (arXiv:2605.12617, "Musical Instruments") | 0.0332 | 5-core, LLOO, full ranking, **sequences truncated to 20**; TIGER-kv 0.0323 |
| GrIT (arXiv:2602.19728) | — | evaluates Video_Games / Industrial_and_Scientific / CDs_and_Vinyl only |
| arXiv:2605.07125 (shortcut-solvable benchmarks) | — | Amazon 2014 Beauty/Sports/Toys/CDs + non-Amazon; no MI |
| arXiv:2603.02709 (sensory-aware) | — | Amazon 2014 five domains; no MI |
| MEMOIR (arXiv:2607.23986) | — | AR2023 Electronics / Clothing only |

Reading: under the AR2023 MI 5-core LLOO full-catalog protocol, the highest **published** value located
remains HSTU-BLaIR's 0.0406, and both of this work's fresh 5-seed CI lower bounds sit above it. The
two 2026 semantic-ID papers that do report Instruments land at 0.033, roughly 20% below, but their
sequence truncation (20) and unstated filtering geometry make them **not numerically interchangeable**
with either our runs or HSTU-BLaIR's; they are cited for coverage only, exactly as the manuscript's
"concurrent protocol landscape" paragraph already does.

## Office_Products (AR2023, 5-core, LLOO, full-catalog)

| source | NDCG@10 | notes |
|---|---:|---|
| **This work, V3 fresh 5-seed K=16** (`OFFICE_V3_RESULTS.md`) | CI-LB **0.03033** (K=8 CI-LB 0.03024) | environment-matched reference 0.0279; published 0.0271; 10/10 seeds above both |
| HSTU-BLaIR, published | 0.0271 | local regeneration 0.0275 final / 0.0279 best |
| any 2026 preprint located | — | none of the seven papers checked reports Office_Products |

Reading: no published Office_Products number above 0.0279 was located.

## What this does and does not license

- **Licensed (with date):** "As of 2026-09-08 we could locate no published NDCG@10 above the
  HSTU-BLaIR values on either category under this protocol." Suitable for the cover letter or a
  response-to-reviewers, not for a "state of the art" sentence.
- **Not licensed:** any general or per-category SOTA claim. Reasons unchanged from
  `CANONICAL_SUBMISSION.md`: the comparator is single-seed, the comparison is a point-estimate
  contrast under a reproduced (environment-caveated) protocol, Video_Games is explicitly not claimed
  (0.0673 vs 0.0760), and the search above is neither exhaustive nor peer-reviewed.
- **Video_Games (context only):** SID-MLP, Latte, GrIT and arXiv:2603.02709 all report Video Games,
  but under Amazon 2014 or different filtering; HSTU-BLaIR's 0.0760 on AR2023 remains the anchor and
  is not reached here.

Sources fetched 2026-09-08: arXiv:2605.12617 (HTML), arXiv:2605.06331 (HTML), arXiv:2602.19728 (HTML),
arXiv:2605.07125v1 (HTML), arXiv:2603.02709 (HTML), arXiv:2607.23986v1 (HTML), arXiv:2504.10545v3.
