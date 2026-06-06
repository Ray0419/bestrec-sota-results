"""Audit rebuild/readiness evidence for an isolated SOTA-lab run.

The default mode is intentionally non-destructive: it checks that the current
artifacts are internally consistent and that manifest output hashes match the
files on disk.

With `--record-level-rebuild`, the script hard-links canonical JSONL records and
evidence audits into a scratch run directory, deletes derived outputs there,
reruns `finalize.py`, and compares regenerated summaries/tables/significance
against the reviewed run. This proves the paper-facing artifacts are
rebuildable from records, but it still does not rerun model training/scoring.

A publication package still needs `strict_clean_rebuild_passed=true`, which this
script will not set unless the full model/scoring pipeline is rerun from
documented commands and record generation is verified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from sota_common import DATASETS, LAB_DIR, RUNS_DIR, utc_now, write_json


DEFAULT_RUN_ID = "confirmatory_masked_candidate_20260701_20260705_candidate_only"

REQUIRED = [
    "run_config.json",
    "results_final.json",
    "significance.json",
    "baseline_audit.json",
    "publication_gate.json",
    "tables.json",
    "results_manifest.json",
]

DERIVED_OUTPUTS = {
    "baseline_audit.json",
    "publication_gate.json",
    "results_final.json",
    "results_manifest.json",
    "significance.json",
    "tables.json",
    "INTERNAL_SOTA_FAILURE_REPORT.md",
    "SOTA_PASS_REPORT.md",
}

REBUILD_INPUT_NAMES = {
    "run_config.json",
    "baseline_run_config_official_dropoutnet_fixed.json",
    "lc2c_v2_audit.json",
    "official_blair_audit.json",
    "official_clcrec_audit.json",
    "official_dropoutnet_audit.json",
    "official_dropoutnet_fixed_audit.json",
    "official_melt_audit.json",
    "official_melt_same_split_audit.json",
    "tiger_liger_retrieval_audit.json",
    "tiger_liger_retrieval_import_audit.json",
}

SEMANTIC_OUTPUTS = [
    "results_final.json",
    "significance.json",
    "baseline_audit.json",
    "publication_gate.json",
    "tables.json",
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_remove_run_dir(path: Path) -> None:
    resolved = path.resolve()
    runs_root = RUNS_DIR.resolve()
    if resolved == runs_root or runs_root not in resolved.parents:
        raise ValueError(f"Refusing to remove non-run scratch directory: {path}")
    if path.exists():
        shutil.rmtree(path)


def link_or_copy(src: Path, dst: Path) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
        return "hardlink"
    except OSError:
        shutil.copy2(src, dst)
        return "copy"


def rebuild_input_files(run_dir: Path) -> list[Path]:
    out: list[Path] = []
    for name in REBUILD_INPUT_NAMES:
        path = run_dir / name
        if path.exists():
            out.append(path)
    for dataset in DATASETS:
        for prefix in ("cold_full_catalog_records", "warm_records"):
            path = run_dir / f"{prefix}_{dataset}.jsonl"
            if path.exists():
                out.append(path)
    return sorted(out, key=lambda p: p.name)


def normalize_semantic(value: Any) -> Any:
    volatile_keys = {
        "checked_at_utc",
        "generated_utc",
        "timestamp_utc",
        "updated_utc",
    }
    if isinstance(value, dict):
        return {k: normalize_semantic(v) for k, v in sorted(value.items()) if k not in volatile_keys and k != "run_id"}
    if isinstance(value, list):
        return [normalize_semantic(v) for v in value]
    return value


def compare_semantic_outputs(original_dir: Path, rebuilt_dir: Path) -> dict[str, Any]:
    comparisons = []
    for name in SEMANTIC_OUTPUTS:
        original_path = original_dir / name
        rebuilt_path = rebuilt_dir / name
        if not original_path.exists() or not rebuilt_path.exists():
            comparisons.append(
                {
                    "name": name,
                    "passed": False,
                    "problem": "missing",
                    "original_exists": original_path.exists(),
                    "rebuilt_exists": rebuilt_path.exists(),
                }
            )
            continue
        original = normalize_semantic(read_json(original_path))
        rebuilt = normalize_semantic(read_json(rebuilt_path))
        comparisons.append({"name": name, "passed": original == rebuilt})
    return {
        "name": "semantic_outputs_match",
        "passed": all(row["passed"] for row in comparisons),
        "comparisons": comparisons,
    }


def check_required(run_dir: Path) -> dict[str, Any]:
    missing = [name for name in REQUIRED if not (run_dir / name).exists()]
    for dataset in DATASETS:
        name = f"cold_full_catalog_records_{dataset}.jsonl"
        if not (run_dir / name).exists():
            missing.append(name)
    return {"name": "required_artifacts_present", "passed": not missing, "missing": missing}


def check_gate_table_consistency(run_dir: Path) -> dict[str, Any]:
    gate = read_json(run_dir / "publication_gate.json")
    tables = read_json(run_dir / "tables.json")
    passed = bool(gate.get("passed")) == bool(tables.get("sota_claim_allowed"))
    return {
        "name": "gate_matches_tables",
        "passed": passed,
        "gate_passed": gate.get("passed"),
        "tables_sota_claim_allowed": tables.get("sota_claim_allowed"),
    }


def check_proxy_table_columns(run_dir: Path) -> dict[str, Any]:
    protocol = read_json(LAB_DIR / "protocols" / "cold_sota_strict_v2.json")
    proxies = set(protocol.get("proxy_methods_disallowed_for_publication", []))
    tables = read_json(run_dir / "tables.json")
    columns = set(tables.get("table_cold_full_catalog", {}).get("columns", []))
    leaked = sorted(proxies & columns)
    return {"name": "no_proxy_methods_in_paper_table", "passed": not leaked, "leaked_proxy_methods": leaked}


def check_manifest_outputs(run_dir: Path) -> dict[str, Any]:
    manifest = read_json(run_dir / "results_manifest.json")
    outputs = manifest.get("latest_run", {}).get("output_hashes", {})
    mismatches = []
    for raw_path, expected in outputs.items():
        path = Path(raw_path)
        if not path.is_absolute():
            path = LAB_DIR.parent / raw_path
        if not path.exists():
            mismatches.append({"path": raw_path, "problem": "missing"})
            continue
        actual = sha256_file(path)
        if actual != expected:
            mismatches.append({"path": raw_path, "problem": "hash_mismatch", "expected": expected, "actual": actual})
    return {
        "name": "manifest_output_hashes_match",
        "passed": not mismatches and bool(outputs),
        "checked_outputs": len(outputs),
        "mismatches": mismatches,
    }


def check_table_significance(run_dir: Path) -> dict[str, Any]:
    tables = read_json(run_dir / "tables.json")
    sig = read_json(run_dir / "significance.json")
    rows = tables.get("table_significance", {}).get("rows", [])
    failures = []
    for row in rows:
        dataset_label = row[0]
        dataset = dataset_label.lower()
        if dataset == "beauty":
            key = "beauty"
        elif dataset == "fashion":
            key = "fashion"
        elif dataset == "instruments":
            key = "instruments"
        elif dataset == "books":
            key = "books"
        else:
            failures.append({"row": row, "problem": "unknown_dataset_label"})
            continue
        block = sig.get("cold_full_catalog", {}).get(key, {})
        if row[1] != block.get("best_baseline"):
            failures.append({"dataset": key, "problem": "best_baseline_mismatch", "table": row[1], "significance": block.get("best_baseline")})
    return {"name": "table_significance_matches_significance_json", "passed": not failures, "failures": failures}


def run_record_level_rebuild(run_id: str, bootstrap_reps: int) -> dict[str, Any]:
    original_dir = RUNS_DIR / run_id
    rebuild_id = f"{run_id}__record_rebuild"
    rebuild_dir = RUNS_DIR / rebuild_id
    safe_remove_run_dir(rebuild_dir)
    rebuild_dir.mkdir(parents=True, exist_ok=True)
    linked = []
    for src in rebuild_input_files(original_dir):
        mode = link_or_copy(src, rebuild_dir / src.name)
        linked.append({"name": src.name, "mode": mode, "sha256": sha256_file(src), "bytes": src.stat().st_size})
    for name in DERIVED_OUTPUTS:
        path = rebuild_dir / name
        if path.exists():
            path.unlink()
    proc = subprocess.run(
        [
            sys.executable,
            str(LAB_DIR / "finalize.py"),
            "--run-id",
            rebuild_id,
            "--bootstrap-reps",
            str(bootstrap_reps),
        ],
        cwd=LAB_DIR.parent,
        check=False,
        capture_output=True,
        text=True,
    )
    checks = [
        check_required(rebuild_dir),
        check_gate_table_consistency(rebuild_dir),
        check_proxy_table_columns(rebuild_dir),
        check_manifest_outputs(rebuild_dir),
        check_table_significance(rebuild_dir),
        compare_semantic_outputs(original_dir, rebuild_dir),
    ]
    passed = proc.returncode == 0 and all(check["passed"] for check in checks)
    payload = {
        "name": "record_level_clean_rebuild",
        "passed": bool(passed),
        "run_id": rebuild_id,
        "rebuild_dir": str(rebuild_dir),
        "bootstrap_reps": bootstrap_reps,
        "input_files": linked,
        "input_file_count": len(linked),
        "finalize_returncode": proc.returncode,
        "finalize_stdout_tail": proc.stdout.splitlines()[-20:],
        "finalize_stderr_tail": proc.stderr.splitlines()[-20:],
        "checks": checks,
        "scope": "Regenerates derived summaries/tables/significance/manifest from canonical JSONL records and audit evidence. It does not rerun model training or record generation.",
    }
    return payload


def run_full_rebuild_compare(
    *,
    run_id: str,
    full_rebuild_run_id: str,
    metric_tolerance: float,
    require_record_hash_match: bool,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(LAB_DIR / "validate_full_clean_rebuild.py"),
        "--canonical-run-id",
        run_id,
        "--run-id",
        full_rebuild_run_id,
        "--metric-tolerance",
        str(metric_tolerance),
    ]
    if require_record_hash_match:
        cmd.append("--require-record-hash-match")
    proc = subprocess.run(cmd, cwd=LAB_DIR.parent, check=False, capture_output=True, text=True)
    compare_path = RUNS_DIR / full_rebuild_run_id / "full_clean_rebuild_compare.json"
    compare_payload = read_json(compare_path) if compare_path.exists() else {}
    return {
        "name": "full_experiment_clean_rebuild",
        "passed": proc.returncode == 0 and bool(compare_payload.get("passed")),
        "canonical_run_id": run_id,
        "full_rebuild_run_id": full_rebuild_run_id,
        "command": cmd,
        "returncode": int(proc.returncode),
        "stdout_tail": proc.stdout.splitlines()[-30:],
        "stderr_tail": proc.stderr.splitlines()[-30:],
        "compare_file": str(compare_path),
        "compare": compare_payload,
        "scope": "Requires an independently generated run with model training/scoring and JSONL record generation already completed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--out", default=str(LAB_DIR / "clean_rebuild_audit.json"))
    parser.add_argument("--record-level-rebuild", action="store_true", help="Rebuild derived artifacts from JSONL records in a scratch run directory.")
    parser.add_argument("--bootstrap-reps", type=int, default=2000)
    parser.add_argument("--full-rebuild-run-id", default="", help="Independent full rebuild run id to compare against this canonical run.")
    parser.add_argument("--metric-tolerance", type=float, default=1e-9)
    parser.add_argument("--require-record-hash-match", action="store_true")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_id
    checks = [
        check_required(run_dir),
        check_gate_table_consistency(run_dir),
        check_proxy_table_columns(run_dir),
        check_manifest_outputs(run_dir),
        check_table_significance(run_dir),
    ]
    consistency_passed = all(check["passed"] for check in checks)
    record_rebuild = run_record_level_rebuild(args.run_id, args.bootstrap_reps) if args.record_level_rebuild else None
    record_rebuild_passed = bool(record_rebuild and record_rebuild.get("passed"))
    full_rebuild = (
        run_full_rebuild_compare(
            run_id=args.run_id,
            full_rebuild_run_id=args.full_rebuild_run_id,
            metric_tolerance=float(args.metric_tolerance),
            require_record_hash_match=bool(args.require_record_hash_match),
        )
        if args.full_rebuild_run_id
        else None
    )
    full_rebuild_passed = bool(full_rebuild and full_rebuild.get("passed"))
    strict_clean_rebuild_passed = bool(full_rebuild_passed)
    payload = {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "run_id": args.run_id,
        "mode": (
            "full_experiment_rebuild"
            if args.full_rebuild_run_id
            else "record_level_rebuild"
            if args.record_level_rebuild
            else "current_artifact_consistency_only"
        ),
        "consistency_passed": bool(consistency_passed),
        "record_level_clean_rebuild_passed": bool(record_rebuild_passed),
        "strict_clean_rebuild_passed": strict_clean_rebuild_passed,
        "passed": bool(consistency_passed and strict_clean_rebuild_passed),
        "checks": checks,
        "record_level_rebuild": record_rebuild,
        "full_experiment_rebuild": full_rebuild,
        "notes": [
            "This audit does not rerun model training or regenerate JSONL records.",
            "The record-level mode verifies that derived paper-facing artifacts can be regenerated from canonical records.",
            "Strict full clean-rebuild approval requires a separate full rebuild run and successful comparison.",
        ],
    }
    write_json(Path(args.out), payload)
    print(f"Wrote {args.out}")
    print(f"Consistency: {'PASSED' if consistency_passed else 'FAILED'}")
    if args.record_level_rebuild:
        print(f"Record-level rebuild: {'PASSED' if record_rebuild_passed else 'FAILED'}")
    if args.full_rebuild_run_id:
        print(f"Strict full experiment clean rebuild: {'PASSED' if full_rebuild_passed else 'FAILED'}")
    else:
        print("Strict full experiment clean rebuild: NOT RUN")
    expected_ok = consistency_passed and (not args.record_level_rebuild or record_rebuild_passed)
    if args.full_rebuild_run_id:
        expected_ok = expected_ok and full_rebuild_passed
    return 0 if expected_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
