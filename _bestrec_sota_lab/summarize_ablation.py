"""Summarize paired ablation records against a reference confirmatory run."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import wilcoxon


LAB_DIR = Path(__file__).resolve().parent
RUNS_DIR = LAB_DIR / "runs"
DEFAULT_REFERENCE = "confirmatory_strict_v2_candidate_20260611_20260615"
METRICS = ("ndcg10", "hr10", "rr")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def run_dir(run_id: str) -> Path:
    path = RUNS_DIR / run_id
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def record_path(run_id: str, dataset: str) -> Path:
    path = run_dir(run_id) / f"cold_full_catalog_records_{dataset}.jsonl"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def load_records(path: Path, method: str) -> dict[tuple[int, int, int, int], dict[str, float]]:
    rows: dict[tuple[int, int, int, int], dict[str, float]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if f'"method": "{method}"' not in line:
                continue
            row = json.loads(line)
            if row.get("method") != method:
                continue
            key = (int(row["seed"]), int(row["fold_id"]), int(row["user_id"]), int(row["target_item_id"]))
            rows[key] = {m: float(row[m]) for m in METRICS}
    return rows


def summarize_pair(ref: dict[tuple[int, int, int, int], dict[str, float]], ab: dict[tuple[int, int, int, int], dict[str, float]]) -> dict[str, Any]:
    common = sorted(set(ref) & set(ab))
    missing_in_ablation = len(set(ref) - set(ab))
    extra_in_ablation = len(set(ab) - set(ref))
    if not common:
        return {
            "n_common": 0,
            "missing_in_ablation": missing_in_ablation,
            "extra_in_ablation": extra_in_ablation,
            "identical_metrics": False,
            "metrics": {},
            "folds": [],
        }
    metric_summary: dict[str, Any] = {}
    identical = True
    for metric in METRICS:
        ref_vals = np.asarray([ref[k][metric] for k in common], dtype=np.float64)
        ab_vals = np.asarray([ab[k][metric] for k in common], dtype=np.float64)
        diffs = ab_vals - ref_vals
        identical = identical and bool(np.allclose(diffs, 0.0, atol=0.0, rtol=0.0))
        metric_summary[metric] = {
            "reference_mean": float(ref_vals.mean()),
            "ablation_mean": float(ab_vals.mean()),
            "mean_delta": float(diffs.mean()),
            "max_abs_delta": float(np.max(np.abs(diffs))),
            "positive_records": int((diffs > 0).sum()),
            "negative_records": int((diffs < 0).sum()),
            "zero_records": int((diffs == 0).sum()),
        }
    fold_keys = sorted({(k[0], k[1]) for k in common})
    folds = []
    for seed, fold_id in fold_keys:
        keys = [k for k in common if k[0] == seed and k[1] == fold_id]
        fold = {"seed": seed, "fold_id": fold_id, "n_common": len(keys), "metrics": {}}
        for metric in METRICS:
            ref_vals = np.asarray([ref[k][metric] for k in keys], dtype=np.float64)
            ab_vals = np.asarray([ab[k][metric] for k in keys], dtype=np.float64)
            diffs = ab_vals - ref_vals
            fold["metrics"][metric] = {
                "reference_mean": float(ref_vals.mean()),
                "ablation_mean": float(ab_vals.mean()),
                "mean_delta": float(diffs.mean()),
                "max_abs_delta": float(np.max(np.abs(diffs))),
            }
        folds.append(fold)
    return {
        "n_common": len(common),
        "missing_in_ablation": missing_in_ablation,
        "extra_in_ablation": extra_in_ablation,
        "identical_metrics": identical,
        "metrics": metric_summary,
        "folds": folds,
    }


def user_mean(records: dict[tuple[int, int, int, int], dict[str, float]], metric: str = "ndcg10") -> dict[int, float]:
    sums: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for key, row in records.items():
        user_id = int(key[2])
        sums[user_id][0] += float(row[metric])
        sums[user_id][1] += 1.0
    return {u: vals[0] / vals[1] for u, vals in sums.items() if vals[1]}


def paired_user_test(
    candidate_records: dict[tuple[int, int, int, int], dict[str, float]],
    baseline_records: dict[tuple[int, int, int, int], dict[str, float]],
    metric: str = "ndcg10",
) -> dict[str, Any]:
    cand = user_mean(candidate_records, metric)
    base = user_mean(baseline_records, metric)
    common = sorted(set(cand) & set(base))
    if not common:
        return {"n_users": 0, "mean_delta": None, "p_greater": None}
    diffs = np.asarray([cand[u] - base[u] for u in common], dtype=np.float64)
    p = 1.0 if np.allclose(diffs, 0.0) else float(wilcoxon(diffs, alternative="greater", zero_method="wilcox").pvalue)
    return {
        "metric": metric,
        "sample_unit": "per-user mean",
        "alternative": "candidate greater than baseline",
        "n_users": len(common),
        "candidate_user_mean": float(np.mean([cand[u] for u in common])),
        "baseline_user_mean": float(np.mean([base[u] for u in common])),
        "mean_delta": float(diffs.mean()),
        "positive_users": int((diffs > 0).sum()),
        "negative_users": int((diffs < 0).sum()),
        "zero_users": int((diffs == 0).sum()),
        "p_greater": p,
    }


def build_report(reference_run: str, ablation_runs: list[str], datasets: list[str], method: str, baseline_methods: list[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "reference_run": reference_run,
        "method": method,
        "baseline_methods": baseline_methods,
        "datasets": datasets,
        "ablation_runs": {},
    }
    for ab_run in ablation_runs:
        config = read_json(run_dir(ab_run) / "run_config.json", {})
        ablation_meta = config.get("frozen_config", {}).get("ablation", {})
        run_block = {
            "ablation": ablation_meta,
            "publication_gate": read_json(run_dir(ab_run) / "publication_gate.json", {}),
            "datasets": {},
        }
        for dataset in datasets:
            ref_records = load_records(record_path(reference_run, dataset), method)
            ab_records = load_records(record_path(ab_run, dataset), method)
            dataset_block = summarize_pair(ref_records, ab_records)
            if baseline_methods:
                baseline_comparisons = {}
                for baseline in baseline_methods:
                    baseline_records = load_records(record_path(reference_run, dataset), baseline)
                    baseline_comparisons[baseline] = paired_user_test(ab_records, baseline_records)
                dataset_block["baseline_comparisons"] = baseline_comparisons
            run_block["datasets"][dataset] = dataset_block
        payload["ablation_runs"][ab_run] = run_block
    return payload


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Ablation Pair Summary",
        "",
        f"Generated: {report['generated_utc']}",
        f"Reference run: `{report['reference_run']}`",
        f"Method: `{report['method']}`",
        "",
        "## Results",
        "",
    ]
    for run_id, run_block in report["ablation_runs"].items():
        ablation = run_block.get("ablation", {})
        gate = run_block.get("publication_gate", {})
        lines.extend(
            [
                f"### {run_id}",
                "",
                f"- Ablation: `{ablation.get('ablation_id', 'unknown')}`",
                f"- Publication gate passed: `{gate.get('passed')}`",
                "",
                "| Dataset | N | Ref NDCG | Ablation NDCG | Delta | Max Abs Delta | Identical |",
                "|---|---:|---:|---:|---:|---:|---|",
            ]
        )
        for dataset, block in run_block.get("datasets", {}).items():
            metric = block.get("metrics", {}).get("ndcg10", {})
            lines.append(
                "| "
                f"{dataset} | {block.get('n_common', 0)} | "
                f"{metric.get('reference_mean', 0.0):.12f} | "
                f"{metric.get('ablation_mean', 0.0):.12f} | "
                f"{metric.get('mean_delta', 0.0):.12f} | "
                f"{metric.get('max_abs_delta', 0.0):.12f} | "
                f"{block.get('identical_metrics')} |"
            )
        lines.append("")
        if report.get("baseline_methods"):
            lines.extend(["| Dataset | Baseline | User Mean Delta | p(greater) | + Users | - Users |", "|---|---|---:|---:|---:|---:|"])
            for dataset, block in run_block.get("datasets", {}).items():
                for baseline, comp in block.get("baseline_comparisons", {}).items():
                    lines.append(
                        "| "
                        f"{dataset} | {baseline} | "
                        f"{comp.get('mean_delta', 0.0):.12f} | "
                        f"{comp.get('p_greater', 1.0):.6g} | "
                        f"{comp.get('positive_users', 0)} | "
                        f"{comp.get('negative_users', 0)} |"
                    )
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-run", default=DEFAULT_REFERENCE)
    parser.add_argument("--ablation-runs", required=True, help="Comma-separated ablation run IDs.")
    parser.add_argument("--datasets", default="beauty")
    parser.add_argument("--method", default="lc2c_retrieval_ltr")
    parser.add_argument("--baseline-methods", default="", help="Optional comma-separated baseline methods loaded from the reference run.")
    parser.add_argument("--out", default=None, help="Output JSON path. Defaults to _bestrec_sota_lab/ablation_reports/<timestamp>.json")
    args = parser.parse_args()

    ablation_runs = parse_csv(args.ablation_runs)
    datasets = parse_csv(args.datasets)
    baseline_methods = parse_csv(args.baseline_methods)
    report = build_report(args.reference_run, ablation_runs, datasets, args.method, baseline_methods)
    if args.out:
        out_json = Path(args.out)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_json = LAB_DIR / "ablation_reports" / f"ablation_summary_{stamp}.json"
    write_json(out_json, report)
    write_markdown(out_json.with_suffix(".md"), report)
    print(f"Wrote {out_json}")
    print(f"Wrote {out_json.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
