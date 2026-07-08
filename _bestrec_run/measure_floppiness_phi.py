#!/usr/bin/env python
# READ-ONLY artifact (NO GPU, NO training, NO model edit). Grounds XF 2026-06-19-2
# (rigidity / Maxwell-Calladine / Singer-Cucuringu). Per-item parameter-free
# "floppiness" phi_i = max(0, r_eff - indep_i)/r_eff, where indep_i = number of
# DISTINCT TRAIN users who interacted with item i (independent-constraint supply,
# train-only => leak-free) and r_eff = effective collaborative rank (campaign
# d_eff ~ 23; reported with a sensitivity band). Tests the cross-dataset
# prediction: tail-tercile mean phi should be HIGH for MI (tail-WIN) and LOW for
# VG/Beauty (tail-null), tracking the measured text-ID tail-Delta ordering.
import csv
from pathlib import Path
from collections import defaultdict
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
SPLIT = ROOT / "data_5core" / "5core" / "last_out"
DATASETS = ["Video_Games", "Musical_Instruments", "Beauty_and_Personal_Care"]
# Measured 5-seed/2-seed text-ID tail-Delta (this campaign), for the ordering test:
TAIL_DELTA = {"Video_Games": -0.000148, "Musical_Instruments": +0.000335,
              "Beauty_and_Personal_Care": None}  # Beauty tail-Delta: see supervisor runs
R_EFF_BAND = [22, 23, 24]

def read_train(ds):
    rows = []
    with open(SPLIT / f"{ds}.train.csv", "r", encoding="utf-8") as fp:
        for r in csv.DictReader(fp):
            rows.append((r["user_id"], r["parent_asin"]))
    return rows

def analyze(ds):
    rows = read_train(ds)
    items = sorted({a for _, a in rows})
    i2 = {a: j for j, a in enumerate(items)}
    n = len(items)
    distinct_users = [set() for _ in range(n)]   # indep_i
    freq = np.zeros(n, dtype=np.int64)            # raw interaction count
    users = set()
    for u, a in rows:
        j = i2[a]; distinct_users[j].add(u); freq[j] += 1; users.add(u)
    indep = np.array([len(s) for s in distinct_users], dtype=np.float64)
    # terciles by TRAIN frequency (rarest third = tail), matching evaluate()'s bucketer
    order = np.argsort(freq, kind="stable")
    t1, t2 = n // 3, 2 * n // 3
    strata = {"tail": order[:t1], "mid": order[t1:t2], "head": order[t2:]}
    out = {"n_items": n, "n_users": len(users), "users_per_item": round(len(users) / n, 3),
           "interactions_per_item": round(freq.sum() / n, 3),
           "mean_distinct_users_per_item": round(float(indep.mean()), 3)}
    for r_eff in R_EFF_BAND:
        phi = np.maximum(0.0, r_eff - indep) / r_eff       # floppiness in [0,1]
        out[f"phi_r{r_eff}"] = {nm: round(float(phi[idx].mean()), 4) for nm, idx in strata.items()}
        # fraction of items below the isostatic point u* ~ r_eff (floppy)
        out[f"frac_floppy_r{r_eff}"] = {nm: round(float((indep[idx] < r_eff).mean()), 4)
                                        for nm, idx in strata.items()}
    return out

if __name__ == "__main__":
    res = {ds: analyze(ds) for ds in DATASETS}
    print("=== per-item floppiness phi (rigidity / Singer-Cucuringu) ===")
    print("prediction: tail-mean phi HIGH for MI (tail-WIN +0.000335), LOW for VG (null -0.000148)\n")
    for ds in DATASETS:
        r = res[ds]
        print("%-26s users/item=%.2f distinct-users/item=%.2f interactions/item=%.2f tailDelta=%s"
              % (ds, r["users_per_item"], r["mean_distinct_users_per_item"],
                 r["interactions_per_item"], TAIL_DELTA[ds]))
        print("    tail-mean phi  (r_eff 22/23/24): %.4f / %.4f / %.4f"
              % (r["phi_r22"]["tail"], r["phi_r23"]["tail"], r["phi_r24"]["tail"]))
        print("    tail frac floppy(r_eff 22/23/24): %.3f / %.3f / %.3f"
              % (r["frac_floppy_r22"]["tail"], r["frac_floppy_r23"]["tail"], r["frac_floppy_r24"]["tail"]))
        print("    mid/head phi (r_eff23): %.4f / %.4f"
              % (r["phi_r23"]["mid"], r["phi_r23"]["head"]))
    print("\nORDERING CHECK (r_eff=23 tail-mean phi): "
          + "  ".join("%s=%.4f" % (ds.split('_')[0], res[ds]["phi_r23"]["tail"]) for ds in DATASETS))
