# -*- coding: utf-8 -*-
"""PREREG_SCALE_LOSS_V1 analyser -- FROZEN per PREREG S5 before any endpoint read.

Implements exactly the estimands in PREREG_SCALE_LOSS_V1.md S5, no others:

  bands (event-count weighted, from by_degree in *.degree_eval.json)
    TAIL = k1-2, k3-5, k6-10, k11-20, k21-50      (k=0 EXCLUDED: degenerate,
                                                   exactly 0.00000 in every arm)
    HEAD = k>200
    AGG  = warm

  S_l(b) = OLS slope of NDCG@10 on log2(d_model) over the rungs, fitted PER SEED.

  H1 gate      fCE relative tail slope > fCE relative head slope
               (each band normalised by its own d=32 level first)
  H2 PRIMARY   S_gBCE(TAIL) - S_fCE(TAIL) < 0        paired by seed
  H3 NULL      S_sCE(TAIL)  - S_fCE(TAIL) CI includes 0
  H4 instrument per rung |D%(gBCE-fCE) TAIL| / |D%(gBCE-fCE) AGG| > 5

  Two-sided, alpha=0.05, Holm across {H2, H3, H4}.  H1 is a gate, not a claim,
  and is NOT in the correction family.  Decisions use t critical values (no
  scipy dependency, matching poc_family_aggregate.py's TC convention).

Usage:  python poc_scale_loss_analyze.py [--stage2]
        --stage2 switches the seed set to n=5 and the df=4 critical values.
"""
import glob
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")

LOSSES = ("fce", "sce", "gbce")
RUNGS = (32, 64, 128, 256)
TAIL_BUCKETS = ("k1-2", "k3-5", "k6-10", "k11-20", "k21-50")
HEAD_BUCKET = "k201-1000000000"
ALL_BUCKETS = TAIL_BUCKETS + ("k51-200", HEAD_BUCKET)

# Two-sided t critical values.  Holm needs three levels for a family of 3.
TCRIT = {2: {0.05: 4.3027, 0.025: 6.2053, 0.0166667: 7.6488},
         4: {0.05: 2.7764, 0.025: 3.4954, 0.0166667: 3.9608}}

# AMENDMENT A2: set by `--lr <value>`; None = the main lr=1e-3 ladder.
LR = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--lr"), None)


def load(loss, d, seed):
    # AMENDMENT A2: --lr <x> reads the lr-suffixed ladder instead of the main one.
    suf = f"_lr{LR}" if LR else ""
    p = os.path.join(OUT, f"results_SXL_{loss}_d{d}{suf}_MI_seed{seed}.degree_eval.json")
    if not os.path.exists(p):
        return None
    r = json.load(open(p, encoding="utf-8"))
    res = r.get("results", r)
    key = next((k for k in res if k.startswith("stock")), None)
    if key is None:
        return None
    node = res[key]
    bd = node.get("by_degree", {})
    return {"by_degree": bd, "warm": node.get("warm"),
            "overall": node.get("overall")}


def band(bd, buckets):
    """Event-count weighted mean NDCG@10 over the given degree buckets."""
    num = den = 0.0
    for b in buckets:
        if b in bd:
            num += bd[b]["n"] * bd[b]["ndcg10"]
            den += bd[b]["n"]
    return (num / den) if den else float("nan")


def slope(xs, ys):
    """OLS slope of y on x.  Returns nan if fewer than 2 finite points."""
    x = np.asarray(xs, float)
    y = np.asarray(ys, float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 2:
        return float("nan")
    x, y = x[m], y[m]
    return float(((x - x.mean()) * (y - y.mean())).sum() / ((x - x.mean()) ** 2).sum())


def ci(vals, df, alpha=0.05):
    """mean, half-width, n for a paired difference at the given alpha."""
    v = np.asarray([x for x in vals if np.isfinite(x)], float)
    n = len(v)
    if n < 2:
        return (float(v[0]) if n else float("nan")), float("nan"), n
    tc = TCRIT[df][min(TCRIT[df], key=lambda a: abs(a - alpha))]
    return float(v.mean()), float(tc * v.std(ddof=1) / math.sqrt(n)), n


def main():
    stage2 = "--stage2" in sys.argv
    seeds = ((20260736, 20260737, 20260738, 20260739, 20260740) if stage2
             else (20260736, 20260737, 20260738))
    df = len(seeds) - 1
    print(f"PREREG_SCALE_LOSS_V1 -- {'STAGE 2 (n=5, inference)' if stage2 else 'STAGE 1 (n=3, SCREEN ONLY -- NO CLAIMS)'}")
    print(f"seeds={seeds}  df={df}\n")

    # ---- load, report coverage honestly -------------------------------------
    D = {}
    missing = []
    for loss in LOSSES:
        for d in RUNGS:
            for s in seeds:
                r = load(loss, d, s)
                if r is None:
                    missing.append(f"{loss}_d{d}_s{s}")
                else:
                    D[(loss, d, s)] = r
    print(f"cells present: {len(D)}/{len(LOSSES)*len(RUNGS)*len(seeds)}")
    if missing:
        print(f"MISSING ({len(missing)}): {', '.join(missing)}")
        print("  -> slopes are fitted on available rungs only; any loss arm with "
              "<2 rungs yields nan and is reported as such, never imputed.\n")

    # ---- secondary: full per-rung bucket table ------------------------------
    print("=== SECONDARY: per-rung, per-bucket NDCG@10 (seed mean) ===")
    hdr = f"{'bucket':<18}" + "".join(f"{f'{l}/d{d}':>14}" for d in RUNGS for l in LOSSES)
    print(hdr)
    for b in ALL_BUCKETS + ("warm",):
        row = f"{b:<18}"
        for d in RUNGS:
            for loss in LOSSES:
                vs = [D[(loss, d, s)]["by_degree"].get(b, {}).get("ndcg10")
                      if b != "warm" else D[(loss, d, s)]["warm"]
                      for s in seeds if (loss, d, s) in D]
                vs = [v for v in vs if v is not None]
                row += f"{(sum(vs)/len(vs)):>14.6f}" if vs else f"{'-':>14}"
        print(row)
    print()

    # ---- band values and per-seed slopes ------------------------------------
    def bandval(loss, d, s, which):
        r = D.get((loss, d, s))
        if r is None:
            return float("nan")
        if which == "TAIL":
            return band(r["by_degree"], TAIL_BUCKETS)
        if which == "HEAD":
            return band(r["by_degree"], (HEAD_BUCKET,))
        return r["warm"]

    S = {}          # absolute slope
    Srel = {}       # slope after normalising the band by its own d=32 level
    for loss in LOSSES:
        for which in ("TAIL", "HEAD", "AGG"):
            for s in seeds:
                ys = [bandval(loss, d, s, which) for d in RUNGS]
                xs = [math.log2(d) for d in RUNGS]
                S[(loss, which, s)] = slope(xs, ys)
                base = ys[RUNGS.index(32)]
                Srel[(loss, which, s)] = (slope(xs, [y / base for y in ys])
                                          if base and np.isfinite(base) else float("nan"))

    print("=== per-seed OLS slopes on log2(d_model) ===")
    for which in ("TAIL", "HEAD", "AGG"):
        for loss in LOSSES:
            v = [S[(loss, which, s)] for s in seeds]
            r = [Srel[(loss, which, s)] for s in seeds]
            print(f"  {which:<5} {loss:<5} abs={['%.6f' % x for x in v]}  "
                  f"rel={['%.4f' % x for x in r]}")
    print()

    # ---- H1 gate ------------------------------------------------------------
    d1 = [Srel[("fce", "TAIL", s)] - Srel[("fce", "HEAD", s)] for s in seeds]
    m, h, n = ci(d1, df)
    npos = sum(1 for x in d1 if np.isfinite(x) and x > 0)
    gate = np.isfinite(m) and (m - h) > 0
    print("=== H1 GATE (replication of arXiv:2311.11351 direction) ===")
    print(f"  relS_fCE(TAIL) - relS_fCE(HEAD) = {m:+.4f} +/- {h:.4f}  "
          f"({npos}/{n} positive)")
    print(f"  -> {'PASS' if gate else 'FAIL'}: "
          + ("full-CE tail benefits more from scale than head."
             if gate else "premise NOT replicated in this regime -- per PREREG S5, "
                          "H2 becomes DESCRIPTIVE ONLY and the paper is rewritten "
                          "as a failed replication."))
    print()

    # ---- H2 / H3 / H4 with Holm --------------------------------------------
    tests = []

    d2 = [S[("gbce", "TAIL", s)] - S[("fce", "TAIL", s)] for s in seeds]
    tests.append(("H2", "S_gBCE(TAIL) - S_fCE(TAIL) < 0  [PRIMARY]", d2, "neg"))

    d3 = [S[("sce", "TAIL", s)] - S[("fce", "TAIL", s)] for s in seeds]
    tests.append(("H3", "S_sCE(TAIL) - S_fCE(TAIL) ~ 0   [pre-registered NULL]",
                  d3, "null"))

    # H4: per-rung amplification, tested as "min over rungs > 5"
    amp_by_rung = {}
    for d in RUNGS:
        per_seed = []
        for s in seeds:
            t_g, t_f = bandval("gbce", d, s, "TAIL"), bandval("fce", d, s, "TAIL")
            a_g, a_f = bandval("gbce", d, s, "AGG"), bandval("fce", d, s, "AGG")
            if not all(np.isfinite(x) and x for x in (t_f, a_f)):
                per_seed.append(float("nan"))
                continue
            dt = abs((t_g - t_f) / t_f)
            da = abs((a_g - a_f) / a_f)
            per_seed.append(dt / da if da else float("inf"))
        amp_by_rung[d] = per_seed
    worst = min(RUNGS, key=lambda d: np.nanmean(amp_by_rung[d])
                if np.isfinite(np.nanmean(amp_by_rung[d])) else np.inf)
    d4 = [x - 5.0 for x in amp_by_rung[worst]]
    tests.append(("H4", f"min-over-rungs amplification > 5  (worst rung d={worst})",
                  d4, "pos"))

    # Holm: order by |t| descending == most significant first
    stats = []
    for name, desc, vals, direction in tests:
        m, h, n = ci(vals, df)
        v = np.asarray([x for x in vals if np.isfinite(x)], float)
        se = (v.std(ddof=1) / math.sqrt(len(v))) if len(v) > 1 else float("nan")
        t = (m / se) if (np.isfinite(se) and se) else float("nan")
        stats.append({"name": name, "desc": desc, "vals": vals, "dir": direction,
                      "m": m, "n": n, "se": se, "t": t})
    order = sorted(range(len(stats)),
                   key=lambda i: -(abs(stats[i]["t"]) if np.isfinite(stats[i]["t"]) else -1))
    levels = [0.0166667, 0.025, 0.05]      # Holm: alpha/3, alpha/2, alpha

    print("=== H2 / H3 / H4  (Holm-corrected across the family of 3) ===")
    verdict = {}
    for rank, i in enumerate(order):
        st = stats[i]
        alpha = levels[rank]
        tc = TCRIT[df][alpha]
        h = tc * st["se"] if np.isfinite(st["se"]) else float("nan")
        lo, hi = st["m"] - h, st["m"] + h
        if st["dir"] == "neg":
            ok = np.isfinite(hi) and hi < 0
        elif st["dir"] == "pos":
            ok = np.isfinite(lo) and lo > 0
        else:                                # null: CI must INCLUDE 0
            ok = np.isfinite(lo) and lo <= 0 <= hi
        verdict[st["name"]] = ok
        signs = sum(1 for x in st["vals"] if np.isfinite(x) and x > 0)
        print(f"  {st['name']}  {st['desc']}")
        print(f"      mean={st['m']:+.6f}  Holm alpha={alpha:.4f} (t*={tc})  "
              f"CI=[{lo:+.6f}, {hi:+.6f}]  {signs}/{st['n']} positive  "
              f"-> {'SUPPORTED' if ok else 'not supported'}")
    print()
    print("  H4 amplification by rung (seed mean):  "
          + "  ".join(f"d{d}={np.nanmean(amp_by_rung[d]):.2f}x" for d in RUNGS))
    print()

    # ---- stage gate ---------------------------------------------------------
    if not stage2:
        fin = [x for x in d2 if np.isfinite(x)]
        consistent = len(fin) == len(seeds) and (all(x < 0 for x in fin)
                                                 or all(x > 0 for x in fin))
        print("=== STAGE 1 -> STAGE 2 GATE (PREREG S6) ===")
        print(f"  sign of H2 contrast: {['%+.6f' % x for x in d2]}")
        print(f"  -> {'FIRE: extend to seeds 20260739, 20260740 for n=5 inference.' if consistent else 'DO NOT FIRE: sign not consistent 3/3.'}")
        print("  REMINDER: no claim is made at n=3.  This program already had a "
              "2/3-seed interim reverse at 5 seeds.")
    else:
        print("=== STAGE 2 VERDICT (PREREG S8: publishable under every outcome) ===")
        if verdict.get("H2") and verdict.get("H3"):
            print("  H2 supported with the H3 null intact -> tail scaling gains are "
                  "CONDITIONAL on the loss regime, and the damage is attributable "
                  "to beta rather than negative count.")
        elif verdict.get("H2") and not verdict.get("H3"):
            print("  H2 supported but H3 NULL FAILED -> the interaction is real but "
                  "NOT cleanly attributable to beta; causal language must be "
                  "withdrawn and the negative-count pathway reported.")
        else:
            print("  H2 not supported -> capacity plausibly rescues the tail; beta "
                  "damage may be a small-model artifact.  This DEFENDS gSASRec and "
                  "rescopes our own S6.6.1.  Report with equal prominence.")

    json.dump({"seeds": list(seeds), "cells_present": len(D), "missing": missing,
               "slopes": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in S.items()},
               "slopes_rel": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in Srel.items()},
               "H1_gate": bool(gate),
               "amp_by_rung": {str(d): amp_by_rung[d] for d in RUNGS},
               "verdicts": verdict},
              open(os.path.join(OUT, "SXL_analysis.json"), "w", encoding="utf-8"),
              indent=1, default=str)
    print(f"\nwrote {os.path.join(OUT, 'SXL_analysis.json')}")


if __name__ == "__main__":
    main()
