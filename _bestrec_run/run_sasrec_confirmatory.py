"""Publication-grade confirmatory rerun harness for SASRec-SBERT.

This script intentionally writes new artifacts under `_bestrec_confirmatory_sasrec/`
and does not overwrite historical exploratory JSON files. It reuses the
implementation in `run_sasrec_sbert.py`, but adds the pieces needed by a strict
reviewer:

- fresh seed list recorded in a run config;
- validation-selected checkpoint restored for final test evaluation;
- per-user JSONL records with full-catalog candidate scope;
- environment, command, source/input/output hashes in a manifest;
- an explicit publication gate that remains failed until protocol-matched
  external comparators are reproduced.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader

import run_sasrec_sbert as base


ROOT = Path(__file__).resolve().parent.parent
RUN_ROOT = ROOT / "_bestrec_confirmatory_sasrec"
DEFAULT_SEEDS = [20260608, 20260609, 20260610, 20260611, 20260612]
METHOD_CONFIGS: dict[str, dict[str, Any]] = {
    "sasrec_sbert": {
        "no_sbert": False,
        "encoder_cache": None,
        "mlp_adaptor": False,
        "sbert_only": False,
    },
    "sasrec_no_sbert": {
        "no_sbert": True,
        "encoder_cache": None,
        "mlp_adaptor": False,
        "sbert_only": False,
    },
    "sasrec_blair": {
        "no_sbert": False,
        "encoder_cache_template": "cache_5core/blair_titles_{category}.npy",
        "mlp_adaptor": False,
        "sbert_only": False,
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def run_cmd(args: list[str]) -> dict[str, Any]:
    try:
        out = subprocess.check_output(args, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return {"ok": True, "output": out.strip()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def parse_csv_ints(value: str) -> list[int]:
    return [int(x.strip()) for x in value.split(",") if x.strip()]


def parse_csv_strs(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = False


def metric_from_rank(rank0: int, top_k: int = 10) -> tuple[float, float, float]:
    if rank0 < top_k:
        return 1.0 / math.log2(rank0 + 2), 1.0, 1.0 / (rank0 + 1)
    return 0.0, 0.0, 1.0 / (rank0 + 1)


def evaluate_with_records(
    model: base.SASRecSBERT,
    user_seqs: dict[int, list[int]],
    test_inters: list[tuple[int, int, float, int]],
    n_items: int,
    pad_id: int,
    max_seq_len: int,
    device: str,
    *,
    dataset: str,
    seed: int,
    method: str,
    user_lookup: list[str],
    item_lookup: list[str],
    extra_history: dict[int, list[int]] | None = None,
    records_path: Path | None = None,
    batch_size: int = 512,
    top_k: int = 10,
    subsample_users: int = 0,
    subsample_seed: int = 0,
) -> dict[str, Any]:
    model.eval()
    test_dict = {u: i for u, i, _, _ in test_inters}
    users = sorted(test_dict.keys())
    if subsample_users and subsample_users < len(users):
        rng = np.random.RandomState(subsample_seed)
        users = sorted(rng.choice(users, subsample_users, replace=False).tolist())
    extra = extra_history or {}
    ndcg: list[float] = []
    hr: list[float] = []
    rr: list[float] = []

    fp = records_path.open("w", encoding="utf-8", newline="\n") if records_path else None
    try:
        with torch.no_grad():
            all_items = model.all_item_features()
            for s in range(0, len(users), batch_size):
                batch_users = users[s:s + batch_size]
                input_ids = torch.full(
                    (len(batch_users), max_seq_len),
                    pad_id,
                    dtype=torch.long,
                    device=device,
                )
                train_items: list[list[int]] = []
                real_len: list[int] = []
                for k, u in enumerate(batch_users):
                    seq = list(user_seqs.get(u, []))
                    if u in extra:
                        seq = seq + list(extra[u])
                    train_items.append(seq)
                    truncated = seq[-max_seq_len:]
                    real_len.append(len(truncated))
                    if truncated:
                        input_ids[k, : len(truncated)] = torch.tensor(
                            truncated, dtype=torch.long, device=device
                        )

                hidden = model.encode(input_ids)
                last_real_pos = torch.tensor(
                    [max(0, n - 1) for n in real_len], device=device
                )
                last_h = hidden[torch.arange(len(batch_users), device=device), last_real_pos, :]
                scores = last_h @ all_items.T
                if torch.isnan(scores).any():
                    raise RuntimeError("NaN logits during confirmatory evaluation")
                for k, items in enumerate(train_items):
                    if items:
                        scores[k, items] = -float("inf")

                for k, u in enumerate(batch_users):
                    tgt = test_dict[u]
                    if real_len[k] == 0:
                        rank0 = n_items
                    else:
                        tgt_score = scores[k, tgt].item()
                        rank0 = int((scores[k] > tgt_score).sum().item())
                    n_, h_, r_ = metric_from_rank(rank0, top_k=top_k)
                    ndcg.append(n_)
                    hr.append(h_)
                    rr.append(r_)
                    if fp:
                        row = {
                            "dataset": dataset,
                            "fold_id": 0,
                            "seed": int(seed),
                            "method": method,
                            "user_id": user_lookup[u],
                            "target_item_id": item_lookup[tgt],
                            "candidate_scope": "full_catalog",
                            "ndcg10": float(n_),
                            "hr10": float(h_),
                            "rr": float(r_),
                            "rank0": int(rank0),
                        }
                        fp.write(json.dumps(row, separators=(",", ":")) + "\n")
    finally:
        if fp:
            fp.close()

    return {
        "NDCG@10": float(np.mean(ndcg)) if ndcg else 0.0,
        "HR@10": float(np.mean(hr)) if hr else 0.0,
        "MRR": float(np.mean(rr)) if rr else 0.0,
        "n_eval": len(users),
    }


def load_category(category: str) -> dict[str, Any]:
    train_csv = base.SPLIT_DIR / f"{category}.train.csv"
    valid_csv = base.SPLIT_DIR / f"{category}.valid.csv"
    test_csv = base.SPLIT_DIR / f"{category}.test.csv"
    for path in (train_csv, valid_csv, test_csv):
        if not path.exists():
            raise FileNotFoundError(path)
    train_rows = base.load_split_csv(train_csv)
    valid_rows = base.load_split_csv(valid_csv)
    test_rows = base.load_split_csv(test_csv)
    train_inters, valid_inters, test_inters, user_list, item_list = base.reindex(
        train_rows, valid_rows, test_rows
    )
    return {
        "train_csv": train_csv,
        "valid_csv": valid_csv,
        "test_csv": test_csv,
        "train_inters": train_inters,
        "valid_inters": valid_inters,
        "test_inters": test_inters,
        "user_list": user_list,
        "item_list": item_list,
        "user_seqs": base.build_user_sequences(train_inters),
        "n_users": len(user_list),
        "n_items": len(item_list),
        "pad_id": len(item_list),
    }


def resolve_method_config(method: str, category: str) -> dict[str, Any]:
    cfg = deepcopy(METHOD_CONFIGS[method])
    template = cfg.pop("encoder_cache_template", None)
    if template:
        cfg["encoder_cache"] = str(ROOT / template.format(category=category))
    return cfg


def load_text_cache(category: str, n_items: int, cfg: dict[str, Any]) -> np.ndarray | None:
    if cfg.get("no_sbert"):
        return None
    cache = Path(cfg["encoder_cache"]) if cfg.get("encoder_cache") else base.EMB_CACHE_DIR / f"sbert_titles_{category}.npy"
    if not cache.exists():
        raise FileNotFoundError(cache)
    arr = np.load(cache).astype(np.float32)
    if arr.shape[0] != n_items:
        arr = arr[:n_items]
    return arr


def run_one(
    *,
    run_dir: Path,
    category: str,
    data: dict[str, Any],
    method: str,
    seed: int,
    args: argparse.Namespace,
) -> dict[str, Any]:
    set_seed(seed)
    method_cfg = resolve_method_config(method, category)
    text_emb = load_text_cache(category, data["n_items"], method_cfg)
    model = base.SASRecSBERT(
        n_items=data["n_items"],
        pad_id=data["pad_id"],
        max_seq_len=args.max_seq_len,
        d_model=args.d_model,
        n_layers=args.n_layers,
        n_heads=args.n_heads,
        dropout=args.dropout,
        sbert_emb=text_emb,
        sbert_only=bool(method_cfg.get("sbert_only", False)),
        mlp_adaptor=bool(method_cfg.get("mlp_adaptor", False)),
        mlp_hidden=args.mlp_hidden,
        mlp_dropout=args.mlp_dropout,
    ).to(base.DEVICE)

    dataset = base.SASRecDataset(
        data["user_seqs"],
        args.max_seq_len,
        data["n_items"],
        data["pad_id"],
        augment_factor=args.augment_factor,
    )
    generator = torch.Generator()
    generator.manual_seed(seed)
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
        collate_fn=base.collate_batch,
        drop_last=False,
        generator=generator,
    )
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-5)

    best_val = -1.0
    best_epoch = 0
    best_state: dict[str, torch.Tensor] | None = None
    best_test_at_eval: dict[str, Any] | None = None
    history: list[dict[str, Any]] = []
    valid_extra = None
    valid_dict = {u: i for u, i, _, _ in data["valid_inters"]}
    test_extra = {u: [i] for u, i in valid_dict.items()}
    print(f"\n=== {category} {method} seed={seed} epochs={args.epochs} ===")
    t0_total = time.time()
    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        loss, n_pos = base.train_one_epoch(
            model,
            loader,
            opt,
            data["pad_id"],
            base.DEVICE,
            sampled_negs=args.sampled_negs,
            in_batch_negs=args.in_batch_negs,
            chunked_full_softmax=args.chunked_full_softmax,
            item_chunk=args.item_chunk,
        )
        row: dict[str, Any] = {
            "epoch": epoch,
            "train_loss": float(loss),
            "n_valid_positions": int(n_pos),
            "epoch_time_s": time.time() - t0,
        }
        if epoch % args.eval_every == 0 or epoch == args.epochs:
            subs = args.eval_subsample if epoch < args.epochs else 0
            val = evaluate_with_records(
                model,
                data["user_seqs"],
                data["valid_inters"],
                data["n_items"],
                data["pad_id"],
                args.max_seq_len,
                base.DEVICE,
                dataset=category,
                seed=seed,
                method=method,
                user_lookup=data["user_list"],
                item_lookup=data["item_list"],
                extra_history=valid_extra,
                records_path=None,
                batch_size=args.eval_batch_size,
                subsample_users=subs,
                subsample_seed=seed + epoch,
            )
            test = evaluate_with_records(
                model,
                data["user_seqs"],
                data["test_inters"],
                data["n_items"],
                data["pad_id"],
                args.max_seq_len,
                base.DEVICE,
                dataset=category,
                seed=seed,
                method=method,
                user_lookup=data["user_list"],
                item_lookup=data["item_list"],
                extra_history=test_extra,
                records_path=None,
                batch_size=args.eval_batch_size,
                subsample_users=subs,
                subsample_seed=seed + epoch + 17,
            )
            row["val"] = val
            row["test"] = test
            print(
                f"  epoch {epoch:>3d} loss={loss:.4f} "
                f"val={val['NDCG@10']:.5f} test={test['NDCG@10']:.5f} "
                f"time={row['epoch_time_s']:.1f}s"
            )
            if val["NDCG@10"] > best_val:
                best_val = float(val["NDCG@10"])
                best_epoch = epoch
                best_test_at_eval = test
                best_state = {
                    k: v.detach().cpu().clone()
                    for k, v in model.state_dict().items()
                }
        else:
            print(f"  epoch {epoch:>3d} loss={loss:.4f} time={row['epoch_time_s']:.1f}s")
        history.append(row)

    if best_state is None:
        raise RuntimeError("no validation checkpoint was selected")
    model.load_state_dict(best_state)
    records_path = run_dir / f"warm_full_catalog_records_{category}_{method}_seed{seed}.jsonl"
    final_test = evaluate_with_records(
        model,
        data["user_seqs"],
        data["test_inters"],
        data["n_items"],
        data["pad_id"],
        args.max_seq_len,
        base.DEVICE,
        dataset=category,
        seed=seed,
        method=method,
        user_lookup=data["user_list"],
        item_lookup=data["item_list"],
        extra_history=test_extra,
        records_path=records_path,
        batch_size=args.eval_batch_size,
    )
    result = {
        "schema_version": 1,
        "dataset": category,
        "candidate_scope": "full_catalog",
        "method": method,
        "seed": int(seed),
        "best_epoch": int(best_epoch),
        "best_val_NDCG10": float(best_val),
        "best_test_at_eval": best_test_at_eval,
        "final_test_from_restored_best_checkpoint": final_test,
        "n_users": data["n_users"],
        "n_items": data["n_items"],
        "n_params": int(sum(p.numel() for p in model.parameters())),
        "config": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "eval_batch_size": args.eval_batch_size,
            "max_seq_len": args.max_seq_len,
            "d_model": args.d_model,
            "n_layers": args.n_layers,
            "n_heads": args.n_heads,
            "dropout": args.dropout,
            "lr": args.lr,
            "sampled_negs": args.sampled_negs,
            "in_batch_negs": args.in_batch_negs,
            "chunked_full_softmax": args.chunked_full_softmax,
            "item_chunk": args.item_chunk,
            "augment_factor": args.augment_factor,
            "method_config": method_cfg,
        },
        "history": history,
        "records_path": rel(records_path),
        "runtime_s": time.time() - t0_total,
    }
    result_path = run_dir / f"result_{category}_{method}_seed{seed}.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def load_records_for_method(run_dir: Path, category: str, method: str) -> dict[tuple[int, str, str], float]:
    out: dict[tuple[int, str, str], float] = {}
    for path in run_dir.glob(f"warm_full_catalog_records_{category}_{method}_seed*.jsonl"):
        with path.open("r", encoding="utf-8") as fp:
            for line in fp:
                row = json.loads(line)
                key = (int(row["seed"]), str(row["user_id"]), str(row["target_item_id"]))
                out[key] = float(row["ndcg10"])
    return out


def summarize_run(run_dir: Path, category: str, methods: list[str], seeds: list[int]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "schema_version": 1,
        "dataset": category,
        "candidate_scope": "full_catalog",
        "seeds": seeds,
        "methods": {},
        "paired_tests": {},
    }
    for method in methods:
        vals = []
        records_total = 0
        for seed in seeds:
            result_path = run_dir / f"result_{category}_{method}_seed{seed}.json"
            if not result_path.exists():
                continue
            data = json.loads(result_path.read_text(encoding="utf-8"))
            vals.append(float(data["final_test_from_restored_best_checkpoint"]["NDCG@10"]))
            records_path = ROOT / data["records_path"]
            if records_path.exists():
                with records_path.open("r", encoding="utf-8") as fp:
                    records_total += sum(1 for _ in fp)
        summary["methods"][method] = {
            "n_completed_seeds": len(vals),
            "ndcg10_values": vals,
            "mean_ndcg10": float(np.mean(vals)) if vals else None,
            "std_ndcg10": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
            "records_total": records_total,
        }

    if "sasrec_sbert" in methods:
        cand = load_records_for_method(run_dir, category, "sasrec_sbert")
        raw_tests: list[tuple[str, dict[str, Any]]] = []
        for baseline in methods:
            if baseline == "sasrec_sbert":
                continue
            base_records = load_records_for_method(run_dir, category, baseline)
            common = sorted(set(cand) & set(base_records))
            diffs = np.array([cand[k] - base_records[k] for k in common], dtype=np.float64)
            test: dict[str, Any] = {
                "candidate": "sasrec_sbert",
                "baseline": baseline,
                "alternative": "candidate_greater",
                "sample_unit": "per-user per-seed NDCG@10 record",
                "n_pairs": int(len(common)),
                "mean_delta_ndcg10": float(np.mean(diffs)) if len(diffs) else None,
            }
            try:
                from scipy.stats import wilcoxon

                if len(diffs):
                    stat, p = wilcoxon(diffs, alternative="greater", zero_method="zsplit")
                    test.update({"wilcoxon_statistic": float(stat), "p_value": float(p)})
            except Exception as exc:
                test["wilcoxon_error"] = str(exc)
            raw_tests.append((f"sasrec_sbert_vs_{baseline}", test))

        # Holm correction over the same-run comparator family.
        p_items = [
            (name, test["p_value"])
            for name, test in raw_tests
            if test.get("p_value") is not None
        ]
        for rank, (name, p_value) in enumerate(sorted(p_items, key=lambda x: x[1]), start=1):
            multiplier = len(p_items) - rank + 1
            for raw_name, test in raw_tests:
                if raw_name == name:
                    test["holm_adjusted_p_value"] = min(1.0, float(p_value) * multiplier)
                    test["holm_family"] = "sasrec_sbert_vs_same_run_confirmatory_comparators"

        for name, test in raw_tests:
            summary["paired_tests"][name] = test
    return summary


def write_gate(run_dir: Path, summary: dict[str, Any], methods: list[str], seeds: list[int]) -> dict[str, Any]:
    all_complete = all(
        summary["methods"].get(m, {}).get("n_completed_seeds") == len(seeds)
        for m in methods
    )
    records_present = all(
        summary["methods"].get(m, {}).get("records_total", 0) > 0
        for m in methods
    )
    gate = {
        "schema_version": 1,
        "confirmatory_run_complete": bool(all_complete),
        "per_user_records_present": bool(records_present),
        "fresh_seed_count": len(seeds),
        "same_run_comparators_reproduced": [m for m in methods if m != "sasrec_sbert"],
        "same_run_paired_tests": summary.get("paired_tests", {}),
        "external_protocol_matched_comparators_reproduced": False,
        "known_external_blockers": [
            {
                "method": "HSTU-BLaIR",
                "source": "https://github.com/snapfinger/HSTU-BLaIR",
                "reported_video_games_ndcg10": 0.0760,
                "local_status": (
                    "not reproduced in this Windows confirmatory package; upstream code "
                    "requires Ubuntu/Python 3.9/CUDA, fbgemm_gpu/torchrec, and uses "
                    "multiprocessing forkserver plus CUDA-only operators"
                ),
                "claim_impact": "blocks broad SOTA claim unless reproduced under the same protocol or beaten",
            },
            {
                "method": "TIGER/LIGER",
                "source": "https://arxiv.org/abs/2411.18814",
                "local_status": (
                    "local LIGER checkout targets Amazon 2014 Beauty/Toys/Sports and Steam, "
                    "not this Amazon Reviews 2023 Video_Games split; protocol-matched "
                    "adaptation was not completed"
                ),
                "claim_impact": "blocks broad generative-retrieval SOTA wording",
            },
        ],
        "final_unqualified_sota_claim_allowed": False,
        "strict_reviewer_verdict": (
            "same-run SASRec ablations are auditable, but final SOTA claim remains blocked "
            "by unreproduced stronger external comparators, especially reported HSTU-BLaIR"
        ),
    }
    path = run_dir / "publication_gate.json"
    path.write_text(json.dumps(gate, indent=2), encoding="utf-8")
    return gate


def write_manifest(
    run_dir: Path,
    *,
    category: str,
    methods: list[str],
    seeds: list[int],
    args: argparse.Namespace,
) -> dict[str, Any]:
    paths = [
        base.SPLIT_DIR / f"{category}.train.csv",
        base.SPLIT_DIR / f"{category}.valid.csv",
        base.SPLIT_DIR / f"{category}.test.csv",
        Path(__file__),
        Path(base.__file__),
    ]
    for method in methods:
        cfg = resolve_method_config(method, category)
        if not cfg.get("no_sbert"):
            cache = Path(cfg["encoder_cache"]) if cfg.get("encoder_cache") else base.EMB_CACHE_DIR / f"sbert_titles_{category}.npy"
            paths.append(cache)
    input_hashes = {rel(p): sha256_file(p) for p in paths if p.exists()}
    mutable_logs = {"process_stdout.log", "process_stderr.log"}
    output_hashes = {
        rel(p): sha256_file(p)
        for p in sorted(run_dir.glob("*"))
        if p.is_file() and p.name not in {"results_manifest.json", *mutable_logs}
    }
    manifest = {
        "schema_version": 1,
        "run_id": run_dir.name,
        "timestamp_utc": utc_now(),
        "command": " ".join(sys.argv),
        "cwd": str(ROOT),
        "category": category,
        "methods": methods,
        "seeds": seeds,
        "config": vars(args),
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "device": base.DEVICE,
            "nvidia_smi": run_cmd(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv,noheader"]),
            "git_head": run_cmd(["git", "rev-parse", "HEAD"]),
            "git_status_short": run_cmd(["git", "status", "--short"]),
        },
        "input_hashes": input_hashes,
        "output_hashes": output_hashes,
    }
    path = run_dir / "results_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", default="Video_Games")
    parser.add_argument("--seeds", default=",".join(str(s) for s in DEFAULT_SEEDS))
    parser.add_argument("--methods", default="sasrec_sbert")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--eval-batch-size", type=int, default=512)
    parser.add_argument("--max-seq-len", type=int, default=50)
    parser.add_argument("--d-model", type=int, default=64)
    parser.add_argument("--n-layers", type=int, default=2)
    parser.add_argument("--n-heads", type=int, default=2)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--eval-every", type=int, default=5)
    parser.add_argument("--eval-subsample", type=int, default=0)
    parser.add_argument("--sampled-negs", type=int, default=0)
    parser.add_argument("--in-batch-negs", action="store_true")
    parser.add_argument("--chunked-full-softmax", action="store_true")
    parser.add_argument("--item-chunk", type=int, default=8192)
    parser.add_argument("--augment-factor", type=int, default=1)
    parser.add_argument("--mlp-hidden", type=int, default=300)
    parser.add_argument("--mlp-dropout", type=float, default=0.2)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    seeds = parse_csv_ints(args.seeds)
    methods = parse_csv_strs(args.methods)
    unknown = sorted(set(methods) - set(METHOD_CONFIGS))
    if unknown:
        raise SystemExit(f"Unknown methods: {unknown}. Valid: {sorted(METHOD_CONFIGS)}")
    run_id = args.run_id or f"{args.category}_sasrec_confirmatory_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = RUN_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_config_path = run_dir / "run_config.json"
    current_config = {
        "run_id": run_id,
        "created_utc": utc_now(),
        "category": args.category,
        "methods": methods,
        "seeds": seeds,
        "candidate_scope": "full_catalog",
        "argv": sys.argv,
        "config": vars(args),
    }
    if args.resume and run_config_path.exists():
        existing = json.loads(run_config_path.read_text(encoding="utf-8"))
        existing_methods = set(existing.get("methods", []))
        existing["methods"] = sorted(existing_methods | set(methods))
        existing["seeds"] = sorted(set(int(x) for x in existing.get("seeds", [])) | set(seeds))
        existing.setdefault("resume_updates", []).append(
            {
                "timestamp_utc": utc_now(),
                "argv": sys.argv,
                "methods": methods,
                "seeds": seeds,
                "config": vars(args),
            }
        )
        run_config_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    else:
        run_config_path.write_text(json.dumps(current_config, indent=2), encoding="utf-8")

    print(f"Run directory: {run_dir}")
    data = load_category(args.category)
    print(
        f"Loaded {args.category}: users={data['n_users']:,} "
        f"items={data['n_items']:,} device={base.DEVICE}"
    )
    for method in methods:
        for seed in seeds:
            result_path = run_dir / f"result_{args.category}_{method}_seed{seed}.json"
            records_path = run_dir / f"warm_full_catalog_records_{args.category}_{method}_seed{seed}.jsonl"
            if args.resume and result_path.exists() and records_path.exists():
                print(f"Skipping existing {method} seed={seed}")
                continue
            run_one(
                run_dir=run_dir,
                category=args.category,
                data=data,
                method=method,
                seed=seed,
                args=args,
            )

    summary = summarize_run(run_dir, args.category, methods, seeds)
    (run_dir / "results_final.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    gate = write_gate(run_dir, summary, methods, seeds)
    manifest = write_manifest(run_dir, category=args.category, methods=methods, seeds=seeds, args=args)
    print("\n=== Confirmatory summary ===")
    print(json.dumps(summary["methods"], indent=2))
    print("\n=== Publication gate ===")
    print(json.dumps(gate, indent=2))
    print(f"\nwrote manifest with {len(manifest['output_hashes'])} output hashes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
