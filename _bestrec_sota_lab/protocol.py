"""Protocol and manifest helpers for the isolated SOTA lab."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


LAB_DIR = Path(__file__).resolve().parent
ROOT = LAB_DIR.parent
BESTREC_RUN_DIR = ROOT / "_bestrec_run"
DEFAULT_PROTOCOL_PATH = LAB_DIR / "protocols" / "cold_sota_strict_v2.json"


def load_protocol(path: str | Path | None = None) -> dict[str, Any]:
    protocol_path = Path(path) if path else DEFAULT_PROTOCOL_PATH
    payload = json.loads(protocol_path.read_text(encoding="utf-8"))
    payload["_path"] = str(protocol_path)
    return payload


def load_dropoutnet_feature_config(protocol: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    protocol = protocol or load_protocol()
    cfg_path = Path(protocol["dropoutnet_feature_config_path"])
    if not cfg_path.is_absolute():
        cfg_path = (LAB_DIR / cfg_path).resolve()
    payload = json.loads(cfg_path.read_text(encoding="utf-8"))
    configs = payload.get("datasets", payload)
    required = set(protocol.get("datasets", []))
    missing = sorted(required - set(configs))
    if missing:
        raise ValueError(f"DropoutNet feature config missing datasets: {missing}")
    return {name: dict(configs[name]) for name in sorted(configs)}


def protocol_summary(protocol: dict[str, Any] | None = None) -> dict[str, Any]:
    protocol = protocol or load_protocol()
    return {
        "protocol_id": protocol.get("protocol_id"),
        "protocol_path": protocol.get("_path"),
        "claim_scope": protocol.get("claim_scope"),
        "datasets": protocol.get("datasets"),
        "fresh_confirmatory_seeds": protocol.get("fresh_confirmatory_seeds"),
        "required_evidence_methods": protocol.get("required_evidence_methods"),
        "minimum_bootstrap_reps": protocol.get("minimum_bootstrap_reps"),
    }


def lab_code_inputs() -> list[Path]:
    patterns = (
        "*.py",
        "README.md",
        "protocols/*.json",
        "dropoutnet_feature_config*.json",
        "publication_candidate*.json",
        "ablation_configs/*.json",
    )
    out: list[Path] = []
    for pattern in patterns:
        out.extend(sorted(LAB_DIR.glob(pattern)))
    return [p for p in out if p.is_file()]


def external_code_inputs() -> list[Path]:
    """Hash external comparator source without pulling in checkpoints/results."""

    roots = [ROOT / "external" / "liger"]
    allowed_suffixes = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt"}
    allowed_names = {"LICENSE", ".gitignore"}
    skip_dirs = {".git", "__pycache__", "outputs", "results"}
    out: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel_parts = set(path.relative_to(root).parts[:-1])
            if rel_parts & skip_dirs:
                continue
            if path.suffix.lower() in allowed_suffixes or path.name in allowed_names:
                out.append(path)
    return out


def bestrec_code_inputs() -> list[Path]:
    names = [
        "artifact_utils.py",
        "ease_efficient.py",
        "run_all_confirmatory.py",
        "run_cold_item.py",
        "run_warm_loo.py",
        "v5_utils.py",
        "run_faithful_dropoutnet.py",
        "run_faithful_blair.py",
        "run_faithful_clcrec.py",
        "pyproject.toml",
        "uv.lock",
    ]
    return [BESTREC_RUN_DIR / name for name in names if (BESTREC_RUN_DIR / name).exists()]


def dataset_cache_inputs(datasets: list[str]) -> list[Path]:
    try:
        from run_cold_item import DATASET_KCORE  # type: ignore
    except Exception:
        DATASET_KCORE = {"beauty": 5, "fashion": 5, "instruments": 5, "books": 5}
    out: list[Path] = []
    for dataset in datasets:
        k_core = DATASET_KCORE[dataset]
        cache_dir = ROOT / "cache" / dataset
        out.append(cache_dir / "raw_data_dedup.pkl")
        out.append(cache_dir / "v5" / f"item_title_k{k_core}_dedup.pt")
        out.append(cache_dir / "v5" / f"item_title_blair_k{k_core}_dedup.pt")
    return [p for p in out if p.exists()]


def run_artifact_inputs(run_dir: Path, datasets: list[str]) -> list[Path]:
    derived_outputs = {
        "baseline_audit.json",
        "results_final.json",
        "significance.json",
        "publication_gate.json",
        "tables.json",
        "results_manifest.json",
        "INTERNAL_SOTA_FAILURE_REPORT.md",
        "SOTA_PASS_REPORT.md",
    }
    out: list[Path] = []
    for dataset in datasets:
        for prefix in ("cold_full_catalog_records", "warm_records"):
            path = run_dir / f"{prefix}_{dataset}.jsonl"
            if path.exists():
                out.append(path)
    for pattern in ("*audit*.json", "*summary*.json", "*run_config*.json", "frozen_candidate_config.json", "research_decision.json"):
        out.extend(path for path in sorted(run_dir.glob(pattern)) if path.name not in derived_outputs)
    for audit_path in sorted(run_dir.glob("*audit*.json")):
        try:
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        source_dir = audit.get("source_dir")
        if source_dir:
            src_dir = Path(source_dir)
            if not src_dir.is_absolute():
                src_dir = ROOT / src_dir
            for name in (
                "official_clcrec_source_audit.json",
                "official_clcrec_source_summary.json",
                "results_faithful_dropoutnet.json",
                "official_dropoutnet_fixed_audit.json",
            ):
                path = src_dir / name
                if path.exists():
                    out.append(path)
        dataset_blocks = audit.get("datasets", {})
        if isinstance(dataset_blocks, dict):
            iterable_blocks = dataset_blocks.values()
        elif isinstance(dataset_blocks, list):
            iterable_blocks = dataset_blocks
        else:
            iterable_blocks = []
        for block in iterable_blocks:
            source_path = block.get("source_path") if isinstance(block, dict) else None
            if source_path:
                path = Path(source_path)
                if not path.is_absolute():
                    path = ROOT / path
                if path.exists():
                    out.append(path)
    return [p for p in out if p.exists()]


def strict_manifest_inputs(run_dir: Path, datasets: list[str]) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for path in [
        *lab_code_inputs(),
        *bestrec_code_inputs(),
        *external_code_inputs(),
        *dataset_cache_inputs(datasets),
        *run_artifact_inputs(run_dir, datasets),
    ]:
        key = str(path.resolve())
        if key not in seen and path.exists():
            seen.add(key)
            out.append(path)
    return out
