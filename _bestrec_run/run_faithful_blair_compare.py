"""Compare faithful BLaIR perpair NDCG@10 to:
  1. Simplified ``blair_text`` proxy (from sota_confirmatory_full_20260521)
  2. ``content_direct`` (from sota_confirmatory_full_20260521)
  3. CDR_validated (from results_cdr_variants_perpair_<ds>.jsonl)

For each comparator: per-(seed, fold, user_id, target_item_id) join, then
per-USER paired Wilcoxon (one-sided, faithful_blair > comparator) with
Holm correction across the 3 baselines per dataset.

Writes _bestrec_run/results_faithful_blair_significance.json.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from scipy.stats import wilcoxon


ROOT = Path("C:/Users/rayxc/Documents/R")
RUN_DIR = Path(__file__).parent
CONF_DIR = ROOT / "_bestrec_confirmatory" / "sota_confirmatory_full_20260521"

DATASETS = ["beauty", "fashion", "instruments", "books"]
SEEDS = [20260521, 20260522, 20260523]  # faithful_blair seeds (books has only 1)


def load_perpair(path, method_filter=None, seed_filter=None):
    """Return {(seed, fold_id, user_id, target_item_id) -> ndcg10}."""
    out = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if method_filter is not None and r.get("method") != method_filter:
                continue
            if seed_filter is not None and int(r["seed"]) not in seed_filter:
                continue
            out[(int(r["seed"]), int(r["fold_id"]),
                 int(r["user_id"]), int(r["target_item_id"]))] = float(r["ndcg10"])
    return out


def per_user_means(records):
    """records: {(seed,fold,uid,tid) -> ndcg10}.  Return {uid: mean_ndcg}."""
    by_user = defaultdict(list)
    for (seed, fold, uid, tid), v in records.items():
        by_user[uid].append(v)
    return {u: float(np.mean(vs)) for u, vs in by_user.items()}


def joined_per_user_means(cand, base):
    """Compute per-user means only over the intersection of records."""
    common = set(cand) & set(base)
    cand_user = defaultdict(list)
    base_user = defaultdict(list)
    for key in common:
        _, _, uid, _ = key
        cand_user[uid].append(cand[key])
        base_user[uid].append(base[key])
    cm = {u: float(np.mean(vs)) for u, vs in cand_user.items()}
    bm = {u: float(np.mean(vs)) for u, vs in base_user.items()}
    return cm, bm, len(common)


def wilcoxon_one_sided(cm, bm, name):
    common_users = sorted(set(cm) & set(bm))
    if not common_users:
        return {"comparison": name, "n_users": 0, "p_raw": 1.0,
                "delta": 0.0, "cand_mean": 0.0, "base_mean": 0.0}
    diffs = np.array([cm[u] - bm[u] for u in common_users])
    if np.allclose(diffs, 0):
        p = 1.0
    else:
        p = float(wilcoxon(diffs, alternative="greater", zero_method="wilcox").pvalue)
    return {
        "comparison": name,
        "n_users": int(len(common_users)),
        "cand_mean": float(np.mean([cm[u] for u in common_users])),
        "base_mean": float(np.mean([bm[u] for u in common_users])),
        "delta": float(np.mean(diffs)),
        "p_raw": float(p),
    }


def holm_adjust(comparisons):
    """Holm-Bonferroni correction across the comparisons in this list."""
    sorted_rows = sorted(comparisons, key=lambda x: x["p_raw"])
    m = len(sorted_rows)
    active = True
    out = []
    for i, row in enumerate(sorted_rows):
        thresh = 0.05 / max(1, m - i)
        sig = bool(active and row["p_raw"] <= thresh)
        if not sig:
            active = False
        marker = "***" if sig and row["p_raw"] < 0.001 else \
                 "**" if sig and row["p_raw"] < 0.01 else \
                 "*" if sig else "n.s."
        out.append({**row, "holm_threshold": float(thresh),
                    "holm_significant": sig, "marker": marker})
    return sorted(out, key=lambda x: x["comparison"])


def compare_dataset(ds):
    """Returns dict with summary stats + Holm-adjusted comparisons."""
    print(f"\n=== {ds.upper()} ===")
    blair_path = RUN_DIR / f"results_faithful_blair_perpair_{ds}.jsonl"
    if not blair_path.exists():
        return {"dataset": ds, "error": "faithful_blair_perpair_missing"}
    cand = load_perpair(blair_path)
    cand_seeds = sorted({k[0] for k in cand})
    print(f"  faithful_blair n_records={len(cand):,}  seeds={cand_seeds}")
    cand_seed_filter = set(cand_seeds)

    # Comparator 1: simplified blair_text (from confirmatory run)
    simp_blair = load_perpair(
        CONF_DIR / f"cold_full_catalog_records_{ds}.jsonl",
        method_filter="blair_text",
        seed_filter=cand_seed_filter,
    )
    # Comparator 2: content_direct
    content = load_perpair(
        CONF_DIR / f"cold_full_catalog_records_{ds}.jsonl",
        method_filter="content_direct",
        seed_filter=cand_seed_filter,
    )
    # Comparator 3: CDR_validated (from results_cdr_variants_perpair_<ds>.jsonl)
    cdr_path = RUN_DIR / f"results_cdr_variants_perpair_{ds}.jsonl"
    cdr = {}
    if cdr_path.exists():
        cdr = load_perpair(cdr_path, method_filter="CDR_validated",
                            seed_filter=cand_seed_filter)
    print(f"  blair_text(simplified) n={len(simp_blair):,}, content_direct n={len(content):,}, CDR_validated n={len(cdr):,}")

    # Compute paired per-user comparisons. Use the intersection of records
    # (per (seed, fold, uid, tid)) so we're comparing on exactly the same
    # held-out pairs.
    comparisons = []
    base_means_dump = {}
    if simp_blair:
        cm, bm, n_common = joined_per_user_means(cand, simp_blair)
        comp = wilcoxon_one_sided(cm, bm, "faithful_blair > blair_text_simplified")
        comp["intersection_records"] = n_common
        comparisons.append(comp)
        base_means_dump["blair_text_simplified"] = bm
    if content:
        cm, bm, n_common = joined_per_user_means(cand, content)
        comp = wilcoxon_one_sided(cm, bm, "faithful_blair > content_direct")
        comp["intersection_records"] = n_common
        comparisons.append(comp)
        base_means_dump["content_direct"] = bm
    if cdr:
        cm, bm, n_common = joined_per_user_means(cand, cdr)
        comp = wilcoxon_one_sided(cm, bm, "faithful_blair > CDR_validated")
        comp["intersection_records"] = n_common
        comparisons.append(comp)
        base_means_dump["CDR_validated"] = bm

    adjusted = holm_adjust(comparisons)

    # Headline NDCG numbers (mean of all faithful_blair NDCG@10 records)
    faithful_mean = float(np.mean(list(cand.values()))) if cand else 0.0

    # Per-fold mean+std (use perfold from results_faithful_blair.json if avail)
    fb = json.load(open(RUN_DIR / "results_faithful_blair.json"))
    pf = fb["datasets"][ds]["perfold_ndcg10"]

    result = {
        "dataset": ds,
        "candidate_method": "faithful_blair",
        "faithful_blair_micro_mean_ndcg10": faithful_mean,
        "faithful_blair_perfold_mean": float(np.mean(pf)),
        "faithful_blair_perfold_std": float(np.std(pf)),
        "n_pairs_faithful_blair": len(cand),
        "n_pairs_blair_text_simplified": len(simp_blair),
        "n_pairs_content_direct": len(content),
        "n_pairs_cdr_validated": len(cdr),
        "comparisons_holm_corrected": adjusted,
    }
    for row in adjusted:
        print(f"  {row['comparison']:<55} n_u={row['n_users']:>6} "
              f"cand={row['cand_mean']:.4f} base={row['base_mean']:.4f} "
              f"delta={row['delta']:+.4f} p={row['p_raw']:.3e} {row['marker']}")
    return result


def main():
    out = {
        "schema_version": 1,
        "candidate_method": "faithful_blair",
        "comparators": ["blair_text_simplified", "content_direct", "CDR_validated"],
        "wilcoxon": "per-user paired one-sided (faithful_blair > baseline), Holm correction within dataset",
        "datasets": {},
    }
    for ds in DATASETS:
        out["datasets"][ds] = compare_dataset(ds)
    outpath = RUN_DIR / "results_faithful_blair_significance.json"
    outpath.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {outpath}")


if __name__ == "__main__":
    main()
