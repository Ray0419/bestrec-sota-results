"""Build canonical paper tables from generated BEST-Rec artifacts.

This script is the only source of empirical table cells for the PDF builder.
It deliberately avoids cache/*/v5_results.json and records enough provenance
for validation to catch stale or hand-edited paper numbers.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from artifact_utils import (
    DATASET_LABELS,
    DATASET_STATS,
    DATASETS,
    MANDATORY_SOTA_BASELINES,
    METHOD_LABELS,
    RUN_DIR,
    append_manifest_run,
    cold_record_to_dict,
    fold_count_summary,
    metric_fmt,
    metric_pm,
    p_marker,
    read_json,
    warm_record_to_dict,
    write_json,
)


FINAL_PATH = RUN_DIR / "results_FINAL.json"
WARM_PATH = RUN_DIR / "results_warm_loo.json"
SIG_WARM_PATH = RUN_DIR / "significance_corrected.json"
COLD_PATH = RUN_DIR / "results_cold_item_v2.json"
SIG_COLD_PATH = RUN_DIR / "significance_cold_item_corrected.json"
BOOT_COLD_PATH = RUN_DIR / "significance_cold_item_bootstrap.json"
SOTA_AUDIT_PATH = RUN_DIR / "results_sota_audit.json"
VALIDATED_PATH = RUN_DIR / "results_lc2cpp_validated.json"
VALIDATED_SIG_PATH = RUN_DIR / "significance_lc2cpp_validated.json"
TABLES_PATH = RUN_DIR / "tables.json"
SIGNIFICANCE_STD_PATH = RUN_DIR / "significance.json"


def _metric(block: dict[str, Any], name: str, fallback: Any = None) -> Any:
    if not isinstance(block, dict):
        return fallback
    return block.get(name, block.get(name.upper(), fallback))


def _warm_counts(warm: dict[str, Any], dataset: str, method: str = "ease_sbert") -> list[int]:
    block = warm.get(dataset, {}).get(method, {})
    counts = block.get("n_pairs_per_fold")
    if counts:
        return [int(x) for x in counts]
    methods = block.get("per_user", {})
    if methods:
        records = methods
    else:
        records = block.get("records", [])
    counter: Counter[int] = Counter()
    for row in records:
        rec = warm_record_to_dict(dataset, method, row)
        counter[int(rec["fold_id"])] += 1
    return [counter[k] for k in sorted(counter)]


def _cold_counts(cold: dict[str, Any], dataset: str, method: str = "lc2c_v2") -> list[int]:
    rows = cold.get(dataset, {}).get("per_pair", {}).get(method, [])
    perpair_path = RUN_DIR / f"results_cold_item_v2_perpair_{dataset}.json"
    if not rows and perpair_path.exists():
        perpair = read_json(perpair_path, default={})
        rows = perpair.get("methods", {}).get(method, [])
    counter: Counter[int] = Counter()
    for row in rows:
        rec = cold_record_to_dict(dataset, method, row)
        counter[int(rec["fold_id"])] += 1
    return [counter[k] for k in sorted(counter)]


def _sig_marker(sig: dict[str, Any], dataset: str, method: str) -> str:
    ds = sig.get(dataset, {})
    method = "higher_order_ease" if method == "higher_order" and "higher_order_ease" in ds else method
    entry = ds.get(method, {})
    if isinstance(entry, dict):
        return entry.get("marker") or p_marker(entry.get("p_corrected", entry.get("p")))
    return p_marker(entry)


def _sig_p(sig: dict[str, Any], dataset: str, method: str) -> Any:
    ds = sig.get(dataset, {})
    method = "higher_order_ease" if method == "higher_order" and "higher_order_ease" in ds else method
    entry = ds.get(method, {})
    if isinstance(entry, dict):
        return entry.get("p_corrected", entry.get("p"))
    return entry


def _baseline_ndcg(final: dict[str, Any], dataset: str, method: str) -> Any:
    final_datasets = final.get("datasets", final)
    baselines = final_datasets.get(dataset, {}).get("baselines", {})
    if method in baselines:
        return baselines[method].get("NDCG@10", baselines[method].get("ndcg10"))
    alt = "higher_order_ease" if method == "higher_order" else method
    if alt in baselines:
        return baselines[alt].get("NDCG@10", baselines[alt].get("ndcg10"))
    return None


def build_standard_significance(sig_warm: dict[str, Any], sig_cold: dict[str, Any], boot_cold: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "correction_family": {
            "warm": "Holm within dataset over compared baselines",
            "cold_item": "Holm within dataset over compared baselines",
        },
        "sample_unit": {
            "warm": "per-user leave-one-out records",
            "cold_item": "per-user target-item ranking records",
            "cold_item_bootstrap": "user/item/fold clustered bootstrap where available",
        },
        "source_records": {
            "warm": str(WARM_PATH.name),
            "cold_item": str(COLD_PATH.name),
        },
        "warm": sig_warm,
        "cold_item": sig_cold,
        "cold_item_bootstrap": boot_cold,
    }
    write_json(SIGNIFICANCE_STD_PATH, payload)
    return payload


def build_tables() -> dict[str, Any]:
    final = read_json(FINAL_PATH)
    final_datasets = final.get("datasets", final)
    warm = read_json(WARM_PATH, default={})
    sig_warm = read_json(SIG_WARM_PATH, default={})
    cold = read_json(COLD_PATH, default={})
    sig_cold = read_json(SIG_COLD_PATH, default={})
    boot_cold = read_json(BOOT_COLD_PATH, default={})
    sota_audit = read_json(SOTA_AUDIT_PATH, default={})
    validated = read_json(VALIDATED_PATH, default={"datasets": {}})
    validated_sig = read_json(VALIDATED_SIG_PATH, default={"comparisons": {}})

    significance = build_standard_significance(sig_warm, sig_cold, boot_cold)

    protocol_rows = []
    dataset_rows = []
    main_rows = []
    baseline_rows = []
    cold_rows = []
    cold_sig_rows = []
    cold_boot_rows = []
    figure_gaps = []
    limitations: list[str] = []

    for dataset in DATASETS:
        stats = DATASET_STATS[dataset]
        label = DATASET_LABELS[dataset]
        warm_counts = _warm_counts(warm, dataset)
        cold_counts = _cold_counts(cold, dataset)
        if dataset == "books" and warm_counts and max(warm_counts) < stats["users"]:
            limitations.append(
                f"Books warm-user evaluation is capped at {fold_count_summary(warm_counts)} "
                f"instead of the full {stats['users']} users per fold."
            )

        dataset_rows.append(
            [
                label,
                str(stats["k"]),
                f"{stats['users']:,}",
                f"{stats['items']:,}",
                f"{stats['ratings']:,}",
            ]
        )
        protocol_rows.append(
            [
                label,
                fold_count_summary(warm_counts),
                fold_count_summary(cold_counts),
                "cold_fold_only (secondary)" if cold_counts else "not generated",
                "capped" if dataset == "books" and warm_counts and max(warm_counts) < stats["users"] else "full",
            ]
        )

        wm = final_datasets.get(dataset, {}).get("warm_mean", {})
        ws = final_datasets.get(dataset, {}).get("warm_std", {})
        main_rows.append(
            [
                label,
                str(stats["k"]),
                f"{stats['users']:,}",
                f"{stats['items']:,}",
                f"{stats['ratings']:,}",
                metric_pm(wm.get("NDCG@10"), ws.get("NDCG@10")),
                metric_fmt(wm.get("HR@10")),
                metric_fmt(wm.get("MRR")),
                metric_pm(wm.get("MAE", wm.get("mae")), ws.get("MAE", ws.get("mae"))),
                metric_pm(wm.get("RMSE", wm.get("rmse")), ws.get("RMSE", ws.get("rmse"))),
            ]
        )

        method_rows = []
        for method in ("popularity", "ease_pure", "higher_order", "ials", "multivae", "lightgcn"):
            ndcg = _baseline_ndcg(final, dataset, method)
            marker = _sig_marker(sig_warm, dataset, method)
            method_rows.append(f"{metric_fmt(ndcg)} {marker}" if ndcg is not None else "OOM/NA")
        baseline_rows.append([label, *method_rows])

        target = _baseline_ndcg(final, dataset, "ease_pure")
        lc2c = final_datasets.get(dataset, {}).get("warm_mean", {}).get("NDCG@10")
        if lc2c is not None and target:
            figure_gaps.append(
                {
                    "dataset": dataset,
                    "label": label,
                    "lc2c_ndcg10": lc2c,
                    "ease_pure_ndcg10": target,
                    "relative_gap_pct": (float(lc2c) - float(target)) / float(target) * 100.0,
                }
            )

    cold_methods = ("content_direct", "dropoutnet", "cf_hybrid", "lc2c", "lc2c_v2", "lc2cpp_validated", "random")
    for dataset in DATASETS:
        label = DATASET_LABELS[dataset]
        methods = cold.get(dataset, {}).get("methods", cold.get(dataset, {}))
        row = [label]
        for method in cold_methods:
            if method == "lc2cpp_validated":
                methods_valid = validated.get("datasets", {}).get(dataset, {}).get("methods", {})
                m = methods_valid.get("lc2cpp_validated_margin", methods_valid.get(method, {}))
            else:
                m = methods.get(method, {})
            row.append(metric_fmt(m.get("NDCG@10", m.get("ndcg10"))))
        cold_rows.append(row)

        cold_sig_rows.append(
            [
                label,
                validated_sig.get("comparisons", {}).get(dataset, {}).get("marker", "n.s."),
                sig_cold.get(dataset, {}).get("lc2c_v2 > dropoutnet", {}).get("marker")
                or p_marker(sig_cold.get(dataset, {}).get("lc2c_v2 > dropoutnet", {}).get("p_corrected")),
                sig_cold.get(dataset, {}).get("lc2c_v2 > content_direct", {}).get("marker")
                or p_marker(sig_cold.get(dataset, {}).get("lc2c_v2 > content_direct", {}).get("p_corrected")),
                sig_cold.get(dataset, {}).get("lc2c_v2 > lc2c (V1)", {}).get("marker")
                or p_marker(sig_cold.get(dataset, {}).get("lc2c_v2 > lc2c (V1)", {}).get("p_corrected")),
            ]
        )

        ds_boot = boot_cold.get(dataset, {})
        cold_boot_rows.append(
            [
                label,
                metric_fmt(ds_boot.get("delta_point")),
                metric_fmt(ds_boot.get("ci_lo_95")),
                metric_fmt(ds_boot.get("ci_hi_95")),
                str(ds_boot.get("B_replicates", "-")),
                str(ds_boot.get("resampling_unit", "-")),
            ]
        )

    baseline_status = {}
    configured = sota_audit.get("baselines", {}) if isinstance(sota_audit, dict) else {}
    for name in MANDATORY_SOTA_BASELINES:
        entry = configured.get(name, {})
        baseline_status[name] = {
            "status": entry.get("status", "not_run"),
            "config": entry.get("config"),
            "seeds": entry.get("seeds", []),
            "runtime_seconds": entry.get("runtime_seconds"),
            "per_user_records": entry.get("per_user_records"),
            "notes": entry.get("notes", "No generated audit entry found."),
        }

    sota_claim_allowed = all(v["status"] == "complete" for v in baseline_status.values())
    win_condition = sota_audit.get("win_condition", {"status": "not_evaluated"}) if isinstance(sota_audit, dict) else {"status": "not_evaluated"}
    if not sota_claim_allowed:
        limitations.append("Core modern SOTA baseline audit is incomplete; SOTA claims must be removed.")
    if win_condition.get("status") != "passed":
        limitations.append("LC2C++ win condition has not passed under the predeclared protocol.")

    payload = {
        "schema_version": 1,
        "sources": {
            "results_final": str(FINAL_PATH.name),
            "warm": str(WARM_PATH.name),
            "significance": str(SIGNIFICANCE_STD_PATH.name),
            "cold_item": str(COLD_PATH.name),
            "sota_audit": str(SOTA_AUDIT_PATH.name) if SOTA_AUDIT_PATH.exists() else None,
        },
        "limitations": sorted(set(limitations)),
        "sota_claim_allowed": bool(sota_claim_allowed and win_condition.get("status") == "passed"),
        "sota_audit": {
            "mandatory_baselines": baseline_status,
            "win_condition": win_condition,
        },
        "table_4_1_dataset_stats": {
            "columns": ["Dataset", "k", "|U|", "|I|", "|R|"],
            "rows": dataset_rows,
        },
        "table_4_2_protocol_sizes": {
            "columns": ["Dataset", "Warm test pairs/fold", "Cold-item pairs/fold", "Cold candidate scope", "Books warm status"],
            "rows": protocol_rows,
        },
        "table_5_1_main": {
            "columns": ["Dataset", "k", "|U|", "|I|", "|R|", "NDCG@10", "HR@10", "MRR", "MAE", "RMSE"],
            "rows": main_rows,
        },
        "table_5_2_baselines": {
            "columns": [
                "Dataset",
                "Popularity",
                "EASE-pure",
                "Higher-Order EASE",
                "iALS",
                "MultiVAE",
                "LightGCN",
            ],
            "rows": baseline_rows,
            "significance_source": "significance.json",
        },
        "figure_5_2_gaps": figure_gaps,
        "table_5_4_cold_item": {
            "columns": [
                "Dataset",
                "Content-direct",
                "DropoutNet",
                "CF hybrid",
                "LC2C V1",
                "LC2C V2",
                "LC2C++ validated",
                "Random",
            ],
            "rows": cold_rows,
        },
        "table_5_4b_cold_item_wilcoxon": {
            "columns": [
                "Dataset",
                "LC2C++ validated > LC2C V2",
                "LC2C V2 > DropoutNet",
                "LC2C V2 > Content-direct",
                "LC2C V2 > LC2C V1",
            ],
            "rows": cold_sig_rows,
            "significance_source": "significance.json",
        },
        "table_5_4c_cold_item_bootstrap": {
            "columns": [
                "Dataset",
                "Delta point",
                "CI low",
                "CI high",
                "B",
                "Resampling unit",
            ],
            "rows": cold_boot_rows,
            "significance_source": "significance.json",
        },
    }
    write_json(TABLES_PATH, payload)
    append_manifest_run(
        command=["python", str(Path(__file__).name)],
        inputs=[FINAL_PATH, WARM_PATH, SIG_WARM_PATH, COLD_PATH, SIG_COLD_PATH, BOOT_COLD_PATH, SOTA_AUDIT_PATH],
        outputs=[TABLES_PATH, SIGNIFICANCE_STD_PATH],
        note="Canonical table and significance build.",
    )
    return payload


def main() -> None:
    payload = build_tables()
    print(f"Wrote {TABLES_PATH}")
    if payload["limitations"]:
        print("Limitations:")
        for item in payload["limitations"]:
            print(f"- {item}")


if __name__ == "__main__":
    main()
