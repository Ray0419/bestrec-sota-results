"""Check whether frozen sparse-RRF confirmatory inputs are present.

This script does not run models. It materializes the exact artifact inventory
needed before `run_sparse_rrf_full_catalog_replay.py` can be used as
confirmatory evidence for the frozen Video_Games sparse-RRF candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from protocol import load_protocol


ROOT = Path(__file__).resolve().parent.parent
LAB_DIR = ROOT / "_bestrec_sota_lab"
DEFAULT_MANIFEST = LAB_DIR / "frozen_candidates" / "video_games_multi_rrf_candidate_20260609.json"
DEFAULT_CONFIRMATORY_PROTOCOL = LAB_DIR / "frozen_candidates" / "video_games_sparse_rrf_confirmatory_protocol_20260609.json"
DEFAULT_OUT = LAB_DIR / "frozen_candidates" / "video_games_sparse_rrf_confirmatory_input_check.json"
DEFAULT_SEQUENCE_CSV = LAB_DIR / "runs" / "hstu_strict_protocol_data_20260609" / "sasrec_format_test_strict.csv"
DEFAULT_ITEM_MAP = LAB_DIR / "runs" / "hstu_item_alignment_20260609" / "hstu_bestrec_item_map.json"
DEFAULT_USER_MAP = LAB_DIR / "runs" / "hstu_user_alignment_20260609" / "hstu_bestrec_user_map.json"


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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_component_path(seed: int, component: str, split: str) -> tuple[Path, str]:
    if component == "sasrec":
        return (
            LAB_DIR
            / "runs"
            / f"video_games_confirmatory_seed{seed}_sasrec_export_{split}"
            / f"warm_full_catalog_records_Video_Games_sasrec_sbert_{split}.jsonl",
            "top_ids",
        )
    return (
        LAB_DIR
        / "runs"
        / f"video_games_confirmatory_seed{seed}_{component}_export_{split}"
        / f"warm_full_catalog_records_Video_Games_strict_hstu_{split}.jsonl",
        "teacher_top_ids",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--confirmatory-protocol", default=str(DEFAULT_CONFIRMATORY_PROTOCOL))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--seeds", default=None, help="Comma-separated override. Defaults to protocol fresh_confirmatory_seeds.")
    parser.add_argument("--split", choices=("valid", "test"), default="test")
    args = parser.parse_args()

    protocol_path = Path(args.confirmatory_protocol)
    protocol = read_json(protocol_path) if protocol_path.exists() else load_protocol()
    seeds = (
        [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
        if args.seeds
        else [int(value) for value in protocol.get("fresh_confirmatory_seeds", [])]
    )
    manifest_path = Path(args.manifest)
    manifest = read_json(manifest_path)
    weights = manifest.get("fusion_config", {}).get("weights", {})
    components = list(weights)
    component_generators = manifest.get("component_generators", {})

    missing: list[str] = []
    present: list[str] = []
    seed_blocks: dict[str, Any] = {}
    for seed in seeds:
        component_blocks = {}
        for component in components:
            path, ids_key = expected_component_path(seed, component, args.split)
            file_record = sha256_file(path)
            block = {
                "component": component,
                "generator_label": component_generators.get(component),
                "ids_key": ids_key,
                "path": str(path),
                "file": file_record,
            }
            component_blocks[component] = block
            if path.exists():
                present.append(str(path))
            else:
                missing.append(str(path))
        seed_blocks[str(seed)] = component_blocks

    static_inputs = {
        "manifest": sha256_file(manifest_path),
        "sequence_csv": sha256_file(DEFAULT_SEQUENCE_CSV),
        "item_map": sha256_file(DEFAULT_ITEM_MAP),
        "user_map": sha256_file(DEFAULT_USER_MAP),
    }
    static_missing = [name for name, record in static_inputs.items() if not record["exists"]]
    status = "ready" if not missing and not static_missing else "missing_inputs"
    replay_commands = []
    for seed in seeds:
        parts = [
            "uv --project _bestrec_run run python _bestrec_sota_lab/run_sparse_rrf_full_catalog_replay.py",
            f"--manifest {manifest_path}",
        ]
        for component in components:
            path, ids_key = expected_component_path(seed, component, args.split)
            parts.append(f"--input {component} {path} {ids_key}")
        parts.extend(
            [
                f"--sequence-csv {DEFAULT_SEQUENCE_CSV}",
                f"--out-dir _bestrec_sota_lab/runs/video_games_sparse_rrf_full_catalog_confirmatory_seed{seed}",
                "--dataset Video_Games",
                f"--seed {seed}",
                "--fold-id 0",
                f"--split {args.split}",
                "--evidence-stage confirmatory",
                "--evidence-scope video_games_sparse_rrf_five_seed_replay",
                f"--protocol-manifest {protocol_path}",
                "--claim-scope local_video_games_component_comparator_evidence_only",
            ]
        )
        replay_commands.append(" ".join(str(part) for part in parts))

    report = {
        "schema_version": 1,
        "status": status,
        "evidence_stage": "confirmatory_inventory",
        "evidence_scope": "video_games_sparse_rrf_confirmatory_inputs",
        "claim_scope": "local_video_games_component_comparator_evidence_only",
        "publication_grade": False,
        "reason": "Inventory check only; no confirmatory result is produced by this script.",
        "protocol_id": protocol.get("protocol_id"),
        "confirmatory_protocol": str(protocol_path) if protocol_path.exists() else "global_cold_sota_strict_v2",
        "retired_seed_sets": protocol.get("retired_seed_sets", []),
        "fresh_confirmatory_seeds": seeds,
        "split": args.split,
        "frozen_manifest": str(manifest_path),
        "components": components,
        "seed_component_inputs": seed_blocks,
        "static_inputs": static_inputs,
        "missing_component_files": missing,
        "missing_static_inputs": static_missing,
        "present_component_files": present,
        "ready_to_replay_confirmatory": status == "ready",
        "replay_commands_after_inputs_exist": replay_commands,
        "required_training_note": (
            "Each missing HSTU component must be regenerated from the frozen generator label on the listed fresh seed; "
            "the SASRec component must likewise be regenerated/exported on the same fresh seed before replay."
        ),
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": status, "missing_component_files": len(missing), "out": str(out_path)}, indent=2))
    return 0 if status == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
