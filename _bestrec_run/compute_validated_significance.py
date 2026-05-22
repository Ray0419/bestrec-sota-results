"""Significance for validation-selected LC2C++ against LC2C V2."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

from artifact_utils import DATASETS, RUN_DIR, read_json, write_json, append_manifest_run


def _user_mean(rows):
    by = defaultdict(list)
    for row in rows:
        u = row[4]
        val = row[7]
        by[int(u)].append(float(val))
    return {u: float(np.mean(v)) for u, v in by.items()}


def _fmt_p(p: float) -> str:
    if p < 1e-300:
        return "<1e-300"
    if p < 1e-10:
        return f"{p:.2e}"
    return f"{p:.4g}"


def holm(rows, alpha=0.05):
    sorted_rows = sorted(rows, key=lambda x: x["p_raw"])
    m = len(sorted_rows)
    still_reject = True
    out = {}
    for i, row in enumerate(sorted_rows):
        threshold = alpha / (m - i)
        sig = bool(still_reject and row["p_raw"] <= threshold)
        if not sig:
            still_reject = False
        marker = "***" if sig and row["p_raw"] < 0.001 else "**" if sig and row["p_raw"] < 0.01 else "*" if sig else "n.s."
        out[row["dataset"]] = {**row, "holm_threshold": threshold, "holm_sig": sig, "marker": marker}
    return out


def main() -> None:
    rows = []
    method = "lc2cpp_validated_margin"
    for dataset in DATASETS:
        path = RUN_DIR / f"results_lc2cpp_validated_perpair_{dataset}.json"
        data = read_json(path)
        methods = data["methods"]
        valid = _user_mean(methods[method])
        base = _user_mean(methods["lc2c_v2"])
        common = sorted(set(valid) & set(base))
        diffs = np.array([valid[u] - base[u] for u in common], dtype=np.float64)
        if len(common) == 0 or np.all(diffs == 0):
            p = 1.0
        else:
            p = float(wilcoxon(diffs, alternative="greater", zero_method="wilcox").pvalue)
        rows.append({
            "dataset": dataset,
            "comparison": f"{method} > lc2c_v2",
            "n_users": len(common),
            "mean_delta": float(diffs.mean()) if len(common) else None,
            "positive_users": int((diffs > 0).sum()),
            "negative_users": int((diffs < 0).sum()),
            "zero_users": int((diffs == 0).sum()),
            "p_raw": p,
            "p_raw_str": _fmt_p(p),
        })
    out = {
        "schema_version": 1,
        "correction_family": "Holm across four dataset-level LC2C++ validated > LC2C V2 comparisons",
        "sample_unit": "per-user mean NDCG@10 from validation-selected cold-fold-only records",
        "method": method,
        "comparisons": holm(rows),
    }
    write_json(RUN_DIR / "significance_lc2cpp_validated.json", out)
    append_manifest_run(
        command=["python", "compute_validated_significance.py"],
        inputs=[*(RUN_DIR.glob("results_lc2cpp_validated_perpair_*.json"))],
        outputs=[RUN_DIR / "significance_lc2cpp_validated.json"],
        datasets=DATASETS,
        note="Holm-corrected per-user significance for validation-selected LC2C++.",
    )
    for dataset in DATASETS:
        c = out["comparisons"][dataset]
        print(f"{dataset:<12} delta={c['mean_delta']:.6f} p={c['p_raw_str']:<10} marker={c['marker']}")


if __name__ == "__main__":
    main()
