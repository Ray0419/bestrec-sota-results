# -*- coding: utf-8 -*-
"""Prove the frozen trainer does not open TEST under --no-test-eval."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TRAINER = HERE / "run_sasrec_sbert_efficiency_ml1m_v1_frozen.py"
CATEGORY = "SequestrationSmoke"


def write_csv(path: Path, rows):
    with path.open("x", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["user_id", "parent_asin", "rating", "timestamp"])
        writer.writeheader()
        writer.writerows(rows)


def main():
    with tempfile.TemporaryDirectory(prefix="fir_eff_sequester_") as temporary:
        directory = Path(temporary)
        train = []
        valid = []
        for user in range(3):
            for index in range(6):
                train.append({
                    "user_id": f"u{user}",
                    "parent_asin": f"i{(user + index) % 7}",
                    "rating": 5,
                    "timestamp": (1000 + user * 100 + index) * 1000,
                })
            valid.append({
                "user_id": f"u{user}", "parent_asin": f"i{(user + 1) % 7}",
                "rating": 5, "timestamp": (2000 + user) * 1000,
            })
        write_csv(directory / f"{CATEGORY}.train.csv", train)
        write_csv(directory / f"{CATEGORY}.valid.csv", valid)
        test_path = directory / f"{CATEGORY}.test.csv"
        # Existing and deliberately unparsable: success proves no TEST open/read.
        test_path.write_text("THIS FILE MUST REMAIN UNREAD\n", encoding="utf-8")
        output = directory / "smoke.json"
        command = [
            sys.executable, str(TRAINER), CATEGORY,
            "--epochs", "1", "--batch-size", "3", "--max-seq-len", "10",
            "--d-model", "16", "--n-layers", "1", "--n-heads", "2",
            "--dropout", "0", "--lr", "0.001", "--no-sbert",
            "--eval-every", "1", "--eval-subsample", "0",
            "--fir-control", "identity", "--fir-control-kernel", "16",
            "--no-test-eval", "--sequester-test-load", "--save-ckpt",
            "--split-dir", str(directory), "--out", str(output),
        ]
        child = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        if child.returncode:
            print(child.stdout)
            print(child.stderr, file=sys.stderr)
            raise AssertionError(f"frozen trainer failed with exit {child.returncode}")
        result = json.loads(output.read_text(encoding="utf-8"))
        provenance = result["provenance"]
        if (result.get("best_test") is not None
                or any("test" in row for row in result.get("history", []))
                or provenance["data_sha256"].get("test_csv") is not None
                or provenance["n_interactions"].get("test") != 0
                or "TEST SEALED" not in child.stdout):
            raise AssertionError("TEST sequestration invariants failed")
    print("FIR EFFICIENCY V1 FILE-LEVEL TEST SEQUESTRATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
