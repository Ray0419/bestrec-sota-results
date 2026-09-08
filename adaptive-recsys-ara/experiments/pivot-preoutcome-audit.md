# PIVOT Cycle-6 Pre-outcome Audit and One-shot Authorization

Date: 2026-08-07 (Australia/Sydney)

## Decision

PIVOT Phase 3 is source-locked and approved for exactly one append-only Phase 4 PoC launch. Phase 5 remains forbidden unless the launcher publishes the sole authenticated external completion marker with `PROMISING=true` and every preregistered gate G1-G9 true.

No Cycle-6 R, V, or T item identity, rating, pair, candidate, metric, or outcome was opened during design, implementation, audit, or qualification. The final qualification used only the frozen item embedding matrix and machine-level timing. It records `archive_opened=false` and `user_outcomes_accessed=false`.

## Frozen scientific and executable sources

Git commit: `44ab96b45f7dd7b8599b199a6fea6a42addcd48d`

| Artifact | SHA-256 |
|---|---|
| `literature/research-question-cycle6.md` | `7ebce20eff80659969ab5c32697a3e80f16356cdc7fec5658c533e933cec9e6f` |
| `architecture-pivot.md` | `e038eab2d2b6ac9cef68c5ed97d3f3c289eb632733c67bf1cfc30bd1a97e6cc7` |
| `experiments/pivot-protocol-v1.md` | `9de86ce435dc63b2997072010d234a8f615f35beaa21da1ff5a02b8952540735` |
| `src/configs/pivot_poc_ml10m_v1.json` | `819d005e2696751293cf62f48196c50bd5cae0f5c5ee960c77e103838e9e5a6c` |
| `src/pivot_poc.py` | `f14cc2b9608dfc98bbc59dbcdc9e66345c85b6fb05d9f11d966c40e38b67845f` |
| `src/launch_pivot_and_verify.py` | `f2538dc6cc3503805446ccff66435f7610bc4117dab4eec4f8f85260da52784c` |

The executable runtime is `C:\Users\rayxc\Documents\R\_bestrec_run\.venv\Scripts\python.exe`, SHA-256 `bad34b1f39dad6a375e594aaf006fe84cd96a7ae46f6f2fa84c0536003234ac9`.

## Frozen external inputs

| Input | Bytes | SHA-256 |
|---|---:|---|
| `adaptive-recsys-ara/data/ml-10m-cycle5/ml-10m.zip` | 65,566,137 | `813c411ccb6122564edfe752e7f80c4dcc5aa25fa94c93622f6877a7ba252862` |
| Cycle-5 exclusion `cohort.json` | 540,884 | `eb68c38d8e0b63b3663d8b65c722695a9eff6ab28db256bac13b579f44968126` |
| Frozen `semantic_vectors.npy` | 16,406,144 | `8ce5877856f5e160893a2cfcd00ebb8efc783729ae1616290b530b5d454c9768` |

## Prospective audits

Two independent implementation audits reviewed the runner/launcher contract, leakage barriers, stage ordering, metric and power estimands, exact work accounting, latency schedule, artifact schemas, append-only authority, and independent G1-G8 replay. Seven identified blockers were corrected before source lock: safe extraction, V choice/power ordering, method-major latency ordering, batch-1 canonical FAISS replay, qualification bindings, archive hashing before reads, and the complete launcher CLI. The final re-audit returned `APPROVED` with no remaining P0/P1 issue.

Outcome-free syntax compilation, runner config validation, runner synthetic self-test, launcher config validation, and launcher synthetic self-test all passed with zero stderr. The runner passed 13 synthetic invariants and the launcher passed 12 authority/replay invariants.

The final target-blind qualification is:

- path: `C:\Users\rayxc\Documents\R\_bestrec_run\pivot_poc_preflight\qualification_final_source_lock.json`
- SHA-256: `c7439d3524d7717cc79ba131416cc90488b40026102f1503af3126f0c7a80958`
- runner SHA-256 recorded: `f14cc2b9608dfc98bbc59dbcdc9e66345c85b6fb05d9f11d966c40e38b67845f`
- config SHA-256 recorded: `819d005e2696751293cf62f48196c50bd5cae0f5c5ee960c77e103838e9e5a6c`
- repeated construction: identical assignment, centroids, and all 32 serialized FAISS index hashes
- assignment SHA-256: `9f747c933f75c63967a8384b956d07e601842d07f887179fcf76ab11cd747b73`
- centroid SHA-256: `2f8945291264fa211f3e29e9d127a45e9c4ac13c67a9b8426cd49462c4fda2be`
- physical work: 32 coarse dots, four probes, 1,336 shard-slot dots, and 100 candidates even after an adversarial 300-item history
- latency: worst PIVOT p95 `0.938390 ms`; worst ratio `1.235943x`; both below the locked `3.0 ms` and `1.5x` ceilings
- environment: Windows kernel affinity mask 1 confirmed; observed peak RSS 806,195,200 bytes

One manual qualification invocation was rejected by argument validation before producing an artifact because it supplied a source-hash argument that qualification mode intentionally forbids. It accessed no archive or outcomes. The successful final qualification above is the only artifact admitted as authorization evidence.

## One-shot execution binding

- external output root: `C:\Users\rayxc\Documents\R\_bestrec_run\pivot_poc_runs`
- run ID: `pivot-poc-v1-cycle6-20260807`
- one-time claim: `C:\Users\rayxc\Documents\R\_bestrec_run\pivot_poc_runs\PIVOT_ONE_TIME_LAUNCH_CLAIM.json`
- run directory: `C:\Users\rayxc\Documents\R\_bestrec_run\pivot_poc_runs\pivot-poc-v1-cycle6-20260807`

At authorization, the output root, claim, and run directory did not exist. The root may be created empty immediately before launch. Any pre-existing claim or run directory invalidates authorization.

The sole authorized command is:

```powershell
& 'C:\Users\rayxc\Documents\R\_bestrec_run\.venv\Scripts\python.exe' -B -u 'C:\Users\rayxc\Documents\R\adaptive-recsys-ara\src\launch_pivot_and_verify.py' --authorized-launcher-sha256 f2538dc6cc3503805446ccff66435f7610bc4117dab4eec4f8f85260da52784c --config 'C:\Users\rayxc\Documents\R\adaptive-recsys-ara\src\configs\pivot_poc_ml10m_v1.json' --protocol 'C:\Users\rayxc\Documents\R\adaptive-recsys-ara\experiments\pivot-protocol-v1.md' --output-root 'C:\Users\rayxc\Documents\R\_bestrec_run\pivot_poc_runs' --local-dataset-archive 'C:\Users\rayxc\Documents\R\adaptive-recsys-ara\data\ml-10m-cycle5\ml-10m.zip' --run-id 'pivot-poc-v1-cycle6-20260807'
```

There is no authorization to resume, repair, rerun, substitute a cohort, alter a threshold, rescue a partial seed, or manually override the external verdict. Any failure, missing/nonfinite/unsupported gate, absent authenticated marker, or `PROMISING=false` kills PIVOT and returns the sprint to Phase 1.
