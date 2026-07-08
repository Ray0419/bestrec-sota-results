"""Gate HSTU/SASRec fusion protocols against known validation leakage.

The current HSTU-BLaIR checkpoint was trained using targets that are
effectively BEST-Rec validation targets. This script turns the split-protocol
audit into an executable gate so future experiment reports cannot accidentally
claim validation-selected HSTU fusion from contaminated validation-query scores.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-protocol-audit", default="_bestrec_sota_lab/runs/hstu_split_protocol_20260609/hstu_split_protocol_audit.json")
    parser.add_argument("--fusion-selection", choices=("none", "predeclared", "bestrec_validation", "fresh_retrained_hstu_validation"), required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    audit_path = Path(args.split_protocol_audit)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    train_vs_valid = audit["comparisons"]["hstu_train_target_vs_bestrec_valid"]
    eval_vs_test = audit["comparisons"]["hstu_eval_target_vs_bestrec_test"]
    validation_contaminated = train_vs_valid["target_mismatches"] <= 10
    allowed = True
    failures: list[str] = []

    if args.fusion_selection == "bestrec_validation" and validation_contaminated:
        allowed = False
        failures.append(
            "Current HSTU train targets are effectively BEST-Rec validation targets; "
            "BEST-Rec-validation-selected fusion would leak HSTU training labels."
        )
    if eval_vs_test["target_mismatches"] > 0:
        failures.append(
            f"HSTU eval targets differ from BEST-Rec test for {eval_vs_test['target_mismatches']} users; "
            "paired diagnostics must exclude/disclose those users."
        )

    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "pass" if allowed else "fail",
        "fusion_selection": args.fusion_selection,
        "validation_contaminated_for_current_hstu_checkpoint": validation_contaminated,
        "hstu_train_target_vs_bestrec_valid_mismatches": train_vs_valid["target_mismatches"],
        "hstu_eval_target_vs_bestrec_test_mismatches": eval_vs_test["target_mismatches"],
        "allowed": allowed,
        "failures": failures,
        "split_protocol_audit": str(audit_path),
        "allowed_routes": [
            "predeclared fusion selected without HSTU validation-query scores",
            "fresh HSTU-compatible retraining with a genuine held-out validation split",
            "diagnostic-only analysis clearly marked non-publication",
        ],
    }
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
