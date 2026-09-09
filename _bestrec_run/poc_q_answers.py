# -*- coding: utf-8 -*-
"""Aggregate evidence for the rigor review's four questions_for_authors.

Q1  p*_inner (0.60-0.75 band) vs pi_t_outer -> does it predict the sign of the
    ALREADY-MEASURED outer E4? Genuine temporally out-of-sample: the inner band
    is disjoint from the reporting window and preceded it in time.
Q2  rank-displacement genuine share from the K5 LOO decomps:
    [d_within_auc*(N_cold-1)] / [d_full_auc*(N_items-1)]  vs the 6.5% figure.
Q3  Steam fusion: inner-window-selected w vs transferred w=0.2, outer report.
Q4  warm invasion rate per dataset / n_cold_items -> per-item propensity,
    plus the stock warm-NDCG margin proxy.
"""
import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
TC = {4: 2.776, 3: 3.182, 2: 4.303}


def tstat(x):
    x = np.asarray(x, float)
    n = len(x)
    m = float(x.mean())
    sd = float(x.std(ddof=1)) if n > 1 else float("nan")
    se = sd / np.sqrt(n) if n > 1 else float("nan")
    tc = TC.get(n - 1, 1.96)
    return m, sd, [m - tc * se, m + tc * se], n


def main():
    rep = {}
    ta = json.load(open(os.path.join(OUT, "temporal_analysis.json"),
                        encoding="utf-8"))

    # ---------------- Q1 ----------------------------------------------------
    print("=" * 72)
    print("Q1 — OUT-OF-SAMPLE PREDICTION: p*_inner vs pi_t_outer vs sign(E4_outer)")
    q1 = {}
    for tag in ("MI", "VG", "STEAM"):
        ps, gs, cs = [], [], []
        for f in sorted(glob.glob(os.path.join(
                OUT, f"results_TEMP_{tag}_seed*.inner_eval.json"))):
            r = json.load(open(f, encoding="utf-8"))
            R = r["results"]
            g = R["imputed@0"]["cold"] - R["stock@0"]["cold"]
            c = R["stock@0"]["warm"] - R["imputed@0"]["warm"]
            if g + abs(c) > 0:
                ps.append(abs(c) / (g + abs(c)))
                gs.append(g)
                cs.append(c)
        if not ps:
            print(f"  {tag}: no inner evals yet")
            continue
        m, sd, ci, n = tstat(ps)
        key = tag if tag in ta else tag
        pi_out = ta[key]["pi_t"]
        e4 = ta[key]["E4"]
        pred_pay = pi_out > m
        e4_pos = e4["mean"] > 0
        e4_decisive = e4["ci95"][0] > 0 or e4["ci95"][1] < 0
        verdict = ("CORRECT" if (pred_pay == e4_pos and e4_decisive)
                   else "CONSISTENT (E4 CI spans 0 — boundary)" if not e4_decisive
                   else "WRONG")
        q1[tag] = {"pstar_inner": [m, sd, ci, n], "pi_t_outer": pi_out,
                   "E4_outer_mean": e4["mean"], "E4_ci": e4["ci95"],
                   "predicts": "pay" if pred_pay else "not pay",
                   "verdict": verdict}
        print(f"  {tag:>6}: p*_inner={100*m:5.2f}% ±{100*sd:.2f} "
              f"CI[{100*ci[0]:5.2f},{100*ci[1]:5.2f}] (n={n}) | "
              f"pi_t_outer={100*pi_out:5.2f}% -> predicts "
              f"{'PAY' if pred_pay else 'NOT pay'} | E4_outer={e4['mean']:+.6f} "
              f"-> {verdict}")
    rep["Q1"] = q1

    # ---------------- Q2 ----------------------------------------------------
    print("=" * 72)
    print("Q2 — RANK-DISPLACEMENT GENUINE SHARE (K5 LOO decomps, AUC units)")
    shares_rank, shares_ndcg = [], []
    for f in sorted(glob.glob(os.path.join(
            OUT, "results_K5_text_k0_MI_seed*.offset_decomp.json"))):
        r = json.load(open(f, encoding="utf-8"))
        A = r["arms"]["stock_plus_offset"]["by_offset"]["0.0"]
        B = r["arms"]["knn_imputed_plus_offset"]["by_offset"]["0.0"]
        if "cold_full_auc" not in A:
            continue
        n_cold = r["n_cold_items"]
        n_items = r["n_items"]
        d_win = B["cold_within_auc"] - A["cold_within_auc"]
        d_full = B["cold_full_auc"] - A["cold_full_auc"]
        if d_full > 0:
            shares_rank.append(d_win * (n_cold - 1) / (d_full * (n_items - 1)))
        g = B["cold_full_ndcg10"] - A["cold_full_ndcg10"]
        w = B["cold_within_ndcg10"] - A["cold_within_ndcg10"]
        if g > 0:
            shares_ndcg.append(w / g)
    if shares_rank:
        m, sd, ci, n = tstat(shares_rank)
        m2, sd2, ci2, n2 = tstat(shares_ndcg)
        rep["Q2"] = {"rank_displacement_share": [m, sd, ci, n],
                     "ndcg10_share": [m2, sd2, ci2, n2]}
        print(f"  genuine share, rank-displacement units: {100*m:5.1f}% "
              f"±{100*sd:.1f} CI[{100*ci[0]:5.1f},{100*ci[1]:5.1f}] (n={n})")
        print(f"  genuine share, top-10 NDCG units      : {100*m2:5.1f}% "
              f"±{100*sd2:.1f} CI[{100*ci2[0]:5.1f},{100*ci2[1]:5.1f}] (n={n2})")
        print(f"  -> metric-stability verdict: "
              f"{'NOT stable — the 93% figure is metric-specific' if abs(m - m2) > 0.05 else 'stable'}")
    else:
        print("  (decomp re-runs with cold_full_auc not present yet)")

    # ---------------- Q3 ----------------------------------------------------
    print("=" * 72)
    print("Q3 — FUSION: inner-selected w vs transferred w=0.2 (Steam outer)")
    ws = ["0.05", "0.1", "0.2", "0.5", "1"]
    inner_by_w = {w: [] for w in ws}
    for f in sorted(glob.glob(os.path.join(
            OUT, "results_TEMP_STEAM_seed*.inner_eval.json"))):
        r = json.load(open(f, encoding="utf-8"))
        R = r["results"]
        for w in ws:
            key = "fusion@0" if w == "0.2" else f"fusion_w{w}@0"
            if key in R:
                inner_by_w[w].append(R[key]["overall"])
    sel = None
    if any(inner_by_w[w] for w in ws):
        means = {w: np.mean(v) for w, v in inner_by_w.items() if v}
        sel = max(means, key=means.get)
        for w in ws:
            if inner_by_w[w]:
                mark = " <- selected" if w == sel else ""
                print(f"    inner overall @ w={w:>4}: {means[w]:.5f}{mark}")
    outer = {w: {"overall": [], "cold": [], "warm": []} for w in ws + ["stock"]}
    for f in sorted(glob.glob(os.path.join(
            OUT, "results_TEMP_STEAM_seed*.outer_sweep.json"))):
        r = json.load(open(f, encoding="utf-8"))
        R = r["results"]
        outer["stock"]["overall"].append(R["stock@0"]["overall"])
        for w in ws:
            key = "fusion@0" if w == "0.2" else f"fusion_w{w}@0"
            if key in R:
                for fld in ("overall", "cold", "warm"):
                    outer[w][fld].append(R[key][fld])
    if sel and outer[sel]["overall"]:
        st = np.mean(outer["stock"]["overall"])
        for w in (sel, "0.2"):
            o = np.mean(outer[w]["overall"])
            print(f"    OUTER w={w:>4}: overall {o:.5f} (stock {st:.5f}, "
                  f"delta {o-st:+.5f}) cold {np.mean(outer[w]['cold']):.5f} "
                  f"warm {np.mean(outer[w]['warm']):.5f}")
        rep["Q3"] = {"selected_w": sel,
                     "outer_selected": {k: float(np.mean(v))
                                        for k, v in outer[sel].items() if v},
                     "outer_transferred": {k: float(np.mean(v))
                                           for k, v in outer["0.2"].items() if v},
                     "outer_stock_overall": float(st)}
    else:
        print("  (outer sweeps not present yet)")

    # ---------------- Q4 ----------------------------------------------------
    print("=" * 72)
    print("Q4 — WARM-COST MECHANISM: invasion propensity vs margin proxy")
    q4 = {}
    for tag in ("MI", "VG", "STEAM"):
        invs, n_cold_items = [], None
        for f in sorted(glob.glob(os.path.join(
                OUT, f"results_TEMP_{tag}_seed*.inner_eval.json"))):
            r = json.load(open(f, encoding="utf-8"))
            R = r["results"]
            if "warm_invasion_rate" in R.get("imputed@0", {}):
                invs.append(R["imputed@0"]["warm_invasion_rate"]
                            - R["stock@0"].get("warm_invasion_rate", 0.0))
                n_cold_items = r.get("n_cold_items")
        if invs and n_cold_items:
            m = float(np.mean(invs))
            per_item = m / n_cold_items
            warm_ndcg = ta[tag]["E4"]  # placeholder; margin proxy from analysis
            q4[tag] = {"warm_invasion_rate_delta": m,
                       "n_cold_items": n_cold_items,
                       "per_1k_cold_items": 1000 * per_item}
            print(f"  {tag:>6}: d(warm events invaded) = {100*m:5.2f}pp over "
                  f"{n_cold_items:,} cold items -> {1000*per_item:.4f}pp per "
                  f"1k cold items")
    rep["Q4"] = q4

    json.dump(rep, open(os.path.join(OUT, "q_answers.json"), "w",
                        encoding="utf-8"), indent=1, default=float)
    print("\nwrote", os.path.join(OUT, "q_answers.json"))


if __name__ == "__main__":
    main()
