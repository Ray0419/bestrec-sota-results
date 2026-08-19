# -*- coding: utf-8 -*-
"""Aggregate the Steam family evals (PREREG_STEAM_V1 S3.3) across 5 seeds."""
import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
TC = 2.776  # t*, df=4

rows = {}
for f in sorted(glob.glob(os.path.join(OUT, "results_TEMP_STEAM_seed*.family_eval.json"))):
    r = json.load(open(f, encoding="utf-8"))
    for arm in ("stock", "imputed", "ridge", "fusion"):
        k = f"{arm}@0"
        if k in r["results"]:
            v = r["results"][k]
            d = rows.setdefault(arm, {"overall": [], "cold": [], "warm": [], "auc": []})
            d["overall"].append(v["overall"])
            d["cold"].append(v["cold"])
            d["warm"].append(v["warm"])
            d["auc"].append(v["cold_auc"])

print(f"{'arm':>8} {'overall':>20} {'cold':>20} {'warm':>20} {'cold AUC':>20}")
for arm, d in rows.items():
    cells = []
    for key in ("overall", "cold", "warm", "auc"):
        x = np.array(d[key])
        cells.append(f"{x.mean():.5f}+-{x.std(ddof=1):.5f}")
    print(f"{arm:>8} " + " ".join(f"{c:>20}" for c in cells))

print()
base = rows["stock"]
agg = {}
for arm in ("imputed", "ridge", "fusion"):
    dA = np.array(rows[arm]["auc"]) - np.array(base["auc"])
    dO = np.array(rows[arm]["overall"]) - np.array(base["overall"])
    n = len(dA)
    se_a = dA.std(ddof=1) / np.sqrt(n)
    se_o = dO.std(ddof=1) / np.sqrt(n)
    agg[arm] = {"dAUC": [dA.mean(), dA.mean() - TC * se_a, dA.mean() + TC * se_a,
                          int((dA > 0).sum()), n],
                "dOverall": [dO.mean(), dO.mean() - TC * se_o, dO.mean() + TC * se_o,
                              int((dO > 0).sum()), n]}
    a, o = agg[arm]["dAUC"], agg[arm]["dOverall"]
    print(f"{arm:>8}: dAUC {a[0]:+.5f} CI[{a[1]:+.5f},{a[2]:+.5f}] {a[3]}/{a[4]}"
          f" | dOverall {o[0]:+.6f} CI[{o[1]:+.6f},{o[2]:+.6f}] {o[3]}/{o[4]}")

json.dump({k: {m: v for m, v in d.items()} for k, d in agg.items()},
          open(os.path.join(OUT, "steam_family_aggregate.json"), "w",
               encoding="utf-8"), indent=1)
print("\nwrote", os.path.join(OUT, "steam_family_aggregate.json"))
