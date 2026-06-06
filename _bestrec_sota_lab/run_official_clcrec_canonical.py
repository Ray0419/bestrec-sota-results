"""Run faithful CLCRec as canonical `official_clcrec` records.

The older wrapper writes source records that must later be imported. This
runner writes directly into the active lab run with exact seed/fold coverage
checks, while importing the faithful CLCRec implementation read-only from
`_bestrec_run`.
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
import torch

from finalize import expected_fold_record_counts
from protocol import load_protocol, protocol_summary
from run_official_blair_baseline import remove_method_rows
from sota_common import BESTREC_RUN_DIR, CONFIRMATORY_SEEDS_CSV, DATASETS, RUNS_DIR, append_jsonl, parse_csv, read_json, write_json

sys.path.insert(0, str(BESTREC_RUN_DIR))
from run_cold_item import make_item_kfold  # noqa: E402
from run_faithful_clcrec import (  # noqa: E402
    BPR_EPOCHS,
    CLC_EPOCHS,
    NORMALIZE,
    encode_all,
    eval_full,
    load_dataset,
    make_score_clcrec,
    select_hp,
    train_bpr,
    train_clcrec_encoder,
)
from v5_utils import NUM_FOLDS  # noqa: E402


METHOD = "official_clcrec"


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
    *,
    dataset: str,
    seeds: list[int],
    run_dir: Path,
    max_new_folds: int,
    fold_ids: set[int] | None,
    force: bool,
    sweep_hp: bool,
) -> dict[str, Any]:
    interactions, n_users, n_items, emb_t = load_dataset(dataset)
    sbert_all = emb_t.cpu().numpy().astype(np.float32) if hasattr(emb_t, "cpu") else np.asarray(emb_t, dtype=np.float32)
    bpr_epochs = int(BPR_EPOCHS.get(dataset, 200))
    record_path = run_dir / f"cold_full_catalog_records_{dataset}.jsonl"
    if force:
        removed = remove_method_rows(record_path, METHOD)
        print(f"{dataset}: removed existing {METHOD} rows: {removed['removed']:,}")
    counts = method_fold_counts(record_path, METHOD)
    expected = expected_fold_record_counts(dataset, seeds)
    stats = {"ndcg": 0.0, "hr": 0.0, "rr": 0.0, "n": 0}
    fold_summaries: list[dict[str, Any]] = []
    selected_hps: list[dict[str, Any]] = []
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
            if sweep_hp:
                t_sel = time.time()
                hp = select_hp(
                    dataset,
                    train_inters,
                    set(int(x) for x in cold_items),
                    sbert_all,
                    n_users,
                    n_items,
                    int(seed),
                    int(fold_id),
                    bpr_epochs=bpr_epochs,
                )
                hp["selection_seconds"] = time.time() - t_sel
            else:
                hp = {
                    "tau": 0.5,
                    "lr": 1e-3,
                    "hidden": 256,
                    "note": "no_sweep_uses_modal_winner_from_source_runner",
                }
            hp["seed"] = int(seed)
            hp["fold_id"] = int(fold_id)
            selected_hps.append(dict(hp))
            U_out, V_warm, bpr_loss = train_bpr(
                train_inters,
                warm_idx,
                n_users,
                int(seed),
                n_epochs=bpr_epochs,
            )
            model, _ = train_clcrec_encoder(
                sbert_all[warm_idx],
                V_warm,
                int(seed),
                tau=float(hp["tau"]),
                lr=float(hp["lr"]),
                hidden=int(hp["hidden"]),
                epochs=CLC_EPOCHS,
            )
            V_full = np.zeros((n_items, V_warm.shape[1]), dtype=np.float32)
            if NORMALIZE:
                V_warm_norm = V_warm / np.maximum(np.linalg.norm(V_warm, axis=1, keepdims=True), 1e-12)
                V_full[warm_idx] = V_warm_norm
            else:
                V_full[warm_idx] = V_warm
            V_full[cold_idx] = encode_all(model, sbert_all[cold_idx])
            score_fn = make_score_clcrec(U_out, V_full, n_items)
            result, _per_user, rows = eval_full(score_fn, train_inters, test_inters, n_items)
            for row in rows:
                row.update(
                    {
                        "dataset": dataset,
                        "seed": int(seed),
                        "fold_id": int(fold_id),
                        "method": METHOD,
                        "candidate_scope": "full_catalog",
                    }
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
                    "bpr_loss": float(bpr_loss) if bpr_loss is not None else None,
                    "hp": dict(hp),
                    "bpr_epochs": bpr_epochs,
                    "clc_epochs": CLC_EPOCHS,
                }
            )
            print(f"{dataset} seed={seed} fold={fold_id}: {METHOD} NDCG@10={result['NDCG@10']:.5f} n={n:,}")
            del U_out, V_warm, V_full, model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        if max_new_folds and new_folds >= max_new_folds:
            break
    total = int(stats["n"])
    return {
        "dataset": dataset,
        "method": METHOD,
        "candidate_scope": "full_catalog",
        "seeds": seeds,
        "sweep_hp": bool(sweep_hp),
        "bpr_epochs": bpr_epochs,
        "clc_epochs": CLC_EPOCHS,
        "new_folds": int(new_folds),
        "summary_new_rows": {
            "NDCG@10": stats["ndcg"] / total if total else None,
            "HR@10": stats["hr"] / total if total else None,
            "MRR": stats["rr"] / total if total else None,
            "n_records": total,
        },
        "fold_summaries_new_rows": fold_summaries,
        "selected_hps_new_rows": selected_hps,
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
    parser.add_argument("--no-sweep", action="store_true")
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

    audit_path = run_dir / "official_clcrec_audit.json"
    audit = read_json(
        audit_path,
        {
            "schema_version": 1,
            "method": METHOD,
            "baseline_slot": "clcrec_contrastive",
            "status": "running",
            "protocol": protocol_summary(protocol),
            "datasets": {},
            "seeds": seeds,
            "sweep_hp": not args.no_sweep,
            "notes": (
                "Faithful CLCRec imported read-only from _bestrec_run; default "
                "mode performs per-fold inner validation and writes canonical "
                "full-catalog records."
            ),
        },
    )
    audit["status"] = "running"
    audit["seeds"] = seeds
    audit["protocol"] = protocol_summary(protocol)
    audit["sweep_hp"] = not args.no_sweep
    write_json(audit_path, audit)
    for dataset in datasets:
        audit["datasets"][dataset] = run_dataset(
            dataset=dataset,
            seeds=seeds,
            run_dir=run_dir,
            max_new_folds=max(0, int(args.max_new_folds)),
            fold_ids=fold_ids,
            force=bool(args.force),
            sweep_hp=not args.no_sweep,
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
