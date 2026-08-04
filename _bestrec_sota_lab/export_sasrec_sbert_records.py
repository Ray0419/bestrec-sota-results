"""Train SASRec-SBERT and export canonical per-user full-catalog records.

This lab-side runner imports `_bestrec_run/run_sasrec_sbert.py` read-only. It
exists because the historical SASRec summaries do not contain per-user records
or checkpoints, so they cannot be fairly paired with HSTU-BLaIR records for
strict review, significance testing, or ensemble diagnostics.

The script does not consume HSTU teacher predictions during training. Teacher
artifacts may be paired only after export for diagnostics unless a future
protocol creates separate validation-query teacher labels.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "_bestrec_run"
sys.path.insert(0, str(RUN_DIR))

import run_sasrec_sbert as sasrec  # noqa: E402


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


def state_dict_to_cpu(model: torch.nn.Module) -> dict[str, torch.Tensor]:
    return {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}


def build_lr_scheduler(args: argparse.Namespace, opt: torch.optim.Optimizer, n_batches: int):
    if args.lr_schedule != "warmup_cosine":
        return None
    total_steps = args.epochs * n_batches
    warmup_steps = max(1, int(0.05 * total_steps))
    cosine_steps = max(1, total_steps - warmup_steps)
    warmup = torch.optim.lr_scheduler.LinearLR(opt, start_factor=1e-3, end_factor=1.0, total_iters=warmup_steps)
    cosine = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cosine_steps, eta_min=0)
    return torch.optim.lr_scheduler.SequentialLR(opt, schedulers=[warmup, cosine], milestones=[warmup_steps])


def environment_record(device: str) -> dict[str, Any]:
    record: dict[str, Any] = {
        "python": sys.version,
        "python_executable": sys.executable,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "device": device,
        "cwd": str(Path.cwd()),
    }
    if torch.cuda.is_available():
        record["cuda_device"] = torch.cuda.get_device_name(0)
    return record


def load_problem(args: argparse.Namespace):
    train_csv = sasrec.SPLIT_DIR / f"{args.category}.train.csv"
    valid_csv = sasrec.SPLIT_DIR / f"{args.category}.valid.csv"
    test_csv = sasrec.SPLIT_DIR / f"{args.category}.test.csv"
    encoder_cache = Path(args.encoder_cache) if args.encoder_cache else sasrec.EMB_CACHE_DIR / f"sbert_titles_{args.category}.npy"
    for path in (train_csv, valid_csv, test_csv):
        if not path.exists():
            raise FileNotFoundError(path)
    if not args.no_sbert and not encoder_cache.exists():
        raise FileNotFoundError(encoder_cache)

    train_rows = sasrec.load_split_csv(train_csv)
    valid_rows = sasrec.load_split_csv(valid_csv)
    test_rows = sasrec.load_split_csv(test_csv)
    train_inters, valid_inters, test_inters, user_list, item_list = sasrec.reindex(train_rows, valid_rows, test_rows)
    n_items = len(item_list)
    pad_id = n_items
    user_seqs = sasrec.build_user_sequences(train_inters)

    sbert_emb = None
    if not args.no_sbert:
        sbert_emb = np.load(encoder_cache).astype(np.float32)
        if sbert_emb.shape[0] != n_items:
            sbert_emb = sbert_emb[:n_items]

    return {
        "paths": {
            "train_csv": train_csv,
            "valid_csv": valid_csv,
            "test_csv": test_csv,
            "encoder_cache": encoder_cache if not args.no_sbert else None,
        },
        "train_inters": train_inters,
        "valid_inters": valid_inters,
        "test_inters": test_inters,
        "user_list": user_list,
        "item_list": item_list,
        "n_items": n_items,
        "pad_id": pad_id,
        "user_seqs": user_seqs,
        "sbert_emb": sbert_emb,
    }


def make_model(args: argparse.Namespace, problem: dict[str, Any], device: str) -> torch.nn.Module:
    return sasrec.SASRecSBERT(
        n_items=problem["n_items"],
        pad_id=problem["pad_id"],
        max_seq_len=args.max_seq_len,
        d_model=args.d_model,
        n_layers=args.n_layers,
        n_heads=args.n_heads,
        dropout=args.dropout,
        sbert_emb=problem["sbert_emb"],
        sbert_only=args.sbert_only,
        mlp_adaptor=args.mlp_adaptor,
        mlp_hidden=args.mlp_hidden,
        mlp_dropout=args.mlp_dropout,
    ).to(device)


def export_records(
    model: torch.nn.Module,
    problem: dict[str, Any],
    eval_inters: list[tuple[int, int, float, int]],
    out_jsonl: Path,
    args: argparse.Namespace,
    device: str,
    split: str,
    extra_history: dict[int, list[int]] | None = None,
) -> dict[str, Any]:
    model.eval()
    test_dict = {u: i for u, i, _, _ in eval_inters}
    users = sorted(test_dict.keys())
    if args.export_limit_users and args.export_limit_users < len(users):
        users = users[: args.export_limit_users]
    n_items = problem["n_items"]
    pad_id = problem["pad_id"]
    user_seqs = problem["user_seqs"]
    extra = extra_history or {}
    top_k_take = max(10, args.export_top_k)
    metric_sums = {"ndcg10": 0.0, "hr10": 0.0, "rr": 0.0}
    records = 0
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()

    with torch.no_grad(), out_jsonl.open("w", encoding="utf-8") as handle:
        all_items = model.all_item_features()
        for start in range(0, len(users), args.eval_batch_size):
            batch_users = users[start : start + args.eval_batch_size]
            input_ids = torch.full((len(batch_users), args.max_seq_len), pad_id, dtype=torch.long, device=device)
            train_items: list[list[int]] = []
            real_len: list[int] = []
            for row_idx, user_id in enumerate(batch_users):
                seq = list(user_seqs.get(user_id, []))
                if user_id in extra:
                    seq = seq + list(extra[user_id])
                train_items.append(seq)
                truncated = seq[-args.max_seq_len :]
                if truncated:
                    input_ids[row_idx, : len(truncated)] = torch.tensor(truncated, dtype=torch.long, device=device)
                real_len.append(len(truncated))

            hidden = model.encode(input_ids)
            last_real_pos = torch.tensor([max(0, length - 1) for length in real_len], device=device)
            last_h = hidden[torch.arange(len(batch_users), device=device), last_real_pos, :]
            scores = last_h @ all_items.T
            for row_idx, items in enumerate(train_items):
                if items:
                    scores[row_idx, items] = -float("inf")
            top_scores, top_ids = torch.topk(scores, k=top_k_take, dim=1)

            for row_idx, user_id in enumerate(batch_users):
                target = int(test_dict[user_id])
                if real_len[row_idx] == 0:
                    rank0 = n_items
                    ndcg10 = hr10 = rr = 0.0
                else:
                    target_score = scores[row_idx, target].item()
                    rank0 = int((scores[row_idx] > target_score).sum().item())
                    if rank0 < 10:
                        ndcg10 = 1.0 / math.log2(rank0 + 2)
                        hr10 = 1.0
                    else:
                        ndcg10 = 0.0
                        hr10 = 0.0
                    rr = 1.0 / (rank0 + 1)
                metric_sums["ndcg10"] += ndcg10
                metric_sums["hr10"] += hr10
                metric_sums["rr"] += rr
                record = {
                    "dataset": args.category,
                    "split": split,
                    "fold_id": 0,
                    "seed": args.seed,
                    "method": args.method,
                    "evidence_stage": args.evidence_stage,
                    "evidence_scope": args.evidence_scope,
                    "publication_grade": bool(args.publication_grade),
                    "user_id": int(user_id),
                    "target_item_id": target,
                    "candidate_scope": "full_catalog_history_masked",
                    "history_scope": "train_plus_valid" if extra_history else "train",
                    "ndcg10": ndcg10,
                    "hr10": hr10,
                    "rr": rr,
                    "rank": rank0 + 1,
                    "item_id_convention": "bestrec_zero_based_item_ids",
                    "user_id_convention": "bestrec_zero_based_user_ids",
                }
                if args.export_top_k:
                    take = min(args.export_top_k, top_ids.shape[1])
                    record["top_ids"] = [int(value) for value in top_ids[row_idx, :take].detach().cpu().tolist()]
                    record["top_scores"] = [float(value) for value in top_scores[row_idx, :take].detach().cpu().tolist()]
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                records += 1

    return {
        "records": records,
        "metrics": {name: total / records for name, total in metric_sums.items()},
        "duration_sec": time.time() - started,
        "output_jsonl": sha256_file(out_jsonl),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", default="Video_Games")
    parser.add_argument("--run-id", default=f"sasrec_sbert_export_{int(time.time())}")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--eval-batch-size", type=int, default=512)
    parser.add_argument("--max-seq-len", type=int, default=50)
    parser.add_argument("--d-model", type=int, default=64)
    parser.add_argument("--n-layers", type=int, default=2)
    parser.add_argument("--n-heads", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--lr-schedule", choices=("none", "warmup_cosine"), default="warmup_cosine")
    parser.add_argument("--no-sbert", action="store_true")
    parser.add_argument("--sbert-only", action="store_true")
    parser.add_argument("--encoder-cache", default=None)
    parser.add_argument("--mlp-adaptor", action="store_true")
    parser.add_argument("--mlp-hidden", type=int, default=300)
    parser.add_argument("--mlp-dropout", type=float, default=0.2)
    parser.add_argument("--chunked-full-softmax", action="store_true", default=True)
    parser.add_argument("--item-chunk", type=int, default=32768)
    parser.add_argument("--augment-factor", type=int, default=1)
    parser.add_argument("--eval-every", type=int, default=1)
    parser.add_argument("--eval-subsample", type=int, default=512)
    parser.add_argument("--export-split", choices=("valid", "test"), default="test")
    parser.add_argument("--export-limit-users", type=int, default=128)
    parser.add_argument("--export-top-k", type=int, default=0)
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--method", default="sasrec_sbert_lab_export")
    parser.add_argument("--evidence-stage", choices=("smoke", "development", "confirmatory"), default="development")
    parser.add_argument("--evidence-scope", default="lab_side_sasrec_full_catalog_export")
    parser.add_argument("--protocol-manifest", default=None)
    parser.add_argument("--claim-scope", default="not_a_broad_sota_claim")
    parser.add_argument("--publication-grade", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    out_dir = ROOT / "_bestrec_sota_lab" / "runs" / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "run_config.json").write_text(json.dumps(vars(args), indent=2, sort_keys=True), encoding="utf-8")

    device = sasrec.DEVICE
    problem = load_problem(args)
    model = make_model(args, problem, device)
    n_params = sum(param.numel() for param in model.parameters())
    dataset = sasrec.SASRecDataset(problem["user_seqs"], args.max_seq_len, problem["n_items"], problem["pad_id"], augment_factor=args.augment_factor)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0, collate_fn=sasrec.collate_batch, drop_last=False)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-5)
    scheduler = build_lr_scheduler(args, opt, len(loader))

    history = []
    best_state = state_dict_to_cpu(model)
    best_val_ndcg = -1.0
    for epoch in range(1, args.epochs + 1):
        start = time.time()
        train_loss, n_positions = sasrec.train_one_epoch(
            model,
            loader,
            opt,
            problem["pad_id"],
            device,
            chunked_full_softmax=args.chunked_full_softmax,
            item_chunk=args.item_chunk,
            scheduler=scheduler,
        )
        entry: dict[str, Any] = {
            "epoch": epoch,
            "train_loss": train_loss,
            "train_positions": n_positions,
            "epoch_time_s": time.time() - start,
        }
        if epoch % args.eval_every == 0 or epoch == args.epochs:
            val_metrics = sasrec.evaluate(
                model,
                problem["user_seqs"],
                problem["valid_inters"],
                problem["n_items"],
                problem["pad_id"],
                args.max_seq_len,
                device,
                batch_size=args.eval_batch_size,
                subsample_users=args.eval_subsample,
                subsample_seed=args.seed + epoch,
            )
            entry["val"] = val_metrics
            if val_metrics["NDCG@10"] > best_val_ndcg:
                best_val_ndcg = val_metrics["NDCG@10"]
                best_state = state_dict_to_cpu(model)
        history.append(entry)
        print(json.dumps(entry, sort_keys=True))

    checkpoint_path = out_dir / "sasrec_sbert_best_val.pt"
    torch.save(
        {
            "state_dict": best_state,
            "config": vars(args),
            "best_val_NDCG10": best_val_ndcg,
            "n_items": problem["n_items"],
            "pad_id": problem["pad_id"],
        },
        checkpoint_path,
    )
    model.load_state_dict({key: value.to(device) for key, value in best_state.items()})

    valid_dict = {u: i for u, i, _, _ in problem["valid_inters"]}
    extra_history = {u: [i] for u, i in valid_dict.items()} if args.export_split == "test" else None
    eval_inters = problem["test_inters"] if args.export_split == "test" else problem["valid_inters"]
    records_path = out_dir / f"warm_full_catalog_records_{args.category}_sasrec_sbert_{args.export_split}.jsonl"
    export_summary = export_records(model, problem, eval_inters, records_path, args, device, args.export_split, extra_history=extra_history)

    summary = {
        "schema_version": 1,
        "status": "complete",
        "evidence_stage": args.evidence_stage,
        "evidence_scope": args.evidence_scope,
        "claim_scope": args.claim_scope,
        "publication_grade": bool(args.publication_grade),
        "publication_note": (
            "Lab-side SASRec export. A full-publication claim additionally requires "
            "a protocol manifest, uncapped export, complete comparator coverage, and "
            "the external publication gate to pass."
        ),
        "category": args.category,
        "method": args.method,
        "device": device,
        "environment": environment_record(device),
        "seed": args.seed,
        "n_users": len(problem["user_list"]),
        "n_items": problem["n_items"],
        "n_params": n_params,
        "best_val_NDCG10": best_val_ndcg,
        "history": history,
        "export": export_summary,
        "checkpoint": sha256_file(checkpoint_path),
        "inputs": {name: sha256_file(path) for name, path in problem["paths"].items() if path is not None},
        "protocol_manifest": sha256_file(Path(args.protocol_manifest)) if args.protocol_manifest else None,
        "teacher_artifact_policy": "No HSTU teacher predictions are consumed during training or model selection in this script.",
    }
    summary_path = out_dir / "sasrec_sbert_export_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "command": f"{sys.executable} " + " ".join(sys.argv),
        "argv": sys.argv,
        "cwd": str(Path.cwd()),
        "environment": environment_record(device),
        "generated_at_unix": time.time(),
        "artifacts": {
            "run_config": sha256_file(out_dir / "run_config.json"),
            "summary": sha256_file(summary_path),
            "checkpoint": sha256_file(checkpoint_path),
            "records": sha256_file(records_path),
        },
    }
    (out_dir / "results_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"run_id": args.run_id, "summary": str(summary_path), "records": str(records_path), "metrics": export_summary["metrics"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
