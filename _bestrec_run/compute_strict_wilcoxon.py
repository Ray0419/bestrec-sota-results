"""Compute per-USER paired Wilcoxon (Holm-corrected) for the strict-confirmatory
SOTA gate, scanning all `results_*_perpair_<ds>.jsonl` files and
`results_warm_loo_perfold_<ds>.json` files.

This closes gap #1 of the SOTA hunt residual-gap list:
- For cold-item full-catalog: pair every cold candidate's per-USER NDCG@10
  against `CDR_validated` (the headline algorithm).
- For warm-LOO: pair every warm baseline's per-USER NDCG@10 against
  `ease_sbert` (the headline algorithm).

Outputs:
  _bestrec_run/results_strict_wilcoxon.json

Each section contains the per-dataset raw two-sided p, the per-dataset
one-sided "headline > baseline" p, and the Holm-Bonferroni adjusted p
across the per-dataset comparisons (within a given baseline group).

Usage:
    cd _bestrec_run
    uv run python compute_strict_wilcoxon.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parent
DATASETS = ["beauty", "fashion", "instruments", "books"]

# ----------------------------------------------------------------------------
# Cold-item full-catalog: read per-pair JSONL records and aggregate per USER
# ----------------------------------------------------------------------------

def load_perpair_records(path: str) -> dict[int, list[float]]:
    """Return {user_id: [ndcg10, ...]} aggregating all per-pair records."""
    per_user: dict[int, list[float]] = defaultdict(list)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            uid = r.get("user_id")
            v = r.get("ndcg10") or r.get("NDCG@10") or r.get("ndcg")
            if uid is None or v is None:
                continue
            per_user[int(uid)].append(float(v))
    return per_user


def load_perpair_records_per_variant(path: str, variant: str) -> dict[int, list[float]]:
    """For files that store multiple variants in the same JSONL (e.g. CDR variants),
    select records matching the given variant string."""
    per_user: dict[int, list[float]] = defaultdict(list)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("variant") != variant and r.get("method") != variant:
                continue
            uid = r.get("user_id")
            v = r.get("ndcg10") or r.get("NDCG@10") or r.get("ndcg")
            if uid is None or v is None:
                continue
            per_user[int(uid)].append(float(v))
    return per_user


def per_user_mean(per_user: dict[int, list[float]]) -> dict[int, float]:
    return {u: float(np.mean(vs)) for u, vs in per_user.items() if vs}


def paired_wilcoxon(cand: dict[int, float], base: dict[int, float],
                     alternative: str = "greater") -> dict[str, Any]:
    """Return paired Wilcoxon stats. Pair on common user IDs."""
    common = sorted(set(cand) & set(base))
    if not common:
        return {"n_users": 0, "p_raw": float("nan"), "delta": float("nan"),
                 "cand_mean": float("nan"), "base_mean": float("nan")}
    diffs = np.array([cand[u] - base[u] for u in common], dtype=np.float64)
    cand_m = float(np.mean([cand[u] for u in common]))
    base_m = float(np.mean([base[u] for u in common]))
    delta = float(np.mean(diffs))
    if np.allclose(diffs, 0.0):
        p_raw = 1.0
    else:
        try:
            p_raw = float(wilcoxon(diffs, alternative=alternative,
                                     zero_method="wilcox").pvalue)
        except Exception:
            p_raw = float("nan")
    return {"n_users": len(common), "p_raw": p_raw, "delta": delta,
            "cand_mean": cand_m, "base_mean": base_m}


def holm_correct(p_values: list[float]) -> list[float]:
    """Holm-Bonferroni step-down. Returns adjusted p in the same order."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adj = [None] * m
    prev = 0.0
    for rank, i in enumerate(order):
        p = p_values[i] * (m - rank)
        p = min(p, 1.0)
        p = max(p, prev)
        adj[i] = p
        prev = p
    return adj


def marker(p: float) -> str:
    if p < 1e-3:
        return "***"
    if p < 1e-2:
        return "**"
    if p < 5e-2:
        return "*"
    return "n.s."


# ----------------------------------------------------------------------------
# Cold-item section
# ----------------------------------------------------------------------------

COLD_CANDIDATES_HEADLINE = "CDR_validated"

COLD_BASELINES = {
    # name -> (perpair_file_glob, variant_filter_or_None)
    "faithful_dropoutnet":   ("results_faithful_dropoutnet_perpair_{ds}.jsonl", None),
    "faithful_clcrec":       ("results_faithful_clcrec_perpair_{ds}.jsonl", None),
    "faithful_blair":        ("results_faithful_blair_perpair_{ds}.jsonl", None),
    "rqvae_knn":             ("results_rqvae_knn_perpair_{ds}.jsonl", None),
    "meltlike_proxy":        ("results_meltlike_proxy_perpair_{ds}.jsonl", None),
}

# The CDR_validated per-pair records live inside the CDR variants JSONL alongside CDR_K
CDR_PERPAIR = "results_cdr_variants_perpair_{ds}.jsonl"


def load_cdr_validated(ds: str) -> dict[int, float]:
    path = str(ROOT / CDR_PERPAIR.format(ds=ds))
    pp = load_perpair_records_per_variant(path, "CDR_validated")
    if not pp:
        # Fallback: maybe the 5-seed Books file used a different path
        if ds == "books":
            alt = str(ROOT / "results_poc_cdr_books_5seed_perpair_books.jsonl")
            pp = load_perpair_records(alt)
    return per_user_mean(pp)


def run_cold_section() -> dict[str, Any]:
    cand_per_user: dict[str, dict[int, float]] = {ds: load_cdr_validated(ds) for ds in DATASETS}

    section: dict[str, Any] = {"headline": COLD_CANDIDATES_HEADLINE,
                                 "task": "cold_item_full_catalog",
                                 "baselines": {}}

    for base_name, (pattern, variant) in COLD_BASELINES.items():
        per_ds: dict[str, dict[str, Any]] = {}
        raw_ps: list[float] = []
        order_dsets: list[str] = []
        for ds in DATASETS:
            path = str(ROOT / pattern.format(ds=ds))
            if variant:
                base_pu = per_user_mean(load_perpair_records_per_variant(path, variant))
            else:
                base_pu = per_user_mean(load_perpair_records(path))
            if not base_pu:
                per_ds[ds] = {"available": False, "reason": f"no per-pair records at {path}"}
                continue
            res = paired_wilcoxon(cand_per_user.get(ds, {}), base_pu, alternative="greater")
            per_ds[ds] = {"available": True, **res, "marker_raw": marker(res["p_raw"])}
            raw_ps.append(res["p_raw"])
            order_dsets.append(ds)
        if raw_ps:
            holm = holm_correct(raw_ps)
            for i, ds in enumerate(order_dsets):
                per_ds[ds]["p_holm"] = holm[i]
                per_ds[ds]["marker_holm"] = marker(holm[i])
        section["baselines"][base_name] = per_ds
    return section


# ----------------------------------------------------------------------------
# Warm-LOO section
# ----------------------------------------------------------------------------

WARM_CANDIDATES_HEADLINE = "ease_sbert"

WARM_PERFOLD_FILE = "results_warm_loo_perfold_{ds}.json"

WARM_BASELINES = {
    # name -> (perfold_json_path_template, schema)
    # schema 'warm_loo': existing per-fold JSON from run_warm_loo.py
    # schema 'lightgcn_strict_perfold': from run_lightgcn_strict.py
    # schema 'multivae_strict_perfold': from run_multivae_strict.py
    # schema 'ials_strict_perfold': new this batch
    "popularity":   (WARM_PERFOLD_FILE, "warm_loo", "popularity"),
    "ease_pure":    (WARM_PERFOLD_FILE, "warm_loo", "ease_pure"),
    "higher_order_ease": (WARM_PERFOLD_FILE, "warm_loo", "higher_order_ease"),
    "lightgcn_strict":   ("results_lightgcn_strict_perfold_{ds}.json", "perfold_records", None),
    "multivae_strict":   ("results_multivae_strict_perfold_{ds}.json", "perfold_records", None),
    "ials_strict":       ("results_ials_strict_perfold_{ds}.json", "perfold_records", None),
}


def load_warm_loo_perfold(path: str, method: str) -> dict[int, list[float]]:
    """Load warm-LOO per-(fold, user, ndcg10) records for a given method
    from the run_warm_loo.py output schema."""
    per_user: dict[int, list[float]] = defaultdict(list)
    if not os.path.exists(path):
        return {}
    try:
        d = json.load(open(path))
    except json.JSONDecodeError:
        return {}
    methods = d.get("methods", {})
    rows = methods.get(method, [])
    for r in rows:
        if isinstance(r, list) and len(r) >= 3:
            _, uid, val = r[0], r[1], r[2]
            per_user[int(uid)].append(float(val))
        elif isinstance(r, dict):
            uid = r.get("user_id"); v = r.get("ndcg10") or r.get("ndcg")
            if uid is not None and v is not None:
                per_user[int(uid)].append(float(v))
    return per_user


def load_perfold_records(path: str) -> dict[int, list[float]]:
    """Schema: top-level dict with a `records` key listing
    {seed, fold, user_id, target_item_id, ndcg10}. Tolerates a 'method' key."""
    per_user: dict[int, list[float]] = defaultdict(list)
    if not os.path.exists(path):
        return {}
    try:
        d = json.load(open(path))
    except json.JSONDecodeError:
        return {}
    rows = d.get("records") or d.get("perpair") or d.get("perfold_records") or []
    if isinstance(rows, dict):
        rows = sum(rows.values(), [])  # flatten if keyed by something
    for r in rows:
        if not isinstance(r, dict):
            continue
        uid = r.get("user_id"); v = r.get("ndcg10") or r.get("NDCG@10") or r.get("ndcg")
        if uid is None or v is None:
            continue
        per_user[int(uid)].append(float(v))
    return per_user


def run_warm_section() -> dict[str, Any]:
    # Candidate: ease_sbert from results_warm_loo_perfold_<ds>.json::methods.ease_sbert
    cand_per_user: dict[str, dict[int, float]] = {}
    for ds in DATASETS:
        path = str(ROOT / WARM_PERFOLD_FILE.format(ds=ds))
        pu = load_warm_loo_perfold(path, "ease_sbert")
        cand_per_user[ds] = per_user_mean(pu)

    section: dict[str, Any] = {"headline": WARM_CANDIDATES_HEADLINE,
                                 "task": "warm_loo_full_item_ranking",
                                 "baselines": {}}

    for base_name, (pattern, schema, method_key) in WARM_BASELINES.items():
        if schema == "warm_loo" and method_key == WARM_CANDIDATES_HEADLINE:
            continue  # don't compare ease_sbert to itself
        per_ds: dict[str, dict[str, Any]] = {}
        raw_ps: list[float] = []
        order_dsets: list[str] = []
        for ds in DATASETS:
            path = str(ROOT / pattern.format(ds=ds))
            if schema == "warm_loo":
                base_pu = per_user_mean(load_warm_loo_perfold(path, method_key))
            else:
                base_pu = per_user_mean(load_perfold_records(path))
            if not base_pu:
                per_ds[ds] = {"available": False, "reason": f"no per-fold records at {path}"}
                continue
            res = paired_wilcoxon(cand_per_user.get(ds, {}), base_pu, alternative="greater")
            per_ds[ds] = {"available": True, **res, "marker_raw": marker(res["p_raw"])}
            raw_ps.append(res["p_raw"])
            order_dsets.append(ds)
        if raw_ps:
            holm = holm_correct(raw_ps)
            for i, ds in enumerate(order_dsets):
                per_ds[ds]["p_holm"] = holm[i]
                per_ds[ds]["marker_holm"] = marker(holm[i])
        section["baselines"][base_name] = per_ds
    return section


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main() -> int:
    cold = run_cold_section()
    warm = run_warm_section()
    out = {"schema_version": 1,
            "description": "Strict per-USER paired Wilcoxon (one-sided, headline > baseline) with "
                            "Holm-Bonferroni correction across per-dataset comparisons within each baseline. "
                            "Headline algorithms: cold = CDR_validated, warm = ease_sbert.",
            "cold_item_full_catalog": cold,
            "warm_loo": warm}
    out_path = ROOT / "results_strict_wilcoxon.json"
    json.dump(out, open(out_path, "w"), indent=2,
               default=lambda o: float(o) if hasattr(o, "item") else str(o))
    print(f"wrote {out_path}")

    print("\n=== Cold-item summary ===")
    for base_name, per_ds in cold["baselines"].items():
        print(f"  {base_name}:")
        for ds in DATASETS:
            v = per_ds.get(ds, {})
            if not v.get("available"):
                print(f"    {ds:>12}: N/A ({v.get('reason', '?')})")
                continue
            print(f"    {ds:>12}: n={v['n_users']:>5} cand={v['cand_mean']:.4f} "
                  f"base={v['base_mean']:.4f} delta={v['delta']:+.4f} "
                  f"p_raw={v['p_raw']:.2e} p_holm={v.get('p_holm', float('nan')):.2e} "
                  f"{v.get('marker_holm', '?')}")

    print("\n=== Warm-LOO summary ===")
    for base_name, per_ds in warm["baselines"].items():
        print(f"  {base_name}:")
        for ds in DATASETS:
            v = per_ds.get(ds, {})
            if not v.get("available"):
                print(f"    {ds:>12}: N/A ({v.get('reason', '?')})")
                continue
            print(f"    {ds:>12}: n={v['n_users']:>5} cand={v['cand_mean']:.4f} "
                  f"base={v['base_mean']:.4f} delta={v['delta']:+.4f} "
                  f"p_raw={v['p_raw']:.2e} p_holm={v.get('p_holm', float('nan')):.2e} "
                  f"{v.get('marker_holm', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
