# Pre-registration: causal-FIR breadth on two new categories (FIR-BREADTH)

**Committed BEFORE any run of this campaign.** Frozen at the git commit introducing this file;
runs execute at this commit or a documentation-only descendant (code identity demonstrated via
the per-run embedded code hashes, as in `SOTA_CONFIRM_PREREG_V2_ERRATA.md` E3).

## Question

Does the strictly causal FIR temporal filter (k=8), added to the frozen V2 stack with **zero
per-category tuning**, improve best-by-val full-catalog NDCG@10 on categories never used in its
development? This is an **internal paired contrast** (filter vs no-filter, identical seeds); no
comparator, no floor, no external number is involved.

## Categories

1. **Industrial_and_Scientific** (AR2023 5-core).
2. **CDs_and_Vinyl** (AR2023 5-core). *Feasibility fallback (declared now):* if CDs_and_Vinyl
   cannot run under the frozen config on the 16 GB GPU (OOM at item-chunk 32768 after one retry
   at item-chunk 16384, or >4 h per epoch-20 run), substitute **Toys_and_Games**; if that also
   fails, report the single-category result honestly. Any substitution is disclosed, and no
   third candidate may be tried (no category shopping).

Preprocessing: `_bestrec_run/preprocess_5core_standard.py` (the paper's standard 5-core LLOO
pipeline), MiniLM title caches via the standard encode script. Dataset statistics
(users/items/interactions) are recorded in each run's provenance manifest before any result is
inspected.

## Frozen configuration and commands

Both arms identical to the V2 stack except the filter flags; per category `<CAT>`, seed `<SEED>`:

```
# ARM F (filter, k=8):
_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py <CAT> \
  --epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
  --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu \
  --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2 \
  --causal-filter --filter-kernel 8 --eval-every 1 --seed <SEED> \
  --out _bestrec_run/results_FIRB_<CAT>_filter_seed<SEED>.json

# ARM N (no filter): identical command with `--causal-filter --filter-kernel 8` REMOVED,
#   --out _bestrec_run/results_FIRB_<CAT>_nofilter_seed<SEED>.json
```

- **Fresh seeds (never inspected in any prior run or decision): 20260713, 20260714, 20260715,
  20260716, 20260717.** Disjoint from every previously used seed family (20260522–23,
  20260608–12, 20260618–22, 20260623–27).
- 2 categories × 2 arms × 5 seeds = 20 runs, sequential (one GPU job at a time).
- Headline readout per run: `best_test["NDCG@10"]` at FULL catalog (`n_eval` must equal the
  category's user count; asserted at adjudication).

## Decision rule (frozen)

Per category, over the 5 seed-paired differences `d_s = NDCG@10(F,s) − NDCG@10(N,s)`:

- **CONFIRMED** iff the two-sided 95% Student-t CI of `d` excludes 0 **and** ≥4/5 seeds have
  `d_s > 0`.
- **NULL** otherwise (reported with identical prominence).
- Tail/by-popularity readouts are recorded but are **exploratory only** — no tail claim from
  this campaign regardless of outcome.

## Claim wording (frozen)

If confirmed on a category: *"the causal FIR filter's paired 5-seed improvement on <CAT>
(transplanted with zero per-category tuning) is positive with a 95% CI excluding zero."*
Nothing broader; no SOTA language of any kind; no comparator statement (none exists here).

## VOID conditions

Any arm with <5 valid runs; non-full-catalog eval; seed substitution; config drift between arms
(argv diff beyond the filter flags); undisclosed category substitution; results file overwritten
rather than appended. Adjudication is mechanical (script committed with the campaign) and the
campaign result — confirmed, null, or void — is published either way.
