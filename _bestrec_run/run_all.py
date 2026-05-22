"""Canonical BEST-Rec pipeline entrypoint.

Documented full command:

    uv run python _bestrec_run/run_all.py --profile full \
      --datasets beauty,fashion,instruments,books --seeds 42,43,44,45,46

The script records every stage in results_manifest.json and refuses to use the
retired notebook or cache/*/v5_results.json as paper sources.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from artifact_utils import DATASETS, ROOT, RUN_DIR, append_manifest_run, read_json, write_json


FIGURE_NAMES = [
    "fig1_warm_methods_x_datasets.png",
    "fig2_vs_lightgcn.png",
    "fig3_ablation_embeddings.png",
    "fig6_hp_sensitivity_combined.png",
    "fig7_cold_item_v2.png",
    "fig8_lc2c_ablation.png",
    "fig9_lc2c_latentdim.png",
]


def parse_csv(value: str, defaults: tuple[str, ...] = DATASETS) -> list[str]:
    if not value:
        return list(defaults)
    return [x.strip() for x in value.split(",") if x.strip()]


def run_stage(cmd: list[str], cwd: Path = ROOT) -> None:
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def copy_figures() -> None:
    dst = ROOT / "figures"
    dst.mkdir(exist_ok=True)
    src = RUN_DIR / "figures"
    for name in FIGURE_NAMES:
        if (src / name).exists():
            shutil.copy2(src / name, dst / name)


def write_sota_audit_stub(seeds: list[str]) -> None:
    path = RUN_DIR / "results_sota_audit.json"
    payload = read_json(path, default={
        "schema_version": 1,
        "baselines": {},
        "win_condition": {
            "status": "not_evaluated",
            "notes": "LC2C++ variants have not yet passed the full-catalog cold-item SOTA protocol.",
        },
    })
    defaults = {
        "faithful_dropoutnet": {
                "status": "not_run",
                "seeds": seeds,
                "notes": "Required WMF-backed multi-seed/grid-tuned DropoutNet has not been generated.",
            },
        "clcrec_melt": {
                "status": "not_run",
                "seeds": seeds,
                "notes": "CLCRec/MELT-style cold-start comparator has not been generated.",
            },
        "blair_text": {
                "status": "not_run",
                "seeds": seeds,
                "notes": "BLaIR-style text retrieval comparator has not been generated.",
            },
        "lightgcn": {
                "status": "legacy_partial",
                "seeds": seeds,
                "notes": "Legacy canonical-setting LightGCN numbers exist, but the repaired tuned multi-seed audit is missing.",
            },
        "multivae": {
                "status": "legacy_partial",
                "seeds": seeds,
                "notes": "Legacy canonical-setting MultiVAE numbers exist, but the repaired tuned multi-seed audit is missing.",
            },
        "ials": {
                "status": "legacy_partial",
                "seeds": seeds,
                "notes": "Legacy iALS is incomplete/OOM on Books; sparse tuned iALS is missing.",
            },
    }
    payload.setdefault("baselines", {})
    for name, entry in defaults.items():
        if name not in payload["baselines"] or payload["baselines"][name].get("status") != "complete":
            payload["baselines"][name] = entry
    write_json(path, payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["audit", "full"], default="audit")
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--seeds", default="42")
    parser.add_argument("--skip-warm", action="store_true")
    parser.add_argument("--skip-cold", action="store_true")
    parser.add_argument("--skip-paper", action="store_true")
    parser.add_argument("--allow-internal-report", action="store_true")
    args = parser.parse_args()

    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, defaults=("42",))
    py_cmd = ["uv", "--project", str(RUN_DIR), "run", "python"]

    if args.profile == "full":
        write_sota_audit_stub(seeds)

    if not args.skip_warm:
        cmd = [*py_cmd, str(RUN_DIR / "run_warm_loo.py"), *datasets]
        if args.profile == "full":
            cmd += ["--seeds", ",".join(seeds), "--max-users", "0"]
        run_stage(cmd)

    if not args.skip_cold:
        run_stage([*py_cmd, str(RUN_DIR / "run_cold_item_v2.py"), *datasets])

    run_stage([*py_cmd, str(RUN_DIR / "compute_significance.py")])
    run_stage([*py_cmd, str(RUN_DIR / "consolidate_final.py")])
    run_stage([*py_cmd, str(RUN_DIR / "build_tables.py")])
    run_stage([*py_cmd, str(RUN_DIR / "make_figures.py")])
    copy_figures()

    outputs = [
        RUN_DIR / "results_FINAL.json",
        RUN_DIR / "significance.json",
        RUN_DIR / "tables.json",
        RUN_DIR / "results_manifest.json",
        *(ROOT / "figures" / name for name in FIGURE_NAMES if (ROOT / "figures" / name).exists()),
    ]
    if not args.skip_paper:
        run_stage([*py_cmd, str(ROOT / "_paper_gen" / "build_paper_full.py")])
        outputs.append(ROOT / "BEST_Rec_v4_Full_Paper.pdf")

    validate_cmd = [*py_cmd, str(RUN_DIR / "validate_artifacts.py")]
    if args.allow_internal_report:
        validate_cmd.append("--allow-internal-report")
    run_stage(validate_cmd)

    append_manifest_run(
        command=["uv", "--project", str(RUN_DIR), "run", "python", str(Path(__file__).name), "--profile", args.profile, "--datasets", ",".join(datasets), "--seeds", ",".join(seeds)],
        inputs=[
            RUN_DIR / "results_warm_loo.json",
            RUN_DIR / "results_cold_item_v2.json",
            RUN_DIR / "significance_corrected.json",
            RUN_DIR / "significance_cold_item_corrected.json",
            RUN_DIR / "significance_cold_item_bootstrap.json",
        ],
        outputs=outputs,
        datasets=datasets,
        seeds=seeds,
        note=f"Canonical run_all profile={args.profile}; sota_claim_allowed={read_json(RUN_DIR / 'tables.json').get('sota_claim_allowed')}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
