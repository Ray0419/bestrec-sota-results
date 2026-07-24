# E-E — closest-baseline benchmark-or-exclusion (setup)

**Goal.** The audits repeatedly say broad novelty is indefensible without a
head-to-head against the closest established methods. E-E benchmarks
**AlphaFuse** ([Hugo-Chinn/AlphaFuse](https://github.com/Hugo-Chinn/AlphaFuse),
SIGIR 2025 — learns ID embeddings in the null space of language embeddings) and
**LLM2Emb** (ESWA, DOI 10.1016/j.eswa.2026.133375 — popularity-gated ID/LLM
long-tail fusion) under **our exact protocol**, or writes a documented
protocol-based exclusion if a faithful port is infeasible.

This directory is the isolated setup. It does not touch the pinned main env,
does not write into the governed tree, and (setup stage) makes no claim.

## What is ready

- `export_ar2023_for_baselines.py` — **DONE + verified.** Exports our exact
  5-core LLOO split into a clean interchange format
  (`export/<cat>/<cat>.sequences.jsonl` + `.items.jsonl` + `.manifest.json`).
  Verified: Office_Products 223,308 users / 77,551 items and Video_Games
  94,762 / 25,612 both **match** our recorded run counts, 100% title coverage.
  Same users, items, leave-last-out targets and full-catalog ranking universe
  as our numbers — so any baseline result is apples-to-apples.
- `setup_ee_env.sh` — creates `ee_baselines/.venv_ee` (isolated), clones
  AlphaFuse, installs its deps, GPU-checks.

## Run it

```bash
# 1. isolated env + external clone
bash ee_baselines/setup_ee_env.sh

# 2. export our split (Office = counted category; VG = largest transfer)
python ee_baselines/export_ar2023_for_baselines.py \
    --categories Office_Products Video_Games --verify

# 3. adapt AlphaFuse's loader to export/<cat>/*.jsonl, then train/eval it
#    (this loader glue is the remaining engineering step — do it locally,
#     it is free to debug; only the final training runs want a bigger GPU).

# 4. record NDCG@10 / HR@10 per category from AlphaFuse's full-catalog eval.
```

## Compute

- The **port/adaptation and smoke test are CPU/small-GPU work — do them
  locally** (your idle local GPU is enough to prove the pipeline).
- Only the **final multi-seed training runs** benefit from a rented A100/L40,
  and only once the pipeline is proven. Do not rent ahead of a working port.

## Governance (frozen-before-report)

E-E is claim-bearing the moment a head-to-head number is reported. Therefore:

1. **Freeze `PREREG_EE.md` + `adjudicate_ee.py` BEFORE reporting any number**
   (committed-before-existence): frozen metric (NDCG@10/HR@10, full-catalog
   LLOO), seeds, the exact export hashes (in each `manifest.json`), the
   comparison wording, and the decision rule.
2. **No SOTA / superiority wording.** The only admissible statements are
   point-estimate comparisons under our environment caveats (same class as the
   two counted comparisons) and honest "we do / do not exceed their number."
3. **Exclusion path (equally valid):** if AlphaFuse/LLM2Emb cannot be run
   faithfully under our full-catalog LLOO split within documented constraints
   (e.g. their protocol uses sampled negatives, a different core, or an
   unavailable LLM), write the **executable exclusion note** — the exact
   protocol mismatch, what was attempted, and why the comparison would be
   apples-to-oranges — which the audits accept in lieu of a benchmark.
4. Endpoints obey the standing seal rules (no plaintext metric committed before
   adjudication; the seal hooks + CI apply).

## Status

- [x] data exporter (verified on Office + VG)
- [x] isolated-env + clone setup script
- [ ] run `setup_ee_env.sh` (fetches external code — do when ready to port)
- [ ] AlphaFuse loader adapter + local smoke test
- [ ] freeze PREREG_EE / adjudicate_ee, OR write the exclusion note
- [ ] (only then) final runs, adjudicate, integrate
