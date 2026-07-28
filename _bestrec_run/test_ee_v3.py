#!/usr/bin/env python3
"""Prelaunch structural and evaluator-conformance gates for PREREG_EE_V3."""

from __future__ import annotations

import ast

import numpy as np
import torch

import ee_v3_common as common


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def test_training_sequestration() -> None:
    path = common.HERE / "run_ee_v3.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    require("test_data.df" not in source, "training runner names TEST data")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = ""
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
        elif isinstance(node.func, ast.Name):
            name = node.func.id
        if name == "load_eval_inputs" and node.args:
            require(not (isinstance(node.args[0], ast.Constant)
                         and node.args[0].value == "test"),
                    "training runner loads TEST evaluation inputs")
        if name == "verify_data":
            for keyword in node.keywords:
                require(not (keyword.arg == "include_test"
                             and isinstance(keyword.value, ast.Constant)
                             and keyword.value.value is True),
                        "training runner verifies/reads TEST data")


def test_synthetic_rank_rules() -> None:
    scores = np.full((1, common.N_ITEMS), -2.0, dtype=np.float64)
    target = 7
    tie = 8
    genuinely_higher = 9
    seen_higher = 10
    scores[0, target] = 1.0
    scores[0, tie] = 1.0
    scores[0, genuinely_higher] = 2.0
    scores[0, seen_higher] = 3.0
    rank = common.ranks_from_scores(
        scores, [target], [[target, seen_higher, target]])
    require(rank.tolist() == [1],
            "strict-greater tie, target exception, or seen mask is wrong")
    metrics = common.metric_family(rank)
    require(metrics["HR@5"] == 1.0 and metrics["NDCG@5"] == 1.0 / np.log2(3.0),
            "rank-to-metric arithmetic mismatch")


def test_real_long_history_and_paper_formula() -> None:
    histories, _ = common.load_train_histories()
    seqs, targets, seen = common.load_eval_inputs("valid")
    candidates = [i for i, history in enumerate(histories) if len(history) > common.MAX_LEN]
    require(candidates, "real data contains no history longer than model input")
    user = candidates[0]
    history = histories[user]
    target = targets[user]
    old_seen = next(x for x in history[:-common.MAX_LEN] if x != target)
    recent_seen = next(x for x in history[-common.MAX_LEN:] if x != target)
    unseen = next(x for x in range(common.N_ITEMS)
                  if x != target and x not in set(seen[user]))
    require(old_seen not in seqs[user], "chosen old item unexpectedly remains in last-50 input")

    scores = np.full((1, common.N_ITEMS), -4.0, dtype=np.float64)
    scores[0, target] = 1.0
    scores[0, old_seen] = 4.0
    scores[0, recent_seen] = 3.0
    scores[0, unseen] = 2.0
    rank = common.ranks_from_scores(scores, [target], [seen[user]])

    paper_style = scores.copy()
    mask = [x for x in seen[user] if x != target]
    paper_style[0, np.asarray(mask, dtype=np.int64)] = -np.inf
    target_score = paper_style[0, target]
    direct_rank = int((paper_style[0] > target_score).sum())
    require(rank.tolist() == [1] and direct_rank == int(rank[0]),
            "real-data rank differs from paper strict-greater arithmetic")
    paper_source = (common.HERE / "run_sasrec_sbert.py").read_text(encoding="utf-8")
    require("rank0 = int((final[k] > tgt_score).sum().item())" in paper_source,
            "paper evaluator rank formula changed")


def test_official_model_contracts() -> None:
    common.verify_upstream()
    common.verify_data(include_test=False)
    frame = common.load_train_frame().iloc[:2]
    seq = torch.stack([torch.as_tensor(x, dtype=torch.long) for x in frame["seq"]])
    target = torch.as_tensor(frame["next"].to_numpy(copy=True), dtype=torch.long)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    seq = seq.to(device)
    target = target.to(device)
    for arm in common.ARMS:
        common.set_seed(common.SEEDS[0])
        model = common.build_model(arm, common.SEEDS[0], device)
        model.eval()
        with torch.no_grad():
            state = model(seq)
            item = model.return_item_emb()
        require(state.shape == (2, 128), f"{arm} forward contract changed: {state.shape}")
        require(item.shape[0] == common.N_ITEMS + 1,
                f"{arm} item-table contract changed: {item.shape}")
        model.train()
        loss = model.calculate_infonce_loss(seq, target, 64, 0.07)
        require(bool(torch.isfinite(loss)), f"{arm} InfoNCE smoke loss is non-finite")
        loss.backward()
        gradients = [p.grad for p in model.parameters() if p.grad is not None]
        require(gradients and all(bool(torch.isfinite(g).all()) for g in gradients),
                f"{arm} smoke backward produced missing/non-finite gradients")
        require(any(bool(torch.count_nonzero(g)) for g in gradients),
                f"{arm} smoke backward produced no active gradient")


def main() -> int:
    test_training_sequestration()
    test_synthetic_rank_rules()
    test_real_long_history_and_paper_formula()
    test_official_model_contracts()
    print("PREREG_EE_V3 structural/conformance suite: PASS")
    print("TEST was not loaded; real-data check used VALID only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
