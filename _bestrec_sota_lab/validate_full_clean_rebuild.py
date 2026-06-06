"""Compare an independent full clean-rebuild run with the canonical run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from sota_common import DATASETS, LAB_PROTOCOL, RUNS_DIR, write_json


SUMMARY_FILES = [
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


def row_multiset_fingerprint(path: Path) -> dict[str, Any]:
    """Order-independent fingerprint for canonical JSONL rows.

    Lab JSONL writers use sorted JSON keys, so the stripped line is a stable row
    representation. Combining SHA-256 row digests with count, modular sum, and
    xor gives a streaming multiset check without sorting multi-GB files.
    """
    modulus = 1 << 256
    count = 0
    digest_sum = 0
    digest_xor = 0
    with path.open("rb") as f:
        for raw in f:
            row = raw.strip()
            if not row:
                continue
            digest = hashlib.sha256(row).digest()
            value = int.from_bytes(digest, "big")
            count += 1
            digest_sum = (digest_sum + value) % modulus
            digest_xor ^= value
    return {
        "row_count": int(count),
        "row_digest_sum_sha256": f"{digest_sum:064x}",
        "row_digest_xor_sha256": f"{digest_xor:064x}",
    }


def metric_diffs(canonical: dict[str, Any], rebuilt: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    can_cold = canonical.get("cold_full_catalog", {})
    reb_cold = rebuilt.get("cold_full_catalog", {})
    for dataset in DATASETS:
        for method, can_metrics in can_cold.get(dataset, {}).items():
            reb_metrics = reb_cold.get(dataset, {}).get(method)
            if not reb_metrics:
                rows.append({"dataset": dataset, "method": method, "problem": "missing_method"})
                continue
            for metric in ("NDCG@10", "HR@10", "MRR"):
                can_value = can_metrics.get(metric)
                reb_value = reb_metrics.get(metric)
                if can_value is None or reb_value is None:
                    rows.append({"dataset": dataset, "method": method, "metric": metric, "problem": "missing_metric"})
                    continue
                rows.append(
                    {
                        "dataset": dataset,
                        "method": method,
                        "metric": metric,
                        "canonical": float(can_value),
                        "rebuilt": float(reb_value),
                        "abs_diff": abs(float(can_value) - float(reb_value)),
                    }
                )
            can_n = int(can_metrics.get("n_records", -1))
            reb_n = int(reb_metrics.get("n_records", -2))
            if can_n != reb_n:
                rows.append({"dataset": dataset, "method": method, "problem": "n_records_mismatch", "canonical": can_n, "rebuilt": reb_n})
    return rows


def record_hashes(canonical_dir: Path, rebuilt_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for dataset in DATASETS:
        name = f"cold_full_catalog_records_{dataset}.jsonl"
        c_path = canonical_dir / name
        r_path = rebuilt_dir / name
        if not c_path.exists() or not r_path.exists():
            rows.append({"dataset": dataset, "file": name, "passed": False, "problem": "missing", "canonical_exists": c_path.exists(), "rebuilt_exists": r_path.exists()})
            continue
        c_hash = sha256_file(c_path)
        r_hash = sha256_file(r_path)
        rows.append({"dataset": dataset, "file": name, "passed": c_hash == r_hash, "canonical_sha256": c_hash, "rebuilt_sha256": r_hash})
    return rows


def record_multiset_fingerprints(canonical_dir: Path, rebuilt_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for dataset in DATASETS:
        name = f"cold_full_catalog_records_{dataset}.jsonl"
        c_path = canonical_dir / name
        r_path = rebuilt_dir / name
        if not c_path.exists() or not r_path.exists():
            rows.append({"dataset": dataset, "file": name, "passed": False, "problem": "missing", "canonical_exists": c_path.exists(), "rebuilt_exists": r_path.exists()})
            continue
        c_fp = row_multiset_fingerprint(c_path)
        r_fp = row_multiset_fingerprint(r_path)
        rows.append({"dataset": dataset, "file": name, "passed": c_fp == r_fp, "canonical": c_fp, "rebuilt": r_fp})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--canonical-run-id", default="confirmatory_masked_candidate_20260701_20260705_candidate_only")
    parser.add_argument("--metric-tolerance", type=float, default=1e-9)
    parser.add_argument("--require-record-hash-match", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    canonical_dir = RUNS_DIR / args.canonical_run_id
    rebuilt_dir = RUNS_DIR / args.run_id
    missing = []
    for directory, label in [(canonical_dir, "canonical"), (rebuilt_dir, "rebuilt")]:
        for name in SUMMARY_FILES:
            if not (directory / name).exists():
                missing.append({"run": label, "file": name})
    if missing:
        payload = {"schema_version": 1, "passed": False, "missing": missing}
        out = Path(args.out) if args.out else rebuilt_dir / "full_clean_rebuild_compare.json"
        write_json(out, payload)
        print(f"Wrote {out}")
        return 1

    canonical_results = read_json(canonical_dir / "results_final.json")
    rebuilt_results = read_json(rebuilt_dir / "results_final.json")
    rebuilt_gate = read_json(rebuilt_dir / "publication_gate.json")
    rebuilt_audit = read_json(rebuilt_dir / "baseline_audit.json")
    diffs = metric_diffs(canonical_results, rebuilt_results)
    max_diff = max((float(row.get("abs_diff", 0.0)) for row in diffs if "abs_diff" in row), default=0.0)
    diff_failures = [row for row in diffs if row.get("problem") or float(row.get("abs_diff", 0.0)) > args.metric_tolerance]
    hashes = record_hashes(canonical_dir, rebuilt_dir)
    hash_failures = [row for row in hashes if not row.get("passed")]
    multiset_hashes = record_multiset_fingerprints(canonical_dir, rebuilt_dir)
    multiset_failures = [row for row in multiset_hashes if not row.get("passed")]
    required_methods = list(LAB_PROTOCOL.get("required_evidence_methods", []))
    incomplete_methods = [
        method
        for method in required_methods
        if rebuilt_audit.get("baselines", {}).get(method, {}).get("status") not in {"complete", "not_applicable_to_zero_interaction_item_cold"}
    ]
    passed = (
        bool(rebuilt_gate.get("passed"))
        and not diff_failures
        and not incomplete_methods
        and not multiset_failures
        and (not args.require_record_hash_match or not hash_failures)
    )
    payload = {
        "schema_version": 1,
        "passed": bool(passed),
        "canonical_run_id": args.canonical_run_id,
        "rebuilt_run_id": args.run_id,
        "metric_tolerance": float(args.metric_tolerance),
        "max_metric_abs_diff": float(max_diff),
        "diff_failures": diff_failures[:50],
        "required_method_failures": incomplete_methods,
        "rebuilt_gate_passed": bool(rebuilt_gate.get("passed")),
        "record_hashes": hashes,
        "record_hashes_match": not hash_failures,
        "record_hash_match_required": bool(args.require_record_hash_match),
        "record_multiset_fingerprints": multiset_hashes,
        "record_multisets_match": not multiset_failures,
    }
    out = Path(args.out) if args.out else rebuilt_dir / "full_clean_rebuild_compare.json"
    write_json(out, payload)
    print(f"Wrote {out}")
    print("Full clean rebuild compare:", "PASSED" if passed else "FAILED")
    if diff_failures:
        print(f"Metric/count differences above tolerance: {len(diff_failures)}")
    if incomplete_methods:
        print("Incomplete methods:", ", ".join(incomplete_methods))
    if hash_failures:
        print(f"Raw record hash differences: {len(hash_failures)}")
    if multiset_failures:
        print(f"Canonical row multiset differences: {len(multiset_failures)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
