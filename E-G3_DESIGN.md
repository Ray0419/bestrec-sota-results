# E-G3 DESIGN NOTE — the clean, countable sparse-warm replication (DESIGN stage; NOT yet frozen, NOT launched)

**Status: DESIGN only.** This note resolves the three structural problems that
made E-G1 and E-G2 exposed/uncountable, so a later tick can BUILD the holdout,
then FREEZE `PREREG_COLDFUSE_V3.md` + `adjudicate_coldfuse_v3.py` BEFORE launch
(committed-before-existence standard). Nothing here is a claim; no endpoint
exists yet. Authored per audit 2026-07-24 03:59 P1 and the maintainer
"improve on your own judgment" directive (2026-07-21).

## Why E-G1/E-G2 could never be counted (the lesson)

Both campaigns evaluated a **repeatedly-exposed fixed test split**, and both
leaked endpoints before their one-time adjudication (E-G1 by mid-campaign
commits/reports; E-G2 by a `git add -A` sweep). Fresh optimizer seeds on an
already-exposed split establish only *seed stability*, never independent
confirmation. E-G3 must therefore change the ESTIMAND (a genuinely untouched
holdout) AND the CUSTODY (endpoints unreachable by tuning code and by git)
before it can be countable.

## Problem 1 — a genuinely untouched holdout (new estimand)

Build a **temporal holdout** never used by any prior campaign, plus an
**item-arrival** subset for a real cold claim:

1. **Global temporal cut.** Re-preprocess AR2023 5-core from raw with a fixed
   calendar cutoff `T*` (chosen from the data's time span, frozen in the
   prereg). Training/validation use only interactions with timestamp `< T*`;
   the **test target is each eligible user's first interaction at `>= T*`**
   (a forward-in-time next-item task), scored full-catalog. This split has
   never been evaluated, so it is not "exposed."
2. **Item-arrival (cold) subset.** Within the holdout, mark items whose FIRST
   appearance in the whole dataset is `>= T*` as **arrival-cold** (they have
   zero training interactions by construction). A positive metric on this
   subset is the ONLY thing that can support a true cold-item / f0 claim; the
   full-catalog reranker on the warm split cannot.
3. **Candidate generation for the cold claim.** To make arrival-cold items
   retrievable at all, the cold arm needs a **text-only semantic candidate
   generator** (ANN index over the frozen MiniLM item embeddings) combined
   with the collaborative candidates under a frozen dedup + score-calibration
   rule. Without a retrieval branch, arrival-cold items are unreachable and
   f0 stays a null — which is itself a valid, publishable boundary, stated as
   such.
4. **Provenance.** The new split is generated once by a committed
   `build_temporal_holdout.py`, every output hashed; the raw-data SHA and the
   frozen `T*` are recorded so the split is reproducible but the TEST LABELS
   are withheld (see Problem 2).

## Problem 2 — custody: endpoints unreachable by tuning code AND by git

`.gitignore` alone is insufficient (a `git add -f` bypassed it). Structural
custody:

1. **Withheld test labels.** `build_temporal_holdout.py` writes the test
   *inputs* (user histories `< T*`) to the repo, but the test *target labels*
   go ONLY into a sealed blob **outside the git worktree** (e.g.
   `%LOCALAPPDATA%/bestrec_sealed/eg3_labels.enc`, AES-encrypted to an
   adjudication key the training/tuning code does not possess). Training and
   validation selection are structurally incapable of reading test labels.
2. **Endpoint storage outside the repo.** The confirm evaluator writes metric
   payloads to the same out-of-repo sealed directory, never under the git
   tree. Only **signed completion hashes** (no values) may be committed before
   the family is sealed.
3. **Enforced by hooks + CI, not honor system.**
   - `pre-commit` and `pre-push` hooks (installed by a committed
     `cloud/install_seal_hooks.sh`) REJECT any staged path matching the
     endpoint patterns (`results_*COLDFUSE3*`, `*.finaleval.*`, `*_labels*`,
     `*_sealed*`) and reject `git add -f` of them.
   - A CI deny-rule mirrors the hook so a hook-less clone still fails.
   - `run_*` drivers refuse to run `git add`/`git push` at all (the E-B
     lesson): exfil is only via the sealed importer.
4. **One-time sealed adjudication.** `adjudicate_coldfuse_v3.py` is the ONLY
   reader: it decrypts labels + endpoints, runs the metadata-only preflight
   (Problem 3), and emits the verdict exactly once.

## Problem 3 — the 8 hardened adjudicator gates + structural nulls

From the audit's confirmed-defect table, the successor MUST implement:

1. **Metadata-only sealed preflight FIRST** — open no metric-bearing file
   unless the exact complete set, per-file hashes, one terminal campaign
   event and a clean launch boundary all pass.
2. **All-eight-seed structural nulls** — encode validation-infeasible seeds as
   `SEL=REF`, all deltas 0, KEEP the seed (frozen df, no outcome-dependent n).
3. **Exact ledger-event schema** — one launch, exact JSON argv per step, one
   success per planned step, no unresolved failure, one terminal event.
4. **Hash the actually-loaded checkpoint** at eval time and match base +
   ledger + final-eval + sealed-manifest digests.
5. **Exact sidecar sets + per-file hashes** for every base/fusion/checkpoint/
   confirm/NPZ; undeclared or mismatched extras fail.
6. **Full finite/shape/bin validation** — schema, exact system names, shapes,
   finite values, bins recomputed from frozen data, every aggregate, before
   any analysis (NaN must not evade `abs()>tol`).
7. **Full C1–C4 persistence** — paired estimates, t/df/p/CI, sign diagnostics,
   all four control summaries; safe behavior for near-zero/negative
   denominators.
8. **Conditional f0 wording + atomic bundles** — f0 wording fires only when
   both REF and SEL HR/NDCG@10 are exactly 0 (scoped to k); write one atomic
   hashed bundle per pipeline (JSON+NPZ+checkpoint), resume only a fully
   verified bundle.

## Statistics (frozen at prereg time, not here)

- **Uncertainty hierarchy:** seed replication, split replication, domain
  replication are DISTINCT. Use ≥8–10 paired seed blocks **within each of
  multiple untouched temporal blocks** (e.g. two cutoffs `T*_1 < T*_2`);
  report blocked/hierarchical uncertainty, not only optimizer-seed t.
- **Controls in the same paired seed/environment blocks:** aligned text,
  exact-frequency permutation, frequency-only prior, norm+covariance-matched
  random features, pure-text retrieval, and a strong learned adaptive-fusion
  baseline (AlphaFuse / LLM2Emb-class) — benchmark-or-documented-exclusion.
- **Utility:** freeze an application-supported utility + mid/head
  noninferiority margins; select on lower confidence bounds; retain a
  zero-delta reference when no policy is feasible; plot the validation Pareto
  frontier.
- **Environment:** pin a container digest + lockfile; one job per GPU;
  hash-chained argv/events; bind solver/array/item-order/code/env/residual
  digests into every result.

## Frozen-wording sketch (to be finalized in the prereg)

W3-POS / W3-NEG / W3-EQUIV / W3-INC on the temporal-holdout f1–5 endpoint,
each stating estimator, n, block structure, split provenance (untouched
temporal), and control attribution. A SEPARATE arrival-cold wording for the
retrieval-branch f0 result (or its null). No SOTA wording; the counted set
(MI V2, Office V3) is untouched; E-G1/E-G2 remain exposed/descriptive.

## Build order (future ticks)

1. `build_temporal_holdout.py` + sealed-label writer (verify counts/hashes;
   no labels in repo).
2. `cloud/install_seal_hooks.sh` + CI deny-rule; verify a `git add -f`
   endpoint is rejected.
3. Retrieval branch (ANN over MiniLM) + frozen dedup/calibration for the cold
   arm.
4. `adjudicate_coldfuse_v3.py` with all 8 gates; unit-test the preflight and
   structural-null path on synthetic bundles.
5. FREEZE `PREREG_COLDFUSE_V3.md` + adjudicator (committed BEFORE launch) →
   launch one job per GPU → one-time sealed adjudication → integrate frozen
   W3 wordings.
