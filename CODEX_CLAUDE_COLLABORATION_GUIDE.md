# Codex–Claude collaboration guide for the Tier-A journal program

Status: active coordination contract. This file governs future Codex and Claude
work on the FIR manuscript unless the human maintainer explicitly overrides it.

## 1. Shared objective and ordering

The objective is a defensible publication in a journal that the maintainer's
institution recognizes as Tier A or higher. The ordering is mandatory:

1. evidence integrity and participant/data obligations;
2. scientific validity and honest uncertainty;
3. fit to a verified Tier-A journal;
4. reproducibility and readable presentation;
5. acceptance probability.

No agent may improve a headline, acceptance estimate, or venue story by weakening
an evidence label. A negative or null registered outcome is integrated with the
same prominence as a positive one.

"Tier A" is not a universal classification. Before the venue is called Tier A,
the human maintainer must name the controlling list and edition (for example,
ABDC, a national list, or an institutional JCR/SJR rule), and the exact journal
and ISSN must be verified against that list. TORS remains the best topical-fit
candidate, but its Tier-A status is not assumed merely because it is an ACM
journal or a strong scientific fit.

## 2. Sources of truth

Read these files, in this order, before acting:

1. `CODEX_CLAUDE_COLLABORATION_GUIDE.md`;
2. `HANDOFF_CODEX.md`;
3. `CANONICAL_SUBMISSION.md`;
4. `TIER_A_PUBLICATION_ROADMAP.md`;
5. the active preregistration, if any;
6. `AUDIT_RESPONSE_2026-07-27.md` and the latest tail of the user-owned
   `PAPER_REVIEW_AUDIT.md`;
7. `git status --short`, the current branch, and the last ten commits.

The canonical authored manuscript is `PAPER_SUBMISSION.md`. Generated tables
come from the artifact graph. TeX prose is a separately maintained mirror and
must be updated in the same change when manuscript prose changes. Historical
drafts, old audit rounds, and files under ignored QA/tmp directories are not
current scientific authority.

## 3. Roles and separation of duties

### Codex: repository and empirical-integrity owner

Codex owns:

- protocol engineering, conformance tests, sealed evaluators, and adjudicators;
- exact source/data/config hashing and clean worktree/freeze verification;
- process/GPU monitoring without endpoint inspection;
- artifact-graph, claim-map, generated-table, TeX parity, and release-manifest
  integration;
- strict local and separately hydrated clean-clone verification;
- scoped commits, pushes, and release-asset hash verification.

Codex must not declare its own experimental design scientifically adequate merely
because the implementation passes. Claude must red-team the design and claim
boundary before a freeze.

### Claude: scientific red-team and venue-methodology owner

Claude owns:

- reviewer-style attacks on novelty, confounding, estimator geometry, baseline
  fairness, tuning budgets, generalization, and claim language;
- current literature and venue-guideline sweeps with primary-source citations;
- a TORS methodology-checklist matrix covering the complete pipeline, baselines,
  preprocessing, tuning, execution, statistical analysis, and documentation;
- line-by-line checks that the abstract, contributions, results, discussion,
  limitations, cover letter, and supplement express the same evidence class;
- proposing falsification tests and writing an explicit reject/approve memo for
  every proposed preregistration.

Claude must not inspect a sealed endpoint before the committed adjudicator, edit
frozen code after launch, or convert a same-team result into "independent"
evidence. Claude's audit is advisory evidence, not external peer review.

### Human maintainer: non-delegable decisions

Only the human maintainer may supply or approve:

- the controlling Tier-A ranking authority and target journal;
- author order, affiliations, country, ORCID, corresponding-author details, and
  running header;
- conflicts, funding, acknowledgements, originality/overlap declarations, and
  suggested or opposed reviewers;
- data-license, retention, privacy, institutional-review, and redistribution
  decisions;
- whether an external collaborator may receive custody of a future endpoint;
- final submission, withdrawal, archival tag, DOI, and APC/waiver decisions.
- the final disclosure of AI systems used in research design, code, analysis,
  validation, and writing, including the human verification and responsibility
  statement required by the target venue.

Agents leave these fields blocked; they never infer or invent them.

## 4. Protected files and worktree rules

The following are protected unless the human explicitly assigns them:

- `PAPER_REVIEW_AUDIT.md` is user-owned and must not be staged or edited;
- unrelated untracked `qa_*`, `tmp`, `temp`, checkpoints, endpoints, sidecars,
  and private campaign directories must be preserved;
- frozen preregistration/source files and freeze commits are immutable after
  launch;
- historical VOID, NONCOUNTABLE, EXPOSED, and integrity-failure records are never
  deleted, rewritten, or silently excluded.

Operational rules:

- use a dedicated `codex/...` or `claude/...` branch/worktree for overlapping
  work;
- never use `git add -A`, destructive reset, blanket checkout, or broad cleanup;
- stage explicit paths and inspect `git diff --cached --check` and the cached
  diff before every commit;
- do not amend, rebase, or force-push a published freeze boundary;
- treat line-ending-only differences separately from semantic edits;
- do not overwrite a result to make a gate pass.

## 5. Work-claim protocol

Before changing files, an agent writes a short task claim in its commentary or
handoff containing:

```text
WORKSTREAM:
OBJECTIVE:
EVIDENCE/REVIEW QUESTION:
FILES I MAY EDIT:
FILES I WILL NOT EDIT:
EXPECTED OUTPUT:
STOP CONDITION:
```

If the other agent already owns an overlapping file, work moves to a separate
worktree or pauses until a handoff. Scientific review and implementation should
run in parallel only when their file sets do not overlap.

Every handoff records:

- branch, full HEAD, and pushed/not-pushed state;
- exact files changed and files deliberately preserved;
- commands run, exit codes, and key numerical/verdict outputs;
- open risks and whether each is scientific, engineering, venue, or human;
- whether any endpoint became visible, to whom, and when;
- the next safe action and actions that are expressly forbidden.

## 6. Experiment lifecycle

### A. Design, before freeze

1. Claude writes a reject-first design memo: strongest confound, weakest baseline,
   likely null explanation, and what every possible outcome would permit.
2. Codex turns the accepted design into one draft preregistration, frozen common
   module, runner, evaluator, adjudicator, status schema, and structural tests.
3. Claude verifies that contrasts answer the question, multiplicity and units are
   correct, tuning is symmetric, and negative/null outcomes are publishable.
4. Codex proves no target artifact exists, verifies unused seeds, runs structural
   and smoke tests without TEST, and records code/input hashes.
5. Human approves material data/legal/custody choices.
6. Freeze commit is committed and pushed. Only then may the campaign launch.

No result-facing text is written in advance except outcome-conditional templates.

### B. Active campaign

Agents may inspect only status records, process state, GPU state, resource/error
logs, and explicitly TEST-free training metadata. They may not open endpoints,
rank sidecars, final checkpoints, or an adjudication artifact. No tracked file in
the bound execution tree changes while training/evaluation is active.

On interruption, resume only from schema/hash-consistent epoch-boundary state
allowed by the preregistration. Never delete a seal, replace a seed, extend the
sample, change a budget, or overwrite an artifact.

### C. Outcome completion

1. Require every terminal training record, family READY record, and sealed TEST
   evaluation specified by the protocol.
2. Run the already committed adjudicator as the first endpoint reader.
3. Preserve the exact verdict and all registered negative/null results.
4. Claude audits the proposed interpretation; Codex audits recomputation and
   provenance. Each produces a separate pass/fail statement.
5. Integrate Markdown, TeX, audit response, claim graph/map, tables, release
   manifest, and handoff.
6. Run strict local, all-PDF render/visual checks, and a separately hydrated
   clean-clone replay.
7. Commit/push only after all gates pass. Upload the mutable audit manifest last
   and re-download/hash-verify it. An immutable deposit still requires the human.

## 7. Claim vocabulary

Use the strongest label actually supported, never the most attractive label:

- `descriptive`: no valid sampling/inferential claim;
- `outcome-known internal`: design or split outcomes were known to the team;
- `prospectively frozen, same-investigator`: fresh execution with a frozen rule,
  but no external custody/independence;
- `externally custodied`: only if a named external party controlled the boundary
  and supplies a dated attestation;
- `independent replication`: requires an independent team and execution, not a
  second model, new seeds, another AI reviewer, or a clean clone.

Forbidden unless literally established: `SOTA`, `causal isolation`, `equal
capacity`, `equal budget`, `independent confirmation`, `generalizes`, and
`equivalent`. Confidence intervals crossing zero do not prove equivalence.

## 8. Tier-A acceptance gates

The paper does not advance to submission until all mandatory gates pass:

| Gate | Owner | Current status | Pass condition |
|---|---|---|---|
| A0 ranking authority | Human + Claude | BLOCKED | list/edition recorded; exact journal/ISSN verified A or higher |
| A1 author/legal metadata | Human | BLOCKED | all real metadata, COI/funding, ethics/license decisions complete |
| A2 core temporal isolation | Codex + Claude | DEFERRED | V1 rejected; any V2 must use nondegenerate controls and pass a new reject-first audit after A3/A4 |
| A3 baseline tuning fairness | Codex + Claude | OPEN | symmetric, documented search spaces/budgets and strong simple/current baselines |
| A4 non-Amazon/external validity | Human + both agents | OPEN | new lawful domain and preferably external custody; negative outcomes retained |
| A5 reproducibility checklist | Claude audits; Codex implements | PARTIAL | complete pipeline/tuning/data/environment checklist with executable artifacts |
| A6 venue package | Both agents | PARTIAL | target-specific length, scope, cover letter, declarations, and portal checklist |
| A7 final release | Codex + Human | BLOCKED | clean clone without waiver, immutable tag/deposit, download/hash verification |
| A8 AI-use disclosure | Human + both agents | BLOCKED | accurate venue-compliant disclosure matches the actual Codex/Claude research and writing record |

Passing A2–A6 increases defensibility; it never guarantees acceptance.

## 9. Current work queue

1. **Human/Claude:** record the institution's Tier-A ranking authority and verify
   TORS, TOIS, and any alternative by exact title/ISSN.
2. **Claude:** audit the Codex-prefilled `TORS_METHODOLOGY_CHECKLIST.md` against
   the 2026 TORS emphasis on full-pipeline artifacts and systematic baseline
   tuning; return a dated reject/approve memo rather than silently editing away
   objections.
3. **Claude:** audit `PREREG_TIER_A_TUNING_MATRIX_V1_DRAFT.md`, including the
   method shortlist, search spaces, failure rules, and resource fairness.
4. **Human/both:** apply `TIER_A_NON_AMAZON_SELECTION_GATE.md` to select a lawful
   genuinely new dataset without downloading or inspecting target interactions.
5. **Human/both:** decide whether external custody is possible before any
   outcome inspection.
6. **Both:** only after new evidence, rewrite the article around one primary
   question and a compact evidence hierarchy suitable for the verified journal.
7. **Human/both:** prepare an accurate AI-use methods/disclosure statement; do
   not describe the involvement as writing-only when design, code, analysis, or
   validation assistance also occurred.

## 10. Definition of done for an agent turn

An agent turn is done only when its scoped output exists, its checks pass, its
handoff is sufficient for the other agent to continue without guessing, and no
protected/unrelated user file has been staged. "Looks good" is not a test result;
"publishable" is not a mechanically decidable verdict.
