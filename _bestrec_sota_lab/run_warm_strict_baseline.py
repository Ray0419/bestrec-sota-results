"""Run strict warm-LOO baselines read-only from `_bestrec_run` into the lab."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sota_common import BESTREC_RUN_DIR, CONFIRMATORY_SEEDS_CSV, DATASETS, make_lab_run_dir, parse_csv, write_json

sys.path.insert(0, str(BESTREC_RUN_DIR))


def _load_runner(method: str):
    if method == "ials":
        from run_ials_strict import run_dataset

        return run_dataset, {
            "max_iters_search": 20,
            "max_iters_final": 40,
            "patience_search": 4,
            "patience_final": 6,
        }
    if method == "lightgcn":
        from run_lightgcn_strict import run_dataset

        return run_dataset, {
            "max_epochs_search": 80,
            "max_epochs_final": 200,
            "patience_search": 10,
            "patience_final": 15,
            "batch_size": 4096,
        }
    if method == "multivae":
        from run_multivae_strict import run_dataset

        return run_dataset, {
            "max_epochs_search": 80,
            "max_epochs_final": 200,
            "patience_search": 10,
            "patience_final": 15,
            "batch_size": 256,
            "sweep_eval_user_cap": 0,
        }
    raise ValueError(f"unknown method: {method}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", choices=["ials", "lightgcn", "multivae"])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--seeds", default=CONFIRMATORY_SEEDS_CSV)
    parser.add_argument("--quick", action="store_true", help="Smoke-test settings; not publication-grade.")
    args = parser.parse_args()

    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    run_id, run_dir = make_lab_run_dir(f"official_{args.method}", args.run_id)
    run_dataset, defaults = _load_runner(args.method)
    if args.quick:
        if args.method == "ials":
            defaults.update({"max_iters_search": 2, "max_iters_final": 2, "patience_search": 1, "patience_final": 1})
        elif args.method == "lightgcn":
            defaults.update({"max_epochs_search": 2, "max_epochs_final": 2, "patience_search": 1, "patience_final": 1})
        elif args.method == "multivae":
            defaults.update({"max_epochs_search": 2, "max_epochs_final": 2, "patience_search": 1, "patience_final": 1, "sweep_eval_user_cap": 100})

    audit = {
        "schema_version": 1,
        "run_id": run_id,
        "method": args.method,
        "seeds": seeds,
        "datasets": {},
        "status": "proxy_smoke" if args.quick else "complete",
        "notes": "Strict warm-LOO baseline imported read-only from _bestrec_run and written under the SOTA lab.",
        "config": defaults,
    }
    for dataset in datasets:
        if dataset not in DATASETS:
            raise ValueError(f"unknown dataset: {dataset}")
        result = run_dataset(dataset, seeds, str(run_dir), **defaults)
        audit["datasets"][dataset] = result
        write_json(run_dir / f"{args.method}_audit.json", audit)
    write_json(run_dir / f"{args.method}_audit.json", audit)
    print(f"Warm baseline {args.method}: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
