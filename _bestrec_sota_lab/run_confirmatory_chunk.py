"""Run a resumable chunk of the repaired confirmatory candidate.

This exists for long publication-shaped runs where Books makes a single
foreground command impractical. The run directory keeps one authoritative
four-dataset confirmatory `run_config.json`; each invocation fills in one or
more dataset record files and then finalizes the still-partial run.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from run_confirmatory import load_ltr_config
from sota_common import (
    CONFIRMATORY_SEEDS_CSV,
    DATASETS,
    LAB_DIR,
    LAB_PROTOCOL,
    OFFICIAL_DROPOUTNET_FEATURE_CONFIG,
    RUNS_DIR,
    parse_csv,
    read_json,
    run_cold_ltr_dataset,
    write_json,
    write_run_config,
)


def _expected_seeds() -> list[int]:
    return [int(x) for x in LAB_PROTOCOL.get("fresh_confirmatory_seeds", [])]


def validate_config(config_meta: dict[str, Any], seeds: list[int]) -> None:
    expected = _expected_seeds()
    if seeds != expected:
        raise ValueError(f"confirmatory chunk seeds must be {expected}, got {seeds}")
    if config_meta.get("protocol", {}).get("protocol_id") != LAB_PROTOCOL.get("protocol_id"):
        raise ValueError("frozen candidate config was not produced under the active strict protocol")
    cfg_seeds = [int(x) for x in config_meta.get("protocol", {}).get("fresh_confirmatory_seeds", [])]
    if cfg_seeds and cfg_seeds != expected:
        raise ValueError(f"frozen config seeds must be {expected}, got {cfg_seeds}")
    if config_meta.get("dropoutnet_feature_config") != OFFICIAL_DROPOUTNET_FEATURE_CONFIG:
        raise ValueError("frozen candidate config does not match active DropoutNet feature config")
    required_ltr = LAB_PROTOCOL.get("required_candidate_ltr_config", {})
    ltr_config = config_meta.get("ltr_config", {})
    for key, value in required_ltr.items():
        if ltr_config.get(key) != value:
            raise ValueError(f"frozen candidate config {key}={ltr_config.get(key)!r}, expected {value!r}")


def ensure_run_config(run_dir: Path, run_id: str, seeds: list[int], config_meta: dict[str, Any], candidate_only: bool) -> None:
    path = run_dir / "run_config.json"
    if not path.exists():
        write_run_config(
            run_dir,
            {
                "stage": "confirmatory",
                "run_id": run_id,
                "datasets": list(DATASETS),
                "seeds": seeds,
                "candidate_scope": "full_catalog",
                "no_books_cap": True,
                "max_folds": 0,
                "quick": False,
                "candidate_only": bool(candidate_only),
                "chunked_confirmatory": True,
                "frozen_config": config_meta,
            },
        )
        return

    existing = read_json(path)
    if existing.get("stage") != "confirmatory":
        raise ValueError(f"{path} is not a confirmatory run_config.json")
    if set(existing.get("datasets", [])) != set(DATASETS):
        raise ValueError(f"{path} does not describe the full protocol dataset set")
    if [int(x) for x in existing.get("seeds", [])] != seeds:
        raise ValueError(f"{path} seed list does not match requested fresh seeds")
    if bool(existing.get("candidate_only")) != bool(candidate_only):
        raise ValueError(f"{path} candidate_only does not match this invocation")
    existing_meta = existing.get("frozen_config", {})
    if existing_meta.get("ltr_config") != config_meta.get("ltr_config"):
        raise ValueError(f"{path} frozen LTR config differs from requested config")


def merge_partial(run_dir: Path, run_id: str, results: dict[str, Any]) -> None:
    path = run_dir / "results_partial.json"
    payload = read_json(path, {"schema_version": 1, "run_id": run_id, "warm": {}, "cold_full_catalog": {}})
    payload.setdefault("cold_full_catalog", {}).update(results)
    write_json(path, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--datasets", required=True)
    parser.add_argument("--seeds", default=CONFIRMATORY_SEEDS_CSV)
    parser.add_argument("--config", default=str(LAB_DIR / "publication_candidate_mask_seen_v2.json"))
    parser.add_argument("--candidate-only", action="store_true", default=True)
    parser.add_argument("--include-local-baselines", action="store_true", help="Write local/proxy baselines too; candidate-only remains the default.")
    parser.add_argument("--fold-ids", default="", help="Optional comma-separated fold IDs to run for every selected seed.")
    parser.add_argument("--max-new-folds", type=int, default=0, help="Stop after this many newly computed seed/folds; 0 means no limit.")
    parser.add_argument("--no-resume", action="store_true", help="Delete and recompute selected dataset record files.")
    parser.add_argument("--finalize-bootstrap-reps", type=int, default=200)
    parser.add_argument("--allow-failure-report", action="store_true", default=True)
    args = parser.parse_args()

    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    fold_ids = set(parse_csv(args.fold_ids, int)) if args.fold_ids else None
    unknown = [x for x in datasets if x not in DATASETS]
    if unknown:
        raise ValueError(f"unknown datasets: {unknown}")
    ltr_config, config_meta = load_ltr_config(args.config)
    validate_config(config_meta, seeds)
    run_dir = RUNS_DIR / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    candidate_only = bool(args.candidate_only and not args.include_local_baselines)
    ensure_run_config(run_dir, args.run_id, seeds, config_meta, candidate_only)

    results: dict[str, Any] = {}
    for dataset in datasets:
        results[dataset] = run_cold_ltr_dataset(
            dataset=dataset,
            seeds=seeds,
            run_dir=run_dir,
            ltr_config=ltr_config,
            stage="confirmatory",
            include_deep=True,
            deep_epochs_scale=1.0,
            max_folds=0,
            resume=not args.no_resume,
            eval_methods=["lc2c_retrieval_ltr"] if candidate_only else None,
            fold_ids=fold_ids,
            max_new_folds=max(0, int(args.max_new_folds)),
        )
        merge_partial(run_dir, args.run_id, {dataset: results[dataset]})

    finalize_cmd = [
        sys.executable,
        str(LAB_DIR / "finalize.py"),
        "--run-id",
        args.run_id,
        "--bootstrap-reps",
        str(args.finalize_bootstrap_reps),
    ]
    res = subprocess.run(finalize_cmd, check=False)
    print(f"Confirmatory chunk run: {run_dir}")
    if res.returncode and not args.allow_failure_report:
        return res.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
