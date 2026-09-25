# -*- coding: utf-8 -*-
"""Fit the cold-catalog scaling law from the 3 within-dataset MI rungs.

Same dataset / architecture / seed / code; only the number of cold items N_cold
differs (31, 649, 3121). For a fixed imputation method, regress
log(warm_cost) and log(break-even p*) on log(N_cold).
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
RUNGS = [("anchor", "results_KDIALCK_text_anchor_MI_seed20260736.posterior_eval.json"),
         ("f0.05", "results_KDIALCK_text_k0f0.05_MI_seed20260736.posterior_eval.json"),
         ("f0.25", "results_KDIALCK_text_k0_MI_seed20260736.posterior_eval.json")]
VARIANTS = ("k0knn_s1", "k0dev_t1.4", "k0orth_t2", "k0fixrdg")


def load(fn):
    r = json.load(open(os.path.join(OUT, fn), encoding="utf-8"))
    n_cold_items = r["n_deg0"]
    sl = r["test_slices"]["stock"]
    n_cold_t = sl["k0-0"]["n"]
    n_tot = sum(s["n"] for s in sl.values())
    stock_cold = r["pareto"]["stock"]["k0_ndcg"]
    out = {}
    for v, p in r["pareto"].items():
        g = p["k0_ndcg"] - stock_cold
        c = p["nonk0_delta_vs_stock"]
        out[v] = {"g": g, "c": c,
                  "pstar": (abs(c) / (g + abs(c))) if (g > 0 and c < 0) else None}
    return n_cold_items, n_cold_t, n_tot, out


def main():
    rows = []
    for tag, fn in RUNGS:
        n_ci, n_ct, n_tot, per_v = load(fn)
        rows.append({"rung": tag, "n_cold_items": n_ci, "n_cold_targets": n_ct,
                     "p_obs": n_ct / n_tot, "per_variant": per_v})
    print(f"{'rung':>8} {'N_cold_items':>13} {'cold targets':>13} {'p_obs':>8}")
    for r in rows:
        print(f"{r['rung']:>8} {r['n_cold_items']:>13,} {r['n_cold_targets']:>13,} "
              f"{100*r['p_obs']:>7.2f}%")

    rep = {"rungs": [{k: v for k, v in r.items() if k != "per_variant"}
                     for r in rows], "fits": {}}
    N = np.array([r["n_cold_items"] for r in rows], dtype=np.float64)
    print(f"\n{'variant':>12} {'cold gain g(N)':>28} {'warm cost |c|(N)':>30} "
          f"{'p*(N)':>26}")
    print(f"{'':>12} " + "  ".join(f"{r['rung']:>8}" for r in rows) +
          "   " + "  ".join(f"{r['rung']:>8}" for r in rows) +
          "   " + "  ".join(f"{r['rung']:>7}" for r in rows))
    for v in VARIANTS:
        gs = np.array([r["per_variant"][v]["g"] for r in rows])
        cs = np.array([abs(r["per_variant"][v]["c"]) for r in rows])
        ps = [r["per_variant"][v]["pstar"] for r in rows]
        line = (f"{v:>12} " + "  ".join(f"{g:>8.5f}" for g in gs) + "   "
                + "  ".join(f"{c:>8.5f}" for c in cs) + "   "
                + "  ".join((f"{100*p:>6.2f}%" if p else "   n/a ") for p in ps))
        print(line)
        ok = (gs > 0) & (cs > 0)
        fit = {}
        if ok.sum() >= 3:
            for name, y in (("cold_gain", gs), ("warm_cost", cs)):
                b = np.polyfit(np.log(N[ok]), np.log(y[ok]), 1)
                pred = np.polyval(b, np.log(N[ok]))
                r2 = 1 - ((np.log(y[ok]) - pred) ** 2).sum() / \
                    max(((np.log(y[ok]) - np.log(y[ok]).mean()) ** 2).sum(), 1e-30)
                fit[name] = {"exponent": float(b[0]), "r2": float(r2)}
            pv = np.array([p for p in ps if p is not None])
            if len(pv) >= 3:
                b = np.polyfit(np.log(N[ok]), np.log(pv), 1)
                pred = np.polyval(b, np.log(N[ok]))
                r2 = 1 - ((np.log(pv) - pred) ** 2).sum() / \
                    max(((np.log(pv) - np.log(pv).mean()) ** 2).sum(), 1e-30)
                fit["breakeven_pstar"] = {"exponent": float(b[0]), "r2": float(r2)}
        rep["fits"][v] = fit

    print("\n=== log-log scaling exponents vs N_cold (3 rungs, same dataset) ===")
    print(f"{'variant':>12} {'gain ~N^a':>16} {'cost ~N^b':>16} {'p* ~N^c':>18}")
    for v, f in rep["fits"].items():
        if not f:
            print(f"{v:>12}  (insufficient positive rungs)")
            continue
        g = f.get("cold_gain", {})
        c = f.get("warm_cost", {})
        p = f.get("breakeven_pstar", {})
        print(f"{v:>12} a={g.get('exponent', float('nan')):+.2f} "
              f"(R2 {g.get('r2', float('nan')):.2f})  "
              f"b={c.get('exponent', float('nan')):+.2f} "
              f"(R2 {c.get('r2', float('nan')):.2f})  "
              f"c={p.get('exponent', float('nan')):+.2f} "
              f"(R2 {p.get('r2', float('nan')):.2f})")

    dst = os.path.join(OUT, "scaling_fit.json")
    json.dump(rep, open(dst, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()
