# CABLE-PREF cycle-5 terminal outcome

Date: 2026-08-07 (Australia/Sydney)

Decision: **KILLED; NO RERUN OR REPAIR; PHASE 5 FORBIDDEN**

## Authoritative event

The sole digest-authorized command recorded in
`experiments/cable-pref-preoutcome-audit.md` consumed the persistent one-time
claim and launched the frozen runner. The runner exited with code 1 after
85.40 seconds. The launcher then published a non-authoritative external failure
record and exited 1. No completion candidate or external completion marker was
published.

The runner stderr terminates with:

```text
IntegrityError: Batched full-row FAISS retrieval disagrees with matrix lexsort oracle
```

The exception arose in `exact_faiss_masked_topk_batch` while
`build_R_target_blind_arrays` was constructing the first target-blind `R`
candidate surface. Under preregistered G1, the FAISS path and independent
float32 matrix/stable-sort oracle had to agree on every ID and order. They did
not. The preceding elementwise score comparison passed at
`rtol=2e-6, atol=2e-6`, so a within-tolerance difference changed at least one
masked top-200 ID or ordering. The artifacts do not reveal which case. This is
a terminal G1 failure regardless of whether the disagreement was caused by
floating-point accumulation, a near-tie, or implementation semantics.
Diagnosing that distinction may inform a future design, but changing or rerunning
CABLE-PREF is prohibited.

## Access boundary and published state

- The structural cohort pass and the authorized `A` rescan completed.
- SentenceTransformer metadata encoding, BPR training, and immutable index
  publication completed.
- The target-blind `R` manifest was not published.
- `R` ratings/items were therefore never loaded; `V` and `T` were also unopened.
- No adapter checkpoint directory, runner completion candidate, verifier report,
  or `CABLE_EXTERNAL_COMPLETE_*.json` marker exists.
- Both runner and outer locks were released, and no matching process remains.
- The one-time claim remains as the durable proof that retry/resume is forbidden.

## Evidence hashes

| Evidence | SHA-256 |
|---|---|
| external launch record | `26b014f5684dc64aa06bb7c6a3c0da61fcf485df7f9d79a7b2e0905de44ae08d` |
| runner stderr | `20696b64c4d0ffaaacd2b9c0fd20a35c2ab08a50b552b05521a09d9d343ea4ac` |
| external failure record | `0ce0121a14900f80eeb8a940c19133a15d05e3166e22967257782d95309ea0b1` |
| runner process record | `7b447d0d41ef28271fa8d6ed033c6e2fdcf170689bcd841f2898fee32e76a781` |
| cohort record | `eb68c38d8e0b63b3663d8b65c722695a9eff6ab28db256bac13b579f44968126` |
| BPR diagnostics | `188bf405190229789c61e9ae7476ce4b190248280d3e84553148a95653b32869` |

The ignored raw launch artifacts remain at
`experiments/launches/cable-pref-poc-v1-cycle5-20260807.*`; runner-owned files
remain under
`C:\Users\rayxc\Documents\R\_bestrec_run\cable_pref_poc_runs\cable-pref-poc-v1-cycle5-20260807`.

## Phase-1 reset constraints

1. A successor may use FAISS for candidate generation, but cross-backend
   floating-point identity cannot itself be a scientific promise gate. Define
   one canonical ranking implementation and audit recall/set semantics with
   explicit score tolerances and deterministic tie handling.
2. The successor must be a new hypothesis, not a corrected CABLE run. It may not
   reuse CABLE's consumed one-time claim, selected cohort, or outcome path.
3. Feasibility tests must cover real frozen embeddings and representative query
   arithmetic before authorization, while all quality labels remain unopened.
