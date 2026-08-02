#!/usr/bin/env python3
"""Consolidate paired EGSP evidence without re-evaluating checkpoints."""

from __future__ import annotations

import argparse
import glob
import json
import math
import statistics
from pathlib import Path

from scipy import stats


def load_group(pattern: str) -> dict:
    paths = [Path(path) for path in sorted(glob.glob(pattern))]
    rows = []
    for path in paths:
        artifact = json.loads(path.read_text(encoding="utf-8"))
        metric = artifact["masks"]["strict_negative_infinity"]["NDCG@10"]
        rows.append({
            "artifact": str(path),
            "baseline_sha256": artifact["baseline"]["sha256"],
            "projected_sha256": artifact["projected"]["sha256"],
            **metric,
        })
    deltas = [row["delta"] for row in rows]
    if not deltas:
        return {"n": 0, "rows": []}
    mean = statistics.mean(deltas)
    sd = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
    half_width = 0.0 if len(deltas) == 1 else \
        stats.t.ppf(0.975, len(deltas) - 1) * sd / math.sqrt(len(deltas))
    return {
        "n": len(rows),
        "mean_delta": mean,
        "sd_delta": sd,
        "seed_level_95_ci": [mean - half_width, mean + half_width],
        "positive_seeds": sum(delta > 0 for delta in deltas),
        "rows": rows,
    }


def load_bestrec_smoke(pattern: str) -> dict:
    paths = [Path(path) for path in sorted(glob.glob(pattern))]
    rows = []
    for path in paths:
        artifact = json.loads(path.read_text(encoding="utf-8"))
        comparison = artifact["paired_vs_normal"]["rank1_projection"]
        rows.append({
            "artifact": str(path),
            "checkpoint_sha256": artifact["provenance"]["checkpoint_sha256"],
            **comparison,
        })
    deltas = [row["delta_ndcg10"] for row in rows]
    return {
        "n": len(rows),
        "mean_delta": statistics.mean(deltas) if deltas else None,
        "positive_seeds": sum(delta > 0 for delta in deltas),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    group = args.root / "experiments" / "group_delay_filter"
    fir = args.root / "experiments" / "fir_inference_ablation"
    artifact = {
        "protocol": "EGSP_EVIDENCE_SUMMARY_V1",
        "warning": (
            "ML-1M groups are exploratory discovery evidence; prospective Sports "
            "evidence is governed separately by PREREG_EGSP_PROSPECTIVE_V1.md."
        ),
        "ml1m_spectral_test": load_group(str(group / "paired_ml1m_full_s[0-9]*.json")),
        "ml1m_spectral_validation": load_group(
            str(group / "paired_ml1m_full_valid_s[0-9]*.json")),
        "ml1m_causal_fir_test": load_group(
            str(group / "paired_ml1m_causal_s[0-9]*.json")),
        "bestrec_fir_validation_smoke": load_bestrec_smoke(
            str(fir / "smoke_rank1_learned_s[0-9]*.json")),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        key: {
            field: value[field] for field in ("n", "mean_delta", "positive_seeds")
        }
        for key, value in artifact.items()
        if isinstance(value, dict) and "n" in value
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
