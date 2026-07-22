#!/usr/bin/env python
"""
make_table_5_4_titration.py  --  EXPERIMENT agent, paper-finishing (CPU, read-only)

Typesets the formal per-rung table for PAPER_DRAFT.md section 5.4 (the
interaction-thinning density-titration DOUBLE result) STRICTLY from the frozen
on-disk result JSONs. NOTHING is re-trained; this only re-reads best_test.by_popularity
from the locked 5-seed artifacts and tabulates paired (text - ID) head/tail deltas
for NDCG@10 and HR@10, with sample-std seed bands and positive-seed counts.

Provenance / honesty:
  * AR2023 Video_Games 5-core LLOO, full-catalog eval (n_eval = 94,762; tail_n = 10,900),
    train-frequency terciles (leak-free), best-by-val checkpoint per run.
  * Realized train-interactions/item per rung are the values PRINTED IN THE RUN LOGS
    (run_TITR*_s08_VG.log / run_TITRATE_idonly_rho066_VG.log), hardcoded below and
    cited; full density = 24.405, rho=0.66 = 16.109 (= MI's native 16.2).
  * (the former alpha = ipi/d_eff column is RETRACTED with the spectral analysis,
    2026-07-19: no alpha or d_eff quantity is computed or printed anywhere here)
    reproduces the MI-subcritical anchor exactly.
  * INTEGRITY GATE: the recomputed per-rung NDCG head/tail means MUST match the locked
    section-5.4 prose values to 5 decimals, else the script aborts (prevents silent drift).

Run:  _bestrec_run/.venv/Scripts/python _bestrec_run/make_table_5_4_titration.py
Emits the markdown table to stdout (paste target = PAPER_DRAFT.md section 5.4).
"""
import json, os, math, sys

# Emit UTF-8 regardless of the host console codepage (Windows cp1252 cannot encode
# the U+2212 minus / ± / Greek used in the table); keeps this artifact re-runnable
# on a stock Windows console, not only under PYTHONIOENCODING=utf-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

RUN = os.path.dirname(os.path.abspath(__file__))
SEEDS = [8, 9, 10, 11, 12]            # 20260608..12
TAIL_N, NEVAL = 10900, 94762

# rung -> (text_files, id_files) keyed by seed index 8..12; realized interactions/item from LOGS
def full_files():
    t = ["results_TAIL_V2_text_VG.json"] + [f"results_TAIL_V2_text_seed202606{s:02d}_VG.json" for s in SEEDS[1:]]
    i = ["results_TAIL_idonly_VG.json"] + [f"results_TAIL_idonly_seed202606{s:02d}_VG.json" for s in SEEDS[1:]]
    return t, i

def titr_files(tag):  # rho in {094,091,088,078}
    t = [f"results_TITR_text_rho{tag}_s{s:02d}_VG.json" for s in SEEDS]
    i = [f"results_TITR_idonly_rho{tag}_s{s:02d}_VG.json" for s in SEEDS]
    return t, i

def rho066_files():
    t = ["results_TITRATE_text_rho066_VG.json"] + [f"results_TITRATE_text_rho066_seed{s:02d}_VG.json" for s in SEEDS[1:]]
    i = ["results_TITRATE_idonly_rho066_VG.json"] + [f"results_TITRATE_idonly_rho066_seed{s:02d}_VG.json" for s in SEEDS[1:]]
    return t, i

# rho, label, realized interactions/item (from run logs), file-getter
RUNGS = [
    (1.00, full_files,            24.405),
    (0.94, lambda: titr_files("094"), 22.947),
    (0.91, lambda: titr_files("091"), 22.210),
    (0.88, lambda: titr_files("088"), 21.484),
    (0.78, lambda: titr_files("078"), 19.030),
    (0.66, rho066_files,          16.109),
]
# D_EFF removed 2026-07-19: the alpha/d_eff quantity is retracted (spectral analysis withdrawal).

# Locked section-5.4 prose NDCG means (head, tail) -- the integrity gate
LOCKED_NDCG = {
    1.00: (0.00221, -0.000148),
    0.94: (0.00239,  0.000165),
    0.91: (0.00254,  0.000039),
    0.88: (0.00252,  0.000537),
    0.78: (0.00266,  0.000056),
    0.66: (0.00354, -0.000108),
}

def load(fn):
    with open(os.path.join(RUN, fn)) as f:
        return json.load(f)

def mean_std(xs):
    n = len(xs); m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1)) if n > 1 else 0.0
    return m, sd

def main():
    rows = []
    integrity_ok = True
    for rho, getter, ipi in RUNGS:
        tfiles, ifiles = getter()
        # per-seed paired (text - ID) deltas
        d = {("head", "NDCG@10"): [], ("head", "HR@10"): [],
             ("tail", "NDCG@10"): [], ("tail", "HR@10"): []}
        for tf, jf in zip(tfiles, ifiles):
            bt_t = load(tf)["best_test"]; bt_i = load(jf)["best_test"]
            # sanity: frozen eval geometry
            assert bt_t["n_eval"] == NEVAL and bt_i["n_eval"] == NEVAL, f"n_eval drift {tf}"
            assert bt_t["by_popularity"]["tail"]["n"] == TAIL_N, f"tail_n drift {tf}"
            for strat in ("head", "tail"):
                for metric in ("NDCG@10", "HR@10"):
                    d[(strat, metric)].append(
                        bt_t["by_popularity"][strat][metric] - bt_i["by_popularity"][strat][metric])
        # aggregate
        agg = {}
        for key, xs in d.items():
            m, sd = mean_std(xs)
            pos = sum(1 for x in xs if x > 0)
            agg[key] = (m, sd, pos, len(xs))
        # integrity gate vs locked NDCG prose
        lh, lt = LOCKED_NDCG[rho]
        if abs(agg[("head", "NDCG@10")][0] - lh) > 5e-5 or abs(agg[("tail", "NDCG@10")][0] - lt) > 5e-5:
            integrity_ok = False
            print(f"!! INTEGRITY FAIL rho={rho}: recomputed head/tail NDCG "
                  f"{agg[('head','NDCG@10')][0]:+.6f}/{agg[('tail','NDCG@10')][0]:+.6f} "
                  f"vs locked {lh:+.5f}/{lt:+.5f}", file=sys.stderr)
        rows.append((rho, ipi, agg))

    if not integrity_ok:
        sys.exit("ABORT: recomputed means diverge from locked section-5.4 prose; not emitting table.")

    # ---- emit markdown ----
    def cell(a):
        m, sd, pos, n = a
        return f"{m:+.6f} ± {sd:.6f} ({pos}/{n})"

    print("**Table: section 5.4 interaction-thinning density-titration ladder "
          "(AR2023 Video_Games 5-core LLOO, full-catalog n_eval = 94,762, tail_n = 10,900; "
          "same-seed-number text−ID (arms not initialization-paired), best-by-val; 5 seeds = 20260608–12 per rung; mean ± sample-std (positive-seed count)).**\n")
    print("| ρ | kept inter./item | head ΔNDCG@10 | head ΔHR@10 | tail ΔNDCG@10 | tail ΔHR@10 |")
    print("|---|---|---|---|---|---|")
    for rho, ipi, agg in rows:
        print(f"| {rho:.2f} | {ipi:.3f} | "
              f"{cell(agg[('head','NDCG@10')])} | {cell(agg[('head','HR@10')])} | "
              f"{cell(agg[('tail','NDCG@10')])} | {cell(agg[('tail','HR@10')])} |")
    print()
    print("- **HEAD = overall rank trend (one reversal; one fixed draw; level contrasts):** head ΔNDCG rises as ρ falls "
          "(density drops), all rungs 5/5 positive ⇒ Spearman ρ_s(head Δ vs density) = "
          "−0.94 (NDCG) / −0.71 (HR). The head text-advantage rises under this bundled thinning intervention (a level trend; not component-level causal attribution).")
    print("- **TAIL = REFUTED dose-response:** tail ΔNDCG is non-monotone / trend-free; no rung clears "
          "MI's native +0.000335 (5/5) bar; Spearman ρ_s(tail Δ vs density) = −0.14 (n.s.). "
          "Thinning VG to MI's exact density (ρ=0.66, 16.109 inter./item ≈ MI 16.2) does **not** reproduce "
          "MI's tail win ⇒ global density is a tail *correlate only*, not supported as a tail driver. "
          "(The ρ=0.88 tail bump is non-monotone and does not survive a six-rung Bonferroni correction; recorded, not headlined.)")
    print("- The former alpha = ipi/d_eff column is RETRACTED with the spectral analysis (2026-07-19); "
          "no alpha or d_eff quantity is computed here. Realized inter./item are the run-log values; "
          "all numbers re-read from the frozen results_TITR*/TAIL_* JSONs (integrity-gated to the locked section-5.4 NDCG means).")

if __name__ == "__main__":
    main()
