# TORS methodology and submission-readiness checklist

Status: Codex prefill for Claude's independent-in-role red-team audit, updated
2026-07-31. This is an internal same-team checklist, not peer review,
independent confirmation, or a claim that ACM TORS satisfies the maintainer's
unresolved Tier-A ranking rule.

Primary methodological reference: ACM TORS, "Improving Methodological Standards
in Recommender Systems Offline Evaluation" (2026),
<https://doi.org/10.1145/3800587>.

Status legend:

- **PASS**: current repository evidence appears to meet the item;
- **PARTIAL**: meaningful support exists, but a stated gap remains;
- **OPEN**: required work has not been completed;
- **BLOCKED-HUMAN**: an agent cannot truthfully close the item;
- **BLOCKED-RANKING**: the controlling journal-ranking authority is unknown.

## 1. Scientific and methodological matrix

| Area | Status | Current evidence | Required closure |
|---|---|---|---|
| Research question and hypotheses | PARTIAL | The modular FIR question, outcome-known evidence hierarchy, negative MovieLens result, and claim restrictions are explicit. | Compress the article around one primary temporal-input question after the matched-input study; preserve outcome-conditional wording. |
| Novelty as a modular contribution | PARTIAL | The paper contributes a small learned causal FIR component, extensive falsification controls, and reproducible artifact governance rather than claiming a new end-to-end framework. | Claude must compare the exact mechanism and empirical claim to the current closest methods and state what is technically new, what is an evaluation contribution, and what is not new. |
| Proposed-method implementation | PASS | Source, runners, frozen protocols, adjudicators, generated tables, claim graph, hashes, and strict build paths are repository-bound. | Recheck after every future scientific phase and disclose any private-artifact boundary. |
| Complete experimental pipeline | PARTIAL | Training, sealed evaluation, adjudication, statistics, tables, TeX, claim mapping, and release verification are unusually complete. | Produce one public execution map from raw lawful inputs to final claims and verify that every distributable dependency is included. |
| Baseline source and execution | PARTIAL | Identity, SASRec-related controls, pointwise controls, and comparator documentation exist. | Add strong simple and current baselines under the same task semantics; identify official implementations and document unavoidable adaptations. |
| Baseline selection rationale | PARTIAL | Existing comparator matrix distinguishes protocol-compatible from contextual literature. | Claude must justify inclusion/exclusion against the current literature and flag any omitted method a reviewer could reasonably view as decisive. |
| Hyperparameter tuning fairness | OPEN | Current campaigns document configurations but several comparisons have unequal architecture, capacity, initialization, campaign date, or tuning opportunity. | Freeze symmetric validation-only search spaces, configuration counts, seeds, early stopping, resource budgets, failed trials, and selected values. No result-dependent rescue budget. |
| Exact-input temporal isolation | DEFERRED | Claude rejected the repeated-current V1 because it collapses to one functional DOF and is weaker than the completed pointwise control; Codex accepted the no-run verdict. | Prioritize A3/A4. Any future V2 needs a new identifier, nondegenerate controls, a fresh reject-first memo, and human authorization. |
| Data preprocessing and cohort definition | PARTIAL | Dataset versions, split rules, candidate semantics, and cohort restrictions are extensively recorded. | Consolidate one dataset card per corpus, including raw source/version, checksums, exclusions, leakage controls, license, retention, and redistribution boundary. |
| Evaluation protocol | PASS | Full-catalog semantics, fixed splits, registered endpoints, sealed evaluation, and explicit non-comparability boundaries are documented. | Revalidate identical semantics for every added baseline/dataset and retain all registered negative outcomes. |
| Statistical analysis | PASS-WITH-LIMITS | Paired seed contrasts, intervals, multiplicity decisions, and exact verdicts are governed. Limits of fixed-split seed inference are stated. | For new work, preregister units, family, adjustment, missing-run handling, and synthesis. Never treat seed intervals as population/dataset uncertainty. |
| Robustness and falsification | PARTIAL | Negative transfer, identity diagnostics, pointwise controls, breadth checks, and failure history are retained. | Complete the closest temporal-input control; do not add post-outcome tests solely to rescue a conclusion. |
| External validity | OPEN | Amazon evidence is heterogeneous and MovieLens is negative, but there is no fresh externally custodied replication. | Freeze a lawful new non-Amazon study before TEST inspection; prefer external endpoint custody. Retain MovieLens regardless of outcome. |
| Compute and environmental reporting | PARTIAL | Environment locks, hashes, hardware records, GPU monitoring, and clean-clone procedures exist. | Provide per-method training/search cost and comparable resource accounting in the final artifact. |
| Reproducibility and artifact graph | PASS | 201 active cells across 25 claim families recompute with zero mismatch or untraceable cells; strict and separately hydrated clean-clone checks have passed. | Repeat after new evidence; publish only distributable artifacts and clearly label any private endpoint/input requirement. |
| Claim/manuscript/TeX parity | PASS | Canonical Markdown, generated numeric tables, TeX parity checks, forbidden-wording scans, and PDF builds are governed. | Re-run on every content change and keep main-article claims identical to supplement/artifact evidence labels. |
| Outcome-independent reporting | PARTIAL | Negative/VOID/deviated histories are preserved and outcome-known labels are prominent. | Claude must verify that title, abstract, contribution list, conclusion, and cover letter do not selectively upgrade favorable outcomes. |
| Author, COI, funding, ethics, and license fields | BLOCKED-HUMAN | Placeholders and explicit blocks are retained rather than invented. | Maintainer supplies and approves all identities, affiliations, disclosures, ethics/legal decisions, and redistribution permissions. |
| AI assistance in the research process | BLOCKED-HUMAN | Codex and Claude have materially assisted repository work, experimental design review, code, analysis, and manuscript preparation. | Maintainer must approve a precise venue-compliant methods/disclosure statement describing which systems were used, for which tasks, the human verification performed, and that humans retain responsibility. Do not minimize this to writing-only assistance if the record shows broader use. |
| Tier-A venue verification | BLOCKED-RANKING | TORS is the strongest current scientific fit, not a verified ranking conclusion. | Record the institution's controlling list/rule and edition, then verify exact title and ISSN before calling any target Tier A. |
| Waiver-free final release | OPEN | A strict clean-clone release exists, but final human metadata/legal boundaries and future-study artifacts remain unresolved. | Complete all human fields, run without draft waiver, create immutable tag/deposit, and download/hash-verify the public package. |

## 2. Required tuning record for every reported method

The final artifact must expose, per dataset and method:

1. implementation repository and exact revision;
2. any local patch and why it was necessary;
3. preprocessing and candidate-universe compatibility;
4. hyperparameter names, domains, and sampling distribution;
5. search strategy and number of attempted/completed configurations;
6. optimizer seeds, initialization seeds, and data-order seeds;
7. early-stopping metric, patience, maximum budget, and tie rule;
8. validation-only selection rule and selected values;
9. failed/OOM/non-finite trials and their fixed handling;
10. training and search wall-clock/GPU accounting;
11. TEST access boundary and first endpoint reader;
12. final evaluation command, environment, and artifact hashes.

A baseline is not fairly tuned merely because its published default runs. If an
official implementation cannot support the paper's task semantics, report it as
contextual rather than silently adapting its result into a direct comparison.

## 3. Claude reject-first audit form

Claude should copy this section into a dated memo and fill every field before a
new protocol is frozen or the venue package is declared ready.

```text
AUDIT DATE:
REVIEWED COMMIT:
TARGET JOURNAL + RANKING AUTHORITY/EDITION:
DECISION: APPROVE / REJECT / APPROVE WITH REQUIRED CHANGES

STRONGEST NOVELTY OBJECTION:
STRONGEST IDENTIFIABILITY/CONFOUNDING OBJECTION:
STRONGEST BASELINE-FAIRNESS OBJECTION:
STRONGEST STATISTICAL OBJECTION:
STRONGEST EXTERNAL-VALIDITY OBJECTION:
STRONGEST REPRODUCIBILITY/DATA-LEGAL OBJECTION:
AI-USE DISCLOSURE CHECK:

MANDATORY CHANGES BEFORE FREEZE/SUBMISSION:
OPTIONAL IMPROVEMENTS:
CLAIMS PERMITTED IF POSITIVE:
CLAIMS PERMITTED IF NULL:
CLAIMS PERMITTED IF NEGATIVE:
FILES AND PRIMARY SOURCES REVIEWED:
```

Claude's approval does not create independent evidence. Codex must separately
verify implementation/provenance, and the human maintainer retains every
submission, legal, identity, and ranking decision.

## 4. Current release decision

**NOT READY FOR TIER-A SUBMISSION.** The repository is mechanically strong, but
the ranking authority, tuning-fairness matrix, closest temporal control, new
non-Amazon evidence, human/legal fields, and AI-use disclosure remain open. This
checklist must be rerun after those items are resolved; completing it cannot
guarantee acceptance.
