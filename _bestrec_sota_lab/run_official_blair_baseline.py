"""Run official-checkpoint BLaIR full-catalog cold-item baseline in the lab.

This script is intentionally isolated: it imports read-only helpers from
`_bestrec_run`, uses already-cached official BLaIR item embeddings, and writes
only into `_bestrec_sota_lab/runs/<run_id>/`.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

from sota_common import BESTREC_RUN_DIR, CONFIRMATORY_SEEDS_CSV, DATASETS, RUNS_DIR, append_jsonl, completed_folds, parse_csv, write_json

sys.path.insert(0, str(BESTREC_RUN_DIR))

from run_all_confirmatory import eval_full_catalog  # noqa: E402
from run_cold_item import DATASET_KCORE, make_item_kfold  # noqa: E402
from run_faithful_blair import build_warm_sparse, load_dataset, make_score_blair_full  # noqa: E402
from v5_utils import NUM_FOLDS, ROOT  # noqa: E402


METHOD = "official_blair"
CHECKPOINT = "hyp1231/blair-roberta-base"


def cached_blair_embeddings(dataset: str, n_items: int) -> tuple[np.ndarray, str]:
    cache_path = Path(ROOT) / "cache" / dataset / "v5" / f"item_title_blair_k{DATASET_KCORE[dataset]}_dedup.pt"
    if not cache_path.exists():
        raise FileNotFoundError(
            f"Missing cached official BLaIR embeddings: {cache_path}. "
            "Run the official BLaIR encoder separately before publication-grade evaluation."
        )
    emb = torch.load(cache_path, weights_only=True)
    emb = emb.cpu().numpy() if hasattr(emb, "cpu") else np.asarray(emb)
    emb = emb.astype(np.float32)
    if emb.shape[0] != n_items:
        raise ValueError(f"{cache_path} has {emb.shape[0]} rows, expected {n_items}")
    norms = np.maximum(np.linalg.norm(emb, axis=1, keepdims=True), 1e-12)
    return emb / norms, str(cache_path)


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
                continue
            fout.write(line)
            kept += 1
    tmp.replace(path)
    return {"kept": kept, "removed": removed}


def run_dataset(dataset: str, seeds: list[int], run_dir: Path, max_folds: int, force: bool) -> dict[str, Any]:
    interactions, titles, n_users, n_items = load_dataset(dataset)
    blair_emb, cache_path = cached_blair_embeddings(dataset, n_items)
    record_path = run_dir / f"cold_full_catalog_records_{dataset}.jsonl"
    if force:
        removed = remove_method_rows(record_path, METHOD)
        print(f"{dataset}: removed existing {METHOD} rows: {removed['removed']:,}")
    done = completed_folds(record_path, METHOD)
    method_stats = {"ndcg": 0.0, "hr": 0.0, "rr": 0.0, "n": 0}
    fold_summaries: list[dict[str, Any]] = []
    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        if max_folds:
            splits = splits[:max_folds]
        for fold_id, (tr_idx, te_idx, cold_items) in enumerate(splits):
            if (seed, fold_id) in done:
                print(f"{dataset} seed={seed} fold={fold_id}: {METHOD} already complete; skipping")
                continue
            t0 = time.time()
            train_inters = [interactions[i] for i in tr_idx]
            test_inters = [interactions[i] for i in te_idx]
            warm_idx = np.array(sorted(set(range(n_items)) - set(cold_items)), dtype=np.int32)
            _, Xw = build_warm_sparse(train_inters, n_users, warm_idx)
            score_fn = make_score_blair_full(Xw, warm_idx, blair_emb, n_items)
            result, rows = eval_full_catalog(dataset, seed, fold_id, METHOD, score_fn, train_inters, test_inters, n_items)
            append_jsonl(record_path, rows)
            n = len(rows)
            method_stats["ndcg"] += float(result["NDCG@10"]) * n
            method_stats["hr"] += float(result["HR@10"]) * n
            method_stats["rr"] += float(result["MRR"]) * n
            method_stats["n"] += n
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
                }
            )
            print(f"{dataset} seed={seed} fold={fold_id}: {METHOD} NDCG@10={result['NDCG@10']:.5f} n={n:,}")
            del Xw
            gc.collect()
    n_total = method_stats["n"]
    return {
        "dataset": dataset,
        "method": METHOD,
        "candidate_scope": "full_catalog",
        "checkpoint": CHECKPOINT,
        "embedding_cache_path": cache_path,
        "seeds": seeds,
        "folds_requested_per_seed": max_folds or NUM_FOLDS,
        "status": "complete" if n_total else "no_new_rows",
        "summary_new_rows": {
            "NDCG@10": method_stats["ndcg"] / n_total if n_total else None,
            "HR@10": method_stats["hr"] / n_total if n_total else None,
            "MRR": method_stats["rr"] / n_total if n_total else None,
            "n_records": int(n_total),
        },
        "fold_summaries_new_rows": fold_summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--seeds", default=CONFIRMATORY_SEEDS_CSV)
    parser.add_argument("--max-folds", type=int, default=0)
    parser.add_argument("--force", action="store_true", help=f"Remove and rerun existing {METHOD} rows.")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    audit_path = run_dir / "official_blair_audit.json"
    audit = {
        "schema_version": 1,
        "method": METHOD,
        "baseline_slot": "blair_text",
        "status": "running",
        "checkpoint": CHECKPOINT,
        "datasets": {},
        "seeds": seeds,
    }
    write_json(audit_path, audit)
    for dataset in datasets:
        audit["datasets"][dataset] = run_dataset(dataset, seeds, run_dir, args.max_folds, args.force)
        write_json(audit_path, audit)
    required = set(DATASETS)
    present = set(audit["datasets"])
    audit["status"] = "complete" if required.issubset(present) and not args.max_folds else "partial"
    write_json(audit_path, audit)
    return 0 if audit["status"] in {"complete", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
