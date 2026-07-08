"""Evaluate the frozen sparse multi-RRF candidate against the full catalog.

The frozen development candidate was selected as an RRF fusion over component
top-50 lists. This script makes that scoring function explicit for full-catalog
evaluation:

* component-listed items receive their weighted RRF score;
* every other unmasked catalog item receives score zero;
* user history items are masked using the strict HSTU sequence CSV;
* ties are deterministic, sorted by ascending BEST-Rec item id.

It removes the narrower top-50-union evaluation ambiguity for the frozen sparse
scoring function. A run is confirmatory only when the caller supplies fresh
seeds/artifacts under a frozen protocol and records that protocol in the
metadata fields below.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from train_multi_rrf_fusion import MethodInput, load_rows, validate_method_sets


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class UserHistory:
    target_item_id: int
    history_items: frozenset[int]


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


def parse_method_input(values: list[str]) -> MethodInput:
    if len(values) != 3:
        raise ValueError(f"Expected NAME PATH IDS_KEY, got {values!r}")
    return MethodInput(name=values[0], path=Path(values[1]), ids_key=values[2])


def load_map(path: Path, key: str) -> list[int | None]:
    payload = read_json(path)
    if payload.get("status") != "complete_bijection":
        raise ValueError(f"{path} status={payload.get('status')!r}, expected complete_bijection")
    values = payload.get(key)
    if not isinstance(values, list):
        raise ValueError(f"{path} missing {key}")
    return [None if value is None else int(value) for value in values]


def translate_hstu_zero_item(mapping: list[int | None], hstu_zero_based: int) -> int:
    hstu_one_based = int(hstu_zero_based) + 1
    if hstu_one_based <= 0 or hstu_one_based >= len(mapping):
        raise ValueError(f"HSTU zero-based item {hstu_zero_based} outside map")
    value = mapping[hstu_one_based]
    if value is None:
        raise ValueError(f"HSTU zero-based item {hstu_zero_based} unmapped")
    return value


def translate_hstu_user(mapping: list[int | None], hstu_user: int) -> int:
    hstu_user = int(hstu_user)
    if hstu_user < 0 or hstu_user >= len(mapping):
        raise ValueError(f"HSTU user {hstu_user} outside map")
    value = mapping[hstu_user]
    if value is None:
        raise ValueError(f"HSTU user {hstu_user} unmapped")
    return value


def parse_int_list(value: str) -> list[int]:
    value = value.strip()
    if not value:
        return []
    return [int(part) for part in value.split(",") if part.strip()]


def load_histories(sequence_csv: Path, item_map: Path, user_map: Path) -> dict[int, UserHistory]:
    item_mapping = load_map(item_map, "hstu_one_based_to_bestrec_zero_based")
    user_mapping = load_map(user_map, "hstu_zero_based_to_bestrec_zero_based")
    out: dict[int, UserHistory] = {}
    with sequence_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            seq_hstu = parse_int_list(row["sequence_item_ids"])
            if len(seq_hstu) < 2:
                continue
            bestrec_user = translate_hstu_user(user_mapping, int(row["user_id"]))
            seq_bestrec = [translate_hstu_zero_item(item_mapping, item_id) for item_id in seq_hstu]
            out[bestrec_user] = UserHistory(
                target_item_id=seq_bestrec[-1],
                history_items=frozenset(seq_bestrec[:-1]),
            )
    if not out:
        raise ValueError(f"No histories loaded from {sequence_csv}")
    return out


def metric_from_rank0(rank0: int) -> dict[str, float]:
    return {
        "ndcg10": 1.0 / math.log2(rank0 + 2) if rank0 < 10 else 0.0,
        "hr10": 1.0 if rank0 < 10 else 0.0,
        "rr": 1.0 / float(rank0 + 1),
    }


def zero_score_less_count(target: int, scores: dict[int, float], history: frozenset[int]) -> int:
    # Count catalog items with zero score and smaller id than target, excluding
    # history and excluding any explicit non-zero scored items.
    count = target
    if history:
        count -= sum(1 for item in history if item < target)
    if scores:
        count -= sum(1 for item, score in scores.items() if item < target and score == 0.0)
        count -= sum(1 for item, score in scores.items() if item < target and score != 0.0)
    return max(0, count)


def full_catalog_rank(
    *,
    user_id: int,
    target: int,
    history: frozenset[int],
    method_rows: dict[str, Any],
    weights: dict[str, float],
    rrf_k: int,
) -> tuple[int, list[int], list[float], int]:
    scores: dict[int, float] = {}
    for method_name, weight in weights.items():
        ids = method_rows[method_name][user_id].ids
        for rank, item_id in enumerate(ids, start=1):
            item_id = int(item_id)
            if item_id in history:
                continue
            scores[item_id] = scores.get(item_id, 0.0) + float(weight) / float(rrf_k + rank)

    target_score = float(scores.get(target, 0.0))
    greater = 0
    equal_less = 0
    for item_id, score in scores.items():
        if item_id in history or item_id == target:
            continue
        if score > target_score:
            greater += 1
        elif score == target_score and item_id < target:
            equal_less += 1
    if target_score == 0.0:
        equal_less += zero_score_less_count(target, scores, history)
    rank0 = greater + equal_less

    scored_ranked = sorted(
        ((item, score) for item, score in scores.items() if item not in history),
        key=lambda pair: (-pair[1], pair[0]),
    )
    top_ids: list[int] = []
    top_scores: list[float] = []
    seen = set()
    for item, score in scored_ranked:
        top_ids.append(int(item))
        top_scores.append(float(score))
        seen.add(int(item))
        if len(top_ids) >= 50:
            break
    if len(top_ids) < 50:
        # Fill deterministic zero-score tail from the full unmasked catalog.
        n_items_probe = max(max(scores, default=0) + 1, target + 1)
        for item in range(n_items_probe):
            if item in history or item in seen:
                continue
            top_ids.append(int(item))
            top_scores.append(0.0)
            if len(top_ids) >= 50:
                break
    return rank0, top_ids, top_scores, len(scores)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--input", nargs=3, action="append", metavar=("NAME", "PATH", "IDS_KEY"), required=True)
    parser.add_argument("--sequence-csv", required=True)
    parser.add_argument("--item-map", default="_bestrec_sota_lab/runs/hstu_item_alignment_20260609/hstu_bestrec_item_map.json")
    parser.add_argument("--user-map", default="_bestrec_sota_lab/runs/hstu_user_alignment_20260609/hstu_bestrec_user_map.json")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--dataset", default="Video_Games")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--fold-id", type=int, default=0)
    parser.add_argument("--split", choices=("valid", "test"), default="test")
    parser.add_argument("--top-k", type=int, default=50)
    parser.add_argument("--evidence-stage", choices=("development", "confirmatory"), default="development")
    parser.add_argument("--evidence-scope", default="video_games_sparse_rrf_full_catalog_replay")
    parser.add_argument("--protocol-manifest", default=None)
    parser.add_argument("--claim-scope", default="not_a_broad_sota_claim")
    parser.add_argument("--publication-grade", action="store_true")
    args = parser.parse_args()

    started = time.time()
    manifest_path = Path(args.manifest)
    manifest = read_json(manifest_path)
    frozen = manifest["fusion_config"]
    raw_weights = {str(name): float(value) for name, value in frozen["weights"].items()}
    rrf_k = int(frozen["rrf_k"])
    specs = [parse_method_input(values) for values in args.input]
    spec_names = {spec.name for spec in specs}
    missing = sorted(set(raw_weights) - spec_names)
    extra = sorted(spec_names - set(raw_weights))
    if missing or extra:
        raise SystemExit(f"ERROR: input names must match frozen weights; missing={missing}, extra={extra}")
    weights = {spec.name: raw_weights[spec.name] for spec in specs}
    method_rows = {spec.name: load_rows(spec, top_k=args.top_k) for spec in specs}
    user_ids = validate_method_sets(method_rows)
    histories = load_histories(Path(args.sequence_csv), Path(args.item_map), Path(args.user_map))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    records_path = out_dir / f"full_catalog_records_{args.dataset}_sparse_rrf_frozen_{args.split}.jsonl"
    sums = {"ndcg10": 0.0, "hr10": 0.0, "rr": 0.0}
    target_mismatches: list[dict[str, int]] = []
    positive_scored_items_sum = 0
    with records_path.open("w", encoding="utf-8") as handle:
        for user_id in user_ids:
            target = method_rows[specs[0].name][user_id].target_item_id
            hist = histories.get(user_id)
            if hist is None:
                raise ValueError(f"user_id={user_id} missing from sequence history")
            if hist.target_item_id != target and len(target_mismatches) < 20:
                target_mismatches.append(
                    {"user_id": int(user_id), "record_target": int(target), "sequence_target": int(hist.target_item_id)}
                )
            rank0, top_ids, top_scores, positive_scored = full_catalog_rank(
                user_id=user_id,
                target=target,
                history=hist.history_items,
                method_rows=method_rows,
                weights=weights,
                rrf_k=rrf_k,
            )
            positive_scored_items_sum += positive_scored
            metrics = metric_from_rank0(rank0)
            for metric in sums:
                sums[metric] += metrics[metric]
            handle.write(
                json.dumps(
                    {
                        "candidate_scope": "full_catalog",
                        "dataset": args.dataset,
                        "fold_id": args.fold_id,
                        "fusion_weights": weights,
                        "history_mask_source": str(args.sequence_csv),
                        "hr10": metrics["hr10"],
                        "method": "multi_rrf_sparse_full_catalog_frozen",
                        "evidence_stage": args.evidence_stage,
                        "evidence_scope": args.evidence_scope,
                        "claim_scope": args.claim_scope,
                        "ndcg10": metrics["ndcg10"],
                        "positive_scored_items": positive_scored,
                        "publication_grade": bool(args.publication_grade),
                        "rank": rank0 + 1,
                        "rr": metrics["rr"],
                        "rrf_k": rrf_k,
                        "seed": args.seed,
                        "split": args.split,
                        "target_item_id": int(target),
                        "top_ids": top_ids,
                        "top_scores": top_scores,
                        "user_id": int(user_id),
                    },
                    sort_keys=True,
                )
                + "\n"
            )

    n = len(user_ids)
    metrics = {metric: sums[metric] / n for metric in sums}
    summary = {
        "schema_version": 1,
        "status": "complete",
        "evidence_stage": args.evidence_stage,
        "evidence_scope": args.evidence_scope,
        "claim_scope": args.claim_scope,
        "publication_grade": bool(args.publication_grade),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_sec": round(time.time() - started, 3),
        "dataset": args.dataset,
        "split": args.split,
        "seed": args.seed,
        "fold_id": args.fold_id,
        "candidate_scope": "full_catalog",
        "method": "multi_rrf_sparse_full_catalog_frozen",
        "scoring_definition": {
            "listed_component_items": "weighted reciprocal-rank score",
            "unlisted_unmasked_catalog_items": 0.0,
            "history_mask": "items before the final sequence target in the strict sequence CSV",
            "tie_break": "ascending BEST-Rec item_id",
        },
        "frozen_manifest": {"path": str(manifest_path), "sha256": sha256_file(manifest_path)["sha256"]},
        "protocol_manifest": sha256_file(Path(args.protocol_manifest)) if args.protocol_manifest else None,
        "weights": weights,
        "rrf_k": rrf_k,
        "weight_iteration_order": [spec.name for spec in specs],
        "records": n,
        "metrics": metrics,
        "avg_positive_scored_items": positive_scored_items_sum / n,
        "target_mismatches_first20": target_mismatches,
        "inputs": {
            "sequence_csv": sha256_file(Path(args.sequence_csv)),
            "item_map": sha256_file(Path(args.item_map)),
            "user_map": sha256_file(Path(args.user_map)),
            "components": {spec.name: {"ids_key": spec.ids_key, "file": sha256_file(spec.path)} for spec in specs},
        },
        "outputs": {"records": sha256_file(records_path)},
        "honest_interpretation": (
            "Full-catalog replay of the frozen sparse top-50 RRF scoring function. "
            "Publication use depends on the recorded evidence stage, protocol manifest, "
            "comparator coverage, and downstream gate results."
        ),
    }
    summary_path = out_dir / f"sparse_rrf_full_catalog_frozen_{args.split}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "complete",
                "candidate_scope": "full_catalog",
                "summary": str(summary_path),
                "records": str(records_path),
                "metrics": metrics,
                "target_mismatch_count_reported": len(target_mismatches),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
