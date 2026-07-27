# Response to `PAPER_REVIEW_AUDIT.md` — 2026-07-27

This response addresses the 18-item list timestamped 2026-07-27 22:00. It does
not edit or supersede the independent audit. “Closed” means the manuscript or
artifact now matches the evidence; it does not retroactively improve study
independence, custody, or construct validity.

| Audit item | Current disposition | Response and evidence |
|---:|---|---|
| 1 | **OPEN — author action required** | Author, affiliation, country, contact, and running-header fields remain placeholders. Builds pass only with a logged `DRAFT_WAIVER=1`; no identity was invented. A release build must be rerun without the waiver after real metadata are supplied. |
| 2 | **OPEN scientific gap; wording closed** | Every headline FIR estimate is explicitly outcome-known/test-exposed. The abstract, contribution ledger, Results, Discussion, and Conclusion make no independent-confirmation claim. Only a genuinely untouched temporal/non-Amazon split with independent one-shot custody can close the evidentiary gap. |
| 3 | **Claim overreach CLOSED; experiment OPEN** | The paper now says only that the tested trainable left-causal residual arms improved frozen identity in this setup. It states that shared/nonlinear arms were not separated from learned taps, MA/HP are redundant, and the absent active lag-0/pointwise non-temporal placebo prevents temporal-specific attribution. A fail-closed no-future-leakage unit test now perturbs future tokens with every filter/control path active and verifies invariant prefix states under both Transformer and HSTU encoders (16/16 paths PASS); this establishes implementation causality, not temporal-mechanism specificity. A new matched placebo study remains required. |
| 4 | **CLOSED after the 22:00 audit** | `bootstrap_public_clone.py` now hydrates and raw-hash-verifies every release section, including all 48 control final-evaluation JSONs, 48 sidecars, and 48 checkpoints. A fresh deep-path Windows clone installed 282/282 release-only assets and passed exact HSTU parity, every adjudicator, Office V1 VOID retention, and the strict graph/manifest gate. The release footprint is documented as approximately 4.60 GB. |
| 5 | **CLOSED** | E-A is labeled the frozen independent-arm Welch/Satterthwaite analysis: ordinary 95% Welch CI, df=13.939; its paired-by-seed result is descriptive only. Hybrid intervals are ordinary paired 95% CIs; Holm adjusts p-values/decisions, not intervals. A new health gate forbids the stale labels. |
| 6 | **OPEN human verification; disclosure closed** | Dirty-tree execution across five commits, absent independent sidecar custody, and the limited local start marker are retained in the main text and erratum. The study remains outcome-known exploratory evidence. Only the maintainer can verify pre-adjudication human/tool visibility. |
| 7 | **Citation/scope CLOSED; executions OPEN** | FreqRec and WEARec are cited in Table 0, Related Work, Method, and the bibliography; BSARec is correctly scoped to Theorem 1 on repeated softmax attention, not the HSTU-style operator. The governed AlphaFuse port is disclosed as `NONCOUNTABLE`/`manuscript_allowed=false`, with no endpoint imported. Equal-protocol current baselines remain future experimental work. |
| 8 | **Claim boundary CLOSED; sensitivities OPEN** | The estimand is next recorded review event, not preference/purchase/deployment engagement. Rating, verified-purchase, keep-latest, real implicit-event, global-time, and query-time-catalog sensitivities remain unrun and are named limitations. |
| 9 | **Partly CLOSED** | Headline E-A is now represented by two paper-bound `fir_v3` graph cells, making 192 active cells across 18 families with zero mismatch/untraceable cells. Availability text distinguishes the numerical artifact graph, the release manifest, and Table 0’s citation ledger; it no longer claims every printed sentence is hash-manifested. Table 0 intentionally remains `checked: 0` because it is a literature/novelty table, not a numerical-result family. Full transitive rank/source coverage and mutation testing remain open assurance work. |
| 10 | **Primary paper type CLOSED; validation depth OPEN** | Title, abstract, Introduction, Table 0, Related Work, Discussion, and Conclusion consistently define the paper as an **incremental modular FIR contribution**. The audit/rebuild apparatus is a supporting contribution, not the lead. Current-baseline execution, cross-repository validation, fault injection, and reviewer-usability evidence would strengthen but do not redefine the paper type. |
| 11 | **CLOSED** | “Transfers,” “cross-category confirmation/transfer,” “FIR-specific interpretation,” and “supports temporal mixing” were removed from the canonical and rendered manuscripts. Shared/nonlinear controls are described as statistically unseparated, never equivalent. The health gate now fails on the stale attribution phrases. |
| 12 | **CLOSED** | The manuscript names the separately frozen five-test family A and four-test family B, reports all nine Holm-adjusted p-values, labels every CI ordinary paired, and states that neither one global nine-test family nor simultaneous-CI coverage is implied. |
| 13 | **OPEN; accurately scoped** | Inference remains over optimizer seeds on fixed splits. Retained tests are not equivalence. Repeated temporal cutoffs/splits and hierarchical dataset/user/item inference require new experiments and were not manufactured post hoc. |
| 14 | **OPEN experiment/opportunity** | The 16-parameter shared arm’s numerical performance is disclosed without a superiority or efficiency claim. Fresh preregistered shared/grouped/low-rank/placebo arms, noninferiority margins, and parameter/latency/memory Pareto curves remain required. |
| 15 | **OPEN experimental/engineering work** | Cache/item-map binding, metadata-missingness controls, repeated thinning draws, tie-safe sensitivity, and item-macro/hierarchical inference remain incomplete. Claims were narrowed rather than treating these omissions as repaired. |
| 16 | **OPEN release/deposit item** | The public evidence assets are complete, remotely size/digest checked, and clean-clone replayed, but the mutable `v0.9-audit-evidence` and stale deposit tag are not represented as a final immutable archival deposit. A new versioned release/tag and DOI deposit must be cut only after final author/legal metadata and a final clean-clone replay. |
| 17 | **Partly CLOSED** | Related Work was condensed; Table 0 was redesigned from six cramped columns to a readable four-column claim ledger; the venue PDF fell from 41 to 40 pages and the reader PDF from 46 to 45; the appendix and supplement overflows were repaired; and targeted visual inspection found no clipping. The final titration block is kept with its heading. Reader bookmarks/tagging, venue PDF tagging, complete accessibility text, and further body-length reduction remain editorial/accessibility work. |
| 18 | **OPEN — author/legal action required** | Outcome visibility, exact dirty patches, author order/identity, portal mode and length, ethics/privacy review, funding/conflicts, licenses, and derivative-redistribution permission require maintainer verification. |

## Net claim after the audit

This is a modular contribution paper, not a brand-new algorithm or architecture
paper. The defensible result is narrower: under fixed outcome-visible settings,
tested trainable left-causal residual arms improved a frozen-identity control.
Learned per-channel FIR taps are one successful realization, but the present
controls establish neither learned-tap superiority nor temporal specificity.
The artifact apparatus makes that boundary, the nulls, and the deviations
reproducible; it does not turn them into independent confirmation.

## Reproduction evidence

The numerical manuscript snapshot at commit `43d3594b` was cloned under an ordinary
deep Windows path. Bootstrap installed and raw-hash-verified 282/282
release-only assets. The strict replay independently hydrated HSTU-BLaIR commit
`40a27879`, obtained bitwise core-block parity, recomputed 192/192 active cells
across 18 claim families with zero mismatches or untraceable cells, verified
745/745 manifested files, passed every governed adjudicator including
`CTRL-ACTIVE-CONTROL-SUPPORTED`, retained Office V1 as VOID, and ended
`SUBMISSION REBUILD: PASS`. The subsequent submission-only update adds the
cover-letter correction and the 16-path causal unit test to the manifest; its
local strict rebuild verifies 747/747 files. A release tag/DOI deposit should
repeat the full fresh-clone check after author/legal metadata are finalized.
