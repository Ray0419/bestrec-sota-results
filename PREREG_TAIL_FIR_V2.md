# PREREG_TAIL_FIR_V2 — pre-declared independent-arm rerun campaign (tail estimand + FIR attribution)

**Frozen 2026-07-20 (Australia/Sydney), before any campaign run starts.** Maintainer directive
2026-07-20 ("fold all 5") authorizes the audit P0 reruns; this file freezes the design. It is
committed and OpenTimestamps-stamped (`PREREG_TAIL_FIR_V2.md.ots`) before the first run
launches — the first campaign with an **independent external timestamp** in this project.

## Why this campaign exists (what it repairs)

Audits 2026-07-19 19:56 → 2026-07-20 00:01 confirmed two design defects in the original
tail and FIR campaigns:

1. **Same-numbered seeds never created paired arms** (treatment modules consume RNG before
   the shared backbone), so all paired inference was withdrawn.
2. **The nominal tail tercile is defective**: it mixes zero-train-exposure targets with
   low-frequency targets and splits frequency ties by item-ID order, and the original runs
   retained no per-row outputs to reanalyze.

This campaign adopts **option (b)** of the 19:56 audit: arms are **pre-specified as
independent** (no pairing claim of any kind), powered by more seeds, analyzed with
independent-arm Welch inference, and every run automatically emits a per-user sidecar
(`<out>.users.jsonl.gz`: user_id, target_item_id, rank0, ndcg10, hr10, rr, pop_bucket)
enabling tie-safe, exposure-separated, row-level reanalysis by anyone.

## Design (frozen)

- **Arms and seeds (8 per arm, never inspected before this freeze):**
  | campaign | arm | seeds | epochs |
  |---|---|---|---|
  | MI tail | text (V2 stack) | 20260801–20260808 | 20 |
  | MI tail | id-only | 20260811–20260818 | 20 |
  | IS FIR | filter (K=8) | 20260821–20260828 | 20 |
  | IS FIR | no-filter | 20260831–20260838 | 20 |
  | CDs FIR | filter (K=8) | 20260861–20260868 | 20 |
  | CDs FIR | no-filter | 20260871–20260878 | 20 |
  | VG tail | text (V2 stack) | 20260841–20260848 | 40 |
  | VG tail | id-only | 20260851–20260858 | 40 |

- **Configurations:** mechanically re-emitted from the original runs' embedded `config`
  dicts (no hand transcription); the frozen command list is
  `_bestrec_run/tfv2_commands.txt`, sha256
  `525496d4bf608f4f62837b729fb6867b61d521df2cee80cf413a8f0c39de1a1b` (64 commands).
  A 1-epoch smoke run validated exact template-side config parity (every template key
  equal except seed/epochs/out/eval_every) and sidecar emission (57,439 rows on MI).
  Driver flags added after the original campaigns ride at their inert defaults; each run
  JSON embeds its full realized config for audit.
- **Execution:** strictly sequential (one GPU job at a time), in table order (MI → IS →
  CDs → VG), via `_bestrec_run/run_tfv2_campaign.sh`; a run whose output JSON already
  exists is skipped (resumability), and existing `results_*.json` files are never
  overwritten.
- **Cohort rules (frozen; computed from the released split CSVs, item-ID-independent):**
  - **Zero-exposure bin:** test targets whose item has train frequency 0. Reported
    separately; never merged into any tail statistic.
  - **Positive-frequency tail (primary):** order items by train frequency ascending;
    let N⁺ = number of positive-frequency items; include whole frequency groups from the
    lowest frequency upward until adding the next whole group would move the cumulative
    item count further from N⁺/3 than stopping (deterministic nearest-to-third whole-group
    rule; no tie is ever split).
  - **Sensitivity strata (secondary):** (a) exclude the boundary frequency group entirely;
    (b) absolute band: train frequency in [1, 6].
- **Endpoints and decision rules (frozen):**
  - **E1 (primary):** MI positive-frequency-tail NDCG@10, text vs id, independent-arm
    Welch; success = two-sided 95% CI excludes 0 in the positive direction.
  - **E2 (primary):** IS overall NDCG@10, filter vs no-filter, Welch; CI excludes 0, positive.
  - **E3 (primary):** CDs overall NDCG@10, filter vs no-filter, Welch; CI excludes 0, positive.
  - **Multiplicity:** Holm across {E1, E2, E3}, family α = 0.05.
  - **Secondary/descriptive (no success gates):** MI zero-exposure-bin Δ; MI tail HR@10;
    the two sensitivity strata; VG tail Δ (no equivalence claim of any kind — no margin is
    pre-specified); four-arm MI−VG Welch–Satterthwaite contrast; FIR per-category tail Δ.
  - The FIR endpoints estimate the **FIR-plus-initialization/optimizer package** effect
    under independent arms (the known singular-initialization coupling is unchanged and
    disclosed; component-level attribution is out of scope for this campaign).
- **Adjudication:** `_bestrec_run/adjudicate_tfv2.py` (to be committed before any result
  is inspected; it consumes only the sidecars + split CSVs and prints per-endpoint
  verdicts). No number from this campaign enters either paper until adjudication runs and
  its output is committed. Failure honesty: a failed endpoint is reported as failed; the
  existing narrowed claims stand and can only narrow further.
- **Claim-boundary interaction:** this campaign ADDS evidence; it changes no frozen prior
  wording. If E1–E3 pass, the papers may state the corresponding independent-arm results
  under this prereg's wording; nothing here authorizes SOTA/comparator/paired language.

## Status log

- 2026-07-20: frozen; smoke parity validated; OTS stamp requested; campaign launched
  (sequential background queue).
