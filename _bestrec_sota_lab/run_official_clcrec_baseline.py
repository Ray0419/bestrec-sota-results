"""Run faithful CLCRec read-only from `_bestrec_run` into the SOTA lab.

This wrapper avoids writing the legacy runner's default `_bestrec_run`
artifacts. It calls the existing faithful CLCRec implementation and stores
records under `_bestrec_sota_lab/runs/<run_id>/`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sota_common import BESTREC_RUN_DIR, CONFIRMATORY_SEEDS_CSV, DATASETS, make_lab_run_dir, parse_csv, write_json

sys.path.insert(0, str(BESTREC_RUN_DIR))
from run_faithful_clcrec import run as run_clcrec  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--seeds", default=CONFIRMATORY_SEEDS_CSV)
    parser.add_argument("--sweep-hp", action="store_true", help="Run the expensive inner HP sweep instead of fixed defaults.")
    args = parser.parse_args()

    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    run_id, run_dir = make_lab_run_dir("official_clcrec", args.run_id)
    audit = {
        "schema_version": 1,
        "run_id": run_id,
        "method": "faithful_clcrec",
        "target_import_method": "official_clcrec",
        "datasets": {},
        "seeds": seeds,
        "sweep_hp": bool(args.sweep_hp),
        "notes": (
            "Faithful CLCRec implementation from _bestrec_run/run_faithful_clcrec.py "
            "imported read-only. Records are written in the lab and should be "
            "renamed to official_clcrec via import_official_records.py. "
            "When sweep_hp=false, the runner uses its documented fixed modal "
            "hyperparameters instead of the expensive per-fold sweep."
        ),
    }

    for dataset in datasets:
        if dataset not in DATASETS:
            raise ValueError(f"unknown dataset: {dataset}")
        record_path = run_dir / f"official_clcrec_source_records_{dataset}.jsonl"
        summary = run_clcrec(dataset, seeds, record_path, sweep_hp=bool(args.sweep_hp))
        audit["datasets"][dataset] = {
            "record_file": record_path.name,
            "mean_ndcg10": summary.get("mean_ndcg10"),
            "std_ndcg10": summary.get("std_ndcg10"),
            "selected_hps": summary.get("selected_hps", []),
            "bpr_losses": summary.get("bpr_losses", []),
        }
        write_json(run_dir / "official_clcrec_source_audit.json", audit)

    (run_dir / "official_clcrec_source_summary.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Official CLCRec source run: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
