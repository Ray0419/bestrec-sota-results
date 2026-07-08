"""Export strict HSTU checkpoint records on explicit strict valid/test CSVs.

Run inside the WSL SM120 HSTU-BLaIR environment. This script loads a checkpoint
created by `train_strict_hstu_sm120.py`, evaluates an explicit strict sequence
CSV, translates HSTU user/item ids into canonical BEST-Rec ids, and writes
per-user JSONL records.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import fbgemm_gpu  # noqa: F401
import torch

from generative_recommenders.research.data.eval import get_eval_state
from generative_recommenders.research.indexing.utils import get_top_k_module
from generative_recommenders.research.modeling.sequential.features import (
    movielens_seq_features_from_row,
)
from train_strict_hstu_sm120 import build_model, make_dataset, make_loader


MAX_K = 2500


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


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


def git_output(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception as exc:  # pragma: no cover - diagnostic only
        return f"<git_error {type(exc).__name__}: {exc}>"


def load_map(path: Path, key: str) -> list[int | None]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "complete_bijection":
        raise ValueError(f"{path} status is {payload.get('status')}, expected complete_bijection")
    values = payload.get(key)
    if not isinstance(values, list):
        raise ValueError(f"{path} missing {key}")
    return [None if value is None else int(value) for value in values]


def translate_item(mapping: list[int | None], hstu_one_based: int) -> int:
    if hstu_one_based <= 0 or hstu_one_based >= len(mapping):
        raise ValueError(f"HSTU one-based item id {hstu_one_based} outside map range")
    value = mapping[hstu_one_based]
    if value is None:
        raise ValueError(f"Unmapped HSTU one-based item id {hstu_one_based}")
    return value


def translate_user(mapping: list[int | None], hstu_zero_based: int) -> int:
    if hstu_zero_based < 0 or hstu_zero_based >= len(mapping):
        raise ValueError(f"HSTU user id {hstu_zero_based} outside map range")
    value = mapping[hstu_zero_based]
    if value is None:
        raise ValueError(f"Unmapped HSTU user id {hstu_zero_based}")
    return value


def row_user_ids(row: dict[str, Any]) -> list[int]:
    users = row.get("user_id")
    if isinstance(users, torch.Tensor):
        return [int(value) for value in users.detach().cpu().tolist()]
    return [int(value) for value in users]


def args_from_checkpoint(checkpoint: dict[str, Any], export_args: argparse.Namespace) -> argparse.Namespace:
    config = dict(checkpoint.get("config") or {})
    if not config:
        raise ValueError("Checkpoint missing config")
    config["gin_config_file"] = export_args.gin_config_file or config["gin_config_file"]
    config["text_embeddings"] = export_args.text_embeddings or config["text_embeddings"]
    config["eval_batch_size"] = export_args.eval_batch_size or config["eval_batch_size"]
    config["max_eval_batches"] = export_args.max_eval_batches
    config["num_workers"] = export_args.num_workers
    config["device"] = export_args.device or config.get("device", "cuda")
    return argparse.Namespace(**config)


@torch.inference_mode()
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--split", choices=("valid", "test"), required=True)
    parser.add_argument("--out-jsonl", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--item-map", default="/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_item_alignment_20260609/hstu_bestrec_item_map.json")
    parser.add_argument("--user-map", default="/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/hstu_user_alignment_20260609/hstu_bestrec_user_map.json")
    parser.add_argument("--gin-config-file", default=None)
    parser.add_argument("--text-embeddings", default=None)
    parser.add_argument("--eval-batch-size", type=int, default=0)
    parser.add_argument("--max-eval-batches", type=int, default=0)
    parser.add_argument("--teacher-top-k", type=int, default=50)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--method", default="strict_hstu_sm120")
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    model_args = args_from_checkpoint(checkpoint, args)
    device = torch.device(model_args.device if torch.cuda.is_available() else "cpu")
    item_map = load_map(Path(args.item_map), "hstu_one_based_to_bestrec_zero_based")
    user_map = load_map(Path(args.user_map), "hstu_zero_based_to_bestrec_zero_based")

    dataset = make_dataset(Path(args.csv), model_args.max_sequence_length)
    loader = make_loader(dataset, model_args.eval_batch_size, shuffle=False, num_workers=model_args.num_workers)
    model, sampler, _, interaction_debug = build_model(model_args, device)
    model.load_state_dict({key: value.to(device) for key, value in checkpoint["model_state_dict"].items()}, strict=True)
    model.eval()

    eval_state = get_eval_state(
        model=model,
        all_item_ids=[item_id + 1 for item_id in range(model_args.num_items)],
        negatives_sampler=sampler,
        top_k_module_fn=lambda item_embeddings, item_ids: get_top_k_module(
            top_k_method=model_args.top_k_method,
            model=model,
            item_embeddings=item_embeddings,
            item_ids=item_ids,
        ),
        device=device,
        float_dtype=None,
    )
    out_jsonl = Path(args.out_jsonl)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    total = 0
    ndcg_sum = 0.0
    hr_sum = 0.0
    rr_sum = 0.0
    with out_jsonl.open("w", encoding="utf-8") as handle:
        for batch_idx, row in enumerate(loader):
            if model_args.max_eval_batches and batch_idx >= model_args.max_eval_batches:
                break
            seq_features, target_ids, _ = movielens_seq_features_from_row(
                row,
                device=device,
                max_output_length=model_args.gr_output_length + 1,
            )
            shared_input_embeddings = model.encode(
                past_lengths=seq_features.past_lengths,
                past_ids=seq_features.past_ids,
                past_embeddings=model.get_item_embeddings(seq_features.past_ids),
                past_payloads=seq_features.past_payloads,
            )
            k = min(MAX_K, eval_state.candidate_index.ids.size(1))
            top_ids, top_scores, _ = eval_state.candidate_index.get_top_k_outputs(
                query_embeddings=shared_input_embeddings,
                top_k_module=eval_state.top_k_module,
                k=k,
                invalid_ids=seq_features.past_ids,
                return_embeddings=False,
            )
            _, rank_indices = torch.max(torch.cat([top_ids, target_ids], dim=1) == target_ids, dim=1)
            ranks = torch.where(rank_indices == k, torch.full_like(rank_indices, MAX_K + 1), rank_indices + 1)
            users = row_user_ids(row)
            top_ids_cpu = top_ids.detach().cpu()
            top_scores_cpu = top_scores.detach().cpu()
            target_cpu = target_ids.squeeze(1).detach().cpu()
            for offset, rank_value in enumerate(ranks.detach().cpu().tolist()):
                hstu_user = int(users[offset])
                hstu_target = int(target_cpu[offset].item())
                rank = int(rank_value)
                ndcg10 = 1.0 / math.log2(rank + 1) if rank <= 10 else 0.0
                hr10 = 1.0 if rank <= 10 else 0.0
                rr = 1.0 / rank
                record = {
                    "dataset": "Video_Games",
                    "split": args.split,
                    "fold_id": 0,
                    "seed": int(model_args.seed),
                    "method": args.method,
                    "user_id": translate_user(user_map, hstu_user),
                    "target_item_id": translate_item(item_map, hstu_target),
                    "candidate_scope": "strict_hstu_full_catalog_top2500_rank_proxy",
                    "history_scope": "strict_train_valid_test_protocol",
                    "ndcg10": ndcg10,
                    "hr10": hr10,
                    "rr": rr,
                    "rank": rank,
                    "rank_proxy_max_k": k,
                    "hstu_user_id": hstu_user,
                    "hstu_target_item_id": hstu_target,
                    "item_id_convention": "BEST-Rec canonical item_id",
                    "user_id_convention": "BEST-Rec canonical user_id",
                }
                if args.teacher_top_k:
                    take = min(args.teacher_top_k, top_ids_cpu.shape[1])
                    hstu_top_ids = [int(value) for value in top_ids_cpu[offset, :take].tolist()]
                    record["hstu_teacher_top_ids"] = hstu_top_ids
                    record["teacher_top_ids"] = [translate_item(item_map, item_id) for item_id in hstu_top_ids]
                    record["teacher_top_scores"] = [float(value) for value in top_scores_cpu[offset, :take].tolist()]
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                total += 1
                ndcg_sum += ndcg10
                hr_sum += hr10
                rr_sum += rr

    summary = {
        "schema_version": 1,
        "status": "complete",
        "publication_grade": False,
        "publication_note": "Strict HSTU record export. Publication evidence requires an uncapped full retrain/export under frozen protocol.",
        "started_at_utc": started,
        "generated_at_utc": utc_now(),
        "split": args.split,
        "records": total,
        "metrics": {
            "NDCG@10": ndcg_sum / max(total, 1),
            "HR@10": hr_sum / max(total, 1),
            "MRR": rr_sum / max(total, 1),
        },
        "candidate_scope": "strict_hstu_full_catalog_top2500_rank_proxy",
        "rank_note": "NDCG@10/HR@10 exact for top-10 under top-2500 retrieval; MRR uses rank=2501 miss proxy.",
        "batch_caps": {"max_eval_batches": model_args.max_eval_batches},
        "interaction_debug": interaction_debug,
        "inputs": {
            "checkpoint": sha256_file(checkpoint_path),
            "csv": sha256_file(Path(args.csv)),
            "item_map": sha256_file(Path(args.item_map)),
            "user_map": sha256_file(Path(args.user_map)),
            "gin_config": sha256_file(Path(model_args.gin_config_file)),
            "text_embeddings": sha256_file(Path(model_args.text_embeddings)),
        },
        "outputs": {
            "jsonl": sha256_file(out_jsonl),
        },
        "environment": {
            "python": sys.version,
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "device": str(device),
            "cwd": str(Path.cwd()),
        },
        "source": {
            "source_commit": git_output("rev-parse", "HEAD"),
            "source_status_short": git_output("status", "--short", "--", ".", ":(exclude)tmp", ":(exclude)exps", ":(exclude)ckpts"),
        },
    }
    summary_json = Path(args.summary_json)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
