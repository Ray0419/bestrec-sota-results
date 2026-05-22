"""Shared artifact helpers for the BEST-Rec script-driven pipeline.

The functions here are intentionally small and dependency-light so every
pipeline stage can use the same hashing, JSON, and schema conventions.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RUN_DIR = Path(__file__).resolve().parent
ROOT = RUN_DIR.parent
CONFIRMATORY_ROOT = ROOT / "_bestrec_confirmatory"

DATASETS = ("beauty", "fashion", "instruments", "books")

DATASET_LABELS = {
    "beauty": "Beauty",
    "fashion": "Fashion",
    "instruments": "Instruments",
    "books": "Books",
}

DATASET_STATS = {
    "beauty": {"k": 5, "users": 253, "items": 177, "ratings": 1467},
    "fashion": {"k": 5, "users": 513, "items": 312, "ratings": 2998},
    "instruments": {"k": 5, "users": 3911, "items": 2400, "ratings": 22274},
    "books": {"k": 5, "users": 14407, "items": 9561, "ratings": 80008},
}

METHOD_LABELS = {
    "ease_sbert": "EASE+SBERT",
    "lc2c_v2": "LC2C V2",
    "lc2c": "LC2C",
    "lc2c_fusion": "LC2C++ rank fusion",
    "lc2c_kernel": "LC2C++ kernel",
    "lc2c_neural": "LC2C++ neural",
    "content_direct": "Content-direct",
    "popularity": "Popularity",
    "ease_pure": "EASE-pure (Steck 2019)",
    "higher_order": "Higher-Order EASE",
    "higher_order_ease": "Higher-Order EASE",
    "ials": "iALS",
    "multivae": "MultiVAE",
    "lightgcn": "LightGCN",
    "dropoutnet": "DropoutNet",
    "dropoutnet_faithful": "Faithful DropoutNet",
    "lc2cpp_validated_margin": "LC2C++ validated margin",
    "clcrec_melt": "CLCRec/MELT-style cold start",
    "clcrec_contrastive": "CLCRec/CCFCRec-style contrastive",
    "melt_tail_transfer": "MELT-style tail transfer",
    "blair_text": "BLaIR-style text retrieval",
    "tiger_liger_retrieval": "TIGER/LIGER-style retrieval",
    "random": "Random",
}

MANDATORY_SOTA_BASELINES = (
    "faithful_dropoutnet",
    "clcrec_contrastive",
    "melt_tail_transfer",
    "blair_text",
    "tiger_liger_retrieval",
    "lightgcn",
    "multivae",
    "ials",
)

CONFIRMATORY_LC2CPP_CONFIG = {
    "method": "lc2cpp_validated_margin",
    "weights": [1.0, 0.995, 0.99, 0.985, 0.98, 0.975, 0.95, 0.90, 0.85, 0.75],
    "validation_fraction": 0.2,
    "minimum_validation_margin": 0.001,
    "fallback": "lc2c_v2",
    "candidate_scope": "full_catalog",
    "locked": True,
    "forbidden_components": [
        "price_affinity",
        "user_gated_selection",
        "fixed_0.95_test_grid_fusion",
        "post_result_variant_edits",
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path: str | Path, default: Any | None = None) -> Any:
    path = Path(path)
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def hash_existing(paths: Iterable[str | Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in paths:
        path = Path(p)
        if path.exists():
            out[str(path.relative_to(ROOT) if path.is_absolute() else path)] = sha256_file(path)
    return out


def rel(path: str | Path) -> str:
    path = Path(path)
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def git_commit() -> str | None:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if res.returncode == 0:
        return res.stdout.strip() or None
    return None


def machine_notes() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cwd": str(ROOT),
        "git_commit": git_commit(),
    }


def append_manifest_run(
    command: list[str],
    inputs: Iterable[str | Path],
    outputs: Iterable[str | Path],
    datasets: Iterable[str] | None = None,
    seeds: Iterable[int | str] | None = None,
    note: str | None = None,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path or RUN_DIR / "results_manifest.json")
    manifest = read_json(manifest_path, default={"schema_version": 1, "runs": []})
    entry = {
        "timestamp_utc": utc_now(),
        "command": command,
        "datasets": list(datasets or []),
        "seeds": [str(s) for s in (seeds or [])],
        "input_hashes": hash_existing(inputs),
        "output_hashes": hash_existing(outputs),
        "machine": machine_notes(),
    }
    if note:
        entry["note"] = note
    manifest.setdefault("runs", []).append(entry)
    manifest["latest_output_hashes"] = hash_existing(outputs)
    manifest["updated_utc"] = utc_now()
    write_json(manifest_path, manifest)
    return manifest


def metric_fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def metric_pm(mean: Any, std: Any, digits: int = 4) -> str:
    if mean is None:
        return "-"
    if std is None:
        return metric_fmt(mean, digits)
    return f"{metric_fmt(mean, digits)} +- {metric_fmt(std, digits)}"


def p_marker(p: Any, fallback: str = "n.s.") -> str:
    if isinstance(p, str):
        return p
    if p is None:
        return fallback
    try:
        val = float(p)
    except (TypeError, ValueError):
        return fallback
    if val < 0.001:
        return "***"
    if val < 0.01:
        return "**"
    if val < 0.05:
        return "*"
    return "n.s."


def fold_count_summary(counts: Any) -> str:
    if not counts:
        return "-"
    if isinstance(counts, dict):
        counts = [counts[k] for k in sorted(counts)]
    counts = list(counts)
    uniq = sorted(set(counts))
    if len(uniq) == 1:
        return f"{uniq[0]} each"
    return ", ".join(str(x) for x in counts)


def warm_record_to_dict(dataset: str, method: str, row: Any, seed: int | str = 42) -> dict[str, Any]:
    """Parse both legacy and canonical warm per-user records."""
    if isinstance(row, dict):
        return row
    if isinstance(row, (list, tuple)) and len(row) >= 9:
        return {
            "dataset": row[0],
            "fold_id": row[1],
            "seed": row[2],
            "method": row[3],
            "user_id": row[4],
            "target_item_id": row[5],
            "ndcg10": row[6],
            "hr10": row[7],
            "rr": row[8],
        }
    if isinstance(row, (list, tuple)) and len(row) >= 3:
        return {
            "dataset": dataset,
            "fold_id": row[0],
            "seed": seed,
            "method": method,
            "user_id": row[1],
            "target_item_id": None,
            "ndcg10": row[2],
            "hr10": None,
            "rr": None,
            "legacy_schema": True,
        }
    raise ValueError(f"Unrecognized warm record for {dataset}/{method}: {row!r}")


def cold_record_to_dict(dataset: str, method: str, row: Any, seed: int | str = 42) -> dict[str, Any]:
    """Parse both legacy and canonical cold per-user records."""
    if isinstance(row, dict):
        return row
    if isinstance(row, (list, tuple)) and len(row) >= 10:
        return {
            "dataset": row[0],
            "fold_id": row[1],
            "seed": row[2],
            "method": row[3],
            "user_id": row[4],
            "target_item_id": row[5],
            "candidate_scope": row[6],
            "ndcg10": row[7],
            "hr10": row[8],
            "rr": row[9],
        }
    if isinstance(row, (list, tuple)) and len(row) >= 4:
        return {
            "dataset": dataset,
            "fold_id": row[0],
            "seed": seed,
            "method": method,
            "user_id": row[1],
            "target_item_id": row[2],
            "candidate_scope": "cold_fold_only",
            "ndcg10": row[3],
            "hr10": None,
            "rr": None,
            "legacy_schema": True,
        }
    raise ValueError(f"Unrecognized cold record for {dataset}/{method}: {row!r}")
