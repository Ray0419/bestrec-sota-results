# -*- coding: utf-8 -*-
"""PREREG_RHO_K_V1 analyser -- FROZEN per S4 before any matrix result is read.

Implements exactly the prereg's estimands:
  rho(k)   = R_forced(k) / R_warm, same-retriever reference, R_warm pooled k>=51
  C1       upper CI bound of rho(k) < 0.5 for every k<=10 bucket (per dataset,
           primary = text retriever, K=200, fce d256)
  C2       pi*(k,K) = c / (g*rho(k) + c) with the CITED constants from
           arXiv:2606.29947 (Yelp g=+10pp c=4.5pp; VideoGames g=+2.2pp c=4.7pp)
  C3       descriptive: R_nat vs R_forced (selection-bias read), no test
Gates G1/G2 must have passed in every run; failed runs are dropped and named.

Per-seed rho is computed from that seed's own counts; CI across seeds
(t, df=n-1, two-sided alpha=.05).  No number is invented for empty buckets.
"""
import glob
import json
import math
import os
import sys

import warnings

import numpy as np

# pop-retriever buckets can have zero natural coverage -> nanmean of all-nan is
# the intended nan; silence the (harmless) RuntimeWarning it emits.
warnings.filterwarnings("ignore", message="Mean of empty slice")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
TCRIT = {2: 4.3027, 4: 2.7764}
LOW = ("k0-0", "k1-2", "k3-5", "k6-10")            # the k<=10 claim buckets
MID = ("k11-20", "k21-50")
WARM = ("k51-200", "k201-1000000000")
ORDER = LOW + MID + WARM
TRADES = {"Yelp": (10.0, 4.5), "VideoGames": (2.2, 4.7)}   # (g_cov, c_cov) pp


def seed_rho(rep, retr, K, bucket):
    pool = rep["pool"][retr]
    a = pool[bucket][str(K)] if isinstance(next(iter(pool[bucket])), str) else pool[bucket][K]
    wh = wn = 0
    for b in WARM:
        w = pool[b][str(K)] if isinstance(next(iter(pool[b])), str) else pool[b][K]
        wh += w["hit_forced"]
        wn += w["n"]
    if not a["n"] or not wn or not wh:
        return None
    return (a["hit_forced"] / a["n"]) / (wh / wn), a, (wh / wn)


def main():
    sets = {
        "MI_d256 (primary)": "results_SXL_fce_d256_MI_seed*.pool_conv.json",
        "MI_d64 (secondary)": "results_SXL_fce_d64_MI_seed*.pool_conv.json",
        "STEAM_d256": "results_SXL_fce_d256_STEAM_seed*.pool_conv.json",
    }
    KS = [int(x) for x in (sys.argv[1].split(",") if len(sys.argv) > 1
                           else ["100", "200", "500", "1000"])]
    report = {}
    c1_all = True
    for label, pat in sets.items():
        fs = sorted(glob.glob(os.path.join(OUT, pat)))
        reps = []
        for f in fs:
            r = json.load(open(f, encoding="utf-8"))
            if not (r["gates"]["G1"] and r["gates"]["G2"]):
                print(f"!! GATE FAILURE, dropped: {os.path.basename(f)}")
                continue
            reps.append(r)
        n = len(reps)
        print(f"\n=== {label}  n={n} (gates passed) ===")
        if n == 0:
            continue
        df = n - 1
        tc = TCRIT.get(df)
        out = {}
        for retr in ("text", "pop"):
            print(f"  retriever {retr}, K=200:")
            print(f"  {'bucket':<10}{'rho mean':>10}{'CI':>24}{'R_frc':>8}{'R_nat':>8}{'C1?':>6}")
            for b in ORDER:
                vals, rf, rn = [], [], []
                for rep in reps:
                    got = seed_rho(rep, retr, 200, b)
                    if got is None:
                        continue
                    rho, a, _ = got
                    vals.append(rho)
                    rf.append(a["hit_forced"] / a["n"])
                    rn.append(a["hit_nat"] / a["nat_cov"] if a["nat_cov"] else np.nan)
                if not vals:
                    print(f"  {b:<10}{'(empty)':>10}")
                    continue
                v = np.array(vals)
                m = v.mean()
                h = (tc * v.std(ddof=1) / math.sqrt(len(v))
                     if len(v) > 1 and tc else float("nan"))
                verdict = ""
                if b in LOW and retr == "text":
                    ok = np.isfinite(h) and (m + h) < 0.5
                    verdict = "PASS" if ok else ("pt<0.5" if m < 0.5 else "REFUTE")
                    if not ok:
                        c1_all = False
                print(f"  {b:<10}{m:>10.4f}   [{m-h:>8.4f},{m+h:>8.4f}]"
                      f"{np.mean(rf):>8.4f}{np.nanmean(rn):>8.4f}{verdict:>6}")
                out[(retr, b)] = (m, h)
        report[label] = out
        # C2: pi*(k,K=200) table, text retriever, cited constants
        print(f"  C2 pi*(k, K=200) using arXiv:2606.29947 trades:")
        print(f"  {'bucket':<10}" + "".join(f"{d:>14}" for d in TRADES))
        for b in LOW + MID:
            if ("text", b) not in out:
                continue
            m, _ = out[("text", b)]
            row = f"  {b:<10}"
            for d, (g, c) in TRADES.items():
                row += f"{100*c/(g*m + c):>13.1f}%"
            print(row)
    print(f"\nC1 (rho(k<=10)<0.5, CI-bound, text, all datasets): "
          f"{'SUPPORTED' if c1_all else 'NOT established'}")
    dst = os.path.join(OUT, "RHO_K_analysis.json")
    json.dump({k: {f"{r}|{b}": v for (r, b), v in d.items()}
               for k, d in report.items()},
              open(dst, "w", encoding="utf-8"), indent=1)
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
