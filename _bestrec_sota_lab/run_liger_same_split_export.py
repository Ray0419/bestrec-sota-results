"""Export BEST-Rec item-cold folds into LIGER's processed sequence format.

This is not a publication-grade LIGER result by itself. It is the adapter layer
needed before running the official `external/liger` training/evaluation stack on
the same item-held-out folds used by the SOTA lab. The script writes only inside
`_bestrec_sota_lab/runs/<run_id>/`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

from sota_common import CONFIRMATORY_SEEDS_CSV, DATASETS, ROOT, make_item_kfold, make_lab_run_dir, parse_csv, utc_now, write_json
from run_all_confirmatory import load_dataset, user_train_and_test
from v5_utils import NUM_FOLDS


LIGER_DIR = ROOT / "external" / "liger"


def meta_to_text(meta: Any) -> str:
    if isinstance(meta, str):
        return meta
    if not isinstance(meta, dict):
        return str(meta)
    parts: list[str] = []
    title = meta.get("title")
    if title:
        parts.append(f"Title: {title}.")
    for key in ("brand", "categories", "description", "price", "avg_rating", "rating_num"):
        value = meta.get(key)
        if value is None or value == "":
            continue
        if isinstance(value, (list, tuple)):
            value = " > ".join(str(x) for x in value if x)
        parts.append(f"{key}: {value}.")
    return " ".join(parts).strip() or "No item text available."


def group_ordered_items(inters: list[dict[str, Any]]) -> dict[int, list[int]]:
    grouped: dict[int, list[int]] = defaultdict(list)
    for row in inters:
        grouped[int(row["user_id"])].append(int(row["item_id"]))
    return dict(grouped)


def write_dataset_assets(export_dir: Path, dataset: str, item_meta: dict[int, Any], n_items: int, item_title_emb: Any) -> dict[str, str]:
    asset_dir = export_dir / dataset / "dataset_assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    id2meta_path = asset_dir / "bestrec_liger_id2meta.json"
    embedding_path = asset_dir / "bestrec_liger_item_embeddings.pt"
    id2meta = {str(i + 1): meta_to_text(item_meta.get(i, {})) for i in range(n_items)}
    write_json(id2meta_path, id2meta)
    emb = item_title_emb.detach().cpu() if hasattr(item_title_emb, "detach") else torch.as_tensor(np.asarray(item_title_emb))
    torch.save(emb, embedding_path)
    return {"id2meta_file": str(id2meta_path), "embedding_file": str(embedding_path)}


def write_liger_fold(
    *,
    export_dir: Path,
    dataset: str,
    seed: int,
    fold_id: int,
    train_inters: list[dict[str, Any]],
    test_inters: list[dict[str, Any]],
    cold_items: set[int],
    n_items: int,
    id2meta_path: Path,
    embedding_path: Path,
    max_items_per_seq: int,
    max_targets: int,
    verify_loader: bool,
) -> dict[str, Any]:
    fold_dir = export_dir / dataset / f"seed_{seed}" / f"fold_{fold_id}"
    fold_dir.mkdir(parents=True, exist_ok=True)
    data_path = fold_dir / "bestrec_liger_sequences.txt"
    target_map_path = fold_dir / "bestrec_liger_target_map.jsonl"
    split_path = fold_dir / "bestrec_liger_expected_split.json"

    train_by_user = group_ordered_items(train_inters)
    user_train, user_test = user_train_and_test(train_inters, test_inters)
    eval_users = sorted(u for u in user_test if user_test[u] and user_train[u])
    warm_items = sorted(set(range(n_items)) - set(cold_items))
    expected_seen = sorted(int(i) + 1 for i in warm_items)
    exported_target_liger_ids: set[int] = set()

    line_count = 0
    target_count = 0
    pseudo_user_id = 1
    with data_path.open("w", encoding="utf-8") as data_f, target_map_path.open("w", encoding="utf-8") as map_f:
        # Anchor sequences ensure every warm item is eligible as seen in LIGER's
        # chronological split rule, where only positions before the last two are
        # counted as train items.
        for original_user in sorted(train_by_user):
            hist = [int(i) + 1 for i in train_by_user[original_user] if int(i) not in cold_items]
            if not hist:
                continue
            seq = hist + [hist[-1], hist[-1]]
            if len(seq) > max_items_per_seq:
                seq = seq[-max_items_per_seq:]
            data_f.write(f"{pseudo_user_id} " + " ".join(str(x) for x in seq) + "\n")
            pseudo_user_id += 1
            line_count += 1

        for original_user in eval_users:
            hist0 = [int(i) for i in train_by_user.get(original_user, []) if int(i) not in cold_items]
            if not hist0:
                continue
            hist = [i + 1 for i in hist0]
            for target0 in sorted(user_test[original_user]):
                if target0 not in cold_items:
                    continue
                target = int(target0) + 1
                exported_target_liger_ids.add(target)
                seq = hist + [hist[-1], target]
                if len(seq) > max_items_per_seq:
                    seq = seq[-max_items_per_seq:]
                data_f.write(f"{pseudo_user_id} " + " ".join(str(x) for x in seq) + "\n")
                map_f.write(
                    json.dumps(
                        {
                            "dataset": dataset,
                            "seed": int(seed),
                            "fold_id": int(fold_id),
                            "pseudo_user_id": int(pseudo_user_id),
                            "original_user_id": int(original_user),
                            "target_item_id": int(target0),
                            "liger_target_item_id": int(target),
                            "history_length": int(len(hist0)),
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
                pseudo_user_id += 1
                line_count += 1
                target_count += 1
                if max_targets and target_count >= max_targets:
                    break
            if max_targets and target_count >= max_targets:
                break

    expected_unseen_test = sorted(exported_target_liger_ids)
    split_payload = {
        "dataset": dataset,
        "seed": int(seed),
        "fold_id": int(fold_id),
        "item_id_base": "BEST-Rec zero-based item_id plus one for LIGER",
        "expected_seen_items": expected_seen,
        "expected_unseen_test_items": expected_unseen_test,
        "all_fold_cold_items": sorted(int(i) + 1 for i in cold_items),
        "expected_unseen_val_items": [],
        "max_items_per_seq": int(max_items_per_seq),
        "sequence_count": int(line_count),
        "target_count": int(target_count),
    }
    write_json(split_path, split_payload)

    verification: dict[str, Any] = {"status": "not_run"}
    if verify_loader:
        sys.path.insert(0, str(LIGER_DIR))
        from ID_generation.utils import process_data_split  # type: ignore

        config = {"dataset": {"max_items_per_seq": int(max_items_per_seq)}}
        id_split, user_sequence = process_data_split(config, str(data_path), str(id2meta_path), is_steam=False)
        unseen_test = sorted(int(x) for x in id_split["unseen_test"].tolist())
        unseen_val = sorted(int(x) for x in id_split["unseen_val"].tolist())
        missing_expected_cold = sorted(set(expected_unseen_test[:]) - set(unseen_test))
        unexpected_unseen_test = sorted(set(unseen_test) - set(expected_unseen_test))
        verification = {
            "status": "passed" if not missing_expected_cold and not unexpected_unseen_test else "failed",
            "official_loader": "external/liger/ID_generation/utils.py::process_data_split",
            "user_sequence_count": int(len(user_sequence)),
            "seen_count": int(len(id_split["seen"])),
            "unseen_val_count": int(len(unseen_val)),
            "unseen_test_count": int(len(unseen_test)),
            "missing_expected_cold_liger_ids": missing_expected_cold,
            "unexpected_unseen_test_liger_ids": unexpected_unseen_test,
            "note": "Verification uses LIGER's own split parser on the exported processed data file.",
        }

    return {
        "dataset": dataset,
        "seed": int(seed),
        "fold_id": int(fold_id),
        "export_dir": str(fold_dir),
        "data_file": str(data_path),
        "id2meta_file": str(id2meta_path),
        "target_map_file": str(target_map_path),
        "embedding_file": str(embedding_path),
        "expected_split_file": str(split_path),
        "sequence_count": int(line_count),
        "target_count": int(target_count),
        "cold_item_count": int(len(cold_items)),
        "warm_item_count": int(len(warm_items)),
        "verification": verification,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--seeds", default=CONFIRMATORY_SEEDS_CSV)
    parser.add_argument("--max-folds", type=int, default=0)
    parser.add_argument("--max-targets-per-fold", type=int, default=0)
    parser.add_argument("--max-items-per-seq", type=int, default=20)
    parser.add_argument("--no-verify-loader", action="store_true")
    args = parser.parse_args()

    if not LIGER_DIR.exists():
        raise FileNotFoundError(f"official LIGER checkout not found: {LIGER_DIR}")

    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    for dataset in datasets:
        if dataset not in DATASETS:
            raise ValueError(f"unknown dataset: {dataset}")

    run_id, run_dir = make_lab_run_dir("liger_same_split_export", args.run_id)
    export_dir = run_dir / "liger_exports"
    audit = {
        "schema_version": 1,
        "status": "running",
        "run_id": run_id,
        "method": "tiger_liger_retrieval",
        "stage": "adapter_export_only",
        "generated_utc": utc_now(),
        "official_source_dir": str(LIGER_DIR),
        "official_split_parser": "external/liger/ID_generation/utils.py::process_data_split",
        "datasets": {},
        "seeds": seeds,
        "max_folds": int(args.max_folds),
        "max_targets_per_fold": int(args.max_targets_per_fold),
        "max_items_per_seq": int(args.max_items_per_seq),
        "publication_grade_records": False,
        "notes": [
            "This export does not claim a LIGER result.",
            "It creates LIGER-compatible processed sequence, item-text, embedding, and target-map files for the exact BEST-Rec item-cold folds.",
            "The publication gate must remain failed until official LIGER/TIGER training is run on these exports and canonical full-catalog JSONL records are imported.",
        ],
    }
    audit_path = run_dir / "liger_same_split_export_audit.json"
    write_json(audit_path, audit)

    failures: list[str] = []
    for dataset in datasets:
        interactions, item_meta, n_users, n_items, item_title_emb = load_dataset(dataset)
        assets = write_dataset_assets(export_dir, dataset, item_meta, n_items, item_title_emb)
        dataset_audit = {
            "n_users": int(n_users),
            "n_items": int(n_items),
            "dataset_assets": assets,
            "folds": [],
        }
        for seed in seeds:
            splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
            if args.max_folds:
                splits = splits[: args.max_folds]
            for fold_id, (tr_idx, te_idx, cold_items) in enumerate(splits):
                train_inters = [interactions[i] for i in tr_idx]
                test_inters = [interactions[i] for i in te_idx]
                fold_audit = write_liger_fold(
                    export_dir=export_dir,
                    dataset=dataset,
                    seed=seed,
                    fold_id=fold_id,
                    train_inters=train_inters,
                    test_inters=test_inters,
                    cold_items=set(int(x) for x in cold_items),
                    n_items=n_items,
                    id2meta_path=Path(assets["id2meta_file"]),
                    embedding_path=Path(assets["embedding_file"]),
                    max_items_per_seq=int(args.max_items_per_seq),
                    max_targets=int(args.max_targets_per_fold),
                    verify_loader=not args.no_verify_loader,
                )
                if fold_audit["verification"].get("status") == "failed":
                    failures.append(f"{dataset} seed={seed} fold={fold_id} LIGER split verification failed")
                dataset_audit["folds"].append(fold_audit)
                write_json(audit_path, audit)
        audit["datasets"][dataset] = dataset_audit
        write_json(audit_path, audit)

    audit["status"] = "export_complete" if not failures else "export_failed"
    audit["failures"] = failures
    audit["completed_utc"] = utc_now()
    write_json(audit_path, audit)
    print(f"LIGER same-split export: {run_dir}")
    print(f"Status: {audit['status']}")
    if failures:
        for failure in failures:
            print(f"- {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
