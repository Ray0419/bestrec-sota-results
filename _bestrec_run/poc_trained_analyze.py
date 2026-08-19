# -*- coding: utf-8 -*-
"""PREREG_TRAINED_V1 readout. Decision rules frozen before the runs.

H1  T1/T2a measurable under the instruments (F04 answer; no directional claim)
H2  T2b > T2a on cold NDCG@10 at equal-or-better warm, >=4/5 seeds, CI excl 0,
    warm not worse than T2a by more than 0.001 absolute
H3  MECHANISM TRAP: if cold NDCG rises but within-pool AUC does not, the gain
    is a pool-offset artifact and H2 is WITHDRAWN (our own S3 result, applied
    to ourselves).
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
TC = {2: 4.303, 3: 3.182, 4: 2.776}
ARMS = ("T1", "T2a", "T2b")


def gpu_busy():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=30)
        return int(o.stdout.strip().splitlines()[0]) >= 6000
    except Exception:
        return False


def ensure(limit):
    n = 0
    for p in sorted(glob.glob(os.path.join(OUT, "results_TRN_*_MI_seed*.json"))):
        if "capset" in p or not os.path.exists(p.replace(".json", ".best.pt")):
            continue
        dst = p.replace(".json", ".temporal_eval.json")
        if os.path.exists(dst) or n >= limit:
            continue
        if gpu_busy():
            print("GPU BUSY — deferring remaining evals.", flush=True)
            break
        print(f"EVAL {os.path.basename(p)}", flush=True)
        rc = subprocess.run([sys.executable, "-u", EVAL, p, "--out", dst],
                            stdout=open(dst.replace(".json", ".log"), "w",
                                        encoding="utf-8"),
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
    tc = TC.get(n - 1, 1.96)
    return m, sd, [m - tc * se, m + tc * se], n, int((x > 0).sum())


def main():
    if len(sys.argv) > 1:
        ensure(int(sys.argv[1]))
    data = {}
    for arm in ARMS:
        rows = []
        for f in sorted(glob.glob(os.path.join(
                OUT, f"results_TRN_{arm}_MI_seed*.temporal_eval.json"))):
            r = json.load(open(f, encoding="utf-8"))
            R = r["results"]
            rows.append({"seed": f.split("seed")[1][:8],
                         "cold": R["stock@0"]["cold"],
                         "warm": R["stock@0"]["warm"],
                         "overall": R["stock@0"]["overall"],
                         "auc": R["stock@0"]["cold_auc"],
                         "imp_cold": R["imputed@0"]["cold"],
                         "imp_overall": R["imputed@0"]["overall"],
                         "E1": r["E1_auc_gain"], "E4": r["E4_overall_delta"],
                         "pstar": r.get("E3_pstar")})
        if rows:
            data[arm] = rows
    # B0 reference from the existing stock temporal runs
    b0 = []
    for f in sorted(glob.glob(os.path.join(
            OUT, "results_TEMP_MI_seed*.temporal_eval.json"))):
        r = json.load(open(f, encoding="utf-8"))
        R = r["results"]
        b0.append({"cold": R["stock@0"]["cold"], "warm": R["stock@0"]["warm"],
                   "overall": R["stock@0"]["overall"],
                   "auc": R["stock@0"]["cold_auc"]})
    if b0:
        data["B0"] = b0

    print(f"{'arm':>5} {'n':>2} {'cold NDCG':>18} {'warm NDCG':>18} "
          f"{'overall':>18} {'within-pool AUC':>18}")
    for arm in ("B0",) + ARMS:
        if arm not in data:
            continue
        d = data[arm]
        cells = []
        for k in ("cold", "warm", "overall", "auc"):
            x = np.array([r[k] for r in d], float)
            cells.append(f"{x.mean():.5f}+-{x.std(ddof=1) if len(x)>1 else 0:.5f}")
        print(f"{arm:>5} {len(d):>2} " + " ".join(f"{c:>18}" for c in cells))

    rep = {}
    if "T2a" in data and "T2b" in data:
        n = min(len(data["T2a"]), len(data["T2b"]))
        dc = np.array([data["T2b"][i]["cold"] - data["T2a"][i]["cold"]
                       for i in range(n)])
        dw = np.array([data["T2b"][i]["warm"] - data["T2a"][i]["warm"]
                       for i in range(n)])
        da = np.array([data["T2b"][i]["auc"] - data["T2a"][i]["auc"]
                       for i in range(n)])
        mc, sdc, cic, nc, posc = tstat(dc)
        mw, sdw, ciw, _, _ = tstat(dw)
        ma, sda, cia, _, posa = tstat(da)
        print("\n=== H2 (primary): T2b - T2a ===")
        print(f"  cold NDCG@10 : {mc:+.6f} +-{sdc:.6f} "
              f"CI[{cic[0]:+.6f},{cic[1]:+.6f}]  {posc}/{nc} pos")
        print(f"  warm NDCG@10 : {mw:+.6f} (guard: not worse than -0.001)")
        print(f"  within-pool AUC: {ma:+.6f} CI[{cia[0]:+.6f},{cia[1]:+.6f}] "
              f"{posa}/{nc} pos")
        cold_ok = (posc >= max(4, nc)) or (posc == nc)
        ci_ok = cic[0] > 0
        warm_ok = mw >= -0.001
        h2 = cold_ok and ci_ok and warm_ok
        auc_ok = ma > 0 and cia[0] > 0
        print(f"\n  H2: {'CONFIRMED' if h2 else 'NOT CONFIRMED'} "
              f"(cold {posc}/{nc}, CI {'excl' if ci_ok else 'incl'} 0, "
              f"warm guard {'ok' if warm_ok else 'FAILED'})")
        if h2:
            print(f"  H3 mechanism trap: within-pool AUC "
                  f"{'ROSE — gain is genuine' if auc_ok else 'DID NOT rise — '
                     'gain is an OFFSET ARTIFACT, H2 WITHDRAWN'}")
        rep = {"H2_cold_delta": [mc, sdc, cic, nc, posc],
               "H2_warm_delta": mw, "H3_auc_delta": [ma, sda, cia],
               "H2_confirmed": bool(h2), "H3_mechanism_ok": bool(auc_ok)}
    json.dump({"arms": data, "verdict": rep},
              open(os.path.join(OUT, "trained_analysis.json"), "w",
                   encoding="utf-8"), indent=1, default=float)
    print(f"\nwrote {os.path.join(OUT, 'trained_analysis.json')}")


if __name__ == "__main__":
    main()
