# -*- coding: utf-8 -*-
"""PREREG_TAIL_FIR_V2 mechanical adjudicator (committed before any campaign result is
inspected; the frozen rules live in PREREG_TAIL_FIR_V2.md and are implemented here 1:1).

Endpoints (frozen):
  E1: MI positive-frequency-tail NDCG@10, text vs id, independent-arm Welch, 95% CI > 0.
  E2: IS overall NDCG@10, filter vs no-filter, Welch, 95% CI > 0.
  E3: CDs overall NDCG@10, filter vs no-filter, Welch, 95% CI > 0.
  Multiplicity: Holm across {E1,E2,E3}, family alpha 0.05.
Secondary/descriptive (no gates): MI zero-exposure bin; MI tail HR@10; sensitivity strata
(exclude-boundary group; absolute band [1,6]); VG tail delta; four-arm MI-VG contrast;
FIR per-category tail deltas.

Cohort rules (frozen, item-ID-independent):
  - item index space = sorted union of split item ids (must match run JSON n_items);
  - zero-exposure bin: train frequency 0;
  - positive-frequency tail: ascending frequency, whole frequency groups, include the next
    group iff doing so moves the cumulative count closer to N+/3 than stopping.
Inputs: split CSVs + per-run sidecars (<out>.users.jsonl.gz) + run JSONs. Output: a
markdown verdict block on stdout. Exit 0 = adjudication ran (verdicts are in the text).
"""
import csv
import glob
import gzip
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPLIT = os.path.join(ROOT, "data_5core", "5core", "last_out")

ARMS = {
    ("MI", "text"): range(20260801, 20260809), ("MI", "idonly"): range(20260811, 20260819),
    ("IS", "filter"): range(20260821, 20260829), ("IS", "nofilter"): range(20260831, 20260839),
    ("CDs", "filter"): range(20260861, 20260869), ("CDs", "nofilter"): range(20260871, 20260879),
    ("VG", "text"): range(20260841, 20260849), ("VG", "idonly"): range(20260851, 20260859),
}
CATNAME = {"MI": "Musical_Instruments", "IS": "Industrial_and_Scientific",
           "CDs": "CDs_and_Vinyl", "VG": "Video_Games"}

def t_sf(t, df):
    x = df / (df + t * t)
    a, b = df / 2.0, 0.5
    def betacf(a, b, x):
        MAXIT, EPS, FPMIN = 300, 3e-10, 1e-30
        qab, qap, qam = a + b, a + 1.0, a - 1.0
        c, d = 1.0, 1.0 - qab * x / qap
        if abs(d) < FPMIN: d = FPMIN
        d = 1.0 / d
        h = d
        for m in range(1, MAXIT + 1):
            m2 = 2 * m
            aa = m * (b - m) * x / ((qam + m2) * (a + m2))
            d = 1.0 + aa * d
            if abs(d) < FPMIN: d = FPMIN
            c = 1.0 + aa / c
            if abs(c) < FPMIN: c = FPMIN
            d = 1.0 / d
            h *= d * c
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
            d = 1.0 + aa * d
            if abs(d) < FPMIN: d = FPMIN
            c = 1.0 + aa / c
            if abs(c) < FPMIN: c = FPMIN
            d = 1.0 / d
            de = d * c
            h *= de
            if abs(de - 1.0) < EPS: break
        return h
    def ibeta(a, b, x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
        bt = math.exp(lb)
        if x < (a + 1) / (a + b + 2):
            return bt * betacf(a, b, x) / a
        return 1.0 - bt * betacf(b, a, 1 - x) / b
    return ibeta(a, b, x)

def t_ppf(q, df):
    lo, hi = 0.0, 400.0
    for _ in range(300):
        mid = (lo + hi) / 2
        if 1 - t_sf(mid, df) / 2 < q: lo = mid
        else: hi = mid
    return (lo + hi) / 2

def welch(a, b):
    na, nb = len(a), len(b)
    ma, mb = sum(a) / na, sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    se = math.sqrt(va / na + vb / nb)
    if se == 0:  # degenerate bin (identical per-seed means, e.g. all-zero zero-exposure NDCG)
        return {"diff": ma - mb, "t": float("nan"), "df": float("nan"), "p": float("nan"),
                "lo": ma - mb, "hi": ma - mb, "n": (na, nb), "degenerate": True}
    t = (ma - mb) / se
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    tc = t_ppf(0.975, df)
    return {"diff": ma - mb, "t": t, "df": df, "p": t_sf(abs(t), df),
            "lo": ma - mb - tc * se, "hi": ma - mb + tc * se, "n": (na, nb)}

def freq_index(cat):
    def rows(split):
        with open(os.path.join(SPLIT, f"{cat}.{split}.csv"), encoding="utf-8") as fp:
            rd = csv.reader(fp)
            next(rd)
            return [(r[0], r[1]) for r in rd]
    tr, va, te = rows("train"), rows("valid"), rows("test")
    items = sorted({i for _, i in tr} | {i for _, i in va} | {i for _, i in te})
    idx = {a: k for k, a in enumerate(items)}
    freq = [0] * len(items)
    for _, i in tr:
        freq[idx[i]] += 1
    return freq

def strata(freq):
    n = len(freq)
    zero = {i for i, f in enumerate(freq) if f == 0}
    pos = sorted((f, i) for i, f in enumerate(freq) if f > 0)
    npos = len(pos)
    target = npos / 3.0
    groups = {}
    for f, i in pos:
        groups.setdefault(f, []).append(i)
    tail, cum = set(), 0
    boundary_f = None
    for f in sorted(groups):
        g = groups[f]
        if abs(cum + len(g) - target) < abs(cum - target):
            tail.update(g)
            cum += len(g)
            boundary_f = f
        else:
            break
    tail_excl_boundary = {i for i in tail if freq[i] != boundary_f}
    band16 = {i for i, f in enumerate(freq) if 1 <= f <= 6}
    return zero, tail, tail_excl_boundary, band16, boundary_f

def sidecar_means(short, arm, wanted, metric="ndcg10"):
    out = []
    for s in ARMS[(short, arm)]:
        p = os.path.join(HERE, f"results_TFV2_{short}_{arm}_seed{s}.users.jsonl.gz")
        if not os.path.exists(p):
            return None, f"missing sidecar {os.path.basename(p)}"
        tot, cnt = 0.0, 0
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if r["target_item_id"] in wanted:
                    tot += r[metric]
                    cnt += 1
        out.append(tot / cnt if cnt else 0.0)
    return out, None

def overall_means(short, arm):
    out = []
    for s in ARMS[(short, arm)]:
        p = os.path.join(HERE, f"results_TFV2_{short}_{arm}_seed{s}.json")
        if not os.path.exists(p):
            return None, f"missing {os.path.basename(p)}"
        out.append(json.load(open(p, encoding="utf-8"))["best_test"]["NDCG@10"])
    return out, None

def fmt(w):
    if w.get("degenerate"):
        return (f"diff {w['diff']:+.6f} (degenerate bin: zero between-seed variance in both "
                f"arms; no t/CI)")
    return (f"diff {w['diff']:+.6f}, t={w['t']:.2f}, df={w['df']:.1f}, p={w['p']:.2e}, "
            f"95% CI [{w['lo']:+.6f}, {w['hi']:+.6f}]")

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("## TFV2 adjudication (mechanical; PREREG_TAIL_FIR_V2.md rules)\n")
    verdicts = {}
    # E1: MI positive-frequency tail
    freq = freq_index(CATNAME["MI"])
    zero, tail, tail_xb, band16, bf = strata(freq)
    print(f"MI cohorts: items={len(freq)}, zero-exposure={len(zero)}, "
          f"positive-tail={len(tail)} (boundary freq {bf}), excl-boundary={len(tail_xb)}, "
          f"band[1,6]={len(band16)}")
    at, e = sidecar_means("MI", "text", tail)
    ai, e2 = sidecar_means("MI", "idonly", tail)
    if e or e2:
        print("E1: NOT ADJUDICABLE:", e or e2)
    else:
        w = welch(at, ai)
        verdicts["E1"] = w
        print(f"E1 MI positive-tail NDCG@10 (text-id): {fmt(w)}")
    # E2/E3
    for name, short in (("E2", "IS"), ("E3", "CDs")):
        a, e = overall_means(short, "filter")
        b, e2 = overall_means(short, "nofilter")
        if e or e2:
            print(f"{name}: NOT ADJUDICABLE:", e or e2)
        else:
            w = welch(a, b)
            verdicts[name] = w
            print(f"{name} {short} overall NDCG@10 (filter-nofilter): {fmt(w)}")
    # Holm
    if len(verdicts) == 3:
        order = sorted(verdicts, key=lambda k: verdicts[k]["p"])
        print("\nHolm (alpha 0.05):")
        passed_all = True
        for rank, k in enumerate(order):
            thr = 0.05 / (3 - rank)
            ok = verdicts[k]["p"] <= thr and verdicts[k]["lo"] > 0
            if not ok:
                passed_all = False
            print(f"  {k}: p={verdicts[k]['p']:.2e} vs {thr:.4f}, CI-low "
                  f"{verdicts[k]['lo']:+.6f} -> {'PASS' if ok else 'FAIL'}")
            if verdicts[k]["p"] > thr:
                break
        print(f"\nPRIMARY FAMILY VERDICT: {'ALL PASS' if passed_all and len(order)==3 else 'NOT ALL PASS'}")
    # Secondary (descriptive)
    print("\nSecondary (descriptive; no gates):")
    for label, wanted in (("MI zero-exposure", zero), ("MI tail excl-boundary", tail_xb),
                          ("MI band[1,6]", band16)):
        at2, e = sidecar_means("MI", "text", wanted)
        ai2, e2 = sidecar_means("MI", "idonly", wanted)
        if not (e or e2):
            print(f"  {label}: {fmt(welch(at2, ai2))}")
    at3, e = sidecar_means("MI", "text", tail, metric="hr10")
    ai3, e2 = sidecar_means("MI", "idonly", tail, metric="hr10")
    if not (e or e2):
        print(f"  MI tail HR@10: {fmt(welch(at3, ai3))}")
    vfreq = freq_index(CATNAME["VG"])
    vzero, vtail, vtail_xb, vband, vbf = strata(vfreq)
    vt, e = sidecar_means("VG", "text", vtail)
    vi, e2 = sidecar_means("VG", "idonly", vtail)
    if not (e or e2):
        print(f"  VG positive-tail (boundary freq {vbf}): {fmt(welch(vt, vi))}")
        if len(verdicts) >= 1 and "E1" in verdicts:
            est = (sum(at) / len(at) - sum(ai) / len(ai)) - (sum(vt) / len(vt) - sum(vi) / len(vi))
            comp = []
            for g in (at, ai, vt, vi):
                mg = sum(g) / len(g)
                comp.append(sum((x - mg) ** 2 for x in g) / (len(g) - 1) / len(g))
            varsum = sum(comp)
            dfS = varsum ** 2 / sum(c ** 2 / (8 - 1) for c in comp)
            tS = est / math.sqrt(varsum)
            print(f"  four-arm (MI-VG) tail contrast: est {est:+.6f}, t={tS:.2f}, "
                  f"df={dfS:.1f}, p={t_sf(abs(tS), dfS):.2e}")
    for short in ("IS", "CDs"):
        f2 = freq_index(CATNAME[short])
        _, t2, _, _, _ = strata(f2)
        a, e = sidecar_means(short, "filter", t2)
        b, e2 = sidecar_means(short, "nofilter", t2)
        if not (e or e2):
            print(f"  {short} positive-tail (filter-nofilter): {fmt(welch(a, b))}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
