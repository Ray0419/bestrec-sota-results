# CABLE-PREF pre-outcome audit

Status: **AUTHORIZED_ONCE - ONE OUTCOME LAUNCH ONLY**

Cycle: 5, Phase 4

Audit scope: source/config/protocol integrity and outcome-blind launch readiness

Dataset or outcome access while preparing this audit: **none**

This is a prospective, fail-closed checklist. A checked item records evidence
already established without opening ML10M. An unchecked item remains a hard
authorization blocker. Completing implementation does not itself authorize the
one permitted outcome run.

## A. Frozen research objects

- [x] The Phase-2 question, estimands, controls, thresholds, and G1-G9 are
  written before outcome access.
- [x] The runner, config, protocol, question, survey, architecture, and external
  launcher/verifier are identified by exact absolute project-relative paths.
- [x] The launcher contains prospective SHA-256 constants for every frozen
  research object other than itself and checks them in self-test, launch, and
  independent verifier modes.
- [x] The parent launcher records its own hash in the append-only launch record;
  the separate verifier process receives that expected hash and checks it.
- [x] The runner completion candidate recursively binds every runner-owned
  artifact before verifier-owned files exist.
- [x] The final independent read-only integrity review reported no P0 or P1
  defect.
- [x] All locked objects are committed, and the hashes below were rechecked
  against commits `3a802c08` and `c12a7e74`.

Prospectively recorded SHA-256 values:

| Research object | SHA-256 |
|---|---|
| `src/cable_pref_poc.py` | `e73e19fed6d13efa7752ee6a603fba9f8f935f76b864fcb9e252be39a1866dc5` |
| `src/configs/cable_pref_poc_ml10m_v1.json` | `81b2bdc2645ee11e26f1e95b2c68cf4fb9412b3da7b6363bb7bc7d0e5c658cf4` |
| `experiments/cable-pref-protocol-v1.md` | `9789d57dc6675ff16cbd7bfbf2f8d8879b1f8e9dc4599e30de3804ce7ae83ae4` |
| `literature/research-question-cycle5.md` | `38c4ba4f21c3ed989dbf525280b71dcbd0ac1460e0adc8f84d6b8caa25df244e` |
| `literature/cycle5-survey-and-ideation.md` | `a85a7059776412cdd82b39f621c19efcbbc693207fba4e75ff76982a0ac01f61` |
| `literature/cable-pref-architecture.md` | `038c74b2d258d5dae871b9d3d40cae7c36d4eeb69a1d5199fc3bb51d4dbef919` |
| `src/launch_cable_pref_and_verify.py` | `b46a89572e24a5e88ae12d5d1664f481f207dc600fc61fb4e35d2d17ff96e338` |

The audit file is intentionally not self-hashed inside itself. Its final hash
must be recorded externally after the authorization decision is frozen.

## B. Outcome-blind implementation review

- [x] No ML10M archive was extracted, listed, parsed, counted, or sampled while
  this launcher/verifier and audit were written or checked.
- [x] No cycle-5 cohort identity, event, label, pair, score, candidate, metric,
  latency value, result, or completion marker was opened.
- [x] Synthetic self-tests contain no dataset-derived outcome constant and run
  without an archive argument.
- [x] Hyperparameters, pair caps, bootstrap seeds, exact tie rules, latency
  limits, and all gate thresholds are bound by config and verifier contracts.
- [x] BPR uses 64 dimensions, 8 epochs, and an exact 200,000-update per-epoch
  cap across question-adjacent architecture, protocol, config, runner, and
  verifier.
- [x] Dataset loading follows one structural pass plus only the registered
  stage-authorized rescans. Structural rows retain no rating payload.
- [x] R/V/T item and rating fields are unavailable before the corresponding
  target-blind manifest is durably published.
- [x] Every participating agent has supplied a final outcome-blind attestation.

Root, implementation reviewer, and independent integrity reviewer attest: **no
archive member, extracted data, or outcome artifact was accessed**. Only the
already registered archive byte count and cryptographic digests were checked.

## C. Exact retrieval and target blindness

- [x] Eligibility requires the registered unseen-catalog floor.
- [x] BPR candidate generation is stable exact masked top-200 on the
  prefix-unseen domain.
- [x] Semantic candidate generation is stable exact masked top-200 on the
  complement of the prefix and frozen BPR branch.
- [x] The two branches are exactly 200 and 200 unique items, disjoint, and form
  one 400-item candidate set.
- [x] Float32 score matrices, masks, stable item order, branch identities, and
  cutoff identities are included in the exact raw evidence inventory.
- [x] The verifier reconstructs both branches using full-matrix stable top-k;
  it does not trust runner IDs, counts, or pass booleans.
- [x] R/V/T manifests are fsynced, content-hashed, and target-blind before their
  stage labels are joined.
- [x] The verifier reopens the authenticated archive after runner exit and
  independently reconstructs histories, queries, candidates, pairs, and labels.
- [x] No target endpoint can be injected into a candidate set.

## D. Independent scientific replay

- [x] The validation raw schema is exact and contains 74 unique fields.
- [x] The test raw schema is exact and contains 56 unique fields.
- [x] The latency raw schema is exact and contains 14 unique fields.
- [x] R events and pairs, V binary relevance and exact preferences, and T
  relevance/preferences are independently reconstructed from authenticated raw
  data and compared with the bound arrays and manifests.
- [x] Natural pair enumeration, low/high canonical identity, deterministic caps,
  pair hashes, selected directions, and per-user counts are replayed.
- [x] Admission metrics use method-independent denominators.
- [x] sPCE@10 assigns both-hidden and hidden-chosen outcomes zero and is
  recomputed from raw top-10 IDs.
- [x] User-macro metrics, stronger-baseline selection, alpha validation, and
  training/control diagnostics are independently replayed.
- [x] All 21 raw/trained adapter checkpoints are loaded, shape/finite checked,
  memory-hash replayed, and used to reconstruct every V/T semantic query and
  learned boundary from authenticated prefix descriptors.
- [x] BPR and semantic full-score oracle replay uses bounded batch-64 GEMMs;
  exact per-request masks, stable top-k IDs/order, and stored component scores
  are still checked independently.
- [x] Paired confidence intervals are regenerated from finite common-user
  differences with exactly 10,000 draws and the registered seed.
- [x] Centered feasibility power is regenerated with exactly 1,000 outer by
  1,000 inner draws for every registered effect and seed.
- [x] G1-G9 are recomputed exactly, including pre-T kill conditions and the
  latency, immutability, support, control, and changed-surface requirements.
- [x] A failed feasibility/support check forbids T access and yields the
  preregistered kill verdict. The project cannot proceed to Phase 5 unless the
  independent external conjunction passes.
- [x] Runner `PROMISING` remains literal `false` and non-authoritative.

## E. Matched controls and anti-gaming checks

- [x] BPR, raw exact-complement hybrid, order-only, admission-only, full
  CABLE-PREF, shuffled-direction, and boundary placebo/control variants are
  bound to the registered shared surfaces.
- [x] Semantic controls share the exact complement operator, 200+200 budget,
  index, vectors, fusion coefficient, and tie rule.
- [x] Trainable controls have matched parameter counts, pair presentations,
  optimizer steps, initialization, clipping, and checkpoint selection.
- [x] Query/item normalization, zero unsupported BPR factors, and bounded adapter
  displacement are replayed.
- [x] Complement counts, cutoff/action ties, pair coverage, admission-change,
  and changed top-10 diagnostics are published and checked.
- [x] Conditional uplift cannot pass without the registered unconditional
  support and coverage floors.

## F. Windows-safe, append-only authorization chain

- [x] The only registered interpreter is
  `C:\Users\rayxc\Documents\R\_bestrec_run\.venv\Scripts\python.exe`, invoked
  with `-B -u`.
- [x] CPU/thread/offline environment variables are fixed before numerical or ML
  imports; Torch intra/inter-op thread counts are one and data workers are zero.
- [x] The run ID is one safe path component and its run directory must be absent.
- [x] A persistent one-time claim is published only after both preflights pass
  and before outcome launch; retry and resume are forbidden.
- [x] One outer owner lock spans runner, separate verifier, and marker
  publication.
- [x] Runner, verifier, and launcher logs/ledgers are persistent, append-only,
  and required to have zero-byte stderr/error ledgers where registered.
- [x] Hidden Windows child processes are awaited by handle, process exit and
  peak working set are recorded, PIDs must be dead, and inner locks must be
  released.
- [x] Source, interpreter, environment, archive, hardware, power policy,
  execution fingerprint, and recursive artifact hashes are checked across the
  chain.
- [x] The outer command must supply the independently recorded lowercase
  launcher SHA-256; CLI, one-time claim, launch record, source inventory,
  verifier argument, and current launcher bytes must all match.
- [x] Reports and markers use same-directory fsync plus no-overwrite hard-link
  publication.
- [x] Exactly one marker matching `CABLE_EXTERNAL_COMPLETE_*.json` is permitted,
  and this external launcher is its sole publisher.
- [x] Any exception can publish only a non-authoritative failure record.

## G. Outcome-blind validation already run

- [x] Registered Python compiled both `src/cable_pref_poc.py` and
  `src/launch_cable_pref_and_verify.py` successfully.
- [x] Runner `--self-test --config ...` exited 0 with zero-byte stderr, exactly
  32 named checks all true, `archive_opened=false`, `archive_listed=false`, and
  `target_outcomes_accessed=false`.
- [x] Launcher `--self-test` exited 0 with zero-byte stderr and every reported
  boolean (17 total) true, including `adapter_state_query_binding`,
  `authorized_launcher_digest_binding`, `frozen_source_files`,
  `scientific_schema_bound`, and `outcome_launch_authorized`.
- [x] Independent final review re-ran both preflights from the committed tree
  and confirmed the recorded hashes: runner 32/32 and launcher 17/17, both exit
  0 with zero-byte stderr.
- [x] Producer/verifier gate replay matched on 26 synthetic cases, including
  fail-closed missing support; exact lowercase launcher-digest authorization
  accepted only the registered digest.
- [x] The exact one-time outcome command has been appended below and approved.

## H. Authorization decision

Current decision: **AUTHORIZED_ONCE - EXECUTE EXACTLY ONE OUTCOME LAUNCH**.

Every applicable box is checked, all outcome-blind attestations are complete,
and the committed hashes match Section A. The command below is the sole
authorized outcome launch. It may not be repaired, resumed, or rerun after the
one-time claim is created, regardless of outcome or infrastructure failure.

Authorized command:

```powershell
& 'C:\Users\rayxc\Documents\R\_bestrec_run\.venv\Scripts\python.exe' -B -u 'C:\Users\rayxc\Documents\R\adaptive-recsys-ara\src\launch_cable_pref_and_verify.py' --authorized-launcher-sha256 b46a89572e24a5e88ae12d5d1664f481f207dc600fc61fb4e35d2d17ff96e338 --config 'C:\Users\rayxc\Documents\R\adaptive-recsys-ara\src\configs\cable_pref_poc_ml10m_v1.json' --protocol 'C:\Users\rayxc\Documents\R\adaptive-recsys-ara\experiments\cable-pref-protocol-v1.md' --output-root 'C:\Users\rayxc\Documents\R\_bestrec_run' --local-dataset-archive 'C:\Users\rayxc\Documents\R\adaptive-recsys-ara\data\ml-10m-cycle5\ml-10m.zip' --run-id cable-pref-poc-v1-cycle5-20260807
```

Authorization frozen: 2026-08-07 (Australia/Sydney), before outcome access.
