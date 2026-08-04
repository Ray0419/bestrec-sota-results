# Tier-A non-Amazon dataset selection gate

Status: metadata-only selection framework, updated 2026-07-31. No dataset is
selected, downloaded, preprocessed, or outcome-inspected by this document.

## 1. Objective

Choose one genuinely new non-Amazon sequential-recommendation domain before target
outcomes are visible. The dataset must support a scientifically interpretable
full-catalog next-item task, lawful use, reproducible acquisition, and—preferably—
external endpoint custody. The existing negative MovieLens result remains reported
regardless of the new result.

## 2. Hard eligibility gates

An exact dataset/version is eligible only if all answers are documented as PASS:

1. first-party or authoritative acquisition URL and immutable version/date;
2. explicit terms/license permit the planned research processing and retention;
3. redistribution boundary is known for raw, derived, and aggregate artifacts;
4. stable user and item identifiers plus event ordering or timestamps;
5. sufficient sequence length, users, and catalog size after a metadata-only
   feasibility rule frozen before outcome evaluation;
6. no target label/TEST metric previously inspected by this team;
7. full-catalog evaluation is computationally feasible without candidate sampling;
8. method inputs can be aligned without method-specific cohort changes;
9. privacy, sensitive-attribute, and deletion obligations are reviewed;
10. an external custodian can hold the TEST transform/endpoints, or the absence of
    external custody is explicitly accepted and disclosed.

Any FAIL eliminates the candidate. UNKNOWN blocks selection; it is not treated as
permission.

## 3. Metadata-only scorecard

After hard gates pass, score without training or TEST inspection:

| Dimension | Weight | Frozen scoring rule |
|---|---:|---|
| Domain distinctness from Amazon retail | 3 | 0 same retail setting; 1 adjacent commerce; 2 materially different content/behavior domain |
| Sequence/candidate suitability | 3 | 0 marginal; 1 workable; 2 strong timestamped histories and meaningful catalog |
| Legal/release clarity | 3 | 0 ambiguous; 1 usable with restrictions; 2 clear acquisition and artifact boundary |
| Reproducibility | 2 | 0 unstable/manual; 1 versionable source; 2 exact version/checksum and deterministic preprocessing |
| External custody feasibility | 2 | 0 unavailable; 1 possible; 2 named willing custodian and written procedure |
| Compute feasibility | 1 | 0 exceeds approved envelope; 1 fits approved full-catalog envelope |

Select the highest total. Ties resolve by stronger legal clarity, then custody,
then larger post-rule item catalog, then lexical dataset identifier. The scorecard,
source evidence, and selection script/hash must be committed before acquisition.

## 4. Metadata-only provisional pre-screen

No candidate below is selected or approved:

- **KuaiRand-Pure — strongest provisional technical candidate.** The official
  project describes timestamped sequential Kuaishou short-video interactions;
  its public repository reports a 7,583-video candidate pool for the Pure version
  and a CC-BY-SA-4.0 repository license. Its manageable full catalog and domain
  difference make it the first candidate to send through human legal review.
  Open questions: exact positive-event definition, policy/exposure mixing,
  preprocessing estimand, raw-data license scope versus repository-code license,
  and external custody. Sources: <https://kuairand.com/> and
  <https://github.com/chongminggao/KuaiRand>.
- **MIND-small — protocol-mismatch risk.** Microsoft's official page provides
  timestamped news behavior logs under Microsoft Research License Terms, but the
  canonical task is impression-candidate news ranking. Converting it to this
  paper's persistent full-catalog next-item task may change the scientific
  question and candidate semantics. Source: <https://msnews.github.io/>.
- **Yelp Open Dataset — legal/sparsity risk.** The official dataset is restricted
  to academic research under a dataset agreement, and business-review sequences
  may be too sparse and geographically exposure-confounded for the desired task.
  It remains UNKNOWN until the maintainer reviews the current agreement and a
  metadata-only feasibility check is designed. Source:
  <https://www.yelp.com/dataset>.

The pre-screen is not a license opinion. In particular, an open-source license on
a repository does not automatically settle the terms of the hosted interaction
data. UNKNOWN remains blocking.

## 5. Required selection record

```text
RANKING AUTHORITY / TARGET JOURNAL:
CANDIDATE EXACT TITLE + VERSION:
AUTHORITATIVE URL:
TERMS/LICENSE URL + HUMAN DECISION:
RAW/DERIVED/AGGREGATE REDISTRIBUTION RULE:
METADATA AVAILABLE WITHOUT TARGET OUTCOME:
FROZEN FEASIBILITY THRESHOLDS:
PRIVACY/ETHICS NOTES:
PREVIOUS TEAM ACCESS CHECK:
EXTERNAL CUSTODIAN + ATTESTATION PLAN:
HARD-GATE VERDICT:
WEIGHTED SCORE:
```

## 6. Stop rule

Do not download or inspect candidate interactions until the human maintainer has
approved the terms/license and the selection record is frozen. If no candidate
passes, report A4 blocked and do not substitute a convenient dataset post hoc.
