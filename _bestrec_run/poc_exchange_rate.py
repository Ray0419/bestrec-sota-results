# -*- coding: utf-8 -*-
"""The cold-start EXCHANGE RATE (RQ1 reframed).

Any method that writes a plausible row for a cold item into a SHARED
full-catalog softmax buys cold-slice gain and pays a warm-slice cost: the
imputed row becomes a competitor for every other query. Per-slice reporting
(the field's convention) shows the numerator, never the denominator.

For each intervention variant v this computes:
    g(v) = mean NDCG@10 gain on COLD targets      (per cold target)
    c(v) = mean NDCG@10 loss on NON-COLD targets  (per warm target)
    p*(v) = |c| / (g + |c|)   = the BREAK-EVEN cold prevalence:
            the intervention is aggregate-positive iff the share of eval
            targets that are cold exceeds p*.
At the observed prevalence p_obs it also reports the realized aggregate delta.

Reads the posterior_eval JSONs (which already store per-variant pareto terms)
and prints the frontier + break-even table.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")


def analyze(path):
    r = json.load(open(path, encoding="utf-8"))
    n_cold_t = None
    for name, sl in r["test_slices"].items():
        if "k0-0" in sl:
            n_cold_t = sl["k0-0"]["n"]
            break
    n_tot = sum(s["n"] for s in r["test_slices"]["stock"].values())
    p_obs = n_cold_t / n_tot
    stock_cold = r["pareto"]["stock"]["k0_ndcg"]
    rows = []
    for v, p in r["pareto"].items():
        if v == "stock":
            continue
        g = p["k0_ndcg"] - stock_cold
        c = p["nonk0_delta_vs_stock"]
        agg = p_obs * g + (1 - p_obs) * c
        pstar = (abs(c) / (g + abs(c))) if (g > 0 and c < 0) else None
        rows.append({"variant": v, "cold_gain": g, "warm_cost": c,
                     "aggregate_delta": agg, "breakeven_prevalence": pstar})
    return {"file": os.path.basename(path), "n_cold_targets": n_cold_t,
            "n_targets": n_tot, "p_observed": p_obs,
            "stock_cold_ndcg": stock_cold, "variants": rows}


def main():
    paths = sys.argv[1:] or sorted(glob.glob(os.path.join(OUT, "*.posterior_eval.json")))
    allrep = []
    for path in paths:
        rep = analyze(path)
        allrep.append(rep)
        print(f"\n=== {rep['file']} ===")
        print(f"cold targets: {rep['n_cold_targets']:,}/{rep['n_targets']:,} "
              f"= {100*rep['p_observed']:.2f}% of eval  "
              f"(stock cold NDCG@10 = {rep['stock_cold_ndcg']:.5f})")
        print(f"{'variant':>13} {'cold gain':>11} {'warm cost':>11} "
              f"{'aggregate':>11} {'break-even p*':>14} {'verdict@p_obs':>14}")
        for v in sorted(rep["variants"], key=lambda x: -x["cold_gain"]):
            ps = (f"{100*v['breakeven_prevalence']:.2f}%"
                  if v["breakeven_prevalence"] is not None else "n/a")
            verdict = "PAYS" if v["aggregate_delta"] > 0 else "costs"
            print(f"{v['variant']:>13} {v['cold_gain']:>+11.5f} "
                  f"{v['warm_cost']:>+11.6f} {v['aggregate_delta']:>+11.6f} "
                  f"{ps:>14} {verdict:>14}")
        pos = [v for v in rep["variants"] if v["breakeven_prevalence"] is not None]
        if pos:
            best = min(pos, key=lambda v: v["breakeven_prevalence"])
            print(f"  best exchange rate: {best['variant']} — pays whenever cold "
                  f"targets exceed {100*best['breakeven_prevalence']:.2f}% of eval "
                  f"(observed here: {100*rep['p_observed']:.2f}%)")
    dst = os.path.join(OUT, "exchange_rate.json")
    json.dump(allrep, open(dst, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()
