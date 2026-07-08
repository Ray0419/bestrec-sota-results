"""Replay a frozen multi-RRF candidate without validation/test tuning.

The script reads a frozen candidate manifest and applies its exact RRF weights
to supplied per-user component records. It is intended as a bridge from
development to confirmatory execution: the fusion recipe is locked before the
records are evaluated.

This script deliberately does not convert top-k component records into a
publication-grade full-catalog claim. If only top-k component lists are
supplied, use the corresponding top-k union candidate scope and keep
publication_grade=false.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from train_multi_rrf_fusion import (
    MethodInput,
    load_rows,
    rank_for_user,
    sha256_file,
    validate_method_sets,
)


ALLOWED_TOPK_SCOPE = "multi_method_top50_union_history_masked"


def parse_method_input(values: list[str]) -> MethodInput:
    if len(values) != 3:
        raise ValueError(f"Expected NAME PATH IDS_KEY, got {values!r}")
    return MethodInput(name=values[0], path=Path(values[1]), ids_key=values[2])


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def metric_sums() -> dict[str, float]:
    return {"ndcg10": 0.0, "hr10": 0.0, "rr": 0.0}


def evaluate_frozen(
    *,
    user_ids: list[int],
    method_rows: dict[str, Any],
    config: dict[str, Any],
    rrf_k: int,
    records_path: Path,
    dataset: str,
    seed: int,
    fold_id: int,
    candidate_scope: str,
    stage: str,
) -> dict[str, Any]:
    sums = metric_sums()
    target_in_union = 0
    records_path.parent.mkdir(parents=True, exist_ok=True)
    with records_path.open("w", encoding="utf-8") as handle:
        for user_id in user_ids:
            ranked, scores, rank0, metrics, target = rank_for_user(
                user_id,
                method_rows,
                config,
                rrf_k=rrf_k,
            )
            if rank0 is not None:
                target_in_union += 1
            for metric, value in metrics.items():
                sums[metric] += value
            handle.write(
                json.dumps(
                    {
                        "candidate_scope": candidate_scope,
                        "dataset": dataset,
                        "fold_id": fold_id,
                        "fusion_config": config["name"],
                        "fusion_weights": config["weights"],
                        "hr10": metrics["hr10"],
                        "method": "multi_rrf_frozen_candidate",
                        "ndcg10": metrics["ndcg10"],
                        "publication_grade": False,
                        "rank": None if rank0 is None else rank0 + 1,
                        "rr": metrics["rr"],
                        "rrf_k": int(config.get("rrf_k", rrf_k)),
                        "seed": seed,
                        "stage": stage,
                        "target_item_id": target,
                        "top_ids": ranked[:50],
                        "top_scores": scores[:50],
                        "user_id": user_id,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    n = len(user_ids)
    return {
        "n": n,
        "ndcg10": sums["ndcg10"] / n if n else math.nan,
        "hr10": sums["hr10"] / n if n else math.nan,
        "rr": sums["rr"] / n if n else math.nan,
        "target_in_union_rate": target_in_union / n if n else math.nan,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--input", nargs=3, action="append", metavar=("NAME", "PATH", "IDS_KEY"), required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--dataset", default="Video_Games")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--fold-id", type=int, default=0)
    parser.add_argument("--stage", choices=["development_replay", "confirmatory"], default="development_replay")
    parser.add_argument("--candidate-scope", default=ALLOWED_TOPK_SCOPE)
    parser.add_argument("--top-k", type=int, default=50)
    args = parser.parse_args()

    if args.candidate_scope == "full_catalog":
        raise SystemExit(
            "ERROR: this replay script consumes top-k component lists and cannot certify full_catalog records. "
            "Generate full-catalog component scores first."
        )
    if args.candidate_scope != ALLOWED_TOPK_SCOPE:
        raise SystemExit(f"ERROR: unsupported candidate scope {args.candidate_scope!r}")

    started = time.time()
    manifest_path = Path(args.manifest)
    manifest = read_json(manifest_path)
    specs = [parse_method_input(value) for value in args.input]
    spec_names = {spec.name for spec in specs}
    frozen = manifest["fusion_config"]
    raw_weights = {str(name): float(value) for name, value in frozen["weights"].items()}
    missing = sorted(set(raw_weights) - spec_names)
    extra = sorted(spec_names - set(raw_weights))
    if missing or extra:
        raise SystemExit(f"ERROR: input names must match frozen weights; missing={missing}, extra={extra}")
    weights = {spec.name: raw_weights[spec.name] for spec in specs}
    rrf_k = int(frozen["rrf_k"])
    config = {
        "name": "frozen_" + "_".join(f"{name}{value:g}" for name, value in sorted(weights.items())) + f"_k{rrf_k}",
        "weights": weights,
        "rrf_k": rrf_k,
    }

    rows = {spec.name: load_rows(spec, top_k=args.top_k) for spec in specs}
    user_ids = validate_method_sets(rows)
    out_dir = Path(args.out_dir)
    records_path = out_dir / f"warm_full_catalog_records_{args.dataset}_multi_rrf_frozen_{args.stage}.jsonl"
    metrics = evaluate_frozen(
        user_ids=user_ids,
        method_rows=rows,
        config=config,
        rrf_k=rrf_k,
        records_path=records_path,
        dataset=args.dataset,
        seed=args.seed,
        fold_id=args.fold_id,
        candidate_scope=args.candidate_scope,
        stage=args.stage,
    )
    summary = {
        "schema_version": 1,
        "status": "complete",
        "publication_grade": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_sec": round(time.time() - started, 3),
        "stage": args.stage,
        "dataset": args.dataset,
        "seed": args.seed,
        "fold_id": args.fold_id,
        "candidate_scope": args.candidate_scope,
        "frozen_manifest": {
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path)["sha256"],
            "candidate_name": manifest.get("candidate_name"),
        },
        "frozen_config": config,
        "weight_iteration_order": [spec.name for spec in specs],
        "inputs": {spec.name: {"ids_key": spec.ids_key, "file": sha256_file(spec.path)} for spec in specs},
        "users": len(user_ids),
        "metrics": metrics,
        "records": sha256_file(records_path),
        "honest_interpretation": (
            "Frozen replay with no validation or test-time fusion search. "
            "Still not publication evidence unless generated from fresh confirmatory full-catalog component scores."
        ),
    }
    summary_path = out_dir / f"multi_rrf_frozen_{args.stage}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "complete",
                "summary": str(summary_path),
                "records": str(records_path),
                "ndcg10": metrics["ndcg10"],
                "hr10": metrics["hr10"],
                "rr": metrics["rr"],
                "candidate_scope": args.candidate_scope,
                "publication_grade": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
