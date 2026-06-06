"""Import publication-grade external baseline records into a lab run.

The source records are produced outside the canonical lab runner but must
already follow the full-catalog per-pair schema. This importer renames the
method to an `official_*` label and appends rows to
`cold_full_catalog_records_<dataset>.jsonl` so finalization can perform paired
tests against the lab candidate on the same seed/fold/user/item keys.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sota_common import DATASETS, RUNS_DIR, parse_csv, write_json
from run_official_blair_baseline import remove_method_rows


REQUIRED = {"dataset", "fold_id", "seed", "method", "user_id", "target_item_id", "candidate_scope", "ndcg10", "hr10", "rr"}


def import_dataset(
    *,
    run_dir: Path,
    source_path: Path,
    dataset: str,
    source_method: str,
    target_method: str,
    force: bool,
) -> dict[str, Any]:
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    target_path = run_dir / f"cold_full_catalog_records_{dataset}.jsonl"
    if force:
        removed = remove_method_rows(target_path, target_method)
    else:
        removed = {"removed": 0}
    imported = 0
    bad = 0
    stats = {"ndcg": 0.0, "hr": 0.0, "rr": 0.0}
    with source_path.open("r", encoding="utf-8") as fin, target_path.open("a", encoding="utf-8") as fout:
        for line_no, line in enumerate(fin, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            missing = REQUIRED - set(row)
            if missing:
                raise ValueError(f"{source_path}:{line_no}: missing fields {sorted(missing)}")
            if row["dataset"] != dataset:
                raise ValueError(f"{source_path}:{line_no}: dataset={row['dataset']} expected {dataset}")
            if row["candidate_scope"] != "full_catalog":
                raise ValueError(f"{source_path}:{line_no}: candidate_scope={row['candidate_scope']}")
            if source_method and row["method"] != source_method:
                bad += 1
                continue
            row["method"] = target_method
            fout.write(json.dumps(row, sort_keys=True) + "\n")
            imported += 1
            stats["ndcg"] += float(row["ndcg10"])
            stats["hr"] += float(row["hr10"])
            stats["rr"] += float(row["rr"])
    return {
        "dataset": dataset,
        "source_path": str(source_path),
        "target_file": target_path.name,
        "source_method": source_method,
        "target_method": target_method,
        "removed_existing_target_rows": int(removed["removed"]),
        "skipped_nonmatching_source_method_rows": int(bad),
        "imported_rows": int(imported),
        "summary": {
            "NDCG@10": stats["ndcg"] / imported if imported else None,
            "HR@10": stats["hr"] / imported if imported else None,
            "MRR": stats["rr"] / imported if imported else None,
            "n_records": int(imported),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--source-pattern", required=True, help="Pattern with {dataset}, e.g. results_faithful_dropoutnet_perpair_{dataset}.jsonl")
    parser.add_argument("--source-method", required=True)
    parser.add_argument("--target-method", required=True)
    parser.add_argument("--audit-file", required=True)
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    source_dir = Path(args.source_dir)
    datasets = parse_csv(args.datasets)
    audit = {
        "schema_version": 1,
        "status": "running",
        "source_dir": str(source_dir),
        "source_pattern": args.source_pattern,
        "source_method": args.source_method,
        "target_method": args.target_method,
        "datasets": {},
    }
    audit_path = run_dir / args.audit_file
    write_json(audit_path, audit)
    for dataset in datasets:
        source_path = source_dir / args.source_pattern.format(dataset=dataset)
        audit["datasets"][dataset] = import_dataset(
            run_dir=run_dir,
            source_path=source_path,
            dataset=dataset,
            source_method=args.source_method,
            target_method=args.target_method,
            force=args.force,
        )
        write_json(audit_path, audit)
    audit["status"] = "complete" if set(DATASETS).issubset(set(audit["datasets"])) else "partial"
    write_json(audit_path, audit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
