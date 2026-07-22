#!/usr/bin/env python
"""
build_hstu_tables.py -- enforceable artifact graph for the canonical HSTU/FIR paper
(audit F2 of STRICT_FULL_METHOD_AND_PAPER_AUDIT_2026-07-10; evidence labeling = F6).

Contract
--------
The manifest `_bestrec_run/hstu_results_manifest.json` enumerates every empirical
table-cell family of PAPER_DRAFT.md (Table 1, 1a, 1b-local, 1c, 1d, 1e, the section-5.4.1
arm-ratio table, the section-5.4.2 user-titration table, the section-5.2 pre-declared
V2 confirmation, and Table 2), each with: source result JSONs, a declarative recompute
rule, the recomputed value(s), seed counts, and an evidence_class label
(confirmatory = >=5-seed multi-seed family or pre-declared confirmation;
 exploratory  = single-seed / <5-seed / post-hoc).

Default mode (no flags):
  1. loads the manifest,
  2. RE-COMPUTES every cell from the SOURCE FILES (never from cached values),
  3. regenerates all tables as markdown into `_bestrec_run/hstu_tables.json`,
  4. EXITS NONZERO if
       (a) any source file is missing,
       (b) any recomputed value drifts > 5e-5 from the manifest value,
       (c) any manifest cell has an empty source_files list without being declared
           status UNTRACEABLE (warning), REMOVED_FROM_PAPER (retired; non-blocking,
           non-warning -- kept only as provenance history), or EXTERNAL_PUBLISHED
           (cited constant).
     UNTRACEABLE cells and paper-value MISMATCHes are listed as WARNINGS; the run
     ends "BUILD OK (N warnings)". "BUILD GREEN" is printed ONLY on a zero-warning
     build (strict resubmission audit 2026-07-11, F1).
  5. Additionally compares every recomputed value against the paper-printed value
     (tolerant parse: the paper rounds to 4-6 decimals; delta columns are differences
      of rounded endpoints). In default mode paper mismatches are WARNINGS.

--submission (fail-closed publication gate; audit F1) additionally EXITS NONZERO if
  (d) ANY cell is status UNTRACEABLE,
  (e) ANY paper check is a MISMATCH (recomputed value does not reproduce the
      paper-printed numeral at its printed precision),
  (f) ANY declared paper-claim family (REQUIRED_FAMILIES, incl. the Office_Products
      confirmation family, audit F3) has no sourced cells in the manifest.
  REMOVED_FROM_PAPER and EXTERNAL_PUBLISHED cells are non-blocking in both modes.

--write-manifest regenerates the manifest from the embedded spec (same engine).
--manifest PATH   overrides the manifest path (used to self-test the failure gates).

Run:  _bestrec_run/.venv/Scripts/python _bestrec_run/build_hstu_tables.py
      _bestrec_run/.venv/Scripts/python _bestrec_run/build_hstu_tables.py --submission
Pure stdlib; CPU-only; read-only on every result artifact.
"""
import argparse
import json
import math
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_UP

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BR = "_bestrec_run/"
MANIFEST_PATH = os.path.join(HERE, "hstu_results_manifest.json")
TABLES_PATH = os.path.join(HERE, "hstu_tables.json")
TOL = 5e-5  # manifest drift gate

# ---------------------------------------------------------------- numerics
def rhu(x, nd):
    """round-half-up at nd decimals (paper-style rounding)."""
    q = Decimal(1).scaleb(-nd)
    return float(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))

def mean(xs):
    return sum(xs) / len(xs)

def sstd(xs):
    n = len(xs)
    if n < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))

def _betacf(a, b, x, itmax=300, eps=3e-12):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < 1e-300:
        d = 1e-300
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h

def betainc(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lb = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
          + a * math.log(x) + b * math.log(1.0 - x))
    front = math.exp(lb)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b

def t_sf(t, df):
    """one-sided upper-tail P(T > t)."""
    x = df / (df + t * t)
    p = 0.5 * betainc(df / 2.0, 0.5, x)
    return p if t > 0 else 1.0 - p

def t_two_sided_p(t, df):
    return 2.0 * t_sf(abs(t), df)

def t_ppf(q, df):
    """quantile of Student t via bisection (q in (0.5, 1))."""
    lo, hi = 0.0, 200.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if 1.0 - t_sf(mid, df) < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)

def binom_sf_all(n):
    """one-sided sign-test p for n/n successes at p=0.5."""
    return 0.5 ** n

def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for rank, i in enumerate(order):
            r[i] = rank + 1.0
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = mean(rx), mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den

# ---------------------------------------------------------------- artifact IO
_CACHE = {}
_MISSING = []

def load(rel):
    ap = os.path.join(ROOT, rel)
    if rel in _CACHE:
        return _CACHE[rel]
    if not os.path.exists(ap):
        _MISSING.append(rel)
        raise FileNotFoundError(rel)
    with open(ap, encoding="utf-8") as f:
        j = json.load(f)
    _CACHE[rel] = j
    return j

def bt_metric(rel, metric):
    return float(load(rel)["best_test"][metric])

def pop(rel, stratum, metric, expect_n_eval=None, expect_n=None):
    j = load(rel)
    bt = j["best_test"]
    if expect_n_eval is not None and bt.get("n_eval") != expect_n_eval:
        raise ValueError(f"n_eval drift in {rel}: {bt.get('n_eval')} != {expect_n_eval}")
    s = bt["by_popularity"][stratum]
    if expect_n is not None and s.get("n") != expect_n:
        raise ValueError(f"{stratum} n drift in {rel}: {s.get('n')} != {expect_n}")
    return float(s[metric])

def paired_stats(deltas):
    n = len(deltas)
    m, sd = mean(deltas), sstd(deltas)
    se = sd / math.sqrt(n) if n > 1 else float("nan")
    t = m / se if (n > 1 and se > 0) else float("nan")
    tc = t_ppf(0.975, n - 1) if n > 1 else float("nan")
    return {"mean": m, "sd": sd, "n": n,
            "pos": sum(1 for d in deltas if d > 0),
            "t": t, "ci_lo": m - tc * se, "ci_hi": m + tc * se}

# ---------------------------------------------------------------- rule engine
def rule_mean_std_metric(p):
    xs = [bt_metric(f, p.get("metric", "NDCG@10")) for f in p["files"]]
    if p.get("expect_n_eval") is not None:
        for f in p["files"]:
            ne = load(f)["best_test"].get("n_eval")
            if ne != p["expect_n_eval"]:
                raise ValueError(f"n_eval drift in {f}: {ne}")
    return {"mean": mean(xs), "sd": sstd(xs), "n": len(xs)}

def rule_single_metric(p):
    return {"value": bt_metric(p["file"], p.get("metric", "NDCG@10"))}

def rule_best_val(p):
    return {"value": float(load(p["file"])["best_val_NDCG10"])}

def rule_delta_means(p):
    a = mean([bt_metric(f, p.get("metric", "NDCG@10")) for f in p["a"]])
    b = mean([bt_metric(f, p.get("metric", "NDCG@10")) for f in p["b"]])
    return {"delta": a - b, "a_mean": a, "b_mean": b}

def rule_paired_delta(p):
    m = p.get("metric", "NDCG@10")
    d = [bt_metric(a, m) - bt_metric(b, m) for a, b in zip(p["a"], p["b"])]
    return paired_stats(d)

def rule_pct_of_paired(p):
    """mean paired (a-b) delta as a percent of mean(b)."""
    m = p.get("metric", "NDCG@10")
    d = [bt_metric(a, m) - bt_metric(b, m) for a, b in zip(p["a"], p["b"])]
    bm = mean([bt_metric(b, m) for b in p["b"]])
    return {"pct": 100.0 * mean(d) / bm}

def rule_pct_change(p):
    """percent change of mean(a) vs mean(b) or vs a published constant denom."""
    m = p.get("metric", "NDCG@10")
    a = mean([bt_metric(f, m) for f in p["a"]])
    b = p.get("denom_const") if p.get("denom_const") is not None else \
        mean([bt_metric(f, m) for f in p["b"]])
    return {"pct": 100.0 * (a / b - 1.0), "a_mean": a, "denom": b}

def rule_share_of_lift(p):
    m = p.get("metric", "NDCG@10")
    x = mean([bt_metric(f, m) for f in p["x"]])
    base = mean([bt_metric(f, m) for f in p["base"]])
    top = mean([bt_metric(f, m) for f in p["top"]])
    return {"pct": 100.0 * (x - base) / (top - base),
            "lift": x - base, "combined": top - base}

def rule_pop_paired_delta(p):
    d = [pop(a, p["stratum"], p.get("metric", "NDCG@10"),
             p.get("expect_n_eval"), p.get("expect_n"))
         - pop(b, p["stratum"], p.get("metric", "NDCG@10"),
               p.get("expect_n_eval_b", p.get("expect_n_eval")), p.get("expect_n"))
         for a, b in zip(p["a"], p["b"])]
    return paired_stats(d)

def rule_pop_arm_mean(p):
    xs = [pop(f, p["stratum"], p.get("metric", "NDCG@10"),
              p.get("expect_n_eval"), p.get("expect_n")) for f in p["files"]]
    return {"mean": mean(xs), "sd": sstd(xs), "n": len(xs)}

def rule_pop_ratio(p):
    m = p.get("metric", "NDCG@10")
    a = mean([pop(f, p["stratum"], m) for f in p["a"]])
    b = mean([pop(f, p["stratum"], m) for f in p["b"]])
    return {"ratio": a / b, "a_mean": a, "b_mean": b}

def rule_pop_pct_change(p):
    m = p.get("metric", "NDCG@10")
    a = mean([pop(f, p["stratum"], m) for f in p["a"]])
    b = mean([pop(f, p["stratum"], m) for f in p["b"]])
    return {"pct": 100.0 * (a / b - 1.0)}

def rule_pop_hits_mean(p):
    xs = [pop(f, p["stratum"], "HR@10") *
          load(f)["best_test"]["by_popularity"][p["stratum"]]["n"] for f in p["files"]]
    return {"hits": mean(xs)}

def rule_pop_single(p):
    return {"value": pop(p["file"], p["stratum"], p.get("metric", "NDCG@10"))}

def rule_dd_paired(p):
    m = p.get("metric", "NDCG@10")
    da = [pop(a, p["stratum"], m) - pop(b, p["stratum"], m)
          for a, b in zip(p["a_text"], p["a_id"])]
    db = [pop(a, p["stratum"], m) - pop(b, p["stratum"], m)
          for a, b in zip(p["b_text"], p["b_id"])]
    return paired_stats([x - y for x, y in zip(da, db)])

def rule_welch(p):
    m = p.get("metric", "NDCG@10")
    da = [pop(a, p["stratum"], m) - pop(b, p["stratum"], m)
          for a, b in zip(p["a_text"], p["a_id"])]
    db = [pop(a, p["stratum"], m) - pop(b, p["stratum"], m)
          for a, b in zip(p["b_text"], p["b_id"])]
    ma, mb = mean(da), mean(db)
    va, vb = sstd(da) ** 2 / len(da), sstd(db) ** 2 / len(db)
    t = (ma - mb) / math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(da) - 1) + vb ** 2 / (len(db) - 1))
    return {"diff": ma - mb, "t": t, "df": df, "p": t_two_sided_p(t, df)}

def rule_welch_2arm(p):
    m = p.get("metric", "NDCG@10")
    xa = [pop(f, p["stratum"], m) for f in p["a"]]
    xb = [pop(f, p["stratum"], m) for f in p["b"]]
    ma, mb = mean(xa), mean(xb)
    va, vb = sstd(xa) ** 2 / len(xa), sstd(xb) ** 2 / len(xb)
    se = math.sqrt(va + vb)
    t = (ma - mb) / se
    df = (va + vb) ** 2 / (va ** 2 / (len(xa) - 1) + vb ** 2 / (len(xb) - 1))
    tc95, tc90 = t_ppf(0.975, df), t_ppf(0.95, df)
    return {"diff": ma - mb, "t": t, "df": df, "p": t_two_sided_p(t, df),
            "ci95_lo": ma - mb - tc95 * se, "ci95_hi": ma - mb + tc95 * se,
            "ci90_lo": ma - mb - tc90 * se, "ci90_hi": ma - mb + tc90 * se,
            "n_units": float(min(len(xa), len(xb)))}

def rule_welch_4arm(p):
    m = p.get("metric", "NDCG@10")
    groups = [[pop(f, p["stratum"], m) for f in p[k]]
              for k in ("a_text", "a_id", "b_text", "b_id")]
    signs = (1.0, -1.0, -1.0, 1.0)
    est = sum(sg * mean(g) for sg, g in zip(signs, groups))
    comp = [sstd(g) ** 2 / len(g) for g in groups]
    varsum = sum(comp)
    t = est / math.sqrt(varsum)
    df = varsum ** 2 / sum(v ** 2 / (len(g) - 1) for v, g in zip(comp, groups))
    tc = t_ppf(0.975, df)
    se = math.sqrt(varsum)
    return {"est": est, "t": t, "df": df, "p": t_two_sided_p(t, df),
            "ci_lo": est - tc * se, "ci_hi": est + tc * se,
            "n_units": float(min(len(g) for g in groups))}

def rule_mde_paired(p):
    m = p.get("metric", "NDCG@10")
    d = [pop(a, p["stratum"], m) - pop(b, p["stratum"], m)
         for a, b in zip(p["a"], p["b"])]
    n = len(d)
    se = sstd(d) / math.sqrt(n)
    return {"mde": (t_ppf(0.95, n - 1) + t_ppf(0.80, n - 1)) * se}

def rule_tost_ci90(p):
    m = p.get("metric", "NDCG@10")
    d = [pop(a, p["stratum"], m) - pop(b, p["stratum"], m)
         for a, b in zip(p["a"], p["b"])]
    n = len(d)
    se = sstd(d) / math.sqrt(n)
    tc = t_ppf(0.95, n - 1)
    lo, hi = mean(d) - tc * se, mean(d) + tc * se
    mg = p["margin"]
    return {"lo": lo, "hi": hi, "equivalent": 1.0 if (-mg < lo and hi < mg) else 0.0}

def rule_ci_lower(p):
    m = p.get("metric", "NDCG@10")
    xs = [bt_metric(f, m) for f in p["files"]]
    if p.get("expect_n_eval") is not None:
        for f in p["files"]:
            if load(f)["best_test"].get("n_eval") != p["expect_n_eval"]:
                raise ValueError(f"n_eval drift in {f}")
    n = len(xs)
    se = sstd(xs) / math.sqrt(n)
    return {"mean": mean(xs), "sd": sstd(xs), "n": n,
            "cilb": mean(xs) - t_ppf(0.975, n - 1) * se}

def rule_count_above(p):
    xs = [bt_metric(f, p.get("metric", "NDCG@10")) for f in p["files"]]
    return {"count": float(sum(1 for x in xs if x > p["threshold"])), "n": len(xs)}

def rule_max_pairwise_diff(p):
    m = p.get("metric", "NDCG@10")
    return {"max_abs": max(abs(bt_metric(a, m) - bt_metric(b, m))
                           for a, b in zip(p["a"], p["b"]))}

def rule_dual_gate(p):
    out = {}
    for tag in ("k16", "k8"):
        xs = [bt_metric(f, "NDCG@10") for f in p[tag]]
        se = sstd(xs) / math.sqrt(len(xs))
        out[tag + "_cilb"] = mean(xs) - t_ppf(0.975, len(xs) - 1) * se
    out["pass"] = 1.0 if (out["k16_cilb"] > p["threshold"] and
                          out["k8_cilb"] > p["threshold"]) else 0.0
    return out

def rule_spearman_rungs(p):
    m = p.get("metric", "NDCG@10")
    ds = []
    for tf, idf in p["rungs"]:
        ds.append(mean([pop(a, p["stratum"], m) - pop(b, p["stratum"], m)
                        for a, b in zip(tf, idf)]))
    return {"rho": spearman(ds, p["densities"])}

def rule_json_scalar(p):
    v = load(p["file"]).get(p["key"])
    if v is None:
        raise ValueError(f"key {p['key']} absent in {p['file']}")
    return {"value": float(v)}

def rule_json_path(p):
    o = load(p["file"])
    for k in p["path"]:
        o = o[k]
    return {"value": float(o)}

def rule_log_scan(p):
    vals = []
    for rel in p["files"]:
        ap = os.path.join(ROOT, rel)
        if not os.path.exists(ap):
            _MISSING.append(rel)
            raise FileNotFoundError(rel)
        with open(ap, encoding="utf-8", errors="replace") as f:
            for mt in re.finditer(p["regex"], f.read()):
                vals.append(float(mt.group(1)))
    if not vals:
        raise ValueError(f"regex {p['regex']!r} matched nothing")
    return {"n_units": float(len(vals)),
            "mean": mean(vals), "min": min(vals), "max": max(vals),
            "n": float(len(vals))}

def rule_sign_test(p):
    m = p.get("metric", "NDCG@10")
    d = [pop(a, p["stratum"], m) - pop(b, p["stratum"], m)
         for a, b in zip(p["a"], p["b"])]
    k, n = sum(1 for x in d if x > 0), len(d)
    pv = sum(math.comb(n, i) for i in range(k, n + 1)) * 0.5 ** n
    return {"p": pv, "pos": float(k)}

def rule_const_ratio(p):
    return {"value": p["num"] / p["den"]}

# ---- Office_Products final-epoch FULL-catalog rules (audit F3) --------------
# CRITICAL: the Office headline values come from history[-1].test with
# n_eval == 223,308 (the always-full final-epoch eval), NOT from best_test
# (which is the 30k best-by-val subsample). This mirrors
# _bestrec_run/office_prereg_tools.py::_final_full exactly.
def _final_full_test(rel, expect_n_eval):
    j = load(rel)
    fins = [h for h in j.get("history", []) if "test" in h]
    if not fins:
        raise ValueError(f"no history[*].test entries in {rel}")
    t = fins[-1]["test"]
    if t.get("n_eval") != expect_n_eval:
        raise ValueError(f"final eval not full-catalog in {rel}: "
                         f"n_eval {t.get('n_eval')} != {expect_n_eval}")
    return t

def rule_final_full_ci(p):
    """per-seed final-epoch full-catalog metric + mean/sd/95% CI-LB
    (+ optional count above threshold and percent vs a published constant)."""
    m = p.get("metric", "NDCG@10")
    xs = [float(_final_full_test(f, p["expect_n_eval"])[m]) for f in p["files"]]
    n = len(xs)
    se = sstd(xs) / math.sqrt(n)
    out = {"mean": mean(xs), "sd": sstd(xs), "n": n,
           "cilb": mean(xs) - t_ppf(0.975, n - 1) * se}
    for s, x in zip(p.get("seeds", []), xs):
        out[f"seed{s}"] = x
    if p.get("threshold") is not None:
        out["n_above"] = float(sum(1 for x in xs if x > p["threshold"]))
    if p.get("pct_vs") is not None:
        out["pct_vs_pub"] = 100.0 * (mean(xs) / p["pct_vs"] - 1.0)
    return out

def rule_final_full_count_above(p):
    m = p.get("metric", "NDCG@10")
    xs = [float(_final_full_test(f, p["expect_n_eval"])[m]) for f in p["files"]]
    return {"count": float(sum(1 for x in xs if x > p["threshold"])), "n": len(xs)}

def rule_final_full_tail_hits(p):
    """pooled stratum hit counts (text arm vs id arm) at cutoff K from the
    final-epoch full eval, plus the two-proportion z of
    office_prereg_tools.py::adjudicate."""
    K, stratum = p["k"], p.get("stratum", "tail")
    def pooled(files):
        tot, ns = 0, []
        for f in files:
            bp = _final_full_test(f, p["expect_n_eval"])["by_popularity"][stratum]
            if p.get("expect_n") is not None and bp.get("n") != p["expect_n"]:
                raise ValueError(f"{stratum} n drift in {f}: {bp.get('n')} != {p['expect_n']}")
            tot += bp[f"n_hit@{K}"]
            ns.append(bp["n"])
        return tot, ns
    ht, ns = pooled(p["a"])
    hi, _ = pooled(p["b"])
    N = ns[0] * len(ns)
    # z RETRACTED 2026-07-19 (audit 22:08): the same tail users recur under every seed
    # and both arms, so the N seed-summed rows are clustered repeated observations, not
    # independent Bernoulli trials; no z is computed. Counts stay descriptive; the valid
    # model-seed-level inference lives in the final_full_tail_welch cells.
    return {"text_hits": float(ht), "id_hits": float(hi), "pooled_n": float(N)}

def rule_final_full_single(p):
    """single run's final-epoch FULL-catalog metric (n_eval asserted)."""
    t = _final_full_test(p["file"], p["expect_n_eval"])
    return {"value": float(t[p.get("metric", "NDCG@10")])}

# ---- reference implementation run locally ("theirs on ours", 2026-07-11) ----
def rule_final_full_tail_welch(p):
    K, stratum = p["k"], p.get("stratum", "tail")
    def rates(files):
        out = []
        for f in files:
            bp = _final_full_test(f, p["expect_n_eval"])["by_popularity"][stratum]
            out.append(bp[f"n_hit@{K}"] / bp["n"])
        return out
    a, b = rates(p["a"]), rates(p["b"])
    ma, mb = mean(a), mean(b)
    va, vb = sstd(a) ** 2 / len(a), sstd(b) ** 2 / len(b)
    se = math.sqrt(va + vb)
    t = (ma - mb) / se
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    tc = t_ppf(0.975, df)
    return {"delta": ma - mb, "t": t, "df": df, "p": t_two_sided_p(t, df),
            "ci_lo": ma - mb - tc * se, "ci_hi": ma - mb + tc * se,
            "n_units": float(min(len(a), len(b)))}

def rule_welch_2arm_bt(p):
    m = p.get("metric", "NDCG@10")
    xa = [bt_metric(f, m) for f in p["a"]]
    xb = [bt_metric(f, m) for f in p["b"]]
    ma, mb = mean(xa), mean(xb)
    va, vb = sstd(xa) ** 2 / len(xa), sstd(xb) ** 2 / len(xb)
    se = math.sqrt(va + vb)
    t = (ma - mb) / se
    df = (va + vb) ** 2 / (va ** 2 / (len(xa) - 1) + vb ** 2 / (len(xb) - 1))
    tc = t_ppf(0.975, df)
    return {"diff": ma - mb, "t": t, "df": df, "p": t_two_sided_p(t, df),
            "ci95_lo": ma - mb - tc * se, "ci95_hi": ma - mb + tc * se,
            "n_units": float(min(len(xa), len(xb)))}

def rule_theirs_jsonl(p):
    """metric from a reference-implementation local run's metrics.jsonl (a tee of
    every value their trainer writes to TensorBoard; THEIRS_ON_OURS_REPORT.md).
    Full-corpus eval rows carry prefix eval_epoch_full; reports the final
    (max epoch) and best (max value) readings, plus percent vs a published
    constant when given."""
    ap = os.path.join(ROOT, p["file"])
    if not os.path.exists(ap):
        _MISSING.append(p["file"])
        raise FileNotFoundError(p["file"])
    rows = []
    with open(ap, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("prefix") == p.get("prefix", "eval_epoch_full") and p["metric"] in r:
                rows.append((int(r["batch_id"]), float(r[p["metric"]])))
    if not rows:
        raise ValueError(f"no {p.get('prefix', 'eval_epoch_full')} rows with "
                         f"{p['metric']} in {p['file']}")
    rows.sort()
    out = {"final": rows[-1][1], "final_epoch": float(rows[-1][0])}
    be, bv = max(rows, key=lambda t: t[1])
    out["best"], out["best_epoch"] = bv, float(be)
    if p.get("pct_vs") is not None:
        out["pct_vs_pub"] = 100.0 * (out["final"] / p["pct_vs"] - 1.0)
    return out

RULES = {r[5:]: fn for r, fn in list(globals().items()) if r.startswith("rule_")}

# ---------------------------------------------------------------- file families
def _f(pat, seeds):
    return [BR + pat.format(s=s) for s in seeds]

S0812 = ["20260608", "20260609", "20260610", "20260611", "20260612"]
S0912 = S0812[1:]
S1822 = ["20260618", "20260619", "20260620", "20260621", "20260622"]

J1 = BR + "results_J1_plain_VG.json"
J2 = BR + "results_J2_tapeonly_VG.json"
H2 = BR + "results_H2_reg50_VG.json"
STACK5 = [H2] + _f("results_BEST_VG_seed{s}.json", S0912)
U2F = [BR + "results_U2_ls02_VG.json"] + _f("results_U2_ls02_seed{s}_VG.json", S0912)
V1B = [BR + "results_V1b_causalfilter_k8_VG.json"] + _f("results_V1b_causalfilter_k8_seed{s}_VG.json", S0912)
V25 = [BR + "results_V2_ls02_filter8_VG.json"] + _f("results_V2_ls02_filter8_seed{s}_VG.json", S0912)
V26 = V25 + [BR + "results_V2_confirm_seed20260613_VG.json"]
IDONLY5 = [BR + "results_TAIL_idonly_VG.json"] + _f("results_TAIL_idonly_seed{s}_VG.json", S0912)
TEXT5 = [BR + "results_TAIL_V2_text_VG.json"] + _f("results_TAIL_V2_text_seed{s}_VG.json", S0912)
K16 = _f("results_KSWEEP_k16_seed{s}_VG.json", S0812)
K4 = _f("results_KSWEEP_k4_seed{s}_VG.json", S0812[:3])
K50 = _f("results_KSWEEP_k50_seed{s}_VG.json", S0812[:3])
D5J1 = _f("results_DECOMP5_J1plain_seed{s}_VG.json", S0912)
D5TB = _f("results_DECOMP5_timebias_seed{s}_VG.json", S0912)
D5PR = _f("results_DECOMP5_posrab_seed{s}_VG.json", S0912)
D5TA = _f("results_DECOMP5_tapeonly_seed{s}_VG.json", S0912)
D5TS = _f("results_DECOMP5_textsim_seed{s}_VG.json", S0912)
DEC_TB = BR + "results_DECOMP_timebias_VG.json"
DEC_TS = BR + "results_DECOMP_textsim_VG.json"
MIBASE4 = _f("results_BEST_MI_sbert_e20_seed{s}.json", S0912)
MILS = [BR + "results_MI_lsonly_seed08.json"] + _f("results_MI_lsonly_seed{s}.json", S0912)
MIFO = [BR + "results_MI_filteronly_seed08.json"] + _f("results_MI_filteronly_seed{s}.json", S0912)
MIK16 = _f("results_MI_V2_ls02_filter16_seed{s}.json", S0812)
MIK8 = [BR + "results_MI_V2_ls02_filter8.json"] + _f("results_MI_V2_ls02_filter8_seed{s}.json", S0912)
MISAS = BR + "results_MI_SASREC_baseline.json"
MIT_T = _f("results_MI_TAIL_V2_text_seed{s}.json", S0812)
MIT_I = _f("results_MI_TAIL_idonly_seed{s}.json", S0812)
BT_T = [BR + "results_Beauty_TAIL_V2_text_seed20260608.json",
        BR + "results_Beauty_TAIL_V2_text_strat_seed20260609.json",
        BR + "results_Beauty_TAIL_V2_text_strat_seed20260610.json"]
BT_I = [BR + "results_Beauty_TAIL_idonly_seed20260608.json",
        BR + "results_Beauty_TAIL_idonly_strat_seed20260609.json",
        BR + "results_Beauty_TAIL_idonly_seed20260610.json"]
def TITR(arm, tag):
    return [BR + f"results_TITR_{arm}_rho{tag}_s{s}_VG.json" for s in ("08", "09", "10", "11", "12")]
T066_T = [BR + "results_TITRATE_text_rho066_VG.json"] + \
    [BR + f"results_TITRATE_text_rho066_seed{s}_VG.json" for s in ("09", "10", "11", "12")]
T066_I = [BR + "results_TITRATE_idonly_rho066_VG.json"] + \
    [BR + f"results_TITRATE_idonly_rho066_seed{s}_VG.json" for s in ("09", "10", "11", "12")]
def UT(arm, rho):
    return [BR + f"results_USERTITR_{arm}_rho{rho}_s{s}_VG.json" for s in ("08", "09", "10", "11", "12")]
SC16 = _f("results_SOTACONF_V2_k16_MI_seed{s}.json", S1822)
SC8 = _f("results_SOTACONF_V2_k8_MI_seed{s}.json", S1822)
SC16E1 = _f("results_SOTACONF_V2_k16_MI_seed{s}.EXEC1.json", S1822)
SC8E1 = _f("results_SOTACONF_V2_k8_MI_seed{s}.EXEC1.json", S1822)
RB16 = _f("rebuild_v2/results_SOTACONF_V2_k16_MI_seed{s}.json", S1822)
RB8 = _f("rebuild_v2/results_SOTACONF_V2_k8_MI_seed{s}.json", S1822)
L1 = BR + "results_L1_decaykernel_VG.json"
Q1 = BR + "results_Q1_sampled512dot_VG.json"
O1 = BR + "results_O1_dualtext_VG.json"
N1 = BR + "results_N1_blair_VG.json"
GD1 = BR + "results_GD1_spectralshrink_VG.json"
M1 = BR + "results_M1_experts4_VG.json"
K1D = BR + "results_K1_distill01_VG.json"
S1 = BR + "results_S1_textinit_VG.json"
R1 = BR + "results_R1_ema09_VG.json"
P1 = BR + "results_P1_heads4_VG.json"
T1 = BR + "results_T1_cl4srec_VG.json"
W1 = BR + "results_W1_nicheshare_VG.json"
X1 = BR + "results_X1_jsshrink_VG.json"
Y1 = BR + "results_Y1_heattarget_VG.json"
Z1 = BR + "results_Z1_fitnessgate_VG.json"
CF1VG = BR + "results_CF1_cuefusion_VG.json"
CF1MI = [BR + "results_CF1_cuefusion_MI.json"] + _f("results_CF1_cuefusion_MI_seed{s}.json", S0912)
CONNG = _f("results_CONNGATE_MI_k8_seed{s}.json", S0812)
CONNG_LOGS = [BR + "run_CONNGATE_MI_k8_seed20260608.log", BR + "run_CONNGATE_5seed_driver.log"]
F1S = BR + "results_F1_seq200_VG.json"
D1C = BR + "results_D1_cosfull_VG.json"
D2C = BR + "results_D2_samp512cos_VG.json"
D3C = BR + "results_D3_samp512_VG.json"
ABLTS = BR + "results_ABL_no_textsim_VG.json"
POPF = BR + "results_5core_Video_Games.json"
HBPORT = "_bestrec_sota_lab/runs/hstu_blair_eval_export_full_20260609_fg/hstu_blair_eval_export_summary.json"
TITRLOG066 = BR + "run_TITRATE_idonly_rho066_VG.log"

SOFF = ["20260623", "20260624", "20260625", "20260626", "20260627"]
OFF16 = _f("results_OFFICE_k16_seed{s}.json", SOFF)
OFF8 = _f("results_OFFICE_k8_seed{s}.json", SOFF)
OFFID = _f("results_OFFICE_idonly_seed{s}.json", SOFF)
OFFFLOOR = BR + "results_OFFICE_sasrecfloor_seed20260623.json"

NEVAL_VG, TAILN_VG = 94762, 10900
NEVAL_MI, TAILN_MI = 57439, 8800
TAILN_B = 71522
NEVAL_OFF_FULL, TAILN_OFF = 223308, 36610   # final-epoch FULL-catalog eval geometry
PUB_SASREC_VG = 0.0573      # Liu 2025, published (external constant)
PUB_HSTUBLAIR_MI = 0.0406   # Liu 2025, published (external constant)
PUB_HSTUBLAIR_OFF = 0.0271  # Liu 2025, published Office_Products (external constant)
PUB_SASREC_OFF = 0.0153     # Liu 2025, published Office_Products SASRec (external constant)

# every table family the paper declares; --submission fails if any has no sourced cells
REQUIRED_FAMILIES = ["table1", "table1a", "table1b", "table1c", "table1d", "table1e",
                     "table541", "table542", "tableV2conf", "table2",
                     "office_confirmation", "theirs_on_ours", "fir_breadth", "office_v3", "tfv2"]

OFFICE_VOID_NOTE = ("VOID under prereg floor check (+44% floor inflation); "
                    "provisional, not counted as a pass")

# ---------------------------------------------------------------- spec helpers
def cell(cid, table, row, metric, files, rule, params, paper, n_seeds, ev,
         status="OK", seeds=None, notes="", status_note=None):
    rule_text = {
        "mean_std_metric": "mean/sample-std over seeds of best_test[{m}]",
        "single_metric": "single run best_test[{m}]",
        "best_val": "single run best_val_NDCG10",
        "delta_means": "mean(a) - mean(b) of best_test[{m}]",
        "paired_delta": "mean/sd over seeds of per-seed paired (a-b) best_test[{m}]",
        "pct_of_paired": "100 * mean per-seed (a-b) / mean(b), best_test[{m}]",
        "pct_change": "100 * (mean(a)/denom - 1), best_test[{m}]",
        "share_of_lift": "100 * (mean(x)-mean(base)) / (mean(top)-mean(base))",
        "pop_paired_delta": "mean/sd over seeds of paired (text-id) best_test.by_popularity[stratum][{m}]",
        "pop_arm_mean": "mean over seeds of best_test.by_popularity[stratum][{m}]",
        "pop_ratio": "mean(text arm) / mean(id arm) of by_popularity[stratum][{m}]",
        "pop_pct_change": "100 * (mean(a)/mean(b) - 1) of by_popularity[stratum][{m}]",
        "pop_hits_mean": "mean over seeds of HR@10 * n in by_popularity[stratum]",
        "pop_single": "single run by_popularity[stratum][{m}]",
        "dd_paired": "per-seed ((a_text-a_id) - (b_text-b_id)) on by_popularity[stratum][{m}]; mean/sd/t/CI",
        "welch": "Welch two-sample t on per-seed paired tail deltas (a vs b)",
        "welch_2arm": "independent-arm Welch t/df/p + 90/95% CIs on per-arm by_popularity[stratum][{m}] (a vs b)",
        "welch_4arm": "four-group Welch-Satterthwaite contrast (a_text-a_id)-(b_text-b_id) on by_popularity[stratum][{m}]",
        "mde_paired": "(t_{0.95,n-1}+t_{0.80,n-1}) * sd/sqrt(n) of per-seed paired deltas",
        "tost_ci90": "90% CI of per-seed paired deltas vs equivalence margin",
        "ci_lower": "mean - t_{0.975,n-1} * sd/sqrt(n) of best_test[{m}]",
        "count_above": "count of seeds with best_test[{m}] > threshold",
        "max_pairwise_diff": "max over seeds of |a-b| best_test[{m}]",
        "dual_gate": "95% CI lower bounds of both kernels vs published threshold",
        "spearman_rungs": "Spearman rho of per-rung mean paired delta vs density",
        "json_scalar": "learned scalar read from result JSON",
        "json_path": "value read from JSON at path",
        "log_scan": "scalar(s) parsed from run log(s) by regex",
        "final_full_tail_welch": "independent-arm Welch on per-seed n_hit@K/n tail rates, final-epoch full eval",
        "welch_2arm_bt": "independent-arm Welch t/df/p + 95% CI on per-arm best_test[{m}] (a vs b)",
        "sign_test": "one-sided binomial sign test on per-seed paired deltas",
        "const_ratio": "ratio of quoted run-log constants",
        "final_full_ci": "per-seed history[-1].test[{m}] (final-epoch FULL-catalog eval, "
                         "n_eval asserted; NOT best_test) + mean/sd/95% CI lower bound",
        "final_full_count_above": "count of seeds with history[-1].test[{m}] > threshold "
                                  "(final-epoch full-catalog eval)",
        "final_full_tail_hits": "pooled n_hit@K (text vs id) from "
                                "history[-1].test.by_popularity[stratum] (final-epoch full "
                                "eval) + two-proportion z",
        "final_full_single": "single run history[-1].test[{m}] (final-epoch FULL-catalog "
                             "eval, n_eval asserted)",
        "theirs_jsonl": "reference-implementation local run: final/best full-corpus {m} "
                        "from metrics.jsonl (eval_epoch_full rows)",
    }[rule].replace("{m}", str(params.get("metric", "NDCG@10")))
    d = {
        "cell_id": cid, "table_id": table, "row_label": row, "metric": metric,
        "evidence_class": ev, "status": status,
        "source_files": files, "n_seeds": n_seeds,
        "seeds": seeds or [],
        "recompute": {"rule": rule, "params": params},
        "recompute_rule": rule_text,
        "paper": paper, "notes": notes,
    }
    if status_note is not None:
        d["status_note"] = status_note
    return d

def unt(cid, table, row, metric, paper, notes, status="UNTRACEABLE"):
    """sourceless cell. status UNTRACEABLE = paper still prints it (warning; fatal in
    --submission). status REMOVED_FROM_PAPER = value was deleted from the manuscript
    (2026-07-11 repair); kept only as provenance history -- non-blocking, non-warning
    in BOTH modes."""
    return {
        "cell_id": cid, "table_id": table, "row_label": row, "metric": metric,
        "evidence_class": "exploratory", "status": status,
        "source_files": [], "n_seeds": None, "seeds": [],
        "recompute": None, "recompute_rule": None,
        "paper": paper, "notes": notes,
    }

def ext(cid, table, row, metric, value, notes):
    return {
        "cell_id": cid, "table_id": table, "row_label": row, "metric": metric,
        "evidence_class": "external", "status": "EXTERNAL_PUBLISHED",
        "source_files": [], "n_seeds": None, "seeds": [],
        "recompute": None, "recompute_rule": None,
        "paper": [{"name": "value", "value": value, "mode": "info"}],
        "notes": notes,
    }

def chk(name, value, precision=None, mode="round", tol=None, other=None):
    c = {"name": name, "value": value, "mode": mode}
    if precision is not None:
        c["precision"] = precision
    if tol is not None:
        c["tol"] = tol
    if other:
        c.update(other)
    return c

# ---------------------------------------------------------------- the spec
def build_spec():
    C = []
    conf, expl = "confirmatory", "exploratory"

    # ---------------- Table 1: VG per-component ablation ladder ----------------
    C.append(cell("t1.plain.ndcg", "table1", "HSTU-style encoder, plain", "NDCG@10",
                  [J1], "single_metric", {"file": J1},
                  [chk("value", 0.0588, 4)], 1, expl, seeds=["20260608"]))
    C.append(cell("t1.tape.ndcg", "table1", "+ TAPE-512", "NDCG@10",
                  [J2], "single_metric", {"file": J2},
                  [chk("value", 0.0597, 4)], 1, expl, seeds=["20260608"]))
    C.append(cell("t1.tape.delta", "table1", "+ TAPE-512", "delta NDCG@10 vs plain (single-flag TAPE)",
                  [J2, J1], "delta_means", {"a": [J2], "b": [J1]},
                  [chk("delta", 0.0009, 4)], 1, expl,
                  notes="Also quoted in abstract/S5.1 as TAPE single-flag +0.0009 (n=1)."))
    C.append(cell("t1.bias_stack.ndcg", "table1", "+ full bias stack (TAPE+time+text-sim+pos-rab)",
                  "NDCG@10 mean +- sd", STACK5, "mean_std_metric",
                  {"files": STACK5, "expect_n_eval": NEVAL_VG},
                  [chk("mean", 0.0637, 4), chk("sd", 0.0003, 4)], 5, conf,
                  seeds=S0812,
                  notes="Seed-08 member is results_H2_reg50_VG.json (the 'H2' ls0 stack of "
                        "ANALYSIS_LOG); seeds 09-12 are results_BEST_VG_seed*."))
    C.append(cell("t1.bias_stack.delta", "table1", "+ full bias stack", "delta vs plain",
                  STACK5 + [J1], "delta_means", {"a": STACK5, "b": [J1]},
                  [chk("delta", 0.0049, 4),
                   chk("delta", 0.0049, 4, mode="endpoint",
                       other={"minuend": "t1.bias_stack.ndcg", "mfield": "mean",
                              "subtrahend": "t1.plain.ndcg", "sfield": "value"})],
                  5, expl, notes="n=5 stack vs n=1 plain baseline."))
    C.append(cell("t1.bias_stack.pct", "table1", "+ full bias stack", "percent vs plain",
                  STACK5 + [J1], "pct_change", {"a": STACK5, "b": [J1]},
                  [chk("pct", 8.3, 1),
                   chk("pct", 8.3, 1, mode="endpoint_pct",
                       other={"minuend": "t1.bias_stack.ndcg", "mfield": "mean",
                              "subtrahend": "t1.plain.ndcg", "sfield": "value",
                              "eprec": 4})], 5, expl,
                  notes="Paper corrected 2026-07-11 (was +8.7%): now prints +8.3% = the ratio "
                        "of the rounded endpoints (+0.0049/0.0588). The direct 5-seed "
                        "ratio-of-means is +8.25% (drift-gated in recomputed.pct); the "
                        "endpoint_pct check verifies the printed figure."))
    C.append(cell("t1.ls.ndcg", "table1", "+ label smoothing e=0.2 (U2)", "NDCG@10 mean +- sd",
                  U2F, "mean_std_metric", {"files": U2F, "expect_n_eval": NEVAL_VG},
                  [chk("mean", 0.0649, 4), chk("sd", 0.0003, 4)], 5, conf, seeds=S0812,
                  notes="Paper corrected 2026-07-11 (was 0.0002): recomputed sample-std "
                        "0.00027 rounds half-up to 0.0003, which the paper now prints."))
    C.append(cell("t1.ls.delta", "table1", "+ label smoothing", "delta vs bias stack",
                  U2F + STACK5, "delta_means", {"a": U2F, "b": STACK5},
                  [chk("delta", 0.0012, 4, mode="endpoint",
                       other={"minuend": "t1.ls.ndcg", "mfield": "mean",
                              "subtrahend": "t1.bias_stack.ndcg", "sfield": "mean"}),
                   chk("delta", 0.0013, 4)],
                  5, conf,
                  notes="Table 1 prints +0.0012 (difference of rounded endpoints); the S5.1/Table-0 "
                        "single-flag figure +0.0013 is the direct 5-seed mean difference (0.00128)."))
    C.append(cell("t1.full.ndcg", "table1", "+ causal FIR filter K=8 -> full model (V2)",
                  "NDCG@10 mean +- sd (6-seed)", V26, "mean_std_metric",
                  {"files": V26, "expect_n_eval": NEVAL_VG},
                  [chk("mean", 0.0673, 4), chk("sd", 0.0003, 4)], 6, conf,
                  seeds=S0812 + ["20260613"]))
    C.append(cell("t1.full.delta", "table1", "full model", "delta vs +LS",
                  V26 + U2F, "delta_means", {"a": V26, "b": U2F},
                  [chk("delta", 0.0024, 4)], 6, conf))
    C.append(cell("t1.full.combined", "table1", "full model", "combined delta vs bias stack (prose)",
                  V26 + STACK5, "delta_means", {"a": V26, "b": STACK5},
                  [chk("delta", 0.0036, 4, mode="endpoint",
                       other={"minuend": "t1.full.ndcg", "mfield": "mean",
                              "subtrahend": "t1.bias_stack.ndcg", "sfield": "mean"})],
                  6, conf,
                  notes="Direct 6-seed difference is +0.00368 (rounds to 0.0037); the paper's "
                        "+0.0036 is the difference of rounded endpoints 0.0673-0.0637."))
    C.append(cell("t1.v1b.ndcg", "table1", "(isolation) FIR package arm (filter component; attribution open), no LS (V1b)",
                  "NDCG@10 mean +- sd", V1B, "mean_std_metric",
                  {"files": V1B, "expect_n_eval": NEVAL_VG},
                  [chk("mean", 0.0652, 4), chk("sd", 0.0003, 4)], 5, conf, seeds=S0812,
                  notes="Recomputed mean 0.065150 rounds (half-up) to 0.0652."))
    C.append(cell("t1.v1b.delta", "table1", "(isolation) FIR package arm (filter component; attribution open)", "delta vs bias stack",
                  V1B + STACK5, "delta_means", {"a": V1B, "b": STACK5},
                  [chk("delta", 0.0015, 4)], 5, conf,
                  notes="Also the S5.1 'causal filter alone +0.0015' single-flag figure."))
    C.append(cell("t1.idonly.ndcg", "table1", "(isolation) ID-only (no SBERT/no text-sim/no prototypes)",
                  "NDCG@10 mean +- sd", IDONLY5, "mean_std_metric",
                  {"files": IDONLY5, "expect_n_eval": NEVAL_VG},
                  [chk("mean", 0.0656, 4), chk("sd", 0.0002, 4)], 5, conf, seeds=S0812))
    C.append(cell("t1.text_add.paired", "table1", "text stack minus ID-only (same seeds)",
                  "paired delta NDCG@10 mean +- sd", TEXT5 + IDONLY5, "paired_delta",
                  {"a": TEXT5, "b": IDONLY5},
                  [chk("mean", 0.00178, 5), chk("sd", 0.00021, 5)], 5, conf, seeds=S0812))
    C.append(cell("t1.text_add.pct", "table1", "text stack vs ID-only", "percent overall",
                  TEXT5 + IDONLY5, "pct_of_paired", {"a": TEXT5, "b": IDONLY5},
                  [chk("pct", 2.7, 1)], 5, conf))
    C.append(cell("t1.full_vs_pub.pct", "table1", "full model vs published SASRec 0.0573",
                  "percent (headline +17.5%)", V26, "pct_change",
                  {"a": V26, "denom_const": PUB_SASREC_VG},
                  [chk("pct", 17.5, 1)], 6, conf,
                  notes="Denominator is the published (external) SASRec 0.0573 of Liu 2025. "
                        "Paper corrected 2026-07-11 (was +17.6%, the superseded 5-seed mean): "
                        "the 6-seed mean 0.067337 gives +17.5%, now printed consistently "
                        "(abstract, S2.2, S5.1, S8)."))
    C.append(cell("t1.idonly_vs_pub.pct", "table1", "ID-only vs published SASRec 0.0573",
                  "percent (~ +14%)", IDONLY5, "pct_change",
                  {"a": IDONLY5, "denom_const": PUB_SASREC_VG},
                  [chk("pct", 14.0, 0)], 5, conf))
    C.append(cell("t1.ksweep.k16", "table1", "kernel sweep K=16", "NDCG@10 mean +- sd",
                  K16, "mean_std_metric", {"files": K16, "expect_n_eval": NEVAL_VG},
                  [chk("mean", 0.0676, 4), chk("sd", 0.0002, 4)], 5, conf, seeds=S0812))
    C.append(cell("t1.ksweep.k4", "table1", "kernel sweep K=4", "NDCG@10 mean (robustness)",
                  K4 + U2F, "delta_means", {"a": K4, "b": U2F},
                  [chk("delta", 0.0, mode="gt")], 3, expl,
                  notes="No numeral printed in the paper; supports 'gain robust across "
                        "K in {4,8,16,50}' -- gate: mean(K4) > mean(no-filter U2 stack)."))
    C.append(cell("t1.ksweep.k50", "table1", "kernel sweep K=50", "NDCG@10 mean (robustness)",
                  K50 + U2F, "delta_means", {"a": K50, "b": U2F},
                  [chk("delta", 0.0, mode="gt")], 3, expl,
                  notes="Same robustness gate as K=4; K=8 is the V2 family itself."))
    # single-seed DECOMP attributions quoted inline in S5.1
    C.append(cell("t1.decomp1.timebias", "table1", "DECOMP single-flag: time bias",
                  "delta NDCG@10 (n=1)", [DEC_TB, J1], "delta_means",
                  {"a": [DEC_TB], "b": [J1]},
                  [chk("delta", 0.0027, 4)], 1, expl, seeds=["20260608"]))
    C.append(cell("t1.decomp1.textsim", "table1", "DECOMP single-flag: text-sim bias",
                  "delta NDCG@10 (n=1, dead weight)", [DEC_TS, J1], "delta_means",
                  {"a": [DEC_TS], "b": [J1]},
                  [chk("delta", 0.0001, mode="bound_abs")], 1, expl,
                  notes="Paper states 'dead weight (+-0.0001)'; gate is |delta| <= 0.0001."))
    C.append(cell("t1.decomp5.base", "table1", "DECOMP5 4-seed cross-check: HSTU-style base",
                  "NDCG@10 mean", D5J1, "mean_std_metric", {"files": D5J1},
                  [chk("mean", 0.0594, 4)], 4, expl, seeds=S0912))
    C.append(cell("t1.decomp5.timebias", "table1", "DECOMP5: time bias", "paired delta (4-seed)",
                  D5TB + D5J1, "paired_delta", {"a": D5TB, "b": D5J1},
                  [chk("mean", 0.0030, 4)], 4, expl))
    C.append(cell("t1.decomp5.posrab", "table1", "DECOMP5: pos-rab", "paired delta (4-seed)",
                  D5PR + D5J1, "paired_delta", {"a": D5PR, "b": D5J1},
                  [chk("mean", 0.0012, 4)], 4, expl))
    C.append(cell("t1.decomp5.tape", "table1", "DECOMP5: TAPE", "paired delta (4-seed)",
                  D5TA + D5J1, "paired_delta", {"a": D5TA, "b": D5J1},
                  [chk("mean", 0.0004, 4)], 4, expl))
    C.append(cell("t1.decomp5.textsim", "table1", "DECOMP5: text-sim", "paired delta (4-seed)",
                  D5TS + D5J1, "paired_delta", {"a": D5TS, "b": D5J1},
                  [chk("mean", -0.00005, 5)], 4, expl,
                  notes="Paper corrected 2026-07-11 (was -0.0001): recomputed 4-seed paired "
                        "mean -0.000047 rounds half-up to -0.00005, which S5.1 now prints. "
                        "Table 2's '+-0.0001 (4)' bound form also passes."))

    C.append(cell("t1.pop_ratio", "table1", "headline vs popularity floor (ratio assertion)",
                  "percent above the popularity floor (paper: ~5.4x)",
                  V26 + [POPF], "pct_change", {"a": V26, "denom_const": 0.0125},
                  [chk("pct", 438.7, mode="approx", tol=3.0)], 6, expl,
                  notes="Asserts the S5.1 ratio sentence (corrected 2026-07-19 from the "
                        "wrong 4.1x to ~5.4x = 0.0673/0.0125): exact-value gate for a "
                        "prose ratio (audit 22:08)."))

    # ---------------- Table 1a: protocol-parity baselines ----------------
    C.append(cell("t1a.popularity.ndcg", "table1a", "popularity floor", "NDCG@10",
                  [POPF], "json_path", {"file": POPF, "path": ["methods", "popularity", "NDCG@10"]},
                  [chk("value", 0.0125, 4)], 1, expl,
                  notes="Deterministic popularity scorer, results_5core_Video_Games.json."))
    C.append(cell("t1a.popularity.hr", "table1a", "popularity floor", "HR@10",
                  [POPF], "json_path", {"file": POPF, "path": ["methods", "popularity", "HR@10"]},
                  [chk("value", 0.0248, 4)], 1, expl))
    RM = ("RETIRED 2026-07-11 (strict resubmission audit F1): this v1-era row and every "
          "observation derived from it were REMOVED from PAPER_SUBMISSION.md/PAPER_DRAFT.md "
          "(Table 1a now carries only the traceable popularity floor plus a removal note). "
          "Cell kept solely as provenance history; non-blocking and non-warning. ")
    C.append(unt("t1a.sasrec_notext", "table1a", "SASRec (no text features, 5-seed)",
                 "NDCG@10 0.0510 +- 0.0006 / HR 0.0923 +- 0.0009 / MRR 0.0460 +- 0.0006 "
                 "(v1-era print, no longer in the paper)",
                 [chk("mean", 0.0510, 4, mode="info")],
                 RM + "No 5-seed VG no-text plain-SASRec family exists on disk; nearest artifact "
                 "is the MI SASRec baseline (different category). The v1-era VG scan files were "
                 "overwritten/not retained.", status="REMOVED_FROM_PAPER"))
    C.append(unt("t1a.sasrec_sbert", "table1a", "SASRec-SBERT (MiniLM, 5-seed) parity baseline",
                 "NDCG@10 0.0551 +- 0.0003 / HR 0.0998 +- 0.0009 / MRR 0.0496 +- 0.0003 "
                 "(v1-era print, no longer in the paper)",
                 [chk("mean", 0.0551, 4, mode="info")],
                 RM + "KNOWN untraceable number (also flagged by the prior audits and quoted in "
                 "SOTA_VERDICT.md). On-disk candidates do not reproduce it: "
                 "results_sasrec_sbert_VG_tuned_* (5 seeds) -> 0.0562 +- 0.0004; "
                 "results_sasrec_sbert_Video_Games_v3.json -> 0.0543; "
                 "seed20260522/23 -> 0.0498/0.0500. The 0.0551 5-seed family predates the "
                 "retained artifact set. Residue resolved 2026-07-11: the S2.2 contributions "
                 "parenthetical now states the number was RETIRED from Table 1a (not "
                 "'retained'), and the 'relative to HSTU-BLaIR' bullet no longer claims the "
                 "3-method encoder ablation -- both papers updated.",
                 status="REMOVED_FROM_PAPER"))
    C.append(unt("t1a.sasrec_blair", "table1a", "SASRec-BLaIR (5-seed)",
                 "NDCG@10 0.0545 +- 0.0007 / HR 0.0986 +- 0.0011 / MRR 0.0492 +- 0.0006 "
                 "(v1-era print, no longer in the paper)",
                 [chk("mean", 0.0545, 4, mode="info")],
                 RM + "Only a single-seed results_sasrec_blair_Video_Games.json (0.0498) exists "
                 "on disk; no 5-seed family reproduces 0.0545.",
                 status="REMOVED_FROM_PAPER"))

    # ---------------- Table 1b: comparator evidence (local rows only) ----------------
    C.append(cell("t1b.port.final_ndcg", "table1b",
                  "HSTU-BLaIR local SM120 compatibility port (final full eval)", "NDCG@10",
                  [HBPORT], "json_path", {"file": HBPORT, "path": ["metrics", "NDCG@10"]},
                  [chk("value", 0.07382, 5)], 1, expl,
                  notes="Single-run WSL/SM120 compatibility port export; validity caveats in S5.1."))
    C.append(cell("t1b.port.final_hr", "table1b", "HSTU-BLaIR local port (final full eval)", "HR@10",
                  [HBPORT], "json_path", {"file": HBPORT, "path": ["metrics", "HR@10"]},
                  [chk("value", 0.13234, 5)], 1, expl))
    C.append(unt("t1b.port.best_ndcg", "table1b", "HSTU-BLaIR local port (best full eval)",
                 "NDCG@10 0.07403 (v1-era print, no longer in the paper)",
                 [chk("value", 0.07403, 5, mode="info")],
                 "RETIRED 2026-07-11 (strict resubmission audit F1): the best-epoch 0.07403 "
                 "was REMOVED from both manuscripts -- Table 1b now prints only the exported "
                 "final full-eval 0.07382 and states that the higher best-epoch reading "
                 "'survives only in an unretained WSL log and is excluded from the artifact "
                 "graph'. The value is not present in the exported summary artifacts; it came "
                 "from the WSL-side training log which was not retained in the repo. Cell kept "
                 "solely as provenance history; non-blocking and non-warning.",
                 status="REMOVED_FROM_PAPER"))
    C.append(ext("t1b.pub.sasrec", "table1b", "SASRec (Liu 2025, published)", "NDCG@10",
                 PUB_SASREC_VG, "Published single-seed comparator; not a local artifact."))
    C.append(ext("t1b.pub.hstublair_vg", "table1b", "HSTU-BLaIR VG (Liu 2025, published)",
                 "NDCG@10", 0.0760, "Published comparator; hardware-blocked locally."))
    C.append(ext("t1b.pub.hstublair_mi", "table1b", "HSTU-BLaIR MI (Liu 2025, published)",
                 "NDCG@10", PUB_HSTUBLAIR_MI,
                 "Published per-category point estimate targeted by the pre-declared V2 confirmation."))

    # ---------------- Table 1c: MI per-lever isolation ----------------
    C.append(cell("t1c.base.ndcg", "table1c", "MI SBERT+TAPE base (4 x e20 seeds)", "NDCG@10 mean +- sd",
                  MIBASE4, "mean_std_metric", {"files": MIBASE4, "expect_n_eval": NEVAL_MI},
                  [chk("mean", 0.0383, 4), chk("sd", 0.0004, 4)], 4, expl, seeds=S0912,
                  notes="4-seed family (paper discloses the seed-08 e15 checkpoint was excluded); "
                        "labeled exploratory per the n>=5 confirmatory rule."))
    C.append(cell("t1c.lsonly.ndcg", "table1c", "+ label smoothing only", "NDCG@10 mean +- sd",
                  MILS, "mean_std_metric", {"files": MILS, "expect_n_eval": NEVAL_MI},
                  [chk("mean", 0.0391, 4), chk("mean", 0.03914, 5), chk("sd", 0.00013, 5)],
                  5, conf, seeds=S0812,
                  notes="Paper quotes both 0.0391 +- 0.0001 (table) and 0.03914 +- 0.00013 (prose)."))
    C.append(cell("t1c.lsonly.delta", "table1c", "+ LS only", "delta vs base",
                  MILS + MIBASE4, "delta_means", {"a": MILS, "b": MIBASE4},
                  [chk("delta", 0.0008, 4)], 5, conf))
    C.append(cell("t1c.lsonly.share", "table1c", "+ LS only", "share of combined k16 lift",
                  MILS + MIBASE4 + MIK16, "share_of_lift",
                  {"x": MILS, "base": MIBASE4, "top": MIK16},
                  [chk("pct", 26.0, 0)], 5, conf))
    C.append(cell("t1c.filteronly.ndcg", "table1c", "+ FIR package arm (filter component; attribution open) (k16)", "NDCG@10 mean",
                  MIFO, "mean_std_metric", {"files": MIFO, "expect_n_eval": NEVAL_MI},
                  [chk("mean", 0.0408, 4)], 5, conf, seeds=S0812))
    C.append(cell("t1c.filteronly.delta", "table1c", "+ filter only", "delta vs base",
                  MIFO + MIBASE4, "delta_means", {"a": MIFO, "b": MIBASE4},
                  [chk("delta", 0.0025, 4)], 5, conf))
    C.append(cell("t1c.filteronly.share", "table1c", "+ filter only", "share of combined k16 lift",
                  MIFO + MIBASE4 + MIK16, "share_of_lift",
                  {"x": MIFO, "base": MIBASE4, "top": MIK16},
                  [chk("pct", 77.0, 0)], 5, conf))
    C.append(cell("t1c.v2k16.ndcg", "table1c", "+ both = V2 (k16)", "NDCG@10 mean +- sd",
                  MIK16, "mean_std_metric", {"files": MIK16, "expect_n_eval": NEVAL_MI},
                  [chk("mean", 0.0415, 4), chk("sd", 0.0002, 4)], 5, conf, seeds=S0812))
    C.append(cell("t1c.v2k16.delta", "table1c", "+ both = V2 (k16)", "delta vs base",
                  MIK16 + MIBASE4, "delta_means", {"a": MIK16, "b": MIBASE4},
                  [chk("delta", 0.0032, 4)], 5, conf))
    C.append(cell("t1c.v2k8.ndcg", "table1c", "V2 k8 (MI headline stack)", "NDCG@10 mean +- sd",
                  MIK8, "mean_std_metric", {"files": MIK8, "expect_n_eval": NEVAL_MI},
                  [chk("mean", 0.0413, 4), chk("sd", 0.0005, 4)], 5, conf, seeds=S0812))
    C.append(cell("t1c.v2k8.share", "table1c", "filter share of k8 combined lift", "percent",
                  MIFO + MIBASE4 + MIK8, "share_of_lift",
                  {"x": MIFO, "base": MIBASE4, "top": MIK8},
                  [chk("pct", 82.0, 0)], 5, conf,
                  notes="Paper: '82% vs the k8 headline stack'; ~80% claims use tol 5pp."))
    C.append(cell("t1c.v2k8.pct_base", "table1c", "V2 k8 vs MI base", "percent (+7.9%)",
                  MIK8 + MIBASE4, "pct_change", {"a": MIK8, "b": MIBASE4},
                  [chk("pct", 7.9, 1)], 5, conf))
    C.append(cell("t1c.sasrec_floor.ndcg", "table1c", "plain ID-only SASRec (MI)", "NDCG@10",
                  [MISAS], "single_metric", {"file": MISAS},
                  [chk("value", 0.0264, 4)], 1, expl, seeds=["20260608"]))
    C.append(cell("t1c.v2k8.pct_sasrec", "table1c", "V2 k8 vs plain SASRec (MI)", "percent (+57%)",
                  MIK8 + [MISAS], "pct_change", {"a": MIK8, "b": [MISAS]},
                  [chk("pct", 57.0, 0)], 5, conf))

    # ---------------- Table 1d: text-vs-ID tail contrast ----------------
    C.append(cell("t1d.mi.tail", "table1d", "Musical_Instruments (sparse)",
                  "tail delta NDCG@10 (same-seed-number, 5-seed; descriptive)",
                  MIT_T + MIT_I, "pop_paired_delta",
                  {"a": MIT_T, "b": MIT_I, "stratum": "tail",
                   "expect_n_eval": NEVAL_MI, "expect_n": TAILN_MI},
                  [chk("mean", 0.000335, 6), chk("sd", 0.000195, 6),
                   chk("pos", 5, mode="count")],
                  5, conf, seeds=S0812,
                  notes="Arms are NOT initialization-paired (S5.3 randomization disclosure, "
                        "2026-07-19); the same-seed-number delta stats are descriptive and "
                        "the inferential CI now comes from t1d.mi.welch."))
    C.append(cell("t1d.mi.welch", "table1d", "MI tail: independent-arm Welch",
                  "Welch t/p + 95% CI (text vs id per-arm tail values)",
                  MIT_T + MIT_I, "welch_2arm",
                  {"a": MIT_T, "b": MIT_I, "stratum": "tail"},
                  [chk("diff", 0.000335, 6), chk("t", 3.94, 2),
                   chk("p", 0.014, mode="approx", tol=0.002),
                   chk("ci95_lo", 0.000109, 6), chk("ci95_hi", 0.000562, 6),
                   chk("ci95_lo", 0.0, mode="gt")],
                  5, conf, seeds=S0812,
                  notes="The conservative independent-arm analysis of the MI tail win "
                        "(added 2026-07-19 with the pairing retraction)."))
    C.append(cell("t1d.vg.welch", "table1d", "VG tail: independent-arm Welch",
                  "Welch p + 90% CI (equivalence NOT established at the retracted margin)",
                  TEXT5 + IDONLY5, "welch_2arm",
                  {"a": TEXT5, "b": IDONLY5, "stratum": "tail"},
                  [chk("diff", -0.000148, 6),
                   chk("p", 0.22, mode="approx", tol=0.02),
                   chk("ci90_lo", -0.000360, 6), chk("ci90_hi", 0.000063, 6)],
                  5, conf, seeds=S0812,
                  notes="90% CI [-0.000360,+0.000063] is NOT contained in the retracted "
                        "data-derived margin +-0.000335 -> no equivalence claim survives "
                        "(2026-07-19 retraction, S5.3)."))
    C.append(cell("t1d.vg.tail", "table1d", "Video_Games (dense)",
                  "tail delta NDCG@10 (same-seed-number, 5-seed; descriptive)",
                  TEXT5 + IDONLY5, "pop_paired_delta",
                  {"a": TEXT5, "b": IDONLY5, "stratum": "tail",
                   "expect_n_eval": NEVAL_VG, "expect_n": TAILN_VG},
                  [chk("mean", -0.000148, 6), chk("sd", 0.000179, 6),
                   chk("pos", 2, mode="count")], 5, conf, seeds=S0812))
    C.append(cell("t1d.beauty.tail", "table1d", "Beauty_and_PC (dense)",
                  "tail delta NDCG@10 (same-seed-number, 3-seed; exploratory)",
                  BT_T + BT_I, "pop_paired_delta",
                  {"a": BT_T, "b": BT_I, "stratum": "tail", "expect_n": TAILN_B},
                  [chk("mean", -0.0000078, 7), chk("sd", 0.000020, 6),
                   chk("pos", 1, mode="count")], 3, expl, seeds=["20260608", "20260609", "20260610"],
                  notes="Heterogeneous eval geometry disclosed: seed08 pair is full-eval "
                        "(n_eval=729,576) both arms; seed09 pair is stratified-eval (212,245) both "
                        "arms; seed10 pairs a stratified TEXT run against a full-eval ID run. The "
                        "tail bucket (n=71,522) is identical across all six files, so the tail "
                        "contrast is bucket-consistent, but the seed10 pair is not user-set-matched. "
                        "Never equivalence-tested (no MDE/TOST nodes); exploratory only (S5.3)."))
    C.append(cell("t1d.mi.tail_hr", "table1d", "MI tail replication on HR@10",
                  "tail delta HR@10 (same-seed-number, 5-seed)", MIT_T + MIT_I, "pop_paired_delta",
                  {"a": MIT_T, "b": MIT_I, "stratum": "tail", "metric": "HR@10",
                   "expect_n_eval": NEVAL_MI, "expect_n": TAILN_MI},
                  [chk("mean", 0.00109, 5), chk("sd", 0.00065, 5), chk("pos", 5, mode="count")],
                  5, conf))
    C.append(cell("t1d.mi.tail_hits_text", "table1d", "MI tail hits/seed (text arm)", "HR@10 x n",
                  MIT_T, "pop_hits_mean", {"files": MIT_T, "stratum": "tail"},
                  [chk("hits", 29.6, 1, mode="approx", tol=0.5)], 5, conf,
                  notes="Paper: '~29.6 vs 20.0 hits/seed'."))
    C.append(cell("t1d.mi.tail_hits_id", "table1d", "MI tail hits/seed (ID arm)", "HR@10 x n",
                  MIT_I, "pop_hits_mean", {"files": MIT_I, "stratum": "tail"},
                  [chk("hits", 20.0, 1, mode="approx", tol=0.5)], 5, conf))
    C.append(cell("t1d.mi.head_abs", "table1d", "MI head delta (largest absolute text lift)",
                  "head delta NDCG@10", MIT_T + MIT_I, "pop_paired_delta",
                  {"a": MIT_T, "b": MIT_I, "stratum": "head",
                   "expect_n_eval": NEVAL_MI},
                  [chk("mean", 0.00527, 5)], 5, conf))
    C.append(cell("t1d.welch", "table1d", "cross-dataset difference MI - VG",
                  "four-arm Welch-Satterthwaite contrast (independence-style; corrected 2026-07-19)",
                  MIT_T + MIT_I + TEXT5 + IDONLY5, "welch_4arm",
                  {"a_text": MIT_T, "a_id": MIT_I, "b_text": TEXT5, "b_id": IDONLY5,
                   "stratum": "tail"},
                  [chk("est", 0.000484, 6), chk("t", 3.51, 2),
                   chk("p", 0.0054, mode="approx", tol=0.001)], 5, conf,
                  notes="Replaces the per-seed-delta Welch (t=4.09) whose units were the "
                        "invalidly-paired same-seed differences (2026-07-19 correction)."))
    C.append(unt("t1d.vg.mde", "table1d", "VG powered-null MDE (RETIRED)",
                 "MDE 0.000246 (retired print, no longer in the paper)", [],
                 "RETRACTED 2026-07-19 (audits 18:53 CP-1 / 19:56 P1): the paired-design MDE "
                 "assumed initialization-paired arms (false; S5.3 disclosure) and backed the "
                 "withdrawn powered-null claim. TOMBSTONE: no recomputation.",
                 status="REMOVED_FROM_PAPER"))
    C.append(unt("t1d.vg.tost", "table1d", "VG TOST equivalence vs MI margin (RETIRED)",
                 "90% CI [-0.000319,+0.000023] vs margin +-0.000335 (retired print)", [],
                 "RETRACTED 2026-07-19: paired TOST with a data-derived margin (= the observed "
                 "MI point estimate); the independent-arm 90% CI [-0.000360,+0.000063] is not "
                 "contained in that margin (t1d.vg.welch). TOMBSTONE: no recomputation.",
                 status="REMOVED_FROM_PAPER"))

    # ---------------- Table 1e: interaction-thinning titration ladder ----------------
    RUNGS = [
        ("100", 1.00, TEXT5, IDONLY5, 24.405,
         (0.002213, 0.000241, 5), (0.004238, 0.000765, 5),
         (-0.000148, 0.000179, 2), (0.000128, 0.000582, 3)),
        ("094", 0.94, TITR("text", "094"), TITR("idonly", "094"), 22.947,
         (0.002389, 0.000267, 5), (0.004083, 0.000830, 5),
         (0.000165, 0.000370, 4), (0.000807, 0.000712, 5)),
        ("091", 0.91, TITR("text", "091"), TITR("idonly", "091"), 22.210,
         (0.002544, 0.000491, 5), (0.004940, 0.000892, 5),
         (0.000039, 0.000310, 3), (0.000110, 0.000766, 3)),
        ("088", 0.88, TITR("text", "088"), TITR("idonly", "088"), 21.484,
         (0.002520, 0.000421, 5), (0.004869, 0.000765, 5),
         (0.000537, 0.000386, 4), (0.000661, 0.000995, 4)),
        ("078", 0.78, TITR("text", "078"), TITR("idonly", "078"), 19.030,
         (0.002664, 0.000398, 5), (0.004467, 0.001082, 5),
         (0.000056, 0.000552, 2), (0.000239, 0.001087, 2)),
        ("066", 0.66, T066_T, T066_I, 16.109,
         (0.003540, 0.000416, 5), (0.005720, 0.000904, 5),
         (-0.000108, 0.000503, 1), (0.000073, 0.001165, 3)),
    ]
    for tag, rho, tf, idf, ipi, hn, hh, tn, th in RUNGS:
        for stratum, metric, (pm, ps, pp) in (
                ("head", "NDCG@10", hn), ("head", "HR@10", hh),
                ("tail", "NDCG@10", tn), ("tail", "HR@10", th)):
            mkey = "ndcg" if metric == "NDCG@10" else "hr"
            C.append(cell(f"t1e.rho{tag}.{stratum}_{mkey}", "table1e",
                          f"rho={rho:.2f} (kept inter./item {ipi}, run-log value)",
                          f"{stratum} delta {metric} (paired, 5-seed)",
                          tf + idf, "pop_paired_delta",
                          {"a": tf, "b": idf, "stratum": stratum, "metric": metric,
                           "expect_n_eval": NEVAL_VG,
                           "expect_n": TAILN_VG if stratum == "tail" else None},
                          [chk("mean", pm, 6), chk("sd", ps, 6), chk("pos", pp, mode="count")],
                          5, conf, seeds=S0812,
                          notes="kept-interactions/item is quoted from the frozen run logs "
                                "(see make_table_5_4_titration.py)."))
    C.append(unt("t1e.alpha066", "table1e", "alpha(rho=0.66) = ipi/d_eff (RETIRED)",
                 "ratio 0.700 (retired print, no longer in the paper)", [],
                 "RETRACTED 2026-07-19 (audits 14:53/15:51/17:56 CP-2): the d_eff=23 "
                 "denominator came from the withdrawn spectral analysis (intervention-"
                 "enforced rank; 23 matches no released artifact). TOMBSTONE: the retired "
                 "quantity is no longer recomputed anywhere in the graph; provenance "
                 "history only.", status="REMOVED_FROM_PAPER"))
    RUNG_FILES = [(r[2], r[3]) for r in RUNGS]
    DENS = [r[1] for r in RUNGS]
    C.append(cell("t1e.spearman.head_ndcg", "table1e", "Spearman rho_s(head delta vs density)",
                  "NDCG@10", sum([a + b for a, b in RUNG_FILES], []), "spearman_rungs",
                  {"rungs": RUNG_FILES, "densities": DENS, "stratum": "head"},
                  [chk("rho", -0.94, 2)], 5, conf))
    C.append(cell("t1e.spearman.head_hr", "table1e", "Spearman rho_s(head delta vs density)",
                  "HR@10", sum([a + b for a, b in RUNG_FILES], []), "spearman_rungs",
                  {"rungs": RUNG_FILES, "densities": DENS, "stratum": "head", "metric": "HR@10"},
                  [chk("rho", -0.71, 2)], 5, conf))
    C.append(cell("t1e.spearman.tail_ndcg", "table1e", "Spearman rho_s(tail delta vs density)",
                  "NDCG@10", sum([a + b for a, b in RUNG_FILES], []), "spearman_rungs",
                  {"rungs": RUNG_FILES, "densities": DENS, "stratum": "tail"},
                  [chk("rho", -0.14, 2)], 5, conf))

    # ---------------- S5.4.1 arm-ratio table ----------------
    ARM = [("vgfull", "VG full density", TEXT5, IDONLY5,
            0.004919, 0.005068, 0.971, 1.026),
           ("rho066", "VG thinned -> MI-density (rho=0.66)", T066_T, T066_I,
            0.003569, 0.003677, 0.971, 1.049),
           ("mi", "MI native", MIT_T, MIT_I,
            0.001551, 0.001216, 1.276, 1.101)]
    for key, row, tf, idf, ptt, pti, ptr, phr in ARM:
        C.append(cell(f"t541.{key}.tail_text", "table541", row, "tail text-arm NDCG@10 mean",
                      tf, "pop_arm_mean", {"files": tf, "stratum": "tail"},
                      [chk("mean", ptt, 6)], 5, conf))
        C.append(cell(f"t541.{key}.tail_id", "table541", row, "tail ID-arm NDCG@10 mean",
                      idf, "pop_arm_mean", {"files": idf, "stratum": "tail"},
                      [chk("mean", pti, 6)], 5, conf))
        C.append(cell(f"t541.{key}.tail_ratio", "table541", row, "tail text/ID ratio",
                      tf + idf, "pop_ratio", {"a": tf, "b": idf, "stratum": "tail"},
                      [chk("ratio", ptr, 3)], 5, conf))
        C.append(cell(f"t541.{key}.head_ratio", "table541", row, "head text/ID ratio",
                      tf + idf, "pop_ratio", {"a": tf, "b": idf, "stratum": "head"},
                      [chk("ratio", phr, 3)], 5, conf))
    C.append(cell("t541.starve.text_pct", "table541", "text-arm tail starvation full->rho0.66",
                  "percent", T066_T + TEXT5, "pop_pct_change",
                  {"a": T066_T, "b": TEXT5, "stratum": "tail"},
                  [chk("pct", -27.4, 1)], 5, conf))
    C.append(cell("t541.starve.id_pct", "table541", "ID-arm tail starvation full->rho0.66",
                  "percent", T066_I + IDONLY5, "pop_pct_change",
                  {"a": T066_I, "b": IDONLY5, "stratum": "tail"},
                  [chk("pct", -27.4, 1)], 5, conf))
    C.append(cell("t541.mi.tail_rel", "table541", "MI tail relative text gain", "percent (+27.6%)",
                  MIT_T + MIT_I, "pop_pct_change",
                  {"a": MIT_T, "b": MIT_I, "stratum": "tail"},
                  [chk("pct", 27.6, 1)], 5, conf))

    # ---------------- S5.4.2 user-mode titration ----------------
    UT66T, UT66I = UT("text", "066"), UT("idonly", "066")
    UT50T, UT50I = UT("text", "050"), UT("idonly", "050")
    UT40T, UT40I = UT("text", "040"), UT("idonly", "040")
    C.append(cell("t542.u066.tail", "table542", "VG user-thinned rho_user=0.66 (users/item 2.44)",
                  "within-rung tail delta NDCG@10", UT66T + UT66I, "pop_paired_delta",
                  {"a": UT66T, "b": UT66I, "stratum": "tail",
                   "expect_n_eval": NEVAL_VG, "expect_n": TAILN_VG},
                  [chk("mean", 0.000178, 6), chk("sd", 0.000153, 6),
                   chk("pos", 5, mode="count")],
                  5, conf, seeds=S0812,
                  notes="users/item 2.44 and interactions/item 16.12 are run-log quantities. "
                        "Paper sd corrected 2026-07-11 (was 0.000137): recomputed sample-std "
                        "0.0001535 rounds to 0.000153, now printed in the S5.4.2 table."))
    C.append(cell("t542.u066.welch", "table542", "user-thinned rho=0.66: independent-arm Welch",
                  "Welch t/p + 95% CI on per-arm tail values (within-rung; corrected 2026-07-19)",
                  UT66T + UT66I, "welch_2arm",
                  {"a": UT66T, "b": UT66I, "stratum": "tail"},
                  [chk("diff", 0.000178, 6), chk("t", 1.58, 2),
                   chk("p", 0.164, mode="approx", tol=0.01),
                   chk("ci95_lo", -0.000095, 6), chk("ci95_hi", 0.000451, 6)],
                  5, conf, seeds=S0812,
                  notes="CI includes zero: the within-rung effect is sign-consistent but not "
                        "significant under the corrected independent-arm analysis."))
    C.append(cell("t542.u066.tail_ratio", "table542", "user-thinned rho=0.66", "tail text/ID ratio",
                  UT66T + UT66I, "pop_ratio", {"a": UT66T, "b": UT66I, "stratum": "tail"},
                  [chk("ratio", 1.046, 3)], 5, conf))
    C.append(cell("t542.u066.head_ratio", "table542", "user-thinned rho=0.66", "head text/ID ratio",
                  UT66T + UT66I, "pop_ratio", {"a": UT66T, "b": UT66I, "stratum": "head"},
                  [chk("ratio", 1.039, 3)], 5, conf))
    C.append(cell("t542.u066.dd_vs_full", "table542", "dd vs full-density anchor",
                  "same-seed diff-of-deltas (tail NDCG@10; descriptive)",
                  UT66T + UT66I + TEXT5 + IDONLY5, "dd_paired",
                  {"a_text": UT66T, "a_id": UT66I, "b_text": TEXT5, "b_id": IDONLY5,
                   "stratum": "tail"},
                  [chk("mean", 0.000326, 6), chk("sd", 0.000210, 6),
                   chk("pos", 5, mode="count")],
                  5, conf,
                  notes="Descriptive only (2026-07-19): the former paired t=3.47 / "
                        "CI-excludes-0 inference is retracted with the pairing assumption; "
                        "the valid inference is t542.u066.dd_welch (p=0.058, CI includes 0)."))
    C.append(cell("t542.u066.dd_welch", "table542", "dd vs full anchor: four-group Welch",
                  "Welch-Satterthwaite contrast (user066_text-user066_id)-(full_text-full_id)",
                  UT66T + UT66I + TEXT5 + IDONLY5, "welch_4arm",
                  {"a_text": UT66T, "a_id": UT66I, "b_text": TEXT5, "b_id": IDONLY5,
                   "stratum": "tail"},
                  [chk("est", 0.000326, 6), chk("t", 2.09, 2),
                   chk("p", 0.058, mode="approx", tol=0.005),
                   chk("ci_lo", -0.000014, 6), chk("ci_hi", 0.000666, 6)],
                  5, conf,
                  notes="NOT significant (p=0.058; CI includes zero): the S5.4.2 finding is "
                        "downgraded to suggestive/descriptive (2026-07-19)."))
    C.append(unt("t542.u066.signtest", "table542", "dd sign test (RETIRED)",
                 "one-sided p = 0.031 (retired print, no longer in the paper)", [],
                 "RETRACTED 2026-07-19: the sign test treated per-seed dd values as "
                 "exchangeable paired blocks; the arms are not initialization-paired "
                 "(S5.3). The 5/5 sign count remains reported descriptively in "
                 "t542.u066.dd_vs_full. TOMBSTONE: no recomputation.",
                 status="REMOVED_FROM_PAPER"))
    C.append(cell("t542.matchedR1.tail", "table542", "matched-R1: (user - interaction) at rho=0.66",
                  "tail delta difference (descriptive level contrast)", UT66T + UT66I + T066_T + T066_I, "dd_paired",
                  {"a_text": UT66T, "a_id": UT66I, "b_text": T066_T, "b_id": T066_I,
                   "stratum": "tail"},
                  [chk("mean", 0.000286, 6)], 5, conf))
    C.append(cell("t542.matchedR1.head", "table542", "matched-R1: (user - interaction) at rho=0.66",
                  "head delta difference (descriptive level contrast)", UT66T + UT66I + T066_T + T066_I, "dd_paired",
                  {"a_text": UT66T, "a_id": UT66I, "b_text": T066_T, "b_id": T066_I,
                   "stratum": "head"},
                  [chk("mean", -0.000475, 6)], 5, conf,
                  notes="diff-of-diffs tail-head = +0.000761 with opposite signs (see both cells)."))
    C.append(cell("t542.u050.tail", "table542", "down-limb rho_user=0.50",
                  "tail delta NDCG@10", UT50T + UT50I, "pop_paired_delta",
                  {"a": UT50T, "b": UT50I, "stratum": "tail",
                   "expect_n_eval": NEVAL_VG, "expect_n": TAILN_VG},
                  [chk("mean", 0.000236, 6), chk("sd", 0.000532, 6), chk("pos", 4, mode="count")],
                  5, conf, seeds=S0812))
    C.append(cell("t542.u040.tail", "table542", "down-limb rho_user=0.40 (floor artifact)",
                  "tail delta NDCG@10", UT40T + UT40I, "pop_paired_delta",
                  {"a": UT40T, "b": UT40I, "stratum": "tail",
                   "expect_n_eval": NEVAL_VG, "expect_n": TAILN_VG},
                  [chk("mean", -0.001545, 6), chk("pos", 1, mode="count")], 5, conf, seeds=S0812))
    C.append(cell("t542.u040.text_abs", "table542", "rho_user=0.40 TEXT-arm tail collapse",
                  "tail text NDCG@10 mean", UT40T, "pop_arm_mean",
                  {"files": UT40T, "stratum": "tail"},
                  [chk("mean", 0.00218, 5)], 5, conf,
                  notes="Paper: 'falls to 0.00218 ~ 44% of the full-density anchor 0.00494'."))
    C.append(cell("t542.u040.text_hr", "table542", "rho_user=0.40 TEXT-arm tail HR",
                  "tail text HR@10 mean", UT40T, "pop_arm_mean",
                  {"files": UT40T, "stratum": "tail", "metric": "HR@10"},
                  [chk("mean", 0.00422, 5)], 5, conf))
    C.append(cell("t542.anchor.text_hr", "table542", "full-density TEXT-arm tail HR anchor",
                  "tail text HR@10 mean", TEXT5, "pop_arm_mean",
                  {"files": TEXT5, "stratum": "tail", "metric": "HR@10"},
                  [chk("mean", 0.0099, 4)], 5, conf,
                  notes="Was the one 2026-07-11 repair miss: the paper printed 0.0100 while "
                        "the recomputed 5-seed mean 0.0099266 rounds to 0.0099. Manuscript "
                        "corrected to 0.0099 ('tail HR 0.00422 vs 0.0099') in both "
                        "PAPER_SUBMISSION.md S5.4.2 and PAPER_DRAFT.md on 2026-07-11; "
                        "expectation updated to match. Never waived: the gate stayed "
                        "fail-closed until the manuscript changed."))
    C.append(cell("t542.u040.id_abs", "table542", "rho_user=0.40 ID-arm tail (holds)",
                  "tail id NDCG@10 mean", UT40I, "pop_arm_mean",
                  {"files": UT40I, "stratum": "tail"},
                  [chk("mean", 0.0037, 4, mode="approx", tol=0.0002)], 5, conf,
                  notes="Paper: 'the ID arm holds ~0.0037'."))

    # ---------------- S5.2 pre-declared V2 confirmation (SOTACONF_V2) ----------------
    C.append(cell("v2conf.k16", "tableV2conf", "K=16 fresh seeds 20260618-22 (EXEC2, gated)",
                  "NDCG@10 mean +- sd, 95% CI lower bound", SC16, "ci_lower",
                  {"files": SC16, "expect_n_eval": NEVAL_MI},
                  [chk("mean", 0.04152, 5), chk("sd", 0.00045, 5), chk("cilb", 0.04096, 5),
                   chk("cilb", PUB_HSTUBLAIR_MI, mode="gt")],
                  5, conf, seeds=S1822,
                  notes="Pre-declared (SOTA_CONFIRM_PREREG_V2.md); gate = CI-LB > published "
                        "0.0406. evidence_class confirmatory + pre-declared."))
    C.append(cell("v2conf.k8", "tableV2conf", "K=8 fresh seeds 20260618-22 (EXEC2, gated)",
                  "NDCG@10 mean +- sd, 95% CI lower bound", SC8, "ci_lower",
                  {"files": SC8, "expect_n_eval": NEVAL_MI},
                  [chk("mean", 0.04120, 5), chk("sd", 0.00030, 5), chk("cilb", 0.04083, 5),
                   chk("cilb", PUB_HSTUBLAIR_MI, mode="gt")],
                  5, conf, seeds=S1822))
    C.append(cell("v2conf.count", "tableV2conf", "fresh seeds above published 0.0406",
                  "count over both kernels", SC16 + SC8, "count_above",
                  {"files": SC16 + SC8, "threshold": PUB_HSTUBLAIR_MI},
                  [chk("count", 10, mode="count")], 10, conf))
    C.append(cell("v2conf.exec_agreement", "tableV2conf", "EXEC1 vs EXEC2 per-seed agreement",
                  "max |NDCG@10 difference|", SC16 + SC16E1 + SC8 + SC8E1, "max_pairwise_diff",
                  {"a": SC16 + SC8, "b": SC16E1 + SC8E1},
                  [chk("max_abs", 0.0003, mode="lt")], 10, conf,
                  notes="Paper: 'both executions agree per-seed to +-0.0003' (the voided EXEC1 "
                        "and the clean-tree EXEC2)."))
    C.append(cell("v2conf.rebuild", "tableV2conf", "clean-rebuild regeneration (rebuild_v2/)",
                  "dual gate holds on rebuilt artifacts", RB16 + RB8, "dual_gate",
                  {"k16": RB16, "k8": RB8, "threshold": PUB_HSTUBLAIR_MI},
                  [chk("pass", 1, mode="count")], 10, conf,
                  notes="From-scratch regeneration (commit 2a5003e) must independently pass the "
                        "pre-declared dual gate."))

    # ---------------- Table 2: negative-result map ----------------
    def t2delta(cid, row, run, basef, paper_delta, prec, notes="", base_label="H2 ls0 stack (seed08)"):
        return cell(cid, "table2", row, f"delta NDCG@10 vs {base_label} (n=1)",
                    [run] + ([basef] if isinstance(basef, str) else list(basef)),
                    "delta_means",
                    {"a": [run], "b": [basef] if isinstance(basef, str) else list(basef)},
                    [chk("delta", paper_delta, prec)], 1, expl, seeds=["20260608"], notes=notes)

    C.append(t2delta("t2.c3_decay", "c3 continuous time-decay attention kernel (L1)",
                     L1, H2, -0.0150, 4,
                     notes="The val>>test gap-exploder; see t2.c3_decay.val/test."))
    C.append(cell("t2.c3_decay.test", "table2", "c3 (L1) absolute test", "NDCG@10",
                  [L1], "single_metric", {"file": L1},
                  [chk("value", 0.0489, 4)], 1, expl))
    C.append(cell("t2.c3_decay.val", "table2", "c3 (L1) record validation", "val NDCG@10",
                  [L1], "best_val", {"file": L1},
                  [chk("value", 0.0725, 4)], 1, expl))
    C.append(t2delta("t2.sampled", "Sampled softmax (Q1, sampled_negs=512)", Q1, H2, -0.0026, 4,
                     notes="RESOLVED 2026-07-11 (repair pass P10): Table 2 once said 'K=1024 "
                           "negatives'; the paper now prints K=512, matching the artifact "
                           "(results_Q1_sampled512dot_VG.json, sampled_negs=512). K=1024 "
                           "belongs to the appendix Beauty scan, not this VG row."))
    C.append(t2delta("t2.dualtext", "Dual text encoder SBERT+BLaIR (O1)", O1, H2, -0.0014, 4))
    C.append(t2delta("t2.blair", "BLaIR text encoder swap (N1)", N1, H2, -0.0013, 4))
    C.append(t2delta("t2.gd1", "GD1 spectral-shrink prior", GD1, V25[0], -0.003, 3,
                     base_label="V2 seed08",
                     notes="Learned shrink driven to zero; BBP irreducibility figure retained."))
    C.append(t2delta("t2.heads4", "n_heads = 4 (P1)", P1, H2, -0.0005, 4))
    C.append(t2delta("t2.cl4srec", "CL4SRec self-supervision (T1)", T1, H2, -0.0005, 4,
                     notes="Direct delta -0.000446 rounds to -0.0004; the printed -0.0005 is the "
                           "difference of rounded endpoints (0.0634 - 0.0639), verified via the "
                           "endpoint check."))
    C[-1]["paper"].append(chk("delta", -0.0005, 4, mode="endpoint_files"))
    C.append(t2delta("t2.c1_experts", "c1 prototype-routed expert heads (M1)", M1, H2, -0.0004, 4))
    C.append(t2delta("t2.c2_distill", "c2 text-distillation aux loss (K1)", K1D, H2, -0.0004, 4))
    C.append(t2delta("t2.textinit", "text-init / warm-start (S1)", S1, H2, -0.0003, 4))
    C.append(t2delta("t2.ema", "EMA / SWA weight averaging (R1)", R1, H2, 0.0001, 4))
    C.append(cell("t2.textsim4", "table2", "text-sim bias (4-seed DECOMP5 isolation)",
                  "paired delta NDCG@10, dead-weight bound", D5TS + D5J1, "paired_delta",
                  {"a": D5TS, "b": D5J1},
                  [chk("mean", 0.0001, mode="bound_abs")], 4, expl,
                  notes="Table-2 row prints '+-0.0001 (4)': gate is |4-seed paired mean| <= "
                        "0.0001 (recomputed -0.000047). Corroborated by the single-seed drop "
                        "test results_ABL_no_textsim_VG.json (-0.000099 vs V2)."))
    C.append(cell("t2.textsim_drop", "table2", "text-sim bias dropped from V2 (ABL, n=1)",
                  "delta NDCG@10 (V2 minus no-textsim)", [V25[0], ABLTS], "delta_means",
                  {"a": [V25[0]], "b": [ABLTS]},
                  [chk("delta", 0.0001, mode="bound_abs")], 1, expl))
    C.append(cell("t2.w1.abs", "table2", "W1 niche-share fitness-sharing penalty",
                  "absolute test NDCG@10 (vs U2 band)", [W1], "single_metric", {"file": W1},
                  [chk("value", 0.0652, 4)], 1, expl,
                  notes="'Within band' holds against the recomputed U2 sd (0.00027): "
                        "|0.06518-0.06494| = 0.00024 < 1 sd. Consistent with the paper's "
                        "printed sd since the 2026-07-11 correction to 0.0003 (t1.ls.ndcg)."))
    C.append(cell("t2.w1.beta", "table2", "W1 learned scalar", "beta (sign-flipped)",
                  [W1], "json_scalar", {"file": W1, "key": "learned_niche_share_beta"},
                  [chk("value", -7.42, 2)], 1, expl))
    C.append(cell("t2.x1.abs", "table2", "X1 frequency-adaptive James-Stein shrinkage",
                  "absolute test NDCG@10 (vs V2 5-seed band)", [X1], "single_metric", {"file": X1},
                  [chk("value", 0.0673, 4)], 1, expl))
    C.append(cell("t2.x1.base_band", "table2", "X1/Y1 base band: V2 5-seed",
                  "NDCG@10 mean +- sd (seeds 08-12)", V25, "mean_std_metric",
                  {"files": V25, "expect_n_eval": NEVAL_VG},
                  [chk("mean", 0.0674, 4), chk("sd", 0.0003, 4)], 5, conf, seeds=S0812))
    C.append(cell("t2.x1.c", "table2", "X1 learned scalar", "shrink c -> 0",
                  [X1], "json_scalar", {"file": X1, "key": "learned_js_shrink_c"},
                  [chk("value", 0.004, 3), chk("value", 0.005, mode="lt")], 1, expl,
                  notes="Paper: 'c ~ 0 (lambda_max ~ 0.004)'; artifact value 0.004376."))
    C.append(cell("t2.y1.abs", "table2", "Y1 heat-kernel/manifold label smoothing",
                  "absolute test NDCG@10", [Y1], "single_metric", {"file": Y1},
                  [chk("value", 0.06653, 5)], 1, expl))
    C.append(cell("t2.y1.T", "table2", "Y1 learned scalar", "temperature T -> 0",
                  [Y1], "json_scalar", {"file": Y1, "key": "learned_heat_target_T"},
                  [chk("value", 0.00061, 5)], 1, expl))
    C.append(cell("t2.z1.tail_pct", "table2", "Z1 forced ID->text routing", "tail collapse percent",
                  [Z1, TEXT5[0]], "pop_pct_change",
                  {"a": [Z1], "b": [TEXT5[0]], "stratum": "tail"},
                  [chk("pct", -75.0, mode="approx", tol=1.0)], 1, expl,
                  notes="Recomputed -75.6% (Z1 tail 0.001206 vs V2-text seed08 tail 0.004941); "
                        "paper prints 'tail -75%'."))
    C.append(cell("t2.z1.overall", "table2", "Z1 overall (flat)", "delta NDCG@10 vs V2 seed08",
                  [Z1, V25[0]], "delta_means", {"a": [Z1], "b": [V25[0]]},
                  [chk("delta", 0.0005, mode="bound_abs")], 1, expl))
    C.append(cell("t2.cf1.vg", "table2", "CF1 cue-fusion gate (VG)", "delta NDCG@10 vs V2 seed08",
                  [CF1VG, V25[0]], "delta_means", {"a": [CF1VG], "b": [V25[0]]},
                  [chk("delta", 0.0005, mode="bound_abs")], 1, expl,
                  notes="RESOLVED 2026-07-12 (round-3 audit F5): the Table-2 base column read "
                        "'V2 / Beauty' but the second CF1 dataset on disk is "
                        "Musical_Instruments (results_CF1_cuefusion_MI*); the paper row now "
                        "prints 'V2 / MI'. Flat/dead verdict unchanged."))
    C.append(cell("t2.cf1.mi", "table2", "CF1 cue-fusion gate (MI, 5-seed)",
                  "paired delta NDCG@10 vs MI V2 k16", CF1MI + MIK16, "paired_delta",
                  {"a": CF1MI, "b": MIK16},
                  [chk("mean", 0.001, mode="bound_abs")], 5, conf,
                  notes="Recomputed -0.00063 (dead, no gain)."))
    C.append(cell("t2.conngate.tail", "table2", "conn-gate connectivity-gated fusion (MI, 5-seed)",
                  "paired tail delta NDCG@10 vs MI V2-text stack", CONNG + MIT_T, "pop_paired_delta",
                  {"a": CONNG, "b": MIT_T, "stratum": "tail",
                   "expect_n_eval": NEVAL_MI, "expect_n": TAILN_MI},
                  [chk("mean", 0.0001, 4), chk("sd", 0.0003, 4),
                   chk("ci_lo", -0.00025, 5), chk("ci_hi", 0.00045, 5)],
                  5, conf, seeds=S0812,
                  notes="The only Table-2 probe at full 5-seed power (pre-declared); CI includes "
                        "zero -> not actionable. Cadence caveat (2026-07-19): conn-gate arms "
                        "evaluated at epochs {10,20} vs every epoch for the base -> unequal "
                        "best-by-val checkpoint opportunities; the tail CI-includes-zero verdict "
                        "is cadence-insensitive but the small overall delta is not, and no claim "
                        "rests on its sign."))
    C.append(cell("t2.conngate.overall", "table2", "conn-gate overall (flat)",
                  "paired delta NDCG@10 vs MI V2-text stack", CONNG + MIT_T, "paired_delta",
                  {"a": CONNG, "b": MIT_T},
                  [chk("mean", 0.0005, mode="bound_abs")], 5, conf))
    C.append(cell("t2.conngate.alpha", "table2", "conn-gate learned scalar", "alpha -> 0.0011 (< init 0.0025)",
                  CONNG_LOGS, "log_scan",
                  {"files": CONNG_LOGS,
                   "regex": r"conn-gate alpha = ([0-9.]+)"},
                  [chk("mean", 0.0011, 4)], 4, expl,
                  notes="The learned alpha is not embedded in the result JSONs (fields null); it "
                        "is parsed from the tracked run logs. Declared n corrected 5->4 "
                        "(2026-07-19, audit 20:57): the driver log records seeds 09-12; the "
                        "seed-20260608 k8 log predates the alpha print line, so only 4/5 "
                        "values are recoverable (0.00107-0.00110, all rounding to 0.0011 "
                        "< init 0.0025)."))
    C.append(cell("t2.seq200", "table2", "max_seq_len 200 / seq > 50 (F1)",
                  "directional: no gain vs full-stack baselines", [F1S, H2], "delta_means",
                  {"a": [F1S], "b": [H2]},
                  [chk("delta", 0.0005, mode="lt")], 1, expl,
                  notes="DIRECTIONAL, config-confounded (100ep, no pos-rab; exact seq-50 twin not "
                        "on disk) -- disclosed in ANALYSIS_LOG; the paper renders it as '~0', "
                        "not a signed delta. Gate: F1 gains nothing over the seed-08 stack."))
    C.append(cell("t2.cosine", "table2", "cosine scoring (D1)",
                  "directional: underperforms dot at all op-points", [D1C, H2, U2F[0]], "delta_means",
                  {"a": [D1C], "b": [H2]},
                  [chk("delta", 0.0, mode="lt")], 1, expl,
                  notes="DIRECTIONAL, config-confounded (100ep, no pos-rab twin). Corroborating "
                        "sampled-pair: D2 samp512+cos 0.05814 < D3 samp512+dot 0.06072 "
                        "(results_D2_samp512cos_VG.json / results_D3_samp512_VG.json)."))

    # ---------------- office_confirmation: pre-declared second category ----------------
    # (audit F3.) SOTA_CONFIRM_PREREG_OFFICE.md, fresh seeds 20260623-27, config carried
    # over from MI unchanged. HEADLINE RULE: final-epoch FULL-catalog eval
    # (history[-1].test, n_eval=223,308) -- NOT best_test (the 30k best-by-val
    # subsample). Mirrors office_prereg_tools.py::_final_full. The dual gate passes
    # numerically on both kernels BUT the pre-declared floor check FAILED
    # (floor 0.02208 = +44% above published SASRec 0.0153), so the family is
    # provisional/VOID under the prereg -- the paper counts MI only (S5.2).
    C.append(cell("office.k16.gate", "office_confirmation",
                  "K=16 fresh seeds 20260623-27 (prereg OFFICE, gated)",
                  "final-epoch full-catalog NDCG@10 per seed + mean +- sd, 95% CI-LB",
                  OFF16, "final_full_ci",
                  {"files": OFF16, "seeds": SOFF, "expect_n_eval": NEVAL_OFF_FULL,
                   "threshold": PUB_HSTUBLAIR_OFF, "pct_vs": PUB_HSTUBLAIR_OFF},
                  [chk("mean", 0.03042, 5), chk("sd", 0.00008, 5), chk("cilb", 0.03032, 5),
                   chk("cilb", PUB_HSTUBLAIR_OFF, mode="gt"),
                   chk("n_above", 5, mode="count"),
                   chk("pct_vs_pub", 12.0, mode="approx", tol=0.5)],
                  5, conf, seeds=SOFF, status_note=OFFICE_VOID_NOTE,
                  notes="Pre-declared (SOTA_CONFIRM_PREREG_OFFICE.md, frozen before the raw "
                        "data finished downloading; zero category-specific tuning). Headline = "
                        "history[-1].test with n_eval asserted == 223,308; best_test is the "
                        "30k subsample and is NOT used. Paper prints 0.03042 +- 0.00008 "
                        "(CI-LB 0.03032), all seeds above published 0.0271, '~+12% margin' -- "
                        "but the S5.2 Office paragraph itself declares the pass VOID under the "
                        "failed prereg floor check; see office.floor."))
    C.append(cell("office.k8.gate", "office_confirmation",
                  "K=8 fresh seeds 20260623-27 (prereg OFFICE, gated)",
                  "final-epoch full-catalog NDCG@10 per seed + mean +- sd, 95% CI-LB",
                  OFF8, "final_full_ci",
                  {"files": OFF8, "seeds": SOFF, "expect_n_eval": NEVAL_OFF_FULL,
                   "threshold": PUB_HSTUBLAIR_OFF, "pct_vs": PUB_HSTUBLAIR_OFF},
                  [chk("mean", 0.03033, 5), chk("sd", 0.00018, 5), chk("cilb", 0.03010, 5),
                   chk("cilb", PUB_HSTUBLAIR_OFF, mode="gt"),
                   chk("n_above", 5, mode="count"),
                   chk("pct_vs_pub", 12.0, mode="approx", tol=0.5)],
                  5, conf, seeds=SOFF, status_note=OFFICE_VOID_NOTE,
                  notes="Same headline rule as office.k16.gate (final-epoch full-catalog, "
                        "n_eval=223,308). Paper prints 0.03033 +- 0.00018 (CI-LB 0.03010)."))
    C.append(cell("office.count_above", "office_confirmation",
                  "fresh seeds above published 0.0271 (both kernels)",
                  "count of final-epoch full-catalog NDCG@10 > 0.0271",
                  OFF16 + OFF8, "final_full_count_above",
                  {"files": OFF16 + OFF8, "expect_n_eval": NEVAL_OFF_FULL,
                   "threshold": PUB_HSTUBLAIR_OFF},
                  [chk("count", 10, mode="count")], 10, conf, seeds=SOFF,
                  status_note=OFFICE_VOID_NOTE,
                  notes="Paper: 'all 10 fresh seeds above the published HSTU-BLaIR point "
                        "estimate 0.0271' -- reported as provisional, not as a counted pass."))
    C.append(cell("office.idonly.arm", "office_confirmation",
                  "ID-only arm, fresh seeds 20260623-27 (prereg OFFICE)",
                  "final-epoch full-catalog NDCG@10 per seed + mean +- sd",
                  OFFID, "final_full_ci",
                  {"files": OFFID, "seeds": SOFF, "expect_n_eval": NEVAL_OFF_FULL},
                  [chk("mean", 0.02840, mode="info"), chk("sd", 0.00005, mode="info")],
                  5, conf, seeds=SOFF,
                  notes="Pre-declared 5-seed contrast arm (text stack removed). The overall "
                        "arm mean is not printed in the manuscript (info checks only; values "
                        "protected by the manifest drift gate); it exists as the ID side of "
                        "the descriptive tail contrast (office.tail.hits*)."))
    C.append(cell("office.floor", "office_confirmation",
                  "plain ID-only SASRec floor run (seed 20260623)",
                  "best_test NDCG@10 (floor check vs published SASRec 0.0153)",
                  [OFFFLOOR], "single_metric", {"file": OFFFLOOR},
                  [chk("value", 0.02208, 5), chk("value", 0.0221, 4)], 1, conf,
                  seeds=["20260623"],
                  status_note="floor check FAILED vs prereg condition",
                  notes="The prereg comparability condition (SOTA_CONFIRM_PREREG_OFFICE.md: "
                        "floor 'must be at or below' the published-SASRec neighborhood) "
                        "FAILED: 0.02208 is +44% above published 0.0153, so the Office "
                        "second-category pass is VOID under the prereg as written (paper "
                        "S5.2/Appendix A.0 disclose this; the matched comparator-baseline "
                        "run is COMPLETE — their own SASRec run locally lands +13.9% above "
                        "its published row, THEIRS_ON_OURS_REPORT.md S4.1 — and the VOID is "
                        "deliberately retained). "
                        "Floor is read from best_test exactly as adjudicated by "
                        "office_prereg_tools.py (the floor rule predates the final-full "
                        "headline rule and was scored on best_test)."))
    C.append(cell("office.floor.pct", "office_confirmation",
                  "floor inflation vs published SASRec 0.0153",
                  "percent (+44%)", [OFFFLOOR], "pct_change",
                  {"a": [OFFFLOOR], "denom_const": PUB_SASREC_OFF},
                  [chk("pct", 44.0, 0)], 1, conf, seeds=["20260623"],
                  status_note="floor check FAILED vs prereg condition",
                  notes="Recomputed +44.3%; the paper prints '+44% ABOVE the published "
                        "SASRec (0.0153)'. This is the quantity that voids the Office pass."))
    for K, chks in ((10, [chk("text_hits", 364, mode="count"),
                          chk("id_hits", 268, mode="count")]),
                    (20, [chk("text_hits", 586, mode="count"),
                          chk("id_hits", 414, mode="count")]),
                    (50, [chk("text_hits", 1170, mode="count"),
                          chk("id_hits", 739, mode="count")]),
                    (100, [chk("text_hits", 1983, mode="count"),
                           chk("id_hits", 1247, mode="count")])):
        C.append(cell(f"office.tail.hits{K}", "office_confirmation",
                      f"pooled tail hits @{K} (text = k8 arm vs ID-only)",
                      f"n_hit@{K} summed over 5 seeds, final-epoch full eval "
                      f"(tail n=36,610/seed)",
                      OFF8 + OFFID, "final_full_tail_hits",
                      {"a": OFF8, "b": OFFID, "k": K, "stratum": "tail",
                       "expect_n_eval": NEVAL_OFF_FULL, "expect_n": TAILN_OFF},
                      chks, 5, expl, seeds=SOFF,
                      status_note="descriptive post-hoc pattern evidence only; the "
                                  "pre-declared Office tail prediction was scored VOID "
                                  "(connectivity 2.89 in the pre-declared ambiguous zone)",
                      notes="Paper (S5.2) prints the @10 and @100 pooled counts with z; the "
                            "@20/@50 counts are printed in SOTA_CONFIRM_OFFICE_RESULTS.md "
                            "(final adjudication) and manifested here for completeness. "
                            "Audit F7: usable only as descriptive pattern evidence, never as "
                            "a pre-declared confirmation of the tail rule. Pooled-z RETRACTED "
                            "2026-07-19 (audit 22:08): clustered repeated users, not "
                            "independent trials; see office.tailwelch.* for valid "
                            "model-seed-level inference."))
    for K, dchk, tchk, lochk, hichk in (
            (10, chk("delta", 0.000524, 6), chk("t", 7.26, 2),
             chk("ci_lo", 0.00036, 5), chk("ci_hi", 0.00069, 5)),
            (100, chk("delta", 0.004021, 6), chk("t", 16.75, 2),
             chk("ci_lo", 0.00347, 5), chk("ci_hi", 0.00457, 5))):
        C.append(cell(f"office.tailwelch.hr{K}", "office_confirmation",
                      f"Office tail HR@{K}: model-seed independent-arm Welch (k8 vs ID-only)",
                      f"per-seed tail n_hit@{K}/n, final-epoch full eval; Welch t/CI",
                      OFF8 + OFFID, "final_full_tail_welch",
                      {"a": OFF8, "b": OFFID, "k": K, "stratum": "tail",
                       "expect_n_eval": NEVAL_OFF_FULL},
                      [dchk, tchk, lochk, hichk], 5, expl, seeds=SOFF,
                      notes="Replaces the retracted pooled two-proportion z (audit 22:08): "
                            "the trained model per arm is the inferential unit; same "
                            "direction, valid geometry. Final per-user sidecars for a fully "
                            "clustered analysis are a queued release item. Descriptive "
                            "pattern evidence only (the pre-declared tail prediction was "
                            "VOID)."))


    # ------- theirs-on-ours: the reference implementation executed locally -------
    # (S5.6 + Appendix A.0 resolution; full recipe/provenance THEIRS_ON_OURS_REPORT.md)
    THEIRS_MI = BR + "theirs_runs/music_hstu_blair/metrics.jsonl"
    THEIRS_OFF = BR + "theirs_runs/office_sasrec_final/metrics.jsonl"
    TON_NOTE = ("Reference repo external/HSTU-BLaIR @40a27879 UNMODIFIED (their "
                "preprocessing -> their gin -> their trainer -> their eval), run "
                "locally via three pure-PyTorch fbgemm data-movement shims + "
                "world-size-1 DDP identity wrapper. SINGLE RUN, unpinned env "
                "(torch 2.11 vs pinned 2.2.2), RTX 5060 Ti -- environment-caveated "
                "regeneration, not a pinned reproduction; changes no claim wording.")
    C.append(cell("theirs.mi.ndcg", "theirs_on_ours",
                  "their HSTU-BLaIR on Musical_Instruments, local run", "NDCG@10 full-corpus",
                  [THEIRS_MI], "theirs_jsonl", {"file": THEIRS_MI, "metric": "ndcg@10"},
                  [chk("final", 0.0391, 4), chk("best", 0.0406, 4)], 1, expl,
                  notes=TON_NOTE + " Best full eval = epoch 35 = published 0.0406 EXACTLY; "
                        "final epoch 100. Their own preprocess assertions passed "
                        "(24,587 items / 57,439 users)."))
    C.append(cell("theirs.mi.hr", "theirs_on_ours",
                  "their HSTU-BLaIR on Musical_Instruments, local run", "HR@10 full-corpus",
                  [THEIRS_MI], "theirs_jsonl", {"file": THEIRS_MI, "metric": "hr@10"},
                  [chk("final", 0.0716, 4), chk("best", 0.0743, 4)], 1, expl))
    C.append(cell("theirs.mi.mrr", "theirs_on_ours",
                  "their HSTU-BLaIR on Musical_Instruments, local run", "MRR full-corpus",
                  [THEIRS_MI], "theirs_jsonl", {"file": THEIRS_MI, "metric": "mrr"},
                  [chk("final", 0.0355, 4), chk("best", 0.0369, 4)], 1, expl))
    C.append(cell("theirs.office.ndcg", "theirs_on_ours",
                  "their SASRec on Office_Products, local run (floor-anomaly check)",
                  "NDCG@10 full-corpus",
                  [THEIRS_OFF], "theirs_jsonl",
                  {"file": THEIRS_OFF, "metric": "ndcg@10", "pct_vs": PUB_SASREC_OFF},
                  [chk("final", 0.0174, 4), chk("best", 0.0177, 4),
                   chk("pct_vs_pub", 13.9, 1)], 1, expl,
                  notes=TON_NOTE + " Lands +13.9% ABOVE its own published row 0.0153 "
                        "(crossed at epoch 20/101, never re-entered) -> the +44% floor "
                        "anomaly decomposes into published-row conservatism x "
                        "baseline-strength protocol differences; Office VOID retained "
                        "(Appendix A.0). Their preprocess assertions passed "
                        "(77,551 items / 223,308 users)."))
    THEIRS_OFFHB = BR + "theirs_runs/office_hstu_blair/metrics.jsonl"
    C.append(cell("theirs.office_hstu.ndcg", "theirs_on_ours",
                  "their HSTU-BLaIR on Office_Products, local run (completed 2026-07-12)",
                  "NDCG@10 full-corpus",
                  [THEIRS_OFFHB], "theirs_jsonl",
                  {"file": THEIRS_OFFHB, "metric": "ndcg@10", "pct_vs": PUB_HSTUBLAIR_OFF},
                  [chk("final", 0.0275, 4), chk("best", 0.0279, 4),
                   chk("pct_vs_pub", 1.6, mode="approx", tol=0.1)], 1, expl,
                  notes=TON_NOTE + " REGENERATES the published Office HSTU-BLaIR row 0.0271 "
                        "(final +1.6%; best full eval ep90 +2.8%) -- refutes the earlier "
                        "extrapolation that this row would be conservative like the Office "
                        "SASRec row (+13.9%): conservatism is per-row, not table-wide. "
                        "Descriptive only; the Office VOID stands on procedural grounds "
                        "(paper Appendix A.0, THEIRS_ON_OURS_REPORT.md S4.3)."))
    C.append(cell("office.floor_final_full", "theirs_on_ours",
                  "our SASRec floor, final-epoch FULL-catalog (decomposition endpoint)",
                  "NDCG@10",
                  [OFFFLOOR], "final_full_single",
                  {"file": OFFFLOOR, "expect_n_eval": NEVAL_OFF_FULL},
                  [chk("value", 0.0204, 4)], 1, expl,
                  notes="Same floor run as office.floor (best_test 0.02208 / 30k subsample) "
                        "read at history[-1].test (223,308 users) for the A.0 decomposition: "
                        "0.0204/0.0174 = +16.9% protocol strength; 0.0174/0.0153 = +13.9% "
                        "published-row conservatism; 1.139 x 1.169 = 1.331 = 0.0204/0.0153."))
    C.append(ext("theirs.pub.mi_hr", "theirs_on_ours",
                 "published MI HSTU-BLaIR (comparator README)", "HR@10", 0.0733,
                 "Liu 2025 README, Musical_Instruments HSTU-BLaIR row (S5.6 table)."))
    C.append(ext("theirs.pub.mi_mrr", "theirs_on_ours",
                 "published MI HSTU-BLaIR (comparator README)", "MRR", 0.0371,
                 "Liu 2025 README, Musical_Instruments HSTU-BLaIR row (S5.6 table)."))

    # ------- fir_breadth: pre-declared paired filter-vs-no-filter contrast -------
    # (PREREG_FIR_BREADTH.md; adjudication FIR_BREADTH_RESULTS.md; seeds 20260713-17)
    FIRB_SEEDS = [20260713, 20260714, 20260715, 20260716, 20260717]
    FB_NOTE = ("Pre-declared breadth campaign (PREREG_FIR_BREADTH.md, committed before any "
               "run; frozen V2 config transplanted with zero per-category tuning; fresh seeds "
               "20260713-17). Internal paired contrast, no comparator. Mechanical adjudication "
               "in FIR_BREADTH_RESULTS.md; n_eval full-catalog verified there per run.")
    for cat, short, exp in (
            ("Industrial_and_Scientific", "is",
             [chk("mean", 0.0024, 4), chk("ci_lo", 0.0018, 4), chk("ci_hi", 0.0030, 4),
              chk("pos", 5, mode="count")]),
            ("CDs_and_Vinyl", "cd",
             [chk("mean", 0.0057, 4), chk("ci_lo", 0.0049, 4), chk("ci_hi", 0.0064, 4),
              chk("pos", 5, mode="count")])):
        FF = [BR + f"results_FIRB_{cat}_filter_seed{s}.json" for s in FIRB_SEEDS]
        FN = [BR + f"results_FIRB_{cat}_nofilter_seed{s}.json" for s in FIRB_SEEDS]
        C.append(cell(f"firb.{short}.paired", "fir_breadth",
                      f"pre-declared FIR breadth: {cat} paired (filter - nofilter)",
                      "paired 5-seed delta NDCG@10 (best-by-val full catalog)",
                      FF + FN, "paired_delta", {"a": FF, "b": FN},
                      exp, 5, conf, seeds=FIRB_SEEDS, notes=FB_NOTE))

    for cat, short, dv, lo, hi in (("Industrial_and_Scientific", "is", 0.0024, 0.0019, 0.0029),
                                   ("CDs_and_Vinyl", "cd", 0.0057, 0.0050, 0.0063)):
        FF = [BR + f"results_FIRB_{cat}_filter_seed{s}.json" for s in FIRB_SEEDS]
        FN = [BR + f"results_FIRB_{cat}_nofilter_seed{s}.json" for s in FIRB_SEEDS]
        C.append(cell(f"firb.{short}.welch", "fir_breadth",
                      f"FIR breadth {cat}: independent-arm Welch (filter vs no-filter)",
                      "Welch 95% CI on per-arm best_test NDCG@10 (robustness companion)",
                      FF + FN, "welch_2arm_bt", {"a": FF, "b": FN},
                      [chk("diff", dv, 4), chk("ci95_lo", lo, 4), chk("ci95_hi", hi, 4),
                       chk("ci95_lo", 0.0, mode="gt")],
                      5, conf, seeds=[str(x) for x in FIRB_SEEDS],
                      notes="Graphs the independent-arm robustness CIs printed alongside the "
                            "pre-declared same-seed analysis (2026-07-19; the arms are not "
                            "initialization-paired, S5.3 disclosure). Part of the pre-declared "
                            "breadth campaign family."))

    # ------- tfv2: pre-declared repaired-estimand campaign (PREREG_TAIL_FIR_V2) -------
    # Externally timestamped (OpenTimestamps); independent 8-vs-8 arms; adjudicated
    # 2026-07-20 (TFV2_ADJUDICATION.md; E1 gated via the strict-chain verdict step).
    for short, cat, cid, dv, tv, lo, hi in (
            ("IS", "Industrial_and_Scientific", "tfv2.is.e2", 0.002131, 16.99, 0.001862, 0.002400),
            ("CDs", "CDs_and_Vinyl", "tfv2.cds.e3", 0.005770, 26.12, 0.005275, 0.006266)):
        FF2 = [BR + f"results_TFV2_{short}_filter_seed{s2}.json"
               for s2 in ({"IS": range(20260821, 20260829), "CDs": range(20260861, 20260869)}[short])]
        FN2 = [BR + f"results_TFV2_{short}_nofilter_seed{s2}.json"
               for s2 in ({"IS": range(20260831, 20260839), "CDs": range(20260871, 20260879)}[short])]
        C.append(cell(cid, "tfv2",
                      f"TFV2 {cat}: independent-arm Welch (filter vs no-filter, 8v8)",
                      "overall NDCG@10 Welch diff/t/95% CI (pre-declared, Holm family)",
                      FF2 + FN2, "welch_2arm_bt", {"a": FF2, "b": FN2},
                      [chk("diff", dv, 6), chk("t", tv, 2),
                       chk("ci95_lo", lo, 6), chk("ci95_hi", hi, 6),
                       chk("ci95_lo", 0.0, mode="gt")],
                      8, conf,
                      notes="PREREG_TAIL_FIR_V2 (externally timestamped before launch); "
                            "PASS under Holm with E1 (adjudicate_tfv2.py gates the strict "
                            "chain; verbatim record TFV2_ADJUDICATION.md)."))

    # ------- office_v3: redesigned pre-declared confirmation (PASSED) -------
    V3_SEEDS = [20260728, 20260729, 20260730, 20260731, 20260732]
    V3_NOTE = ("PREREG_OFFICE_V3.md (committed before any run; ERRATUM E1 pre-campaign): gate "
               "reference = the ENVIRONMENT-MATCHED local regeneration of the comparator "
               "(0.0279 best full-eval, above published 0.0271). Both arms PASSED "
               "(OFFICE_V3_RESULTS.md, block 196799e7c46d): 10/10 seeds above both references; "
               "per-category point-estimate comparison per the frozen wording -- no paired "
               "superiority, not SOTA. The V1 campaign remains VOID (Appendix A.0).")
    for arm, exp3 in ((16, [chk("mean", 0.03047, 5), chk("sd", 0.00011, 5),
                            chk("cilb", 0.03033, 5), chk("n_above", 5, mode="count")]),
                      (8, [chk("mean", 0.03029, 5), chk("sd", 0.00005, 5),
                           chk("cilb", 0.03024, 5), chk("n_above", 5, mode="count")])):
        V3F = [BR + f"results_OFFICEV3_k{arm}_seed{s}.json" for s in V3_SEEDS]
        C.append(cell(f"officev3.k{arm}.gate", "office_v3",
                      f"Office V3 pre-declared gate, K={arm} (final-epoch FULL-catalog)",
                      "NDCG@10 mean/sd/95% CI-LB vs local-regen 0.0279",
                      V3F, "final_full_ci",
                      {"files": V3F, "expect_n_eval": 223308, "threshold": 0.0279,
                       "seeds": V3_SEEDS},
                      exp3, 5, conf, seeds=V3_SEEDS, notes=V3_NOTE))

    # selection-timing taxonomy sweep (2026-07-19, audit 22:08): confirmatory labels are
    # reserved for the pre-declared prospective campaigns; every other multi-seed cell is
    # exploratory (multi-seed post-hoc: precision-improved, not confirmatory).
    # firb.* removed 2026-07-20 (audit 00:01): the frozen breadth rule is a paired t whose
    # pairing premise is false; its cells stay as frozen-rule records but are NOT
    # confirmatory. Welch companions are post-hoc (exploratory).
    PREDECLARED_PREFIXES = ("v2conf.", "officev3.", "t2.conngate.", "tfv2.")
    for c0 in C:
        if c0.get("evidence_class") == "confirmatory" and \
                (not c0["cell_id"].startswith(PREDECLARED_PREFIXES)
                 or c0["cell_id"].endswith(".welch")):
            c0["evidence_class"] = "exploratory"
            c0["notes"] = (c0.get("notes", "") + " [Evidence class set to exploratory under "
                           "the selection-timing criterion, 2026-07-19: multi-seed post-hoc "
                           "development/analysis work, not a pre-declared campaign.]").strip()
    return C

# ---------------------------------------------------------------- compute & verify
def compute_cell(c):
    if c.get("recompute") is None:
        return None
    fn = RULES[c["recompute"]["rule"]]
    return fn(c["recompute"]["params"])

def check_paper(c, rec, by_id):
    """classify each paper check; returns (results, cell_class)."""
    out = []
    any_fail, any_soft = False, False
    for k in c.get("paper", []):
        mode = k.get("mode", "round")
        name, pv = k.get("name"), k.get("value")
        rv = None if rec is None else rec.get(name)
        res = {"name": name, "paper": pv, "mode": mode, "recomputed": rv}
        if mode == "info" or rec is None:
            res["result"] = "info"
        elif mode == "round":
            r = rhu(rv, k["precision"])
            res["result"] = "exact" if abs(r - pv) < 10 ** (-k["precision"] - 6) else "MISMATCH"
            res["rounded"] = r
        elif mode == "approx":
            ok = abs(rv - pv) <= k["tol"]
            res["result"] = "within_tol" if ok else "MISMATCH"
        elif mode == "bound_abs":
            ok = abs(rv) <= pv + 5e-7
            res["result"] = "bound_ok" if ok else "MISMATCH"
        elif mode == "lt":
            res["result"] = "qual_ok" if rv < pv else "MISMATCH"
        elif mode == "gt":
            res["result"] = "qual_ok" if rv > pv else "MISMATCH"
        elif mode == "count":
            res["result"] = "exact" if int(round(rv)) == int(pv) else "MISMATCH"
        elif mode == "endpoint":
            mc, sc = by_id.get(k["minuend"]), by_id.get(k["subtrahend"])
            if not mc or not sc or mc.get("recomputed") is None or sc.get("recomputed") is None:
                res["result"] = "info"
            else:
                prec = k.get("precision", 4)
                ep = rhu(mc["recomputed"][k["mfield"]], prec) - rhu(sc["recomputed"][k["sfield"]], prec)
                res["endpoint_delta"] = rhu(ep, prec)
                res["result"] = ("endpoint_ok" if abs(res["endpoint_delta"] - pv)
                                 < 10 ** (-prec - 6) else "MISMATCH")
        elif mode == "endpoint_files":
            prec = k.get("precision", 4)
            a = rhu(rec["a_mean"], prec) if "a_mean" in rec else None
            b = rhu(rec["b_mean"], prec) if "b_mean" in rec else None
            if a is None or b is None:
                res["result"] = "info"
            else:
                res["endpoint_delta"] = rhu(a - b, prec)
                res["result"] = ("endpoint_ok" if abs(res["endpoint_delta"] - pv)
                                 < 10 ** (-prec - 6) else "MISMATCH")
        elif mode == "endpoint_pct":
            # percent formed from the ROUNDED endpoints (paper-style):
            # 100 * (round(minuend) - round(subtrahend)) / round(subtrahend)
            mc, sc = by_id.get(k["minuend"]), by_id.get(k["subtrahend"])
            if not mc or not sc or mc.get("recomputed") is None or sc.get("recomputed") is None:
                res["result"] = "info"
            else:
                eprec = k.get("eprec", 4)
                av = rhu(mc["recomputed"][k["mfield"]], eprec)
                bv = rhu(sc["recomputed"][k["sfield"]], eprec)
                prec = k.get("precision", 1)
                res["endpoint_pct"] = rhu(100.0 * (av - bv) / bv, prec)
                res["result"] = ("endpoint_ok" if abs(res["endpoint_pct"] - pv)
                                 < 10 ** (-prec - 6) else "MISMATCH")
        else:
            res["result"] = "info"
        if res["result"] == "MISMATCH":
            any_fail = True
        elif res["result"] in ("endpoint_ok", "within_tol", "bound_ok", "qual_ok"):
            any_soft = True
        out.append(res)
    # a cell whose 'round' checks fail but which carries a passing endpoint/tolerance
    # variant of the same named check is classified within_rounding, not MISMATCH
    names_fail = {r["name"] for r in out if r["result"] == "MISMATCH"}
    names_soft = {r["name"] for r in out
                  if r["result"] in ("endpoint_ok", "within_tol", "bound_ok")}
    superseded = False
    if names_fail and names_fail <= names_soft:
        any_fail = False
        superseded = True
        for r in out:
            if r["result"] == "MISMATCH" and r["name"] in names_soft:
                r["result"] = "mismatch_superseded_by_endpoint"
    # 'hard' checks compare a printed numeral at its printed precision; 'soft' checks
    # are endpoint-identities, tolerances, bounds, and qualitative sign/threshold gates.
    n_hard_pass = sum(1 for r in out if r["result"] == "exact")
    if any_fail:
        cls = "MISMATCH"
    elif superseded or (any_soft and n_hard_pass == 0):
        cls = "within_rounding"
    elif n_hard_pass:
        cls = "exact"
    elif any_soft:
        cls = "within_rounding"
    else:
        cls = "exact"  # info-only cells
    return out, cls

# ---------------------------------------------------------------- rendering
def fmt(v, nd=6):
    return f"{v:+.{nd}f}" if v < 0 or nd >= 5 else f"{v:.{nd}f}"

def render_tables(cells):
    by_id = {c["cell_id"]: c for c in cells}

    def R(cid, field="mean", nd=4):
        c = by_id[cid]
        return f"{c['recomputed'][field]:.{nd}f}"

    def MS(cid, nd=4):
        c = by_id[cid]["recomputed"]
        return f"{c['mean']:.{nd}f} ± {c['sd']:.{nd}f}"

    def PD(cid, nd=6):
        c = by_id[cid]["recomputed"]
        return f"{c['mean']:+.{nd}f} ± {c['sd']:.{nd}f} ({int(c['pos'])}/{int(c['n'])})"

    T = {}
    T["table1"] = "\n".join([
        "**Table 1 (regenerated): Headline component ablation — NDCG@10, AR2023 Video_Games "
        "5-core LLOO, full-catalog n_eval=94,762 (values recomputed from manifested artifacts).**",
        "",
        "| Configuration | NDCG@10 | seeds | Δ (direct recompute) | evidence |",
        "|---|---:|---:|---:|---|",
        f"| HSTU-style encoder, plain | {R('t1.plain.ndcg','value')} | 1 | — | exploratory |",
        f"| + TAPE-512 | {R('t1.tape.ndcg','value')} | 1 | {by_id['t1.tape.delta']['recomputed']['delta']:+.4f} | exploratory |",
        f"| + full bias stack | {MS('t1.bias_stack.ndcg')} | 5 | {by_id['t1.bias_stack.delta']['recomputed']['delta']:+.4f} vs plain | multi-seed (post-hoc) |",
        f"| + label smoothing ε=0.2 | {MS('t1.ls.ndcg')} | 5 | {by_id['t1.ls.delta']['recomputed']['delta']:+.4f} | multi-seed (post-hoc) |",
        f"| **+ causal FIR filter K=8 → full model** | **{MS('t1.full.ndcg')}** | **6** | "
        f"**{by_id['t1.full.delta']['recomputed']['delta']:+.4f}** | multi-seed (post-hoc) |",
        f"| *(isolation)* FIR package arm (filter component; attribution open), no LS | {MS('t1.v1b.ndcg')} | 5 | {by_id['t1.v1b.delta']['recomputed']['delta']:+.4f} vs stack | multi-seed (post-hoc) |",
        f"| *(isolation)* ID-only | {MS('t1.idonly.ndcg')} | 5 | text adds {by_id['t1.text_add.paired']['recomputed']['mean']:+.5f} "
        f"({by_id['t1.text_add.pct']['recomputed']['pct']:+.1f}%) | multi-seed (post-hoc) |",
        f"| kernel sweep K=16 | {MS('t1.ksweep.k16')} | 5 | — | multi-seed (post-hoc) |",
        f"| kernel sweep K=4 / K=50 (3-seed) | {by_id['t1.ksweep.k4']['recomputed']['a_mean']:.4f} / "
        f"{by_id['t1.ksweep.k50']['recomputed']['a_mean']:.4f} | 3 | robustness only | exploratory |",
        "",
        f"Single-flag attribution (seed 20260608, exploratory): time bias "
        f"{by_id['t1.decomp1.timebias']['recomputed']['delta']:+.4f}; text-sim "
        f"{by_id['t1.decomp1.textsim']['recomputed']['delta']:+.6f}. 4-seed DECOMP5 cross-check "
        f"(exploratory): base {R('t1.decomp5.base')}, time bias "
        f"{by_id['t1.decomp5.timebias']['recomputed']['mean']:+.4f}, pos-rab "
        f"{by_id['t1.decomp5.posrab']['recomputed']['mean']:+.4f}, TAPE "
        f"{by_id['t1.decomp5.tape']['recomputed']['mean']:+.4f}, text-sim "
        f"{by_id['t1.decomp5.textsim']['recomputed']['mean']:+.6f}.",
    ])

    unt_rows = [c for c in cells if c["table_id"] == "table1a" and c["status"] == "UNTRACEABLE"]
    ret_rows = [c for c in cells if c["table_id"] == "table1a"
                and c["status"] == "REMOVED_FROM_PAPER"]
    T["table1a"] = "\n".join([
        "**Table 1a (regenerated): SASRec-family protocol-parity baselines.** The v1-era "
        "SASRec/SBERT/BLaIR rows were removed from the manuscript (2026-07-11, audit F1); "
        "only the traceable popularity floor remains a paper row.",
        "",
        "| Method | NDCG@10 | HR@10 | provenance |",
        "|---|---:|---:|---|",
        f"| popularity | {R('t1a.popularity.ndcg','value')} | {R('t1a.popularity.hr','value')} | "
        f"results_5core_Video_Games.json (deterministic) |",
    ] + [f"| {c['row_label']} | UNTRACEABLE | UNTRACEABLE | **WARNING: no on-disk source** "
         f"(paper prints: {c['metric']}) |" for c in unt_rows]
      + [f"| {c['row_label']} | — | — | RETIRED (REMOVED_FROM_PAPER): row + derived "
         f"observations deleted from the manuscript; kept in the manifest as provenance "
         f"history only (was: {c['metric']}) |" for c in ret_rows])

    T["table1b"] = "\n".join([
        "**Table 1b (regenerated, local rows only): HSTU-BLaIR comparator evidence.** "
        "Published rows are cited constants (EXTERNAL_PUBLISHED), not local artifacts.",
        "",
        "| Row | NDCG@10 | HR@10 | provenance |",
        "|---|---:|---:|---|",
        f"| HSTU-BLaIR local SM120 port (final full eval) | {R('t1b.port.final_ndcg','value',5)} | "
        f"{R('t1b.port.final_hr','value',5)} | _bestrec_sota_lab/.../hstu_blair_eval_export_summary.json |",
        "| HSTU-BLaIR local port (best full eval) | RETIRED (REMOVED_FROM_PAPER; was paper: "
        "0.07403) | — | best-epoch reading survives only in an unretained WSL log; removed "
        "from the manuscript, which now prints the exported final full-eval 0.07382 only |",
        "| SASRec / HSTU / HSTU-BLaIR published rows | 0.0573 / 0.0741 / 0.0760 | — | "
        "external published (Liu 2025; Zhai 2024) |",
    ])

    T["table1c"] = "\n".join([
        "**Table 1c (regenerated): Musical_Instruments per-lever isolation — NDCG@10, best-by-val, "
        "n_eval=57,439 (recomputed).**",
        "",
        "| Configuration | NDCG@10 | Δ vs base | share of k16 combined lift |",
        "|---|---:|---:|---:|",
        f"| MI SBERT+TAPE base (four 20-epoch seeds) | {MS('t1c.base.ndcg')} | — | — |",
        f"| + label smoothing only (5-seed) | {MS('t1c.lsonly.ndcg', 5)} | "
        f"{by_id['t1c.lsonly.delta']['recomputed']['delta']:+.4f} | "
        f"{by_id['t1c.lsonly.share']['recomputed']['pct']:.0f}% |",
        f"| + FIR package arm (filter component; attribution open) (k16, 5-seed) | {R('t1c.filteronly.ndcg')} | "
        f"{by_id['t1c.filteronly.delta']['recomputed']['delta']:+.4f} | "
        f"{by_id['t1c.filteronly.share']['recomputed']['pct']:.0f}% |",
        f"| + both = V2 (k16, 5-seed) | {MS('t1c.v2k16.ndcg')} | "
        f"{by_id['t1c.v2k16.delta']['recomputed']['delta']:+.4f} | 100% |",
        f"| V2 k8 headline stack (5-seed) | {MS('t1c.v2k8.ndcg')} | "
        f"+{by_id['t1c.v2k8.pct_base']['recomputed']['pct']:.1f}% vs base; filter share "
        f"{by_id['t1c.v2k8.share']['recomputed']['pct']:.0f}% | — |",
        f"| plain ID-only SASRec (MI floor) | {R('t1c.sasrec_floor.ndcg','value')} | "
        f"V2 k8 is +{by_id['t1c.v2k8.pct_sasrec']['recomputed']['pct']:.0f}% above | — |",
    ])

    T["table1d"] = "\n".join([
        "**Table 1d (regenerated): text − ID tail-tercile NDCG@10 contrast (same-seed-number "
        "arms — NOT initialization-paired; §5.3 randomization disclosure).**",
        "",
        "| dataset | tail Δ NDCG@10 | seeds positive | evidence |",
        "|---|---:|---:|---|",
        f"| Musical_Instruments (sparse) | {PD('t1d.mi.tail')} , Welch 95% CI "
        f"[{by_id['t1d.mi.welch']['recomputed']['ci95_lo']:+.6f}, "
        f"{by_id['t1d.mi.welch']['recomputed']['ci95_hi']:+.6f}] | "
        f"{int(by_id['t1d.mi.tail']['recomputed']['pos'])}/5 | multi-seed post-hoc (independent-arm Welch) |",
        f"| Video_Games (dense) | {PD('t1d.vg.tail')} | {int(by_id['t1d.vg.tail']['recomputed']['pos'])}/5 | null — equivalence claim RETRACTED 2026-07-19 (§5.3) |",
        f"| Beauty_and_PC (dense) | {PD('t1d.beauty.tail', 7)} | {int(by_id['t1d.beauty.tail']['recomputed']['pos'])}/3 | exploratory (3-seed; mixed eval geometry) |",
        "",
        f"MI tail HR replication: {PD('t1d.mi.tail_hr', 5)}; hits/seed "
        f"{by_id['t1d.mi.tail_hits_text']['recomputed']['hits']:.1f} vs "
        f"{by_id['t1d.mi.tail_hits_id']['recomputed']['hits']:.1f}; MI head Δ "
        f"{by_id['t1d.mi.head_abs']['recomputed']['mean']:+.5f}. MI independent-arm Welch: t = "
        f"{by_id['t1d.mi.welch']['recomputed']['t']:.2f}, p = "
        f"{by_id['t1d.mi.welch']['recomputed']['p']:.3f}. VG independent-arm Welch: p = "
        f"{by_id['t1d.vg.welch']['recomputed']['p']:.2f}, 90% CI "
        f"[{by_id['t1d.vg.welch']['recomputed']['ci90_lo']:+.6f}, "
        f"{by_id['t1d.vg.welch']['recomputed']['ci90_hi']:+.6f}] — NOT contained in the retracted "
        f"±0.000335 margin (no equivalence claim). Cross-dataset four-arm Welch–Satterthwaite: "
        f"MI−VG = {by_id['t1d.welch']['recomputed']['est']:+.6f}, t = "
        f"{by_id['t1d.welch']['recomputed']['t']:.2f}, df = "
        f"{by_id['t1d.welch']['recomputed']['df']:.1f}, p = "
        f"{by_id['t1d.welch']['recomputed']['p']:.4f}. (The former paired-CI/MDE/TOST nodes are "
        f"tombstoned — retracted 2026-07-19.)",
    ])

    rows1e = []
    for tag, rho, ipi in (("100", 1.00, 24.405), ("094", 0.94, 22.947), ("091", 0.91, 22.210),
                          ("088", 0.88, 21.484), ("078", 0.78, 19.030), ("066", 0.66, 16.109)):
        rows1e.append(
            f"| {rho:.2f} | {ipi:.3f} | "
            f"{PD(f't1e.rho{tag}.head_ndcg')} | {PD(f't1e.rho{tag}.head_hr')} | "
            f"{PD(f't1e.rho{tag}.tail_ndcg')} | {PD(f't1e.rho{tag}.tail_hr')} |")
    T["table1e"] = "\n".join([
        "**Table 1e (regenerated): interaction-thinning density-titration ladder** "
        "(paired text−ID, best-by-val; 5 seeds/rung; n_eval=94,762, tail_n=10,900; "
        "kept-inter./item quoted from run logs; the former α=ipi/d_eff column is "
        "RETRACTED with the spectral analysis, 2026-07-19).",
        "",
        "| ρ | kept inter./item | head ΔNDCG@10 | head ΔHR@10 | tail ΔNDCG@10 | tail ΔHR@10 |",
        "|---|---|---|---|---|---|"] + rows1e + [
        "",
        f"Spearman ρ_s vs density: head NDCG {by_id['t1e.spearman.head_ndcg']['recomputed']['rho']:+.2f}, "
        f"head HR {by_id['t1e.spearman.head_hr']['recomputed']['rho']:+.2f}, "
        f"tail NDCG {by_id['t1e.spearman.tail_ndcg']['recomputed']['rho']:+.2f} (n.s.).",
    ])

    T["table541"] = "\n".join([
        "**§5.4.1 (regenerated): scale-free tail/head arm-ratio table.**",
        "",
        "| regime | TAIL text | TAIL id | TAIL ratio | HEAD ratio |",
        "|---|---:|---:|---:|---:|",
        f"| VG full density | {R('t541.vgfull.tail_text','mean',6)} | {R('t541.vgfull.tail_id','mean',6)} | "
        f"{R('t541.vgfull.tail_ratio','ratio',3)} | {R('t541.vgfull.head_ratio','ratio',3)} |",
        f"| VG thinned → MI-density (ρ=0.66) | {R('t541.rho066.tail_text','mean',6)} | "
        f"{R('t541.rho066.tail_id','mean',6)} | {R('t541.rho066.tail_ratio','ratio',3)} | "
        f"{R('t541.rho066.head_ratio','ratio',3)} |",
        f"| MI native | {R('t541.mi.tail_text','mean',6)} | {R('t541.mi.tail_id','mean',6)} | "
        f"{R('t541.mi.tail_ratio','ratio',3)} | {R('t541.mi.head_ratio','ratio',3)} |",
        "",
        f"Tail starvation full→ρ0.66: text {by_id['t541.starve.text_pct']['recomputed']['pct']:+.1f}%, "
        f"ID {by_id['t541.starve.id_pct']['recomputed']['pct']:+.1f}%; MI tail relative text gain "
        f"{by_id['t541.mi.tail_rel']['recomputed']['pct']:+.1f}%.",
    ])

    T["table542"] = "\n".join([
        "**§5.4.2 (regenerated): user-mode titration (connectivity).**",
        "",
        "| regime | TAIL ratio | tail Δ (5-seed) | HEAD ratio |",
        "|---|---:|---:|---:|",
        f"| VG full | {R('t541.vgfull.tail_ratio','ratio',3)} | {PD('t1d.vg.tail')} | "
        f"{R('t541.vgfull.head_ratio','ratio',3)} |",
        f"| VG interaction-thinned ρ=0.66 | {R('t541.rho066.tail_ratio','ratio',3)} | "
        f"{PD('t1e.rho066.tail_ndcg')} | {R('t541.rho066.head_ratio','ratio',3)} |",
        f"| **VG user-thinned ρ_user=0.66** | **{R('t542.u066.tail_ratio','ratio',3)}** | "
        f"**{PD('t542.u066.tail')}** (Welch p = "
        f"{by_id['t542.u066.welch']['recomputed']['p']:.2f}, n.s.) | "
        f"{R('t542.u066.head_ratio','ratio',3)} |",
        f"| MI native | {R('t541.mi.tail_ratio','ratio',3)} | {PD('t1d.mi.tail')} | "
        f"{R('t541.mi.head_ratio','ratio',3)} |",
        "",
        f"dd vs full anchor (descriptive): {PD('t542.u066.dd_vs_full')}; four-group Welch "
        f"t = {by_id['t542.u066.dd_welch']['recomputed']['t']:.2f}, p = "
        f"{by_id['t542.u066.dd_welch']['recomputed']['p']:.3f}, 95% CI "
        f"[{by_id['t542.u066.dd_welch']['recomputed']['ci_lo']:+.6f}, "
        f"{by_id['t542.u066.dd_welch']['recomputed']['ci_hi']:+.6f}] — includes zero: suggestive, "
        f"NOT significant (the former paired t/sign-test inference is retracted 2026-07-19). "
        f"Matched-R1 (user − interaction): tail "
        f"{by_id['t542.matchedR1.tail']['recomputed']['mean']:+.6f}, head "
        f"{by_id['t542.matchedR1.head']['recomputed']['mean']:+.6f} (diff-of-diffs "
        f"{by_id['t542.matchedR1.tail']['recomputed']['mean'] - by_id['t542.matchedR1.head']['recomputed']['mean']:+.6f}). "
        f"Down-limb: ρ_user=0.50 {PD('t542.u050.tail')}; ρ_user=0.40 {PD('t542.u040.tail')} — "
        f"TEXT-arm floor collapse (tail abs {R('t542.u040.text_abs','mean',5)}, tail HR "
        f"{R('t542.u040.text_hr','mean',5)} vs full-density anchor {R('t542.anchor.text_hr','mean',4)}; "
        f"ID arm {R('t542.u040.id_abs','mean',4)}).",
    ])

    k16, k8 = by_id["v2conf.k16"]["recomputed"], by_id["v2conf.k8"]["recomputed"]
    T["tableV2conf"] = "\n".join([
        "**§5.2 (regenerated): pre-declared dual-kernel V2 confirmation "
        "(SOTACONF_V2, fresh seeds 20260618–22, EXEC2 gated artifacts, n_eval=57,439).**",
        "",
        "| kernel | fresh 5-seed NDCG@10 | 95% CI lower bound | vs published 0.0406 |",
        "|---|---:|---:|---|",
        f"| K=16 | {k16['mean']:.5f} ± {k16['sd']:.5f} | {k16['cilb']:.5f} | ABOVE |",
        f"| K=8 | {k8['mean']:.5f} ± {k8['sd']:.5f} | {k8['cilb']:.5f} | ABOVE |",
        "",
        f"Fresh seeds above 0.0406: {int(by_id['v2conf.count']['recomputed']['count'])}/10. "
        f"EXEC1↔EXEC2 max per-seed |Δ| = "
        f"{by_id['v2conf.exec_agreement']['recomputed']['max_abs']:.6f} (< 0.0003). "
        f"Clean rebuild (rebuild_v2/): K=16 CI-LB "
        f"{by_id['v2conf.rebuild']['recomputed']['k16_cilb']:.5f}, K=8 CI-LB "
        f"{by_id['v2conf.rebuild']['recomputed']['k8_cilb']:.5f} — dual gate "
        f"{'PASS' if by_id['v2conf.rebuild']['recomputed']['pass'] else 'FAIL'}.",
    ])

    def _seeds(cid):
        r = by_id[cid]["recomputed"]
        return " / ".join(f"{r['seed' + s]:.5f}" for s in
                          ("20260623", "20260624", "20260625", "20260626", "20260627"))

    ok16, ok8 = by_id["office.k16.gate"]["recomputed"], by_id["office.k8.gate"]["recomputed"]
    oid, ofl = by_id["office.idonly.arm"]["recomputed"], by_id["office.floor"]["recomputed"]
    hitrows = []
    for K in (10, 20, 50, 100):
        h = by_id[f"office.tail.hits{K}"]["recomputed"]
        hitrows.append(f"@{K}: {int(h['text_hits'])} vs {int(h['id_hits'])} (descriptive counts; pooled z retracted 2026-07-19)")
    T["office_confirmation"] = "\n".join([
        "**office_confirmation (regenerated): second-category pre-declared confirmation — "
        "Office_Products** (SOTA_CONFIRM_PREREG_OFFICE.md; fresh seeds 20260623–27; headline "
        "rule = final-epoch FULL-catalog eval, history[-1].test, n_eval=223,308 — NOT the "
        "30k best_test subsample).",
        "",
        "**STATUS: VOID under the prereg floor check (+44% floor inflation) — provisional; "
        "the V1 Office campaign counts in no claim. Office V3 — a separate, redesigned "
        "pre-declaration — passed and is counted under its frozen per-category "
        "point-estimate wording (§5.2).**",
        "",
        "| arm | per-seed NDCG@10 (final-epoch full) | mean ± sd | 95% CI-LB | vs published 0.0271 |",
        "|---|---|---:|---:|---|",
        f"| K=16 | {_seeds('office.k16.gate')} | {ok16['mean']:.5f} ± {ok16['sd']:.5f} | "
        f"{ok16['cilb']:.5f} | ABOVE ({int(ok16['n_above'])}/5 seeds) — provisional/VOID |",
        f"| K=8 | {_seeds('office.k8.gate')} | {ok8['mean']:.5f} ± {ok8['sd']:.5f} | "
        f"{ok8['cilb']:.5f} | ABOVE ({int(ok8['n_above'])}/5 seeds) — provisional/VOID |",
        f"| ID-only (contrast arm) | {_seeds('office.idonly.arm')} | {oid['mean']:.5f} ± "
        f"{oid['sd']:.5f} | {oid['cilb']:.5f} | (no gate; tail-contrast arm) |",
        f"| SASRec floor (best_test, seed 20260623) | {ofl['value']:.5f} | — | — | "
        f"floor check FAILED: {by_id['office.floor.pct']['recomputed']['pct']:+.1f}% vs "
        f"published SASRec 0.0153 → Office pass VOID under prereg |",
        "",
        f"Fresh seeds above published 0.0271: "
        f"{int(by_id['office.count_above']['recomputed']['count'])}/10 (provisional; not a "
        f"counted pass). Pooled tail hits, text (k8 arm) vs ID-only, final-epoch full eval "
        f"(tail n=36,610/seed): " + "; ".join(hitrows) + " — descriptive post-hoc pattern "
        "evidence only (the pre-declared Office tail prediction was scored VOID: "
        "connectivity 2.89 in the pre-declared ambiguous zone).",
    ])

    t2rows = []
    for cid, lever, basecol, n in [
            ("t2.c3_decay", "c3 continuous time-decay kernel (L1)", "H2 stack 0.0639", 1),
            ("t2.sampled", "Sampled softmax (Q1, negs=512)", "H2 (full-softmax)", 1),
            ("t2.dualtext", "Dual text encoder (O1)", "H2 (SBERT)", 1),
            ("t2.blair", "BLaIR encoder swap (N1)", "H2 (SBERT)", 1),
            ("t2.gd1", "GD1 spectral-shrink", "V2 seed08", 1),
            ("t2.heads4", "n_heads = 4 (P1)", "H2", 1),
            ("t2.cl4srec", "CL4SRec SSL (T1)", "H2", 1),
            ("t2.c1_experts", "c1 expert heads (M1)", "H2", 1),
            ("t2.c2_distill", "c2 text-distill (K1)", "H2", 1),
            ("t2.textinit", "text-init warm-start (S1)", "H2", 1),
            ("t2.ema", "EMA/SWA (R1)", "H2", 1)]:
        d = by_id[cid]["recomputed"]["delta"]
        t2rows.append(f"| {lever} | {basecol} | {d:+.5f} | n/a | {n} |")
    t2rows.append(f"| text-sim bias (DECOMP5) | J1 plain 4-seed | "
                  f"{by_id['t2.textsim4']['recomputed']['mean']:+.6f} (|Δ|≤0.0001) | n/a | 4 |")
    t2rows.append(f"| W1 niche-share | U2 band | abs {R('t2.w1.abs','value')} | "
                  f"β = {by_id['t2.w1.beta']['recomputed']['value']:.4f} | 1 |")
    t2rows.append(f"| X1 James–Stein shrink | V2 band {MS('t2.x1.base_band')} | abs "
                  f"{R('t2.x1.abs','value')} | c = {by_id['t2.x1.c']['recomputed']['value']:.4f} → off | 1 |")
    t2rows.append(f"| Y1 heat-kernel target | V2 band | abs {R('t2.y1.abs','value',5)} | "
                  f"T = {by_id['t2.y1.T']['recomputed']['value']:.5f} → 0 | 1 |")
    t2rows.append(f"| Z1 forced ID→text routing | V2-text tail (s08) | tail "
                  f"{by_id['t2.z1.tail_pct']['recomputed']['pct']:+.1f}% (overall "
                  f"{by_id['t2.z1.overall']['recomputed']['delta']:+.5f}) | forced | 1 |")
    t2rows.append(f"| CF1 cue-fusion | V2 (VG) / MI k16 | {by_id['t2.cf1.vg']['recomputed']['delta']:+.5f} / "
                  f"{by_id['t2.cf1.mi']['recomputed']['mean']:+.5f} | gate → 0 | 1 / 5 |")
    cg = by_id["t2.conngate.tail"]["recomputed"]
    t2rows.append(f"| conn-gate (MI, 5-seed; cadence-caveated) | MI V2-text stack | tail {cg['mean']:+.5f} ± "
                  f"{cg['sd']:.5f}, 95% CI [{cg['ci_lo']:+.5f}, {cg['ci_hi']:+.5f}] | α = "
                  f"{by_id['t2.conngate.alpha']['recomputed']['mean']:.5f} (voted off; 4/5 logs) | 5 |")
    t2rows.append(f"| max_seq_len 200 (F1, directional) | full-stack baselines | "
                  f"{by_id['t2.seq200']['recomputed']['delta']:+.5f} (no gain) | n/a | 1 |")
    t2rows.append(f"| cosine scoring (D1, directional) | dot baselines | "
                  f"{by_id['t2.cosine']['recomputed']['delta']:+.5f} (≤0) | n/a | 1 |")
    T["table2"] = "\n".join([
        "**Table 2 (regenerated): screening log of capacity-adding probes.** All single-seed rows are "
        "exploratory (audit F6); conn-gate (cadence-caveated) and the titration nulls of "
        "§5.3–§5.4 were run at full pre-declared power (no null thereby confirmed — the "
        "equivalence framework is withdrawn); the former VG/Beauty equivalence claims are "
        "retracted (§5.3).",
        "",
        "| Lever | Base | Δ NDCG@10 (recomputed) | learned scalar | n |",
        "|---|---|---:|---|---:|"] + t2rows)
    return T

# ---------------------------------------------------------------- main modes
def write_manifest(path):
    cells = build_spec()
    by_id = {c["cell_id"]: c for c in cells}
    n_err = 0
    for c in cells:
        if c.get("recompute") is None:
            c["recomputed"] = None
            c["recomputed_value"] = None
            continue
        try:
            rec = compute_cell(c)
        except Exception as e:
            print(f"ERROR computing {c['cell_id']}: {e}", file=sys.stderr)
            n_err += 1
            continue
        c["recomputed"] = rec
        prim = c["paper"][0]["name"] if c.get("paper") else None
        c["recomputed_value"] = rec.get(prim) if prim in (rec or {}) else \
            next(iter(rec.values()))
    if n_err:
        sys.exit(f"ABORT --write-manifest: {n_err} cells failed to compute")
    for c in cells:
        if c.get("recomputed") is not None:
            c["paper_check"], c["paper_check_class"] = check_paper(c, c["recomputed"], by_id)
        elif c["status"] == "UNTRACEABLE":
            c["paper_check"], c["paper_check_class"] = [], "UNTRACEABLE"
        elif c["status"] == "REMOVED_FROM_PAPER":
            c["paper_check"], c["paper_check_class"] = [], "REMOVED_FROM_PAPER"
        else:
            c["paper_check"], c["paper_check_class"] = [], "external"
    manifest = {
        "manifest_version": 3,
        "generated": "2026-07-11",
        "purpose": "Enforceable artifact graph for the canonical HSTU/FIR manuscript: every "
                   "empirical table cell -> source result JSONs -> recompute rule -> "
                   "recomputed value. Audit F2; evidence labels audit F6; fail-closed "
                   "submission gate + Office_Products family per the strict resubmission "
                   "audit 2026-07-11 (F1, F3).",
        "paper": "PAPER_SUBMISSION.md (canonical submission copy; printed-value snapshot "
                 "2026-07-11 post audit-repair) / PAPER_DRAFT.md kept in sync",
        "builder": "_bestrec_run/build_hstu_tables.py",
        "rerun": "_bestrec_run/.venv/Scripts/python _bestrec_run/build_hstu_tables.py",
        "rerun_submission_gate": "_bestrec_run/.venv/Scripts/python "
                                 "_bestrec_run/build_hstu_tables.py --submission",
        "recompute_tolerance": TOL,
        "evidence_class_rule": "confirmatory labels are reserved for pre-declared prospective "
                               "campaigns and their frozen-protocol locks -- selection timing, "
                               "not seed count, is the criterion (corrected 2026-07-19; the "
                               "full cell-by-cell taxonomy audit against this criterion is "
                               "queued). exploratory = single-seed / post-hoc; external = "
                               "published comparator constant.",
        "status_semantics": "OK = sourced + recomputed + drift-gated. UNTRACEABLE = paper "
                            "prints it, no on-disk source (warning; FATAL in --submission). "
                            "REMOVED_FROM_PAPER = value retired from the manuscript "
                            "(2026-07-11/2026-07-19 retirements); TOMBSTONED: no "
                            "recomputation, counted in the retired total, non-blocking in "
                            "both modes. EXTERNAL_PUBLISHED = cited constant.",
        "required_families": REQUIRED_FAMILIES,
        "paths_relative_to": "repository root",
        "cells": cells,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    print(f"wrote {path} ({len(cells)} cells)")

def verify(manifest_path, tables_path, submission=False):
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    cells = manifest["cells"]
    by_id = {c["cell_id"]: c for c in cells}
    errors, warnings = [], []
    n_ok, n_retired = 0, 0
    for c in cells:
        if c.get("recompute") is None:
            if c["status"] == "UNTRACEABLE":
                warnings.append(
                    f"UNTRACEABLE: [{c['table_id']}] {c['row_label']} -- paper prints "
                    f"'{c['metric']}' with NO on-disk source. {c['notes'][:160]}")
            elif c["status"] == "REMOVED_FROM_PAPER":
                n_retired += 1  # retired provenance record: non-blocking, non-warning
            elif c["status"] == "EXTERNAL_PUBLISHED":
                pass
            else:
                errors.append(f"(c) cell {c['cell_id']} has no source files and no declared status")
            continue
        # gate (a): sources exist
        miss = [s for s in c["source_files"] if not os.path.exists(os.path.join(ROOT, s))]
        if miss:
            errors.append(f"(a) {c['cell_id']}: missing source file(s): {miss}")
            continue
        # recompute from files
        try:
            rec = compute_cell(c)
        except Exception as e:
            errors.append(f"(a) {c['cell_id']}: recompute failed: {e}")
            continue
        # gate (b): drift vs manifest
        stored = c.get("recomputed") or {}
        for k, v in rec.items():
            sv = stored.get(k)
            if sv is None:
                errors.append(f"(b) {c['cell_id']}: component '{k}' absent from manifest")
            elif abs(float(v) - float(sv)) > TOL:
                errors.append(f"(b) {c['cell_id']}.{k}: recomputed {v!r} drifts from "
                              f"manifest {sv!r} by more than {TOL}")
        c["recomputed"] = rec  # use fresh values downstream
        # gate (n): declared-vs-recomputed sample count (audit 2026-07-19 20:57)
        for nk in ("n", "n_units"):
            nv = rec.get(nk)
            if nv is not None and c.get("n_seeds") is not None \
                    and c["status"] not in ("REMOVED_FROM_PAPER", "EXTERNAL_PUBLISHED") \
                    and int(round(float(nv))) != int(c["n_seeds"]):
                errors.append(f"(n) {c['cell_id']}: recomputed {nk}="
                              f"{int(round(float(nv)))} != declared n_seeds {c['n_seeds']}")
        n_ok += 1
    # paper comparison (warning in default mode; FATAL in --submission)
    paper_report = {"exact": [], "within_rounding": [], "MISMATCH": [],
                    "UNTRACEABLE": [], "REMOVED_FROM_PAPER": []}
    for c in cells:
        if c.get("recompute") is None:
            if c["status"] in ("UNTRACEABLE", "REMOVED_FROM_PAPER"):
                paper_report[c["status"]].append(c["cell_id"])
            continue
        checks, cls = check_paper(c, c["recomputed"], by_id)
        c["paper_check"], c["paper_check_class"] = checks, cls
        if cls in paper_report:
            paper_report[cls].append(c["cell_id"])
    mismatch_cells = [
        {"cell_id": c["cell_id"], "table": c["table_id"], "row": c["row_label"],
         "checks": [x for x in c["paper_check"] if x["result"] == "MISMATCH"],
         "notes": c["notes"]}
        for c in cells if c.get("paper_check_class") == "MISMATCH"]
    # --submission fail-closed escalations (audit F1 + F3)
    sub_errors = []
    if submission:
        for c in cells:
            if c["status"] == "UNTRACEABLE":
                sub_errors.append(f"(d) UNTRACEABLE cell {c['cell_id']} [{c['table_id']}] "
                                  f"{c['row_label']}: paper prints '{c['metric']}' with no "
                                  f"on-disk source")
        for m in mismatch_cells:
            det = "; ".join(f"{x['name']}: paper {x['paper']} vs recomputed "
                            f"{x['recomputed']:.6g}" for x in m["checks"])
            sub_errors.append(f"(e) paper MISMATCH {m['cell_id']} [{m['table']}] "
                              f"{m['row']}: {det}")
        sourced = {c["table_id"] for c in cells
                   if c["status"] == "OK" and c.get("source_files")}
        for fam in manifest.get("required_families", REQUIRED_FAMILIES):
            if fam not in sourced:
                sub_errors.append(f"(f) declared paper-claim family '{fam}' has no sourced "
                                  f"cells in the manifest")
    # render tables (only from a fully recomputed cell set)
    if errors:
        tables = {"_error": "tables not rendered: build gates failed", "_gate_errors": errors}
    else:
        try:
            tables = render_tables(cells)
        except Exception as e:  # structurally incomplete manifest (e.g. family stripped)
            errors.append(f"(a) table rendering failed -- manifest structurally "
                          f"incomplete: {type(e).__name__}: {e}")
            tables = {"_error": f"tables not rendered: {type(e).__name__}: {e}"}
    n_warn = len(warnings) + len(mismatch_cells)
    out = {
        "generated_by": "build_hstu_tables.py (recomputed from source artifacts; no cached values)",
        "manifest": os.path.relpath(manifest_path, ROOT),
        "mode": "submission" if submission else "default",
        "gates": {"missing_sources_or_recompute_failures": [e for e in errors if e.startswith("(a)")],
                  "manifest_drift": [e for e in errors if e.startswith("(b)")],
                  "unsourced_cells": [e for e in errors if e.startswith("(c)")]},
        "submission_gate": {
            "enforced": submission,
            "policy": "fail-closed: UNTRACEABLE cells (d), paper-check MISMATCHes (e), and "
                      "missing declared claim families (f) are FATAL in --submission "
                      "(strict resubmission audit 2026-07-11, F1/F3); REMOVED_FROM_PAPER "
                      "and EXTERNAL_PUBLISHED are non-blocking in both modes",
            "violations": sub_errors,
        },
        "warnings_untraceable": warnings,
        "retired_removed_from_paper": paper_report["REMOVED_FROM_PAPER"],
        "paper_check_summary": {k: len(v) for k, v in paper_report.items()},
        "paper_mismatch_cells": mismatch_cells,
        "tables": tables,
    }
    with open(tables_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    # console report
    print(f"mode                : {out['mode']}")
    print(f"cells recomputed OK : {n_ok}")
    if n_retired:
        print(f"retired cells       : {n_retired} REMOVED_FROM_PAPER "
              f"(provenance history; non-blocking)")
    print(f"paper-check         : {out['paper_check_summary']}")
    for w in warnings:
        print("WARNING " + w)
    for m in mismatch_cells:
        det = "; ".join(f"{x['name']}: paper {x['paper']} vs recomputed "
                        f"{x['recomputed']:.6g}" for x in m["checks"])
        print(f"WARNING PAPER MISMATCH [{m['table']}] {m['row']} -> {det}")
    if errors:
        print(f"\nBUILD FAILED ({len(errors)} gate violations):", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
    if submission and sub_errors:
        print(f"\nSUBMISSION GATE FAILED ({len(sub_errors)} violation(s)) -- fail-closed "
              f"per strict resubmission audit F1/F3:", file=sys.stderr)
        for e in sub_errors:
            print("  " + e, file=sys.stderr)
    if errors:
        sys.exit(2)
    if submission and sub_errors:
        sys.exit(3)
    if submission:
        print(f"\nSUBMISSION BUILD GREEN: {n_ok} cells recomputed from source artifacts; "
              f"0 untraceable, 0 paper mismatches, all "
              f"{len(manifest.get('required_families', REQUIRED_FAMILIES))} declared claim "
              f"families sourced; tables written to {tables_path}")
    elif n_warn:
        print(f"\nBUILD OK ({n_warn} warning{'s' if n_warn != 1 else ''}): {n_ok} cells "
              f"recomputed from source artifacts; {len(warnings)} untraceable, "
              f"{len(mismatch_cells)} paper mismatch(es) -- run --submission for the "
              f"fail-closed gate; tables written to {tables_path}")
    else:
        print(f"\nBUILD GREEN: {n_ok} cells recomputed from source artifacts; 0 warnings; "
              f"tables written to {tables_path}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-manifest", action="store_true",
                    help="regenerate the manifest from the embedded spec")
    ap.add_argument("--submission", action="store_true",
                    help="fail-closed publication gate: exit nonzero on any UNTRACEABLE "
                         "cell, any paper-check MISMATCH, or any missing declared claim "
                         "family (audit F1/F3)")
    ap.add_argument("--manifest", default=MANIFEST_PATH)
    ap.add_argument("--tables-out", default=TABLES_PATH)
    a = ap.parse_args()
    if a.write_manifest:
        write_manifest(a.manifest)
    verify(a.manifest, a.tables_out, submission=a.submission)

if __name__ == "__main__":
    main()
