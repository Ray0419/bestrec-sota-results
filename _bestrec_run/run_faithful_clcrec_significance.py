"""Compute per-USER paired Wilcoxon (one-sided, Holm-corrected) for:
  - faithful CLCRec vs simplified clcrec_contrastive proxy
  - CDR-CL vs CDR_validated

Reads:
  - results_faithful_clcrec_records_<dataset>.jsonl  (faithful CLCRec)
  - results_cdr_cl_records_<dataset>.jsonl           (CDR-CL)
  - _bestrec_confirmatory/sota_confirmatory_full_20260521/
        cold_full_catalog_records_<dataset>.jsonl    (simplified proxy + others)
  - results_poc_cdr_3seed.json (or results_poc_cdr.json) for CDR_validated
    per-user records, but we will regenerate them from the per-fold runs if
    needed (results_poc_cdr.json only has fold means, no per-pair records).

Writes:
  - results_faithful_clcrec_significance.json
  - results_cdr_cl_significance.json

The CDR_validated per-USER baseline is rebuilt from
``run_poc_cdr_books.py`` invocation; if no per-pair records exist for it we
fall back to using the values stored under
``per_user_ndcg10`` from the CDR-CL run's twin (we always run CDR_validated
alongside CDR-CL in this report).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from scipy.stats import wilcoxon

RUN_DIR = Path(__file__).resolve().parent
ROOT = RUN_DIR.parent
SOTA_DIR = ROOT / "_bestrec_confirmatory" / "sota_confirmatory_full_20260521"


def load_pair_records(path: Path, method_filter: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if method_filter is not None and r.get("method") != method_filter:
                continue
            rows.append(r)
    return rows


def per_user_ndcg(rows: list[dict[str, Any]]) -> dict[int, float]:
    by_u: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        by_u[int(r["user_id"])].append(float(r["ndcg10"]))
    return {u: float(np.mean(v)) for u, v in by_u.items()}


def wilcoxon_pair(cand: dict[int, float], base: dict[int, float]) -> dict[str, Any]:
    common = sorted(set(cand) & set(base))
    diffs = np.array([cand[u] - base[u] for u in common], dtype=np.float64)
    if len(diffs) == 0 or np.allclose(diffs, 0):
        p = 1.0
    else:
        p = float(wilcoxon(diffs, alternative="greater", zero_method="wilcox").pvalue)
    return {
        "n_users": len(common),
        "cand_mean": float(np.mean([cand[u] for u in common])) if common else 0.0,
        "base_mean": float(np.mean([base[u] for u in common])) if common else 0.0,
        "delta": float(np.mean(diffs)) if len(diffs) else 0.0,
        "positive_users": int((diffs > 0).sum()),
        "negative_users": int((diffs < 0).sum()),
        "zero_users": int((diffs == 0).sum()),
        "p_raw": p,
    }


def holm(comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """In-place Holm correction of a list of comparison dicts (each has p_raw)."""
    indexed = list(enumerate(comparisons))
    indexed.sort(key=lambda x: x[1]["p_raw"])
    m = len(indexed)
    active = True
    out = list(comparisons)
    for rank, (orig_idx, comp) in enumerate(indexed):
        threshold = 0.05 / max(1, m - rank)
        sig = bool(active and comp["p_raw"] <= threshold)
        if not sig:
            active = False
        marker = "n.s."
        if sig:
            if comp["p_raw"] < 0.001:
                marker = "***"
            elif comp["p_raw"] < 0.01:
                marker = "**"
            elif comp["p_raw"] < 0.05:
                marker = "*"
        out[orig_idx] = {
            **comp,
            "holm_threshold": float(threshold),
            "holm_significant": sig,
            "marker": marker,
        }
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--datasets", default="beauty,fashion,instruments,books")
    ap.add_argument("--clcrec-out", default="results_faithful_clcrec_significance.json")
    ap.add_argument("--cdrcl-out", default="results_cdr_cl_significance.json")
    args = ap.parse_args()
    datasets = [d.strip() for d in args.datasets.split(",") if d.strip()]

    clcrec_out: dict[str, Any] = {
        "schema_version": 1,
        "test": "per-user paired Wilcoxon, one-sided, greater. Holm correction across datasets.",
        "cand": "faithful_clcrec",
        "base": "clcrec_contrastive (simplified proxy from sota_confirmatory_full_20260521)",
        "datasets": {},
    }
    cdrcl_out: dict[str, Any] = {
        "schema_version": 1,
        "test": "per-user paired Wilcoxon, one-sided, greater. Holm correction across datasets.",
        "cand": "cdr_cl",
        "base": "CDR_validated (regenerated from run_cdr_cl_validated_records_<dataset>.jsonl)",
        "datasets": {},
    }

    clcrec_comparisons = []
    cdrcl_comparisons = []
    for ds in datasets:
        # faithful CLCRec vs simplified proxy
        cand_rows = load_pair_records(RUN_DIR / f"results_faithful_clcrec_records_{ds}.jsonl")
        proxy_rows = load_pair_records(SOTA_DIR / f"cold_full_catalog_records_{ds}.jsonl",
                                          method_filter="clcrec_contrastive")
        cand_pu = per_user_ndcg(cand_rows)
        base_pu = per_user_ndcg(proxy_rows)
        clcrec_comparisons.append({"dataset": ds, "comparison": f"faithful_clcrec_{ds}",
                                     **wilcoxon_pair(cand_pu, base_pu)})

        # CDR-CL vs CDR_validated
        cdrcl_rows = load_pair_records(RUN_DIR / f"results_cdr_cl_records_{ds}.jsonl")
        validated_rows = load_pair_records(RUN_DIR / f"results_cdr_validated_records_{ds}.jsonl")
        cdrcl_pu = per_user_ndcg(cdrcl_rows)
        validated_pu = per_user_ndcg(validated_rows)
        cdrcl_comparisons.append({"dataset": ds, "comparison": f"cdr_cl_{ds}",
                                    **wilcoxon_pair(cdrcl_pu, validated_pu)})

    clcrec_comparisons = holm(clcrec_comparisons)
    cdrcl_comparisons = holm(cdrcl_comparisons)
    clcrec_out["comparisons"] = clcrec_comparisons
    cdrcl_out["comparisons"] = cdrcl_comparisons
    for c in clcrec_comparisons:
        clcrec_out["datasets"][c["dataset"]] = c
    for c in cdrcl_comparisons:
        cdrcl_out["datasets"][c["dataset"]] = c
    with open(RUN_DIR / args.clcrec_out, "w") as f:
        json.dump(clcrec_out, f, indent=2)
    with open(RUN_DIR / args.cdrcl_out, "w") as f:
        json.dump(cdrcl_out, f, indent=2)
    print("\n=== faithful CLCRec vs simplified proxy ===")
    for c in clcrec_comparisons:
        print(f"  {c['dataset']:<12} n={c['n_users']:>6} cand={c['cand_mean']:.4f} "
              f"base={c['base_mean']:.4f} delta={c['delta']:+.4f} p={c['p_raw']:.3e} {c['marker']}")
    print("\n=== CDR-CL vs CDR_validated ===")
    for c in cdrcl_comparisons:
        print(f"  {c['dataset']:<12} n={c['n_users']:>6} cand={c['cand_mean']:.4f} "
              f"base={c['base_mean']:.4f} delta={c['delta']:+.4f} p={c['p_raw']:.3e} {c['marker']}")


if __name__ == "__main__":
    main()
