# PRE-REGISTRATION — Office_Products (4th category): out-of-sample prediction + point-estimate gate

**Written 2026-07-10, BEFORE the Office_Products raw data finished downloading and before ANY
Office statistic, split, or run existed locally.** This file is never edited after the commit
introducing it; results go to `SOTA_CONFIRM_OFFICE_RESULTS.md`. Purpose: answer the novelty
audit's N7 ("law needs broader replication and a predictive model") and N13 ("needs broader wins
across categories") with *pre-registered out-of-sample evidence*, not wording concessions.

## Comparators (published, Liu 2025 arXiv:2504.10545, single-seed, AR2023 Office_Products
5-core LLOO full-catalog): SASRec NDCG@10 = 0.0153 · HSTU = 0.0223 · **HSTU-BLaIR = 0.0271**.

## P1 — Out-of-sample test of the dataset-conditional tail pattern (the "predictive rule")

The campaign's connectivity finding predicts *where* text rescues the rare-item tail. The rule is
locked NOW, before Office's statistics are known:

- Let **U = mean distinct-users-per-item** in the Office 5-core TRAIN split (measured after
  preprocessing, before any training run; recorded in the results file).
- **If U < 2.5** (MI-like sparse-connectivity regime): PREDICT text−ID tail Δ > 0 (positive
  tail effect, majority of seeds positive).
- **If U ≥ 3.0** (VG/Beauty-like regime): PREDICT tail Δ ≈ 0 (null).
- **If 2.5 ≤ U < 3.0**: declared ambiguous a priori — the prediction is scored as VOID (neither
  confirms nor refutes). Reference points: MI U=2.34 (tail win), VG U=3.70 (null), Beauty
  U=3.51 (null).
- **Test:** paired text-stack vs ID-only contrast (identical config/seed; ID-only = `--no-sbert`,
  no text-prototypes, no text-sim-bias), 5 seeds, tail = rarest train-frequency tercile.
  Primary read = pooled tail hit-counts at @10/@20/@50/@100 (two-proportion z) + per-seed sign
  count; the seed-level mean Δ reported alongside. Scoring: prediction CONFIRMED if the
  direction matches at @50 and @100 with pooled p<0.05 (the depth range the MI analysis showed
  is properly powered); REFUTED if significant in the opposite direction; INCONCLUSIVE otherwise.

## P2 — Per-category point-estimate gate (dual-kernel, identical to the MI V2 protocol)

- **Frozen config** (identical to `SOTA_CONFIRM_PREREG_V2.md` except the two Office adaptations
  declared here): epochs 20, batch 256, d_model 64, n_layers 4, n_heads 2, dropout 0.5, lr 1e-3
  warmup_cosine, encoder hstu, chunked-full-softmax (item-chunk 32768), time-bias,
  text-sim-bias, text-prototypes 512, pos-rab, label-smoothing 0.2, causal-filter.
  Office adaptations (declared before any run; uniform across ALL arms): `--eval-every 2` and
  `--eval-subsample 30000` (Office is several times larger than MI; periodic val on a 30k-user
  subsample selects best-by-val, the FINAL epoch is always evaluated on ALL users — the
  headline numbers come from full-catalog, all-user evaluations only).
- **Arms:** filter-kernel 16 and filter-kernel 8, **fresh seeds 20260623–27** (next consecutive
  integers; never used anywhere).
- **GATE:** BOTH arms' fresh 5-seed 95% t-interval lower bound (mean − 2.776·sd/√5) >
  **0.0271**, and ≥4/5 seeds individually above, per arm.
- **Floor check:** one plain ID-only SASRec run (`--encoder transformer --no-sbert`, no novel
  flags, seed 20260623); its NDCG@10 must be at or below the published SASRec 0.0153
  neighborhood for the split-parity argument (an easier split would inflate it).
- **If the gate PASSES:** the claim (frozen wording): *"fresh five-seed means and CIs exceed the
  published HSTU-BLaIR point estimate on AR2023 Office_Products for both kernels — a
  per-category point-estimate comparison, not a paired-superiority or general SOTA claim."*
  Combined with the approved MI result: "on two of the three AR2023 categories reported by the
  comparator paper."
- **If it FAILS:** recorded permanently as a negative; no re-runs, no re-tuning (the config is
  frozen from MI — zero Office-specific tuning by construction).

## Execution

- Runs execute via `_bestrec_run/run_office_program.sh` (committed with this prereg): waits for
  the downloads + FIR-ablation GPU job, gunzips, preprocesses (official-mirror kcore script),
  encodes titles, records split SHA256s + n_users/n_items/n_interactions + U (and applies the
  P1 rule mechanically, before any training), then runs k16×5, k8×5, ID-only×5, SASRec-floor×1
  (16 runs, one GPU job at a time), then adjudicates.
- Provenance: every run carries the standard manifest (git commit, dirty-tracked flag, data
  SHA256s, code SHA256s, sidecar hash); doc-only commit descendants are disclosed per the V2
  erratum precedent.
- Total budget declared: exactly these 16 runs. No additional Office runs of any kind before
  adjudication.

## Wording caps (identical to V2)

No "statistically significantly better," no "general SOTA," no "SOTA on Amazon Reviews 2023,"
no paired-superiority claims. The comparator is a published single-seed point estimate; its
implementation cannot run on this hardware (documented).
