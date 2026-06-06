"""Run tuned faithful DropoutNet as `official_dropoutnet` in the SOTA lab.

This is the publication-grade tuned DropoutNet comparator. It imports the
faithful WMF-backed DropoutNet implementation read-only from `_bestrec_run`,
selects dataset-level hyperparameters by inner validation on the first active
confirmatory seed, and appends canonical full-catalog JSONL records into the
isolated lab run.
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
from run_official_blair_baseline import remove_method_rows
from sota_common import BESTREC_RUN_DIR, CONFIRMATORY_SEEDS_CSV, DATASETS, RUNS_DIR, append_jsonl, parse_csv, read_json, write_json

sys.path.insert(0, str(BESTREC_RUN_DIR))
from run_cold_item import make_item_kfold  # noqa: E402
from run_faithful_dropoutnet import (  # noqa: E402
    build_inference_factors,
    build_warm_matrix,
    eval_full_catalog,
    hp_sweep,
    load_dataset,
    make_dropoutnet_score,
    train_item_tower,
    wmf_als,
)
from v5_utils import NUM_FOLDS  # noqa: E402


METHOD = "official_dropoutnet"


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


def choose_hp(
    *,
    dataset: str,
    seeds: list[int],
    interactions: list[dict[str, Any]],
    n_users: int,
    n_items: int,
    item_title_emb: Any,
    audit_dataset: dict[str, Any],
    retune: bool,
    sweep_wmf_iters: int,
    sweep_tower_epochs: int,
) -> dict[str, Any]:
    existing = audit_dataset.get("chosen_hp")
    if existing and not retune:
        return dict(existing)
    seed = int(seeds[0])
    t0 = time.time()
    hp = hp_sweep(
        dataset,
        interactions,
        n_users,
        n_items,
        item_title_emb,
        seed=seed,
        wmf_iters=int(sweep_wmf_iters),
        tower_epochs=int(sweep_tower_epochs),
        verbose=True,
    )
    hp["selection_seed"] = seed
    hp["selection_seconds"] = time.time() - t0
    return hp


def run_dataset(
    *,
    dataset: str,
    seeds: list[int],
    run_dir: Path,
    max_new_folds: int,
    fold_ids: set[int] | None,
    force: bool,
    retune: bool,
    wmf_iters: int,
    tower_epochs: int,
    sweep_wmf_iters: int,
    sweep_tower_epochs: int,
    audit_dataset: dict[str, Any],
) -> dict[str, Any]:
    interactions, n_users, n_items, item_title_emb = load_dataset(dataset)
    emb_np = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
    emb_np = emb_np.astype(np.float32)
    record_path = run_dir / f"cold_full_catalog_records_{dataset}.jsonl"
    if force:
        removed = remove_method_rows(record_path, METHOD)
        print(f"{dataset}: removed existing {METHOD} rows: {removed['removed']:,}")
    hp = choose_hp(
        dataset=dataset,
        seeds=seeds,
        interactions=interactions,
        n_users=n_users,
        n_items=n_items,
        item_title_emb=item_title_emb,
        audit_dataset=audit_dataset,
        retune=retune,
        sweep_wmf_iters=sweep_wmf_iters,
        sweep_tower_epochs=sweep_tower_epochs,
    )
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
            warm_idx = np.array(sorted(set(range(n_items)) - set(cold_items)), dtype=np.int32)
            cold_idx = np.array(sorted(cold_items), dtype=np.int32)
            X_warm = build_warm_matrix(train_inters, n_users, warm_idx)
            sbert_warm = emb_np[warm_idx]
            sbert_cold = emb_np[cold_idx]
            U_wmf, V_warm_wmf = wmf_als(
                X_warm,
                k=int(hp["k"]),
                alpha=40.0,
                reg=float(hp["reg"]),
                n_iter=int(wmf_iters),
                seed=int(seed),
            )
            tower = train_item_tower(
                V_warm_wmf,
                sbert_warm,
                p_drop=float(hp["p_drop"]),
                epochs=int(tower_epochs),
                lr=1e-3,
                batch_size=256,
                seed=int(seed),
            )
            V_warm_used, V_cold_used = build_inference_factors(
                str(hp["inference_mode"]),
                V_warm_wmf,
                sbert_warm,
                sbert_cold,
                tower,
                int(hp["k"]),
            )
            score_fn = make_dropoutnet_score(U_wmf, V_warm_used, V_cold_used, warm_idx, cold_idx, n_items)
            result, rows = eval_full_catalog(dataset, int(seed), int(fold_id), METHOD, score_fn, train_inters, test_inters, n_items)
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
                    "chosen_hp": {k: v for k, v in hp.items() if k != "sweep_results"},
                }
            )
            print(
                f"{dataset} seed={seed} fold={fold_id}: {METHOD} "
                f"NDCG@10={result['NDCG@10']:.5f} n={n:,}"
            )
            del tower, U_wmf, V_warm_wmf, X_warm
            gc.collect()
        if max_new_folds and new_folds >= max_new_folds:
            break
    total = int(stats["n"])
    return {
        "dataset": dataset,
        "method": METHOD,
        "candidate_scope": "full_catalog",
        "seeds": seeds,
        "chosen_hp": hp,
        "wmf_iters": int(wmf_iters),
        "tower_epochs": int(tower_epochs),
        "sweep_wmf_iters": int(sweep_wmf_iters),
        "sweep_tower_epochs": int(sweep_tower_epochs),
        "new_folds": int(new_folds),
        "summary_new_rows": {
            "NDCG@10": stats["ndcg"] / total if total else None,
            "HR@10": stats["hr"] / total if total else None,
            "MRR": stats["rr"] / total if total else None,
            "n_records": total,
        },
        "fold_summaries_new_rows": fold_summaries,
        "coverage": coverage_summary(record_path, METHOD, expected),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--seeds", default=CONFIRMATORY_SEEDS_CSV)
    parser.add_argument("--max-new-folds", type=int, default=0)
    parser.add_argument("--fold-ids", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--retune", action="store_true")
    parser.add_argument("--wmf-iters", type=int, default=50)
    parser.add_argument("--tower-epochs", type=int, default=100)
    parser.add_argument("--sweep-wmf-iters", type=int, default=30)
    parser.add_argument("--sweep-tower-epochs", type=int, default=60)
    args = parser.parse_args()

    protocol = load_protocol()
    run_dir = RUNS_DIR / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    fold_ids = set(parse_csv(args.fold_ids, int)) if args.fold_ids else None
    for dataset in datasets:
        if dataset not in DATASETS:
            raise ValueError(f"unknown dataset: {dataset}")

    audit_path = run_dir / "official_dropoutnet_audit.json"
    audit = read_json(
        audit_path,
        {
            "schema_version": 1,
            "method": METHOD,
            "baseline_slot": "faithful_dropoutnet_tuned",
            "status": "running",
            "protocol": protocol_summary(protocol),
            "datasets": {},
            "seeds": seeds,
            "notes": (
                "Tuned faithful DropoutNet with WMF item factors, dataset-level "
                "inner validation on the first active confirmatory seed, and "
                "canonical full-catalog records."
            ),
        },
    )
    audit["status"] = "running"
    audit["seeds"] = seeds
    audit["protocol"] = protocol_summary(protocol)
    write_json(audit_path, audit)
    for dataset in datasets:
        audit["datasets"][dataset] = run_dataset(
            dataset=dataset,
            seeds=seeds,
            run_dir=run_dir,
            max_new_folds=max(0, int(args.max_new_folds)),
            fold_ids=fold_ids,
            force=bool(args.force),
            retune=bool(args.retune),
            wmf_iters=int(args.wmf_iters),
            tower_epochs=int(args.tower_epochs),
            sweep_wmf_iters=int(args.sweep_wmf_iters),
            sweep_tower_epochs=int(args.sweep_tower_epochs),
            audit_dataset=dict(audit.get("datasets", {}).get(dataset, {})),
        )
        write_json(audit_path, audit)
    completed_datasets = {
        name
        for name, summary in audit.get("datasets", {}).items()
        if summary.get("coverage", {}).get("status") == "complete"
        and int(summary.get("coverage", {}).get("complete_folds", 0)) == int(summary.get("coverage", {}).get("expected_folds", -1))
    }
    audit["status"] = "complete" if set(DATASETS).issubset(completed_datasets) and not args.max_new_folds else "partial"
    write_json(audit_path, audit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
