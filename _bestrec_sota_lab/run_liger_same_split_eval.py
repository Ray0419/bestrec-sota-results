"""Train/evaluate LIGER-style dense retrieval on exported BEST-Rec folds.

This lab runner consumes `_bestrec_sota_lab/run_liger_same_split_export.py`
outputs, uses official modules from `external/liger` for RQ-VAE semantic IDs,
TIGER model construction, model forwarding, and dense target scoring, then
writes canonical full-catalog JSONL records.

Tiny `--train-steps`/`--rqvae-epochs` smoke runs are useful for validating the
adapter only. Publication-grade use requires a frozen full configuration and all
strict datasets/seeds/folds.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from torch.nn.utils import clip_grad_norm_
from torch.utils.data import DataLoader
from transformers import T5Config

from sota_common import CONFIRMATORY_SEEDS_CSV, DATASETS, ROOT, RUNS_DIR, append_jsonl, make_item_kfold, make_lab_run_dir, parse_csv, utc_now, write_json
from protocol import load_protocol
from run_all_confirmatory import load_dataset, user_train_and_test
from v5_utils import NUM_FOLDS


LIGER_DIR = ROOT / "external" / "liger"
TOP_K = 10


def seed_everything(modules: dict[str, Any], seed: int) -> None:
    """Seed all RNGs used by the LIGER adapter before model construction."""
    modules["set_seed"](int(seed))
    random.seed(int(seed))
    np.random.seed(int(seed) % (2**32 - 1))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))


class NoopWriter:
    def log(self, payload: dict[str, Any]) -> None:
        return None

    def finish(self) -> None:
        return None


def import_liger_modules() -> dict[str, Any]:
    if not LIGER_DIR.exists():
        raise FileNotFoundError(f"official LIGER checkout not found: {LIGER_DIR}")
    sys.path.insert(0, str(LIGER_DIR))
    from ID_generation.rqvae.rqvae import RQVAE  # type: ignore
    from ID_generation.train_rqvae import train_rqvae  # type: ignore
    from ID_generation.utils import process_data_split  # type: ignore
    from src.evaluation import get_target_embed, model_forward  # type: ignore
    from src.load_data import load_data  # type: ignore
    from src.tiger import TIGER  # type: ignore
    from utils import CustomDataset, set_seed  # type: ignore

    return {
        "CustomDataset": CustomDataset,
        "RQVAE": RQVAE,
        "TIGER": TIGER,
        "get_target_embed": get_target_embed,
        "load_data": load_data,
        "model_forward": model_forward,
        "process_data_split": process_data_split,
        "set_seed": set_seed,
        "train_rqvae": train_rqvae,
    }


def parse_target_map(path: Path, limit: int = 0) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            out.append(json.loads(line))
            if limit and len(out) >= limit:
                break
    return out


def count_existing_records(record_path: Path, method: str = "tiger_liger_retrieval") -> dict[tuple[int, int], int]:
    counts: dict[tuple[int, int], int] = {}
    if not record_path.exists():
        return counts
    with record_path.open("r", encoding="utf-8") as f:
        for line in f:
            if f'"method": "{method}"' not in line:
                continue
            row = json.loads(line)
            if row.get("method") != method:
                continue
            key = (int(row["seed"]), int(row["fold_id"]))
            counts[key] = counts.get(key, 0) + 1
    return counts


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def group_fold_train(dataset: str, seed: int, fold_id: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    interactions, _, _, n_items, _ = load_dataset(dataset)
    splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
    tr_idx, te_idx, _ = splits[fold_id]
    train_inters = [interactions[i] for i in tr_idx]
    test_inters = [interactions[i] for i in te_idx]
    return train_inters, test_inters, n_items


def make_rqvae_ids(
    *,
    modules: dict[str, Any],
    item_embedding: torch.Tensor,
    seen_liger_ids: np.ndarray,
    id_save_path: Path,
    device: torch.device,
    seed: int,
    rqvae_epochs: int,
    codebook_size: int,
    latent_dim: int,
    batch_size: int,
) -> dict[str, Any]:
    if id_save_path.exists():
        ids = pickle.loads(id_save_path.read_bytes())
        return {"semantic_id_file": str(id_save_path), "status": "cached", "shape": list(np.asarray(ids).shape)}

    seed_everything(modules, seed)
    input_dim = int(item_embedding.shape[1])
    hidden_mid = max(latent_dim * 2, min(input_dim, 256))
    hidden_sizes = [input_dim, hidden_mid]
    cfg = {
        "optimizer": "AdamW",
        "weight_decay": 0.01,
        "batch_size": int(batch_size),
        "epochs": int(rqvae_epochs),
        "lr": 1e-3,
        "beta": 0.25,
        "input_dim": input_dim,
        "hidden_dim": hidden_sizes,
        "latent_dim": int(latent_dim),
        "num_layers": 3,
        "dropout": 0.1,
        "code_book_size": int(codebook_size),
        "max_seq_len": 256,
        "val_ratio": 0.05,
    }
    rqvae = modules["RQVAE"](
        input_dim,
        list(hidden_sizes),
        int(latent_dim),
        3,
        int(codebook_size),
        0.1,
        latent_loss_weight=0.25,
    )
    seen_tensor = item_embedding[seen_liger_ids - 1].to(device)
    modules["train_rqvae"](rqvae, seen_tensor, device, NoopWriter(), cfg)
    rqvae.to(device)
    rqvae.eval()
    with torch.no_grad():
        ids = rqvae.get_codes(item_embedding.to(device)).detach().cpu().numpy()
    id_save_path.parent.mkdir(parents=True, exist_ok=True)
    with id_save_path.open("wb") as f:
        pickle.dump(ids, f)
    return {"semantic_id_file": str(id_save_path), "status": "trained", "shape": list(ids.shape), "config": cfg}


def method_config(embedding_dim: int, mode: str) -> dict[str, Any]:
    if mode == "tiger":
        return {
            "include_user_id": False,
            "use_id": "sid",
            "flag_add_input_embedding": False,
            "flag_use_output_embedding": False,
            "embedding_loss_weight": 0,
            "sid_loss_weight": 1,
            "evaluation_method": "default",
            "embedding_head_dict": {
                "use_new_init": False,
                "embed_target": "ground_truth",
                "embed_proj_type": "mlp",
            },
        }
    return {
        "include_user_id": False,
        "use_id": "sid",
        "flag_add_input_embedding": True,
        "flag_use_output_embedding": True,
        "embedding_loss_weight": 1,
        "sid_loss_weight": 1,
        "evaluation_method": "dense",
        "embedding_head_dict": {
            "use_new_init": False,
            "embed_target": "ground_truth",
            "embed_proj_type": "mlp",
            "normalize_logits": True,
            "logits_temperature": 0.07,
            "text_embedding_dim": int(embedding_dim),
            "hidden_sizes": [128, 128],
            "embd_proj_dropout_rate": 0.1,
            "embd_proj_in_dropout_rate": 0.05,
        },
    }


def build_model(
    *,
    modules: dict[str, Any],
    vocab_size: int,
    n_positions: int,
    n_semantic_codebook: int,
    max_items_per_seq: int,
    mode_config: dict[str, Any],
    d_model: int,
) -> Any:
    t5_config = T5Config(
        num_layers=1,
        num_decoder_layers=1,
        d_model=int(d_model),
        d_ff=max(128, int(d_model) * 4),
        num_heads=4,
        d_kv=max(16, int(d_model) // 4),
        dropout_rate=0.1,
        vocab_size=int(vocab_size),
        pad_token_id=0,
        eos_token_id=int(vocab_size - 1),
        decoder_start_token_id=0,
        feed_forward_proj="relu",
        n_positions=int(n_positions),
        layer_norm_epsilon=1e-8,
        initializer_factor=0.02,
    )
    return modules["TIGER"](
        config=t5_config,
        n_semantic_codebook=int(n_semantic_codebook),
        max_items_per_seq=int(max_items_per_seq),
        flag_use_output_embedding=bool(mode_config["flag_use_output_embedding"]),
        flag_use_learnable_text_embed=bool(mode_config["flag_add_input_embedding"]),
        embedding_head_dict=mode_config["embedding_head_dict"],
    )


def train_liger_dense(
    *,
    modules: dict[str, Any],
    model: Any,
    training_data: dict[str, Any],
    item_embedding: torch.Tensor,
    item2sid: np.ndarray,
    seen_liger_ids: np.ndarray,
    mode_config: dict[str, Any],
    device: torch.device,
    train_steps: int,
    batch_size: int,
    lr: float,
    seed: int,
) -> dict[str, Any]:
    seed_everything(modules, seed)
    dataset = modules["CustomDataset"](training_data)
    loader = DataLoader(dataset, batch_size=int(batch_size), shuffle=True)
    if len(loader) == 0 or train_steps <= 0:
        return {"status": "skipped", "steps": 0, "loss": None}
    model.to(device)
    model.train()
    item_embedding = item_embedding.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(lr), weight_decay=0.01)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    unseen_liger_ids = np.setdiff1d(np.arange(item2sid.shape[0]) + 1, seen_liger_ids)
    global_step = 0
    last_loss = None
    while global_step < train_steps:
        for batch in loader:
            if global_step >= train_steps:
                break
            optimizer.zero_grad(set_to_none=True)
            outputs, _ = modules["model_forward"](model, batch, device, int(item2sid.shape[1]), mode_config)
            loss = outputs.loss * float(mode_config["sid_loss_weight"])
            if mode_config["flag_use_output_embedding"]:
                predicted_embedding = model.predicted_embedding
                _, logits = modules["get_target_embed"](predicted_embedding, model, mode_config, item_embedding)
                logits_label = batch["labels_ids"][:, 0].to(device) - 1
                if len(unseen_liger_ids):
                    logits[:, unseen_liger_ids - 1] = -100
                embed_loss = F.cross_entropy(logits, logits_label)
                loss = loss + embed_loss * float(mode_config["embedding_loss_weight"])
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            global_step += 1
            last_loss = float(loss.detach().cpu())
    return {"status": "trained", "steps": int(global_step), "loss": last_loss}


def score_records(
    *,
    modules: dict[str, Any],
    model: Any,
    unseen_test_data: dict[str, Any],
    target_rows: list[dict[str, Any]],
    train_inters: list[dict[str, Any]],
    item_embedding: torch.Tensor,
    item2sid: np.ndarray,
    mode_config: dict[str, Any],
    dataset: str,
    seed: int,
    fold_id: int,
    device: torch.device,
    batch_size: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not mode_config["flag_use_output_embedding"]:
        raise ValueError("canonical full-catalog scoring currently requires LIGER dense output embeddings")
    if len(target_rows) > len(unseen_test_data["input_ids"]):
        raise ValueError("target map has more rows than LIGER unseen_test_data")
    limited_data = {k: v[: len(target_rows)] for k, v in unseen_test_data.items()}
    loader = DataLoader(modules["CustomDataset"](limited_data), batch_size=int(batch_size), shuffle=False)
    user_train, _ = user_train_and_test(train_inters, [])
    item_embedding = item_embedding.to(device)
    model.to(device)
    model.eval()
    records: list[dict[str, Any]] = []
    ndcg: list[float] = []
    hr: list[float] = []
    rr: list[float] = []
    row_offset = 0
    with torch.no_grad():
        for batch in loader:
            _, _ = modules["model_forward"](model, batch, device, int(item2sid.shape[1]), mode_config)
            predicted_embedding = model.predicted_embedding
            _, logits = modules["get_target_embed"](predicted_embedding, model, mode_config, item_embedding)
            scores = logits.detach().float().cpu().numpy()
            for local_idx in range(scores.shape[0]):
                meta = target_rows[row_offset + local_idx]
                user_id = int(meta["original_user_id"])
                target_item = int(meta["target_item_id"])
                row_scores = scores[local_idx].copy()
                seen = user_train.get(user_id, set())
                if seen:
                    row_scores[list(seen)] = -np.inf
                target_score = row_scores[target_item]
                rank0 = int((row_scores > target_score).sum())
                h = 1.0 if rank0 < TOP_K else 0.0
                n = 1.0 / math.log2(rank0 + 2) if rank0 < TOP_K else 0.0
                r = 1.0 / (rank0 + 1)
                ndcg.append(n)
                hr.append(h)
                rr.append(r)
                records.append(
                    {
                        "dataset": dataset,
                        "fold_id": int(fold_id),
                        "seed": int(seed),
                        "method": "tiger_liger_retrieval",
                        "user_id": user_id,
                        "target_item_id": target_item,
                        "candidate_scope": "full_catalog",
                        "ndcg10": float(n),
                        "hr10": float(h),
                        "rr": float(r),
                    }
                )
            row_offset += scores.shape[0]
    summary = {
        "NDCG@10": float(np.mean(ndcg)) if ndcg else 0.0,
        "HR@10": float(np.mean(hr)) if hr else 0.0,
        "MRR": float(np.mean(rr)) if rr else 0.0,
        "n_records": len(records),
    }
    return records, summary


def run_fold(
    *,
    modules: dict[str, Any],
    export_fold: dict[str, Any],
    out_dir: Path,
    mode: str,
    train_steps: int,
    rqvae_epochs: int,
    max_targets: int,
    codebook_size: int,
    latent_dim: int,
    batch_size: int,
    eval_batch_size: int,
    lr: float,
    d_model: int,
    device: torch.device,
) -> dict[str, Any]:
    dataset = str(export_fold["dataset"])
    seed = int(export_fold["seed"])
    fold_id = int(export_fold["fold_id"])
    data_file = Path(export_fold["data_file"])
    id2meta_file = Path(export_fold["id2meta_file"])
    target_map_file = Path(export_fold["target_map_file"])
    item_embedding = torch.load(export_fold["embedding_file"], map_location="cpu", weights_only=False).float()
    target_rows = parse_target_map(target_map_file, max_targets)
    train_inters, _, n_items = group_fold_train(dataset, seed, fold_id)
    if int(item_embedding.shape[0]) != int(n_items):
        raise ValueError(f"embedding item count {item_embedding.shape[0]} != n_items {n_items}")
    split_cfg = {"dataset": {"max_items_per_seq": int(export_fold.get("max_items_per_seq", 20) or 20)}}
    # The export audit stores max_items_per_seq at top level, but fold records
    # from older exports omit it. Recover from the expected split file.
    expected_split = json.loads(Path(export_fold["expected_split_file"]).read_text(encoding="utf-8"))
    max_items_per_seq = int(expected_split.get("max_items_per_seq", 20))
    split_cfg["dataset"]["max_items_per_seq"] = max_items_per_seq
    id_split, user_sequence = modules["process_data_split"](split_cfg, str(data_file), str(id2meta_file), is_steam=False)
    semantic_id_path = out_dir / "semantic_ids" / dataset / f"seed_{seed}_fold_{fold_id}_cb{codebook_size}_e{rqvae_epochs}.pkl"
    rqvae_audit = make_rqvae_ids(
        modules=modules,
        item_embedding=item_embedding,
        seen_liger_ids=id_split["seen"],
        id_save_path=semantic_id_path,
        device=device,
        seed=seed + fold_id,
        rqvae_epochs=rqvae_epochs,
        codebook_size=codebook_size,
        latent_dim=latent_dim,
        batch_size=batch_size,
    )
    mode_config = method_config(int(item_embedding.shape[1]), mode)
    max_length = max_items_per_seq * 4 + 2
    unseen_val_for_load = id_split["unseen_val"]
    unseen_val_placeholder: int | None = None
    if len(unseen_val_for_load) == 0:
        # Official LIGER load_data assumes unseen_val has at least one item and
        # indexes shape[1] after constructing the semantic-id array. The strict
        # BEST-Rec export has no cold validation targets, so we supply a seen
        # item solely to keep validation bookkeeping non-empty. Test labels,
        # train examples, and canonical scored records are unchanged.
        unseen_val_placeholder = int(id_split["seen"][0])
        unseen_val_for_load = np.array([unseen_val_placeholder], dtype=id_split["seen"].dtype)
    (
        training_data,
        _val_data,
        _test_data,
        _unseen_val_data,
        unseen_test_data,
        seen_semantic_ids,
        _val_unseen_semantic_ids,
        _test_unseen_semantic_ids,
        max_last_semantic_ids,
        n_semantic_codebook,
        _n_codebook,
        item2sid,
    ) = modules["load_data"](
        str(semantic_id_path),
        user_sequence,
        unseen_val_for_load,
        id_split["unseen_test"],
        id_split["seen"],
        item_embedding,
        mode_config,
        max_length=max_length,
        codebook_size=codebook_size,
        max_items_per_seq=max_items_per_seq,
    )
    vocab_size = int(codebook_size * n_semantic_codebook + max(max_last_semantic_ids, codebook_size) + 2)
    seed_everything(modules, seed + 1000 * (fold_id + 1))
    model = build_model(
        modules=modules,
        vocab_size=vocab_size,
        n_positions=max_length,
        n_semantic_codebook=n_semantic_codebook,
        max_items_per_seq=max_items_per_seq,
        mode_config=mode_config,
        d_model=d_model,
    )
    train_audit = train_liger_dense(
        modules=modules,
        model=model,
        training_data=training_data,
        item_embedding=item_embedding,
        item2sid=item2sid,
        seen_liger_ids=id_split["seen"],
        mode_config=mode_config,
        device=device,
        train_steps=train_steps,
        batch_size=batch_size,
        lr=lr,
        seed=seed + 1000 * (fold_id + 1),
    )
    records, summary = score_records(
        modules=modules,
        model=model,
        unseen_test_data=unseen_test_data,
        target_rows=target_rows,
        train_inters=train_inters,
        item_embedding=item_embedding,
        item2sid=item2sid,
        mode_config=mode_config,
        dataset=dataset,
        seed=seed,
        fold_id=fold_id,
        device=device,
        batch_size=eval_batch_size,
    )
    return {
        "records": records,
        "summary": summary,
        "audit": {
            "dataset": dataset,
            "seed": seed,
            "fold_id": fold_id,
            "mode": mode,
            "train_steps": int(train_steps),
            "rqvae_epochs": int(rqvae_epochs),
            "codebook_size": int(codebook_size),
            "latent_dim": int(latent_dim),
            "d_model": int(d_model),
            "target_rows_scored": len(target_rows),
            "training_examples": int(len(training_data["input_ids"])),
            "unseen_test_examples": int(len(unseen_test_data["input_ids"])),
            "unseen_val_placeholder_liger_id": unseen_val_placeholder,
            "rqvae": rqvae_audit,
            "train": train_audit,
            "summary": summary,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--export-run-id", default="liger_export_post_repair_20260701_20260705")
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--seeds", default=CONFIRMATORY_SEEDS_CSV)
    parser.add_argument("--max-folds", type=int, default=0)
    parser.add_argument("--fold-ids", default="", help="Optional comma-separated fold IDs to evaluate for every selected seed; incompatible with --max-folds for publication use.")
    parser.add_argument("--max-targets-per-fold", type=int, default=0)
    parser.add_argument("--resume", action="store_true", help="Skip folds whose existing canonical record count matches the exported target count.")
    parser.add_argument("--mode", choices=["liger_dense", "tiger"], default="liger_dense")
    parser.add_argument("--train-steps", type=int, default=10)
    parser.add_argument("--rqvae-epochs", type=int, default=5)
    parser.add_argument("--codebook-size", type=int, default=32)
    parser.add_argument("--latent-dim", type=int, default=64)
    parser.add_argument("--d-model", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--eval-batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    if args.mode == "tiger":
        raise ValueError("TIGER generative full-catalog record export is not implemented; use liger_dense.")
    requested_device = args.device
    if requested_device == "cuda" and not torch.cuda.is_available():
        requested_device = "cpu"
    device = torch.device(requested_device)
    modules = import_liger_modules()
    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    fold_ids = parse_csv(args.fold_ids, int) if args.fold_ids else []
    if args.max_folds and fold_ids:
        raise ValueError("--max-folds and --fold-ids cannot be combined")
    for dataset in datasets:
        if dataset not in DATASETS:
            raise ValueError(f"unknown dataset: {dataset}")

    export_audit_path = RUNS_DIR / args.export_run_id / "liger_same_split_export_audit.json"
    export_audit = json.loads(export_audit_path.read_text(encoding="utf-8"))
    run_id, run_dir = make_lab_run_dir("liger_same_split_eval", args.run_id)
    protocol = load_protocol()
    strict_seeds = [int(x) for x in protocol.get("fresh_confirmatory_seeds", [])]
    full_publication_scope = (
        set(datasets) == set(DATASETS)
        and list(seeds) == strict_seeds
        and not args.max_folds
        and not fold_ids
        and not args.max_targets_per_fold
        and args.mode == "liger_dense"
        and args.train_steps >= 1000
        and args.rqvae_epochs >= 100
    )
    audit = {
        "schema_version": 1,
        "status": "running",
        "run_id": run_id,
        "source_export_run_id": args.export_run_id,
        "method": "tiger_liger_retrieval",
        "mode": args.mode,
        "stage": "candidate_publication_run" if full_publication_scope else "smoke_or_partial",
        "publication_grade_records": False,
        "generated_utc": utc_now(),
        "official_source_dir": str(LIGER_DIR),
        "device": str(device),
        "config": vars(args),
        "publication_scope_checks": {
            "requires_all_datasets": list(DATASETS),
            "requires_strict_seeds": strict_seeds,
            "datasets_ok": set(datasets) == set(DATASETS),
            "seeds_ok": list(seeds) == strict_seeds,
            "no_fold_cap": not args.max_folds and not fold_ids,
            "no_target_cap": not args.max_targets_per_fold,
            "minimum_train_steps_ok": args.train_steps >= 1000,
            "minimum_rqvae_epochs_ok": args.rqvae_epochs >= 100,
        },
        "datasets": {},
        "notes": [
            "Uses official LIGER modules for RQ-VAE, TIGER model construction, model_forward, and dense target scoring.",
            "Smoke/partial settings are not publication-grade and must not satisfy the strict gate.",
        ],
    }
    audit_path = run_dir / "tiger_liger_retrieval_audit.json"
    write_json(audit_path, audit)
    t0 = time.time()

    for dataset in datasets:
        record_path = run_dir / f"tiger_liger_retrieval_records_{dataset}.jsonl"
        if record_path.exists() and not args.resume:
            record_path.unlink()
        existing_counts = count_existing_records(record_path)
        dataset_audit = {"folds": [], "record_file": str(record_path), "n_records": 0, "resumed": bool(args.resume)}
        folds = export_audit["datasets"][dataset]["folds"]
        selected = [f for f in folds if int(f["seed"]) in seeds]
        if fold_ids:
            selected = [f for f in selected if int(f["fold_id"]) in set(fold_ids)]
        if args.max_folds:
            by_seed: dict[int, int] = {}
            keep = []
            for f in selected:
                seed = int(f["seed"])
                count = by_seed.get(seed, 0)
                if count < args.max_folds:
                    keep.append(f)
                    by_seed[seed] = count + 1
            selected = keep
        for fold in selected:
            key = (int(fold["seed"]), int(fold["fold_id"]))
            expected_records = int(fold["target_count"])
            if args.max_targets_per_fold:
                expected_records = min(expected_records, int(args.max_targets_per_fold))
            if args.resume and key in existing_counts and existing_counts[key] != expected_records:
                raise ValueError(
                    f"{dataset} seed={key[0]} fold={key[1]} has partial/mismatched existing LIGER records "
                    f"({existing_counts[key]} found, expected {expected_records}); use a fresh run id or remove the partial rows."
                )
            if args.resume and existing_counts.get(key) == expected_records:
                skipped = {
                    "dataset": dataset,
                    "seed": key[0],
                    "fold_id": key[1],
                    "status": "skipped_existing_complete",
                    "existing_records": int(existing_counts[key]),
                    "expected_records": int(expected_records),
                }
                dataset_audit["folds"].append(skipped)
                dataset_audit["n_records"] = count_jsonl(record_path)
                audit["datasets"][dataset] = dataset_audit
                write_json(audit_path, audit)
                print(f"{dataset} seed={key[0]} fold={key[1]}: skipped existing complete records={existing_counts[key]}")
                continue
            fold_result = run_fold(
                modules=modules,
                export_fold=fold,
                out_dir=run_dir,
                mode=args.mode,
                train_steps=int(args.train_steps),
                rqvae_epochs=int(args.rqvae_epochs),
                max_targets=int(args.max_targets_per_fold),
                codebook_size=int(args.codebook_size),
                latent_dim=int(args.latent_dim),
                batch_size=int(args.batch_size),
                eval_batch_size=int(args.eval_batch_size),
                lr=float(args.lr),
                d_model=int(args.d_model),
                device=device,
            )
            append_jsonl(record_path, fold_result["records"])
            dataset_audit["folds"].append(fold_result["audit"])
            dataset_audit["n_records"] = count_jsonl(record_path)
            existing_counts[key] = expected_records
            audit["datasets"][dataset] = dataset_audit
            write_json(audit_path, audit)
        audit["datasets"][dataset] = dataset_audit
        write_json(audit_path, audit)

    audit["status"] = "complete" if full_publication_scope else "partial_complete"
    audit["publication_grade_records"] = bool(full_publication_scope and audit["status"] == "complete")
    audit["elapsed_seconds"] = round(time.time() - t0, 3)
    audit["completed_utc"] = utc_now()
    write_json(audit_path, audit)
    print(f"LIGER same-split eval: {run_dir}")
    print(f"Status: {audit['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
