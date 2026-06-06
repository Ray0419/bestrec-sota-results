"""Import publication-grade LIGER/TIGER records into a confirmatory lab run.

This importer is intentionally strict. It refuses smoke or partial LIGER runs,
even when their JSONL schema is valid, because the publication gate requires
all four datasets, frozen strict seeds, no caps, and a publication-grade source
audit from `run_liger_same_split_eval.py`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from run_official_blair_baseline import remove_method_rows
from sota_common import DATASETS, RUNS_DIR, parse_csv, write_json


METHOD = "tiger_liger_retrieval"
REQUIRED = {
    "dataset",
    "fold_id",
    "seed",
    "method",
    "user_id",
    "target_item_id",
    "candidate_scope",
    "ndcg10",
    "hr10",
    "rr",
}


def source_audit_is_publication_grade(audit: dict[str, Any], datasets: list[str]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if audit.get("method") != METHOD:
        failures.append(f"source audit method={audit.get('method')} expected {METHOD}")
    if audit.get("status") != "complete":
        failures.append(f"source audit status={audit.get('status')} expected complete")
    if audit.get("stage") != "candidate_publication_run":
        failures.append(f"source audit stage={audit.get('stage')} expected candidate_publication_run")
    if not audit.get("publication_grade_records"):
        failures.append("source audit publication_grade_records is not true")
    checks = audit.get("publication_scope_checks", {})
    for key in ("datasets_ok", "seeds_ok", "no_fold_cap", "no_target_cap", "minimum_train_steps_ok", "minimum_rqvae_epochs_ok"):
        if checks.get(key) is not True:
            failures.append(f"source audit publication_scope_checks.{key} is not true")
    missing = sorted(set(datasets) - set(audit.get("datasets", {})))
    if missing:
        failures.append(f"source audit missing datasets {missing}")
    return not failures, failures


def source_audit_is_partial_rebuild_ok(audit: dict[str, Any], datasets: list[str]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if audit.get("method") != METHOD:
        failures.append(f"source audit method={audit.get('method')} expected {METHOD}")
    if audit.get("status") not in {"complete", "partial_complete"}:
        failures.append(f"source audit status={audit.get('status')} expected complete or partial_complete")
    checks = audit.get("publication_scope_checks", {})
    for key in ("seeds_ok", "no_fold_cap", "no_target_cap", "minimum_train_steps_ok", "minimum_rqvae_epochs_ok"):
        if checks.get(key) is not True:
            failures.append(f"source audit publication_scope_checks.{key} is not true")
    return not failures, failures


def expected_fold_counts(source_audit: dict[str, Any], dataset: str) -> dict[tuple[int, int], int]:
    dataset_audit = source_audit.get("datasets", {}).get(dataset, {})
    counts: dict[tuple[int, int], int] = {}
    for fold in dataset_audit.get("folds", []):
        key = (int(fold["seed"]), int(fold["fold_id"]))
        if "target_rows_scored" in fold:
            counts[key] = int(fold["target_rows_scored"])
        elif "expected_records" in fold:
            counts[key] = int(fold["expected_records"])
    return counts


def expected_fold_counts_from_export(source_audit: dict[str, Any], dataset: str) -> dict[tuple[int, int], int]:
    export_run_id = (
        source_audit.get("source_export_run_id")
        or source_audit.get("export_run_id")
        or source_audit.get("config", {}).get("export_run_id")
    )
    if not export_run_id:
        return {}
    export_path = RUNS_DIR / str(export_run_id) / "liger_same_split_export_audit.json"
    if not export_path.exists():
        return {}
    export_audit = json.loads(export_path.read_text(encoding="utf-8"))
    config = source_audit.get("config", {})
    requested_seeds = set(parse_csv(str(config.get("seeds", "")), int)) if config.get("seeds") else None
    requested_folds = set(parse_csv(str(config.get("fold_ids", "")), int)) if config.get("fold_ids") else None
    max_targets = int(config.get("max_targets_per_fold") or 0)
    counts: dict[tuple[int, int], int] = {}
    for fold in export_audit.get("datasets", {}).get(dataset, {}).get("folds", []):
        seed = int(fold["seed"])
        fold_id = int(fold["fold_id"])
        if requested_seeds is not None and seed not in requested_seeds:
            continue
        if requested_folds is not None and fold_id not in requested_folds:
            continue
        expected = int(fold["target_count"])
        if max_targets:
            expected = min(expected, max_targets)
        counts[(seed, fold_id)] = expected
    return counts


def validate_and_copy_dataset(
    source_path: Path,
    target_path: Path,
    dataset: str,
    force: bool,
    dry_run: bool,
    expected_counts: dict[tuple[int, int], int],
) -> dict[str, Any]:
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    removed = {"removed": 0}
    if force and not dry_run:
        removed = remove_method_rows(target_path, METHOD)
    imported = 0
    stats = {"ndcg": 0.0, "hr": 0.0, "rr": 0.0}
    fold_counts: dict[tuple[int, int], int] = {}
    rows_to_write: list[str] = []
    with source_path.open("r", encoding="utf-8") as fin:
        for line_no, line in enumerate(fin, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            missing = REQUIRED - set(row)
            if missing:
                raise ValueError(f"{source_path}:{line_no}: missing fields {sorted(missing)}")
            if row["dataset"] != dataset:
                raise ValueError(f"{source_path}:{line_no}: dataset={row['dataset']} expected {dataset}")
            if row["method"] != METHOD:
                raise ValueError(f"{source_path}:{line_no}: method={row['method']} expected {METHOD}")
            if row["candidate_scope"] != "full_catalog":
                raise ValueError(f"{source_path}:{line_no}: candidate_scope={row['candidate_scope']}")
            for metric in ("ndcg10", "hr10", "rr"):
                val = float(row[metric])
                if val < 0.0 or val > 1.0:
                    raise ValueError(f"{source_path}:{line_no}: {metric}={val} outside [0,1]")
            imported += 1
            fold_key = (int(row["seed"]), int(row["fold_id"]))
            fold_counts[fold_key] = fold_counts.get(fold_key, 0) + 1
            stats["ndcg"] += float(row["ndcg10"])
            stats["hr"] += float(row["hr10"])
            stats["rr"] += float(row["rr"])
            rows_to_write.append(json.dumps(row, sort_keys=True))
    if imported <= 0:
        raise ValueError(f"{source_path}: no importable records")
    if expected_counts:
        missing_folds = sorted(set(expected_counts) - set(fold_counts))
        extra_folds = sorted(set(fold_counts) - set(expected_counts))
        mismatched = sorted(
            (key, expected_counts[key], fold_counts.get(key, 0))
            for key in set(expected_counts) & set(fold_counts)
            if expected_counts[key] != fold_counts[key]
        )
        if missing_folds or extra_folds or mismatched:
            raise ValueError(
                f"{source_path}: fold coverage mismatch; "
                f"missing={missing_folds[:5]} extra={extra_folds[:5]} mismatched={mismatched[:5]}"
            )
    if not dry_run:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("a", encoding="utf-8") as fout:
            for row in rows_to_write:
                fout.write(row + "\n")
    return {
        "dataset": dataset,
        "source_path": str(source_path),
        "target_file": target_path.name,
        "removed_existing_target_rows": int(removed["removed"]),
        "imported_rows": int(imported),
        "dry_run": bool(dry_run),
        "summary": {
            "NDCG@10": stats["ndcg"] / imported,
            "HR@10": stats["hr"] / imported,
            "MRR": stats["rr"] / imported,
            "n_records": imported,
        },
        "fold_count": len(fold_counts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Confirmatory target run id.")
    parser.add_argument("--source-run-id", required=True, help="Source run from run_liger_same_split_eval.py.")
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-partial-rebuild",
        action="store_true",
        help="Allow same-protocol partial rebuild imports. Imported records remain non-publication-grade and keep the strict gate failed until all datasets are complete.",
    )
    args = parser.parse_args()

    datasets = parse_csv(args.datasets)
    target_dir = RUNS_DIR / args.run_id
    source_dir = RUNS_DIR / args.source_run_id
    source_audit_path = source_dir / "tiger_liger_retrieval_audit.json"
    if not source_audit_path.exists():
        raise FileNotFoundError(source_audit_path)
    source_audit = json.loads(source_audit_path.read_text(encoding="utf-8"))
    ok, failures = source_audit_is_publication_grade(source_audit, datasets)
    partial_ok, partial_failures = source_audit_is_partial_rebuild_ok(source_audit, datasets)
    accepted_partial = bool(args.allow_partial_rebuild and not ok and partial_ok)
    audit = {
        "schema_version": 1,
        "status": "running",
        "target_run_id": args.run_id,
        "source_run_id": args.source_run_id,
        "source_audit": str(source_audit_path),
        "method": METHOD,
        "datasets": {},
        "dry_run": bool(args.dry_run),
        "publication_grade_source_ok": bool(ok),
        "source_failures": failures,
        "allow_partial_rebuild": bool(args.allow_partial_rebuild),
        "partial_rebuild_source_ok": bool(partial_ok),
        "partial_source_failures": partial_failures,
        "accepted_partial_rebuild_source": bool(accepted_partial),
    }
    import_audit_path = target_dir / "tiger_liger_retrieval_import_audit.json"
    write_json(import_audit_path, audit)
    if not ok and not accepted_partial:
        audit["status"] = "rejected_source_not_publication_grade"
        write_json(import_audit_path, audit)
        raise SystemExit("Refusing to import non-publication-grade LIGER/TIGER records:\n- " + "\n- ".join(failures))

    for dataset in datasets:
        source_path = source_dir / f"tiger_liger_retrieval_records_{dataset}.jsonl"
        target_path = target_dir / f"cold_full_catalog_records_{dataset}.jsonl"
        expected_counts = expected_fold_counts(source_audit, dataset)
        if not expected_counts and accepted_partial:
            expected_counts = expected_fold_counts_from_export(source_audit, dataset)
        audit["datasets"][dataset] = validate_and_copy_dataset(
            source_path,
            target_path,
            dataset,
            args.force,
            args.dry_run,
            expected_counts,
        )
        write_json(import_audit_path, audit)

    audit["status"] = "dry_run_complete" if args.dry_run else "complete"
    write_json(import_audit_path, audit)
    if not args.dry_run:
        all_requested_complete = all(
            audit["datasets"].get(dataset, {}).get("fold_count") == 25
            and audit["datasets"].get(dataset, {}).get("imported_rows", 0) > 0
            for dataset in datasets
        )
        aggregate_publication_grade = bool(ok or (accepted_partial and set(datasets) == set(DATASETS) and all_requested_complete))
        target_audit = dict(source_audit)
        target_audit["status"] = "complete" if aggregate_publication_grade else "partial"
        target_audit["import_audit_file"] = import_audit_path.name
        target_audit["source_run_id"] = args.source_run_id
        target_audit["publication_grade_records"] = bool(aggregate_publication_grade)
        target_audit["partial_rebuild_import"] = bool(accepted_partial)
        target_audit["chunked_rebuild_aggregate"] = bool(accepted_partial and aggregate_publication_grade)
        target_audit["datasets"] = {
            dataset: {
                "record_file": audit["datasets"][dataset]["target_file"],
                "n_records": audit["datasets"][dataset]["imported_rows"],
                "fold_count": audit["datasets"][dataset]["fold_count"],
                "summary": audit["datasets"][dataset]["summary"],
            }
            for dataset in datasets
        }
        checks = dict(target_audit.get("publication_scope_checks", {}))
        if aggregate_publication_grade:
            checks["datasets_ok"] = True
            checks["chunked_rebuild_aggregate_ok"] = True
        target_audit["publication_scope_checks"] = checks
        write_json(target_dir / "tiger_liger_retrieval_audit.json", target_audit)
    print(f"LIGER/TIGER import audit: {import_audit_path}")
    print(f"Status: {audit['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
