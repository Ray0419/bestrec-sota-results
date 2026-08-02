#!/usr/bin/env python3
"""Validation-only post-training interventions on released FIR checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "_bestrec_run"
sys.path.insert(0, str(RUN_DIR))

import run_sasrec_sbert as rsp  # noqa: E402
from fuse_ease_eval import build_model_from_config  # noqa: E402


MODES = (
    "normal", "zero", "current_only", "lag_only", "channel_mean",
    "orthogonal_history", "orthogonal_lag", "terminal_only",
    "terminal_lag_only", "position_only", "item_only",
    "rank1_projection",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def bootstrap_delta(
    reference: np.ndarray,
    candidate: np.ndarray,
    seed: int,
    n_boot: int,
) -> dict[str, float]:
    """Paired bootstrap for candidate minus reference mean NDCG@10."""
    delta = np.asarray(candidate) - np.asarray(reference)
    rng = np.random.default_rng(seed)
    samples = np.empty(n_boot, dtype=np.float64)
    for start in range(0, n_boot, 100):
        stop = min(start + 100, n_boot)
        idx = rng.integers(0, len(delta), size=(stop - start, len(delta)))
        samples[start:stop] = delta[idx].mean(axis=1)
    lo, hi = np.quantile(samples, [0.025, 0.975])
    return {
        "delta_ndcg10": float(delta.mean()),
        "ci95_low": float(lo),
        "ci95_high": float(hi),
    }


def intervene(model: torch.nn.Module, arm: str, mode: str, original: torch.Tensor) -> None:
    if mode in {
            "normal", "orthogonal_history", "terminal_only",
            "position_only", "item_only"}:
        weight = original
    elif mode == "rank1_projection":
        target = original[:, 0, :].T.to(torch.float64)
        u, s, vh = torch.linalg.svd(target, full_matrices=False)
        estimate = (u[:, :1] * s[:1]) @ vh[:1, :]
        weight = estimate.T.unsqueeze(1).to(dtype=original.dtype)
    elif mode == "zero":
        weight = torch.zeros_like(original)
    elif mode == "current_only":
        weight = torch.zeros_like(original)
        weight[..., -1] = original[..., -1]
    elif mode == "lag_only":
        weight = original.clone()
        weight[..., -1] = 0
    elif mode in {"orthogonal_lag", "terminal_lag_only"}:
        weight = original.clone()
        weight[..., -1] = 0
    elif mode == "channel_mean":
        if arm != "learned":
            raise ValueError("channel_mean is defined only for the learned arm")
        weight = original.mean(dim=0, keepdim=True).expand_as(original).clone()
    else:
        raise ValueError(f"unknown intervention: {mode}")
    with torch.no_grad():
        model.fir_control_module.weight.copy_(weight)
    model._fir_probe_mode = mode


def install_orthogonal_probe(model: torch.nn.Module, arm: str):
    """Project a learned FIR output off the current token for probe modes."""
    if arm != "learned":
        return None

    def hook(_module, inputs, output):
        if getattr(model, "_fir_probe_mode", "normal") not in {
                "orthogonal_history", "orthogonal_lag"}:
            return output
        padded = inputs[0]
        current = padded[..., model.fir_control_kernel_len - 1:]
        coefficient = (output * current).sum(dim=1, keepdim=True) \
            / current.square().sum(dim=1, keepdim=True).clamp_min(1e-8)
        return output - coefficient * current

    return model.fir_control_module.register_forward_hook(hook)


def install_terminal_probe(model: torch.nn.Module, arm: str):
    """Retain the FIR residual only at each sequence's final real position."""
    original_encode = model.encode

    def encode(input_ids, times=None):
        model._fir_probe_input_ids = input_ids
        model._fir_probe_last_position = (
            (input_ids != model.pad_id).sum(dim=1) - 1).clamp_min(0)
        return original_encode(input_ids, times=times)

    def hook(_module, _inputs, output):
        if getattr(model, "_fir_probe_mode", "normal") not in {
                "terminal_only", "terminal_lag_only"}:
            return output
        positions = model._fir_probe_last_position
        if arm == "shared":
            positions = positions.repeat_interleave(model.d_model)
        mask = torch.zeros(
            (output.shape[0], 1, output.shape[-1]),
            dtype=output.dtype, device=output.device)
        mask[torch.arange(output.shape[0], device=output.device), 0, positions] = 1
        return output * mask

    model.encode = encode
    return model.fir_control_module.register_forward_hook(hook)


def install_component_probe(model: torch.nn.Module, arm: str):
    """Split the linear FIR output into item and positional contributions."""
    def hook(module, _inputs, output):
        mode = getattr(model, "_fir_probe_mode", "normal")
        if mode not in {"position_only", "item_only"}:
            return output
        batch, seq_len = model._fir_probe_input_ids.shape
        positions = torch.arange(seq_len, device=output.device)
        position_x = model.pos_emb(positions).unsqueeze(0).expand(batch, -1, -1)
        position_x = torch.nn.functional.pad(
            position_x.transpose(1, 2),
            (model.fir_control_kernel_len - 1, 0))
        if arm == "shared":
            position_x = position_x.reshape(batch * model.d_model, 1, -1)
            position_delta = torch.nn.functional.conv1d(
                position_x, module.weight)
        else:
            position_delta = torch.nn.functional.conv1d(
                position_x, module.weight, groups=model.d_model)
        return position_delta if mode == "position_only" \
            else output - position_delta

    return model.fir_control_module.register_forward_hook(hook)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("learned", "shared"), default="learned")
    ap.add_argument("--seed", type=int, default=20260901)
    ap.add_argument("--subsample-users", type=int, default=1000,
                    help="0 evaluates the complete validation split")
    ap.add_argument("--subsample-seed", type=int, default=314159)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--ni-margin", type=float, default=0.0005)
    ap.add_argument("--threads", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    modes = [x.strip() for x in args.modes.split(",") if x.strip()]
    if args.arm != "learned":
        modes = [x for x in modes if x not in {
            "channel_mean", "orthogonal_history", "orthogonal_lag"}]
    unknown = set(modes) - set(MODES)
    if unknown:
        raise SystemExit(f"unknown modes: {sorted(unknown)}")
    if "normal" not in modes:
        raise SystemExit("modes must include normal as the paired reference")

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    device = torch.device("cpu")
    run_stem = f"results_Musical_Instruments_FIRCTRL_{args.arm}_seed{args.seed}"
    run_path = RUN_DIR / f"{run_stem}.json"
    ckpt_path = RUN_DIR / f"{run_stem}.best.pt"
    if not run_path.exists() or not ckpt_path.exists():
        raise SystemExit(f"missing run artifacts for {run_stem}")

    base = json.loads(run_path.read_text(encoding="utf-8"))
    cfg = base["config"]
    category = cfg["category"]
    train_file = rsp.SPLIT_DIR / f"{category}.train.csv"
    valid_file = rsp.SPLIT_DIR / f"{category}.valid.csv"
    test_file = rsp.SPLIT_DIR / f"{category}.test.csv"
    train_rows = rsp.load_split_csv(train_file)
    valid_rows = rsp.load_split_csv(valid_file)
    # Test rows are used only to reproduce the immutable item-ID mapping that
    # the released checkpoint was trained with. No test target is evaluated.
    test_rows = rsp.load_split_csv(test_file)
    train, valid, _, _, items = rsp.reindex(train_rows, valid_rows, test_rows)
    n_items, pad_id = len(items), len(items)
    seqs = rsp.build_user_sequences(train)
    times = rsp.build_user_time_sequences(train) if cfg.get("time_bias") else None

    emb_path = rsp.EMB_CACHE_DIR / f"sbert_titles_{category}.npy"
    sbert = None if cfg.get("no_sbert") else np.load(emb_path).astype(np.float32)[:n_items]
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    proto = [x.to(device) for x in ckpt.get("proto_assign", [])] or None
    model = build_model_from_config(cfg, n_items, pad_id, sbert, proto)
    model.load_state_dict(ckpt["state_dict"], strict=True)
    model.to(device).eval()
    orthogonal_hook = install_orthogonal_probe(model, args.arm)
    terminal_hook = install_terminal_probe(model, args.arm)
    component_hook = install_component_probe(model, args.arm)
    original = model.fir_control_module.weight.detach().clone()

    results: dict[str, dict] = {}
    records: dict[str, np.ndarray] = {}
    started = time.time()
    for mode in modes:
        intervene(model, args.arm, mode, original)
        t0 = time.time()
        metrics = rsp.evaluate(
            model, seqs, valid, n_items, pad_id, cfg["max_seq_len"], device,
            top_k=10, batch_size=args.batch_size,
            subsample_users=args.subsample_users,
            subsample_seed=args.subsample_seed,
            user_times=times,
            cosine=cfg.get("cosine_scoring", False),
        )
        user_records = metrics.pop("_user_records")
        records[mode] = np.asarray(user_records["ndcg10"], dtype=np.float64)
        results[mode] = {**metrics, "elapsed_seconds": time.time() - t0}

    reference = records["normal"]
    comparisons = {}
    for i, mode in enumerate(modes):
        if mode == "normal":
            continue
        stats = bootstrap_delta(
            reference, records[mode], args.subsample_seed + i, args.bootstrap)
        # NI is established when the lower confidence bound on candidate-normal
        # is no worse than -margin.
        stats["noninferior_at_margin"] = stats["ci95_low"] > -args.ni_margin
        comparisons[mode] = stats

    artifact = {
        "protocol": "FIR_INFERENCE_ABLATION_VALIDATION_ONLY_V1",
        "category": category,
        "arm": args.arm,
        "seed": args.seed,
        "selected_epoch": int(ckpt["epoch"]),
        "selected_val_NDCG10_recorded": float(ckpt["val_NDCG10"]),
        "subsample_users": args.subsample_users,
        "subsample_seed": args.subsample_seed,
        "ni_margin_ndcg10": args.ni_margin,
        "modes": modes,
        "results": results,
        "paired_vs_normal": comparisons,
        "kernel": {
            "shape": list(original.shape),
            "mean_abs": float(original.abs().mean()),
            "current_tap_mean_abs": float(original[..., -1].abs().mean()),
            "strict_lag_mean_abs": float(original[..., :-1].abs().mean()),
        },
        "elapsed_seconds": time.time() - started,
        "provenance": {
            "run_json": str(run_path.relative_to(ROOT)),
            "run_json_sha256": sha256(run_path),
            "checkpoint": str(ckpt_path.relative_to(ROOT)),
            "checkpoint_sha256": sha256(ckpt_path),
            "test_usage": "item-ID mapping only; no test target scored",
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    if orthogonal_hook is not None:
        orthogonal_hook.remove()
    terminal_hook.remove()
    component_hook.remove()
    print(json.dumps({
        "out": str(args.out),
        "results": {k: v["NDCG@10"] for k, v in results.items()},
        "paired_vs_normal": comparisons,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
