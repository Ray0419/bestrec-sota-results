"""Train HSTU-BLaIR on strict BEST-Rec-compatible sequence splits.

Run inside the WSL SM120 HSTU-BLaIR environment from the HSTU source checkout.
This script does not patch upstream files. It reuses upstream HSTU modules but
constructs datasets from explicit strict train/valid/test CSVs so validation
targets are not training labels.

The script is intended first as a smoke/dev lane. Full publication evidence
requires a frozen config, full validation/test export, fresh seeds, and strict
comparison gates.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import fbgemm_gpu  # noqa: F401
import gin
import torch

from generative_recommenders.research.data.dataset import DatasetV2
from generative_recommenders.research.data.eval import get_eval_state
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
from generative_recommenders.research.modeling.sequential.losses.sampled_softmax import (
    SampledSoftmaxLoss,
)
from generative_recommenders.research.modeling.sequential.output_postprocessors import (
    L2NormEmbeddingPostprocessor,
)
from generative_recommenders.research.modeling.similarity_utils import (
    get_similarity_function,
)
from generative_recommenders.research.trainer import train as _train_configurables  # noqa: F401,E402


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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def make_dataset(path: Path, max_sequence_length: int) -> DatasetV2:
    return DatasetV2(
        ratings_file=str(path),
        padding_length=max_sequence_length + 1,
        ignore_last_n=0,
        shift_id_by=1,
        chronological=True,
    )


def make_loader(dataset: torch.utils.data.Dataset, batch_size: int, shuffle: bool, num_workers: int) -> torch.utils.data.DataLoader:
    kwargs: dict[str, Any] = {
        "batch_size": batch_size,
        "shuffle": shuffle,
        "num_workers": num_workers,
        "drop_last": False,
    }
    if num_workers:
        kwargs["prefetch_factor"] = 4
    return torch.utils.data.DataLoader(dataset, **kwargs)


def build_model(args: argparse.Namespace, device: torch.device):
    gin.clear_config()
    gin.parse_config_file(args.gin_config_file)
    if args.hstu_linear_dropout_rate is not None:
        gin.bind_parameter("hstu_encoder.linear_dropout_rate", args.hstu_linear_dropout_rate)
    if args.hstu_attn_dropout_rate is not None:
        gin.bind_parameter("hstu_encoder.attn_dropout_rate", args.hstu_attn_dropout_rate)
    if args.hstu_num_blocks is not None:
        gin.bind_parameter("hstu_encoder.num_blocks", args.hstu_num_blocks)
    if args.hstu_num_heads is not None:
        gin.bind_parameter("hstu_encoder.num_heads", args.hstu_num_heads)
    if args.hstu_dv is not None:
        gin.bind_parameter("hstu_encoder.dv", args.hstu_dv)
    if args.hstu_dqk is not None:
        gin.bind_parameter("hstu_encoder.dqk", args.hstu_dqk)
    torch.backends.cuda.matmul.allow_tf32 = args.enable_tf32
    torch.backends.cudnn.allow_tf32 = args.enable_tf32

    text_embeddings = torch.load(args.text_embeddings, map_location="cpu").to(torch.float32)
    embedding_module = ItemEmbeddingWithText(
        num_items=args.num_items,
        item_embedding_dim=args.item_embedding_dim,
        text_embedding_dim=text_embeddings.shape[1],
        text_embeddings=text_embeddings.to(device),
    )
    interaction_module, interaction_debug = get_similarity_function(
        module_type=args.interaction_module_type,
        query_embedding_dim=args.item_embedding_dim,
        item_embedding_dim=args.item_embedding_dim,
    )
    input_preproc_module = LearnablePositionalEmbeddingWithTextPreprocessor(
        max_sequence_len=args.max_sequence_length + args.gr_output_length + 1,
        embedding_dim=args.item_embedding_dim,
        dropout_rate=args.dropout_rate,
    )
    output_postproc_module = L2NormEmbeddingPostprocessor(
        embedding_dim=args.item_embedding_dim,
        eps=args.l2_norm_eps,
    )
    model = get_sequential_encoder(
        module_type=args.main_module,
        max_sequence_length=args.max_sequence_length,
        max_output_length=args.gr_output_length + 1,
        embedding_module=embedding_module,
        interaction_module=interaction_module,
        input_preproc_module=input_preproc_module,
        output_postproc_module=output_postproc_module,
        verbose=True,
    ).to(device)
    sampler = LocalTextNegativesSampler(
        num_items=args.num_items,
        item_emb=model._embedding_module._item_emb,
        text_emb=model._embedding_module._text_embeddings,
        text_projection=model._embedding_module._text_projection,
        all_item_ids=[item_id + 1 for item_id in range(args.num_items)],
        l2_norm=args.item_l2_norm,
        l2_norm_eps=args.l2_norm_eps,
    ).to(device)
    loss_module = SampledSoftmaxLoss(
        num_to_sample=args.num_negatives,
        softmax_temperature=args.temperature,
        model=model,
        activation_checkpoint=False,
    ).to(device)
    return model, sampler, loss_module, interaction_debug


@torch.inference_mode()
def evaluate(model, sampler, loader, args: argparse.Namespace, device: torch.device, split: str) -> dict[str, Any]:
    model.eval()
    eval_state = get_eval_state(
        model=model,
        all_item_ids=[item_id + 1 for item_id in range(args.num_items)],
        negatives_sampler=sampler,
        top_k_module_fn=lambda item_embeddings, item_ids: get_top_k_module(
            top_k_method=args.top_k_method,
            model=model,
            item_embeddings=item_embeddings,
            item_ids=item_ids,
        ),
        device=device,
        float_dtype=None,
    )
    total = 0
    ndcg_sum = 0.0
    hr_sum = 0.0
    rr_sum = 0.0
    started = time.time()
    for batch_idx, row in enumerate(loader):
        if args.max_eval_batches and batch_idx >= args.max_eval_batches:
            break
        seq_features, target_ids, _ = movielens_seq_features_from_row(
            row,
            device=device,
            max_output_length=args.gr_output_length + 1,
        )
        shared_input_embeddings = model.encode(
            past_lengths=seq_features.past_lengths,
            past_ids=seq_features.past_ids,
            past_embeddings=model.get_item_embeddings(seq_features.past_ids),
            past_payloads=seq_features.past_payloads,
        )
        k = min(MAX_K, eval_state.candidate_index.ids.size(1))
        top_ids, _, _ = eval_state.candidate_index.get_top_k_outputs(
            query_embeddings=shared_input_embeddings,
            top_k_module=eval_state.top_k_module,
            k=k,
            invalid_ids=seq_features.past_ids,
            return_embeddings=False,
        )
        _, rank_indices = torch.max(torch.cat([top_ids, target_ids], dim=1) == target_ids, dim=1)
        ranks = torch.where(rank_indices == k, torch.full_like(rank_indices, MAX_K + 1), rank_indices + 1)
        for rank in ranks.detach().cpu().tolist():
            rank = int(rank)
            ndcg_sum += 1.0 / math.log2(rank + 1) if rank <= 10 else 0.0
            hr_sum += 1.0 if rank <= 10 else 0.0
            rr_sum += 1.0 / rank
            total += 1
    return {
        "split": split,
        "records": total,
        "NDCG@10": ndcg_sum / max(total, 1),
        "HR@10": hr_sum / max(total, 1),
        "MRR": rr_sum / max(total, 1),
        "duration_sec": time.time() - started,
        "max_eval_batches": args.max_eval_batches,
    }


def train_one_epoch(model, sampler, loss_module, loader, opt, args: argparse.Namespace, device: torch.device) -> dict[str, Any]:
    model.train()
    total_loss = 0.0
    batches = 0
    positions = 0
    started = time.time()
    for batch_idx, row in enumerate(loader):
        if args.max_train_batches and batch_idx >= args.max_train_batches:
            break
        seq_features, target_ids, _ = movielens_seq_features_from_row(
            row,
            device=device,
            max_output_length=args.gr_output_length + 1,
        )
        seq_features.past_ids.scatter_(
            dim=1,
            index=seq_features.past_lengths.view(-1, 1),
            src=target_ids.view(-1, 1),
        )
        input_embeddings = model.get_item_embeddings(seq_features.past_ids)
        seq_embeddings = model(
            past_lengths=seq_features.past_lengths,
            past_ids=seq_features.past_ids,
            past_embeddings=input_embeddings,
            past_payloads=seq_features.past_payloads,
        )
        supervision_ids = seq_features.past_ids
        sampler = LocalTextNegativesSampler(
            num_items=args.num_items,
            item_emb=model._embedding_module._item_emb,
            text_emb=model._embedding_module._text_embeddings,
            text_projection=model._embedding_module._text_projection,
            all_item_ids=[item_id + 1 for item_id in range(args.num_items)],
            l2_norm=args.item_l2_norm,
            l2_norm_eps=args.l2_norm_eps,
        ).to(device)
        ar_mask = supervision_ids[:, 1:] != 0
        loss, _ = loss_module(
            lengths=seq_features.past_lengths,
            output_embeddings=seq_embeddings[:, :-1, :],
            supervision_ids=supervision_ids[:, 1:],
            supervision_embeddings=input_embeddings[:, 1:, :],
            supervision_weights=ar_mask.float(),
            negatives_sampler=sampler,
            **seq_features.past_payloads,
        )
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        opt.step()
        total_loss += float(loss.detach().cpu().item())
        batches += 1
        positions += int(ar_mask.sum().detach().cpu().item())
    return {
        "train_loss": total_loss / max(batches, 1),
        "batches": batches,
        "positions": positions,
        "duration_sec": time.time() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-csv", required=True)
    parser.add_argument("--valid-csv", required=True)
    parser.add_argument("--test-csv", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--gin-config-file", default="configs/amzn23_game/hstu-sampled-softmax-n512-blair.gin")
    parser.add_argument("--text-embeddings", default="tmp/amzn23_game/item_text_embeddings_blair.pt")
    parser.add_argument("--num-items", type=int, default=25612)
    parser.add_argument("--max-sequence-length", type=int, default=50)
    parser.add_argument("--main-module", default="HSTU")
    parser.add_argument("--dropout-rate", type=float, default=0.5)
    parser.add_argument("--hstu-linear-dropout-rate", type=float, default=None)
    parser.add_argument("--hstu-attn-dropout-rate", type=float, default=None)
    parser.add_argument("--hstu-num-blocks", type=int, default=None)
    parser.add_argument("--hstu-num-heads", type=int, default=None)
    parser.add_argument("--hstu-dv", type=int, default=None)
    parser.add_argument("--hstu-dqk", type=int, default=None)
    parser.add_argument("--item-embedding-dim", type=int, default=64)
    parser.add_argument("--interaction-module-type", default="DotProduct")
    parser.add_argument("--gr-output-length", type=int, default=10)
    parser.add_argument("--l2-norm-eps", type=float, default=1e-6)
    parser.add_argument("--item-l2-norm", action="store_true", default=True)
    parser.add_argument("--top-k-method", default="MIPSBruteForceTopK")
    parser.add_argument("--num-negatives", type=int, default=512)
    parser.add_argument("--temperature", type=float, default=0.05)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--eval-batch-size", type=int, default=128)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--eval-every", type=int, default=1)
    parser.add_argument("--max-train-batches", type=int, default=0)
    parser.add_argument("--max-eval-batches", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260701)
    parser.add_argument("--grad-clip", type=float, default=5.0)
    parser.add_argument("--enable-tf32", action="store_true", default=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--resume-checkpoint", default=None, help="Optional strict_hstu_best_valid.pt checkpoint to continue from with a fresh optimizer.")
    args = parser.parse_args()

    seed_everything(args.seed)
    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    out_dir = Path(args.out_dir)
    if args.run_id is None:
        args.run_id = out_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "run_config.json", vars(args))

    train_dataset = make_dataset(Path(args.train_csv), args.max_sequence_length)
    valid_dataset = make_dataset(Path(args.valid_csv), args.max_sequence_length)
    test_dataset = make_dataset(Path(args.test_csv), args.max_sequence_length)
    train_loader = make_loader(train_dataset, args.batch_size, shuffle=True, num_workers=args.num_workers)
    valid_loader = make_loader(valid_dataset, args.eval_batch_size, shuffle=False, num_workers=args.num_workers)
    test_loader = make_loader(test_dataset, args.eval_batch_size, shuffle=False, num_workers=args.num_workers)
    model, sampler, loss_module, interaction_debug = build_model(args, device)
    resume_info = None
    if args.resume_checkpoint:
        resume_path = Path(args.resume_checkpoint)
        payload = torch.load(resume_path, map_location="cpu")
        state = payload.get("model_state_dict")
        if not isinstance(state, dict):
            raise ValueError(f"Resume checkpoint has no model_state_dict: {resume_path}")
        model.load_state_dict({key: value.to(device) for key, value in state.items()})
        resume_info = {
            "path": str(resume_path),
            "sha256": sha256_file(resume_path).get("sha256"),
            "source_run_id": payload.get("run_id"),
            "source_best_epoch": payload.get("best_epoch"),
            "source_best_valid": payload.get("best_valid"),
            "source_test_metrics": payload.get("test_metrics"),
            "optimizer_state": "not_available_fresh_optimizer_started",
        }
    opt = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, betas=(0.9, 0.98), weight_decay=args.weight_decay)

    history = []
    best_valid = None
    best_epoch = None
    best_state = None
    started = utc_now()
    if resume_info is not None:
        initial_valid = evaluate(model, sampler, valid_loader, args, device, "valid_resume_epoch0")
        best_valid = initial_valid
        best_epoch = 0
        best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        epoch0_record = {
            "epoch": 0,
            "resume_checkpoint_eval": True,
            "valid": initial_valid,
        }
        history.append(epoch0_record)
        print(json.dumps(epoch0_record, sort_keys=True), flush=True)
    for epoch in range(1, args.epochs + 1):
        epoch_record: dict[str, Any] = {"epoch": epoch}
        epoch_record.update(train_one_epoch(model, sampler, loss_module, train_loader, opt, args, device))
        if epoch % args.eval_every == 0 or epoch == args.epochs:
            valid_metrics = evaluate(model, sampler, valid_loader, args, device, "valid")
            epoch_record["valid"] = valid_metrics
            if best_valid is None or valid_metrics["NDCG@10"] > best_valid["NDCG@10"]:
                best_valid = valid_metrics
                best_epoch = epoch
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        history.append(epoch_record)
        print(json.dumps(epoch_record, sort_keys=True), flush=True)

    if best_state is not None:
        model.load_state_dict({key: value.to(device) for key, value in best_state.items()})
    test_metrics = evaluate(model, sampler, test_loader, args, device, "test")
    checkpoint_path = out_dir / "strict_hstu_best_valid.pt"
    torch.save(
        {
            "model_state_dict": {key: value.detach().cpu() for key, value in model.state_dict().items()},
            "run_id": args.run_id,
            "checkpoint_role": "best_valid",
            "best_epoch": best_epoch,
            "resume_info": resume_info,
            "saved_at_utc": utc_now(),
            "config": vars(args),
            "best_valid": best_valid,
            "test_metrics": test_metrics,
        },
        checkpoint_path,
    )
    summary = {
        "schema_version": 1,
        "status": "complete",
        "publication_grade": False,
        "publication_note": "Strict HSTU smoke/dev lane. Full publication evidence requires full epochs, no batch caps, fresh seeds, and canonical per-user exports.",
        "batch_caps": {
            "max_train_batches": args.max_train_batches,
            "max_eval_batches": args.max_eval_batches,
        },
        "known_caveats": [
            "SM120 CUDA 12.8 compatibility environment, not faithful upstream pinned torch==2.2.2+cu121.",
            "fbgemm dense_to_jagged and jagged_to_padded_dense autograd warnings may appear under torch==2.8.0+cu128.",
            "This trainer is single-GPU and lab-side; it does not patch upstream HSTU files.",
        ],
        "started_at_utc": started,
        "generated_at_utc": utc_now(),
        "history": history,
        "best_epoch": best_epoch,
        "best_valid": best_valid,
        "test": test_metrics,
        "resume_info": resume_info,
        "interaction_debug": interaction_debug,
        "gin_effective_config": gin.config_str(),
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
        "inputs": {
            "train_csv": sha256_file(Path(args.train_csv)),
            "valid_csv": sha256_file(Path(args.valid_csv)),
            "test_csv": sha256_file(Path(args.test_csv)),
            "gin_config": sha256_file(Path(args.gin_config_file)),
            "text_embeddings": sha256_file(Path(args.text_embeddings)),
        },
        "outputs": {
            "checkpoint": sha256_file(checkpoint_path),
        },
    }
    summary_path = out_dir / "strict_hstu_train_summary.json"
    write_json(summary_path, summary)
    manifest = {
        "schema_version": 1,
        "command": f"{sys.executable} " + " ".join(sys.argv),
        "argv": sys.argv,
        "environment": summary["environment"],
        "run_config": sha256_file(out_dir / "run_config.json"),
        "summary": sha256_file(summary_path),
        "checkpoint": sha256_file(checkpoint_path),
    }
    write_json(out_dir / "results_manifest.json", manifest)
    print(json.dumps({"summary": str(summary_path), "best_valid": best_valid, "test": test_metrics}, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
