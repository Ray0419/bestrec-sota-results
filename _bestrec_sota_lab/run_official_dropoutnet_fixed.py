"""Run the fixed DropoutNet component comparator for the SOTA lab.

This baseline is not HP-tuned on confirmatory data. It uses the exact
DropoutNet config consumed by the candidate when `official_dropoutnet` is an
LTR feature, which makes the component comparison fair and auditable.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from finalize import expected_fold_record_counts
from protocol import load_protocol, protocol_summary
from sota_common import (
    BESTREC_RUN_DIR,
    CONFIRMATORY_SEEDS_CSV,
    DATASETS,
    OFFICIAL_DROPOUTNET_FEATURE_CONFIG,
    RUNS_DIR,
    append_jsonl,
    parse_csv,
    read_json,
    write_json,
    write_run_config,
)
from run_official_blair_baseline import remove_method_rows

sys.path.insert(0, str(BESTREC_RUN_DIR))
from run_cold_item import make_item_kfold  # noqa: E402
from run_faithful_dropoutnet import (  # noqa: E402
    build_inference_factors,
    build_warm_matrix,
    eval_full_catalog,
    load_dataset,
    make_dropoutnet_score,
    train_item_tower,
    wmf_als,
)
from v5_utils import NUM_FOLDS  # noqa: E402


METHOD = "official_dropoutnet_fixed"


def method_fold_counts(path: Path, method: str) -> Counter[tuple[int, int]]:
    counts: Counter[tuple[int, int]] = Counter()
    if not path.exists():
        return counts
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if f'"method": "{method}"' not in line:
                continue
            row = json.loads(line)
            counts[(int(row["seed"]), int(row["fold_id"]))] += 1
    return counts


def coverage_summary(record_path: Path, method: str, expected: dict[str, int]) -> dict[str, Any]:
    counts = method_fold_counts(record_path, method)
    missing: list[dict[str, Any]] = []
    partial: list[dict[str, Any]] = []
    complete = 0
    for key, expected_count in sorted(expected.items()):
        seed_s, fold_s = key.split(":", 1)
        actual = int(counts.get((int(seed_s), int(fold_s)), 0))
        if actual == int(expected_count):
            complete += 1
        elif actual == 0:
            missing.append({"seed": int(seed_s), "fold_id": int(fold_s), "expected": int(expected_count)})
        else:
            partial.append(
                {
                    "seed": int(seed_s),
                    "fold_id": int(fold_s),
                    "expected": int(expected_count),
                    "actual": int(actual),
                }
            )
    return {
        "status": "complete" if not missing and not partial else "partial",
        "complete_folds": int(complete),
        "expected_folds": int(len(expected)),
        "missing_folds": missing,
        "partial_folds": partial,
    }


def run_dataset(
    dataset: str,
    seeds: list[int],
    run_dir: Path,
    max_folds: int,
    max_new_folds: int,
    fold_ids: set[int] | None,
    force: bool,
    quick: bool,
    wmf_iters: int,
    tower_epochs: int,
) -> dict[str, Any]:
    interactions, n_users, n_items, item_title_emb = load_dataset(dataset)
    sbert = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
    sbert = sbert.astype(np.float32)
    cfg = OFFICIAL_DROPOUTNET_FEATURE_CONFIG[dataset]
    record_path = run_dir / f"cold_full_catalog_records_{dataset}.jsonl"
    if force:
        removed = remove_method_rows(record_path, METHOD)
        print(f"{dataset}: removed existing {METHOD} rows: {removed['removed']:,}")
    counts = method_fold_counts(record_path, METHOD)
    expected = expected_fold_record_counts(dataset, seeds)
    stats = {"ndcg": 0.0, "hr": 0.0, "rr": 0.0, "n": 0}
    fold_summaries: list[dict[str, Any]] = []
    scale = 0.05 if quick else 1.0
    wmf_n_iter = max(2, int(round(wmf_iters * scale)))
    tower_n_epochs = max(2, int(round(tower_epochs * scale)))
    new_folds = 0
    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        if max_folds:
            splits = splits[:max_folds]
        for fold_id, (tr_idx, te_idx, cold_items) in enumerate(splits):
            if fold_ids is not None and fold_id not in fold_ids:
                continue
            key = (int(seed), int(fold_id))
            expected_count = int(expected[f"{seed}:{fold_id}"])
            existing_count = int(counts.get(key, 0))
            if existing_count == expected_count:
                print(f"{dataset} seed={seed} fold={fold_id}: {METHOD} already complete; skipping")
                continue
            if existing_count:
                raise RuntimeError(
                    f"{dataset} seed={seed} fold={fold_id}: existing {METHOD} rows={existing_count}, "
                    f"expected {expected_count}; rerun with --force to remove partial rows"
                )
            if max_new_folds and new_folds >= max_new_folds:
                break
            t0 = time.time()
            train_inters = [interactions[i] for i in tr_idx]
            test_inters = [interactions[i] for i in te_idx]
            warm_idx = np.array(sorted(set(range(n_items)) - set(cold_items)), dtype=np.int32)
            cold_idx = np.array(sorted(cold_items), dtype=np.int32)
            X_warm = build_warm_matrix(train_inters, n_users, warm_idx)
            U_wmf, V_warm_wmf = wmf_als(
                X_warm,
                k=int(cfg["k"]),
                alpha=40.0,
                reg=float(cfg["reg"]),
                n_iter=wmf_n_iter,
                seed=seed,
            )
            tower = train_item_tower(
                V_warm_wmf,
                sbert[warm_idx],
                p_drop=float(cfg["p_drop"]),
                epochs=tower_n_epochs,
                lr=1e-3,
                batch_size=256,
                seed=seed,
            )
            V_warm_used, V_cold_used = build_inference_factors(
                str(cfg["mode"]),
                V_warm_wmf,
                sbert[warm_idx],
                sbert[cold_idx],
                tower,
                int(cfg["k"]),
            )
            score_fn = make_dropoutnet_score(U_wmf, V_warm_used, V_cold_used, warm_idx, cold_idx, n_items)
            result, rows = eval_full_catalog(dataset, seed, fold_id, METHOD, score_fn, train_inters, test_inters, n_items)
            if len(rows) != expected_count:
                raise RuntimeError(
                    f"{dataset} seed={seed} fold={fold_id}: evaluator produced {len(rows)} rows, "
                    f"expected {expected_count}"
                )
            append_jsonl(record_path, rows)
            n = len(rows)
            stats["ndcg"] += float(result["NDCG@10"]) * n
            stats["hr"] += float(result["HR@10"]) * n
            stats["rr"] += float(result["MRR"]) * n
            stats["n"] += n
            counts[key] = expected_count
            new_folds += 1
            fold_summaries.append(
                {
                    "dataset": dataset,
                    "seed": int(seed),
                    "fold_id": int(fold_id),
                    "NDCG@10": float(result["NDCG@10"]),
                    "HR@10": float(result["HR@10"]),
                    "MRR": float(result["MRR"]),
                    "n_eval": int(n),
                    "elapsed_seconds": time.time() - t0,
                    "config": dict(cfg),
                    "wmf_iters": int(wmf_n_iter),
                    "tower_epochs": int(tower_n_epochs),
                }
            )
            print(f"{dataset} seed={seed} fold={fold_id}: {METHOD} NDCG@10={result['NDCG@10']:.5f} n={n:,}")
            del tower, U_wmf, V_warm_wmf, X_warm
            gc.collect()
        if max_new_folds and new_folds >= max_new_folds:
            break
    n_total = stats["n"]
    coverage = coverage_summary(record_path, METHOD, expected)
    return {
        "dataset": dataset,
        "method": METHOD,
        "candidate_scope": "full_catalog",
        "fixed_config": dict(cfg),
        "seeds": seeds,
        "folds_requested_per_seed": max_folds or NUM_FOLDS,
        "new_folds": int(new_folds),
        "quick": bool(quick),
        "summary_new_rows": {
            "NDCG@10": stats["ndcg"] / n_total if n_total else None,
            "HR@10": stats["hr"] / n_total if n_total else None,
            "MRR": stats["rr"] / n_total if n_total else None,
            "n_records": int(n_total),
        },
        "fold_summaries_new_rows": fold_summaries,
        "coverage": coverage,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--seeds", default=CONFIRMATORY_SEEDS_CSV)
    parser.add_argument("--max-folds", type=int, default=0)
    parser.add_argument("--max-new-folds", type=int, default=0)
    parser.add_argument("--fold-ids", default="")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--wmf-iters", type=int, default=50)
    parser.add_argument("--tower-epochs", type=int, default=100)
    args = parser.parse_args()

    protocol = load_protocol()
    run_dir = RUNS_DIR / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    fold_ids = set(parse_csv(args.fold_ids, int)) if args.fold_ids else None
    baseline_config = {
        "schema_version": 1,
        "stage": "baseline",
        "run_id": args.run_id,
        "datasets": datasets,
        "seeds": seeds,
        "candidate_scope": "full_catalog",
        "max_folds": args.max_folds,
        "max_new_folds": args.max_new_folds,
        "fold_ids": sorted(fold_ids) if fold_ids is not None else None,
        "quick": bool(args.quick),
        "baseline_method": METHOD,
        "protocol": protocol_summary(protocol),
        "dropoutnet_feature_config": OFFICIAL_DROPOUTNET_FEATURE_CONFIG,
    }
    if (run_dir / "run_config.json").exists():
        write_json(run_dir / f"baseline_run_config_{METHOD}.json", baseline_config)
    else:
        write_run_config(run_dir, baseline_config)
    audit_path = run_dir / "official_dropoutnet_fixed_audit.json"
    audit = read_json(
        audit_path,
        {
            "schema_version": 1,
            "method": METHOD,
            "baseline_slot": "faithful_dropoutnet_fixed_component",
            "status": "running",
            "protocol": protocol_summary(protocol),
            "dropoutnet_feature_config": OFFICIAL_DROPOUTNET_FEATURE_CONFIG,
            "datasets": {},
            "seeds": seeds,
            "notes": "Uses the exact frozen DropoutNet config consumed by lc2c_retrieval_ltr when official_dropoutnet is enabled.",
        },
    )
    audit["status"] = "running"
    audit["seeds"] = seeds
    audit["protocol"] = protocol_summary(protocol)
    audit["dropoutnet_feature_config"] = OFFICIAL_DROPOUTNET_FEATURE_CONFIG
    write_json(audit_path, audit)
    for dataset in datasets:
        if dataset not in DATASETS:
            raise ValueError(f"unknown dataset: {dataset}")
        audit["datasets"][dataset] = run_dataset(
            dataset,
            seeds,
            run_dir,
            args.max_folds,
            max(0, int(args.max_new_folds)),
            fold_ids,
            args.force,
            args.quick,
            args.wmf_iters,
            args.tower_epochs,
        )
        write_json(audit_path, audit)
    completed_datasets = {
        name
        for name, summary in audit.get("datasets", {}).items()
        if summary.get("coverage", {}).get("status") == "complete"
        and int(summary.get("coverage", {}).get("complete_folds", 0)) == int(summary.get("coverage", {}).get("expected_folds", -1))
    }
    audit["status"] = (
        "complete"
        if set(DATASETS).issubset(completed_datasets) and not args.max_folds and not args.max_new_folds and not args.quick
        else "partial"
    )
    write_json(audit_path, audit)
    return 0 if audit["status"] in {"complete", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
