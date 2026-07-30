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
(confirmatory = prospectively pre-declared with required timing/custody intact;
 exploratory = single-seed, post-hoc, outcome-visible, or protocol-deviated).

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
import csv
import hashlib
import json
import math
import os
import re
import sys
import tempfile
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

def sha256_file(rel):
    ap = os.path.join(ROOT, rel)
    h = hashlib.sha256()
    with open(ap, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_lf(rel):
    """SHA-256 after normalizing CRLF to LF, matching frozen text-file rules."""
    ap = os.path.join(ROOT, rel)
    with open(ap, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()

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

def rule_paired_delta_adjudicated(p):
    """Recompute a matched-init paired contrast and bind it to its frozen adjudication."""
    out = rule_paired_delta(p)
    adjud = load(p["adjud"])
    cat = p["category"]
    seeds = [int(s) for s in p["seeds"]]
    if adjud.get("verdict") != p["expect_verdict"]:
        raise ValueError(f"adjudication verdict drift for {cat}")
    if adjud.get("kernel") != p["expect_kernel"] or adjud.get("epochs") != p["expect_epochs"]:
        raise ValueError(f"frozen canonical-FIR configuration drift for {cat}")
    if [int(s) for s in adjud.get("seeds", [])] != seeds:
        raise ValueError(f"adjudication seed drift for {cat}")
    if not adjud.get("passed", {}).get(cat) or not adjud.get("holm", {}).get(cat, {}).get("significant"):
        raise ValueError(f"adjudication no longer records a Holm-significant pass for {cat}")

    for seed, learned_file, identity_file in zip(seeds, p["a"], p["b"]):
        learned, identity = load(learned_file), load(identity_file)
        for arm, expected_mode in ((learned, "learned"), (identity, "frozen")):
            if arm.get("category") != cat or int(arm["config"]["seed"]) != seed:
                raise ValueError(f"category/seed drift for {cat} seed {seed}")
            if arm.get("fir_v3") != expected_mode:
                raise ValueError(f"canonical-FIR arm drift for {cat} seed {seed}")
            if arm.get("fir_v3_kernel") != p["expect_kernel"] or \
                    arm["config"].get("epochs") != p["expect_epochs"]:
                raise ValueError(f"canonical-FIR run configuration drift for {cat} seed {seed}")
        if learned.get("init_state_sha256") != identity.get("init_state_sha256"):
            raise ValueError(f"matched-initialization failure for {cat} seed {seed}")
        recorded_hashes = adjud["init_hash_by_cat_seed"][cat][str(seed)]
        if recorded_hashes.get("a1learned") != learned.get("init_state_sha256") or \
                recorded_hashes.get("a0ident") != identity.get("init_state_sha256"):
            raise ValueError(f"adjudicated initialization hash drift for {cat} seed {seed}")
        if abs(float(identity.get("fir_v3_final_l2", float("nan")))) > 1e-12:
            raise ValueError(f"identity arm moved from delta=0 for {cat} seed {seed}")

    recorded = adjud["per_category"][cat]
    expected = {
        "mean": float(recorded["paired_mean"]),
        "ci_lo": float(recorded["paired_ci"][0]),
        "ci_hi": float(recorded["paired_ci"][1]),
        "t": float(recorded["paired_t"]),
        "pos": int(recorded["sign_pos"]),
    }
    for name, value in expected.items():
        if abs(float(out[name]) - value) > 1e-12:
            raise ValueError(f"adjudicated {name} drift for {cat}: {out[name]} != {value}")
    out["paired_p"] = t_two_sided_p(out["t"], out["n"] - 1)
    if abs(out["paired_p"] - float(recorded["paired_p"])) > 1e-12:
        raise ValueError(f"adjudicated paired-p drift for {cat}")
    out["holm_significant"] = 1.0
    out["passed"] = 1.0
    return out

def rule_fir_control_contrast(p):
    """Recompute one sealed FIR active-control contrast and bind it to adjudication.

    Unlike the ordinary training JSONs, this campaign kept TEST sealed until a
    one-shot final evaluation.  The endpoint therefore lives under ``test`` in
    the ``*.finaleval.json`` records rather than under ``best_test``.
    """
    def endpoint(rel, expected_arm, expected_seed):
        rec = load(rel)
        if (rec.get("protocol") != "PREREG_FIR_CONTROLS"
                or rec.get("category") != "Musical_Instruments"
                or rec.get("arm") != expected_arm
                or int(rec.get("seed", -1)) != int(expected_seed)):
            raise ValueError(f"FIR-control final-evaluation binding drift in {rel}")
        selected = int(rec.get("selected_epoch", -1))
        if not (1 <= selected <= 20):
            raise ValueError(f"FIR-control selected-epoch out of range in {rel}")
        train_rel = rel.replace(".finaleval.json", ".json")
        train = load(train_rel)
        history = train.get("history", [])
        selected_rows = [row for row in history if int(row.get("epoch", -1)) == selected]
        selected_val = float(rec.get("selected_val_NDCG10"))
        max_val = max(float(row["val"]["NDCG@10"]) for row in history)
        if (train.get("best_test") is not None or len(selected_rows) != 1
                or abs(float(selected_rows[0]["val"]["NDCG@10"]) - selected_val) > 1e-12
                or abs(float(train.get("best_val_NDCG10")) - selected_val) > 1e-12
                or abs(max_val - selected_val) > 1e-12):
            raise ValueError(f"FIR-control validation selection binding drift in {rel}")
        value = rec.get("test", {}).get("NDCG@10")
        if value is None or not math.isfinite(float(value)):
            raise ValueError(f"FIR-control endpoint missing/nonfinite in {rel}")
        return float(value)

    seeds = [int(s) for s in p["seeds"]]
    av = [endpoint(f, p["a_arm"], s) for f, s in zip(p["a"], seeds)]
    bv = [endpoint(f, p["b_arm"], s) for f, s in zip(p["b"], seeds)]
    out = paired_stats([a - b for a, b in zip(av, bv)])

    adjud = load(p["adjud"])
    if (adjud.get("protocol") != "PREREG_FIR_CONTROLS"
            or adjud.get("verdict") != "CTRL-ACTIVE-CONTROL-SUPPORTED"
            or adjud.get("category") != "Musical_Instruments"
            or int(adjud.get("kernel", -1)) != 16
            or [int(s) for s in adjud.get("seeds", [])] != seeds):
        raise ValueError("FIR-control frozen adjudication metadata drift")
    family = adjud[p["family"]]
    holm = adjud[p["holm"]]
    recorded = family[p["contrast"]]
    decision = holm[p["contrast"]]
    expected = {
        "mean": float(recorded["mean"]), "sd": float(recorded["sd"]),
        "t": float(recorded["t"]), "ci_lo": float(recorded["ci95"][0]),
        "ci_hi": float(recorded["ci95"][1]),
    }
    for name, value in expected.items():
        if abs(float(out[name]) - value) > 1e-12:
            raise ValueError(f"FIR-control adjudicated {name} drift for "
                             f"{p['contrast']}: {out[name]} != {value}")
    out["paired_p"] = t_two_sided_p(out["t"], out["n"] - 1)
    if abs(out["paired_p"] - float(recorded["p"])) > 1e-12:
        raise ValueError(f"FIR-control paired-p drift for {p['contrast']}")
    out["holm_p"] = float(decision["p_holm"])
    out["holm_reject"] = 1.0 if decision["reject"] else 0.0
    return out

def rule_fir_pointwise_contrast(p):
    """Recompute the sealed FIR-vs-pointwise placebo contrast and bind its verdict."""
    def endpoint(rel, expected_arm, expected_seed):
        rec = load(rel)
        if (rec.get("protocol") != "PREREG_FIR_POINTWISE_V1"
                or rec.get("category") != "Musical_Instruments"
                or rec.get("arm") != expected_arm
                or int(rec.get("seed", -1)) != int(expected_seed)):
            raise ValueError(f"FIR-pointwise final-evaluation binding drift in {rel}")
        selected = int(rec.get("selected_epoch", -1))
        if not (1 <= selected <= 20):
            raise ValueError(f"FIR-pointwise selected-epoch out of range in {rel}")
        train_rel = rel.replace(".finaleval.json", ".json")
        train = load(train_rel)
        history = train.get("history", [])
        selected_rows = [row for row in history if int(row.get("epoch", -1)) == selected]
        selected_val = float(rec.get("selected_val_NDCG10"))
        max_val = max(float(row["val"]["NDCG@10"]) for row in history)
        if (train.get("best_test") is not None or len(selected_rows) != 1
                or abs(float(selected_rows[0]["val"]["NDCG@10"]) - selected_val) > 1e-12
                or abs(float(train.get("best_val_NDCG10")) - selected_val) > 1e-12
                or abs(max_val - selected_val) > 1e-12):
            raise ValueError(f"FIR-pointwise validation selection binding drift in {rel}")
        value = rec.get("test", {}).get("NDCG@10")
        if value is None or not math.isfinite(float(value)):
            raise ValueError(f"FIR-pointwise endpoint missing/nonfinite in {rel}")
        return float(value)

    seeds = [int(s) for s in p["seeds"]]
    av = [endpoint(f, p["a_arm"], s) for f, s in zip(p["a"], seeds)]
    bv = [endpoint(f, p["b_arm"], s) for f, s in zip(p["b"], seeds)]
    out = paired_stats([a - b for a, b in zip(av, bv)])

    adjud = load(p["adjud"])
    if (adjud.get("protocol") != "PREREG_FIR_POINTWISE_V1"
            or adjud.get("verdict") != "POINTWISE-FIR-DISCRIMINATED"
            or adjud.get("scope") != "internal outcome-known parameter-matched placebo study"
            or adjud.get("category") != "Musical_Instruments"
            or int(adjud.get("kernel_or_width", -1)) != 16
            or [int(s) for s in adjud.get("seeds", [])] != seeds
            or int(adjud.get("n_trainable_params", {}).get("learned", -1))
               != int(adjud.get("n_trainable_params", {}).get("pointwise", -2))):
        raise ValueError("FIR-pointwise frozen adjudication metadata drift")
    recorded = adjud["contrasts"][p["contrast"]]
    decision = adjud["holm"][p["contrast"]]
    expected = {
        "mean": float(recorded["mean"]), "sd": float(recorded["sd"]),
        "t": float(recorded["t"]), "ci_lo": float(recorded["ci95"][0]),
        "ci_hi": float(recorded["ci95"][1]),
    }
    for name, value in expected.items():
        if abs(float(out[name]) - value) > 1e-12:
            raise ValueError(f"FIR-pointwise adjudicated {name} drift for "
                             f"{p['contrast']}: {out[name]} != {value}")
    out["paired_p"] = t_two_sided_p(out["t"], out["n"] - 1)
    if abs(out["paired_p"] - float(recorded["p"])) > 1e-12:
        raise ValueError(f"FIR-pointwise paired-p drift for {p['contrast']}")
    out["holm_p"] = float(decision["p_holm"])
    out["holm_reject"] = 1.0 if decision["reject"] else 0.0
    return out

def rule_fir_prospective_sw_v3_contrast(p):
    """Recompute and fully bind the prospective Software FIR contrast."""
    adjud = load(p["adjud"])
    seeds = [int(s) for s in p["seeds"]]
    if (adjud.get("protocol") != "PREREG_FIR_PROSPECTIVE_SW_V3"
            or adjud.get("verdict") != "SW-V3-PRACTICAL-POS"
            or adjud.get("scope") != ("prospective same-investigator, same-code-lineage, "
                                      "same-Amazon-family category attempt; not independent "
                                      "confirmation")
            or adjud.get("custody_scope") != ("local same-user operational first-reader "
                                               "handoff; no external escrow or independent "
                                               "custody")
            or adjud.get("category") != "Software"
            or [int(s) for s in adjud.get("seeds", [])] != seeds
            or abs(float(adjud.get("alpha", -1)) - 0.05) > 1e-15
            or abs(float(adjud.get("practical_threshold", -1)) - 0.0005) > 1e-15):
        raise ValueError("Software V3 prospective adjudication metadata drift")

    state_hashes = {
        p["attempt"]: adjud["attempt_sha256"],
        p["ready"]: adjud["ready_sha256"],
        p["endpoints_complete"]: adjud["endpoints_complete_sha256"],
    }
    for rel, expected in state_hashes.items():
        if sha256_file(rel) != expected:
            raise ValueError(f"Software V3 state-artifact hash drift in {rel}")
        state = load(rel)
        if state.get("protocol") != "PREREG_FIR_PROSPECTIVE_SW_V3":
            raise ValueError(f"Software V3 state-artifact protocol drift in {rel}")
    status = load(p["status"])
    if (status.get("protocol") != "PREREG_FIR_PROSPECTIVE_SW_V3"
            or status.get("state") != "complete"
            or int(status.get("trained", -1)) != 16
            or int(status.get("evaluated", -1)) != 16
            or int(status.get("adjudicated", -1)) != 1):
        raise ValueError("Software V3 terminal status drift")

    evidence = adjud.get("evidence", {})
    backbone = adjud.get("backbone_hashes", {})
    values = {"learned": [], "identity": []}
    for arm in ("learned", "identity"):
        for rel, seed in zip(p[arm], seeds):
            key = f"{arm}:{seed}"
            ev = evidence.get(key, {})
            rec = load(rel)
            if (rec.get("protocol") != "PREREG_FIR_PROSPECTIVE_SW_V3"
                    or rec.get("category") != "Software"
                    or rec.get("arm") != arm
                    or int(rec.get("seed", -1)) != seed
                    or int(rec.get("test", {}).get("n_eval", -1)) != 146396
                    or sha256_file(rel) != ev.get("finaleval_sha256")):
                raise ValueError(f"Software V3 sealed endpoint binding drift in {rel}")
            selected = int(rec.get("selected_epoch", -1))
            train_rel = rel.replace(".finaleval.json", ".json")
            train = load(train_rel)
            history = train.get("history", [])
            rows = [row for row in history if int(row.get("epoch", -1)) == selected]
            selected_val = float(rec.get("selected_val_NDCG10"))
            if (not 1 <= selected <= 20 or train.get("best_test") is not None
                    or len(rows) != 1
                    or abs(float(rows[0]["val"]["NDCG@10"]) - selected_val) > 1e-12
                    or abs(float(train.get("best_val_NDCG10")) - selected_val) > 1e-12
                    or abs(max(float(row["val"]["NDCG@10"]) for row in history)
                           - selected_val) > 1e-12
                    or sha256_file(train_rel) != ev.get("run_json_sha256")
                    or train.get("best_ckpt_sha256") != ev.get("checkpoint_sha256")
                    or train.get("backbone_init_sha256")
                       != backbone.get(str(seed), {}).get(arm)):
                raise ValueError(f"Software V3 training/selection binding drift in {rel}")
            prov = rec.get("provenance", {})
            if (prov.get("protocol") != "PREREG_FIR_PROSPECTIVE_SW_V3"
                    or prov.get("execution_git_tag") != "fir-prospective-sw-v3-freeze"
                    or prov.get("execution_git_head") != adjud.get("execution_git_head")
                    or prov.get("run_json_sha256") != ev.get("run_json_sha256")
                    or prov.get("checkpoint_sha256") != ev.get("checkpoint_sha256")
                    or prov.get("users_sidecar_sha256") != ev.get("users_sha256")
                    or prov.get("started_seal_sha256") != ev.get("seal_sha256")):
                raise ValueError(f"Software V3 endpoint provenance drift in {rel}")
            sidecar = rel.replace(".finaleval.json", ".finaleval.users.npz")
            seal = rel.replace(".finaleval.json", ".finaleval.started.json")
            if (sha256_file(sidecar) != ev.get("users_sha256")
                    or sha256_file(seal) != ev.get("seal_sha256")):
                raise ValueError(f"Software V3 sealed sidecar/hash drift for {rel}")
            value = rec.get("test", {}).get("NDCG@10")
            if value is None or not math.isfinite(float(value)):
                raise ValueError(f"Software V3 endpoint missing/nonfinite in {rel}")
            values[arm].append(float(value))

    for seed in seeds:
        h = backbone.get(str(seed), {})
        if not h.get("learned") or h.get("learned") != h.get("identity"):
            raise ValueError(f"Software V3 matched-backbone hash drift for seed {seed}")
    out = paired_stats([a - b for a, b in zip(values["learned"], values["identity"])])
    out["learned_mean"] = mean(values["learned"])
    out["identity_mean"] = mean(values["identity"])
    out["paired_p"] = t_two_sided_p(out["t"], out["n"] - 1)
    deltas = [a - b for a, b in zip(values["learned"], values["identity"])]
    # Exact two-sided sign sensitivity.  This is deliberately descriptive and
    # does not replace the frozen paired-t decision rule; it shows how the
    # small-n conclusion changes when only signs, not normality, are used.
    n_positive = sum(d > 0.0 for d in deltas)
    n_negative = sum(d < 0.0 for d in deltas)
    nonzero = n_positive + n_negative
    tail = min(n_positive, n_negative)
    out["sign_p_two_sided"] = min(
        1.0,
        2.0 * sum(math.comb(nonzero, k) for k in range(tail + 1))
        / (2.0 ** nonzero),
    )
    out["n_positive"] = float(n_positive)
    for i, delta in enumerate(deltas, start=1):
        out[f"delta_{i}"] = delta
    with open(os.path.join(ROOT, p["figure_data"]), newline="", encoding="utf-8") as fp:
        figure_rows = list(csv.DictReader(fp))
    if len(figure_rows) != len(seeds):
        raise ValueError("Software V3 figure-data row-count drift")
    for row, seed, ident, learn, delta in zip(
            figure_rows, seeds, values["identity"], values["learned"], deltas):
        if (int(row["seed"]) != seed
                or abs(float(row["identity_ndcg10"]) - ident) > 5e-13
                or abs(float(row["learned_ndcg10"]) - learn) > 5e-13
                or abs(float(row["delta_ndcg10"]) - delta) > 5e-13):
            raise ValueError(f"Software V3 figure-data drift for seed {seed}")
    primary = adjud["primary_contrast"]
    expected = {
        "mean": primary["mean"], "sd": primary["sd"], "t": primary["t"],
        "ci_lo": primary["ci95"][0], "ci_hi": primary["ci95"][1],
        "paired_p": primary["p_two_sided"],
        "learned_mean": adjud["means"]["learned"],
        "identity_mean": adjud["means"]["identity"],
    }
    for name, value in expected.items():
        if abs(float(out[name]) - float(value)) > 1e-12:
            raise ValueError(f"Software V3 adjudicated {name} drift")
    out["practical_pass"] = 1.0 if (out["ci_lo"] > 0.0005
                                           and out["paired_p"] < 0.05) else 0.0
    if out["practical_pass"] != 1.0:
        raise ValueError("Software V3 practical-effect verdict no longer reproduces")
    return out

def rule_fir_evidence_summary(p):
    """Bind the cross-adjudication evidence-map CSV to its source records."""
    mi = load(p["mi"])
    breadth = load(p["breadth"])
    controls = load(p["controls"])
    pointwise = load(p["pointwise"])
    software = load(p["software"])
    ml1m = load(p["ml1m"])
    if (mi.get("verdict") != "W-POS"
            or breadth.get("verdict") != "CANON-BREADTH-POS"
            or controls.get("verdict") != "CTRL-ACTIVE-CONTROL-SUPPORTED"
            or pointwise.get("verdict") != "POINTWISE-FIR-DISCRIMINATED"
            or software.get("verdict") != "SW-V3-PRACTICAL-POS"
            or ml1m.get("verdict") != "ML1M-NO-FIR-REPLICATION"):
        raise ValueError("FIR evidence-map source verdict drift")
    primary = next(
        row for row in mi["contrasts"] if row["contrast"] == "A1-A0 (PRIMARY)"
    )
    expected = [
        ("Outcome-known internal Amazon", "MI: learned - identity",
         primary["est"], primary["ci"][0], primary["ci"][1],
         "fir_v3_adjudication.json", "contrasts/A1-A0 (PRIMARY)",
         "outcome-known internal; Welch interval"),
    ]
    for category, label in (
            ("Industrial_and_Scientific", "Industrial: learned - identity"),
            ("CDs_and_Vinyl", "CDs: learned - identity")):
        record = breadth["per_category"][category]
        expected.append((
            "Outcome-known internal Amazon", label,
            record["paired_mean"], record["paired_ci"][0], record["paired_ci"][1],
            "fir_canonical_breadth_adjudication.json", f"per_category/{category}",
            "outcome-known internal; paired-t interval",
        ))
    record = software["primary_contrast"]
    expected.append((
        "Outcome-known internal Amazon", "Software: learned - identity",
        record["mean"], record["ci95"][0], record["ci95"][1],
        "fir_prospective_sw_v3_adjudication.json", "primary_contrast",
        "outcome-known same-team robustness; paired-t interval",
    ))
    record = pointwise["contrasts"]["learned-pointwise"]
    expected.append((
        "Matched MI control boundaries", "Learned - pointwise FIR",
        record["mean"], record["ci95"][0], record["ci95"][1],
        "fir_pointwise_v1_adjudication.json", "contrasts/learned-pointwise",
        "outcome-known internal; paired-t interval",
    ))
    record = controls["family_b"]["learned-shared"]
    expected.append((
        "Matched MI control boundaries", "Learned - shared filter",
        record["mean"], record["ci95"][0], record["ci95"][1],
        "fir_controls_adjudication.json", "family_b/learned-shared",
        "outcome-known internal; paired-t interval",
    ))
    for key, label in (("learned-identity", "Learned - identity"),
                       ("learned-pointwise", "Learned - pointwise FIR")):
        record = ml1m["replication"][key]
        expected.append((
            "Prospectively frozen MovieLens transfer", label,
            record["mean"], record["ci"][0], record["ci"][1],
            "fir_efficiency_ml1m_v1_adjudication.json", f"replication/{key}",
            "prospectively frozen same-investigator; paired-t interval",
        ))

    with open(os.path.join(ROOT, p["figure_data"]), newline="", encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    if len(rows) != len(expected):
        raise ValueError("FIR evidence-map row-count drift")
    positive_excluding_zero = 0
    intervals_including_zero = 0
    for index, (row, exp) in enumerate(zip(rows, expected), start=1):
        group, label, est, low, high, source_file, source_key, scope = exp
        if (row.get("group") != group or row.get("label") != label
                or row.get("source_file") != source_file
                or row.get("source_key") != source_key
                or row.get("evidence_scope") != scope):
            raise ValueError(f"FIR evidence-map metadata drift in row {index}")
        for key, value in (("estimate", est), ("ci_low", low), ("ci_high", high)):
            if abs(float(row[key]) - float(value)) > 5e-12:
                raise ValueError(f"FIR evidence-map {key} drift in row {index}")
        positive_excluding_zero += int(float(low) > 0.0)
        intervals_including_zero += int(float(low) <= 0.0 <= float(high))
    return {
        "rows": float(len(rows)),
        "positive_excluding_zero": float(positive_excluding_zero),
        "intervals_including_zero": float(intervals_including_zero),
    }


def rule_fir_efficiency_ml1m_v1_aggregate(p):
    """Recompute the public aggregate ML-1M verdict and resource figure.

    Record-level MovieLens inputs, sealed endpoints, checkpoints, and per-user
    sidecars cannot be redistributed.  This rule therefore fails closed over the
    public adjudication's aggregate seed vectors and frozen-code hashes.  It
    independently recomputes the published means, paired intervals, Holm
    decisions, noninferiority bounds, and every figure-data row, but does not
    claim an independent replay of the private endpoint extraction.
    """
    adjud = load(p["adjud"])
    seeds = [int(s) for s in p["seeds"]]
    arms = list(p["arms"])
    if (adjud.get("protocol") != "PREREG_FIR_EFFICIENCY_ML1M_V1"
            or adjud.get("verdict") != "ML1M-NO-FIR-REPLICATION"
            or adjud.get("scope") != ("prospectively frozen same-investigator "
                                       "non-Amazon robustness and efficiency study")
            or adjud.get("not_independent_confirmation") is not True
            or adjud.get("primary_category") != "MovieLens1M_R4"
            or [int(s) for s in adjud.get("seeds", [])] != seeds
            or list(adjud.get("arms", [])) != arms
            or abs(float(adjud.get("alpha", -1)) - 0.05) > 1e-15
            or abs(float(adjud.get("noninferiority_margin_ndcg10", -1))
                   - 0.0005) > 1e-15):
        raise ValueError("MovieLens FIR-efficiency adjudication metadata drift")

    for role, rel in p["frozen_files"].items():
        expected = adjud.get("frozen_sha256_lf", {}).get(role)
        if not expected or sha256_lf(rel) != expected:
            raise ValueError(f"MovieLens FIR-efficiency frozen {role} hash drift")

    values = adjud.get("primary_values", {})
    if any(len(values.get(arm, [])) != len(seeds) for arm in arms):
        raise ValueError("MovieLens FIR-efficiency primary seed-vector drift")
    out = {"n_units": float(len(seeds)), "negative_verdict": 1.0}
    for arm in arms:
        observed = [float(x) for x in values[arm]]
        arm_mean = mean(observed)
        if abs(arm_mean - float(adjud["primary_means"][arm])) > 1e-12:
            raise ValueError(f"MovieLens FIR-efficiency {arm} mean drift")
        out[f"mean_{arm}"] = arm_mean

    def paired_from_vectors(a, b):
        result = paired_stats([float(x) - float(y) for x, y in zip(a, b)])
        result["p_two_sided"] = t_two_sided_p(result["t"], result["n"] - 1)
        return result

    replication_raw = {}
    for contrast, a_arm, b_arm in (
            ("learned-identity", "learned", "identity"),
            ("learned-pointwise", "learned", "pointwise")):
        rec = paired_from_vectors(values[a_arm], values[b_arm])
        recorded = adjud["replication"][contrast]
        expected = {
            "mean": recorded["mean"], "sd": recorded["sd"],
            "t": recorded["t"], "ci_lo": recorded["ci"][0],
            "ci_hi": recorded["ci"][1], "p_two_sided": recorded["p_two_sided"],
        }
        for name, expected_value in expected.items():
            if abs(float(rec[name]) - float(expected_value)) > 1e-12:
                raise ValueError(f"MovieLens replication {contrast} {name} drift")
        replication_raw[contrast] = rec["p_two_sided"]
        prefix = contrast.replace("-", "_")
        for name in ("mean", "sd", "t", "ci_lo", "ci_hi", "p_two_sided"):
            out[f"{prefix}_{name}"] = float(rec[name])

    def holm(raw):
        ordered = sorted(raw, key=raw.get)
        running, adjusted = 0.0, {}
        for index, name in enumerate(ordered):
            running = max(running, (len(ordered) - index) * raw[name])
            adjusted[name] = min(1.0, running)
        return adjusted

    for contrast, p_holm in holm(replication_raw).items():
        recorded = adjud["replication_holm"][contrast]
        reject = p_holm < 0.05
        if (abs(p_holm - float(recorded["p_holm"])) > 1e-12
                or reject != bool(recorded["reject"])
                or bool(adjud["replication_positive"][contrast]) != reject):
            raise ValueError(f"MovieLens replication Holm decision drift for {contrast}")
        prefix = contrast.replace("-", "_")
        out[f"{prefix}_p_holm"] = p_holm
        out[f"{prefix}_reject"] = float(reject)

    ni_raw = {}
    for candidate in ("shared", "grouped", "lowrank"):
        deltas = [float(x) - float(y)
                  for x, y in zip(values[candidate], values["learned"])]
        n, mu, sd = len(deltas), mean(deltas), sstd(deltas)
        se = sd / math.sqrt(n)
        t_margin = (mu + 0.0005) / se
        p_one_sided = t_sf(t_margin, n - 1)
        simultaneous_lower = mu - t_ppf(1.0 - 0.05 / 3.0, n - 1) * se
        recorded = adjud["noninferiority"][candidate]
        expected = {
            "mean": mu, "sd": sd, "t_margin": t_margin,
            "p_one_sided": p_one_sided,
            "simultaneous_lower": simultaneous_lower,
        }
        for name, value in expected.items():
            if abs(float(recorded[name]) - float(value)) > 1e-12:
                raise ValueError(f"MovieLens noninferiority {candidate} {name} drift")
        ni_raw[candidate] = p_one_sided
        out[f"{candidate}_minus_learned"] = mu
        out[f"{candidate}_simultaneous_lower"] = simultaneous_lower

    for candidate, p_holm in holm(ni_raw).items():
        recorded = adjud["noninferiority_holm"][candidate]
        passed = p_holm < 0.05 and out[f"{candidate}_simultaneous_lower"] > -0.0005
        if (abs(p_holm - float(recorded["p_holm"])) > 1e-12
                or passed != bool(recorded["reject"])
                or passed != bool(adjud["noninferiority_pass"][candidate])):
            raise ValueError(f"MovieLens noninferiority Holm decision drift for {candidate}")
        out[f"{candidate}_ni_p_holm"] = p_holm
        out[f"{candidate}_ni_pass"] = float(passed)

    all_view = adjud["all_ratings_sensitivity"]
    for contrast, key in (("all_learned_identity", "learned_minus_identity"),
                          ("all_learned_pointwise", "learned_minus_pointwise")):
        rec = all_view[key]
        out[f"{contrast}_mean"] = float(rec["mean"])
        out[f"{contrast}_ci_lo"] = float(rec["ci"][0])
        out[f"{contrast}_ci_hi"] = float(rec["ci"][1])

    cluster_zero_count = 0
    for candidate, sensitivity in adjud["cluster_sensitivities"].items():
        for interval_name in ("user_cluster_percentile_ci95",
                              "item_cluster_percentile_ci95"):
            low, high = map(float, sensitivity[interval_name])
            cluster_zero_count += int(low <= 0.0 <= high)
    out["cluster_intervals_including_zero"] = float(cluster_zero_count)

    resource = adjud["resource_summary"]["MovieLens1M_R4"]
    with open(os.path.join(ROOT, p["figure_data"]), newline="", encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    if [row.get("arm") for row in rows] != arms:
        raise ValueError("MovieLens FIR-efficiency figure-data arm order drift")
    for row in rows:
        arm = row["arm"]
        expected = {
            "filter_trainable_params": adjud["filter_trainable_parameters"][arm],
            "mean_ndcg10": adjud["primary_means"][arm],
            "flops_per_user_median": resource[arm]["flops_per_user_median"],
            "latency_ms_median": resource[arm]["latency_ms_median_across_seeds"],
            "inference_peak_mib_median":
                resource[arm]["inference_peak_cuda_memory_bytes_median"] / 2**20,
            "training_peak_mib_median":
                resource[arm]["training_peak_cuda_memory_bytes_median"] / 2**20,
            "training_wall_time_s_median":
                resource[arm]["training_wall_time_s_median"],
        }
        for name, value in expected.items():
            if abs(float(row[name]) - float(value)) > 5e-12:
                raise ValueError(f"MovieLens FIR-efficiency figure {arm}.{name} drift")
            out[f"{arm}_{name}"] = float(value)

    with open(os.path.join(ROOT, p["cohort_flow_data"]), newline="", encoding="utf-8") as fp:
        cohort_rows = list(csv.DictReader(fp))
    view_names = ["MovieLens1M_R4", "MovieLens1M_ALL"]
    if [row.get("view") for row in cohort_rows] != view_names:
        raise ValueError("MovieLens cohort-flow view order drift")
    views = adjud["data_provenance"]["views"]
    for row, view_name in zip(cohort_rows, view_names):
        view = views[view_name]
        expected = {
            "minimum_rating": view["minimum_rating"],
            "time_fraction": view["time_fraction"],
            "cutoff_timestamp_s": view["cutoff_timestamp_s"],
            "filtered_events": view["n_filtered_events"],
            "candidate_users": view["n_candidate_users"],
            "retained_users": view["n_users"],
            "train_catalog_items": view["n_train_catalog_items"],
            "train_rows": view["n_rows"]["train"],
            "valid_rows": view["n_rows"]["valid"],
            "test_rows": view["n_rows"]["test"],
        }
        for name, value in expected.items():
            if abs(float(row[name]) - float(value)) > 5e-12:
                raise ValueError(f"MovieLens cohort-flow {view_name}.{name} drift")
    out["cohort_views"] = float(len(cohort_rows))
    out["primary_candidate_users"] = float(views["MovieLens1M_R4"]["n_candidate_users"])
    out["primary_retained_users"] = float(views["MovieLens1M_R4"]["n_users"])
    return out

def rule_wearec_v1_aggregate(p):
    """Recompute the public WEARec aggregate without replaying private endpoints.

    The sealed TEST endpoints and per-user rank sidecars are private.  The public
    graph therefore starts from the adjudicator-released NDCG@10 vectors, verifies
    the six pre-existing Git-backed reference artifacts using the repository's
    LF-normalized text identity rule, and independently
    recomputes both one-sample summaries and the descriptive Welch contrast.  This
    is an aggregate arithmetic replay, not independent endpoint extraction.
    """
    adjud = load(p["adjud"])
    seeds = [int(s) for s in p["seeds"]]
    expected_boundary = (
        "official 2026 WEARec model/training code under the paper's shared split, "
        "full-catalog mask, and tie rule; not independent confirmation, SOTA, a "
        "paired experiment, or equal tuning budgets"
    )
    if (adjud.get("protocol") != "PREREG_WEAREC_BASELINE_V1"
            or adjud.get("evidence_class") != (
                "prospectively frozen execution on an outcome-known split by the "
                "same investigators")
            or adjud.get("claim_boundary") != expected_boundary
            or adjud.get("upstream", {}).get("url") !=
                "https://github.com/xhy963319431/WEARec.git"
            or adjud.get("upstream", {}).get("commit") !=
                "2087335339b1ead87da6e066ce14e2d33880a95e"
            or [int(s) for s in adjud.get("assessment_seeds", [])] != seeds
            or adjud.get("selected_preset") not in
                {"official_sports", "official_beauty"}
            or set(adjud.get("validation_selection", {})) !=
                {"official_sports", "official_beauty"}):
        raise ValueError("WEARec V1 adjudication metadata drift")

    vectors = adjud.get("vectors", {})
    wearec = [float(x) for x in vectors.get("wearec_ndcg10", [])]
    reference = [float(x) for x in vectors.get("existing_reference_ndcg10", [])]
    if len(wearec) != len(seeds) or len(reference) != len(p["reference_files"]):
        raise ValueError("WEARec V1 released aggregate-vector drift")

    recorded_hashes = adjud.get("reference_sha256", {})
    normalized_hashes = p["reference_lf_sha256"]
    for rel in p["reference_files"]:
        name = os.path.basename(rel)
        raw_ok = sha256_file(rel) == recorded_hashes.get(name)
        lf_ok = sha256_lf(rel) == normalized_hashes.get(name)
        if not (raw_ok or lf_ok):
            raise ValueError(f"WEARec V1 reference identity drift: {name}")
    artifact_reference = [bt_metric(rel, "NDCG@10")
                          for rel in p["reference_files"]]
    if any(abs(a - b) > 1e-15
           for a, b in zip(artifact_reference, reference)):
        raise ValueError("WEARec V1 reference vector does not match source artifacts")

    def summarize(values):
        n = len(values)
        mu = mean(values)
        sd = sstd(values)
        half = t_ppf(0.975, n - 1) * sd / math.sqrt(n)
        return {"n": float(n), "mean": mu, "sd": sd,
                "ci_lo": mu - half, "ci_hi": mu + half}

    def verify_summary(label, recomputed, recorded):
        expected = {"n": recorded["n"], "mean": recorded["mean"],
                    "sd": recorded["sd"], "ci_lo": recorded["ci95"][0],
                    "ci_hi": recorded["ci95"][1]}
        for key, value in expected.items():
            if abs(float(recomputed[key]) - float(value)) > 1e-12:
                raise ValueError(f"WEARec V1 {label} {key} drift")

    w = summarize(wearec)
    r = summarize(reference)
    verify_summary("WEARec", w, adjud["wearec_ndcg10"])
    verify_summary("existing reference", r,
                   adjud["existing_full_model_reference_ndcg10"])

    va = w["sd"] ** 2 / len(wearec)
    vb = r["sd"] ** 2 / len(reference)
    se = math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va * va / (len(wearec) - 1)
                            + vb * vb / (len(reference) - 1))
    delta = w["mean"] - r["mean"]
    t_value = delta / se
    half = t_ppf(0.975, df) * se
    contrast = {"delta": delta, "se": se, "t": t_value, "df": df,
                "p_two_sided_unadjusted": t_two_sided_p(t_value, df),
                "ci_lo": delta - half, "ci_hi": delta + half}
    recorded = adjud["descriptive_welch_contrast"]
    expected = {
        "delta": recorded["delta"], "se": recorded["se"],
        "t": recorded["t"], "df": recorded["df"],
        "p_two_sided_unadjusted": recorded["p_two_sided_unadjusted"],
        "ci_lo": recorded["ci95_unadjusted"][0],
        "ci_hi": recorded["ci95_unadjusted"][1],
    }
    for key, value in expected.items():
        if abs(float(contrast[key]) - float(value)) > 1e-12:
            raise ValueError(f"WEARec V1 descriptive Welch {key} drift")

    if contrast["ci_lo"] > 0.0:
        verdict = "WEAREC-ABOVE-EXISTING-REFERENCE"
    elif contrast["ci_hi"] < 0.0:
        verdict = "WEAREC-BELOW-EXISTING-REFERENCE"
    else:
        verdict = "WEAREC-REFERENCE-OVERLAP"
    if adjud.get("verdict") != verdict:
        raise ValueError("WEARec V1 verdict drift")

    resources = adjud.get("resources", [])
    if ([int(row.get("seed", -1)) for row in resources] != seeds
            or len({int(row.get("n_params", -1)) for row in resources}) != 1):
        raise ValueError("WEARec V1 resource-vector drift")

    def median(values):
        ordered = sorted(float(x) for x in values)
        mid = len(ordered) // 2
        return (ordered[mid] if len(ordered) % 2
                else 0.5 * (ordered[mid - 1] + ordered[mid]))

    endpoint_hashes = adjud.get("endpoint_sha256", {})
    if (set(endpoint_hashes) != {str(seed) for seed in seeds}
            or any(not re.fullmatch(r"[0-9a-f]{64}", str(value))
                   for value in endpoint_hashes.values())):
        raise ValueError("WEARec V1 private endpoint-hash ledger drift")

    out = {
        "n_units": float(len(wearec)),
        "wearec_mean": w["mean"], "wearec_sd": w["sd"],
        "wearec_ci_lo": w["ci_lo"], "wearec_ci_hi": w["ci_hi"],
        "reference_mean": r["mean"], "reference_sd": r["sd"],
        "reference_ci_lo": r["ci_lo"], "reference_ci_hi": r["ci_hi"],
        "delta": contrast["delta"], "delta_ci_lo": contrast["ci_lo"],
        "delta_ci_hi": contrast["ci_hi"],
        "p_two_sided_unadjusted": contrast["p_two_sided_unadjusted"],
        "welch_df": contrast["df"],
        "verdict_above": float(verdict == "WEAREC-ABOVE-EXISTING-REFERENCE"),
        "verdict_below": float(verdict == "WEAREC-BELOW-EXISTING-REFERENCE"),
        "verdict_overlap": float(verdict == "WEAREC-REFERENCE-OVERLAP"),
        "n_params": float(resources[0]["n_params"]),
        "best_epoch_median": median(row["best_epoch"] for row in resources),
        "train_seconds_median": median(row["train_seconds"] for row in resources),
        "peak_cuda_mib_median": median(row["peak_cuda_memory_bytes"] for row in resources) / 2**20,
        "eval_seconds_median": median(row["eval_seconds"] for row in resources),
        "private_endpoint_count": float(len(endpoint_hashes)),
        "private_endpoint_replay": 0.0,
    }
    for index, value in enumerate(wearec, start=1):
        out[f"wearec_seed_{index}"] = value
    for index, value in enumerate(reference, start=1):
        out[f"reference_seed_{index}"] = value
    return out


def rule_ee_v3_aggregate(p):
    """Recompute the public E-E V3 aggregate without replaying private endpoints.

    The public adjudication releases optimizer-seed metric vectors, descriptive
    Welch contrasts, fixed-dataset bootstrap intervals, resource summaries, and
    a hash ledger for the sequestered TEST endpoints/rank sidecars.  The graph
    recomputes all released aggregate arithmetic and verifies the Git-backed
    existing-reference artifacts.  It deliberately does not replay private
    endpoint extraction or record-level bootstrap resampling.
    """
    adjud = load(p["adjud"])
    seeds = [int(s) for s in p["seeds"]]
    arms = [str(a) for a in p["arms"]]
    expected_boundary = (
        "Prospectively frozen but outcome-known same-investigator execution; "
        "AlphaFuse-style MiniLM representation package versus its repository "
        "SASRec ID backbone under shared data and complete-history-masked "
        "evaluator. Architectures, text availability, initialization, trainable "
        "capacity, and parameter allocation are not equalized. This is not "
        "independent confirmation, an isolation of null-space fusion, "
        "equal-tuning evidence, or a general SOTA claim."
    )
    if (adjud.get("protocol") != "PREREG_EE_V3"
            or adjud.get("classification") !=
                "PROSPECTIVELY_FROZEN_OUTCOME_KNOWN_SAME_INVESTIGATOR_EXPLORATORY"
            or adjud.get("verdict") != "EEV3-REPORTABLE-OUTCOME-KNOWN"
            or adjud.get("claim_boundary") != expected_boundary
            or adjud.get("countable_as_current_comparator") is not True
            or adjud.get("independent_confirmation") is not False
            or adjud.get("general_sota_claim_allowed") is not False
            or adjud.get("repository_commit") != p["repository_commit"]
            or adjud.get("upstream_commit") != p["upstream_commit"]
            or [int(s) for s in adjud.get("seeds", [])] != seeds
            or [str(a) for a in adjud.get("arms", [])] != arms
            or not re.fullmatch(r"[0-9a-f]{64}", str(adjud.get("ready_sha256", "")))):
        raise ValueError("E-E V3 adjudication metadata drift")

    def summarize(values):
        n = len(values)
        mu = mean(values)
        sd = sstd(values)
        half = t_ppf(0.975, n - 1) * sd / math.sqrt(n)
        return {"n": float(n), "mean": mu, "sd": sd,
                "ci_lo": mu - half, "ci_hi": mu + half}

    def verify_summary(label, values, recorded):
        recomputed = summarize(values)
        expected = {
            "n": recorded["n"], "mean": recorded["mean"],
            "sd": recorded["sd"], "ci_lo": recorded["ci95"][0],
            "ci_hi": recorded["ci95"][1],
        }
        for key, value in expected.items():
            if abs(float(recomputed[key]) - float(value)) > 1e-12:
                raise ValueError(f"E-E V3 {label} {key} drift")
        return recomputed

    summaries = {}
    vectors = {}
    arm_records = adjud.get("arm_seed_summaries", {})
    for arm in arms:
        if set(arm_records.get(arm, {})) != {"NDCG@10", "HR@10", "MRR"}:
            raise ValueError(f"E-E V3 {arm} metric-family drift")
        for metric in ("NDCG@10", "HR@10", "MRR"):
            rec = arm_records[arm][metric]
            values = [float(x) for x in rec.get("vector", [])]
            if len(values) != len(seeds):
                raise ValueError(f"E-E V3 {arm} {metric} seed-vector drift")
            vectors[(arm, metric)] = values
            summaries[(arm, metric)] = verify_summary(
                f"{arm} {metric}", values, rec)

    reference_record = adjud.get("existing_paper_reference", {}).get("NDCG@10", {})
    reference = [float(x) for x in reference_record.get("vector", [])]
    if len(reference) != len(p["reference_files"]):
        raise ValueError("E-E V3 existing-reference vector drift")
    reference_summary = verify_summary("existing reference", reference, reference_record)
    recorded_hashes = adjud.get("existing_paper_reference", {}).get("files_sha256", {})
    for rel in p["reference_files"]:
        name = os.path.basename(rel)
        raw_ok = sha256_file(rel) == recorded_hashes.get(name)
        lf_ok = sha256_lf(rel) == p["reference_lf_sha256"].get(name)
        if not (raw_ok or lf_ok):
            raise ValueError(f"E-E V3 reference identity drift: {name}")
    artifact_reference = [bt_metric(rel, "NDCG@10") for rel in p["reference_files"]]
    if any(abs(a - b) > 1e-15 for a, b in zip(artifact_reference, reference)):
        raise ValueError("E-E V3 reference vector does not match source artifacts")

    def welch(first, second):
        a = summarize(first)
        b = summarize(second)
        va = a["sd"] ** 2 / len(first)
        vb = b["sd"] ** 2 / len(second)
        se = math.sqrt(va + vb)
        df = (va + vb) ** 2 / (va * va / (len(first) - 1)
                                + vb * vb / (len(second) - 1))
        delta = a["mean"] - b["mean"]
        t_value = delta / se
        half = t_ppf(0.975, df) * se
        return {"delta": delta, "df": df,
                "p_two_sided_unadjusted": t_two_sided_p(t_value, df),
                "ci_lo": delta - half, "ci_hi": delta + half}

    def verify_contrast(label, first, second, recorded):
        recomputed = welch(first, second)
        expected = {
            "delta": recorded["delta"], "df": recorded["welch_df"],
            "p_two_sided_unadjusted": recorded["p_two_sided_unadjusted"],
            "ci_lo": recorded["ci95"][0], "ci_hi": recorded["ci95"][1],
        }
        for key, value in expected.items():
            if abs(float(recomputed[key]) - float(value)) > 1e-12:
                raise ValueError(f"E-E V3 {label} Welch {key} drift")
        direction = ("ABOVE" if recomputed["ci_lo"] > 0.0 else
                     "BELOW" if recomputed["ci_hi"] < 0.0 else "OVERLAP")
        if (recorded.get("direction") != direction
                or recorded.get("estimand") != "first arm minus second arm"
                or recorded.get("inference_boundary") !=
                    "descriptive independent-arm Welch on optimizer-seed estimates"):
            raise ValueError(f"E-E V3 {label} contrast-boundary drift")
        recomputed["direction"] = direction
        return recomputed

    alpha_ndcg = vectors[("alphafuse_package", "NDCG@10")]
    sasrec_ndcg = vectors[("sasrec_id", "NDCG@10")]
    contrasts = adjud.get("contrasts", {})
    vs_sasrec = verify_contrast(
        "AlphaFuse-minus-SASRec-ID", alpha_ndcg, sasrec_ndcg,
        contrasts["alphafuse_package_minus_sasrec_id"])
    vs_reference = verify_contrast(
        "AlphaFuse-minus-existing-reference", alpha_ndcg, reference,
        contrasts["alphafuse_package_minus_existing_paper_reference"])

    sensitivity = adjud.get("fixed_dataset_sensitivity", {})
    user_ci = [float(x) for x in sensitivity.get(
        "user_resample_percentile_ci95", [])]
    item_ci = [float(x) for x in sensitivity.get(
        "target_item_cluster_resample_percentile_ci95", [])]
    if (sensitivity.get("boundary") !=
            "fixed-split sensitivity only; not optimizer or population inference"
            or sensitivity.get("estimand") !=
            "mean over users of eight-seed AlphaFuse NDCG@10 minus eight-seed ID NDCG@10"
            or int(sensitivity.get("replicates", -1)) != 2000
            or int(sensitivity.get("rng_seed", -1)) != 20262299
            or int(sensitivity.get("n_target_item_clusters", -1)) != 18219
            or abs(float(sensitivity.get("point_estimate")) - vs_sasrec["delta"]) > 1e-12
            or len(user_ci) != 2 or len(item_ci) != 2
            or not (user_ci[0] < vs_sasrec["delta"] < user_ci[1])
            or not (item_ci[0] < vs_sasrec["delta"] < item_ci[1])):
        raise ValueError("E-E V3 fixed-dataset sensitivity metadata drift")

    ledger = adjud.get("endpoint_ledger", [])
    expected_pairs = [(arm, seed) for arm in arms for seed in seeds]
    if (len(ledger) != len(expected_pairs)
            or [(str(row.get("arm")), int(row.get("seed", -1)))
                for row in ledger] != expected_pairs):
        raise ValueError("E-E V3 endpoint-ledger arm/seed drift")
    endpoint_hashes, sidecar_hashes = set(), set()
    for row in ledger:
        arm, seed = str(row["arm"]), int(row["seed"])
        if (row.get("endpoint_file") !=
                f"assessment_EEV3_{arm}_seed{seed}.finaleval.json"
                or row.get("sidecar_file") !=
                f"assessment_EEV3_{arm}_seed{seed}.finaleval.users.npz"
                or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("endpoint_sha256", "")))
                or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("sidecar_sha256", "")))):
            raise ValueError("E-E V3 endpoint-ledger schema/hash-string drift")
        endpoint_hashes.add(row["endpoint_sha256"])
        sidecar_hashes.add(row["sidecar_sha256"])
    if len(endpoint_hashes) != 16 or len(sidecar_hashes) != 16:
        raise ValueError("E-E V3 endpoint-ledger hash uniqueness drift")

    def median(values):
        ordered = sorted(float(x) for x in values)
        mid = len(ordered) // 2
        return (ordered[mid] if len(ordered) % 2
                else 0.5 * (ordered[mid - 1] + ordered[mid]))

    if (adjud.get("resource_scope") !=
            "profiler FLOPs are operator-accounted forward-plus-full-catalog-score lower bounds"):
        raise ValueError("E-E V3 resource-scope drift")
    resource_fields = (
        "cuda_peak_allocated_bytes", "eval_seconds",
        "profiler_accounted_flops_per_user", "selected_epoch", "total_params",
        "trainable_params", "training_wall_seconds", "users_per_second")
    resource_medians = {}
    for arm in arms:
        arm_resources = adjud.get("resources", {}).get(arm, {})
        if set(arm_resources) != set(resource_fields):
            raise ValueError(f"E-E V3 {arm} resource-family drift")
        for field in resource_fields:
            rec = arm_resources[field]
            values = [float(x) for x in rec.get("vector", [])]
            if (len(values) != len(seeds)
                    or abs(median(values) - float(rec.get("median"))) > 1e-12):
                raise ValueError(f"E-E V3 {arm} {field} resource drift")
            resource_medians[(arm, field)] = median(values)

    alpha = summaries[("alphafuse_package", "NDCG@10")]
    sasrec = summaries[("sasrec_id", "NDCG@10")]
    out = {
        "n_units_per_arm": float(len(seeds)),
        "alphafuse_ndcg_mean": alpha["mean"],
        "alphafuse_ndcg_sd": alpha["sd"],
        "alphafuse_ndcg_ci_lo": alpha["ci_lo"],
        "alphafuse_ndcg_ci_hi": alpha["ci_hi"],
        "sasrec_id_ndcg_mean": sasrec["mean"],
        "sasrec_id_ndcg_sd": sasrec["sd"],
        "sasrec_id_ndcg_ci_lo": sasrec["ci_lo"],
        "sasrec_id_ndcg_ci_hi": sasrec["ci_hi"],
        "existing_reference_mean": reference_summary["mean"],
        "existing_reference_ci_lo": reference_summary["ci_lo"],
        "existing_reference_ci_hi": reference_summary["ci_hi"],
        "delta_vs_sasrec_id": vs_sasrec["delta"],
        "delta_vs_sasrec_id_ci_lo": vs_sasrec["ci_lo"],
        "delta_vs_sasrec_id_ci_hi": vs_sasrec["ci_hi"],
        "delta_vs_sasrec_id_p": vs_sasrec["p_two_sided_unadjusted"],
        "delta_vs_sasrec_id_welch_df": vs_sasrec["df"],
        "relative_gain_vs_sasrec_id_pct":
            100.0 * vs_sasrec["delta"] / sasrec["mean"],
        "delta_vs_existing_reference": vs_reference["delta"],
        "delta_vs_existing_reference_ci_lo": vs_reference["ci_lo"],
        "delta_vs_existing_reference_ci_hi": vs_reference["ci_hi"],
        "delta_vs_existing_reference_p": vs_reference["p_two_sided_unadjusted"],
        "delta_vs_existing_reference_welch_df": vs_reference["df"],
        "direction_above_sasrec_id": float(vs_sasrec["direction"] == "ABOVE"),
        "direction_below_existing_reference":
            float(vs_reference["direction"] == "BELOW"),
        "countable_as_current_comparator": 1.0,
        "independent_confirmation": 0.0,
        "general_sota_claim_allowed": 0.0,
        "verdict_reportable_outcome_known": 1.0,
        "bootstrap_replicates": float(sensitivity["replicates"]),
        "bootstrap_user_ci_lo": user_ci[0],
        "bootstrap_user_ci_hi": user_ci[1],
        "bootstrap_item_cluster_ci_lo": item_ci[0],
        "bootstrap_item_cluster_ci_hi": item_ci[1],
        "private_bootstrap_replay": 0.0,
        "private_endpoint_count": float(len(ledger)),
        "private_sidecar_count": float(len(ledger)),
        "private_endpoint_replay": 0.0,
    }
    for arm in arms:
        prefix = "alphafuse" if arm == "alphafuse_package" else "sasrec_id"
        for metric in ("HR@10", "MRR"):
            metric_key = "hr10" if metric == "HR@10" else "mrr"
            summary = summaries[(arm, metric)]
            out[f"{prefix}_{metric_key}_mean"] = summary["mean"]
            out[f"{prefix}_{metric_key}_ci_lo"] = summary["ci_lo"]
            out[f"{prefix}_{metric_key}_ci_hi"] = summary["ci_hi"]
        for field in resource_fields:
            out[f"{prefix}_{field}_median"] = resource_medians[(arm, field)]
    for index, value in enumerate(alpha_ndcg, start=1):
        out[f"alphafuse_ndcg_seed_{index}"] = value
    for index, value in enumerate(sasrec_ndcg, start=1):
        out[f"sasrec_id_ndcg_seed_{index}"] = value
    for index, value in enumerate(reference, start=1):
        out[f"existing_reference_ndcg_seed_{index}"] = value
    return out


def rule_ee_v4_aggregate(p):
    """Recompute the public E-E V4 normal-initialization sensitivity.

    The compact adjudication releases the eight optimizer-seed metric vectors,
    three descriptive independent-arm Welch contrasts, resource summaries, and
    a hash ledger for private TEST endpoints/sidecars.  The graph verifies those
    aggregates and the prior V3 adjudication without reading private endpoints.
    """
    adjud = load(p["adjud"])
    prior_path = p["prior_adjud"]
    prior = load(prior_path)
    seeds = [int(s) for s in p["seeds"]]
    expected_boundary = (
        "Prospectively frozen but outcome-known same-investigator cross-campaign "
        "sensitivity using the upstream-default-normal-init AlphaFuse-repository "
        "SASRec class. Phase/date and initialization are confounded; architecture, "
        "capacity, and parameter allocation remain unequal. This does not isolate "
        "initialization, establish SOTA, or provide independent confirmation."
    )
    prior_meta = adjud.get("prior_public_adjudication", {})
    if (adjud.get("protocol") != "PREREG_EE_V4"
            or adjud.get("classification") !=
                "PROSPECTIVELY_FROZEN_OUTCOME_KNOWN_SAME_INVESTIGATOR_COMPARATOR_FAIRNESS_SENSITIVITY"
            or adjud.get("verdict") != "EEV4-ALPHAFUSE-ABOVE-NORMAL-SASREC"
            or adjud.get("claim_boundary") != expected_boundary
            or adjud.get("countable_as_normal_init_sensitivity") is not True
            or adjud.get("independent_confirmation") is not False
            or adjud.get("general_sota_claim_allowed") is not False
            or adjud.get("initialization") != "upstream CLI default Normal(0,1)"
            or adjud.get("repository_commit") != p["repository_commit"]
            or adjud.get("upstream_commit") != p["upstream_commit"]
            or [int(s) for s in adjud.get("seeds", [])] != seeds
            or not re.fullmatch(r"[0-9a-f]{64}", str(adjud.get("ready_sha256", "")))
            or prior_meta.get("file") != os.path.basename(prior_path)
            or prior_meta.get("sha256") != sha256_file(prior_path)
            or prior.get("verdict") != "EEV3-REPORTABLE-OUTCOME-KNOWN"):
        raise ValueError("E-E V4 adjudication metadata drift")

    def summarize(values):
        n = len(values)
        mu = mean(values)
        sd = sstd(values)
        half = t_ppf(0.975, n - 1) * sd / math.sqrt(n)
        return {"n": float(n), "mean": mu, "sd": sd,
                "ci_lo": mu - half, "ci_hi": mu + half}

    def verify_summary(label, recorded, expected_n=None):
        values = [float(x) for x in recorded.get("vector", [])]
        expected_n = int(recorded.get("n", -1)) if expected_n is None else expected_n
        if len(values) != expected_n:
            raise ValueError(f"E-E V4 {label} seed-vector drift")
        recomputed = summarize(values)
        expected = {"n": recorded["n"], "mean": recorded["mean"],
                    "sd": recorded["sd"], "ci_lo": recorded["ci95"][0],
                    "ci_hi": recorded["ci95"][1]}
        for key, value in expected.items():
            if abs(float(recomputed[key]) - float(value)) > 1e-12:
                raise ValueError(f"E-E V4 {label} {key} drift")
        return values, recomputed

    arm_records = adjud.get("arm_seed_summary", {})
    if set(arm_records) != {"NDCG@10", "HR@10", "MRR"}:
        raise ValueError("E-E V4 metric-family drift")
    vectors, summaries = {}, {}
    for metric in ("NDCG@10", "HR@10", "MRR"):
        vectors[metric], summaries[metric] = verify_summary(
            metric, arm_records[metric], len(seeds))

    prior_vectors = {}
    for key in ("alphafuse_zero_ndcg10", "sasrec_zero_ndcg10",
                "existing_reference_ndcg10"):
        prior_vectors[key], _ = verify_summary(key, prior_meta[key])

    def verify_welch(label, first, second, recorded):
        a, b = summarize(first), summarize(second)
        va, vb = a["sd"] ** 2 / len(first), b["sd"] ** 2 / len(second)
        se = math.sqrt(va + vb)
        df = (va + vb) ** 2 / (va * va / (len(first) - 1)
                                + vb * vb / (len(second) - 1))
        delta = a["mean"] - b["mean"]
        half = t_ppf(0.975, df) * se
        recomputed = {"delta": delta, "welch_df": df,
                      "p_two_sided_unadjusted": t_two_sided_p(delta / se, df),
                      "ci_lo": delta - half, "ci_hi": delta + half}
        expected = {"delta": recorded["delta"], "welch_df": recorded["welch_df"],
                    "p_two_sided_unadjusted": recorded["p_two_sided_unadjusted"],
                    "ci_lo": recorded["ci95"][0], "ci_hi": recorded["ci95"][1]}
        for key, value in expected.items():
            if abs(float(recomputed[key]) - float(value)) > 1e-12:
                raise ValueError(f"E-E V4 {label} Welch {key} drift")
        direction = ("ABOVE" if recomputed["ci_lo"] > 0.0 else
                     "BELOW" if recomputed["ci_hi"] < 0.0 else "OVERLAP")
        if (recorded.get("direction") != direction
                or recorded.get("estimand") != "first arm minus second arm"
                or recorded.get("inference_boundary") !=
                    "descriptive independent-arm Welch on optimizer-seed estimates"):
            raise ValueError(f"E-E V4 {label} boundary drift")
        recomputed["direction"] = direction
        return recomputed

    contrasts = adjud.get("contrasts", {})
    alpha_minus_normal = verify_welch(
        "V3 AlphaFuse minus V4 normal SASRec",
        prior_vectors["alphafuse_zero_ndcg10"], vectors["NDCG@10"],
        contrasts["v3_alphafuse_zero_minus_v4_sasrec_normal"])
    normal_minus_zero = verify_welch(
        "V4 normal SASRec minus V3 zero SASRec", vectors["NDCG@10"],
        prior_vectors["sasrec_zero_ndcg10"],
        contrasts["v4_sasrec_normal_minus_v3_sasrec_zero"])
    normal_minus_reference = verify_welch(
        "V4 normal SASRec minus existing reference", vectors["NDCG@10"],
        prior_vectors["existing_reference_ndcg10"],
        contrasts["v4_sasrec_normal_minus_existing_paper_reference"])

    ledger = adjud.get("endpoint_ledger", [])
    if (len(ledger) != len(seeds)
            or [int(row.get("seed", -1)) for row in ledger] != seeds):
        raise ValueError("E-E V4 endpoint-ledger seed drift")
    endpoint_hashes, sidecar_hashes = set(), set()
    for row in ledger:
        seed = int(row["seed"])
        if (row.get("arm") != "sasrec_normal"
                or row.get("endpoint_file") !=
                    f"assessment_EEV4_sasrec_normal_seed{seed}.finaleval.json"
                or row.get("sidecar_file") !=
                    f"assessment_EEV4_sasrec_normal_seed{seed}.finaleval.users.npz"
                or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("endpoint_sha256", "")))
                or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("sidecar_sha256", "")))):
            raise ValueError("E-E V4 endpoint-ledger schema/hash drift")
        endpoint_hashes.add(row["endpoint_sha256"])
        sidecar_hashes.add(row["sidecar_sha256"])
    if len(endpoint_hashes) != 8 or len(sidecar_hashes) != 8:
        raise ValueError("E-E V4 endpoint-ledger uniqueness drift")

    if (adjud.get("resource_scope") !=
            "two-process concurrent training waves make wall time unsuitable for hardware-efficiency claims; profiler FLOPs are operator-accounted lower bounds"):
        raise ValueError("E-E V4 resource-scope drift")
    for field, recorded in adjud.get("resources", {}).items():
        values = sorted(float(x) for x in recorded.get("vector", []))
        if len(values) != len(seeds):
            raise ValueError(f"E-E V4 {field} resource-vector drift")
        median = 0.5 * (values[3] + values[4])
        if abs(median - float(recorded.get("median"))) > 1e-12:
            raise ValueError(f"E-E V4 {field} resource-median drift")

    ndcg = summaries["NDCG@10"]
    return {
        "verdict_alphafuse_above_normal_sasrec": 1.0,
        "countable_as_normal_init_sensitivity": 1.0,
        "independent_confirmation": 0.0,
        "general_sota_claim_allowed": 0.0,
        "n_units": float(len(seeds)),
        "normal_ndcg_mean": ndcg["mean"],
        "normal_ndcg_ci_lo": ndcg["ci_lo"],
        "normal_ndcg_ci_hi": ndcg["ci_hi"],
        "normal_hr10_mean": summaries["HR@10"]["mean"],
        "normal_hr10_ci_lo": summaries["HR@10"]["ci_lo"],
        "normal_hr10_ci_hi": summaries["HR@10"]["ci_hi"],
        "normal_mrr_mean": summaries["MRR"]["mean"],
        "alpha_minus_normal": alpha_minus_normal["delta"],
        "alpha_minus_normal_ci_lo": alpha_minus_normal["ci_lo"],
        "alpha_minus_normal_ci_hi": alpha_minus_normal["ci_hi"],
        "alpha_minus_normal_p": alpha_minus_normal["p_two_sided_unadjusted"],
        "normal_minus_zero": normal_minus_zero["delta"],
        "normal_minus_zero_ci_lo": normal_minus_zero["ci_lo"],
        "normal_minus_zero_ci_hi": normal_minus_zero["ci_hi"],
        "normal_minus_reference": normal_minus_reference["delta"],
        "normal_minus_reference_ci_lo": normal_minus_reference["ci_lo"],
        "normal_minus_reference_ci_hi": normal_minus_reference["ci_hi"],
        "private_endpoint_count": float(len(ledger)),
        "private_endpoint_replay": 0.0,
    }

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

def rule_fir_v3_welch_adjudicated(p):
    """Bind an E-A frozen Welch contrast to runs, initialization, and verdict."""
    out = rule_welch_2arm_bt(p)
    adjud = load(p["adjud"])
    if adjud.get("verdict") != "W-POS":
        raise ValueError("FIR V3 adjudication verdict drift")
    rows = {row["contrast"]: row for row in adjud.get("contrasts", [])}
    if p["contrast"] not in rows:
        raise ValueError(f"FIR V3 adjudication missing {p['contrast']}")
    row = rows[p["contrast"]]
    expected = {"diff": row["est"], "t": row["t"], "df": row["df"],
                "p": row["p"], "ci95_lo": row["ci"][0],
                "ci95_hi": row["ci"][1]}
    for key, value in expected.items():
        if abs(float(out[key]) - float(value)) > 1e-12:
            raise ValueError(f"FIR V3 adjudicated {key} drift: {out[key]} != {value}")
    for seed, af, bf in zip(p["seeds"], p["a"], p["b"]):
        a, b = load(af), load(bf)
        if (a["config"].get("seed") != seed or b["config"].get("seed") != seed
                or a.get("init_state_sha256") != b.get("init_state_sha256")):
            raise ValueError(f"FIR V3 matched-initialization drift for seed {seed}")
        frozen = adjud["init_hash_by_seed"][str(seed)]
        if (frozen.get(p["a_arm"]) != a.get("init_state_sha256")
                or frozen.get(p["b_arm"]) != b.get("init_state_sha256")):
            raise ValueError(f"FIR V3 adjudicated initialization drift for seed {seed}")
    out["holm_significant"] = float(bool(row.get("holm_significant")))
    out["verdict_w_pos"] = 1.0
    return out

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
                     "office_confirmation", "theirs_on_ours", "fir_breadth",
                     "fir_v3", "fir_canonical_breadth", "fir_controls",
                     "fir_pointwise", "fir_evidence_summary", "fir_prospective_sw_v3",
                     "fir_efficiency_ml1m_v1", "wearec_v1", "ee_v3", "ee_v4",
                     "office_v3", "tfv2"]

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
        "paired_delta_adjudicated": "matched-init paired (a-b) best_test[{m}], with frozen configuration, initialization hashes, statistics, verdict, and Holm decision cross-checked against the mechanical adjudication JSON",
        "fir_v3_welch_adjudicated": "frozen E-A independent-arm Welch contrast on best_test[{m}], bound to matched initialization hashes, adjudicated statistics, and verdict",
        "fir_control_contrast": "matched-init paired (a-b) sealed one-shot final test NDCG@10, with statistics, frozen verdict, and Holm decision cross-checked against the mechanical active-control adjudication JSON",
        "fir_pointwise_contrast": "matched-init paired (a-b) sealed one-shot final test NDCG@10, with parameter equality, statistics, frozen verdict, and Holm decision cross-checked against the mechanical pointwise-placebo adjudication JSON",
        "fir_evidence_summary": "visual-index CSV bound row-by-row to six released adjudications; source estimators and evidence classes remain separate, with no pooling or new multiplicity family",
        "fir_prospective_sw_v3_contrast": "prospective matched-init paired learned-minus-identity sealed one-shot Software TEST NDCG@10, with validation-only checkpoint selection, state and evidence hashes, statistics, practical threshold, and committed adjudicator verdict independently cross-checked",
        "fir_efficiency_ml1m_v1_aggregate": "prospectively frozen same-investigator MovieLens 1M aggregate adjudication: recompute seed-vector means, paired intervals, Holm decisions, noninferiority bounds, and figure-resource rows; private record-level endpoints are not redistributable and are not independently replayed by the public graph",
        "wearec_v1_aggregate": "prospectively frozen outcome-known same-investigator WEARec aggregate adjudication: verify the six existing reference artifacts and recompute released NDCG@10 seed-vector means, t intervals, and the descriptive unpaired Welch contrast; private sealed endpoints and per-user sidecars are not independently replayed by the public graph",
        "ee_v3_aggregate": "prospectively frozen outcome-known same-investigator AlphaFuse-style aggregate adjudication: verify the six existing reference artifacts; recompute released NDCG@10/HR@10/MRR seed summaries and descriptive independent-arm Welch contrasts; validate fixed-dataset sensitivity metadata and resource summaries; check the private endpoint/sidecar ledger's shape, 64-hex syntax, and uniqueness without reading or hashing the private files; private endpoint extraction and record-level bootstrap resampling are not independently replayed by the public graph",
        "ee_v4_aggregate": "prospectively frozen outcome-known same-investigator parser-default Normal(0,1) SASRec sensitivity: verify the prior V3 adjudication hash, recompute the released NDCG@10/HR@10/MRR summary and three descriptive cross-campaign Welch contrasts, validate resource medians, and check the private endpoint/sidecar ledger without reading private files; phase/date and initialization remain confounded",
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
                  "delta NDCG@10 (n=1; no observed benefit)", [DEC_TS, J1], "delta_means",
                  {"a": [DEC_TS], "b": [J1]},
                  [chk("delta", 0.0001, mode="bound_abs")], 1, expl,
                  notes="Paper states 'no observed benefit (+-0.0001)'; gate is |delta| <= 0.0001."))
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

    # ---------------- Table 1c: MI arm-by-arm comparison ----------------
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
    C.append(cell("t1c.filteronly.delta", "table1c", "+ FIR package arm (attribution open)", "delta vs base",
                  MIFO + MIBASE4, "delta_means", {"a": MIFO, "b": MIBASE4},
                  [chk("delta", 0.0025, 4)], 5, conf))
    C.append(cell("t1c.filteronly.share", "table1c", "+ FIR package arm (attribution open)", "share of combined k16 lift",
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
                  "same-seed-record delta NDCG@10, no-benefit bound (paired premise withdrawn)", D5TS + D5J1, "paired_delta",
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

    # ------- fir_v3: headline E-A frozen Welch contrasts -------
    FIRV3_SEEDS = list(range(20260713, 20260721))
    FIRV3_ADJ = BR + "fir_v3_adjudication.json"
    FIRV3_NOTE = ("PREREG_FIR_V3.md frozen analysis: independent-arm Welch/"
                  "Satterthwaite despite matched initialization; paired-by-seed "
                  "difference is descriptive. Outcome-visible internal evidence.")
    for short, a_arm, b_arm, contrast, mu, lo, hi, df, pv, holm in (
            ("primary", "a1learned", "a0ident", "A1-A0 (PRIMARY)",
             0.002265, 0.001928, 0.002602, 13.9394, 9.16123454430081e-10, 1),
            ("wd", "a2learnedwd0", "a1learned", "A2-A1",
             0.000010, -0.000339, 0.000360, 13.9991, 0.9505409921847826, 0)):
        AF = [BR + f"results_MI_FIRV3_{a_arm}_seed{s}.json" for s in FIRV3_SEEDS]
        BF = [BR + f"results_MI_FIRV3_{b_arm}_seed{s}.json" for s in FIRV3_SEEDS]
        C.append(cell(f"firv3.{short}.welch", "fir_v3",
                      f"E-A FIR V3 {contrast} frozen Welch contrast",
                      "independent-arm Welch 95% CI on best-by-val full-catalog NDCG@10",
                      AF + BF + [FIRV3_ADJ], "fir_v3_welch_adjudicated",
                      {"a": AF, "b": BF, "a_arm": a_arm, "b_arm": b_arm,
                       "contrast": contrast, "adjud": FIRV3_ADJ,
                       "seeds": FIRV3_SEEDS},
                      [chk("diff", mu, 6), chk("ci95_lo", lo, 6),
                       chk("ci95_hi", hi, 6), chk("df", df, 4),
                       chk("p", pv, mode="approx", tol=1e-12),
                       chk("holm_significant", holm, mode="count"),
                       chk("verdict_w_pos", 1, mode="count")],
                      8, "exploratory", seeds=FIRV3_SEEDS, notes=FIRV3_NOTE))

    # ------- fir_canonical_breadth: canonical gradient-active FIR vs identity -------
    # Frozen matched-initialization design; one K/epoch configuration, zero category tuning.
    FIRCAN_SEEDS = list(range(20260810, 20260818))
    FIRCAN_ADJ = BR + "fir_canonical_breadth_adjudication.json"
    FIRCAN_NOTE = ("PREREG_FIR_CANONICAL_BREADTH.md was committed before launch with its "
                   "mechanical adjudicator. Canonical gradient-active FIR vs delta=0 identity; "
                   "matched initialization per category/seed; K=16, 20 epochs, one frozen "
                   "configuration and zero category tuning. The categories were selected after "
                   "favorable legacy-package outcomes and TEST was evaluated each epoch, so this "
                   "is outcome-known/test-exposed internal robustness, not independent "
                   "confirmation. Internal contrast only: no SOTA, external-comparator, or "
                   "distributional-superiority claim. Ordinary paired-t CIs; Holm-adjusted "
                   "decisions. Verdict CANON-BREADTH-POS; both categories PASS under Holm.")
    for cat, short, mu, lo, hi, tv, pv in (
            ("Industrial_and_Scientific", "is", 0.002110, 0.001820, 0.002399,
             17.2344, 5.438952e-7),
            ("CDs_and_Vinyl", "cd", 0.006150, 0.005849, 0.006450,
             48.3917, 4.210648e-10)):
        A1 = [BR + f"results_{cat}_FIRCANON_a1learned_seed{s}.json" for s in FIRCAN_SEEDS]
        A0 = [BR + f"results_{cat}_FIRCANON_a0ident_seed{s}.json" for s in FIRCAN_SEEDS]
        C.append(cell(f"fircanon.{short}.paired", "fir_canonical_breadth",
                      f"canonical FIR breadth: {cat} matched-init (learned - identity)",
                      "paired 8-seed delta NDCG@10 (best-by-val full catalog; Holm family)",
                      A1 + A0 + [FIRCAN_ADJ], "paired_delta_adjudicated",
                      {"a": A1, "b": A0, "adjud": FIRCAN_ADJ, "category": cat,
                       "seeds": FIRCAN_SEEDS, "expect_verdict": "CANON-BREADTH-POS",
                       "expect_kernel": 16, "expect_epochs": 20},
                      [chk("mean", mu, 6), chk("ci_lo", lo, 6), chk("ci_hi", hi, 6),
                       chk("t", tv, 4), chk("paired_p", pv, mode="approx", tol=1e-12),
                       chk("pos", 8, mode="count"),
                       chk("holm_significant", 1, mode="count"),
                       chk("passed", 1, mode="count")],
                      8, conf, seeds=FIRCAN_SEEDS, notes=FIRCAN_NOTE))
        for metric_name, metric_key, sec_mu, sec_lo, sec_hi in (
                ("HR@10", "HR@10",
                 0.003474 if short == "is" else 0.010728,
                 0.002942 if short == "is" else 0.010295,
                 0.004006 if short == "is" else 0.011162),
                ("MRR", "MRR",
                 0.001819 if short == "is" else 0.005033,
                 0.001570 if short == "is" else 0.004710,
                 0.002069 if short == "is" else 0.005356)):
            C.append(cell(f"fircanon.{short}.{metric_name.lower().replace('@', '').replace('10', '10')}",
                          "fir_canonical_breadth",
                          f"canonical FIR breadth supportive: {cat} learned - identity",
                          f"paired 8-seed delta {metric_name} (supportive, ordinary CI)",
                          A1 + A0 + [FIRCAN_ADJ], "paired_delta",
                          {"a": A1, "b": A0, "metric": metric_key},
                          [chk("mean", sec_mu, 6), chk("ci_lo", sec_lo, 6),
                           chk("ci_hi", sec_hi, 6)],
                          8, "exploratory", seeds=FIRCAN_SEEDS,
                          notes=FIRCAN_NOTE + " Registered supportive endpoint; no "
                                "multiplicity-adjusted secondary claim."))

    # ------- fir_controls: pre-declared, outcome-known internal mechanism study -------
    # The campaign was frozen only after the canonical MI identity contrast was known.
    # It is therefore an active-control mechanism study, not independent confirmation.
    FIRCTRL_SEEDS = list(range(20260901, 20260909))
    FIRCTRL_ADJ = BR + "fir_controls_adjudication.json"
    FIRCTRL_NOTE = ("PREREG_FIR_CONTROLS.md was committed before launch with its "
                    "mechanical first-reader adjudicator. Six matched-initialization "
                    "arms, K=16, 20 epochs, best-by-validation checkpoint selection, "
                    "then a sealed one-shot final TEST evaluation. Outcome-known "
                    "internal active-control study only: no independent-confirmation, "
                    "external-comparator, SOTA, equivalence, or distributional claim. "
                    "Frozen verdict CTRL-ACTIVE-CONTROL-SUPPORTED.")
    def ctrl_files(arm, suffix):
        return [BR + f"results_Musical_Instruments_FIRCTRL_{arm}_seed{s}{suffix}"
                for s in FIRCTRL_SEEDS]
    ctrl_specs = (
        ("a.learned", "learned", "identity", "family_a", "holm_a",
         "learned-identity", 0.002116, 0.001910, 0.002322, 1),
        ("a.fixed_ma", "fixed_ma", "identity", "family_a", "holm_a",
         "fixed_ma-identity", 0.000712, 0.000509, 0.000915, 1),
        ("a.fixed_hp", "fixed_hp", "identity", "family_a", "holm_a",
         "fixed_hp-identity", 0.000708, 0.000510, 0.000907, 1),
        ("a.shared", "shared", "identity", "family_a", "holm_a",
         "shared-identity", 0.002197, 0.002008, 0.002386, 1),
        ("a.nonlinear", "nonlinear", "identity", "family_a", "holm_a",
         "nonlinear-identity", 0.001912, 0.001657, 0.002166, 1),
        ("b.fixed_ma", "learned", "fixed_ma", "family_b", "holm_b",
         "learned-fixed_ma", 0.001404, 0.001085, 0.001723, 1),
        ("b.fixed_hp", "learned", "fixed_hp", "family_b", "holm_b",
         "learned-fixed_hp", 0.001407, 0.001089, 0.001726, 1),
        ("b.shared", "learned", "shared", "family_b", "holm_b",
         "learned-shared", -0.000081, -0.000337, 0.000175, 0),
        ("b.nonlinear", "learned", "nonlinear", "family_b", "holm_b",
         "learned-nonlinear", 0.000204, -0.000038, 0.000446, 0),
    )
    for short, a_arm, b_arm, family, holm_family, contrast, mu, lo, hi, reject in ctrl_specs:
        af = ctrl_files(a_arm, ".finaleval.json")
        bf = ctrl_files(b_arm, ".finaleval.json")
        source = af + bf
        for arm in (a_arm, b_arm):
            source += ctrl_files(arm, ".json")
            source += ctrl_files(arm, ".finaleval.started.json")
            source += ctrl_files(arm, ".finaleval.users.npz")
        source.append(FIRCTRL_ADJ)
        C.append(cell(f"firctrl.{short}", "fir_controls",
                      f"FIR active control: {contrast}",
                      "paired 8-seed delta sealed final-test NDCG@10 (Holm family)",
                      source, "fir_control_contrast",
                      {"a": af, "b": bf, "a_arm": a_arm, "b_arm": b_arm,
                       "family": family, "holm": holm_family,
                       "contrast": contrast, "adjud": FIRCTRL_ADJ,
                       "seeds": FIRCTRL_SEEDS},
                      [chk("mean", mu, 6), chk("ci_lo", lo, 6),
                       chk("ci_hi", hi, 6),
                       chk("holm_reject", reject, mode="count")],
                      8, "exploratory", seeds=FIRCTRL_SEEDS,
                      notes=FIRCTRL_NOTE))

    # ------- fir_pointwise: pre-declared, outcome-known non-temporal placebo -------
    FIRPOINT_SEEDS = list(range(20261001, 20261009))
    FIRPOINT_ADJ = BR + "fir_pointwise_v1_adjudication.json"
    FIRPOINT_NOTE = ("PREREG_FIR_POINTWISE_V1.md and its mechanical first-reader "
                     "adjudicator were committed and pushed before launch. Identity, "
                     "learned K=16 depthwise FIR, and a parameter-matched width-16 "
                     "current-position-only DCT/GELU/linear residual used exact "
                     "per-seed matched backbone initialization and sealed one-shot "
                     "final TEST evaluation. Outcome-known Musical_Instruments "
                     "mechanism study only: no independent-confirmation, external-"
                     "comparator, SOTA, equivalence, per-channel-necessity, or "
                     "cross-domain claim. Frozen verdict POINTWISE-FIR-DISCRIMINATED.")
    def point_files(arm, suffix):
        return [BR + f"results_Musical_Instruments_FIRPOINTV1_{arm}_seed{s}{suffix}"
                for s in FIRPOINT_SEEDS]
    point_specs = (
        ("learned_identity", "learned", "identity", "learned-identity",
         0.001872, 0.001737, 0.002007, 1),
        ("pointwise_identity", "pointwise", "identity", "pointwise-identity",
         -0.000069, -0.000200, 0.000061, 0),
        ("learned_pointwise", "learned", "pointwise", "learned-pointwise",
         0.001941, 0.001788, 0.002095, 1),
    )
    for short, a_arm, b_arm, contrast, mu, lo, hi, reject in point_specs:
        af = point_files(a_arm, ".finaleval.json")
        bf = point_files(b_arm, ".finaleval.json")
        source = af + bf
        for arm in (a_arm, b_arm):
            source += point_files(arm, ".json")
            source += point_files(arm, ".finaleval.started.json")
            source += point_files(arm, ".finaleval.users.npz")
        source.append(FIRPOINT_ADJ)
        C.append(cell(f"firpoint.{short}", "fir_pointwise",
                      f"FIR pointwise placebo: {contrast}",
                      "paired 8-seed delta sealed final-test NDCG@10 (one Holm family)",
                      source, "fir_pointwise_contrast",
                      {"a": af, "b": bf, "a_arm": a_arm, "b_arm": b_arm,
                       "contrast": contrast, "adjud": FIRPOINT_ADJ,
                       "seeds": FIRPOINT_SEEDS},
                      [chk("mean", mu, 6), chk("ci_lo", lo, 6),
                       chk("ci_hi", hi, 6),
                       chk("holm_reject", reject, mode="count")],
                      8, "exploratory", seeds=FIRPOINT_SEEDS,
                      notes=FIRPOINT_NOTE))

    # ------- cross-adjudication FIR evidence-map figure -------
    evidence_adjudications = {
        "mi": BR + "fir_v3_adjudication.json",
        "breadth": BR + "fir_canonical_breadth_adjudication.json",
        "controls": BR + "fir_controls_adjudication.json",
        "pointwise": BR + "fir_pointwise_v1_adjudication.json",
        "software": BR + "fir_prospective_sw_v3_adjudication.json",
        "ml1m": BR + "fir_efficiency_ml1m_v1_adjudication.json",
    }
    evidence_figure_data = "figures/fig_fir_evidence_summary_data.csv"
    C.append(cell(
        "firevidence.summary", "fir_evidence_summary",
        "FIR evidence map: scope and boundary conditions",
        "eight released contrasts indexed without pooling",
        list(evidence_adjudications.values()) + [
            evidence_figure_data,
            "figures/fig_fir_evidence_summary.png",
            "figures/fig_fir_evidence_summary.pdf",
            BR + "make_fig_fir_evidence_summary.py",
        ],
        "fir_evidence_summary",
        {**evidence_adjudications, "figure_data": evidence_figure_data},
        [chk("rows", 8, mode="count"),
         chk("positive_excluding_zero", 5, mode="count"),
         chk("intervals_including_zero", 3, mode="count")],
        8, "exploratory",
        notes=("Visual index only. The intervals retain their source estimators "
               "and evidence classes and do not form a pooled analysis or one "
               "common multiplicity family. Positive Amazon contrasts coexist "
               "with the shared-filter boundary and the prospectively frozen "
               "same-investigator negative MovieLens transfer result.")))

    # ------- fir_prospective_sw_v3: frozen same-user Software robustness attempt -------
    SWV3_SEEDS = list(range(20261301, 20261309))
    SWV3_ADJ = BR + "fir_prospective_sw_v3_adjudication.json"
    def swv3_files(arm, suffix):
        return [BR + f"results_Software_FIRPROSPV3_{arm}_seed{s}{suffix}"
                for s in SWV3_SEEDS]
    swv3_learned = swv3_files("learned", ".finaleval.json")
    swv3_identity = swv3_files("identity", ".finaleval.json")
    swv3_sources = swv3_learned + swv3_identity
    for arm in ("learned", "identity"):
        swv3_sources += swv3_files(arm, ".json")
        swv3_sources += swv3_files(arm, ".finaleval.started.json")
        swv3_sources += swv3_files(arm, ".finaleval.users.npz")
    swv3_sources += [SWV3_ADJ,
                     "figures/fig_software_v3_pairs_data.csv",
                     "FIR_PROSPECTIVE_SW_V3_REPLAY_ERRATUM.md",
                     BR + "fir_prospective_sw_v3_attempt.json",
                     BR + "fir_prospective_sw_v3_ready.json",
                     BR + "fir_prospective_sw_v3_endpoints_complete.json",
                     BR + "fir_prospective_sw_v3_status.json"]
    SWV3_NOTE = ("PREREG_FIR_PROSPECTIVE_SW_V3 was frozen and pushed before launch. "
                 "All 16 training runs selected checkpoints on validation only with no "
                 "training-time TEST scores; the committed driver then created exclusive-created, "
                 "hash-linked local READY and endpoint seals, performed one final TEST evaluation "
                 "per selected checkpoint, and invoked the protocol-designated adjudicator. The "
                 "transductive all-split item catalog was explicitly predeclared. Human non-visibility "
                 "of earlier V2 validation output cannot be established from tracked evidence, so this "
                 "same-investigator, same-code-lineage, same-Amazon-family Software attempt is classified "
                 "outcome-known/exploratory robustness under local same-user custody, not external escrow, "
                 "independent confirmation, or cross-domain replication. The frozen tag also has a disclosed "
                 "raw-line-ending reference-hash replay defect; it does not affect endpoint arithmetic. "
                 "Frozen verdict SW-V3-PRACTICAL-POS.")
    C.append(cell("firprosp.swv3.learned_identity", "fir_prospective_sw_v3",
                  "Frozen Software FIR robustness: learned-identity",
                  "paired 8-seed delta sealed final-test NDCG@10",
                  swv3_sources, "fir_prospective_sw_v3_contrast",
                  {"learned": swv3_learned, "identity": swv3_identity,
                   "adjud": SWV3_ADJ, "seeds": SWV3_SEEDS,
                   "figure_data": "figures/fig_software_v3_pairs_data.csv",
                   "attempt": BR + "fir_prospective_sw_v3_attempt.json",
                   "ready": BR + "fir_prospective_sw_v3_ready.json",
                   "endpoints_complete": BR + "fir_prospective_sw_v3_endpoints_complete.json",
                   "status": BR + "fir_prospective_sw_v3_status.json"},
                  [chk("mean", 0.005062, 6), chk("ci_lo", 0.004591, 6),
                   chk("ci_hi", 0.005533, 6),
                   chk("sd", 0.000564, 6),
                   chk("learned_mean", 0.120200, 6),
                   chk("identity_mean", 0.115138, 6),
                   chk("sign_p_two_sided", 0.0078125, 7),
                   chk("n_positive", 8, mode="count"),
                   chk("delta_1", 0.0051975481, 10),
                   chk("delta_2", 0.0043089738, 10),
                   chk("delta_3", 0.0050821811, 10),
                   chk("delta_4", 0.0057889687, 10),
                   chk("delta_5", 0.0054392902, 10),
                   chk("delta_6", 0.0055166480, 10),
                   chk("delta_7", 0.0041945430, 10),
                   chk("delta_8", 0.0049667125, 10),
                   chk("practical_pass", 1, mode="count")],
                  8, "exploratory", seeds=SWV3_SEEDS, notes=SWV3_NOTE))

    # ------- fir_efficiency_ml1m_v1: prospective non-Amazon negative replication -------
    ML1M_ADJ = BR + "fir_efficiency_ml1m_v1_adjudication.json"
    ML1M_SEEDS = list(range(20261101, 20261109))
    ML1M_ARMS = ["identity", "shared", "grouped", "lowrank", "learned", "pointwise"]
    ML1M_FROZEN = {
        "trainer": BR + "run_sasrec_sbert_efficiency_ml1m_v1_frozen.py",
        "evaluator": BR + "eval_fir_efficiency_ml1m_v1.py",
        "runner": BR + "run_fir_efficiency_ml1m_v1.py",
        "structural_test": BR + "test_fir_efficiency_v1.py",
        "sequestration_test": BR + "test_fir_efficiency_sequestration_v1.py",
        "acquisition": BR + "acquire_movielens_fir_efficiency_v1.py",
        "preregistration": "PREREG_FIR_EFFICIENCY_ML1M_V1.md",
    }
    ML1M_FIGURE_DATA = "figures/fig_fir_efficiency_ml1m_v1_data.csv"
    ML1M_COHORT_FLOW_DATA = "figures/fig_movielens_cohort_flow_data.csv"
    ML1M_NOTE = (
        "PREREG_FIR_EFFICIENCY_ML1M_V1.md, code, and adjudicator were committed and "
        "pushed before MovieLens acquisition. Ninety-six training runs completed with "
        "TEST bytes sequestered, followed by 96 one-shot sealed evaluations and the "
        "protocol-designated adjudicator. Local logs do not establish first human/tool "
        "access. Exact verdict "
        "ML1M-NO-FIR-REPLICATION: learned FIR did not reject versus identity or the "
        "equal-parameter pointwise arm. Shared/grouped/low-rank noninferiority passes "
        "are conditional numerical compression results and do not imply FIR value when "
        "the learned-FIR replication gate fails. Prospectively frozen same-investigator "
        "non-Amazon evidence, not independent confirmation or population generalization. "
        "The ML-1M README prohibits redistribution, so the public graph recomputes from "
        "the aggregate adjudication vectors and frozen-code hashes but cannot independently "
        "replay private record-level endpoints, checkpoints, or per-user sidecars.")
    C.append(cell(
        "fireff.ml1m.aggregate", "fir_efficiency_ml1m_v1",
        "MovieLens 1M R4 FIR replication, conditional parsimony, and resources",
        "aggregate 8-seed paired NDCG@10 and descriptive resource plane",
        [ML1M_ADJ, ML1M_FIGURE_DATA, ML1M_COHORT_FLOW_DATA,
         "figures/fig_movielens_cohort_flow.png",
         "figures/fig_movielens_cohort_flow.pdf",
         BR + "make_fig_fir_efficiency_ml1m_v1.py",
         BR + "make_fig_movielens_cohort_flow.py"] + list(ML1M_FROZEN.values()),
        "fir_efficiency_ml1m_v1_aggregate",
        {"adjud": ML1M_ADJ, "seeds": ML1M_SEEDS, "arms": ML1M_ARMS,
         "frozen_files": ML1M_FROZEN, "figure_data": ML1M_FIGURE_DATA,
         "cohort_flow_data": ML1M_COHORT_FLOW_DATA},
        [
            chk("negative_verdict", 1, mode="count"),
            chk("mean_identity", 0.052151, 6),
            chk("mean_shared", 0.052211, 6),
            chk("mean_grouped", 0.052125, 6),
            chk("mean_lowrank", 0.052211, 6),
            chk("mean_learned", 0.052151, 6),
            chk("mean_pointwise", 0.052116, 6),
            chk("learned_identity_mean", 0.000000, 6),
            chk("learned_identity_ci_lo", -0.000074, 6),
            chk("learned_identity_ci_hi", 0.000075, 6),
            chk("learned_identity_p_holm", 0.995, 3),
            chk("learned_identity_reject", 0, mode="count"),
            chk("learned_pointwise_mean", 0.000035, 6),
            chk("learned_pointwise_ci_lo", -0.000057, 6),
            chk("learned_pointwise_ci_hi", 0.000127, 6),
            chk("learned_pointwise_p_holm", 0.796, 3),
            chk("learned_pointwise_reject", 0, mode="count"),
            chk("shared_minus_learned", 0.000060, 6),
            chk("shared_simultaneous_lower", -0.000068, 6),
            chk("shared_ni_p_holm", 0.00000520, mode="approx", tol=5e-9),
            chk("shared_ni_pass", 1, mode="count"),
            chk("grouped_minus_learned", -0.000027, 6),
            chk("grouped_simultaneous_lower", -0.000128, 6),
            chk("grouped_ni_p_holm", 0.00000520, mode="approx", tol=5e-9),
            chk("grouped_ni_pass", 1, mode="count"),
            chk("lowrank_minus_learned", 0.000060, 6),
            chk("lowrank_simultaneous_lower", -0.000033, 6),
            chk("lowrank_ni_p_holm", 0.00000143, mode="approx", tol=5e-9),
            chk("lowrank_ni_pass", 1, mode="count"),
            chk("all_learned_identity_mean", 0.000012, 6),
            chk("all_learned_identity_ci_lo", -0.000107, 6),
            chk("all_learned_identity_ci_hi", 0.000131, 6),
            chk("all_learned_pointwise_mean", 0.000043, 6),
            chk("all_learned_pointwise_ci_lo", -0.000082, 6),
            chk("all_learned_pointwise_ci_hi", 0.000168, 6),
            chk("cluster_intervals_including_zero", 6, mode="count"),
            chk("identity_filter_trainable_params", 0, mode="count"),
            chk("shared_filter_trainable_params", 16, mode="count"),
            chk("grouped_filter_trainable_params", 128, mode="count"),
            chk("lowrank_filter_trainable_params", 320, mode="count"),
            chk("learned_filter_trainable_params", 1024, mode="count"),
            chk("pointwise_filter_trainable_params", 1024, mode="count"),
            chk("identity_latency_ms_median", 2.076, 3),
            chk("shared_latency_ms_median", 2.105, 3),
            chk("grouped_latency_ms_median", 2.087, 3),
            chk("lowrank_latency_ms_median", 2.132, 3),
            chk("learned_latency_ms_median", 2.073, 3),
            chk("pointwise_latency_ms_median", 2.120, 3),
            chk("cohort_views", 2, mode="count"),
            chk("primary_candidate_users", 1102, mode="count"),
            chk("primary_retained_users", 1033, mode="count"),
        ],
        8, "exploratory", seeds=ML1M_SEEDS, notes=ML1M_NOTE))

    # ------- WEARec V1: official-code equal-evaluation current baseline -------
    WEAREC_SEEDS = list(range(20262001, 20262009))
    WEAREC_ADJ = BR + "wearec_baseline_v1_adjudication.json"
    WEAREC_SELECTION = BR + "wearec_baseline_v1_selection.json"
    WEAREC_REFERENCES = [
        BR + "results_V2_ls02_filter8_VG.json",
        BR + "results_V2_ls02_filter8_seed20260609_VG.json",
        BR + "results_V2_ls02_filter8_seed20260610_VG.json",
        BR + "results_V2_ls02_filter8_seed20260611_VG.json",
        BR + "results_V2_ls02_filter8_seed20260612_VG.json",
        BR + "results_V2_confirm_seed20260613_VG.json",
    ]
    # The adjudicator froze raw Windows working-tree hashes.  Git checkouts use
    # LF for these tracked JSON files, so the graph accepts either that exact raw
    # identity or the corresponding canonical LF identity and then recomputes
    # the reference vector from the JSON content itself.
    WEAREC_REFERENCE_LF_SHA256 = {
        "results_V2_ls02_filter8_VG.json":
            "8e22dcc882af35fb99c9a2f746c1fdd310a1a4158f958bc684477a6b9ca65f48",
        "results_V2_ls02_filter8_seed20260609_VG.json":
            "d6f607fe7b7e3943dc9354b87f8639cd10cfae8ba2f09c6a6d2d2f077d24d66e",
        "results_V2_ls02_filter8_seed20260610_VG.json":
            "adaa757aac318958b4ef23bd1234d243beacb5215751bbf7d4064ad09c32456d",
        "results_V2_ls02_filter8_seed20260611_VG.json":
            "19db16452087a64a66ee98315216675bc13719db5a86a74eaf28556d1bea74f2",
        "results_V2_ls02_filter8_seed20260612_VG.json":
            "b4c4df8aa5a7bfec28628f5b1bd5130d7b2f28646020b1472ccaa2eb6cf34658",
        "results_V2_confirm_seed20260613_VG.json":
            "4a1f1ac8b9a8e14fa8c98f781c6980292365e9fd5b7e0a2fb96bd4fa82db79f4",
    }
    WEAREC_FROZEN = [
        "PREREG_WEAREC_BASELINE_V1.md",
        BR + "acquire_wearec_baseline_v1.py",
        BR + "prepare_wearec_baseline_v1.py",
        BR + "wearec_baseline_v1_common.py",
        BR + "test_wearec_baseline_v1.py",
        BR + "run_wearec_baseline_v1.py",
        BR + "eval_wearec_baseline_v1.py",
        BR + "run_wearec_campaign_v1.py",
        BR + "adjudicate_wearec_baseline_v1.py",
        BR + "wearec_baseline_v1_catalog_manifest.json",
    ]
    WEAREC_NOTE = (
        "PREREG_WEAREC_BASELINE_V1 froze the official AAAI 2026 WEARec repository "
        "at commit 2087335339b1ead87da6e066ce14e2d33880a95e, two validation-only "
        "presets, and eight assessment seeds. All eight checkpoints were selected "
        "without TEST scoring before eight sealed one-shot evaluations. The "
        "protocol-designated adjudicator was the first authorized endpoint reader. "
        "Exact verdict WEAREC-BELOW-EXISTING-REFERENCE: WEARec mean NDCG@10 "
        "0.059184 [0.058674, 0.059693] versus the existing six-seed full-model "
        "reference 0.067337 [0.067063, 0.067611]; descriptive outcome-known "
        "unpaired Welch delta -0.008154 [-0.008689, -0.007618], p=1.16e-11. "
        "This is official-model/equal-evaluation evidence only: same investigators "
        "on an outcome-known split, not independent confirmation, SOTA, a paired "
        "experiment, equal architecture, equal loss/schedule, or equal tuning budgets. "
        "The public graph recomputes the released NDCG vector arithmetic and verifies "
        "the reference files and private endpoint-hash ledger; it does not replay "
        "private endpoint extraction or HR/MRR from unreleased raw vectors.")
    C.append(cell(
        "wearec.v1.aggregate", "wearec_v1",
        "Official WEARec current-baseline run under the paper evaluator",
        "aggregate NDCG@10 and descriptive existing-reference contrast",
        [WEAREC_ADJ, WEAREC_SELECTION] + WEAREC_REFERENCES + WEAREC_FROZEN,
        "wearec_v1_aggregate",
        {"adjud": WEAREC_ADJ, "seeds": WEAREC_SEEDS,
         "reference_files": WEAREC_REFERENCES,
         "reference_lf_sha256": WEAREC_REFERENCE_LF_SHA256},
        [
            chk("verdict_below", 1, mode="count"),
            chk("n_units", 8, mode="count"),
            chk("wearec_mean", 0.059184, 6),
            chk("wearec_ci_lo", 0.058674, 6),
            chk("wearec_ci_hi", 0.059693, 6),
            chk("reference_mean", 0.067337, 6),
            chk("reference_ci_lo", 0.067063, 6),
            chk("reference_ci_hi", 0.067611, 6),
            chk("delta", -0.008154, 6),
            chk("delta_ci_lo", -0.008689, 6),
            chk("delta_ci_hi", -0.007618, 6),
            chk("p_two_sided_unadjusted", 1.1567406255137613e-11,
                mode="approx", tol=1e-14),
            chk("n_params", 1775682, mode="count"),
            chk("private_endpoint_count", 8, mode="count"),
            chk("private_endpoint_replay", 0, mode="count"),
        ],
        8, "exploratory", seeds=WEAREC_SEEDS, notes=WEAREC_NOTE))

    # ------- E-E V3: clean AlphaFuse-style text+ID current comparator -------
    EEV3_SEEDS = list(range(20262201, 20262209))
    EEV3_ARMS = ["alphafuse_package", "sasrec_id"]
    EEV3_ADJ = BR + "ee_v3_adjudication.json"
    EEV3_FROZEN = [
        "PREREG_EE_V3.md",
        BR + "prepare_ee_v3.py",
        BR + "ee_v3_input_manifest.json",
        BR + "ee_v3_common.py",
        BR + "test_ee_v3.py",
        BR + "run_ee_v3.py",
        BR + "eval_ee_v3.py",
        BR + "run_ee_v3_campaign.py",
        BR + "adjudicate_ee_v3.py",
    ]
    EEV3_NOTE = (
        "PREREG_EE_V3 and its designated adjudicator were committed and pushed before "
        "launch. Prelaunch preparation opened the outcome-known combined TRAIN/VALID/TEST "
        "export and retained only TRAIN histories and VALID targets in the training input. "
        "Sixteen fresh-seed trainings selected checkpoints with complete-history-masked "
        "VALID NDCG@10 without loading, hashing, or scoring TEST; after all 16 training "
        "bundles were READY, 16 sealed one-shot evaluations followed. "
        "The unchanged committed adjudicator returned EEV3-REPORTABLE-OUTCOME-KNOWN. "
        "The AlphaFuse-style MiniLM representation package scored NDCG@10 0.048273 "
        "[0.048129, 0.048416] versus 0.039024 [0.038106, 0.039941] for a zero-initialized "
        "upstream-class SASRec ID control: descriptive independent-arm Welch delta "
        "+0.009249 [+0.008329, +0.010169], p=3.48e-08. It remained below the existing "
        "six-seed full-model reference by -0.019065 [-0.019347, -0.018783]. This is "
        "countable current-comparator evidence under shared data/evaluation and a "
        "frozen configuration, but it is outcome-known, same-investigator, and a "
        "whole-package contrast. It does not reproduce AlphaFuse's published text "
        "encoder, test the parser-default Normal(0,1) setting (which official recipes may "
        "override by dataset), equalize architecture/"
        "text availability/initialization/capacity, "
        "isolate null-space fusion, supply independent confirmation, or support SOTA. "
        "The public graph recomputes released aggregate arithmetic and checks the private "
        "endpoint/sidecar ledger's schema, 64-hex syntax, and uniqueness; it does not read "
        "or hash the private files or replay record-level bootstrap resampling. The local "
        "adjudicator checked the private-file digests.")
    C.append(cell(
        "eev3.aggregate", "ee_v3",
        "AlphaFuse-style MiniLM package versus zero-initialized upstream-class SASRec ID control",
        "aggregate NDCG@10/HR@10/MRR and descriptive Welch contrasts",
        [EEV3_ADJ] + WEAREC_REFERENCES + EEV3_FROZEN,
        "ee_v3_aggregate",
        {"adjud": EEV3_ADJ, "seeds": EEV3_SEEDS, "arms": EEV3_ARMS,
         "repository_commit": "f7c9c551d313de07b433545ed4887400ed4f4d98",
         "upstream_commit": "b501a0540b609370df995ad06fb245859b10a18a",
         "reference_files": WEAREC_REFERENCES,
         "reference_lf_sha256": WEAREC_REFERENCE_LF_SHA256},
        [
            chk("verdict_reportable_outcome_known", 1, mode="count"),
            chk("countable_as_current_comparator", 1, mode="count"),
            chk("independent_confirmation", 0, mode="count"),
            chk("general_sota_claim_allowed", 0, mode="count"),
            chk("direction_above_sasrec_id", 1, mode="count"),
            chk("direction_below_existing_reference", 1, mode="count"),
            chk("n_units_per_arm", 8, mode="count"),
            chk("alphafuse_ndcg_mean", 0.048273, 6),
            chk("alphafuse_ndcg_ci_lo", 0.048129, 6),
            chk("alphafuse_ndcg_ci_hi", 0.048416, 6),
            chk("sasrec_id_ndcg_mean", 0.039024, 6),
            chk("sasrec_id_ndcg_ci_lo", 0.038106, 6),
            chk("sasrec_id_ndcg_ci_hi", 0.039941, 6),
            chk("delta_vs_sasrec_id", 0.009249, 6),
            chk("delta_vs_sasrec_id_ci_lo", 0.008329, 6),
            chk("delta_vs_sasrec_id_ci_hi", 0.010169, 6),
            chk("delta_vs_sasrec_id_p", 3.4753606736507286e-08,
                mode="approx", tol=1e-11),
            chk("relative_gain_vs_sasrec_id_pct", 23.7, 1),
            chk("existing_reference_mean", 0.067337, 6),
            chk("delta_vs_existing_reference", -0.019065, 6),
            chk("delta_vs_existing_reference_ci_lo", -0.019347, 6),
            chk("delta_vs_existing_reference_ci_hi", -0.018783, 6),
            chk("delta_vs_existing_reference_p", 1.9554396631393096e-15,
                mode="approx", tol=1e-17),
            chk("alphafuse_hr10_mean", 0.089756, 6),
            chk("alphafuse_hr10_ci_lo", 0.089350, 6),
            chk("alphafuse_hr10_ci_hi", 0.090163, 6),
            chk("sasrec_id_hr10_mean", 0.073632, 6),
            chk("sasrec_id_hr10_ci_lo", 0.072351, 6),
            chk("sasrec_id_hr10_ci_hi", 0.074913, 6),
            chk("alphafuse_mrr_mean", 0.043412, 6),
            chk("sasrec_id_mrr_mean", 0.035281, 6),
            chk("bootstrap_replicates", 2000, mode="count"),
            chk("private_bootstrap_replay", 0, mode="count"),
            chk("private_endpoint_count", 16, mode="count"),
            chk("private_sidecar_count", 16, mode="count"),
            chk("private_endpoint_replay", 0, mode="count"),
        ],
        8, "exploratory", seeds=EEV3_SEEDS, notes=EEV3_NOTE))

    # ------- E-E V4: parser-default Normal(0,1) SASRec-ID sensitivity -------
    EEV4_SEEDS = list(range(20262301, 20262309))
    EEV4_ADJ = BR + "ee_v4_adjudication.json"
    EEV4_FROZEN = [
        "PREREG_EE_V4.md",
        BR + "ee_v4_common.py",
        BR + "test_ee_v4.py",
        BR + "run_ee_v4.py",
        BR + "eval_ee_v4.py",
        BR + "run_ee_v4_campaign.py",
        BR + "adjudicate_ee_v4.py",
    ]
    EEV4_NOTE = (
        "PREREG_EE_V4 and its adjudicator were committed before launch. Eight fresh "
        "parser-default Normal(0,1) SASRec-ID runs completed in four frozen two-process "
        "waves, followed by eight sealed evaluations and the committed adjudicator's "
        "first endpoint read. Verdict EEV4-ALPHAFUSE-ABOVE-NORMAL-SASREC: normal-init "
        "SASRec-ID NDCG@10 0.043065 [0.042645, 0.043486]; the cross-campaign V3 "
        "AlphaFuse-style package minus V4 normal-init control is +0.005207 "
        "[+0.004779, +0.005635]. Normal-init exceeds the earlier zero-init SASRec-ID "
        "control by +0.004042 [+0.003089, +0.004995] but remains below the existing "
        "full-model reference by -0.024272 [-0.024728, -0.023816]. This is countable "
        "only as outcome-known same-investigator comparator-fairness sensitivity. "
        "Phase/date and initialization are confounded; architecture, capacity, and "
        "allocation remain unequal. It is not independent confirmation, causal "
        "isolation, an equal-budget factorial, or SOTA.")
    C.append(cell(
        "eev4.aggregate", "ee_v4",
        "Parser-default Normal(0,1) SASRec-ID sensitivity",
        "aggregate metrics and three descriptive cross-campaign Welch contrasts",
        [EEV4_ADJ, EEV3_ADJ] + EEV4_FROZEN,
        "ee_v4_aggregate",
        {"adjud": EEV4_ADJ, "prior_adjud": EEV3_ADJ, "seeds": EEV4_SEEDS,
         "repository_commit": "6d3b404836fb57ee4efdb03846c0ccf2757bbce2",
         "upstream_commit": "b501a0540b609370df995ad06fb245859b10a18a"},
        [
            chk("verdict_alphafuse_above_normal_sasrec", 1, mode="count"),
            chk("countable_as_normal_init_sensitivity", 1, mode="count"),
            chk("independent_confirmation", 0, mode="count"),
            chk("general_sota_claim_allowed", 0, mode="count"),
            chk("n_units", 8, mode="count"),
            chk("normal_ndcg_mean", 0.043065, 6),
            chk("normal_ndcg_ci_lo", 0.042645, 6),
            chk("normal_ndcg_ci_hi", 0.043486, 6),
            chk("normal_hr10_mean", 0.079308, 6),
            chk("normal_hr10_ci_lo", 0.078714, 6),
            chk("normal_hr10_ci_hi", 0.079902, 6),
            chk("normal_mrr_mean", 0.039033, 6),
            chk("alpha_minus_normal", 0.005207, 6),
            chk("alpha_minus_normal_ci_lo", 0.004779, 6),
            chk("alpha_minus_normal_ci_hi", 0.005635, 6),
            chk("alpha_minus_normal_p", 1.0197151662903752e-09,
                mode="approx", tol=1e-12),
            chk("normal_minus_zero", 0.004042, 6),
            chk("normal_minus_zero_ci_lo", 0.003089, 6),
            chk("normal_minus_zero_ci_hi", 0.004995, 6),
            chk("normal_minus_reference", -0.024272, 6),
            chk("normal_minus_reference_ci_lo", -0.024728, 6),
            chk("normal_minus_reference_ci_hi", -0.023816, 6),
            chk("private_endpoint_count", 8, mode="count"),
            chk("private_endpoint_replay", 0, mode="count"),
        ],
        8, "exploratory", seeds=EEV4_SEEDS, notes=EEV4_NOTE))

    # ------- tfv2: pre-declared repaired-estimand campaign (PREREG_TAIL_FIR_V2) -------
    # Independent 8-vs-8 arms, but outcome-visible: the first independently verifiable
    # timestamp postdates the first result and adjudicator timing/custody do not support
    # confirmation status (manuscript S5.3(vii)).
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
                      8, expl,
                      notes="PREREG_TAIL_FIR_V2; outcome-visible, not confirmatory. PASS "
                            "under the frozen Holm arithmetic with E1 (adjudicate_tfv2.py "
                            "gates artifact integrity in the strict chain; verbatim record "
                            "TFV2_ADJUDICATION.md)."))

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
    PREDECLARED_PREFIXES = ("v2conf.", "officev3.", "t2.conngate.", "firprosp.")
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
    ml1m = by_id["fireff.ml1m.aggregate"]["recomputed"]
    T["fir_efficiency_ml1m_v1"] = "\n".join([
        "**MovieLens 1M R4 aggregate FIR replication and conditional parsimony.**",
        "",
        "| arm | filter parameters | mean NDCG@10 | arm - learned | simultaneous lower bound | frozen interpretation |",
        "|---|---:|---:|---:|---:|---|",
        f"| identity | {int(ml1m['identity_filter_trainable_params'])} | {ml1m['mean_identity']:.6f} | -0.000000 | - | learned replication failed |",
        f"| shared K=16 | {int(ml1m['shared_filter_trainable_params'])} | {ml1m['mean_shared']:.6f} | {ml1m['shared_minus_learned']:+.6f} | {ml1m['shared_simultaneous_lower']:+.6f} | NI-PASS |",
        f"| grouped K=16 | {int(ml1m['grouped_filter_trainable_params'])} | {ml1m['mean_grouped']:.6f} | {ml1m['grouped_minus_learned']:+.6f} | {ml1m['grouped_simultaneous_lower']:+.6f} | NI-PASS |",
        f"| low-rank K=16 | {int(ml1m['lowrank_filter_trainable_params'])} | {ml1m['mean_lowrank']:.6f} | {ml1m['lowrank_minus_learned']:+.6f} | {ml1m['lowrank_simultaneous_lower']:+.6f} | NI-PASS |",
        f"| learned per-channel K=16 | {int(ml1m['learned_filter_trainable_params']):,} | {ml1m['mean_learned']:.6f} | 0 | - | effect gate failed |",
        f"| pointwise placebo | {int(ml1m['pointwise_filter_trainable_params']):,} | {ml1m['mean_pointwise']:.6f} | {-ml1m['learned_pointwise_mean']:+.6f} | - | learned-pointwise failed |",
    ])
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
        "**Table 1c (regenerated): Musical_Instruments arm-by-arm comparison — NDCG@10, best-by-val, "
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
    elif a.submission:
        # Audit 2026-07-30: verifying a stale checked-in manifest against its
        # own recorded rules is insufficient when the embedded generator has
        # changed. Regenerate independently and require exact byte equality
        # before trusting the tracked artifact.
        fd, generated_path = tempfile.mkstemp(
            prefix="hstu_results_manifest.generated.", suffix=".json", dir=HERE)
        os.close(fd)
        try:
            write_manifest(generated_path)
            with open(generated_path, "rb") as generated_handle:
                generated_bytes = generated_handle.read()
            with open(a.manifest, "rb") as tracked_handle:
                tracked_bytes = tracked_handle.read()
            if generated_bytes != tracked_bytes:
                print("SUBMISSION GATE FAILED: tracked hstu_results_manifest.json "
                      "is not byte-identical to the embedded generator output; "
                      "run --write-manifest and review the semantic diff",
                      file=sys.stderr)
                sys.exit(4)
        finally:
            try:
                os.remove(generated_path)
            except FileNotFoundError:
                pass
    verify(a.manifest, a.tables_out, submission=a.submission)

if __name__ == "__main__":
    main()
