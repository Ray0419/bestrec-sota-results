"""Strict artifact validator for the repaired BEST-Rec pipeline."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from artifact_utils import CONFIRMATORY_LC2CPP_CONFIG, CONFIRMATORY_ROOT, DATASET_STATS, DATASETS, MANDATORY_SOTA_BASELINES, ROOT, RUN_DIR, read_json


TABLES_PATH = RUN_DIR / "tables.json"
SIGNIFICANCE_PATH = RUN_DIR / "significance.json"
MANIFEST_PATH = RUN_DIR / "results_manifest.json"
BASELINE_AUDIT_PATH = RUN_DIR / "results_sota_audit.json"
PUBLICATION_GATE_PATH = RUN_DIR / "publication_gate.json"
PAPER_SCRIPT = ROOT / "_paper_gen" / "build_paper_full.py"
ROOT_NOTEBOOK = ROOT / "BEST_Rec_v4.ipynb"
CONFIRMATORY_RUN_DIR: Path | None = None


def _latest_confirmatory_run() -> Path:
    if not CONFIRMATORY_ROOT.exists():
        raise FileNotFoundError(f"No confirmatory root exists: {CONFIRMATORY_ROOT}")
    candidates = [p for p in CONFIRMATORY_ROOT.iterdir() if p.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No confirmatory runs exist under: {CONFIRMATORY_ROOT}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def configure_paths(confirmatory_run: str | None, strict_publication: bool = False) -> None:
    global TABLES_PATH, SIGNIFICANCE_PATH, MANIFEST_PATH, BASELINE_AUDIT_PATH, PUBLICATION_GATE_PATH, CONFIRMATORY_RUN_DIR
    if confirmatory_run or strict_publication:
        run_dir = CONFIRMATORY_ROOT / confirmatory_run if confirmatory_run else _latest_confirmatory_run()
        CONFIRMATORY_RUN_DIR = run_dir
        TABLES_PATH = run_dir / "tables.json"
        SIGNIFICANCE_PATH = run_dir / "significance.json"
        MANIFEST_PATH = run_dir / "results_manifest.json"
        BASELINE_AUDIT_PATH = run_dir / "baseline_audit.json"
        PUBLICATION_GATE_PATH = run_dir / "publication_gate.json"


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def manifest_contains(manifest: dict[str, Any], rel_path: str) -> bool:
    wanted = rel_path.replace("\\", "/")
    keys: set[str] = set()
    keys.update(k.replace("\\", "/") for k in manifest.get("latest_output_hashes", {}))
    for run in manifest.get("runs", []):
        keys.update(k.replace("\\", "/") for k in run.get("output_hashes", {}))
    return wanted in keys


def check_required_artifacts(errors: list[str]) -> None:
    for path in (TABLES_PATH, SIGNIFICANCE_PATH, MANIFEST_PATH):
        if not path.exists():
            fail(errors, f"Missing required artifact: {path}")
    if errors:
        return
    manifest = read_json(MANIFEST_PATH)
    for rel in ("_bestrec_run/tables.json", "_bestrec_run/significance.json"):
        if not manifest_contains(manifest, rel):
            fail(errors, f"Manifest does not record generated artifact: {rel}")


def _rel_to_root(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if line:
                try:
                    yield line_no, read_json_object(line)
                except Exception as exc:
                    raise ValueError(f"{path}:{line_no}: invalid JSONL row: {exc}") from exc


def read_json_object(text: str) -> dict[str, Any]:
    import json
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("row is not an object")
    return obj


def check_confirmatory_artifacts(errors: list[str]) -> None:
    if CONFIRMATORY_RUN_DIR is None:
        fail(errors, "Strict publication validation requires a confirmatory run directory.")
        return
    required = [
        CONFIRMATORY_RUN_DIR / "run_config.json",
        CONFIRMATORY_RUN_DIR / "results_final.json",
        CONFIRMATORY_RUN_DIR / "tables.json",
        CONFIRMATORY_RUN_DIR / "significance.json",
        CONFIRMATORY_RUN_DIR / "baseline_audit.json",
        CONFIRMATORY_RUN_DIR / "publication_gate.json",
        CONFIRMATORY_RUN_DIR / "results_manifest.json",
    ]
    for dataset in DATASETS:
        required.append(CONFIRMATORY_RUN_DIR / f"cold_full_catalog_records_{dataset}.jsonl")
        required.append(CONFIRMATORY_RUN_DIR / f"warm_records_{dataset}.jsonl")
    for path in required:
        if not path.exists():
            fail(errors, f"Missing confirmatory artifact: {path}")
    if errors:
        return
    manifest = read_json(MANIFEST_PATH)
    for path in required:
        rel_path = _rel_to_root(path)
        if path.name == "results_manifest.json":
            continue
        if not manifest_contains(manifest, rel_path):
            fail(errors, f"Confirmatory manifest does not record generated artifact: {rel_path}")
    all_manifest_paths: list[str] = []
    all_manifest_paths.extend(manifest.get("latest_output_hashes", {}).keys())
    for run in manifest.get("runs", []):
        all_manifest_paths.extend(run.get("input_hashes", {}).keys())
        all_manifest_paths.extend(run.get("output_hashes", {}).keys())
    for path in all_manifest_paths:
        norm = path.replace("\\", "/")
        if re.search(r"cache/.+/v5(/|_).*v5_results\.json$", norm):
            fail(errors, f"Strict publication manifest references stale cache/v5 results: {path}")


def check_confirmatory_publication_gate(errors: list[str]) -> None:
    if CONFIRMATORY_RUN_DIR is None or errors:
        return
    tables = read_json(TABLES_PATH)
    gate = read_json(PUBLICATION_GATE_PATH)
    audit = read_json(BASELINE_AUDIT_PATH)
    config = read_json(CONFIRMATORY_RUN_DIR / "run_config.json")
    if not tables.get("confirmatory"):
        fail(errors, "tables.json is not marked as a confirmatory artifact.")
    if tables.get("primary_candidate_scope") != "full_catalog":
        fail(errors, "Primary cold-item candidate scope is not full_catalog.")
    if tables.get("algorithm_config") != CONFIRMATORY_LC2CPP_CONFIG:
        fail(errors, "Confirmatory LC2C++ algorithm config does not match the frozen lock file.")
    if config.get("lc2cpp_config") != CONFIRMATORY_LC2CPP_CONFIG:
        fail(errors, "run_config.json does not record the frozen LC2C++ config.")
    if not gate.get("passed"):
        failures = gate.get("failures", [])
        fail(errors, "Publication gate did not pass: " + "; ".join(str(x) for x in failures[:8]))
    for name in MANDATORY_SOTA_BASELINES:
        entry = audit.get("baselines", {}).get(name, {})
        if entry.get("status") != "complete":
            fail(errors, f"Mandatory baseline is not publication-grade complete: {name} status={entry.get('status')}")
    for dataset in DATASETS:
        cold_path = CONFIRMATORY_RUN_DIR / f"cold_full_catalog_records_{dataset}.jsonl"
        seen_rows = 0
        for _, row in _iter_jsonl(cold_path):
            seen_rows += 1
            required_keys = {"dataset", "fold_id", "seed", "method", "user_id", "target_item_id", "candidate_scope", "ndcg10", "hr10", "rr"}
            missing = required_keys - set(row)
            if missing:
                fail(errors, f"{cold_path.name} row missing keys: {sorted(missing)}")
                break
            if row.get("candidate_scope") != "full_catalog":
                fail(errors, f"{cold_path.name} contains non-full-catalog row.")
                break
        if seen_rows == 0:
            fail(errors, f"{cold_path.name} has no records.")
    books_path = CONFIRMATORY_RUN_DIR / "warm_records_books.jsonl"
    counts: dict[tuple[str, int, int], int] = {}
    for _, row in _iter_jsonl(books_path):
        if row.get("method") == "ease_sbert":
            key = (str(row.get("method")), int(row.get("seed")), int(row.get("fold_id")))
            counts[key] = counts.get(key, 0) + 1
    required_books = DATASET_STATS["books"]["users"]
    if not counts:
        fail(errors, "Books warm_records has no ease_sbert records.")
    for key, count in sorted(counts.items()):
        if count < required_books:
            fail(errors, f"Books warm-LOO is capped or incomplete for {key}: {count} < {required_books}.")


def check_table_5_2(errors: list[str]) -> None:
    tables = read_json(TABLES_PATH)
    sig = read_json(SIGNIFICANCE_PATH)
    rows = tables.get("table_5_2_baselines", {}).get("rows", [])
    columns = tables.get("table_5_2_baselines", {}).get("columns", [])
    method_to_key = {
        "Popularity": "popularity",
        "EASE-pure": "ease_pure",
        "Higher-Order EASE": "higher_order_ease",
        "iALS": "ials",
        "MultiVAE": "multivae",
        "LightGCN": "lightgcn",
    }
    for row in rows:
        dataset_label = row[0].lower()
        dataset = "instruments" if dataset_label.startswith("instruments") else dataset_label
        for idx, column in enumerate(columns[1:], start=1):
            cell = row[idx]
            if cell == "OOM/NA":
                continue
            key = method_to_key[column]
            entry = sig.get("warm", {}).get(dataset, {}).get(key, {})
            marker = entry.get("marker")
            if not marker and key == "higher_order_ease":
                marker = sig.get("warm", {}).get(dataset, {}).get("higher_order", {}).get("marker")
            if marker and marker not in cell:
                fail(errors, f"Table 5.2 mismatch for {dataset}/{column}: cell={cell!r}, significance marker={marker!r}")


def check_paper_builder(errors: list[str]) -> None:
    text = PAPER_SCRIPT.read_text(encoding="utf-8")
    required_terms = [
        "TABLES_PATH",
        "MANIFEST_PATH",
        "generated_table(\"table_5_2_baselines\")",
        "--confirmatory-run",
        "table_confirmatory_cold_full_catalog",
    ]
    for term in required_terms:
        if term not in text:
            fail(errors, f"Paper builder is not manifest/table gated; missing {term!r}")
    forbidden = [
        "baseline_data = [",
        "protocol_size_data = [",
        "main_data = [",
        "cold_item_data = [",
        "wilcoxon_data = [",
        "bootstrap_data = [",
    ]
    for needle in forbidden:
        if needle in text:
            fail(errors, f"Paper builder still hardcodes empirical table via {needle}")


def check_docs(errors: list[str]) -> None:
    bad_patterns = [
        re.compile(r"set\s+DATASET\s+in\s+the\s+notebook", re.I),
        re.compile(r"run\s+all\s+cells", re.I),
        re.compile(r"notebook\s+path\s+is\s+needed", re.I),
        re.compile(r"uv\s+run\s+python\s+make_figures_v3\.py", re.I),
        re.compile(r"run_cold_user\.py", re.I),
    ]
    for rel in ("README.md", "RUNNING.md", "SUBMISSION.md", "_paper_gen/build_paper_full.py"):
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pat in bad_patterns:
            if pat.search(text):
                fail(errors, f"Forbidden reproduction instruction in {rel}: {pat.pattern}")
    if ROOT_NOTEBOOK.exists():
        fail(errors, "BEST_Rec_v4.ipynb still exists at repository root; move it to archive/legacy_notebooks/.")


def check_sota_gate(errors: list[str], allow_internal: bool) -> None:
    tables = read_json(TABLES_PATH)
    if tables.get("sota_claim_allowed"):
        return
    if allow_internal:
        return
    fail(errors, "SOTA claim is not allowed by tables.json; build must be treated as an internal failure report.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-internal-report", action="store_true", help="Allow validation to pass with SOTA claims disabled.")
    parser.add_argument("--strict-publication", action="store_true", help="Validate the latest or named confirmatory run against publication/SOTA gates.")
    parser.add_argument("--confirmatory-run", default=None, help="Confirmatory run_id under _bestrec_confirmatory. Defaults to latest run for --strict-publication.")
    args = parser.parse_args()

    errors: list[str] = []
    try:
        configure_paths(args.confirmatory_run, args.strict_publication)
    except Exception as exc:
        fail(errors, str(exc))

    if args.strict_publication or args.confirmatory_run:
        if not errors:
            check_confirmatory_artifacts(errors)
        if not errors:
            check_paper_builder(errors)
            check_docs(errors)
            check_confirmatory_publication_gate(errors)
    else:
        check_required_artifacts(errors)
    if not errors and not (args.strict_publication or args.confirmatory_run):
        check_table_5_2(errors)
        check_paper_builder(errors)
        check_docs(errors)
        check_sota_gate(errors, args.allow_internal_report)

    if errors:
        print("VALIDATION FAILED")
        for item in errors:
            print(f"- {item}")
        return 1
    print("VALIDATION PASSED")
    for dataset in DATASETS:
        print(f"- checked {dataset}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
