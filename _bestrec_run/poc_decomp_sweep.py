# -*- coding: utf-8 -*-
"""MERGED AGENDA step 2: offset-degeneracy decomposition across seeds/datasets.

Runs poc_offset_decomp.py over every available checkpoint and aggregates the
central instrument:

    offset-matched efficiency ratio
      = (warm cost per unit cold gain of a PURE OFFSET)
      / (warm cost per unit cold gain of the METHOD)

    == 1.0  the method is exactly a disguised pool offset (learns nothing)
     > 1.0  the method buys cold gain more cheaply than a pure offset, i.e.
            it carries genuine within-cold relevance

plus the genuine share = within-cold gain / full-catalog cold gain.

Waits for a free GPU before each eval (the parallel session's lock intent).
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
DECOMP = os.path.join(HERE, "poc_offset_decomp.py")
GPU_BUSY_MIB = 6000


def gpu_busy():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=30)
        return int(o.stdout.strip().splitlines()[0]) >= GPU_BUSY_MIB
    except Exception:
        return False


def targets():
    """Checkpointed runs worth decomposing (need a non-trivial cold pool)."""
    out = []
    for p in sorted(glob.glob(os.path.join(OUT, "results_K5_text_k0_MI_seed*.json"))):
        if "capset" in p:
            continue
        if os.path.exists(p.replace(".json", ".best.pt")):
            out.append(p)
    for p in sorted(glob.glob(os.path.join(OUT, "results_DOSE_text_MI_seed*.json"))):
        if "capset" in p:
            continue
        if os.path.exists(p.replace(".json", ".best.pt")):
            out.append(p)
    for extra in ("results_KDIALCK_text_k0_MI_seed20260736.json",
                  "results_KDIALCK_text_k0f0.05_MI_seed20260736.json",
                  "results_POC_VG_idonly_seed20260851.json"):
        p = os.path.join(OUT, extra)
        if os.path.exists(p) and os.path.exists(p.replace(".json", ".best.pt")):
            out.append(p)
    return out


def main():
    max_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 99
    done = 0
    for p in targets():
        dst = os.path.join(OUT, os.path.basename(p).replace(
            ".json", ".offset_decomp.json"))
        if os.path.exists(dst):
            continue
        if done >= max_runs:
            break
        if gpu_busy():
            print("GPU BUSY — stopping without launching.", flush=True)
            break
        print(f"DECOMP {os.path.basename(p)}", flush=True)
        rc = subprocess.run([sys.executable, "-u", DECOMP, p],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.STDOUT).returncode
        print(f"  rc={rc}", flush=True)
        if rc != 0:
            sys.exit(rc)
        done += 1

    # ---- aggregate ---------------------------------------------------------
    rows = []
    for f in sorted(glob.glob(os.path.join(OUT, "*.offset_decomp.json"))):
        r = json.load(open(f, encoding="utf-8"))
        A = r["arms"]["stock_plus_offset"]["by_offset"]
        B = r["arms"]["knn_imputed_plus_offset"]["by_offset"]
        base, imp = A["0.0"], B["0.0"]
        g = imp["cold_full_ndcg10"] - base["cold_full_ndcg10"]
        c = base["warm_full_ndcg10"] - imp["warm_full_ndcg10"]     # positive = cost
        w = imp["cold_within_ndcg10"] - base["cold_within_ndcg10"]
        # best pure offset: smallest cost-per-gain among offsets with gain > 0
        best = None
        for k, v in A.items():
            gk = v["cold_full_ndcg10"] - base["cold_full_ndcg10"]
            ck = base["warm_full_ndcg10"] - v["warm_full_ndcg10"]
            if gk > 1e-9:
                rate = ck / gk
                if best is None or rate < best[0]:
                    best = (rate, float(k), gk, ck)
        if g <= 0 or best is None:
            continue
        method_rate = c / g
        rows.append({
            "run": r["run"], "n_cold_items": r["n_cold_items"],
            "cold_gain": g, "warm_cost": c, "within_gain": w,
            "genuine_share": w / g if g else float("nan"),
            "method_cost_per_gain": method_rate,
            "offset_cost_per_gain": best[0], "best_offset_delta": best[1],
            "efficiency_ratio": best[0] / method_rate if method_rate else float("nan"),
            # CLAIM #9 (coarse-vs-fine): AUC = broad within-pool discrimination,
            # NDCG@10/MRR = top-rank precision. Both offset-invariant.
            "auc_gain": imp.get("cold_within_auc", float("nan"))
                        - base.get("cold_within_auc", float("nan")),
            "mrr_gain": imp.get("cold_within_mrr", float("nan"))
                        - base.get("cold_within_mrr", float("nan")),
            "ndcg_within_gain": w})

    if not rows:
        print("no decompositions yet")
        return
    print(f"\n{'run':>46} {'N_cold':>7} {'genuine%':>9} {'method c/g':>11} "
          f"{'offset c/g':>11} {'eff.ratio':>10}")
    for x in rows:
        print(f"{x['run'][:46]:>46} {x['n_cold_items']:>7,} "
              f"{100*x['genuine_share']:>8.1f}% {x['method_cost_per_gain']:>11.2f} "
              f"{x['offset_cost_per_gain']:>11.2f} {x['efficiency_ratio']:>10.2f}")

    def agg(fam, prefix, label):
        if len(fam) < 2:
            return
        n = len(fam)
        tcrit = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776}.get(n - 1, 1.96)
        print(f"\n--- {label} ({n} seeds) ---")
        for name, key in (("efficiency ratio", "efficiency_ratio"),
                          ("within-pool AUC gain", "auc_gain"),
                          ("within-pool MRR gain", "mrr_gain"),
                          ("within-pool NDCG@10 gain", "ndcg_within_gain")):
            v = np.array([x[key] for x in fam], dtype=float)
            if np.isnan(v).any():
                continue
            m, sd = float(v.mean()), float(v.std(ddof=1))
            se = sd / np.sqrt(n)
            lo, hi = m - tcrit * se, m + tcrit * se
            ex = "EXCL 0" if (lo > 0 or hi < 0) else "incl 0"
            print(f"  {name:>26}: {m:>+9.5f} +- {sd:<8.5f} "
                  f"CI[{lo:>+9.5f},{hi:>+9.5f}] {ex:>6}  "
                  f"{int((v > 0).sum())}/{n} pos")

    agg([x for x in rows if x["run"].startswith("results_K5_")], "K5",
        "K-DIAL k0 pool (N=3121)")
    agg([x for x in rows if x["run"].startswith("results_DOSE_")], "DOSE",
        "DOSE k0 pool (N=455)")
    json.dump(rows, open(os.path.join(OUT, "decomp_sweep.json"), "w",
                         encoding="utf-8"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'decomp_sweep.json')}")


if __name__ == "__main__":
    main()
