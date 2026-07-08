"""Pair corrected HSTU-BLaIR and SASRec-SBERT records for diagnostics.

This script checks whether the two Video_Games runs can be compared in the
same BEST-Rec user/item id space, then reports complementarity and fixed
rank-fusion diagnostics. It is not a publication gate: any fusion selected from
these test records would be post-hoc and must be rerun through a separate
validation/confirmatory protocol.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


METRICS = ("ndcg10", "hr10", "rr")
USER_ID_CONVENTIONS = {"bestrec_zero_based_user_ids", "BEST-Rec canonical user_id"}
ITEM_ID_CONVENTIONS = {"bestrec_zero_based_item_ids", "BEST-Rec canonical item_id"}


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


def load_rows(path: Path, top_key: str) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            user_id = int(row["user_id"])
            if user_id in rows:
                raise ValueError(f"Duplicate user_id={user_id} in {path} at line {line_number}")
            if row.get("user_id_convention") not in USER_ID_CONVENTIONS:
                raise ValueError(f"{path} line {line_number} has noncanonical user id convention: {row.get('user_id_convention')}")
            if row.get("item_id_convention") not in ITEM_ID_CONVENTIONS:
                raise ValueError(f"{path} line {line_number} has noncanonical item id convention: {row.get('item_id_convention')}")
            if top_key not in row:
                raise ValueError(f"{path} line {line_number} missing {top_key}")
            rows[user_id] = row
    return rows


def metric_summary(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {metric: sum(float(row[metric]) for row in rows) / len(rows) for metric in METRICS}


def top_ids(row: dict[str, Any], key: str) -> list[int]:
    return [int(value) for value in row.get(key, [])]


def rank_metrics_from_top(target: int, ranked: list[int], miss_rank: int = 101) -> dict[str, float]:
    try:
        rank0 = ranked.index(target)
    except ValueError:
        return {"ndcg10": 0.0, "hr10": 0.0, "rr_proxy": 1.0 / miss_rank, "rank_proxy": float(miss_rank)}
    return {
        "ndcg10": 1.0 / math.log2(rank0 + 2) if rank0 < 10 else 0.0,
        "hr10": 1.0 if rank0 < 10 else 0.0,
        "rr_proxy": 1.0 / (rank0 + 1),
        "rank_proxy": float(rank0 + 1),
    }


def rrf_fusion(hstu_ids: list[int], sasrec_ids: list[int], hstu_weight: float, k: int) -> list[int]:
    scores: dict[int, float] = {}
    for idx, item_id in enumerate(hstu_ids, start=1):
        scores[item_id] = scores.get(item_id, 0.0) + hstu_weight / (k + idx)
    sas_weight = 1.0 - hstu_weight
    for idx, item_id in enumerate(sasrec_ids, start=1):
        scores[item_id] = scores.get(item_id, 0.0) + sas_weight / (k + idx)
    return [item for item, _ in sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hstu-jsonl", required=True)
    parser.add_argument("--sasrec-jsonl", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--posthoc-weights", default="0.0,0.25,0.5,0.75,1.0")
    parser.add_argument("--allow-target-mismatch", action="store_true", help="Exclude and disclose rows whose HSTU and SASRec targets differ.")
    args = parser.parse_args()

    hstu_path = Path(args.hstu_jsonl)
    sasrec_path = Path(args.sasrec_jsonl)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    hstu_by_user = load_rows(hstu_path, "teacher_top_ids")
    sasrec_by_user = load_rows(sasrec_path, "top_ids")
    hstu_users = set(hstu_by_user)
    sasrec_users = set(sasrec_by_user)
    if hstu_users != sasrec_users:
        raise ValueError(
            f"User sets differ: hstu_only={len(hstu_users - sasrec_users)} sasrec_only={len(sasrec_users - hstu_users)}"
        )

    paired_hstu = []
    paired_sasrec = []
    target_mismatches = []
    top10_overlap_sum = 0.0
    top50_overlap_sum = 0.0
    target_sets = {
        "both_top10": 0,
        "hstu_only_top10": 0,
        "sasrec_only_top10": 0,
        "neither_top10": 0,
        "hstu_top50": 0,
        "sasrec_top50": 0,
        "union_top50": 0,
    }
    win_counts = {"hstu_ndcg_better": 0, "sasrec_ndcg_better": 0, "ndcg_tie": 0}
    weights = [float(value) for value in args.posthoc_weights.split(",") if value.strip()]
    fusion_sums = {
        weight: {"ndcg10": 0.0, "hr10": 0.0, "rr_proxy": 0.0, "target_in_union": 0}
        for weight in weights
    }
    oracle_sums = {"ndcg10": 0.0, "hr10": 0.0, "rr_proxy": 0.0}

    for user_id in sorted(hstu_users):
        hstu = hstu_by_user[user_id]
        sasrec = sasrec_by_user[user_id]
        hstu_target = int(hstu["target_item_id"])
        sasrec_target = int(sasrec["target_item_id"])
        if hstu_target != sasrec_target:
            target_mismatches.append({"user_id": user_id, "hstu_target_item_id": hstu_target, "sasrec_target_item_id": sasrec_target})
            continue
        paired_hstu.append(hstu)
        paired_sasrec.append(sasrec)
        hstu_ids = top_ids(hstu, "teacher_top_ids")
        sasrec_ids = top_ids(sasrec, "top_ids")
        hstu_top10 = set(hstu_ids[:10])
        sasrec_top10 = set(sasrec_ids[:10])
        hstu_top50 = set(hstu_ids[:50])
        sasrec_top50 = set(sasrec_ids[:50])
        top10_overlap_sum += len(hstu_top10 & sasrec_top10) / max(1, len(hstu_top10 | sasrec_top10))
        top50_overlap_sum += len(hstu_top50 & sasrec_top50) / max(1, len(hstu_top50 | sasrec_top50))
        hstu_hit10 = hstu_target in hstu_top10
        sasrec_hit10 = hstu_target in sasrec_top10
        if hstu_hit10 and sasrec_hit10:
            target_sets["both_top10"] += 1
        elif hstu_hit10:
            target_sets["hstu_only_top10"] += 1
        elif sasrec_hit10:
            target_sets["sasrec_only_top10"] += 1
        else:
            target_sets["neither_top10"] += 1
        if hstu_target in hstu_top50:
            target_sets["hstu_top50"] += 1
        if hstu_target in sasrec_top50:
            target_sets["sasrec_top50"] += 1
        if hstu_target in (hstu_top50 | sasrec_top50):
            target_sets["union_top50"] += 1
        if float(hstu["ndcg10"]) > float(sasrec["ndcg10"]):
            win_counts["hstu_ndcg_better"] += 1
        elif float(sasrec["ndcg10"]) > float(hstu["ndcg10"]):
            win_counts["sasrec_ndcg_better"] += 1
        else:
            win_counts["ndcg_tie"] += 1

        oracle = max(
            rank_metrics_from_top(hstu_target, hstu_ids[:50]),
            rank_metrics_from_top(hstu_target, sasrec_ids[:50]),
            key=lambda row: (row["ndcg10"], row["rr_proxy"]),
        )
        for key in oracle_sums:
            oracle_sums[key] += oracle[key]

        for weight in weights:
            fused = rrf_fusion(hstu_ids[:50], sasrec_ids[:50], weight, args.rrf_k)
            fused_metrics = rank_metrics_from_top(hstu_target, fused)
            for key in ("ndcg10", "hr10", "rr_proxy"):
                fusion_sums[weight][key] += fused_metrics[key]
            if hstu_target in set(fused):
                fusion_sums[weight]["target_in_union"] += 1

    if target_mismatches and not args.allow_target_mismatch:
        payload = {
            "status": "failed_target_alignment",
            "publication_grade": False,
            "n_total_users": len(hstu_users),
            "target_mismatches": len(target_mismatches),
            "target_mismatches_first20": target_mismatches[:20],
            "required_action": "Investigate split/protocol differences or rerun with --allow-target-mismatch for disclosed diagnostic-only exclusion.",
        }
        (out_dir / "hstu_sasrec_pair_diagnostics.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        raise ValueError(f"Target mismatches between paired HSTU and SASRec records: {target_mismatches[:3]}")

    n = len(paired_hstu)
    if n == 0:
        raise ValueError("No target-matched pairs available for diagnostics")
    hstu_summary = metric_summary(paired_hstu)
    sasrec_summary = metric_summary(paired_sasrec)
    fusion_summary = {
        str(weight): {
            "ndcg10": values["ndcg10"] / n,
            "hr10": values["hr10"] / n,
            "rr_top50_union_proxy": values["rr_proxy"] / n,
            "target_in_fused_union_rate": values["target_in_union"] / n,
        }
        for weight, values in fusion_sums.items()
    }
    payload = {
        "schema_version": 1,
        "status": "complete",
        "publication_grade": False,
        "publication_warning": (
            "Diagnostics pair test-set records. Do not select a fusion weight or train a "
            "student from these test-query teacher outputs and then claim publication evidence."
        ),
        "n_pairs": n,
        "target_alignment": {
            "total_common_users": len(hstu_users),
            "matched_pairs_used": n,
            "target_mismatches_excluded": len(target_mismatches),
            "target_mismatches_first20": target_mismatches[:20],
        },
        "full_input_metrics_before_target_exclusion": {
            "hstu_blair_sm120": metric_summary(list(hstu_by_user.values())),
            "sasrec_sbert_seed101": metric_summary(list(sasrec_by_user.values())),
        },
        "metrics": {
            "hstu_blair_sm120": hstu_summary,
            "sasrec_sbert_seed101": sasrec_summary,
            "sasrec_minus_hstu": {metric: sasrec_summary[metric] - hstu_summary[metric] for metric in METRICS},
            "oracle_best_of_hstu_or_sasrec_top50_upper_bound": {
                "ndcg10": oracle_sums["ndcg10"] / n,
                "hr10": oracle_sums["hr10"] / n,
                "rr_top50_proxy": oracle_sums["rr_proxy"] / n,
            },
            "fixed_rrf_top50_union": fusion_summary,
        },
        "overlap": {
            "mean_top10_jaccard": top10_overlap_sum / n,
            "mean_top50_jaccard": top50_overlap_sum / n,
        },
        "target_membership": target_sets,
        "paired_wins": win_counts,
        "inputs": {
            "hstu_jsonl": sha256_file(hstu_path),
            "sasrec_jsonl": sha256_file(sasrec_path),
        },
    }

    out_json = out_dir / "hstu_sasrec_pair_diagnostics.json"
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# HSTU/SASRec Pair Diagnostics",
        "",
        "This is a diagnostic report, not publication evidence.",
        "",
        f"- Pairs: `{n:,}`",
        f"- Target mismatches excluded: `{len(target_mismatches):,}`",
        f"- HSTU NDCG@10: `{hstu_summary['ndcg10']:.10f}`",
        f"- SASRec NDCG@10: `{sasrec_summary['ndcg10']:.10f}`",
        f"- SASRec minus HSTU NDCG@10: `{sasrec_summary['ndcg10'] - hstu_summary['ndcg10']:.10f}`",
        f"- Mean top-10 Jaccard: `{top10_overlap_sum / n:.6f}`",
        f"- Mean top-50 Jaccard: `{top50_overlap_sum / n:.6f}`",
        "",
        "## Fixed RRF Diagnostics",
        "",
        "| HSTU weight | NDCG@10 | HR@10 | RR proxy |",
        "|---:|---:|---:|---:|",
    ]
    for weight in sorted(fusion_summary, key=float):
        row = fusion_summary[weight]
        lines.append(f"| `{weight}` | `{row['ndcg10']:.10f}` | `{row['hr10']:.10f}` | `{row['rr_top50_union_proxy']:.10f}` |")
    lines.extend(
        [
            "",
            "## Warning",
            "",
            "The fusion weights above are test-set diagnostics. A publishable fusion would need a frozen validation-selected rule and fresh confirmatory records.",
        ]
    )
    (out_dir / "HSTU_SASREC_PAIR_DIAGNOSTICS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "out_json": str(out_json), "n_pairs": n, "hstu_ndcg10": hstu_summary["ndcg10"], "sasrec_ndcg10": sasrec_summary["ndcg10"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
