"""Export SASRec-SBERT records from an existing lab checkpoint.

This avoids retraining when we need validation/test records from the exact same
checkpoint for paired fusion diagnostics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import torch

ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = ROOT / "_bestrec_sota_lab"
sys.path.insert(0, str(LAB_DIR))

import export_sasrec_sbert_records as sasrec_export  # noqa: E402


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--export-split", choices=("valid", "test"), required=True)
    parser.add_argument("--export-limit-users", type=int, default=0)
    parser.add_argument("--export-top-k", type=int, default=50)
    parser.add_argument("--method", default=None)
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    saved_config = dict(checkpoint["config"])
    saved_config["run_id"] = args.run_id
    saved_config["export_split"] = args.export_split
    saved_config["export_limit_users"] = args.export_limit_users
    saved_config["export_top_k"] = args.export_top_k
    if args.method is not None:
        saved_config["method"] = args.method
    export_args = argparse.Namespace(**saved_config)

    out_dir = LAB_DIR / "runs" / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "run_config.json").write_text(json.dumps(saved_config, indent=2, sort_keys=True), encoding="utf-8")

    device = sasrec_export.sasrec.DEVICE
    problem = sasrec_export.load_problem(export_args)
    model = sasrec_export.make_model(export_args, problem, device)
    model.load_state_dict({key: value.to(device) for key, value in checkpoint["state_dict"].items()})

    valid_dict = {u: i for u, i, _, _ in problem["valid_inters"]}
    extra_history = {u: [i] for u, i in valid_dict.items()} if args.export_split == "test" else None
    eval_inters = problem["test_inters"] if args.export_split == "test" else problem["valid_inters"]
    records_path = out_dir / f"warm_full_catalog_records_{export_args.category}_sasrec_sbert_{args.export_split}.jsonl"
    export_summary = sasrec_export.export_records(
        model,
        problem,
        eval_inters,
        records_path,
        export_args,
        device,
        args.export_split,
        extra_history=extra_history,
    )

    summary = {
        "schema_version": 1,
        "status": "complete",
        "publication_grade": False,
        "publication_note": "Checkpoint export for validation-safe diagnostics; not confirmatory evidence.",
        "source_checkpoint": sha256_file(checkpoint_path),
        "best_val_NDCG10": checkpoint.get("best_val_NDCG10"),
        "export": export_summary,
        "environment": sasrec_export.environment_record(device),
        "inputs": {name: sha256_file(path) for name, path in problem["paths"].items() if path is not None},
    }
    summary_path = out_dir / "sasrec_checkpoint_export_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "command": f"{sys.executable} " + " ".join(sys.argv),
        "argv": sys.argv,
        "generated_at_unix": time.time(),
        "artifacts": {
            "run_config": sha256_file(out_dir / "run_config.json"),
            "summary": sha256_file(summary_path),
            "source_checkpoint": sha256_file(checkpoint_path),
            "records": sha256_file(records_path),
        },
    }
    (out_dir / "results_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"run_id": args.run_id, "records": str(records_path), "metrics": export_summary["metrics"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
