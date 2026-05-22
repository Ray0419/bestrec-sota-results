"""Consolidate current generated BEST-Rec artifacts into results_FINAL.json.

This script is intentionally forbidden from reading cache/*/v5_results.json.
Warm ranking metrics come from results_warm_loo.json, significance comes from
significance_corrected.json, and legacy fields are only preserved when there is
no current generated replacement.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from artifact_utils import (
    DATASETS,
    RUN_DIR,
    append_manifest_run,
    metric_fmt,
    p_marker,
    read_json,
    write_json,
)


FINAL_PATH = RUN_DIR / "results_FINAL.json"
WARM_PATH = RUN_DIR / "results_warm_loo.json"
SIG_PATH = RUN_DIR / "significance_corrected.json"
TABLES_PATH = RUN_DIR / "tables.json"

WARM_METHOD_MAP = {
    "ease_sbert": ("warm_mean", None),
    "popularity": ("baselines", "popularity"),
    "ease_pure": ("baselines", "ease_pure"),
    "higher_order_ease": ("baselines", "higher_order"),
    "higher_order": ("baselines", "higher_order"),
    "ials": ("baselines", "ials"),
    "lightgcn": ("baselines", "lightgcn"),
    "multivae": ("baselines", "multivae"),
}


def _empty_final() -> dict[str, Any]:
    return {
        "algorithm": "BEST-Rec v4/v5 repaired: script-driven LC2C/EASE+SBERT evaluation",
        "schema_version": 2,
        "config": {},
        "datasets": {},
        "_provenance": {
            "generated_by": "consolidate_final.py",
            "forbidden_inputs": ["cache/*/v5/v5_results.json"],
        },
    }


def _mean_std(block: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    mean = {
        "NDCG@10": block.get("ndcg_mean", block.get("NDCG@10")),
        "HR@10": block.get("hr_mean", block.get("HR@10")),
        "MRR": block.get("mrr_mean", block.get("MRR")),
    }
    std = {
        "NDCG@10": block.get("ndcg_std"),
        "HR@10": block.get("hr_std"),
        "MRR": block.get("mrr_std"),
    }
    return mean, std


def _sig(sig: dict[str, Any], dataset: str, method: str) -> dict[str, Any]:
    ds = sig.get(dataset, {})
    if method == "higher_order" and "higher_order_ease" in ds:
        method = "higher_order_ease"
    entry = ds.get(method, {})
    if not isinstance(entry, dict):
        return {}
    return {
        "p_vs_ease_sbert": entry.get("p_corrected", entry.get("p")),
        "p_uncorrected": entry.get("p"),
        "significance": entry.get("marker") or p_marker(entry.get("p_corrected", entry.get("p"))),
    }


def consolidate() -> dict[str, Any]:
    previous = read_json(FINAL_PATH, default=_empty_final())
    final = deepcopy(previous)
    final.setdefault("schema_version", 2)
    final.setdefault("datasets", {})
    final.setdefault("_provenance", {})
    final["_provenance"].update(
        {
            "generated_by": "consolidate_final.py",
            "forbidden_inputs": ["cache/*/v5/v5_results.json"],
            "primary_inputs": [WARM_PATH.name, SIG_PATH.name],
        }
    )

    warm = read_json(WARM_PATH)
    sig = read_json(SIG_PATH, default={})

    for dataset in DATASETS:
        final["datasets"].setdefault(dataset, {})
        ds_final = final["datasets"][dataset]
        ds_final.setdefault("baselines", {})

        warm_ds = warm.get(dataset, {})
        for warm_method, block in warm_ds.items():
            if not isinstance(block, dict) or warm_method not in WARM_METHOD_MAP:
                continue
            target_section, target_method = WARM_METHOD_MAP[warm_method]
            mean, std = _mean_std(block)
            mean = {k: v for k, v in mean.items() if v is not None}
            std = {k: v for k, v in std.items() if v is not None}

            if target_section == "warm_mean":
                ds_final.setdefault("warm_mean", {})
                ds_final.setdefault("warm_std", {})
                ds_final["warm_mean"].update(mean)
                ds_final["warm_std"].update(std)
                ds_final["warm_mean"]["source"] = WARM_PATH.name
                if block.get("n_pairs_per_fold"):
                    ds_final["warm_mean"]["n_pairs_per_fold"] = block["n_pairs_per_fold"]
            else:
                baseline = ds_final["baselines"].setdefault(target_method, {})
                baseline.update(mean)
                baseline.update(_sig(sig, dataset, target_method or warm_method))
                baseline["source"] = WARM_PATH.name
                if block.get("n_pairs_per_fold"):
                    baseline["n_pairs_per_fold"] = block["n_pairs_per_fold"]

        # Existing deep baselines are preserved but clearly marked if no current
        # per-user record file exists for the new SOTA audit.
        for method, baseline in ds_final.get("baselines", {}).items():
            if isinstance(baseline, dict) and "source" not in baseline:
                baseline["source"] = "legacy_prior_pipeline_preserved_by_consolidator"

    write_json(FINAL_PATH, final)
    append_manifest_run(
        command=["python", str(Path(__file__).name)],
        inputs=[WARM_PATH, SIG_PATH],
        outputs=[FINAL_PATH],
        datasets=DATASETS,
        note="Consolidated only current generated artifacts; no cache/v5 inputs.",
    )
    return final


def main() -> None:
    final = consolidate()
    print(f"Wrote {FINAL_PATH}")
    print("Warm NDCG@10 after consolidation:")
    for dataset in DATASETS:
        wm = final.get("datasets", {}).get(dataset, {}).get("warm_mean", {})
        if "NDCG@10" in wm:
            print(f"  {dataset:<12} {metric_fmt(wm['NDCG@10'])}")
    if TABLES_PATH.exists():
        print(f"Note: rerun build_tables.py after consolidation to refresh {TABLES_PATH.name}.")


if __name__ == "__main__":
    main()
