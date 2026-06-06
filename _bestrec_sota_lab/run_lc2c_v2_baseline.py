"""Append LC2C V2 full-catalog records to a SOTA-lab run.

The confirmatory candidate runner writes only `lc2c_retrieval_ltr` in
candidate-only mode. This script adds the required same-seed LC2C V2 comparator
without recomputing or overwriting candidate rows.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from finalize import expected_fold_record_counts
from sota_common import (
    CONFIRMATORY_SEEDS_CSV,
    DATASETS,
    LAB_DIR,
    RUNS_DIR,
    append_jsonl,
    build_base_scorers,
    content_sim_matrix,
    load_dataset,
    make_item_kfold,
    parse_csv,
    read_json,
    write_json,
)
from v5_utils import NUM_FOLDS


METHOD = "lc2c_v2"


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


def remove_method_rows(path: Path, method: str) -> dict[str, int]:
    if not path.exists():
        return {"kept": 0, "removed": 0}
    tmp = path.with_suffix(path.suffix + ".tmp")
    kept = 0
    removed = 0
    with path.open("r", encoding="utf-8") as fin, tmp.open("w", encoding="utf-8") as fout:
        for line in fin:
            if f'"method": "{method}"' in line:
                removed += 1
            else:
                fout.write(line)
                kept += 1
    tmp.replace(path)
    return {"kept": kept, "removed": removed}


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
    expected_keys = {tuple(int(x) for x in key.split(":", 1)) for key in expected}
    extras = [
        {"seed": int(seed), "fold_id": int(fold_id), "actual": int(actual)}
        for (seed, fold_id), actual in sorted(counts.items())
        if (int(seed), int(fold_id)) not in expected_keys
    ]
    return {
        "status": "complete" if not missing and not partial else "partial",
        "complete_folds": int(complete),
        "expected_folds": int(len(expected)),
        "missing_folds": missing,
        "partial_folds": partial,
        "extra_folds": extras,
    }


def run_dataset(
    *,
    dataset: str,
    seeds: list[int],
    run_dir: Path,
    max_new_folds: int,
    fold_ids: set[int] | None,
    force: bool,
) -> dict[str, Any]:
    interactions, _, n_users, n_items, item_title_emb = load_dataset(dataset)
    s_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    record_path = run_dir / f"cold_full_catalog_records_{dataset}.jsonl"
    if force:
        removed = remove_method_rows(record_path, METHOD)
        print(f"{dataset}: removed existing {METHOD} rows: {removed['removed']:,}")
    counts = method_fold_counts(record_path, METHOD)
    expected = expected_fold_record_counts(dataset, seeds)
    stats = {"ndcg": 0.0, "hr": 0.0, "rr": 0.0, "n": 0}
    fold_summaries: list[dict[str, Any]] = []
    new_folds = 0
    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
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
            scorers, meta, _ = build_base_scorers(
                dataset=dataset,
                seed=int(seed),
                fold_id=int(fold_id),
                train_inters=train_inters,
                cold_items=set(int(x) for x in cold_items),
                interactions=interactions,
                n_users=n_users,
                n_items=n_items,
                item_title_emb=item_title_emb,
                S_content=s_content,
                include_deep=False,
                needed_methods={METHOD},
            )
            result, rows = __import__("sota_common").eval_full_catalog(
                dataset,
                int(seed),
                int(fold_id),
                METHOD,
                scorers[METHOD],
                train_inters,
                test_inters,
                n_items,
            )
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
                    "meta": meta,
                }
            )
            print(f"{dataset} seed={seed} fold={fold_id}: {METHOD} NDCG@10={result['NDCG@10']:.5f} n={n:,}")
        if max_new_folds and new_folds >= max_new_folds:
            break
    total = int(stats["n"])
    coverage = coverage_summary(record_path, METHOD, expected)
    return {
        "dataset": dataset,
        "method": METHOD,
        "seeds": seeds,
        "candidate_scope": "full_catalog",
        "new_folds": int(new_folds),
        "summary_new_rows": {
            "NDCG@10": stats["ndcg"] / total if total else None,
            "HR@10": stats["hr"] / total if total else None,
            "MRR": stats["rr"] / total if total else None,
            "n_records": total,
        },
        "fold_summaries_new_rows": fold_summaries,
        "coverage": coverage,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--seeds", default=CONFIRMATORY_SEEDS_CSV)
    parser.add_argument("--max-new-folds", type=int, default=0)
    parser.add_argument("--fold-ids", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--finalize-bootstrap-reps", type=int, default=200)
    parser.add_argument("--no-finalize", action="store_true")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    fold_ids = set(parse_csv(args.fold_ids, int)) if args.fold_ids else None
    for dataset in datasets:
        if dataset not in DATASETS:
            raise ValueError(f"unknown dataset: {dataset}")

    audit_path = run_dir / "lc2c_v2_audit.json"
    audit = read_json(audit_path, {"schema_version": 1, "method": METHOD, "status": "running", "datasets": {}, "seeds": seeds})
    audit["status"] = "running"
    audit["seeds"] = seeds
    write_json(audit_path, audit)
    for dataset in datasets:
        audit["datasets"][dataset] = run_dataset(
            dataset=dataset,
            seeds=seeds,
            run_dir=run_dir,
            max_new_folds=max(0, int(args.max_new_folds)),
            fold_ids=fold_ids,
            force=bool(args.force),
        )
        write_json(audit_path, audit)
    completed_datasets = {
        name
        for name, summary in audit.get("datasets", {}).items()
        if summary.get("coverage", {}).get("status") == "complete"
        and int(summary.get("coverage", {}).get("complete_folds", 0)) == int(summary.get("coverage", {}).get("expected_folds", -1))
    }
    audit["status"] = "complete" if set(DATASETS).issubset(completed_datasets) else "partial"
    write_json(audit_path, audit)
    if not args.no_finalize:
        cmd = [
            sys.executable,
            str(LAB_DIR / "finalize.py"),
            "--run-id",
            args.run_id,
            "--bootstrap-reps",
            str(args.finalize_bootstrap_reps),
        ]
        subprocess.run(cmd, check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
