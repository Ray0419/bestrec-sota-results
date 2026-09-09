# -*- coding: utf-8 -*-
"""AMENDMENT A1 E1/E2 analysis -- frozen rules from PREREG_RHO_K_V1 S5a.

E1: own-dataset coverage trade  g_b(lambda) = Cov_b(lambda) - Cov_b(0)
E2: P1  sign(dS_meas(lambda)) == sign(dS_pred(lambda)) for every lambda whose
        dS_pred CI excludes 0, on MI and Steam (per-dataset verdict);
    P2  (secondary, loose) pred/meas magnitude ratio in [0.5, 2] at the
        lambda maximizing |dS_pred|.
dS_pred(lambda) = sum_b w_b * dCov_b(lambda) * R_b,  with R_b the same-seed
FORCED-coverage conversion (text retriever, K=200) from *.pool_conv.json and
w_b the event share of bucket b.  All quantities per seed, CI across seeds
(t, df=n-1).  No lambda-grid, K, or bucket changes permitted.
"""
import glob
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
TCRIT = {4: 2.7764}
BINS = ["k0-0", "k1-2", "k3-5", "k6-10", "k11-20", "k21-50",
        "k51-200", "k201-1000000000"]
LAMS = [round(0.1 * i, 1) for i in range(11)]


def load_pair(ds):
    pats = sorted(glob.glob(os.path.join(
        OUT, f"results_SXL_fce_d256_{ds}_seed*.cov_trade.json")))
    pairs = []
    for f in pats:
        ct = json.load(open(f, encoding="utf-8"))
        pc = json.load(open(f.replace(".cov_trade.json", ".pool_conv.json"),
                            encoding="utf-8"))
        pairs.append((ct, pc))
    return pairs


def ci(vals, alpha_t=2.7764):
    v = np.asarray(vals, float)
    m = v.mean()
    h = alpha_t * v.std(ddof=1) / math.sqrt(len(v)) if len(v) > 1 else float("nan")
    return m, h


def main():
    overall = {}
    for ds in ("MI", "STEAM"):
        pairs = load_pair(ds)
        n = len(pairs)
        print(f"\n=== {ds}  n={n} seeds ===")
        dS_meas = {l: [] for l in LAMS}
        dS_pred = {l: [] for l in LAMS}
        dcov_tab = {l: {b: [] for b in BINS} for l in LAMS}
        for ct, pc in pairs:
            bk = ct["buckets"]
            # per-seed R_b from the forced-coverage instrument (text, K=200)
            R = {}
            for b in BINS:
                a = pc["pool"]["text"][b]["200"]
                R[b] = (a["hit_forced"] / a["n"]) if a["n"] else 0.0
            ntot = sum(bk[b]["0.0"]["n"] for b in BINS)
            w = {b: bk[b]["0.0"]["n"] / ntot for b in BINS}
            s0 = sum(bk[b]["0.0"]["suc"] for b in BINS) / ntot
            for l in LAMS:
                key = str(l)
                s_l = sum(bk[b][key]["suc"] for b in BINS) / ntot
                dS_meas[l].append(s_l - s0)
                pred = 0.0
                for b in BINS:
                    c_l = bk[b][key]["cov"] / max(bk[b][key]["n"], 1)
                    c_0 = bk[b]["0.0"]["cov"] / max(bk[b]["0.0"]["n"], 1)
                    dcov_tab[l][b].append(c_l - c_0)
                    pred += w[b] * (c_l - c_0) * R[b]
                dS_pred[l].append(pred)
        # ---- report ----
        print(f"  {'lam':>5}{'dS_meas':>12}{'+/-':>9}{'dS_pred':>12}{'+/-':>9}"
              f"{'sign?':>7}{'seeds agree':>12}")
        qualified, agree_all = [], True
        for l in LAMS[1:]:
            mm, hm = ci(dS_meas[l])
            mp, hp = ci(dS_pred[l])
            qual = np.isfinite(hp) and (abs(mp) - hp) > 0
            sgn = (np.sign(mm) == np.sign(mp))
            per_seed = sum(1 for a, b in zip(dS_meas[l], dS_pred[l])
                           if np.sign(a) == np.sign(b))
            if qual:
                qualified.append(l)
                if not sgn:
                    agree_all = False
            print(f"  {l:>5}{mm:>12.6f}{hm:>9.6f}{mp:>12.6f}{hp:>9.6f}"
                  f"{('YES' if sgn else 'NO') if qual else '(n.q.)':>7}"
                  f"{per_seed:>9}/{len(dS_meas[l])}")
        # P2 at argmax |dS_pred|
        lmax = max(LAMS[1:], key=lambda l: abs(np.mean(dS_pred[l])))
        ratio = (np.mean(dS_pred[lmax]) / np.mean(dS_meas[lmax])
                 if np.mean(dS_meas[lmax]) else float("inf"))
        p2 = 0.5 <= abs(ratio) <= 2.0 and np.sign(ratio) > 0
        print(f"  P1 [{ds}]: {'SUPPORTED' if agree_all and qualified else ('NO QUALIFYING LAMBDA' if not qualified else 'REFUTED')}"
              f"  (qualifying lambdas: {qualified})")
        print(f"  P2 [{ds}]: ratio pred/meas at lam={lmax}: {ratio:+.2f} -> "
              f"{'within [0.5,2]' if p2 else 'OUTSIDE band'}")
        # E1 own-dataset trade at the qualifying lambda nearest 0.2 (report aid)
        print(f"  E1 own-dataset trade (dCov pp, seed mean) at lam=0.2:")
        for b in BINS:
            m, h = ci(dcov_tab[0.2][b])
            print(f"    {b:<16}{100*m:>+8.2f}pp +/- {100*h:.2f}")
        overall[ds] = {"P1": agree_all and bool(qualified), "P2": p2,
                       "qualified": qualified,
                       "dS_meas": {str(l): dS_meas[l] for l in LAMS},
                       "dS_pred": {str(l): dS_pred[l] for l in LAMS},
                       "dcov_lam02": {b: dcov_tab[0.2][b] for b in BINS}}
    json.dump(overall, open(os.path.join(OUT, "COV_TRADE_analysis.json"),
                            "w", encoding="utf-8"), indent=1, default=str)
    print(f"\nwrote {os.path.join(OUT, 'COV_TRADE_analysis.json')}")


if __name__ == "__main__":
    main()
