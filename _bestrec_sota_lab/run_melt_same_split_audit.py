"""Audit whether official MELT can fairly serve as a zero-interaction item-cold comparator.

The official MELT code targets long-tailed sequential recommendation. Its item
branch estimates tail item representations from item interaction contexts in
the training data. Under the BEST-Rec strict item-held-out protocol, every cold
target item has zero training interactions by construction, so those contexts
are empty. This script makes that mismatch measurable on the same folds.
"""

from __future__ import annotations

import argparse
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from sota_common import CONFIRMATORY_SEEDS_CSV, DATASETS, ROOT, make_item_kfold, make_lab_run_dir, parse_csv, utc_now, write_json
from run_all_confirmatory import load_dataset
from v5_utils import NUM_FOLDS


MELT_DIR = ROOT / "_bestrec_sota_lab" / "third_party" / "MELT"
SOURCE_FILES = [
    "embedder.py",
    "src/data.py",
    "src/sampler.py",
    "models/MELT_SASRec.py",
    "models/SASRec.py",
    "src/argument.py",
]


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def count_items(inters: list[dict[str, Any]]) -> Counter[int]:
    counts: Counter[int] = Counter()
    for row in inters:
        counts[int(row["item_id"])] += 1
    return counts


def audit_fold(
    *,
    dataset: str,
    seed: int,
    fold_id: int,
    train_inters: list[dict[str, Any]],
    test_inters: list[dict[str, Any]],
    cold_items: set[int],
) -> dict[str, Any]:
    train_counts = count_items(train_inters)
    test_counts = count_items(test_inters)
    cold_train_counts = {int(i): int(train_counts.get(int(i), 0)) for i in sorted(cold_items)}
    cold_test_counts = {int(i): int(test_counts.get(int(i), 0)) for i in sorted(cold_items)}
    cold_with_train_context = [i for i, n in cold_train_counts.items() if n > 0]
    cold_with_test_evidence = [i for i, n in cold_test_counts.items() if n > 0]
    return {
        "dataset": dataset,
        "seed": int(seed),
        "fold_id": int(fold_id),
        "cold_item_count": int(len(cold_items)),
        "cold_items_with_train_context": int(len(cold_with_train_context)),
        "cold_items_with_test_evidence": int(len(cold_with_test_evidence)),
        "all_cold_items_have_zero_train_context": not cold_with_train_context,
        "cold_train_context_examples": cold_with_train_context[:20],
        "cold_items_without_test_evidence_examples": [i for i, n in cold_test_counts.items() if n == 0][:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--seeds", default=CONFIRMATORY_SEEDS_CSV)
    parser.add_argument("--max-folds", type=int, default=0)
    args = parser.parse_args()

    if not MELT_DIR.exists():
        raise FileNotFoundError(f"official MELT checkout not found: {MELT_DIR}")

    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    for dataset in datasets:
        if dataset not in DATASETS:
            raise ValueError(f"unknown dataset: {dataset}")

    run_id, run_dir = make_lab_run_dir("melt_same_split_audit", args.run_id)
    audit = {
        "schema_version": 1,
        "status": "running",
        "run_id": run_id,
        "method": "official_melt",
        "stage": "same_split_applicability_audit",
        "generated_utc": utc_now(),
        "official_source_dir": str(MELT_DIR),
        "official_source_hashes": {name: sha256(MELT_DIR / name) for name in SOURCE_FILES},
        "publication_grade_records": False,
        "datasets": {},
        "seeds": seeds,
        "max_folds": int(args.max_folds),
        "source_findings": [
            "embedder.py constructs item_context only from train_data.",
            "models/SASRec.py update_tail_item_representation updates a tail item only when item_context[i] has at least one context sequence.",
            "src/sampler.py evaluates against a sampled candidate set, not the full catalog.",
            "src/data.py ValidData/TestData expose one validation/test item per sequential user, not BEST-Rec's multi-target item-held-out record schema.",
        ],
        "notes": [
            "This audit does not claim a MELT result.",
            "It checks whether BEST-Rec cold items have the train contexts required by MELT's item branch.",
            "If all cold items have zero train context, official MELT is not a fair zero-interaction item-cold full-catalog comparator without a method change.",
        ],
    }
    audit_path = run_dir / "official_melt_audit.json"
    audit_alias_path = run_dir / "official_melt_same_split_audit.json"

    def write_audit() -> None:
        write_json(audit_path, audit)
        write_json(audit_alias_path, audit)

    write_audit()

    global_zero_context = True
    for dataset in datasets:
        interactions, _, _, n_items, _ = load_dataset(dataset)
        dataset_audit = {"n_items": int(n_items), "folds": []}
        for seed in seeds:
            splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
            if args.max_folds:
                splits = splits[: args.max_folds]
            for fold_id, (tr_idx, te_idx, cold_items) in enumerate(splits):
                fold = audit_fold(
                    dataset=dataset,
                    seed=seed,
                    fold_id=fold_id,
                    train_inters=[interactions[i] for i in tr_idx],
                    test_inters=[interactions[i] for i in te_idx],
                    cold_items=set(int(x) for x in cold_items),
                )
                global_zero_context = global_zero_context and bool(fold["all_cold_items_have_zero_train_context"])
                dataset_audit["folds"].append(fold)
                write_audit()
        audit["datasets"][dataset] = dataset_audit
        write_audit()

    audit["status"] = "not_applicable_to_zero_interaction_item_cold" if global_zero_context else "adapter_required"
    audit["completed_utc"] = utc_now()
    audit["reviewer_decision"] = (
        "Do not count proxy MELT evidence as publication-grade. Either restrict claims to methods applicable to zero-interaction item-cold full-catalog ranking, "
        "or define and run a modified MELT adapter as a new non-official baseline."
    )
    write_audit()
    print(f"MELT same-split audit: {run_dir}")
    print(f"Status: {audit['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
