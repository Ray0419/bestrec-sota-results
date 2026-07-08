"""Export HSTU-BLaIR eval records to BEST-Rec lab JSONL.

Run this from the HSTU-BLaIR source tree inside the WSL SM120 environment. It
does not patch upstream files. The script reconstructs the HSTU model from the
same config, loads a checkpoint, evaluates the full item candidate index, and
writes per-user records for audit/comparison work.

The exported rank is exact for top-10 metrics because the upstream evaluator
retrieves top-2500 candidates. MRR is the upstream top-2500 proxy: misses are
assigned rank 2501.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import fbgemm_gpu  # noqa: F401
import gin
import torch

from generative_recommenders.research.data.eval import get_eval_state
from generative_recommenders.research.data.reco_dataset import get_reco_dataset
from generative_recommenders.research.indexing.utils import get_top_k_module
from generative_recommenders.research.modeling.sequential.autoregressive_losses import (
    LocalTextNegativesSampler,
)
from generative_recommenders.research.modeling.sequential.embedding_modules import (
    ItemEmbeddingWithText,
)
from generative_recommenders.research.modeling.sequential.encoder_utils import (
    get_sequential_encoder,
)
from generative_recommenders.research.modeling.sequential.features import (
    movielens_seq_features_from_row,
)
from generative_recommenders.research.modeling.sequential.input_features_preprocessors import (
    LearnablePositionalEmbeddingWithTextPreprocessor,
)
from generative_recommenders.research.modeling.sequential.output_postprocessors import (
    L2NormEmbeddingPostprocessor,
)
from generative_recommenders.research.modeling.similarity_utils import (
    get_similarity_function,
)
# Import for Gin registration of train_fn.* bindings in the upstream config.
from generative_recommenders.research.trainer import train as _train_configurables  # noqa: F401,E402


MAX_K = 2500


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return record
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    stat = path.stat()
    record.update(
        {
            "sha256": h.hexdigest(),
            "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }
    )
    return record


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def git_output(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception as exc:  # pragma: no cover - diagnostic only
        return f"<git_error {type(exc).__name__}: {exc}>"


def tensor_to_list(value: Any) -> list[Any]:
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().tolist()
    if isinstance(value, list):
        return value
    return list(value)


def strip_ddp_prefix(state_dict: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    if not state_dict:
        return state_dict
    if all(key.startswith("module.") for key in state_dict):
        return {key[len("module.") :]: value for key, value in state_dict.items()}
    return state_dict


def build_hstu_blair_model(args: argparse.Namespace, device: torch.device):
    gin.parse_config_file(args.gin_config_file)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    dataset = get_reco_dataset(
        dataset_name=args.dataset_name,
        text_embedding_model=args.text_embedding_model,
        max_sequence_length=args.max_sequence_length,
        chronological=True,
    )
    assert dataset.text_embedding_dictmat is not None, "BLaIR text embeddings missing"

    embedding_module = ItemEmbeddingWithText(
        num_items=dataset.max_item_id,
        item_embedding_dim=args.item_embedding_dim,
        text_embedding_dim=dataset.text_embedding_dictmat.shape[1],
        text_embeddings=dataset.text_embedding_dictmat.to(device),
    )
    interaction_module, interaction_debug = get_similarity_function(
        module_type=args.interaction_module_type,
        query_embedding_dim=args.item_embedding_dim,
        item_embedding_dim=args.item_embedding_dim,
    )
    input_preproc_module = LearnablePositionalEmbeddingWithTextPreprocessor(
        max_sequence_len=dataset.max_sequence_length + args.gr_output_length + 1,
        embedding_dim=args.item_embedding_dim,
        dropout_rate=args.dropout_rate,
    )
    output_postproc_module = L2NormEmbeddingPostprocessor(
        embedding_dim=args.item_embedding_dim,
        eps=args.l2_norm_eps,
    )
    model = get_sequential_encoder(
        module_type=args.main_module,
        max_sequence_length=dataset.max_sequence_length,
        max_output_length=args.gr_output_length + 1,
        embedding_module=embedding_module,
        interaction_module=interaction_module,
        input_preproc_module=input_preproc_module,
        output_postproc_module=output_postproc_module,
        verbose=True,
    ).to(device)

    checkpoint = torch.load(args.checkpoint, map_location=device)
    state_dict = strip_ddp_prefix(checkpoint["model_state_dict"])
    model.load_state_dict(state_dict, strict=True)
    model.eval()

    negatives_sampler = LocalTextNegativesSampler(
        num_items=dataset.max_item_id,
        item_emb=model._embedding_module._item_emb,
        text_emb=model._embedding_module._text_embeddings,
        text_projection=model._embedding_module._text_projection,
        all_item_ids=dataset.all_item_ids,
        l2_norm=True,
        l2_norm_eps=args.l2_norm_eps,
    ).to(device)
    eval_state = get_eval_state(
        model=model,
        all_item_ids=dataset.all_item_ids,
        negatives_sampler=negatives_sampler,
        top_k_module_fn=lambda item_embeddings, item_ids: get_top_k_module(
            top_k_method=args.top_k_method,
            model=model,
            item_embeddings=item_embeddings,
            item_ids=item_ids,
        ),
        device=device,
        float_dtype=None,
    )
    return dataset, model, eval_state, interaction_debug


@torch.inference_mode()
def eval_batch_records(
    eval_state,
    model,
    seq_features,
    target_ids: torch.Tensor,
    user_max_batch_size: int | None,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    shared_input_embeddings = model.encode(
        past_lengths=seq_features.past_lengths,
        past_ids=seq_features.past_ids,
        past_embeddings=model.get_item_embeddings(seq_features.past_ids),
        past_payloads=seq_features.past_payloads,
    )
    k = min(MAX_K, eval_state.candidate_index.ids.size(1))
    user_max_batch_size = user_max_batch_size or shared_input_embeddings.size(0)
    num_batches = (shared_input_embeddings.size(0) + user_max_batch_size - 1) // user_max_batch_size

    top_ids_all = []
    top_scores_all = []
    for mb in range(num_batches):
        start = mb * user_max_batch_size
        end = (mb + 1) * user_max_batch_size
        top_ids, top_scores, _ = eval_state.candidate_index.get_top_k_outputs(
            query_embeddings=shared_input_embeddings[start:end, ...],
            top_k_module=eval_state.top_k_module,
            k=k,
            invalid_ids=seq_features.past_ids[start:end, :],
            return_embeddings=False,
        )
        top_ids_all.append(top_ids)
        top_scores_all.append(top_scores)
    top_ids = top_ids_all[0] if len(top_ids_all) == 1 else torch.cat(top_ids_all, dim=0)
    top_scores = top_scores_all[0] if len(top_scores_all) == 1 else torch.cat(top_scores_all, dim=0)
    _, rank_indices = torch.max(torch.cat([top_ids, target_ids], dim=1) == target_ids, dim=1)
    ranks = torch.where(rank_indices == k, torch.full_like(rank_indices, MAX_K + 1), rank_indices + 1)
    return ranks, top_ids, top_scores, torch.tensor(k, device=target_ids.device)


def record_user_ids(row: dict[str, Any]) -> list[Any]:
    users = row.get("user_id")
    if isinstance(users, torch.Tensor):
        return users.detach().cpu().tolist()
    if isinstance(users, list):
        return users
    return list(users)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--out-jsonl", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--gin-config-file", default="configs/amzn23_game/hstu-sampled-softmax-n512-blair.gin")
    parser.add_argument("--dataset-name", default="amzn23_game")
    parser.add_argument("--dataset-label", default="Video_Games")
    parser.add_argument("--method", default="hstu_blair_sm120_export")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--text-embedding-model", default="blair")
    parser.add_argument("--max-sequence-length", type=int, default=50)
    parser.add_argument("--eval-batch-size", type=int, default=128)
    parser.add_argument("--eval-user-max-batch-size", type=int, default=128)
    parser.add_argument("--main-module", default="HSTU")
    parser.add_argument("--dropout-rate", type=float, default=0.5)
    parser.add_argument("--item-embedding-dim", type=int, default=64)
    parser.add_argument("--interaction-module-type", default="DotProduct")
    parser.add_argument("--gr-output-length", type=int, default=10)
    parser.add_argument("--l2-norm-eps", type=float, default=1e-6)
    parser.add_argument("--top-k-method", default="MIPSBruteForceTopK")
    parser.add_argument("--limit-batches", type=int, default=0)
    parser.add_argument("--teacher-top-k", type=int, default=0, help="Optionally include top-k ids/scores for distillation.")
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    out_jsonl = Path(args.out_jsonl)
    summary_json = Path(args.summary_json)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    start = utc_now()
    dataset, model, eval_state, interaction_debug = build_hstu_blair_model(args, device)
    loader = torch.utils.data.DataLoader(
        dataset.eval_dataset,
        batch_size=args.eval_batch_size,
        shuffle=False,
        num_workers=0,
    )

    total = 0
    ndcg_sum = 0.0
    hr_sum = 0.0
    rr_sum = 0.0
    with out_jsonl.open("w", encoding="utf-8") as handle:
        for batch_idx, row in enumerate(loader):
            if args.limit_batches and batch_idx >= args.limit_batches:
                break
            seq_features, target_ids, target_ratings = movielens_seq_features_from_row(
                row,
                device=device,
                max_output_length=args.gr_output_length + 1,
            )
            ranks, top_ids, top_scores, k_tensor = eval_batch_records(
                eval_state,
                model,
                seq_features,
                target_ids=target_ids,
                user_max_batch_size=args.eval_user_max_batch_size,
            )
            ranks_cpu = ranks.detach().cpu()
            target_cpu = target_ids.squeeze(1).detach().cpu()
            user_ids = record_user_ids(row)
            top_ids_cpu = top_ids.detach().cpu()
            top_scores_cpu = top_scores.detach().cpu()
            for offset, rank_value in enumerate(ranks_cpu.tolist()):
                rank = int(rank_value)
                ndcg10 = 1.0 / torch.log2(torch.tensor(float(rank + 1))).item() if rank <= 10 else 0.0
                hr10 = 1.0 if rank <= 10 else 0.0
                rr = 1.0 / float(rank)
                record = {
                    "dataset": args.dataset_label,
                    "seed": args.seed,
                    "method": args.method,
                    "user_id": int(user_ids[offset]),
                    "target_item_id": int(target_cpu[offset].item()),
                    "candidate_scope": "hstu_full_catalog_top2500_rank_proxy",
                    "ndcg10": ndcg10,
                    "hr10": hr10,
                    "rr": rr,
                    "rank": rank,
                    "rank_proxy_max_k": int(k_tensor.item()),
                    "item_id_convention": "hstu_one_based_shifted_item_ids",
                }
                if args.teacher_top_k:
                    take = min(args.teacher_top_k, top_ids_cpu.shape[1])
                    record["teacher_top_ids"] = [int(x) for x in top_ids_cpu[offset, :take].tolist()]
                    record["teacher_top_scores"] = [float(x) for x in top_scores_cpu[offset, :take].tolist()]
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                total += 1
                ndcg_sum += ndcg10
                hr_sum += hr10
                rr_sum += rr

    summary = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "started_at_utc": start,
        "dataset": args.dataset_label,
        "method": args.method,
        "seed": args.seed,
        "n_records": total,
        "metrics": {
            "NDCG@10": ndcg_sum / max(total, 1),
            "HR@10": hr_sum / max(total, 1),
            "MRR": rr_sum / max(total, 1),
        },
        "candidate_scope": "hstu_full_catalog_top2500_rank_proxy",
        "rank_note": "NDCG@10/HR@10 exact for top-10 under upstream top-2500 retrieval; MRR uses upstream rank=2501 miss proxy.",
        "config": vars(args),
        "source": {
            "cwd": str(Path.cwd()),
            "source_commit": git_output("rev-parse", "HEAD"),
            "source_status_short": git_output("status", "--short", "--", ".", ":(exclude)tmp", ":(exclude)exps", ":(exclude)ckpts"),
            "interaction_module_debug": interaction_debug,
            "checkpoint": sha256_file(Path(args.checkpoint)),
            "gin_config": sha256_file(Path(args.gin_config_file)),
            "output_jsonl": sha256_file(out_jsonl),
        },
        "environment": {
            "python": sys.version,
            "torch": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda": torch.version.cuda,
            "device": str(device),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
    }
    write_json(summary_json, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
