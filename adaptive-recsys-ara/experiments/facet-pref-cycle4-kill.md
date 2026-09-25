# FACET-PREF Cycle-4 Kill Record

Date: 2026-08-07

## Decision

**FACET-PREF is killed. Phase 5 is prohibited. No rerun or post-outcome repair is authorized.**

The one prospectively authorized launch failed the registered retrieval-feasibility contract before any validation preference outcome or test outcome was opened. This is a scientific systems failure under the stated fixed-budget architecture, not a transient infrastructure failure.

## Bound execution

- Git commit: `54992276ba6d28bdc36ae1a54f8e179aadeb7f1c`
- Run ID: `facet-pref-poc-v1-20260807-prospective-seq001`
- Protocol fingerprint: `2f652fb34c7ac6399580fe8c2083a2fb38529966ea6876e55425358a8b9bb52e`
- Runner SHA-256: `3ede7d2f387c3ca5db7c1882b8f898c4d827d06e23403651599ba39901b2461c`
- Launcher/verifier SHA-256: `4b76a1f03a5dccb135c20db4c7b488ef1d9e50f34dd975a69b481536736a464c`
- Dataset archive SHA-256: `a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20`

## Registered failure

The runner authenticated the archive, locked A-only representations and indexes, published R descriptors before joining R labels, capped the R corpus at 30,000 natural pairs, trained every registered adapter for all three seeds, and published the target-blind V descriptors. It then failed while constructing the first target-blind V candidate manifest:

```text
caper_poc.IntegrityError: The fixed depth-700 collaborative row exhausted before 200
```

The fixed BPR search returns only 700 catalog rows and then filters all prefix-seen items. For at least one valid fresh-cohort request, fewer than 200 unseen items remained. The locked contract requires exactly 200 collaborative candidates, exactly 200 BPR-novel semantic candidates, no adaptive deeper query, and `exhaustion_policy=fail_closed`. Therefore the method cannot satisfy its own G1 feasibility invariant on the registered cohort.

This is not repaired by increasing depth after observing the failure: that would change the preregistered latency/scale intervention and consume the same fresh cohort adaptively.

## Outcome-access boundary

- A and R were opened as authorized for representation/training.
- Target-blind V descriptors were published.
- Zero V candidate manifests were completed.
- V relevance was not joined.
- V preference/power outcomes were not opened.
- No T descriptor, manifest, raw test, metric, or latency artifact was created.
- No runner completion candidate or external completion marker exists.
- Runner, launcher child, and locks exited/released; asynchronous ledgers remained empty.

The lack of an external completion marker is expected because the runner failed before publishing a completion candidate. The persisted launcher failure is the terminal record.

## Evidence hashes

| Evidence | SHA-256 | Bytes |
|---|---|---:|
| Runner stderr | `d78978759931900d59060337ec9336183bca45b7910ab1752dc3b395241590a8` | 1,041 |
| External failure record | `07ed6a65c32496b26609da23b0fb44471f39908bfb6c0257b73c236f19f0a52b` | 1,521 |
| Launch record | `2264f6b704ab7f7c17871d2e283838aa83e1836c96ecbfa6b8974fe5e11d0631` | 3,001 |
| Runner event ledger | `1526850e2f86906ba34d66aec243d0c9394195ece8a2336aa6f91f948b83faae` | 1,554 |
| Target-blind V descriptors | `c92677cf38287cfca4c3d5f72800fd0d7930f88411dff5b59f3ac1ce1a785eba` | 1,967,507 |
| Empty runner async ledger | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| Empty launcher async ledger | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |

## Phase-1 reset constraint

Cycle 5 must make fixed candidate feasibility a construction-level guarantee rather than an empirical hope. It may not tune a deeper search depth on this cohort. A successor must either use an exact masked top-k operation, define a depth from a prospective worst-case history bound, or reformulate the branch budget so it is always achievable while preserving a meaningful scale/latency question.
