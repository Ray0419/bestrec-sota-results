"""Validation-selected multi-method RRF fusion for lab-only repair probes.

This script is intentionally conservative: it selects one fixed fusion config
on validation records, then evaluates that config once on held-out test records.
It does not train on or tune from test records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


METRICS = ("ndcg10", "hr10", "rr")


@dataclass(frozen=True)
class MethodInput:
    name: str
    path: Path
    ids_key: str


@dataclass
class UserRecord:
    target_item_id: int
    ids: list[int]


def sha256_file(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return record
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    record.update({"sha256": digest.hexdigest(), "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return record


def parse_method_input(values: list[str]) -> MethodInput:
    if len(values) != 3:
        raise ValueError(f"Expected NAME PATH IDS_KEY, got {values!r}")
    name, path, ids_key = values
    return MethodInput(name=name, path=Path(path), ids_key=ids_key)


def load_rows(spec: MethodInput, *, top_k: int) -> dict[int, UserRecord]:
    rows: dict[int, UserRecord] = {}
    with spec.path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            user_id = int(row["user_id"])
            if user_id in rows:
                raise ValueError(f"Duplicate user_id={user_id} in {spec.path} at line {line_number}")
            if spec.ids_key not in row:
                raise ValueError(f"{spec.path} line {line_number} missing {spec.ids_key}")
            rows[user_id] = UserRecord(
                target_item_id=int(row["target_item_id"]),
                ids=[int(value) for value in row[spec.ids_key][:top_k]],
            )
    if not rows:
        raise ValueError(f"No rows loaded from {spec.path}")
    return rows


def metric_from_rank(rank0: int | None) -> dict[str, float]:
    if rank0 is None:
        return {"ndcg10": 0.0, "hr10": 0.0, "rr": 0.0}
    return {
        "ndcg10": 1.0 / math.log2(rank0 + 2) if rank0 < 10 else 0.0,
        "hr10": 1.0 if rank0 < 10 else 0.0,
        "rr": 1.0 / float(rank0 + 1),
    }


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    clean = {name: float(value) for name, value in weights.items() if float(value) > 1e-12}
    total = sum(clean.values())
    if total <= 0:
        raise ValueError(f"Invalid zero-weight config: {weights}")
    return {name: value / total for name, value in clean.items()}


def config_name(weights: dict[str, float]) -> str:
    parts = [f"{name}{value:.3f}".rstrip("0").rstrip(".") for name, value in sorted(weights.items()) if value > 1e-12]
    return "rrf_" + "_".join(parts)


def generate_simplex(names: list[str], *, units: int) -> list[dict[str, float]]:
    configs: list[dict[str, float]] = []

    def rec(idx: int, remaining: int, current: list[int]) -> None:
        if idx == len(names) - 1:
            values = current + [remaining]
            if any(values):
                configs.append({name: value / units for name, value in zip(names, values) if value})
            return
        for value in range(remaining + 1):
            rec(idx + 1, remaining - value, current + [value])

    rec(0, units, [])
    return configs


def parse_center(center: str) -> dict[str, float]:
    weights: dict[str, float] = {}
    if not center.strip():
        return weights
    for part in center.split(","):
        if not part.strip():
            continue
        if "=" not in part:
            raise ValueError(f"Invalid local center component {part!r}; expected name=value")
        name, value = part.split("=", 1)
        weights[name.strip()] = float(value)
    return normalize_weights(weights)


def parse_fixed_config(config: str) -> dict[str, float]:
    return parse_center(config)


def generate_local_configs(method_names: list[str], *, center: dict[str, float], radius: float, step: float) -> list[dict[str, float]]:
    if not center:
        return []
    extra = set(center) - set(method_names)
    if extra:
        raise ValueError(f"Local center has unknown methods: {sorted(extra)}")
    if radius <= 0 or step <= 0:
        return []
    units = round(1.0 / step)
    radius_units = max(1, round(radius / step))
    centers = {name: round(center.get(name, 0.0) * units) for name in method_names}
    configs: list[dict[str, float]] = []

    ranges = {
        name: range(max(0, centers[name] - radius_units), min(units, centers[name] + radius_units) + 1)
        for name in method_names
    }

    def rec(idx: int, remaining: int, current: dict[str, int]) -> None:
        if idx == len(method_names) - 1:
            name = method_names[idx]
            if remaining in ranges[name]:
                values = {**current, name: remaining}
                configs.append({key: value / units for key, value in values.items() if value})
            return
        name = method_names[idx]
        for value in ranges[name]:
            if value <= remaining:
                rec(idx + 1, remaining - value, {**current, name: value})

    rec(0, units, {})
    return configs


def generate_configs(
    method_names: list[str],
    *,
    pair_grid: list[float],
    simplex_step: float,
    sasrec_name: str,
    local_center: dict[str, float],
    local_radius: float,
    local_step: float,
    fixed_config: dict[str, float],
    rrf_k_grid: list[int],
    local_only: bool,
) -> list[dict[str, Any]]:
    if fixed_config:
        missing = set(method_names) - set(fixed_config)
        extra = set(fixed_config) - set(method_names)
        if extra:
            raise ValueError(f"Fixed config has unknown methods: {sorted(extra)}")
        raw: list[dict[str, float]] = [{name: fixed_config.get(name, 0.0) for name in method_names if fixed_config.get(name, 0.0) > 0}]
        if missing:
            raw[0].update({name: 0.0 for name in missing})
    elif local_only:
        raw = generate_local_configs(method_names, center=local_center, radius=local_radius, step=local_step)
    else:
        raw = []
        for name in method_names:
            raw.append({name: 1.0})
        for i, left in enumerate(method_names):
            for right in method_names[i + 1 :]:
                for value in pair_grid:
                    raw.append({left: value, right: 1.0 - value})
        if len(method_names) > 2:
            raw.append({name: 1.0 / len(method_names) for name in method_names})
        hstu_names = [name for name in method_names if name != sasrec_name]
        if len(hstu_names) >= 2:
            units = max(1, round(1.0 / simplex_step))
            raw.extend(generate_simplex(hstu_names, units=units))
            if sasrec_name in method_names:
                for sas_weight in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30):
                    h_weight = (1.0 - sas_weight) / len(hstu_names)
                    raw.append({sasrec_name: sas_weight, **{name: h_weight for name in hstu_names}})
        raw.extend(generate_local_configs(method_names, center=local_center, radius=local_radius, step=local_step))

    seen: set[tuple[tuple[str, float], ...]] = set()
    configs: list[dict[str, Any]] = []
    for weights in raw:
        norm = normalize_weights(weights)
        key = tuple(sorted((name, round(value, 6)) for name, value in norm.items()))
        if key in seen:
            continue
        seen.add(key)
        configs.append({"name": config_name(norm), "weights": norm})
    if rrf_k_grid:
        expanded: list[dict[str, Any]] = []
        for config in configs:
            for k_value in rrf_k_grid:
                expanded.append({**config, "name": f"{config['name']}_k{k_value}", "rrf_k": int(k_value)})
        configs = expanded
    return configs


def validate_method_sets(method_rows: dict[str, dict[int, UserRecord]]) -> list[int]:
    names = list(method_rows)
    common = set(method_rows[names[0]])
    for name in names[1:]:
        common &= set(method_rows[name])
    if not common:
        raise ValueError("No common users across method inputs")
    dropped = {name: len(set(rows) - common) for name, rows in method_rows.items()}
    if any(dropped.values()):
        raise ValueError(f"User sets differ across methods; dropped users would be {dropped}")
    user_ids = sorted(common)
    for user_id in user_ids:
        targets = {method_rows[name][user_id].target_item_id for name in names}
        if len(targets) != 1:
            raise ValueError(f"Target mismatch for user_id={user_id}: {targets}")
    return user_ids


def rank_for_user(
    user_id: int,
    method_rows: dict[str, dict[int, UserRecord]],
    config: dict[str, Any],
    *,
    rrf_k: int,
) -> tuple[list[int], list[float], int | None, dict[str, float], int]:
    target = next(iter(method_rows.values()))[user_id].target_item_id
    actual_rrf_k = int(config.get("rrf_k", rrf_k))
    scores: dict[int, float] = {}
    for method_name, weight in config["weights"].items():
        ids = method_rows[method_name][user_id].ids
        for rank, item_id in enumerate(ids, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + weight / float(actual_rrf_k + rank)
    ranked_pairs = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    ranked = [item for item, _score in ranked_pairs]
    fused_scores = [float(score) for _item, score in ranked_pairs]
    try:
        rank0 = ranked.index(target)
    except ValueError:
        rank0 = None
    return ranked, fused_scores, rank0, metric_from_rank(rank0), target


def evaluate_config(
    user_ids: list[int],
    method_rows: dict[str, dict[int, UserRecord]],
    config: dict[str, Any],
    *,
    rrf_k: int,
    write_records: Path | None = None,
    seed: int,
) -> dict[str, Any]:
    sums = {metric: 0.0 for metric in METRICS}
    target_in_union = 0
    handle = write_records.open("w", encoding="utf-8") if write_records else None
    try:
        for user_id in user_ids:
            ranked, scores, rank0, metrics, target = rank_for_user(user_id, method_rows, config, rrf_k=rrf_k)
            if rank0 is not None:
                target_in_union += 1
            for metric in METRICS:
                sums[metric] += metrics[metric]
            if handle is not None:
                handle.write(
                    json.dumps(
                        {
                            "dataset": "Video_Games",
                            "fold_id": 0,
                            "seed": seed,
                            "method": "multi_rrf_fusion_dev",
                            "user_id": user_id,
                            "target_item_id": target,
                            "candidate_scope": "multi_method_top50_union_history_masked",
                            "ndcg10": metrics["ndcg10"],
                            "hr10": metrics["hr10"],
                            "rr": metrics["rr"],
                            "rank": None if rank0 is None else rank0 + 1,
                            "fusion_config": config["name"],
                            "fusion_weights": config["weights"],
                            "rrf_k": int(config.get("rrf_k", rrf_k)),
                            "top_ids": ranked[:50],
                            "top_scores": scores[:50],
                            "publication_grade": False,
                            "development_note": "Validation-selected multi-method RRF fusion; requires frozen confirmatory rerun before any claim.",
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
    finally:
        if handle is not None:
            handle.close()
    n = len(user_ids)
    return {
        "n": n,
        "ndcg10": sums["ndcg10"] / n,
        "hr10": sums["hr10"] / n,
        "rr": sums["rr"] / n,
        "target_in_union_rate": target_in_union / n,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--valid-input", nargs=3, action="append", metavar=("NAME", "PATH", "IDS_KEY"), required=True)
    parser.add_argument("--test-input", nargs=3, action="append", metavar=("NAME", "PATH", "IDS_KEY"), required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--seed", type=int, default=20260609)
    parser.add_argument("--pair-grid", default="0.0,0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95,1.0")
    parser.add_argument("--simplex-step", type=float, default=0.25)
    parser.add_argument("--sasrec-name", default="sasrec")
    parser.add_argument("--local-center", default="", help="Optional comma list like dev9=0.3,dev10=0.3,dev13=0.3,sasrec=0.1.")
    parser.add_argument("--local-radius", type=float, default=0.0)
    parser.add_argument("--local-step", type=float, default=0.05)
    parser.add_argument("--local-only", action="store_true", help="Use only local-center candidates instead of adding the global default grid.")
    parser.add_argument("--fixed-config", default="", help="Optional comma list of fixed weights; disables generated weight grid.")
    parser.add_argument("--rrf-k-grid", default="", help="Optional comma-separated RRF k values to select by validation.")
    args = parser.parse_args()

    started = time.time()
    valid_specs = [parse_method_input(values) for values in args.valid_input]
    test_specs = [parse_method_input(values) for values in args.test_input]
    valid_names = [spec.name for spec in valid_specs]
    test_names = [spec.name for spec in test_specs]
    if sorted(valid_names) != sorted(test_names):
        raise ValueError(f"Validation/test method names differ: {valid_names} vs {test_names}")
    if len(set(valid_names)) != len(valid_names):
        raise ValueError(f"Duplicate method names: {valid_names}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pair_grid = [float(value) for value in args.pair_grid.split(",") if value.strip()]
    local_center = parse_center(args.local_center)
    fixed_config = parse_fixed_config(args.fixed_config)
    rrf_k_grid = [int(value) for value in args.rrf_k_grid.split(",") if value.strip()]
    configs = generate_configs(
        valid_names,
        pair_grid=pair_grid,
        simplex_step=args.simplex_step,
        sasrec_name=args.sasrec_name,
        local_center=local_center,
        local_radius=args.local_radius,
        local_step=args.local_step,
        fixed_config=fixed_config,
        rrf_k_grid=rrf_k_grid,
        local_only=args.local_only,
    )

    valid_rows = {spec.name: load_rows(spec, top_k=args.top_k) for spec in valid_specs}
    valid_user_ids = validate_method_sets(valid_rows)
    candidate_results = []
    for config in configs:
        candidate_results.append({"config": config, "selection_metrics": evaluate_config(valid_user_ids, valid_rows, config, rrf_k=args.rrf_k, seed=args.seed)})
    selected = max(candidate_results, key=lambda row: (row["selection_metrics"]["ndcg10"], row["selection_metrics"]["hr10"], row["selection_metrics"]["rr"]))

    test_rows = {spec.name: load_rows(spec, top_k=args.top_k) for spec in test_specs}
    test_user_ids = validate_method_sets(test_rows)
    records_path = out_dir / "warm_full_catalog_records_Video_Games_multi_rrf_fusion_test.jsonl"
    test_metrics = evaluate_config(test_user_ids, test_rows, selected["config"], rrf_k=args.rrf_k, write_records=records_path, seed=args.seed)
    summary = {
        "schema_version": 1,
        "status": "complete",
        "publication_grade": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_sec": round(time.time() - started, 3),
        "parameters": {
            "top_k": args.top_k,
            "rrf_k": args.rrf_k,
            "seed": args.seed,
            "pair_grid": pair_grid,
            "simplex_step": args.simplex_step,
            "sasrec_name": args.sasrec_name,
            "local_center": local_center,
            "local_radius": args.local_radius,
            "local_step": args.local_step,
            "local_only": args.local_only,
            "fixed_config": fixed_config,
            "rrf_k_grid": rrf_k_grid,
            "candidate_count": len(configs),
        },
        "inputs": {
            "valid": {spec.name: {"ids_key": spec.ids_key, "file": sha256_file(spec.path)} for spec in valid_specs},
            "test": {spec.name: {"ids_key": spec.ids_key, "file": sha256_file(spec.path)} for spec in test_specs},
        },
        "validation_users": len(valid_user_ids),
        "test_users": len(test_user_ids),
        "candidate_results": candidate_results,
        "selected_config": selected["config"],
        "selected_selection_metrics": selected["selection_metrics"],
        "test_metrics": test_metrics,
        "comparators": {
            "content_adaptive_best_ndcg10": 0.07295666914314712,
            "local_hstu_sm120_final_export_ndcg10": 0.07382241421701587,
            "upstream_hstu_report_ndcg10": 0.076,
            "gap_to_content_adaptive_best": test_metrics["ndcg10"] - 0.07295666914314712,
            "gap_to_local_hstu_sm120_final_export": test_metrics["ndcg10"] - 0.07382241421701587,
            "gap_to_upstream_hstu_report": test_metrics["ndcg10"] - 0.076,
        },
        "records": sha256_file(records_path),
        "honest_interpretation": "Development-only validation-selected multi-method RRF fusion; not publication evidence without frozen fresh confirmatory seeds.",
    }
    summary_path = out_dir / "multi_rrf_fusion_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "complete",
                "candidate_count": len(configs),
                "selected_config": selected["config"],
                "selection_ndcg10": selected["selection_metrics"]["ndcg10"],
                "test_ndcg10": test_metrics["ndcg10"],
                "gap_to_content_adaptive_best": summary["comparators"]["gap_to_content_adaptive_best"],
                "gap_to_local_hstu": summary["comparators"]["gap_to_local_hstu_sm120_final_export"],
                "summary": str(summary_path),
                "records": str(records_path),
                "records_sha256": summary["records"].get("sha256"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
