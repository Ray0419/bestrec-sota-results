"""Resumable full clean-rebuild orchestrator for the SOTA lab.

This script runs the record-generating commands in a fresh run directory. It is
intentionally only an orchestrator: it does not declare success unless the
requested stages actually finish and the final artifacts pass their own gates.
Use small stage/filter options for smoke tests, and the default all-dataset
settings for the publication rebuild.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from sota_common import CONFIRMATORY_SEEDS_CSV, DATASETS, LAB_DIR, RUNS_DIR, parse_csv, read_json, utc_now, write_json


DEFAULT_RUN_ID = "full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705"
CANONICAL_RUN_ID = "confirmatory_masked_candidate_20260701_20260705_candidate_only"
STAGE_ORDER = [
    "candidate",
    "lc2c_v2",
    "official_blair",
    "dropoutnet_fixed",
    "dropoutnet",
    "clcrec",
    "melt_audit",
    "liger_export",
    "liger_eval",
    "liger_import",
    "finalize",
    "compare",
]


def csv(values: list[str | int]) -> str:
    return ",".join(str(x) for x in values)


def tail(text: str, n: int = 40) -> list[str]:
    lines = text.splitlines()
    return lines[-n:]


def append_flag(cmd: list[str], flag: str, value: str | int | None) -> None:
    if value is not None and str(value) != "":
        cmd.extend([flag, str(value)])


def stage_commands(args: argparse.Namespace) -> dict[str, list[str]]:
    py = sys.executable
    datasets = args.datasets
    seeds = args.seeds
    bootstrap = str(args.bootstrap_reps)
    max_new = int(args.max_new_folds)
    fold_ids = args.fold_ids
    max_folds = int(args.max_folds)
    run_id = args.run_id
    export_run_id = args.liger_export_run_id
    liger_run_id = args.liger_run_id

    candidate = [
        py,
        str(LAB_DIR / "run_confirmatory_chunk.py"),
        "--run-id",
        run_id,
        "--datasets",
        datasets,
        "--seeds",
        seeds,
        "--config",
        str(LAB_DIR / "publication_candidate_mask_seen_v2.json"),
        "--candidate-only",
        "--finalize-bootstrap-reps",
        bootstrap,
    ]
    if max_new:
        candidate.extend(["--max-new-folds", str(max_new)])
    append_flag(candidate, "--fold-ids", fold_ids)

    lc2c = [
        py,
        str(LAB_DIR / "run_lc2c_v2_baseline.py"),
        "--run-id",
        run_id,
        "--datasets",
        datasets,
        "--seeds",
        seeds,
        "--finalize-bootstrap-reps",
        bootstrap,
    ]
    if max_new:
        lc2c.extend(["--max-new-folds", str(max_new)])
    append_flag(lc2c, "--fold-ids", fold_ids)
    if args.force:
        lc2c.append("--force")

    blair = [
        py,
        str(LAB_DIR / "run_official_blair_baseline.py"),
        "--run-id",
        run_id,
        "--datasets",
        datasets,
        "--seeds",
        seeds,
    ]
    if max_folds:
        blair.extend(["--max-folds", str(max_folds)])
    if args.force:
        blair.append("--force")

    dropout_fixed = [
        py,
        str(LAB_DIR / "run_official_dropoutnet_fixed.py"),
        "--run-id",
        run_id,
        "--datasets",
        datasets,
        "--seeds",
        seeds,
    ]
    if max_new:
        dropout_fixed.extend(["--max-new-folds", str(max_new)])
    append_flag(dropout_fixed, "--fold-ids", fold_ids)
    if args.force:
        dropout_fixed.append("--force")

    dropout = [
        py,
        str(LAB_DIR / "run_official_dropoutnet_baseline.py"),
        "--run-id",
        run_id,
        "--datasets",
        datasets,
        "--seeds",
        seeds,
    ]
    if max_new:
        dropout.extend(["--max-new-folds", str(max_new)])
    append_flag(dropout, "--fold-ids", fold_ids)
    if args.force:
        dropout.append("--force")

    clcrec = [
        py,
        str(LAB_DIR / "run_official_clcrec_canonical.py"),
        "--run-id",
        run_id,
        "--datasets",
        datasets,
        "--seeds",
        seeds,
    ]
    if max_new:
        clcrec.extend(["--max-new-folds", str(max_new)])
    append_flag(clcrec, "--fold-ids", fold_ids)
    if args.force:
        clcrec.append("--force")

    melt = [
        py,
        str(LAB_DIR / "run_melt_same_split_audit.py"),
        "--run-id",
        run_id,
        "--datasets",
        datasets,
        "--seeds",
        seeds,
    ]

    liger_export = [
        py,
        str(LAB_DIR / "run_liger_same_split_export.py"),
        "--run-id",
        export_run_id,
        "--datasets",
        datasets,
        "--seeds",
        seeds,
    ]
    if max_folds:
        liger_export.extend(["--max-folds", str(max_folds)])

    liger_eval = [
        py,
        str(LAB_DIR / "run_liger_same_split_eval.py"),
        "--run-id",
        liger_run_id,
        "--export-run-id",
        export_run_id,
        "--datasets",
        datasets,
        "--seeds",
        seeds,
        "--mode",
        "liger_dense",
        "--train-steps",
        str(args.liger_train_steps),
        "--rqvae-epochs",
        str(args.liger_rqvae_epochs),
        "--device",
        args.device,
        "--resume",
    ]
    if max_folds:
        liger_eval.extend(["--max-folds", str(max_folds)])
    append_flag(liger_eval, "--fold-ids", fold_ids)
    if args.max_targets_per_fold:
        liger_eval.extend(["--max-targets-per-fold", str(args.max_targets_per_fold)])

    liger_import = [
        py,
        str(LAB_DIR / "import_liger_records.py"),
        "--run-id",
        run_id,
        "--source-run-id",
        liger_run_id,
        "--datasets",
        datasets,
    ]
    if args.force:
        liger_import.append("--force")
    if args.allow_partial_liger_import:
        liger_import.append("--allow-partial-rebuild")

    finalize = [
        py,
        str(LAB_DIR / "finalize.py"),
        "--run-id",
        run_id,
        "--bootstrap-reps",
        bootstrap,
    ]

    compare = [
        py,
        str(LAB_DIR / "validate_full_clean_rebuild.py"),
        "--run-id",
        run_id,
        "--canonical-run-id",
        args.canonical_run_id,
    ]

    return {
        "candidate": candidate,
        "lc2c_v2": lc2c,
        "official_blair": blair,
        "dropoutnet_fixed": dropout_fixed,
        "dropoutnet": dropout,
        "clcrec": clcrec,
        "melt_audit": melt,
        "liger_export": liger_export,
        "liger_eval": liger_eval,
        "liger_import": liger_import,
        "finalize": finalize,
        "compare": compare,
    }


def selected_stages(raw: str) -> list[str]:
    stages = STAGE_ORDER if raw == "all" else parse_csv(raw)
    unknown = [stage for stage in stages if stage not in STAGE_ORDER]
    if unknown:
        raise ValueError(f"unknown stages: {unknown}; valid stages: {STAGE_ORDER}")
    return stages


def audit_path(run_id: str) -> Path:
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir / "full_clean_rebuild_audit.json"


def load_audit(run_id: str) -> dict[str, Any]:
    path = audit_path(run_id)
    return read_json(path, {"schema_version": 1, "run_id": run_id, "stages": {}, "created_utc": utc_now()})


def save_audit(run_id: str, payload: dict[str, Any]) -> None:
    payload["updated_utc"] = utc_now()
    write_json(audit_path(run_id), payload)


def run_stage(stage: str, cmd: list[str], args: argparse.Namespace, audit: dict[str, Any]) -> int:
    entry = {
        "stage": stage,
        "command": cmd,
        "started_utc": utc_now(),
        "dry_run": bool(args.dry_run),
    }
    audit.setdefault("stages", {})[stage] = entry
    save_audit(args.run_id, audit)
    print(f"\n=== {stage} ===")
    print(" ".join(cmd))
    if args.dry_run:
        entry["status"] = "dry_run"
        entry["completed_utc"] = utc_now()
        save_audit(args.run_id, audit)
        return 0
    proc = subprocess.run(cmd, cwd=LAB_DIR.parent, check=False, capture_output=True, text=True)
    traceback_seen = "Traceback (most recent call last):" in proc.stderr
    effective_returncode = 1 if traceback_seen else int(proc.returncode)
    entry.update(
        {
            "returncode": int(proc.returncode),
            "effective_returncode": int(effective_returncode),
            "traceback_seen": bool(traceback_seen),
            "stdout_tail": tail(proc.stdout),
            "stderr_tail": tail(proc.stderr),
            "completed_utc": utc_now(),
            "status": "passed" if effective_returncode == 0 else "failed",
        }
    )
    save_audit(args.run_id, audit)
    if proc.stdout:
        print("\n".join(tail(proc.stdout, 12)))
    if proc.stderr:
        print("\n".join(tail(proc.stderr, 12)), file=sys.stderr)
    return int(effective_returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--canonical-run-id", default=CANONICAL_RUN_ID)
    parser.add_argument("--liger-export-run-id", default="", help="Defaults to <run-id>__liger_export.")
    parser.add_argument("--liger-run-id", default="", help="Defaults to <run-id>__liger_eval.")
    parser.add_argument("--stages", default="all", help=f"Comma-separated stages or 'all'. Valid: {','.join(STAGE_ORDER)}")
    parser.add_argument("--datasets", default=csv(list(DATASETS)))
    parser.add_argument("--seeds", default=CONFIRMATORY_SEEDS_CSV)
    parser.add_argument("--bootstrap-reps", type=int, default=2000)
    parser.add_argument("--max-new-folds", type=int, default=0, help="Chunk candidate/LC2C/DropoutNet/CLCRec stages; 0 means full.")
    parser.add_argument("--max-folds", type=int, default=0, help="Fold cap for BLaIR/LIGER export/eval smoke use; 0 means full.")
    parser.add_argument("--fold-ids", default="")
    parser.add_argument("--max-targets-per-fold", type=int, default=0)
    parser.add_argument("--liger-train-steps", type=int, default=1000)
    parser.add_argument("--liger-rqvae-epochs", type=int, default=100)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-partial-liger-import", action="store_true", help="Allow partial same-protocol LIGER imports for incremental rebuild slices.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()
    if not args.liger_export_run_id:
        args.liger_export_run_id = f"{args.run_id}__liger_export"
    if not args.liger_run_id:
        args.liger_run_id = f"{args.run_id}__liger_eval"

    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    if any(dataset not in DATASETS for dataset in datasets):
        raise ValueError(f"unknown datasets: {datasets}")
    args.datasets = csv(datasets)
    args.seeds = csv(seeds)

    stages = selected_stages(args.stages)
    commands = stage_commands(args)
    audit = load_audit(args.run_id)
    audit.update(
        {
            "run_id": args.run_id,
            "canonical_run_id": args.canonical_run_id,
            "liger_export_run_id": args.liger_export_run_id,
            "liger_run_id": args.liger_run_id,
            "requested_stages": stages,
            "datasets": datasets,
            "seeds": seeds,
            "publication_shape": {
                "all_datasets": set(datasets) == set(DATASETS),
                "strict_seed_count": len(seeds) == len(parse_csv(CONFIRMATORY_SEEDS_CSV, int)),
                "no_caps": not args.max_new_folds and not args.max_folds and not args.fold_ids and not args.max_targets_per_fold,
                "liger_publication_minimum": args.liger_train_steps >= 1000 and args.liger_rqvae_epochs >= 100,
            },
        }
    )
    save_audit(args.run_id, audit)
    for stage in stages:
        code = run_stage(stage, commands[stage], args, audit)
        if code and not args.continue_on_error:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
