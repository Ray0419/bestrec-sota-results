# -*- coding: utf-8 -*-
"""PREREG_SCALING_V1 readout. Decision rules frozen before the runs.

Primary: beta_p, the log-log exponent in p*(N) = |c|/(g+|c|) ~ N^beta.
Confirmed iff positive in 3/3 seeds AND the across-seed 95% CI excludes 0.
"sqrt(N)" claimed only if that CI also contains 0.5.
Kill: sign-inconsistent across seeds -> withdraw, demote to qualitative.
"""
import glob
import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
DECOMP = os.path.join(HERE, "poc_offset_decomp.py")
TCRIT = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776}
GPU_BUSY_MIB = 6000


def gpu_busy():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=30)
        return int(o.stdout.strip().splitlines()[0]) >= GPU_BUSY_MIB
    except Exception:
        return False


def ensure_decomps(limit):
    n = 0
    for p in sorted(glob.glob(os.path.join(OUT, "results_SCAL_*_MI_seed*.json"))):
        if "capset" in p or not os.path.exists(p.replace(".json", ".best.pt")):
            continue
        dst = p.replace(".json", ".offset_decomp.json")
        if os.path.exists(dst):
            continue
        if n >= limit:
            break
        if gpu_busy():
            print("GPU BUSY — deferring remaining decompositions.", flush=True)
            break
        print(f"DECOMP {os.path.basename(p)}", flush=True)
        rc = subprocess.run([sys.executable, "-u", DECOMP, p],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.STDOUT).returncode
        if rc != 0:
            sys.exit(rc)
        n += 1
    return n


def load_points():
    pts = {}
    for f in sorted(glob.glob(os.path.join(OUT, "results_SCAL_*.offset_decomp.json"))):
        r = json.load(open(f, encoding="utf-8"))
        m = re.search(r"results_SCAL_(f[\d]+)_MI_seed(\d+)", r["run"])
        if not m:
            continue
        seed = int(m.group(2))
        A = r["arms"]["stock_plus_offset"]["by_offset"]
        B = r["arms"]["knn_imputed_plus_offset"]["by_offset"]
        base, imp = A["0.0"], B["0.0"]
        g = imp["cold_full_ndcg10"] - base["cold_full_ndcg10"]
        c = base["warm_full_ndcg10"] - imp["warm_full_ndcg10"]
        best = None
        for k, v in A.items():
            gk = v["cold_full_ndcg10"] - base["cold_full_ndcg10"]
            ck = base["warm_full_ndcg10"] - v["warm_full_ndcg10"]
            if gk > 1e-9:
                rate = ck / gk
                if best is None or rate < best:
                    best = rate
        if g <= 0 or c <= 0 or not best:
            continue
        pts.setdefault(seed, []).append({
            "N": r["n_cold_items"], "g": g, "c": c,
            "pstar": c / (g + c), "ratio": best / (c / g),
            "auc_gain": imp.get("cold_within_auc", float("nan"))
                        - base.get("cold_within_auc", float("nan"))})
    for s in pts:
        pts[s].sort(key=lambda x: x["N"])
    return pts


def tstat(x):
    x = np.asarray(x, float)
    n = len(x)
    m, sd = float(x.mean()), float(x.std(ddof=1)) if n > 1 else (float(x.mean()), float("nan"))
    sd = float(x.std(ddof=1)) if n > 1 else float("nan")
    se = sd / np.sqrt(n) if n > 1 else float("nan")
    tc = TCRIT.get(n - 1, 1.96)
    return {"mean": m, "sd": sd, "ci95": [m - tc * se, m + tc * se],
            "n_pos": int((x > 0).sum()), "n": n}


def main():
    if len(sys.argv) > 1:
        ensure_decomps(int(sys.argv[1]))
    pts = load_points()
    if not pts:
        print("no decompositions yet")
        return
    print(f"{'seed':>10} {'N':>7} {'cold gain':>11} {'warm cost':>11} "
          f"{'p*':>9} {'eff.ratio':>10} {'AUC gain':>10}")
    for s in sorted(pts):
        for p in pts[s]:
            print(f"{s:>10} {p['N']:>7,} {p['g']:>+11.5f} {p['c']:>+11.5f} "
                  f"{100*p['pstar']:>8.2f}% {p['ratio']:>10.2f} "
                  f"{p['auc_gain']:>+10.5f}")

    betas = {"pstar": [], "c": [], "g": [], "ratio": []}
    usable = [s for s in sorted(pts) if len(pts[s]) >= 3]
    for s in usable:
        N = np.array([p["N"] for p in pts[s]], float)
        for key, field in (("pstar", "pstar"), ("c", "c"), ("g", "g"),
                           ("ratio", "ratio")):
            y = np.array([p[field] for p in pts[s]], float)
            if (y <= 0).any():
                continue
            betas[key].append(float(np.polyfit(np.log(N), np.log(y), 1)[0]))

    print(f"\n=== per-seed log-log exponents ({len(usable)} usable seeds) ===")
    for key in ("pstar", "c", "g", "ratio"):
        if betas[key]:
            print(f"  {key:>6} ~ N^b : " +
                  "  ".join(f"{b:+.3f}" for b in betas[key]))

    if not betas["pstar"]:
        print("\ninsufficient points for the primary test")
        return
    st = tstat(betas["pstar"])
    consistent = st["n_pos"] in (0, st["n"])
    excl0 = st["ci95"][0] > 0 or st["ci95"][1] < 0
    has_half = st["ci95"][0] <= 0.5 <= st["ci95"][1]
    print("\n=== PRE-REGISTERED TEST (primary: beta_p) ===")
    print(f"  beta_p = {st['mean']:+.3f} +- {st['sd']:.3f}  "
          f"CI[{st['ci95'][0]:+.3f}, {st['ci95'][1]:+.3f}]  "
          f"{st['n_pos']}/{st['n']} positive")
    verdict = ("CONFIRMED" if (st["n_pos"] == st["n"] and excl0)
               else "WITHDRAWN (sign-inconsistent)" if not consistent
               else "NOT CONFIRMED (CI includes 0)")
    print(f"  scaling law: {verdict}")
    if st["n_pos"] == st["n"] and excl0:
        print(f"  sqrt(N) framing: {'RETAINED' if has_half else 'DROPPED'} "
              f"(CI {'contains' if has_half else 'excludes'} 0.5) -> report at "
              f"measured exponent {st['mean']:+.3f}")
    rep = {"points": {str(k): v for k, v in pts.items()}, "betas": betas,
           "primary": {**st, "verdict": verdict, "ci_contains_0.5": bool(has_half)}}
    json.dump(rep, open(os.path.join(OUT, "scaling_v1_analysis.json"), "w",
                        encoding="utf-8"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'scaling_v1_analysis.json')}")


if __name__ == "__main__":
    main()
