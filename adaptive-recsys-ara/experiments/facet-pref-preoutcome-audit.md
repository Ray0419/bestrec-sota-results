# FACET-PREF Pre-Outcome Audit

Date: 2026-08-07
Status: **prospectively frozen; no FACET-PREF outcome has been opened**

## Purpose and authorization boundary

This audit freezes the cycle-4 implementation before the one authorized proof-of-concept execution. The runner may open the fresh, preregistered eligible-user slice `[2000:4000]` only through the source-bound launcher. The runner is not authoritative: it must always write top-level `PROMISING=false`. Only the separate post-exit verifier may publish an `EXTERNAL_COMPLETE_*` marker after independently replaying the registered evidence.

The exact policy remains:

- if the pre-`T` validation-power audit fails, stop before opening `T`, kill FACET-PREF, and return to Phase 1;
- if any externally replayed G1--G9 gate fails, kill FACET-PREF and return to Phase 1;
- proceed to Phase 5 only if the external marker records the conjunction G1--G9 as true;
- do not retry, repair, or tune from this outcome.

## Frozen source bindings

| Artifact | SHA-256 | Lines | Bytes |
|---|---|---:|---:|
| `src/facet_pref_poc.py` | `3ede7d2f387c3ca5db7c1882b8f898c4d827d06e23403651599ba39901b2461c` | 3,608 | 162,685 |
| `src/launch_facet_pref_and_verify.py` | `4b76a1f03a5dccb135c20db4c7b488ef1d9e50f34dd975a69b481536736a464c` | 4,202 | 187,885 |
| `src/configs/facet_pref_poc_ml1m_v1.json` | `28a933dd671c2d7d994b25b56acb554c72ae4500c352b670e67d7e857fa62d5d` | 403 | 15,116 |
| `experiments/facet-pref-protocol-v1.md` | `03af0f865c97d7489eac1c11805705224bdf00f2f0f2d97d6a6bae030677527e` | 446 | 23,239 |
| `architecture-facet-pref.md` | `884076435a96ce42892563c98a9339ec70f98ddf459257aff9e182459fae4c56` | 366 | 16,207 |
| `research-question-cycle4.md` | `5aeff2cf11ee248b458f4f5d45c6afbdb52e3ef9beadf5c91d61124f6b84c25d` | 290 | 15,217 |
| `literature/cycle4-survey-and-ideation.md` | `a871da9cc8a6f5ed8e813f3a5b7fdaf2b0636a82121f6ce701507ce5c439d550` | 187 | 11,902 |
| `src/caper_poc.py` numerical dependency | `9ddd41c2db74424dfed8672933144147af6f9c6b49745ada13611c2cbac1588c` | 3,572 | 146,598 |

Registered MovieLens 1M archive SHA-256: `a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20`.

The runner independently constructs a protocol fingerprint from the protocol name and seven runner-bound source hashes. After validation selects the BPR variant and shared alpha, it constructs an execution fingerprint from the protocol fingerprint, dataset hash, sorted FACET cohort identity hash, selected variant/alpha, and three optimization seeds. The verifier independently reconstructs both fingerprints. Protocol fingerprints are checked in the result, raw V/T/latency evidence, and every V/T manifest; execution fingerprints are checked in the runner candidate and result, which are the only runner schemas that carry them.

## Outcome-free implementation checks

All commands exited zero under `C:\Users\rayxc\Documents\R\_bestrec_run\.venv\Scripts\python.exe`:

```text
python -B -m py_compile src/facet_pref_poc.py src/launch_facet_pref_and_verify.py
python -B src/facet_pref_poc.py --validate-config
python -B src/facet_pref_poc.py --self-test
python -B src/launch_facet_pref_and_verify.py --self-test
git diff --check -- src/facet_pref_poc.py src/launch_facet_pref_and_verify.py
```

Runner self-test: 13/13 checks true, including `target_outcomes_accessed=false`, deterministic facets, exact 200 BPR-novel semantic candidates, per-iteration canonicalization, lower-canonical duplicate ownership, per-item ownership evidence, finite adapter training, and identity behavior of the zero-output adapter.

Launcher/verifier self-test: 7/7 checks true, including deterministic pair outcome/bootstrap replay, non-authoritative all-pass runner handling, overlap-adjusted quota/backfill replay, recursive hash closure, exclusive ownership locks, and atomic no-overwrite publication.

Producer/consumer parity was checked field by field:

- raw validation NPZ: 47/47 fields;
- raw test NPZ: 48/48 fields;
- raw latency NPZ: 7/7 fields;
- six validation manifests and three test manifests use exact registered inventories.

Two independent source audits found no remaining launch-blocking P0/P1 error after the final one-line stored-difference key correction.

## Defects found and corrected before outcome access

| Area | Pre-outcome defect | Resolution |
|---|---|---|
| Controls | Early control names could diverge between config, runner, and verifier. | Exact eight-method registration and synthetic equality check. |
| Facets | Label swaps during spherical two-means could create false convergence. | Canonicalize facets after every assignment/update iteration. |
| Retrieval ownership | A higher facet could claim an item returned anywhere in the lower facet row. | Lower-canonical ownership over complete eligible rows, per-item owner evidence, and overlap/backfill replay. |
| Retrieval evidence | Aggregate counts alone could not prove the 200-slot semantic allocation. | Store all semantic owners plus six diagnostics for every request/method/seed; replay quota and backfill arithmetic. |
| Pair universes | Stored pair counts were insufficient to establish R/V/T identities and caps. | Store raw events; independently enumerate natural pairs, directions, per-user caps, global R cap, and pair-pool rows. |
| Validation selection | Stored selected BPR/alpha could be trusted accidentally. | Reconstruct all six V manifests, five alpha-grid rankings, relevance metrics, tie breaks, and final locks. |
| Test binding | Raw T arrays could drift from pre-target manifests. | Bind the exact three-manifest inventory and compare every candidate, score, ranking, quota, owner, and diagnostic array. |
| Metrics and gates | Runner summaries could become self-certifying. | Recompute per-user metrics, paired bootstraps, G1--G9, and the candidate conjunction from raw evidence. |
| Verdict authority | An all-pass runner conjunction could conflict with the required non-authoritative top-level verdict. | Require runner `PROMISING=false`; compare separate `runner_candidate_promising`; external marker alone owns the verdict. |
| Publication | Direct exclusive writes were not crash-atomic. | Fsync a same-directory temporary, atomically hard-link without overwrite, then clean the temporary. |
| Environment/provenance | Interpreter, thread environment, archive/extraction, and source snapshots needed exact binding. | Source/Interpreter/environment hashes, recursive closure, authenticated post-T source reparse, and strict process/lock/log checks. |
| Stored V differences | A singular/plural key typo skipped one redundant comparison. | Match runner key `seed_averaged_spce_differences`; lower bounds and pass probabilities remain independently replayed. |

## Residual limitation accepted prospectively

The verifier proves exact fixed budgets, uniqueness, prefix-unseen status, BPR novelty, lower-facet ownership, raw component fusion, rankings, immutable matrix/index hashes, and manifest timing. It does not independently invoke FAISS again to regenerate every depth-700 returned row. The returned rows are instead constrained by source-bound runner code, immutable index artifacts, candidate arrays, ownership diagnostics, and recursive hashes. This limits the integrity claim to source-bound deterministic execution plus extensive raw replay; it is not a second implementation of FAISS.

## Prospective launch decision

Phase 3 is complete. The frozen code is authorized for exactly one append-only FACET-PREF PoC launch against the registered local archive. No fresh-cohort MovieLens events, FACET R/V/T targets, scientific metric, or gate result was accessed while preparing this audit.
