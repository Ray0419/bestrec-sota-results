# -*- coding: utf-8 -*-
"""PREREG_TEMPORAL_V1 readout. Decision rules frozen before the runs (S3).

E1 within-pool AUC gain  : confirmed iff all seeds > 0 and 95% CI excludes 0
E2 efficiency ratio      : confirmed iff all seeds > 1 and 95% CI EXCLUDES 1.0
E3 break-even p*         : reported with CI, compared to observed pi_t
E4 PRIMARY overall delta : imputation pays iff all seeds > 0 and CI excludes 0
                           (E3 vs pi_t must agree in sign with E4)

Runs any missing temporal evals first (GPU-probed), then aggregates.
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
EVAL = os.path.join(HERE, "poc_temporal_eval.py")
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


def ensure(limit):
    n = 0
    for p in sorted(glob.glob(os.path.join(OUT, "results_TEMP_*_seed*.json"))):
        if not os.path.exists(p.replace(".json", ".best.pt")):
            continue
        dst = p.replace(".json", ".temporal_eval.json")
        if os.path.exists(dst) or n >= limit:
            continue
        if gpu_busy():
            print("GPU BUSY — deferring remaining evals.", flush=True)
            break
        print(f"EVAL {os.path.basename(p)}", flush=True)
        rc = subprocess.run([sys.executable, "-u", EVAL, p],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.STDOUT).returncode
        if rc != 0:
            sys.exit(rc)
        n += 1
    return n


def tstat(x):
    x = np.asarray(x, float)
    n = len(x)
    m = float(x.mean())
    sd = float(x.std(ddof=1)) if n > 1 else float("nan")
    se = sd / np.sqrt(n) if n > 1 else float("nan")
    tc = TCRIT.get(n - 1, 1.96)
    return {"mean": m, "sd": sd, "ci95": [m - tc * se, m + tc * se], "n": n,
            "n_pos": int((x > 0).sum())}


def main():
    if len(sys.argv) > 1:
        ensure(int(sys.argv[1]))
    rows = {}
    for f in sorted(glob.glob(os.path.join(OUT, "*.temporal_eval.json"))):
        r = json.load(open(f, encoding="utf-8"))
        if not r["run"].startswith("results_TEMP_"):
            continue
        tag = r["run"].split("_")[2]
        rows.setdefault(tag, []).append(r)
    if not rows:
        print("no temporal evals yet")
        return

    rep = {}
    for tag, rs in rows.items():
        b = [x["results"]["stock@0"] for x in rs]
        i = [x["results"]["imputed@0"] for x in rs]
        pi = float(np.mean([x["pi_t"] for x in rs]))
        e1 = tstat([x["E1_auc_gain"] for x in rs])
        e4 = tstat([x["E4_overall_delta"] for x in rs])
        pstar = tstat([x["E3_pstar"] for x in rs if x["E3_pstar"] is not None])
        # E2: cost-per-gain of the best pure offset / that of the method
        ratios = []
        for x in rs:
            R = x["results"]
            g = R["imputed@0"]["cold"] - R["stock@0"]["cold"]
            c = R["stock@0"]["warm"] - R["imputed@0"]["warm"]
            best = None
            for k, v in R.items():
                if not k.startswith("stock@"):
                    continue
                d = float(k.split("@")[1])
                if d == 0:
                    continue
                gk = v["cold"] - R["stock@0"]["cold"]
                ck = R["stock@0"]["warm"] - v["warm"]
                if gk > 1e-9:
                    rr = ck / gk
                    best = rr if best is None else min(best, rr)
            if best and g > 0 and c > 0:
                ratios.append(best / (c / g))
        e2 = tstat(ratios) if len(ratios) >= 2 else None

        print(f"\n=== {tag} ({len(rs)} seeds) — observed pi_t = {100*pi:.2f}% ===")
        print(f"  stock   overall {np.mean([x['overall'] for x in b]):.5f}  "
              f"cold {np.mean([x['cold'] for x in b]):.5f}  "
              f"warm {np.mean([x['warm'] for x in b]):.5f}")
        print(f"  imputed overall {np.mean([x['overall'] for x in i]):.5f}  "
              f"cold {np.mean([x['cold'] for x in i]):.5f}  "
              f"warm {np.mean([x['warm'] for x in i]):.5f}")
        ex1 = e1["ci95"][0] > 0 or e1["ci95"][1] < 0
        print(f"  E1 AUC gain      {e1['mean']:+.5f} +-{e1['sd']:.5f} "
              f"CI[{e1['ci95'][0]:+.5f},{e1['ci95'][1]:+.5f}] "
              f"{e1['n_pos']}/{e1['n']}  -> "
              f"{'CONFIRMED' if (ex1 and e1['n_pos'] == e1['n']) else 'not confirmed'}")
        if e2:
            ex2 = e2["ci95"][0] > 1.0
            print(f"  E2 eff. ratio    {e2['mean']:.3f} +-{e2['sd']:.3f} "
                  f"CI[{e2['ci95'][0]:.3f},{e2['ci95'][1]:.3f}] -> "
                  f"{'CONFIRMED (excludes 1.0)' if ex2 else 'not confirmed'}")
        if pstar["n"]:
            print(f"  E3 p*            {100*pstar['mean']:.2f}% "
                  f"CI[{100*pstar['ci95'][0]:.2f}%,{100*pstar['ci95'][1]:.2f}%]  "
                  f"vs pi_t {100*pi:.2f}%  -> imputation should "
                  f"{'PAY' if pi > pstar['mean'] else 'NOT pay'}")
        ex4 = e4["ci95"][0] > 0 or e4["ci95"][1] < 0
        pays = e4["mean"] > 0 and e4["n_pos"] == e4["n"] and e4["ci95"][0] > 0
        print(f"  E4 overall delta {e4['mean']:+.6f} +-{e4['sd']:.6f} "
              f"CI[{e4['ci95'][0]:+.6f},{e4['ci95'][1]:+.6f}] "
              f"{e4['n_pos']}/{e4['n']}")
        print(f"  E4 VERDICT: imputation {'PAYS' if pays else 'does NOT pay'} "
              f"at observed prevalence"
              f"{'' if ex4 else '  (CI includes 0 — inconclusive)'}")
        agree = (pi > pstar["mean"]) == (e4["mean"] > 0) if pstar["n"] else None
        print(f"  E3/E4 sign agreement: {agree}")
        rep[tag] = {"n_seeds": len(rs), "pi_t": pi, "E1": e1,
                    "E2": e2, "E3_pstar": pstar, "E4": e4,
                    "E3_E4_agree": agree}
    json.dump(rep, open(os.path.join(OUT, "temporal_analysis.json"), "w",
                        encoding="utf-8"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'temporal_analysis.json')}")


if __name__ == "__main__":
    main()
