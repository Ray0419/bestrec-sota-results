#!/usr/bin/env python3
"""Fail-closed driver for the frozen WEARec current-baseline campaign."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import wearec_baseline_v1_common as common


PYTHON = Path(sys.executable)
HERE = Path(__file__).resolve().parent
RUNNER = HERE / "run_wearec_baseline_v1.py"
EVALUATOR = HERE / "eval_wearec_baseline_v1.py"
STRUCTURAL_TEST = HERE / "test_wearec_baseline_v1.py"
ACQUIRE = HERE / "acquire_wearec_baseline_v1.py"
STATUS = HERE / "wearec_baseline_v1_status.json"
SELECTION = HERE / "wearec_baseline_v1_selection.json"


def status(state: str, *, tuning: int, trained: int, evaluated: int, started: float, detail: str = "") -> None:
    common.atomic_json(
        STATUS,
        {
            "protocol": common.PROTOCOL,
            "state": state,
            "tuning_complete": tuning,
            "assessment_trained": trained,
            "assessment_evaluated": evaluated,
            "assessment_total": len(common.ASSESSMENT_SEEDS),
            "elapsed_min": round((time.perf_counter() - started) / 60.0, 1),
            "detail": detail,
        },
    )


def run(command: list[str]) -> None:
    child = subprocess.run(command, cwd=common.ROOT)
    if child.returncode:
        raise RuntimeError(f"child failed rc={child.returncode}: {' '.join(command)}")


def load_training(phase: str, preset: str, seed: int) -> dict:
    path = common.train_output(phase, preset, seed)
    with path.open("r", encoding="utf-8") as handle:
        obj = json.load(handle)
    if (
        obj.get("protocol") != common.PROTOCOL
        or obj.get("state") != "training_complete_test_unread"
        or obj.get("test_read_or_scored") is not False
        or obj.get("config", {}).get("preset") != preset
        or obj.get("config", {}).get("seed") != seed
    ):
        raise RuntimeError(f"invalid training artifact: {path}")
    return obj


def preflight() -> None:
    run([str(PYTHON), str(ACQUIRE)])
    run([str(PYTHON), str(STRUCTURAL_TEST)])
    if not common.CATALOG_MANIFEST.is_file() or not common.CATALOG.is_file():
        raise RuntimeError("prefreeze catalog/manifest missing")
    if SELECTION.exists() or STATUS.exists():
        raise RuntimeError("campaign selection/status already exists")
    for preset in common.PRESET_ORDER:
        for path in (
            common.train_output("tune", preset, common.TUNE_SEED),
            common.checkpoint_path("tune", preset, common.TUNE_SEED),
        ):
            if path.exists() or path.with_suffix(".started.json").exists():
                raise RuntimeError(f"prefight found prior tuning attempt: {path}")
    for seed in common.ASSESSMENT_SEEDS:
        for preset in common.PRESET_ORDER:
            paths = (
                common.train_output("assessment", preset, seed),
                common.checkpoint_path("assessment", preset, seed),
                common.endpoint_path(preset, seed),
                common.endpoint_users_path(preset, seed),
                common.endpoint_seal_path(preset, seed),
            )
            if any(path.exists() for path in paths):
                raise RuntimeError(f"preflight found prior assessment attempt for {preset}/{seed}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()
    preflight()
    if args.preflight_only:
        print(f"{common.PROTOCOL} PREFLIGHT: PASS")
        return 0
    tuning = trained = evaluated = 0
    status("tuning", tuning=tuning, trained=trained, evaluated=evaluated, started=started)
    tune_values: dict[str, float] = {}
    for preset in common.PRESET_ORDER:
        run(
            [
                str(PYTHON),
                str(RUNNER),
                "--phase", "tune",
                "--preset", preset,
                "--seed", str(common.TUNE_SEED),
            ]
        )
        tune_values[preset] = float(
            load_training("tune", preset, common.TUNE_SEED)["best_valid"]["NDCG@10"]
        )
        tuning += 1
        status("tuning", tuning=tuning, trained=trained, evaluated=evaluated, started=started)
    selected = max(common.PRESET_ORDER, key=lambda name: (tune_values[name], -common.PRESET_ORDER.index(name)))
    common.atomic_json(
        SELECTION,
        {
            "protocol": common.PROTOCOL,
            "selection_endpoint": "maximum shared-evaluator VALID NDCG@10",
            "tuning_seed": common.TUNE_SEED,
            "preset_order_for_exact_ties": list(common.PRESET_ORDER),
            "validation_ndcg10": tune_values,
            "selected_preset": selected,
            "test_read_or_scored": False,
        },
    )
    status("training", tuning=tuning, trained=trained, evaluated=evaluated, started=started, detail=selected)
    for seed in common.ASSESSMENT_SEEDS:
        run(
            [
                str(PYTHON),
                str(RUNNER),
                "--phase", "assessment",
                "--preset", selected,
                "--seed", str(seed),
            ]
        )
        load_training("assessment", selected, seed)
        trained += 1
        status("training", tuning=tuning, trained=trained, evaluated=evaluated, started=started, detail=selected)

    # Hard barrier: every immutable assessment checkpoint exists before TEST begins.
    for seed in common.ASSESSMENT_SEEDS:
        load_training("assessment", selected, seed)
        checkpoint = common.checkpoint_path("assessment", selected, seed)
        if not checkpoint.is_file():
            raise RuntimeError(f"assessment checkpoint missing at TEST barrier: {checkpoint}")
    status("evaluating", tuning=tuning, trained=trained, evaluated=evaluated, started=started, detail=selected)
    for seed in common.ASSESSMENT_SEEDS:
        run(
            [
                str(PYTHON),
                str(EVALUATOR),
                "--preset", selected,
                "--seed", str(seed),
            ]
        )
        evaluated += 1
        status("evaluating", tuning=tuning, trained=trained, evaluated=evaluated, started=started, detail=selected)
    status("complete", tuning=tuning, trained=trained, evaluated=evaluated, started=started, detail=selected)
    print(
        f"{common.PROTOCOL} COMPLETE: tuning={tuning}/2 assessment={trained}/8 sealed_eval={evaluated}/8; "
        "run committed adjudicator before reading endpoints",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        try:
            status("failed", tuning=0, trained=0, evaluated=0, started=time.perf_counter(), detail=str(exc))
        except Exception:
            pass
        raise
